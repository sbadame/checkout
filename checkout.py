import csv
import sys
import os.path as path

from collections import namedtuple
from config import Config
from customgui import NoVisibleFocusItemDelegate
from goodreads import GoodReads
from checkoutgui import Ui_MainWindow
from datetime import datetime
from PySide import QtGui, QtCore
from shelfdialog import Ui_Dialog as BaseShelfDialog

# How we represent books stored in the inventory csv
InventoryRecord = namedtuple('InventoryRecord',
    ['title', 'author', 'checked_in', 'checked_out'])

# Default file paths for configuration
CONFIG_FILE_PATH = path.normpath(path.expanduser("~/checkout.credentials"))
DEFAULT_INVENTORY_FILE_PATH = path.normpath(path.expanduser("~/inventory.csv"))
DEFAULT_LOG_PATH = path.normpath(path.expanduser("~/checkout.csv"))

# Keys for the configuration hash
LIBRARY_SHELF = "LIBRARY_SHELF" # The name of the shelf where books are stored
_LOG_PATH_KEY = 'LOG_PATH'
_INVENTORY_PATH_KEY = 'INVENTORY_PATH'

# UI Constants
USER_LABEL_TEXT = 'Currently logged in as %s.'
CHECKEDOUT_SHELF_LABEL_TEXT = 'Your "%s" shelf is being used to store the books that are checked out.'
CHECKEDIN_SHELF_LABEL_TEXT = 'Your "%s" shelf is being used to store the books that are available.'
LOG_LABEL_TEXT = 'The log is recorded at "%s".'

# Colors
CHECKOUT_COLOR = "#FF7373"
CHECKOUT_COLOR_SELECTED = "#BF3030"

AVAILABLE_COLOR = "#67E667"
AVAILABLE_COLOR_SELECTED = "#269926"

# How books in the UI are sorted
BOOKSORT = lambda (id, title, author): (list(reversed(author.split())), title)

DEVELOPER_KEY = "DEVELOPER_KEY"
DEVELOPER_SECRET = "DEVELOPER_SECRET"

""" To regenerate the gui from the design: pyside-uic checkout.ui -o checkoutgui.py"""
class Main(QtGui.QMainWindow):

    @QtCore.Slot(object)
    def set_config(self, config):
        self.config = config
        self.shelf = self.config[LIBRARY_SHELF]
        self.goodreads = GoodReads(config[DEVELOPER_KEY], config[DEVELOPER_SECRET], waitfunction=self.wait_for_user)
        self.load_inventory()
        self.refresh()

    def load_dev_key(self):
        key, success = QtGui.QInputDialog.getText(None, "Developer Key?",
                'A developer key is needed to communicate with goodreads.\nYou can usually find it here: http://www.goodreads.com/api/keys')
        if not success: exit()
        return str(key)

    def load_dev_secret(self):
        secret, success = QtGui.QInputDialog.getText(None, "Developer Secret?",
                'What is the developer secret for the key that you just gave?\n(It\'s also on that page with the key: http://www.goodreads.com/api/keys)')
        if not success: exit()
        return str(secret)

    def load_inventory(self):
        try:
            with open(self.config[_INVENTORY_PATH_KEY], 'rb') as inventoryfile:
                for (id, title, author, num_in, num_out) in csv.reader(inventoryfile):
                    self.inventory[int(id)] = InventoryRecord(title, author, int(num_in), int(num_out))
        except IOError as e:
            try:
                print("Creating a new inventory file")
                with open(self.config[_INVENTORY_PATH_KEY], 'wb') as inventoryfile:
                    print("Creating a new inventory file")
                    writer = csv.writer(inventoryfile)
                    for id, title, author in self.listbooks(self.shelf):
                        writer.writerow([id, title, author, 1, 0])
                        self.inventory[int(id)] = InventoryRecord(title, author, 1, 0)
            except IOError as e:
                print("Couldn't create a new inventory file: " + str(e))

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
        self.ui.books.setItemDelegate(NoVisibleFocusItemDelegate())
        self.ui.books.setFocus()

        self.ui.search_query.setDefaultText()
        self.ui.search.clicked.connect(self.on_search_clicked)
        self.ui.search_reset.pressed.connect(self.on_search_reset_clicked)
        self.ui.options.clicked.connect(lambda : self.ui.uistack.setCurrentWidget(self.ui.optionspage))
        self.ui.back_to_books.clicked.connect(lambda : self.ui.uistack.setCurrentWidget(self.ui.bookpage))


        def load_config(log):
            log("Loading: " + CONFIG_FILE_PATH)
            try:
                with open(CONFIG_FILE_PATH, "r") as configfile:
                    # How to populate the configuration if it isn't set yet...
                    # Note that these are function calls and order maters!
                    config = Config.load_from_file(configfile)
            except IOError as e:
                    print("Error loading: %s (%s). (This is normal for a first run)" % (CONFIG_FILE_PATH, e))
                    config = Config(CONFIG_FILE_PATH)

            default_configuration = [
                (_LOG_PATH_KEY, lambda: DEFAULT_LOG_PATH),
                (_INVENTORY_PATH_KEY, lambda: DEFAULT_INVENTORY_FILE_PATH),
                (DEVELOPER_KEY, self.load_dev_key),
                (DEVELOPER_SECRET, self.load_dev_secret),
                (LIBRARY_SHELF, lambda: self.on_switch_library_button_pressed(refresh=False)),
            ]

            for key, loader in default_configuration:
                if key not in config:
                    config[key] = loader()

            return config

        self.longtask((self.set_config, load_config))

    def developer_key(self):
        return QtGui.QInputDialog.getText(None, "Developer Key?",
                'A developer key is needed to communicate with goodreads.\nYou can usually find it here: http://www.goodreads.com/api/keys')

    def update_progress(self, text):
        self.progress.show()
        self.progress.setLabelText(text)

    def on_search_clicked(self):
        """ Connected to signal through AutoConnect """
        search_query = self.ui.search_query.text()
        if search_query == self.ui.search_query.default_text():
            search_query = ""

        def search(log):
            log("Searching for: \"%s\"" % search_query)
            return self.goodreads.search(search_query, self.shelf)

        self.longtask((self.populate_table, search))

    def on_search_reset_clicked(self):
        def updateUI(books):
            self.ui.search_query.setText("")
            self.populate_table(books)

        self.longtask((updateUI, self.load_available))

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
        print("Look at switch user again")

    def on_switch_library_button_pressed(self, refresh=True):
        dialog = ShelfDialog(self, "the library books", self.goodreads)
        if dialog.exec_():
            shelf = dialog.shelf()
            if shelf:
                self.shelf = shelf
                self.config[LIBRARY_SHELF] = shelf
                if refresh:
                    #TODO: fix this in the options, add the library shelf option
                    pass

    def on_view_log_button_pressed(self):
        config_file = self.config[_LOG_PATH_KEY]
        import os
        if sys.platform.startswith('win'):
            os.startfile(config_file)
        elif sys.platform.startswith("darwin"):
            os.system("open " + config_file)
        else:
            os.system("xdg-open " + config_file)

    def on_switch_log_button_pressed(self):
        file = QtGui.QFileDialog.getSaveFileName(self, filter="CSV file (*.csv)")
        self.config[_LOG_PATH_KEY] = str(file)
        self.refresh(self.logfile)

    def persist_inventory(self):
        with open(self.config[_INVENTORY_PATH_KEY], 'wb') as inventoryfile:
            writer = csv.writer(inventoryfile)
            data = self.inventory.items()
            data.sort(key = lambda (id, record): (record.author, record.title))
            for id, record in data:
                writer.writerow([id, record.title, record.author, record.checked_in, record.checked_out])

    def checkout_pressed(self, id, title):
        """ Connected to signal in populate_table """
        name, success = QtGui.QInputDialog.getText(self,
            'Checking out %s' % title, 'What is your name?')

        if success:
            date = datetime.now().strftime("%m/%d/%Y %I:%M%p")

            with open(self.config[_LOG_PATH_KEY], 'ab') as logfile:
                writer = csv.writer(logfile)
                writer.writerow([date, str(name), "checked out", title])

            if id in self.inventory:
                old = self.inventory[id]
                self.inventory[id] = old._replace(
                    checked_in = old.checked_in - 1,
                    checked_out = old.checked_out + 1)
                self.persist_inventory()
            else:
                print("couldn't find %d: %s" % (id, title))

            self.refresh(self.load_available)

    def checkin_pressed(self, id, title):
        """ Connected to signal in populate_table """
        reply = QtGui.QMessageBox.question(self, "Checking in",
                'Are you checking in: %s?' % title, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)

        if reply == QtGui.QMessageBox.Yes:
            date = datetime.now().strftime("%m/%d/%Y %I:%M%p")
            with open(self.config[_LOG_PATH_KEY], 'ab') as logfile:
                writer = csv.writer(logfile)
                writer.writerow([date, "", "checked in", title])

            if id in self.inventory:
                old = self.inventory[id]
                self.inventory[id] = old._replace(
                    checked_in = old.checked_in + 1,
                    checked_out = old.checked_out - 1)
                self.persist_inventory()
            else:
                print("Couldn't find ID: %d, title: %s" % (id, title))

            self.refresh(self.load_available)

    def load_available(self, log):
        log("Reloading your books...")
        books = self.goodreads.listbooks(self.shelf)
        books.sort(key=BOOKSORT)
        for (id, title, author) in books:
            if id not in self.inventory:
                self.inventory[int(id)]= InventoryRecord(title, author, 1, 0)
        self.persist_inventory()
        return books

    def current_user(self, log):
        log("Reloading the current user")
        return USER_LABEL_TEXT % self.goodreads.user()[1]

    def log_file(self, log):
        log("Reloading the log file")
        return LOG_LABEL_TEXT % self.config[_LOG_PATH_KEY]

    def refresh(self, *refresh):
        all_tasks = [(self.populate_table, self.load_available),
            (self.ui.user_label.setText, self.current_user),
            (self.ui.log_label.setText, self.log_file)]

        slots, tasks = zip(*all_tasks) #unzip in python

        if not refresh or refresh == ('',) or refresh == (None,):
            tasks = all_tasks
        else:
            not_allowed = filter(lambda t: t not in tasks, refresh)
            if not_allowed:
                raise ValueError("'%s' are not available for refresh" % not_allowed)
            else:
                tasks = [all_tasks[tasks.index(task)] for task in refresh]

        self.longtask(*tasks)

    def on_books_currentCellChanged(self, prow, pcolumn, row, column):
        if self.books:
            id, title, author = self.books[prow]
            style = AVAILABLE_COLOR_SELECTED if self.available(id) else CHECKOUT_COLOR_SELECTED
            self.ui.books.setStyleSheet('selection-background-color: "%s"' % style)

    def available(self, book_id):
        return self.inventory[book_id].checked_in > 0

    def populate_table(self, books):
        self.books = books
        table = self.ui.books
        table.clearContents()
        table.setRowCount(0)
        for (index, (id, title, author)) in enumerate(books):
            table.insertRow(index)

            titlewidget = QtGui.QTableWidgetItem(title)
            titlewidget.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            table.setItem(index, 0, titlewidget)

            authorwidget = QtGui.QTableWidgetItem(author)
            authorwidget.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
            table.setItem(index, 1, authorwidget)

            button_widget = QtGui.QWidget()
            layout = QtGui.QVBoxLayout()
            button_widget.setLayout(layout)
            if self.available(id) > 0:
                checkout_button = QtGui.QPushButton("Check this book out!")
                checkout_button.clicked.connect(lambda a = id, b = title: self.checkout_pressed(a,b))
            else:
                checkout_button = QtGui.QPushButton("Return this book")
                checkout_button.clicked.connect(lambda a = id, b = title: self.checkin_pressed(a,b))
                checkout_button.setStyleSheet('background-color: "%s"' % CHECKOUT_COLOR )
                button_widget.setStyleSheet('margin:0px; background-color: "%s"' % CHECKOUT_COLOR )
                titlewidget.setBackground(QtGui.QBrush(QtGui.QColor(CHECKOUT_COLOR)))
                authorwidget.setBackground(QtGui.QBrush(QtGui.QColor(CHECKOUT_COLOR)))

            layout.addWidget(checkout_button)
            table.setCellWidget(index, 2, button_widget)

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
    signal = QtCore.Signal(object)
    progress = QtCore.Signal(str)

    def __init__(self, slot, task, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.task = task
        self.main = main
        self.signal.connect(slot)
        self.finished = False
        self.result = None

    def log(self, message):
        self.progress.emit(message)
        print("[LOG] " + message)

    def run(self):
        self.result = self.task(self.log)
        self.finished = True

    def commit(self):
        if self.finished:
            if not self.result:
                self.result = ""
            self.signal.emit(self.result)

def main():
    app = QtGui.QApplication(sys.argv)
    window = Main()
    window.show()
    window.startup()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
