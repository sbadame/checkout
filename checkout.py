import csv
import sys
import goodreads
from checkoutgui import Ui_MainWindow
from datetime import datetime
from PyQt4 import QtGui, QtCore
from shelfdialog import Ui_Dialog as BaseShelfDialog

_LOG_PATH_KEY = 'LOG_PATH'
if _LOG_PATH_KEY not in goodreads.config:
    goodreads.config[_LOG_PATH_KEY] = 'checkout.csv'

checkoutrecord = csv.writer(open(goodreads.config[_LOG_PATH_KEY], 'ab'))

USER_LABEL_TEXT = 'Currently logged in as %s.'
CHECKEDOUT_SHELF_LABEL_TEXT = 'Your "%s" shelf is being used to store the books that are checked out.'
CHECKEDIN_SHELF_LABEL_TEXT = 'Your "%s" shelf is being used to store the books that are checked in.'
LOG_LABEL_TEXT = 'The log is recorded at "%s".'

""" To regenerate the gui from the design: pyuic4 checkout.ui -o checkoutgui.py"""
class Main(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.refresh()

    def on_checkout_search_pressed(self):
        """ Connected to signal through AutoConnect """
        search_query = self.ui.checkout_query.text()
        self.populate_table(
            goodreads.search(search_query, goodreads.CHECKEDIN_SHELF),
            self.ui.checkedin_books,
            self.checkout_pressed)

    def on_checkin_search_pressed(self):
        """ Connected to signal through AutoConnect """
        search_query = self.ui.checkin_query.text()
        self.populate_table(
            goodreads.search(search_query, goodreads.CHECKEDOUT_SHELF),
            self.ui.checkedout_books,
            self.checkin_pressed)

    def on_switch_user_button_pressed(self):
        def wait_for_user():
            QtGui.QMessageBox.question(self, "Hold up!",
"""I'm opening a link to goodreads for you.
Once you have clicked on accept in the new browser window, click "Yes" below.""",
                    QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)

        goodreads.authenticate(wait_for_user)


    def on_switch_checkedout_button_pressed(self):
        dialog = ShelfDialog(self, "the checked out books")
        if dialog.exec_():
            shelf = dialog.shelf()
            if shelf:
                goodreads.config[goodreads._CHECKEDOUT_SHELF_KEY] = shelf
                goodreads.CHECKEDOUT_SHELF = shelf
                self.refresh()

    def on_switch_checkedin_button_pressed(self):
        dialog = ShelfDialog(self, "the checked in books")
        if dialog.exec_():
            shelf = dialog.shelf()
            if shelf:
                goodreads.config[goodreads._CHECKEDIN_SHELF_KEY] = shelf
                goodreads.CHECKEDIN_SHELF = shelf
                self.refresh()

    def on_view_log_button_pressed(self):
        config_file = goodreads.config[_LOG_PATH_KEY]
        import os
        if sys.platform.startswith('win'):
            os.startfile(config_file)
        elif sys.platform.startswith("darwin"):
            os.system("open " + config_file)
        else:
            os.system("xdg-open " + config_file)

    def on_switch_log_button_pressed(self):
        file = QtGui.QFileDialog.getSaveFileName(self, filter="CSV file (*.csv)")
        goodreads.config[_LOG_PATH_KEY] = str(file)
        self.refresh()

    def populate_table(self, books, table, buttontext, onclick):
        table.clearContents()
        table.setRowCount(0)
        for (index, (id, title, author)) in enumerate(books):
            table.insertRow(index)
            table.setItem(index, 0, QtGui.QTableWidgetItem(title))
            table.setItem(index, 1, QtGui.QTableWidgetItem(author))
            checkout_button = QtGui.QPushButton(buttontext)
            checkout_button.setFixedWidth(150)
            QtCore.QObject.connect(
                checkout_button,
                QtCore.SIGNAL("clicked()"),
                lambda a = id, b = title: onclick(a,b))
            table.setCellWidget(index, 2, checkout_button)
        horizontal_header = table.horizontalHeader()
        horizontal_header.setResizeMode(0, QtGui.QHeaderView.Stretch)
        horizontal_header.setResizeMode(1, QtGui.QHeaderView.ResizeToContents)
        horizontal_header.setResizeMode(2, QtGui.QHeaderView.Fixed)
        horizontal_header.setStretchLastSection(False)
        table.setColumnWidth(2, 155)

    def checkout_pressed(self, id, title):
        """ Connected to signal in populate_table """
        name, success = QtGui.QInputDialog.getText(self,
            'Checking out %s' % title, 'What is your name?')

        if success:
            goodreads.checkout(id)
            date = datetime.now().strftime("%m/%d/%Y %I:%M%p")
            checkoutrecord.writerow([date, name, "checked out", title])
            self.refresh()

    def checkin_pressed(self, id, title):
        """ Connected to signal in populate_table """
        reply = QtGui.QMessageBox.question(self, "Checking in",
                'Are you checking in: %s?' % title, QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)

        if reply == QtGui.QMessageBox.Yes:
            goodreads.checkin(id)
            date = datetime.now().strftime("%m/%d/%Y %I:%M%p")
            checkoutrecord.writerow([date, "", "checked in", title])
            self.refresh()

    def refresh(self):
        self.refresh_checkedout()
        self.refresh_checkedin()
        self.ui.user_label.setText(
            USER_LABEL_TEXT % goodreads.user()[1])
        self.ui.checkedout_shelf_label.setText(
            CHECKEDOUT_SHELF_LABEL_TEXT % goodreads.CHECKEDOUT_SHELF)
        self.ui.checkedin_shelf_label.setText(
            CHECKEDIN_SHELF_LABEL_TEXT % goodreads.CHECKEDIN_SHELF)
        self.ui.log_label.setText(
            LOG_LABEL_TEXT % goodreads.config[_LOG_PATH_KEY])

    def refresh_checkedin(self):
        self.populate_table(
            goodreads.listbooks(goodreads.CHECKEDIN_SHELF),
            self.ui.checkedin_books,
            "Check this book out!",
            self.checkout_pressed)

    def refresh_checkedout(self):
        self.populate_table(
            goodreads.listbooks(goodreads.CHECKEDOUT_SHELF),
            self.ui.checkedout_books,
            "Return this book",
            self.checkin_pressed)

class ShelfDialog(QtGui.QDialog, BaseShelfDialog):
    def __init__(self, parent, use):
        QtGui.QDialog.__init__(self, parent)
        self.setupUi(self)
        self.label.setText(str(self.label.text()) % use)
        QtCore.QObject.connect(
            self.new_shelf_button,
            QtCore.SIGNAL("clicked()"),
            self.create_new_shelf)
        self.refresh()

    def create_new_shelf(self):
        name, success = QtGui.QInputDialog.getText(self,
            'Adding a new shelf',
            'What would you like to name the new shelf?')

        if success:
            goodreads.add_shelf(name)
            self.refresh()

    def refresh(self):
        self.list.clear()
        self.list.insertItems(0, goodreads.shelves())

    def shelf(self):
        return str(self.list.currentItem().text())

def main():
    app = QtGui.QApplication(sys.argv)
    window = Main()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
