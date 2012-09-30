
from checkoutgui import Ui_MainWindow
from customgui import NoVisibleFocusItemDelegate

class MainUi(Ui_MainWindow):

    def __init__(self):
        super(MainUi, self).__init__()

    def setupUi(self, main):
        super(MainUi, self).setupUi(main)
        self.search_reset.hide()
        self.books.setItemDelegate(NoVisibleFocusItemDelegate())
        self.books.setFocus()
        self.search_query.setDefaultText()


