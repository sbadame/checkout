import bisect
import functools
import logging
import unicodecsv as csv

from PyQt4 import QtCore

from safewriter import SafeWrite

logger = logging.getLogger()


def debug_trace():
    '''Set a tracepoint in the Python debugger that works with Qt'''
    from PyQt4.QtCore import pyqtRemoveInputHook
    from pdb import set_trace
    pyqtRemoveInputHook()
    set_trace()


@functools.total_ordering
class InventoryRecord(QtCore.QObject):
    """The line item of this program."""

    # Number of fields per Inventory record in the csv
    NUMBER_OF_CSV_FIELDS = 5

    # Emitted whenever the quantities of this book changes
    inventory_changed = QtCore.pyqtSignal(int, int)

    def __init__(self, title, author, checked_in=1, checked_out=0,
                 extra_data=None):
        super(QtCore.QObject, self).__init__()
        self.title = title
        self.author = author
        self.checked_in = checked_in
        self.checked_out = checked_out
        if extra_data:
            self.extra_data = extra_data
        else:
            self.extra_data = []

    def check_in_a_copy(self):
        self.checked_in += 1
        self.checked_out -= 1
        self.inventory_changed.emit(self.checked_in, self.checked_out)

    def check_out_a_copy(self):
        self.checked_in -= 1
        self.checked_out += 1
        self.inventory_changed.emit(self.checked_in, self.checked_out)

    def __str__(self):
        info = (self.__class__.__name__, self.title, self.author,
                int(self.checked_in), int(self.checked_out),
                str(self.extra_data))
        return (('%s(title=%s,author=%s,checked_in=%d,checked_out=%d,'
                'extra_data=%s)') % info)

    def __eq__(self, other):
        try:
            return ((self.title.lower(), self.author.lower()) ==
                    (other.title.lower(), other.author.lower()))
        except AttributeError:
            return False

    def __lt__(self, other):
        return ((list(reversed(self.author.lower().split())), self.title) <
                (list(reversed(other.author.lower().split())), other.title))


class Inventory(QtCore.QObject):

    # Emitted whenever a book is added to the inventory
    bookAdded = QtCore.pyqtSignal(InventoryRecord, int)

    def __init__(self, path):
        super(QtCore.QObject, self).__init__()
        self.path = path
        self.inventory = []

    def load_inventory(self):
        with open(self.path, 'rb') as inventoryfile:
            logger.info("Loading inventory from %s", self.path)
            number_of_fields = InventoryRecord.NUMBER_OF_CSV_FIELDS
            for row in csv.reader(inventoryfile):
                id, title, author, num_in, num_out = row[0:number_of_fields]
                self.addBook(title, author, int(num_in), int(num_out))

    def persist(self):
        logger.info("Persisting the inventory to %s", self.path)

        with SafeWrite(self.path, 'b') as (inventoryfile, _):
            writer = csv.writer(inventoryfile)
            for book in self.inventory:
                writer.writerow(
                    [-1,
                     book.title,
                     book.author,
                     book.checked_in,
                     book.checked_out] +
                    book.extra_data)
        logger.info("Done with persisting.")

    def addBook(self, title, author, checked_in=1, checked_out=0):
        if not self.containsTitleAndAuthor(title, author):
            book = InventoryRecord(title, author, checked_in, checked_out)
            index = self.index(book)
            self.inventory.insert(index, book)
            self.bookAdded.emit(book, index)
            return book
        else:
            raise ValueError("%s,%s is already contained in this inventory" %
                             (title, author))

    def containsTitleAndAuthor(self, title, author):
        return (title, author) in [(b.title, b.author) for b in self.inventory]

    def __contains__(self, book):
        index = bisect.bisect_left(self.inventory, book)
        return self.inventory[index] == book

    def items(self):
        return self.inventory.items()

    def index(self, book):
        return bisect.bisect_left(self.inventory, book)
