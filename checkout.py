import csv
import sys
import os.path as path

from config import Config
from goodreads import GoodReads
from checkoutgui import Ui_MainWindow
from datetime import datetime
from PyQt4 import QtGui, QtCore
from shelfdialog import Ui_Dialog as BaseShelfDialog

CONFIG_FILE_PATH = path.normpath(path.expanduser("~/checkout.credentials"))

USER_LABEL_TEXT = 'Currently logged in as %s.'
CHECKEDOUT_SHELF_LABEL_TEXT = 'Your "%s" shelf is being used to store the books that are checked out.'
CHECKEDIN_SHELF_LABEL_TEXT = 'Your "%s" shelf is being used to store the books that are available.'
LOG_LABEL_TEXT = 'The log is recorded at "%s".'
_LOG_PATH_KEY = 'LOG_PATH'
_INVENTORY_PATH_KEY = 'INVENTORY_PATH'

CHECKED_IN = "CHECKED_IN" 
CHECKED_OUT = "CHECKED_OUT"
TITLE = "TITLE"
AUTHOR = "AUTHOR"
BOOKSORT = lambda (id, title, author): (author, title)

""" To regenerate the gui from the design: pyuic4 checkout.ui -o checkoutgui.py"""
class Main(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)

        self.progress = QtGui.QProgressDialog(self)
        self.progress.setRange(0,0)
        self.progress.setWindowTitle("Working...")
        self.asyncs = []
        self.inventory = {}

    def startup(self):
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.search_reset.hide()
        self.ui.books.setFocus()

        self.ui.search_query.setDefaultText()

        def initialize(log):
            log("Loading: " + CONFIG_FILE_PATH)
            try:
                with open(CONFIG_FILE_PATH, "r") as configfile:
                    config = Config.load_from_file(configfile)
            except IOError as e:
                    print("Error loading: %s (%s). (This is normal for a first run)" % (CONFIG_FILE_PATH, e))
                    config = Config(CONFIG_FILE_PATH)

            log("Loading Keys for Goodreads")
            if "DEVELOPER_KEY" not in config or "DEVELOPER_SECRET" not in config:
                key, success = QtGui.QInputDialog.getText(None, "Developer Key?",
                        'A developer key is needed to communicate with goodreads.\nYou can usually find it here: http://www.goodreads.com/api/keys')
                if not success: exit()

                config["DEVELOPER_KEY"] = str(key)

                secret, success = QtGui.QInputDialog.getText(None, "Developer Secret?",
                        'What is the developer secret for the key that you just gave?\n(It\'s also on that page with the key: http://www.goodreads.com/api/keys)')
                if not success: exit()
                config["DEVELOPER_SECRET"] = str(secret)

            log("Setting up a GoodReads Connection")
            self.goodreads = GoodReads(config, waitfunction=self.wait_for_user, log=log)

            if "CHECKEDOUT_SHELF" not in config:
                self.on_switch_checkedout_button_pressed(refresh=False)

            if "CHECKEDIN_SHELF" not in config:
                self.on_switch_checkedin_button_pressed(refresh=False)

            if _LOG_PATH_KEY not in self.goodreads.config:
                self.goodreads.config[_LOG_PATH_KEY] = path.normpath(path.expanduser("~/checkout.csv"))

            log("Loading your inventory")
            if _INVENTORY_PATH_KEY not in self.goodreads.config:
                config[_INVENTORY_PATH_KEY] = path.normpath(path.expanduser("~/inventory.csv"))

            try:
                with open(config[_INVENTORY_PATH_KEY], 'rb') as inventoryfile:
                    for (id, title, author, num_in, num_out) in csv.reader(inventoryfile):
                        self.inventory[int(id)] = {TITLE: title, AUTHOR: author, CHECKED_IN: int(num_in), CHECKED_OUT: int(num_out)}
            except IOError as e:
                try:
                    log("Creating a new inventory file")
                    with open(config[_INVENTORY_PATH_KEY], 'wb') as inventoryfile:
                        log("Creating a new inventory file")
                        writer = csv.writer(inventoryfile)
                        for id, title, author in self.goodreads.listbooks(self.goodreads.checkedin_shelf):
                            writer.writerow([id, title, author, 1, 0])
                            self.inventory[int(id)] = {TITLE: title, AUTHOR: author, CHECKED_IN: 1, CHECKED_OUT: 0}
                        for id, title, author in self.goodreads.listbooks(self.goodreads.checkedout_shelf):
                            writer.writerow([id, title, author, 0, 1])
                            self.inventory[int(id)] = {TITLE: title, AUTHOR: author, CHECKED_IN: 0, CHECKED_OUT: 1}
                except IOError as e:
                    print("Couldn't create a new inventory file: " + str(e))

        self.longtask((self.refresh, initialize))

    def update_progress(self, text):
        self.progress.show()
        self.progress.setLabelText(text)

    def on_search_pressed(self):
        """ Connected to signal through AutoConnect """

        search_query = self.ui.search_query.text()
        def search(log):
            log("Searching for \"%s\"" % search_query)
            return self.goodreads.search(search_query,
                self.goodreads.checkedin_shelf,
                self.goodreads.checkedout_shelf)

        def updateUI(books):
            self.populate_table(books)

        self.longtask((updateUI, search))

    def on_search_reset_pressed(self):
        """ Connected to signal through AutoConnect """

        def updateUI(books):
            self.populate_table(books)
            self.ui.search_query.setText("")

        self.longtask((updateUI, self.available))

    def longtask(self, *args):
        for slot, task in args:
            async = ASyncWorker(slot, task)
            async.progress.connect(self.update_progress)
            async.start()
            self.asyncs.append(async)

        asyncs = self.asyncs

        def on_cancel():
            for async in asyncs:
                async.terminate()

        def wait_for_death():
            for async in asyncs: async.wait()

            #Update the UI only if everything finished correctly.
            if all(async.finished for async in asyncs):
                for async in asyncs: async.commit()

            del asyncs[:]

        self.progress_thread = QtCore.QThread()
        self.progress_thread.run = wait_for_death
        self.progress_thread.started.connect(self.progress.show)
        self.progress_thread.finished.connect(self.progress.hide)
        self.progress_thread.terminated.connect(self.progress.hide)
        self.progress.canceled.connect(on_cancel)

        self.progress_thread.start()

    def wait_for_user(self):
        QtGui.QMessageBox.question(self, "Hold up!",
"""I'm opening a link to goodreads for you.
Once the goodreads page loads click "Yes" below to continue.
If this is your first time, you will have to give 'Checkout' permission to access your goodreads account.""",
            QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)

    def on_switch_user_button_pressed(self):
        self.goodreads.authenticate(self.wait_for_user)

    def on_switch_checkedout_button_pressed(self, refresh=True):
        dialog = ShelfDialog(self, "the checked out books", self.goodreads)
        if dialog.exec_():
            shelf = dialog.shelf()
            if shelf:
                self.goodreads.config['CHECKEDOUT_SHELF'] = shelf
                self.goodreads.checkedout_shelf = shelf
                if refresh:
                    self.refresh(self.checkedout_shelf, self.checkedout)

    def on_switch_checkedin_button_pressed(self, refresh=True):
        dialog = ShelfDialog(self, "the available books", self.goodreads)
        if dialog.exec_():
            shelf = dialog.shelf()
            if shelf:
                self.goodreads.config['CHECKEDIN_SHELF'] = shelf
                self.goodreads.checkedin_shelf = shelf
                if refresh:
                    self.refresh(self.available_shelf, self.available)

    def on_view_log_button_pressed(self):
        config_file = self.goodreads.config[_LOG_PATH_KEY]
        import os
        if sys.platform.startswith('win'):
            os.startfile(config_file)
        elif sys.platform.startswith("darwin"):
            os.system("open " + config_file)
        else:
            os.system("xdg-open " + config_file)

    def on_switch_log_button_pressed(self):
        file = QtGui.QFileDialog.getSaveFileName(self, filter="CSV file (*.csv)")
        self.goodreads.config[_LOG_PATH_KEY] = str(file)
        self.refresh(self.logfile)

    def persist_inventory(self):
        with open(self.goodreads.config[_INVENTORY_PATH_KEY], 'wb') as inventoryfile:
            writer = csv.writer(inventoryfile)
            data = [(id, book[TITLE], book[AUTHOR], book[CHECKED_IN], book[CHECKED_OUT]) for id, book in self.inventory.items()]
            data.sort(key = lambda (id, title, author, checked_in, checked_out): (author, title))
            for id, title, author, checked_in, checked_out in data:
                writer.writerow([id, title, author, checked_in, checked_out])

    def checkout_pressed(self, id, title):
        """ Connected to signal in populate_table """
        name, success = QtGui.QInputDialog.getText(self,
            'Checking out %s' % title, 'What is your name?')

        if success:
            self.goodreads.checkout(id)
            date = datetime.now().strftime("%m/%d/%Y %I:%M%p")

            with open(self.goodreads.config[_LOG_PATH_KEY], 'ab') as logfile:
                writer = csv.writer(logfile)
                writer.writerow([date, str(name), "checked out", title])

            if id in self.inventory:
                self.inventory[id][CHECKED_IN] -= 1
                self.inventory[id][CHECKED_OUT] += 1
                self.persist_inventory()
            else:
                print("couldn't find %d: %s" % (id, title))

            self.refresh(self.available, self.checkedout)

    def checkin_pressed(self, id, title):
        """ Connected to signal in populate_table """
        reply = QtGui.QMessageBox.question(self, "Checking in",
                'Are you checking in: %s?' % title, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)

        if reply == QtGui.QMessageBox.Yes:
            self.goodreads.checkin(id)
            date = datetime.now().strftime("%m/%d/%Y %I:%M%p")
            with open(self.goodreads.config[_LOG_PATH_KEY], 'ab') as logfile:
                writer = csv.writer(logfile)
                writer.writerow([date, "", "checked in", title])

            if id in self.inventory:
                self.inventory[id][CHECKED_IN] += 1
                self.inventory[id][CHECKED_OUT] -= 1
                self.persist_inventory()
            else:
                print("Couldn't find ID: %d, title: %s" % (id, title))

            self.refresh(self.available, self.checkedout)

    def available(self, log):
        log("Reloading the available books")
        books = self.goodreads.listbooks(self.goodreads.checkedin_shelf)
        books += self.goodreads.listbooks(self.goodreads.checkedout_shelf)
        books.sort(key=BOOKSORT)
        for (id, title, author) in books:
            if id not in self.inventory:
                self.inventory[int(id)]= {TITLE: title, AUTHOR: author, CHECKED_IN: 1, CHECKED_OUT: 0}
        self.persist_inventory()
        return books

    def current_user(self, log):
        log("Reloading the current user")
        return USER_LABEL_TEXT % self.goodreads.user()[1]

    def checkedout_shelf(self, log):
        log("Reloading the checked out shelf")
        return CHECKEDOUT_SHELF_LABEL_TEXT % self.goodreads.checkedout_shelf

    def available_shelf(self, log):
        log("Reloading the available shelf")
        return CHECKEDIN_SHELF_LABEL_TEXT % self.goodreads.checkedin_shelf

    def log_file(self, log):
        log("Reloading the log file")
        return LOG_LABEL_TEXT % self.goodreads.config[_LOG_PATH_KEY]

    def refresh(self, *refresh):

        all_tasks = [(self.populate_table, self.available),
            (self.ui.user_label.setText, self.current_user),
            (self.ui.checkedout_shelf_label.setText, self.checkedout_shelf),
            (self.ui.log_label.setText, self.log_file),
            (self.ui.checkedin_shelf_label.setText, self.available_shelf)]

        slots, tasks = zip(*all_tasks) #unzip in python

        if not refresh or refresh == (None,):
            tasks = all_tasks
        else:
            not_allowed = filter(lambda t: t not in tasks, refresh)
            if not_allowed:
                raise ValueError("'%s' are not an available for refresh" % not_allowed)
            else:
                tasks = [all_tasks[tasks.index(task)] for task in refresh]

        self.longtask(*tasks)

    def populate_table(self, books):
        table = self.ui.books
        table.clearContents()
        table.setRowCount(0)
        for (index, (id, title, author)) in enumerate(books):
            table.insertRow(index)
            titlewidget = QtGui.QTableWidgetItem(title)
            titlewidget.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            authorwidget = QtGui.QTableWidgetItem(author)
            authorwidget.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            table.setItem(index, 0, titlewidget)
            table.setItem(index, 1, authorwidget)

            if self.inventory[id][CHECKED_IN] > 0:
                checkout_button = QtGui.QPushButton("Check this book out!")
                checkout_button.clicked.connect(lambda c, a = id, b = title: self.checkout_pressed(a,b))
            else:
                checkout_button = QtGui.QPushButton("Return this book")
                checkout_button.clicked.connect(lambda c, a = id, b = title: self.checkin_pressed(a,b))
            table.setCellWidget(index, 2, checkout_button)

        horizontal_header = table.horizontalHeader()
        horizontal_header.setResizeMode(0, QtGui.QHeaderView.Stretch)
        horizontal_header.setResizeMode(1, QtGui.QHeaderView.ResizeToContents)
        horizontal_header.setResizeMode(2, QtGui.QHeaderView.ResizeToContents)
        horizontal_header.setStretchLastSection(False)

class ShelfDialog(QtGui.QDialog, BaseShelfDialog):
    def __init__(self, parent, use, goodreads):
        QtGui.QDialog.__init__(self, parent)
        self.setupUi(self)
        self.label.setText(str(self.label.text()) % use)
        QtCore.QObject.connect(
            self.new_shelf_button,
            QtCore.SIGNAL("clicked()"),
            self.create_new_shelf)
        self.goodreads = goodreads
        self.refresh()

    def create_new_shelf(self):
        name, success = QtGui.QInputDialog.getText(self,
            'Adding a new shelf',
            'What would you like to name the new shelf?')

        if success:
            self.goodreads.add_shelf(str(name))
            self.refresh()

    def refresh(self):
        self.list.clear()
        self.list.insertItems(0, self.goodreads.shelves())

    def shelf(self):
        return str(self.list.currentItem().text())

class ASyncWorker(QtCore.QThread):
    signal = QtCore.pyqtSignal(object)
    progress = QtCore.pyqtSignal(str)

    def __init__(self, slot, task, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.task = task
        self.main = main
        self.signal.connect(slot)
        self.finished = False
        self.result = None

    def log(self, message):
        self.progress.emit(message)

    def run(self):
        self.result = self.task(self.log)
        self.finished = True

    def commit(self):
        if self.finished:
            self.signal.emit(self.result)

def main():
    app = QtGui.QApplication(sys.argv)
    window = Main()
    window.show()
    window.startup()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
