"""Handles showing off the books"""

import logging
import inventory

from PyQt4 import QtGui, QtCore
from bookwidget import Ui_Form as BookBase
from checkoutgui import Ui_MainWindow
from customgui import NoVisibleFocusItemDelegate

LOGGER = logging.getLogger()

BACKGROUND_COLOR = "#FFFFFF"
SELECTED_COLOR = "#336699"

CHECKOUT_COLOR = "#FF7373"
CHECKOUT_COLOR_SELECTED = "#BF3030"


class BookWidget(QtGui.QWidget, BookBase):
    def __init__(self, book, oncheckedin, oncheckedout):
        QtGui.QWidget.__init__(self)
        self.setupUi(self)
        self.setObjectName(str(book))
        self.title.setText(book.title)
        self.author.setText(book.author)
        self.checkin.clicked.connect(oncheckedin)
        self.checkout.clicked.connect(oncheckedout)
        self.book = book
        book.inventory_changed.connect(self.onInventoryChange)
        self.setStyleSheet('background-color: "%s"' % BACKGROUND_COLOR)
        self.onInventoryChange(book.checked_in, book.checked_out)

    def focusInEvent(self, event):
        self.setStyleSheet('background-color: "%s"' % SELECTED_COLOR)

    def focusOutEvent(self, event):
        self.setStyleSheet('background-color: "%s"' % BACKGROUND_COLOR)

    @QtCore.pyqtSlot(int, int)
    def onInventoryChange(self, checked_in, checked_out):
        self.checkin.setVisible(checked_out > 0)
        self.checkout.setVisible(checked_in > 0)
        if checked_in <= 0:
            if self.hasFocus():
                self.setStyleSheet('background-color: "%s"' %
                                   CHECKOUT_COLOR_SELECTED)
            else:
                self.setStyleSheet('background-color: "%s"' % CHECKOUT_COLOR)
        else:
            if self.hasFocus():
                self.setStyleSheet('background-color: "%s"' %
                                   SELECTED_COLOR)
            else:
                self.setStyleSheet('background-color: "%s"' % BACKGROUND_COLOR)

    def setSearchQuery(self, query):
        if query in str(self.title.text()).lower() or (
                query in str(self.author.text()).lower()):
            self.show()
        else:
            self.hide()

    def clearSearchQuery(self):
        self.show()


class MainUi(Ui_MainWindow):

    def __init__(self):
        super(MainUi, self).__init__()

    def setupUi(self, main):
        super(MainUi, self).setupUi(main)
        self.books.setItemDelegate(NoVisibleFocusItemDelegate())
        self.books.setFocus()
        self.search_query.setDefaultText()

    def setSearchQuery(self, query):
        for i in range(self.booklist.count()):
            self.booklist.itemAt(i).widget().setSearchQuery(query)

    def clearSearchQuery(self):
        for i in range(self.booklist.count()):
            self.booklist.itemAt(i).widget().clearSearchQuery()

    def showBooks(self, booksWithId):
        if booksWithId:
            ids, books = zip(*booksWithId)
            for i in range(self.booklist.count()):
                bookwidget = self.booklist.itemAt(i).widget()
                bookwidget.setVisible(bookwidget.book in books)

    def showAllBooks(self):
        for i in range(self.booklist.count()):
            self.booklist.itemAt(i).widget().setVisible(True)

    def populate_list(self, books, oncheckin, oncheckout):
        LOGGER.info("Repopulating list")
        self._books_cached = books
        for id, book in books:
            self.show_book_in_list(
                book,
                lambda c, a=id, b=book.title: oncheckin(a, b),
                lambda c, a=id, b=book.title: oncheckout(a, b))

    @QtCore.pyqtSlot(inventory.InventoryRecord, object, object)
    def addBook(self, id, book, oncheckedin, oncheckedout):
        self.booklist.addWidget(BookWidget(
            book,
            lambda c, a=id, b=book.title: oncheckedin(a, b),
            lambda c, a=id, b=book.title: oncheckedout(a, b)))
