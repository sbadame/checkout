from PyQt4 import QtGui, QtCore
from checkoutgui import Ui_MainWindow
from customgui import NoVisibleFocusItemDelegate

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

    def show_book_in_table(self, id, book, oncheckin, oncheckout):
        table = self.books
        row = table.rowCount()
        table.insertRow(row)

        titlewidget = QtGui.QTableWidgetItem(book.title)
        titlewidget.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
        table.setItem(row, 0, titlewidget)

        authorwidget = QtGui.QTableWidgetItem(book.author)
        authorwidget.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
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
            titlewidget.setBackground(QtGui.QBrush(QtGui.QColor(CHECKOUT_COLOR)))
            authorwidget.setBackground(QtGui.QBrush(QtGui.QColor(CHECKOUT_COLOR)))
            button_widget.setStyleSheet('background-color: "%s";' % CHECKOUT_COLOR);

        table.setCellWidget(row, 2, button_widget)
