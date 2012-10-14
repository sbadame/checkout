from __future__ import print_function
from PyQt4 import QtGui, QtCore
import inventory
import sys
import os.path as path
import logging

from config import Config
from dialogs import ListDialog
from goodreads import GoodReads
from inventory import InventoryRecord
from datetime import datetime
from tasks import longtask, cancel_longtask
from mainui import MainUi
import unicodecsv as csv

logger = logging.getLogger()

sh = logging.StreamHandler()
sh.setLevel(logging.DEBUG)
logger.addHandler(sh)

fh = logging.FileHandler(path.expanduser("~/checkout.programlog"))
fh.setLevel(logging.DEBUG)
fh.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s'))
logger.addHandler(fh)
logger.setLevel(logging.DEBUG)

# Default file paths for configuration
CONFIG_FILE_PATH = path.normpath(path.expanduser("~/checkout.credentials"))
DEFAULT_INVENTORY_FILE_PATH = path.normpath(path.expanduser("~/inventory.csv"))
DEFAULT_LOG_PATH = path.normpath(path.expanduser("~/checkout.csv"))

# Keys for the configuration hash
LIBRARY_SHELF = "LIBRARY_SHELF" # The name of the shelf where books are stored
_LOG_PATH_KEY = 'LOG_PATH'
_INVENTORY_PATH_KEY = 'INVENTORY_PATH'

# UI Constants
USER_LABEL_TEXT = None
LIBRARY_SHELF_LABEL_TEXT = None
LOG_LABEL_TEXT = None
INVENTORY_LABEL_TEXT = None
SHELF_DIALOG_LABEL_TEXT = "Which shelf should be used for the library books?"

# Colors
CHECKOUT_COLOR_SELECTED = "#BF3030"

AVAILABLE_COLOR = "#0000FF"
AVAILABLE_COLOR_SELECTED = "#0000FF"

# How books in the UI are sorted
BOOKSORT = lambda (id, book): (list(reversed(book.author.split())), book.title)

DEVELOPER_KEY = "DEVELOPER_KEY"
DEVELOPER_SECRET = "DEVELOPER_SECRET"

def openfile(filepath):
    import os
    if sys.platform.startswith('win'):
        os.startfile(filepath)
    elif sys.platform.startswith("darwin"):
        os.system("open " + filepath)
    else:
        os.system("xdg-open " + filepath)

""" To regenerate the gui from the design: pyside-uic checkout.ui -o checkoutgui.py"""
class Main(QtGui.QMainWindow):

    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.progress = QtGui.QProgressDialog(self)
        self.progress.setRange(0,0)
        self.progress.setWindowTitle("Working...")
        self.progress.canceled.connect(cancel_longtask)
        self.books_in_table = []

    def startup(self):
        logger.info("Starting up!")
        self.ui = MainUi()
        self.ui.setupUi(self)

        self.ui.options.clicked.connect(lambda : self.ui.uistack.setCurrentWidget(self.ui.optionspage))
        self.ui.back_to_books.clicked.connect(lambda : self.ui.uistack.setCurrentWidget(self.ui.bookpage))

        self.all_tasks = [
            (self.populate_table, self.local_inventory),
            (self.ui.user_label.setText, self.current_user),
            (self.ui.log_label.setText, self.log_file),
            (self.ui.library_shelf_label.setText, self.library_shelf),
            (self.ui.inventory_label.setText, self.inventory_file)]

        self.task_args = {
            "on_progress": self.update_progress,
            "on_start" : self.progress.show,
            "on_finish" : self.progress.hide,
            "on_terminate" : self.progress.hide}

        self.config = self.init_config()
        self.goodreads = GoodReads(self.config[DEVELOPER_KEY], self.config[DEVELOPER_SECRET], waitfunction=self.wait_for_user)
        if LIBRARY_SHELF not in self.config:
            self.on_switch_library_button_pressed(refresh=False)

        self.inventory_path = self.config[_INVENTORY_PATH_KEY]

        try:
            self.inventory = inventory.load_inventory(self.inventory_path)
        except IOError as e:
            self.inventory = inventory.create_inventory(self.inventory_path)

        longtask(self.all_tasks + [(self.populate_table, self.update_from_goodreads)], **self.task_args)

    def populate_table(self, books):
        self.ui.populate_table(books, self.checkin_pressed, self.checkout_pressed)

    def init_config(self):
        try:
            with open(CONFIG_FILE_PATH, "r") as configfile:
                logger.info("Loading: " + CONFIG_FILE_PATH)
                # How to populate the configuration if it isn't set yet...
                # Note that these are function calls and order maters!
                config = Config.load_from_file(configfile)
        except IOError as e:
                logger.warn("Error loading: %s (%s). (This is normal for a first run)" % (CONFIG_FILE_PATH, e))
                config = Config(CONFIG_FILE_PATH)

        default_configuration = [
            (_LOG_PATH_KEY, lambda: DEFAULT_LOG_PATH),
            (_INVENTORY_PATH_KEY, lambda: DEFAULT_INVENTORY_FILE_PATH),
            (DEVELOPER_KEY, self.request_dev_key),
            (DEVELOPER_SECRET, self.request_dev_secret),
        ]

        for key, loader in default_configuration:
            if key not in config:
                logger.info("Missing a value for your %s property, lets get one!" % key)
                config[key] = loader()

        return config

    def update_progress(self, text):
        self.progress.show()
        self.progress.setLabelText(text)

    def shelf(self):
        return self.config[LIBRARY_SHELF]

    def request_dev_key(self, log=logger.info):
        key, success = QtGui.QInputDialog.getText(None, "Developer Key?",
                'A developer key is needed to communicate with goodreads.\nYou can usually find it here: http://www.goodreads.com/api/keys')
        if not success: exit()
        return str(key)

    def request_dev_secret(self):
        secret, success = QtGui.QInputDialog.getText(None, "Developer Secret?",
                'What is the developer secret for the key that you just gave?\n(It\'s also on that page with the key: http://www.goodreads.com/api/keys)')
        if not success: exit()
        return str(secret)

    def on_search_query_textEdited(self, text):
        query = str(text).strip()
        if query:
            def search(log):
                log("Searching for: " + query)
                return self.inventory.search(query)
            longtask([(self.populate_table, search)], **self.task_args)
        else:
            longtask([(self.populate_table, lambda x: self.inventory.items())],
                     **self.task_args)

    def on_search_pressed(self):
        """ Connected to signal through AutoConnect """
        search_query = self.ui.search_query.text()
        if search_query == self.ui.search_query.default_text():
            search_query = ""

        def search(log):
            log("Searching for: \"%s\"" % search_query)
            return self.goodreads.search(search_query, self.shelf())

        def on_search_complete(*data):
            self.ui.search_reset.show()
            self.populate_table(*data)

        logger.info("Firing search for: " + search_query)
        longtask([(on_search_complete, search)], **self.task_args)

    def on_search_reset_pressed(self):
        def updateUI(books):
            self.ui.search_query.setText("")
            self.populate_table(books)

        longtask([(updateUI, self.local_inventory)], **self.task_args)

    def wait_for_user(self):
        QtGui.QMessageBox.question(self, "Hold up!",
"""I'm opening a link to goodreads for you.
Once the goodreads page loads click "Yes" below to continue.
If this is your first time, you will have to give 'Checkout' permission to access your goodreads account.""",
            QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)

    def on_switch_user_button_pressed(self):
        logger.warn("Look at switch user again")

    def on_switch_library_button_pressed(self, refresh=True):
        dialog = ListDialog(self, SHELF_DIALOG_LABEL_TEXT, self.goodreads.shelves())

        def create_new_shelf():
            name, success = QtGui.QInputDialog.getText(dialog,
                'Adding a new shelf',
                'What would you like to name the new shelf?')

            if success:
                self.goodreads.add_shelf(str(name))
                dialog.setItems(self.goodreads.shelves())

        dialog.button.pressed.connect(create_new_shelf)
        dialog.button.setText("Create a new shelf")

        if dialog.exec_():
            shelf = dialog.result()
            if shelf:
                self.config[LIBRARY_SHELF] = shelf
                refresh_list = [self.library_shelf]
                if refresh:
                    refresh_list.append(self.local_inventory)
                self.refresh(*refresh_list)

    def on_view_log_button_pressed(self):
        openfile(self.config[_LOG_PATH_KEY])

    def on_view_inventory_button_pressed(self):
        openfile(self.config[_INVENTORY_PATH_KEY])

    def on_switch_log_button_pressed(self):
        file = QtGui.QFileDialog.getSaveFileName(
                self, filter="CSV file (*.csv)")
        if file:
            self.config[_LOG_PATH_KEY] = str(file)
            self.refresh(self.log_file)

    def on_switch_inventory_button_pressed(self):
        file = QtGui.QFileDialog.getSaveFileName(
                self, filter="CSV file (*.csv)")
        if file:
            self.config[_INVENTORY_PATH_KEY] = str(file)
            self.refresh(self.inventory_file)
            self.inventory.persist()

    def checkout_pressed(self, id, title):
        """ Connected to signal in populate_table """

        name, success = QtGui.QInputDialog.getText(self,
            'Checking out %s' % title, 'What is your name?')
        if success:
            date = datetime.now().strftime("%m/%d/%Y %I:%M%p")

            with open(self.config[_LOG_PATH_KEY], 'ab') as logfile:
                writer = csv.writer(logfile)
                writer.writerow([date, str(name), "checked out", id, title])

            if id in self.inventory:
                self.inventory.checkout(id)
                self.inventory.persist()
            else:
                logger.critical("couldn't find %d: %s" % (id, title))

            self.refresh(self.local_inventory)

    def candidates_for_return(self, bookid):
        possible_people = []
        with open(self.config[_LOG_PATH_KEY], 'rb') as logfile:
            for row in csv.reader(logfile):
                try:
                    if int(row[3]) == bookid:
                        name = row[1].strip()
                        if name not in possible_people:
                            possible_people.append(name)
                except ValueError as ve:
                    # it's ok if there is a malformed cell/row
                    logger.warn("Malformed row: " + str(row))
                    pass
        return possible_people

    def checkin_pressed(self, id, title):
        """ Connected to signal in populate_table """
        candidates_for_return = self.candidates_for_return(id)

        dialog = ListDialog(self, "Who are you?", candidates_for_return)

        def not_on_list():
            name, success = QtGui.QInputDialog.getText(self,
                'Return %s' % title, 'What is your name?')

            name = str(name).strip()
            if success and name:
                dialog.forced_result = name
                dialog.accept()

        dialog.button.setText("I'm not on the list!")
        dialog.button.pressed.connect(not_on_list)

        if dialog.exec_():
            name = dialog.result()
            if name:
                date = datetime.now().strftime("%m/%d/%Y %I:%M%p")
                with open(self.config[_LOG_PATH_KEY], 'ab') as logfile:
                    writer = csv.writer(logfile)
                    writer.writerow([date, name, "checked in", id, title])

                if id in self.inventory:
                    self.inventory.checkin(id)
                    self.inventory.persist()
                else:
                    logger.critical("Couldn't find ID: %d, title: %s" % (id, title))

                self.refresh(self.local_inventory)

    def local_inventory(self, log):
        log("Grabbing the local copy of your books.")
        books = self.inventory.items()
        books.sort(key=BOOKSORT)
        return books

    def update_from_goodreads(self, log):
        log("Reloading your books from goodreads...")
        books = []
        for (id, t, a) in self.goodreads.listbooks(self.shelf()):
            book = InventoryRecord(t, a, 1, 0, [])
            books.append((id, book))
            if id not in self.inventory:
                self.inventory[int(id)] = book
        books.sort(key=BOOKSORT)
        self.inventory.persist()
        return books

    # Update the user interface
    def current_user(self, log):
        global USER_LABEL_TEXT
        """ Returns the string used in the Options GUI for user name """
        log("Finding out who your are")
        if not USER_LABEL_TEXT:
            USER_LABEL_TEXT = str(self.ui.user_label.text())
        return USER_LABEL_TEXT % self.goodreads.user()[1]

    def log_file(self, log):
        global LOG_LABEL_TEXT
        """ Returns the string used in the Options GUI for the log file """
        log("Finding that log file")
        if not LOG_LABEL_TEXT:
            LOG_LABEL_TEXT = str(self.ui.log_label.text())
        return LOG_LABEL_TEXT % self.config[_LOG_PATH_KEY]

    def inventory_file(self, log):
        global INVENTORY_LABEL_TEXT
        """ Returns the string used in the Options GUI for the inventory file """
        log("Figuring out where I keep track of your books")
        if not INVENTORY_LABEL_TEXT:
            INVENTORY_LABEL_TEXT = str(self.ui.inventory_label.text())
        return INVENTORY_LABEL_TEXT % self.config[_INVENTORY_PATH_KEY]

    def library_shelf(self, log):
        global LIBRARY_SHELF_LABEL_TEXT
        """ Returns the string used in the Options GUI for the shelf """
        log("Figuring out where you keep your books")
        if not LIBRARY_SHELF_LABEL_TEXT:
            LIBRARY_SHELF_LABEL_TEXT = str(self.ui.library_shelf_label.text())
        return LIBRARY_SHELF_LABEL_TEXT % self.shelf()

    def refresh(self, *refresh):

        slots, tasks = zip(*self.all_tasks) #unzip in python

        if not refresh or refresh == ('',) or refresh == (None,):
            tasks = self.all_tasks
        else:
            not_allowed = filter(lambda t: t not in tasks, refresh)
            if not_allowed:
                raise ValueError("'%s' are not available for refresh" % not_allowed)
            else:
                tasks = [self.all_tasks[tasks.index(task)] for task in refresh]

        longtask(tasks, **self.task_args)

    def available(self, book_id):
        return self.inventory[book_id].checked_in > 0

def main():
    app = QtGui.QApplication(sys.argv)
    window = Main()
    window.show()
    window.startup()
    returncode = app.exec_()
    logger.info("======== All Done (%s) ========" % str(returncode))
    sys.exit(returncode)

if __name__ == "__main__":
    logger.info("======== Starting Up ========")
    def error_handler(type, value, tb):
        logger.error("Exiting from uncaught exception",
                     exc_info = (type, value, tb))
        exit(1)
    sys.excepthook = error_handler
    main()
