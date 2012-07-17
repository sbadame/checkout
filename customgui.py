from PyQt4.QtGui import QLineEdit, QFocusEvent, QItemDelegate
from PyQt4.QtCore import QEvent

class CustomLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super(CustomLineEdit, self).__init__(parent)
        self.defaultText = None

    def focusInEvent(self, event):
        if self.defaultText and self.displayText() == self.defaultText:
            self.clear()
            self.setStyleSheet("color: black; font-style: normal")
        QLineEdit.focusInEvent(self, QFocusEvent(QEvent.FocusIn))

    def focusOutEvent(self, event):
        if self.defaultText and not str(self.displayText()).strip():
            self.setText(self.defaultText)
            self.setStyleSheet("color: gray; font-style: italic")
        QLineEdit.focusOutEvent(self, QFocusEvent(QEvent.FocusOut))

    def setDefaultText(self, text=None):
        if text:
            self.defaultText = text
        else:
            self.defaultText = self.displayText()
        self.setStyleSheet("color: gray; font-style: italic")

class NoVisibleFocusItemDelegate(QItemDelegate):
    def __init__(self, parent=None):
        super(QItemDelegate, self).__init__(parent)

    def drawFocus(self, painter, option, rect):
        pass
