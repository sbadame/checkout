import goodreads
import inventory
import sys
import os.path as path
import logging

from PyQt4 import QtGui, QtCore
from config import Config
from dialogs import ListDialog
from datetime import datetime
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
_LIBRARY_SHELF_KEY = "LIBRARY_SHELF"
_LOG_PATH_KEY = 'LOG_PATH'
_INVENTORY_PATH_KEY = 'INVENTORY_PATH'

# UI Constants
USER_LABEL_TEXT = None
LIBRARY_SHELF_LABEL_TEXT = None
LOG_LABEL_TEXT = None
INVENTORY_LABEL_TEXT = None
SHELF_DIALOG_LABEL_TEXT = "Which shelf should be used for the library books?"

DEVELOPER_KEY = "DEVELOPER_KEY"
DEVELOPER_SECRET = "DEVELOPER_SECRET"

SEARCH_TIMEOUT = 800


def openfile(filepath):
    import os
    if sys.platform.startswith('win'):
        os.startfile(filepath)
    elif sys.platform.startswith("darwin"):
        os.system("open " + filepath)
    else:
        os.system("xdg-open " + filepath)


# To regenerate the gui from the design:
#   pyuic4 checkout.ui -o checkoutgui.py


class Main(QtGui.QMainWindow):

    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.progress = QtGui.QProgressDialog(self)
        self.progress.setRange(0, 0)
        self.progress.setWindowTitle("Working...")
        self.books_in_table = []
        self._goodreads = None

    def startup(self):
        self.ui = MainUi()
        self.ui.setupUi(self)

        self.ui.options_button.clicked.connect(
            lambda: self.ui.uistack.setCurrentWidget(self.ui.optionspage))
        self.ui.back_to_books.clicked.connect(
            lambda: self.ui.uistack.setCurrentWidget(self.ui.bookpage))

        self.searchTimer = None

        self.config = self.init_config()

        inventory_path = self.config[_INVENTORY_PATH_KEY]
        self.inventory = inventory.Inventory(inventory_path)
        self.inventory.bookAdded.connect(
            lambda book, index: self.ui.addBook(
                book, self.checkin_pressed, self.checkout_pressed, index))
        try:
            self.inventory.load_inventory()
        except IOError:
            logger.warn('Error accessing: %s, is this a first run?',
                        inventory_path)

    def populate_table(self, books):
        self.ui.populate_table(books, self.checkin_pressed,
                               self.checkout_pressed)

    def init_config(self):
        config = Config(CONFIG_FILE_PATH)
        config.connectKey(
            _LOG_PATH_KEY,
            lambda x: self.ui.log_label.setText(self.log_file(x)))
        config.connectKey(
            _INVENTORY_PATH_KEY,
            lambda x: self.ui.inventory_label.setText(self.inventory_file(x)))
        config.connectKey(
            _LIBRARY_SHELF_KEY,
            lambda x: self.ui.library_shelf_label.setText(
                self.library_shelf(x)))

        try:
            with open(CONFIG_FILE_PATH, "r") as configfile:
                config.load_from_file(configfile)
        except IOError as e:
                logger.warn(("Error loading: %s (%s)."
                             "(This is normal for a first run)") %
                            (CONFIG_FILE_PATH, e))

        default_configuration = [
            (_LOG_PATH_KEY, lambda: DEFAULT_LOG_PATH),
            (_INVENTORY_PATH_KEY, lambda: DEFAULT_INVENTORY_FILE_PATH),
            (DEVELOPER_KEY, self.request_dev_key),
            (DEVELOPER_SECRET, self.request_dev_secret),
        ]

        for key, loader in default_configuration:
            if key not in config:
                logger.info("Missing a value for your %s property" % key)
                config[key] = loader()

        return config

    def update_progress(self, text):
        self.progress.show()
        self.progress.setLabelText(text)

    def hide_progress(self):
        self.progress.hide()

    def shelf(self):
        return self.config[_LIBRARY_SHELF_KEY]

    def request_dev_key(self, log=logger.info):
        key, success = QtGui.QInputDialog.getText(
            None,
            "Developer Key?",
            ('A developer key is needed to communicate with goodreads.\n'
             'You can find it here: http://www.goodreads.com/api/keys'))
        if not success:
            exit()
        return str(key)

    def request_dev_secret(self):
        secret, success = QtGui.QInputDialog.getText(
            None, "Developer Secret?",
            ('What is the developer secret for the key that you just gave?\n'
             'It\'s also on that page with the key: '
             'http://www.goodreads.com/api/keys)'))
        if not success:
            exit()
        return str(secret)

    def on_search_query_textEdited(self, text):
        def do_search(x):
            logger.info("Searching for %s", x)
            query = str(x).strip().lower()
            if query:
                self.ui.setSearchQuery(query)
            else:
                self.ui.clearSearchQuery()

        if self.searchTimer:
            self.searchTimer.stop()

        self.searchTimer = QtCore.QTimer()
        self.searchTimer.setSingleShot(True)
        self.searchTimer.setInterval(SEARCH_TIMEOUT)
        self.searchTimer.timeout.connect(lambda: do_search(text))
        self.searchTimer.start()

    def wait_for_user(self):
        QtGui.QMessageBox.question(
            self,
            "Hold up!",
            ('I\'m opening a link to goodreads for you. '
             'Once the goodreads page loads click "Yes" below to continue.'
             'If this is your first time, you will have to give "Checkout" '
             'permission to access your goodreads account.'),
            QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)

    def goodreads(self):
        if not self._goodreads:
            self._goodreads = goodreads.GoodReads(
                dev_key=self.config[DEVELOPER_KEY],
                dev_secret=self.config[DEVELOPER_SECRET],
                wait_function=self.wait_for_user)
        return self._goodreads

    def on_sync_button_pressed(self):
        shelf = self.shelf()
        logger.info('Syncing books from shelf: %s,', shelf)

        dirty = False
        for id, title, author in self.goodreads().listbooks(shelf):
            if not self.inventory.containsTitleAndAuthor(title, author):
                dirty = True
                self.inventory.addBook(title, author)
        if dirty:
            self.inventory.persist()
        logging.info('Done with Sync')

    def on_switch_user_button_pressed(self):
        logger.warn("Look at switch user again")

    def on_switch_library_button_pressed(self):
        dialog = ListDialog(self, SHELF_DIALOG_LABEL_TEXT,
                            self.goodreads().shelves())

        def create_new_shelf():
            name, success = QtGui.QInputDialog.getText(
                dialog,
                'Adding a new shelf',
                'What would you like to name the new shelf?')

            if success:
                self.goodreads().add_shelf(str(name))
                dialog.setItems(self.goodreads().shelves())

        dialog.button.pressed.connect(create_new_shelf)
        dialog.button.setText("Create a new shelf")

        def accepted():
            shelf = dialog.result()
            if shelf:
                self.config[_LIBRARY_SHELF_KEY] = shelf

        dialog.accepted.connect(accepted)
        dialog.exec_()

    def on_view_log_button_pressed(self):
        openfile(self.config[_LOG_PATH_KEY])

    def on_view_inventory_button_pressed(self):
        openfile(self.config[_INVENTORY_PATH_KEY])

    def on_switch_log_button_pressed(self):
        file = QtGui.QFileDialog.getSaveFileName(self,
                                                 filter='CSV file (*.csv)')
        if file:
            self.config[_LOG_PATH_KEY] = str(file)

    def on_switch_inventory_button_pressed(self):
        file = QtGui.QFileDialog.getSaveFileName(self,
                                                 filter='CSV file (*.csv)')
        if file:
            self.config[_INVENTORY_PATH_KEY] = str(file)
            self.inventory.persist()

    def checkout_pressed(self, book):
        """ Connected to signal in populate_table """

        name, success = QtGui.QInputDialog.getText(
            self,
            'Checking out %s' % book.title, 'What is your name?')
        if success:
            date = datetime.now().strftime("%m/%d/%Y %I:%M%p")

            with open(self.config[_LOG_PATH_KEY], 'ab') as logfile:
                writer = csv.writer(logfile)
                writer.writerow([date, str(name), "checked out", -1,
                                 book.title])

            if book in self.inventory:  # This can probably be removed
                book.check_out_a_copy()
                self.inventory.persist()
            else:
                logger.critical("checkout.checkout_pressed: Didn't find %s"
                                % book)

    def candidates_for_return(self, book):
        possible_people = []
        with open(self.config[_LOG_PATH_KEY], 'rb') as logfile:
            for row in csv.reader(logfile):
                try:
                    if row[4].strip() == book.title:
                        name = row[1].strip()
                        if name not in possible_people:
                            possible_people.append(name)
                except ValueError:
                    # it's ok if there is a malformed cell/row
                    logger.warn("Malformed row: " + str(row))

        return possible_people

    def checkin_pressed(self, book):
        """ Connected to signal in populate_table """

        dialog = ListDialog(self,
                            "Who are you?",
                            self.candidates_for_return(book))

        def not_on_list():
            name, success = QtGui.QInputDialog.getText(
                self,
                'Return %s' % book.title, 'What is your name?')

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
                    writer.writerow([date, name, "checked in", -1, book.title])

                if book in self.inventory:  # Can probably remove this check
                    book.check_in_a_copy()
                    self.inventory.persist()
                else:
                    logger.critical('Couldn\'t find book: %s' % book)

    def log_file(self, log_file):
        """Returns the string used in the Options GUI for the log file """
        global LOG_LABEL_TEXT
        if not LOG_LABEL_TEXT:
            LOG_LABEL_TEXT = str(self.ui.log_label.text())
        return LOG_LABEL_TEXT % log_file

    def inventory_file(self, inventory_file):
        """Text used in the Options GUI for the inventory file."""
        global INVENTORY_LABEL_TEXT

        logging.info("Figuring out where I keep track of your books")
        if not INVENTORY_LABEL_TEXT:
            INVENTORY_LABEL_TEXT = str(self.ui.inventory_label.text())
        return INVENTORY_LABEL_TEXT % inventory_file

    def library_shelf(self, shelf):
        global LIBRARY_SHELF_LABEL_TEXT
        """ Returns the string used in the Options GUI for the shelf """
        logging.info("Figuring out where you keep your books")
        if not LIBRARY_SHELF_LABEL_TEXT:
            LIBRARY_SHELF_LABEL_TEXT = str(self.ui.library_shelf_label.text())
        return LIBRARY_SHELF_LABEL_TEXT % shelf


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
                     exc_info=(type, value, tb))
        exit(1)
    sys.excepthook = error_handler
    main()
