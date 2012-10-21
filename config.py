import json
from safewriter import SafeWrite
from PyQt4 import QtCore


class Config(dict):

    def __init__(self, filepath, *args):
        self.filepath = filepath
        self.signal_sender = SignalSender()
        self.slots = {}
        super(Config, self).__init__(self, *args)

    def load_from_file(self, fp):
        for k, v in json.load(fp).items():
            self.__setitem__withoutwrite(k, v)

    def __setitem__withoutwrite(self, key, val):
        super(Config, self).__setitem__(key, val)
        if key in self.slots:
            self.slots[key].optionChanged.emit(val)

    def __setitem__(self, key, val):
        self.__setitem__withoutwrite(key, val)
        with SafeWrite(self.filepath) as (configfile, oldfile):
            json.dump(self, configfile)

    def connectKey(self, key, slot):
        if key not in self.slots:
            self.slots[key] = SignalSender()
        self.slots[key].optionChanged.connect(slot)


class SignalSender(QtCore.QObject):

    # Emitted whenever a book is added to the inventory
    optionChanged = QtCore.pyqtSignal(str)

    def __init__(self):
        super(QtCore.QObject, self).__init__()
