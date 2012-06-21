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
        self.populate_table(goodreads.listbooks(goodreads.CHECKEDIN_SHELF))

    def on_checkout_search_pressed(self):
        """ Connected to signal through AutoConnect """
        search_query = self.ui.checkout_query.text()
        self.populate_table(goodreads.search(search_query, goodreads.CHECKEDIN_SHELF))

    def on_checkin_search_pressed(self):
        """ Connected to signal through AutoConnect """
        print(self.ui.checkin_query.text())

    def populate_table(self, books):
        self.ui.checkedin_books.clearContents()
        self.ui.checkedin_books.setRowCount(0)
        for (index, (id, title, author)) in enumerate(books):
            self.ui.checkedin_books.insertRow(index)
            self.ui.checkedin_books.setItem(index, 0, QtGui.QTableWidgetItem(title))
            self.ui.checkedin_books.setItem(index, 1, QtGui.QTableWidgetItem(author))
            checkout_button = QtGui.QPushButton("Checkout!")
            QtCore.QObject.connect(
                checkout_button, 
                QtCore.SIGNAL("clicked()"),
                lambda b = (id, title, author): self.checkout_pressed(b))
            self.ui.checkedin_books.setCellWidget(index, 2, checkout_button)

    def checkout_pressed(self, (id, title, author)):
        """ Connected to signal in populate_table """
        name, success = QtGui.QInputDialog.getText(self,
            'Checking out %s' % title,
            'What is your name?')

        if success:
            goodreads.checkout(id)
            date = datetime.now().strftime("%m/%d/%Y %I:%M%p")
            checkoutrecord.writerow([date, name, "checked out", title])
            self.populate_table(goodreads.listbooks(goodreads.CHECKEDIN_SHELF))

def main():
    app = QtGui.QApplication(sys.argv)
    window = Main()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
