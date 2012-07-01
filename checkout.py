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

""" To regenerate the gui from the design: pyuic4 checkout.ui -o checkoutgui.py"""
class Main(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)

        self.progress = QtGui.QProgressDialog(None)
        self.progress.setRange(0,0)
        self.progress.setWindowTitle("Working...")

    def startup(self):
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.configthread = Worker(self)
        self.configthread.progress_signal.connect(self.update_progress)
        self.configthread.finished.connect(self.progress.hide)
        self.configthread.finished.connect(self.refresh)

        self.progress.show()
        self.configthread.start()

    def update_progress(self, text):
        self.progress.show()
        self.progress.setLabelText(text)

    def on_checkout_search_pressed(self):
        """ Connected to signal through AutoConnect """
        search_query = self.ui.checkout_query.text()

        long_task = lambda: self.goodreads.search(search_query, self.goodreads.checkedin_shelf)
        self.checkout_searcher = BookPasser(long_task)
        self.checkout_searcher.books_arrived.connect(self.refresh_checkedin)
        self.checkout_searcher.finished.connect(self.progress.hide)
        self.checkout_searcher.start()

    def on_checkin_search_pressed(self):
        """ Connected to signal through AutoConnect """
        search_query = self.ui.checkin_query.text()

        long_task = lambda: self.goodreads.search(search_query, self.goodreads.checkedout_shelf)
        self.checkin_searcher = BookPasser(long_task)
        self.checkin_searcher.books_arrived.connect(self.refresh_checkedout)
        self.checkin_searcher.finished.connect(self.progress.hide)
        self.checkin_searcher.start()

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
                    self.refresh([RefreshWorker.checkedout_shelf, RefreshWorker.checkedout])

    def on_switch_checkedin_button_pressed(self, refresh=True):
        dialog = ShelfDialog(self, "the available books", self.goodreads)
        if dialog.exec_():
            shelf = dialog.shelf()
            if shelf:
                self.goodreads.config['CHECKEDIN_SHELF'] = shelf
                self.goodreads.checkedin_shelf = shelf
                if refresh:
                    self.refresh([RefreshWorker.available_shelf, RefreshWorker.available])

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
        self.refresh([RefreshWorker.logfile])


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
            self.refresh([RefreshWorker.available, RefreshWorker.checkedout])

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
            self.refresh([RefreshWorker.available, RefreshWorker.checkedout])

    def refresh(self, refresh=None):
        self.progress.show()
        if not refresh:
            refresh = RefreshWorker.ALL
        self.refresher = RefreshWorker(self, refresh)
        self.progress.canceled.connect(self.refresher.cancel)
        self.refresher.progress_signal.connect(self.update_progress)
        self.refresher.finished.connect(self.progress.hide)

        self.refresher.checkedin_books_arrived.connect(self.refresh_checkedin)
        self.refresher.checkedout_books_arrived.connect(self.refresh_checkedout)
        self.refresher.newUserSignal.connect(self.ui.user_label.setText)
        self.refresher.checkedout_shelf_arrived.connect(self.ui.checkedout_shelf_label.setText)
        self.refresher.checkedin_shelf_arrived.connect(self.ui.checkedin_shelf_label.setText)
        self.refresher.log_file_arrived.connect(self.ui.log_label.setText)
        self.refresher.newUserSignal.connect(self.ui.user_label.setText)

        self.refresher.start()

    def refresh_checkedin(self, books):
        self.populate_table(books, self.ui.checkedin_books, "Check this book out!", self.checkout_pressed)

    def refresh_checkedout(self, books):
        self.populate_table(books, self.ui.checkedout_books, "Return this book", self.checkin_pressed)

    def populate_table(self, books, table, buttontext, onclick):
        table.clearContents()
        table.setRowCount(0)
        for (index, (id, title, author)) in enumerate(books):
            table.insertRow(index)
            table.setItem(index, 0, QtGui.QTableWidgetItem(title))
            table.setItem(index, 1, QtGui.QTableWidgetItem(author))
            checkout_button = QtGui.QPushButton(buttontext)
            checkout_button.clicked.connect(lambda c, a = id, b = title: onclick(a,b))
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
        self.refresh([RefreshWorker.available_shelf, RefreshWorker.checkedout_shelf])

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

class Worker(QtCore.QThread):

    progress_signal = QtCore.pyqtSignal(str)

    def __init__(self, main, parent = None):
        QtCore.QThread.__init__(self, parent)
        self.main = main

    def progress(self, description):
        self.progress_signal.emit(description)

    def run(self):
        self.progress("Loading local config file")
        try:
            with open(CONFIG_FILE_PATH, "r") as configfile:
                config = Config.load_from_file(configfile)
        except IOError as e:
                print("Error loading: %s (%s). (This is normal for a first run)" % (CONFIG_FILE_PATH, e))
                config = Config(CONFIG_FILE_PATH)

        if "DEVELOPER_KEY" not in config or "DEVELOPER_SECRET" not in config:
            key, success = QtGui.QInputDialog.getText(None, "Developer Key?",
                    'A developer key is needed to communicate with goodreads.\nYou can usually find it here: http://www.goodreads.com/api/keys')
            if not success: exit()

            config["DEVELOPER_KEY"] = str(key)

            secret, success = QtGui.QInputDialog.getText(None, "Developer Secret?",
                    'What is the developer secret for the key that you just gave?\n(It\'s also on that page with the key: http://www.goodreads.com/api/keys)')
            if not success: exit()
            config["DEVELOPER_SECRET"] = str(secret)

        self.main.goodreads = GoodReads(config, waitfunction=self.main.wait_for_user, log=self.progress)

        if "CHECKEDOUT_SHELF" not in config:
            self.main.on_switch_checkedout_button_pressed(refresh=False)

        if "CHECKEDIN_SHELF" not in config:
            self.main.on_switch_checkedin_button_pressed(refresh=False)

        if _LOG_PATH_KEY not in self.main.goodreads.config:
            self.main.goodreads.config[_LOG_PATH_KEY] = path.normpath(path.expanduser("~/checkout.csv"))

class BookPasser(QtCore.QThread):
    books_arrived = QtCore.pyqtSignal(object)

    def __init__(self, longtask, parent = None):
        QtCore.QThread.__init__(self, parent)
        self.longtask = longtask

    def run(self):
        self.books_arrived.emit(self.longtask())

class RefreshWorker(QtCore.QThread):
    progress_signal = QtCore.pyqtSignal(str)
    checkedout_shelf_arrived = QtCore.pyqtSignal(str)
    checkedin_shelf_arrived = QtCore.pyqtSignal(str)
    log_file_arrived = QtCore.pyqtSignal(str)
    newUserSignal = QtCore.pyqtSignal(QtCore.QString)
    checkedin_books_arrived = QtCore.pyqtSignal(list)
    checkedout_books_arrived = QtCore.pyqtSignal(list)

    def __init__(self, main, refresh=None, parent = None):
        QtCore.QThread.__init__(self, parent)
        self.canceled = False
        self.main = main
        if refresh:
            self.refresh = refresh
        else:
            self.refresh = RefreshWorker.ALL

    def progress(self, description):
        self.progress_signal.emit(description)

    def cancel(self):
        self.canceled = True

    def available(self):
        self.progress("Reloading the available books")
        checkedin_books = self.main.goodreads.listbooks(self.main.goodreads.checkedin_shelf)
        return (self.checkedin_books_arrived, checkedin_books)

    def checkedout(self):
        self.progress("Reloading the checked out books")
        checkedout_books = self.main.goodreads.listbooks(self.main.goodreads.checkedout_shelf)
        return (self.checkedout_books_arrived, checkedout_books)

    def current_user(self):
        self.progress("Reloading the current user")
        return (self.newUserSignal, USER_LABEL_TEXT % self.main.goodreads.user()[1])

    def checkedout_shelf(self):
        self.progress("Reloading the checked out shelf")
        return (self.checkedout_shelf_arrived, CHECKEDOUT_SHELF_LABEL_TEXT % self.main.goodreads.checkedout_shelf)

    def available_shelf(self):
        self.progress("Reloading the available shelf")
        return (self.checkedin_shelf_arrived, CHECKEDIN_SHELF_LABEL_TEXT % self.main.goodreads.checkedin_shelf)

    def log_file(self):
        self.progress("Reloading the log file")
        return (self.log_file_arrived, LOG_LABEL_TEXT % self.main.goodreads.config[_LOG_PATH_KEY])

    ALL = [available, checkedout, current_user, checkedout_shelf, available_shelf, log_file]

    def run(self):
        results = []
        for r in self.refresh:
            if self.canceled:
                return
            results.append(r(self))

        for (signal, value) in results:
            signal.emit(value)

def main():
    app = QtGui.QApplication(sys.argv)
    window = Main()
    window.show()
    window.startup()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
