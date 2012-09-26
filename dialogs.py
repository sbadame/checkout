from shelfdialog import Ui_Dialog as BaseShelfDialog
from PyQt4 import QtGui, QtCore

SHELF_DIALOG_LABEL_TEXT = "Which shelf should be used for the library books?"

class ShelfDialog(QtGui.QDialog, BaseShelfDialog):
    def __init__(self, parent, items):
        QtGui.QDialog.__init__(self, parent)
        self.setupUi(self)
        self.label.setText(SHELF_DIALOG_LABEL_TEXT)
        self.list.clear()
        self.list.insertItems(0, items)

    def on_button_press(self):
        pass


    def shelf(self):
        return str(self.list.currentItem().text())
