from shelfdialog import Ui_Dialog as BaseShelfDialog
from PyQt4 import QtGui, QtCore

class ListDialog(QtGui.QDialog, BaseShelfDialog):
    def __init__(self, parent, labeltext, items):
        QtGui.QDialog.__init__(self, parent)
        self.setupUi(self)
        self.label.setText(labeltext)
        self.setItems(items)
        self.forced_result = None

    def setItems(self, items):
        self.list.clear()
        self.list.insertItems(0, items)

    def result(self):
        if not self.forced_result:
            return str(self.list.currentItem().text())
        else:
            return self.forced_result

