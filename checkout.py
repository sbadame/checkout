import csv
import sys
import goodreads
from checkoutgui import Ui_MainWindow
from datetime import datetime
from PyQt4 import QtGui, QtCore

checkoutrecord = csv.writer(open('checkout.csv', 'ab'))

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

    def populate_table(self, books, table, buttontext, onclick):
        table.clearContents()
        table.setRowCount(0)
        for (index, (id, title, author)) in enumerate(books):
            table.insertRow(index)
            table.setItem(index, 0, QtGui.QTableWidgetItem(title))
            table.setItem(index, 1, QtGui.QTableWidgetItem(author))
            checkout_button = QtGui.QPushButton(buttontext)
            QtCore.QObject.connect(
                checkout_button,
                QtCore.SIGNAL("clicked()"),
                lambda a = id, b = title: onclick(a,b))
            table.setCellWidget(index, 2, checkout_button)

    def checkout_pressed(self, id, title):
        """ Connected to signal in populate_table """
        name, success = QtGui.QInputDialog.getText(self,
            'Checking out %s' % title,
            'What is your name?')

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

    def refresh_checkedin(self):
        self.populate_table(
            goodreads.listbooks(goodreads.CHECKEDIN_SHELF),
            self.ui.checkedin_books,
            "Check it out!",
            self.checkout_pressed)

    def refresh_checkedout(self):
        self.populate_table(
            goodreads.listbooks(goodreads.CHECKEDOUT_SHELF),
            self.ui.checkedout_books,
            "Return this book",
            self.checkin_pressed)

def main():
    app = QtGui.QApplication(sys.argv)
    window = Main()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
