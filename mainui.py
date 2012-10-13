"""Handles showing off the books"""

import logging

from PyQt4 import QtGui, QtCore
from checkoutgui import Ui_MainWindow
from customgui import NoVisibleFocusItemDelegate

LOGGER = logging.getLogger()

CHECKOUT_COLOR = "#FF7373"

class MainUi(Ui_MainWindow):

    def __init__(self):
        super(MainUi, self).__init__()

    def setupUi(self, main):
        super(MainUi, self).setupUi(main)
        self.search_reset.hide()
        self.books.setItemDelegate(NoVisibleFocusItemDelegate())
        self.books.setFocus()
        self.search_query.setDefaultText()

    def populate_table(self, books, oncheckin, oncheckout):
        LOGGER.info("Repopulating table")
        self._books_cached = books
        table = self.books
        table.clearContents()
        table.setRowCount(0)
        for (id, book) in books:
            self.show_book_in_table(book,
                lambda c, a=id, b=book.title: oncheckin(a, b),
                lambda c, a=id, b=book.title: oncheckout(a, b))

        horizontal_header = table.horizontalHeader()
        horizontal_header.setResizeMode(0, QtGui.QHeaderView.Stretch)
        horizontal_header.setResizeMode(1, QtGui.QHeaderView.ResizeToContents)
        horizontal_header.setResizeMode(2, QtGui.QHeaderView.ResizeToContents)
        horizontal_header.setStretchLastSection(False)

    def show_book_in_table(self, book, oncheckin, oncheckout):
        table = self.books
        row = table.rowCount()
        table.insertRow(row)

        titlewidget = QtGui.QTableWidgetItem(book.title)
        titlewidget.setFlags(QtCore.Qt.ItemIsEnabled |
                             QtCore.Qt.ItemIsSelectable)
        table.setItem(row, 0, titlewidget)

        authorwidget = QtGui.QTableWidgetItem(book.author)
        authorwidget.setFlags(QtCore.Qt.ItemIsEnabled |
                              QtCore.Qt.ItemIsSelectable)
        table.setItem(row, 1, authorwidget)

        button_widget = QtGui.QWidget()
        layout = QtGui.QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0,0,3,0)
        button_widget.setLayout(layout)

        show_checkout_button = book.checked_in > 0
        show_checkin_button = book.checked_out > 0

        if show_checkout_button:
            checkout_button = QtGui.QPushButton("Check this book out!")
            checkout_button.clicked.connect(oncheckout)
            layout.addWidget(checkout_button)

        if show_checkin_button:
            checkin_button = QtGui.QPushButton("Return this book")
            checkin_button.clicked.connect(oncheckin)
            layout.addWidget(checkin_button)

        if show_checkout_button and show_checkin_button:
            button_widget.setStyleSheet('margin:0px; padding:0px;')

        if not show_checkout_button:
            titlewidget.setBackground(
                    QtGui.QBrush(QtGui.QColor(CHECKOUT_COLOR)))
            authorwidget.setBackground(
                    QtGui.QBrush(QtGui.QColor(CHECKOUT_COLOR)))
            button_widget.setStyleSheet(
                    'background-color: "%s";' % CHECKOUT_COLOR)

        table.setCellWidget(row, 2, button_widget)

    def on_books_currentCellChanged(self, prow, pcolumn, row, column):
        if self._books_cached:
            book = self.books[prow]
            if book.checked_in > 0:
                self.ui.books.setStyleSheet('')
            else:
                self.ui.books.setStyleSheet(
                        'selection-background-color: "%s"' %
                        CHECKOUT_COLOR_SELECTED)
