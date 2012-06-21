import sys
import goodreads
from checkoutgui import Ui_MainWindow
from PyQt4 import QtGui


class Main(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        available_books = goodreads.listbooks(goodreads.CHECKEDIN_SHELF)
        for (index, (id, title, author)) in enumerate(available_books):
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
