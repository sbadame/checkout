"""Handles showing off the books"""

import logging
import inventory

from PyQt4 import QtGui, QtCore
from bookwidget import Ui_Form as BookBase
from checkoutgui import Ui_MainWindow

logger = logging.getLogger()

BACKGROUND_COLOR = "#FFFFFF"
SELECTED_COLOR = "#336699"

CHECKOUT_COLOR = "#FF7373"
CHECKOUT_COLOR_SELECTED = "#BF3030"


class BookWidget(QtGui.QWidget, BookBase):
    def __init__(self, book, oncheckedin, oncheckedout):
        QtGui.QWidget.__init__(self)
        self.setupUi(self)
        self.book = book
        self.formatter = str(self.text.text())
        self.text.setText(self.uiText())
        self.checkin.clicked.connect(lambda _: oncheckedin(book))
        self.checkout.clicked.connect(lambda _: oncheckedout(book))
        book.inventory_changed.connect(self.onInventoryChange)
        self.onInventoryChange(book.checked_in, book.checked_out)

    def uiText(self):
        return (self.formatter % {"title": self.book.title,
                                  "author": self.book.author})

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
        if (query in self.book.title.lower() or
                (query in self.book.author.lower())):

            self.show()
            q_len = len(query)
            ui_text = self.uiText()
            i = ui_text.lower().find(query)
            content = (ui_text[:i] + "<u><span style='color:#2358ac;'>" +
                       ui_text[i:i + q_len] + "</span></u>" +
                       ui_text[i + q_len:])
            self.text.setText(content)
        else:
            self.hide()

    def clearSearchQuery(self):
        self.text.setText(self.uiText())
        self.show()


class MainUi(Ui_MainWindow):

    def __init__(self):
        super(MainUi, self).__init__()

    def setupUi(self, main):
        super(MainUi, self).setupUi(main)
        self.search_query.setDefaultText()
        self.booklist.insertStretch(-1)  # This fills down to the bottom

    def setSearchQuery(self, query):
        for i in range(self.booklist.count() - 1):  # Spacer at the end
            self.booklist.itemAt(i).widget().setSearchQuery(query)

    def clearSearchQuery(self):
        for i in range(self.booklist.count() - 1):   # Spacer at the end
            self.booklist.itemAt(i).widget().clearSearchQuery()

    def showBooks(self, booksWithId):
        if booksWithId:
            ids, books = zip(*booksWithId)
            for i in range(self.booklist.count()):
                bookwidget = self.booklist.itemAt(i).widget()
                bookwidget.setVisible(bookwidget.book in books)

    @QtCore.pyqtSlot(inventory.InventoryRecord, object, object, int)
    def addBook(self, book, oncheckedin, oncheckedout, index):
        self.booklist.insertWidget(index, BookWidget(
            book, oncheckedin, oncheckedout))
