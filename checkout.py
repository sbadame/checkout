import sys
import goodreads
from checkoutgui import Ui_MainWindow
from PyQt4 import QtGui


""" To regenerate the gui from the design: pyuic4 checkout.ui -o checkoutgui.py"""
class Main(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.populate_table(goodreads.listbooks(goodreads.CHECKEDIN_SHELF))

    def on_searchbutton_pressed(self):
        search_query = self.ui.query_text.text()
        self.populate_table(goodreads.search(search_query, goodreads.CHECKEDIN_SHELF))

    def populate_table(self, books):
        self.ui.books.clearContents()
        for (index, (id, title, author)) in enumerate(books):
            self.ui.books.insertRow(index)
            self.ui.books.setItem(index, 0, QtGui.QTableWidgetItem(title))
            self.ui.books.setItem(index, 1, QtGui.QTableWidgetItem(author))
            self.ui.books.setItem(index, 2, QtGui.QTableWidgetItem("available"))


def main():
    app = QtGui.QApplication(sys.argv)
    window = Main()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
