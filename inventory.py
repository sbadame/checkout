import logging
import unicodecsv as csv

from PyQt4 import QtCore

from safewriter import SafeWrite

logger = logging.getLogger()


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


class Inventory(QtCore.QObject):

    # Emitted whenever a book is added to the inventory
    bookAdded = QtCore.pyqtSignal(int, InventoryRecord)

    def __init__(self, path):
        super(QtCore.QObject, self).__init__()
        self.path = path
        self.inventory = {}

    def load_inventory(self):
        with open(self.path, 'rb') as inventoryfile:
            logger.info("Loading inventory from %s", self.path)
            # The book id is the key in the dictionary, but is
            # not stored in the InventoryRecord, so we need to add one for it.
            # buuut we have an extra field "extra_data" that stores the extra
            # stuff so it all works out in the end
            number_of_fields = InventoryRecord.NUMBER_OF_CSV_FIELDS
            for row in csv.reader(inventoryfile):
                id, title, author, num_in, num_out = row[0:number_of_fields]
                self.addBook(int(id), title, author, int(num_in), int(num_out))

    def persist(self):
        logger.info("Persisting the inventory to %s", self.path)

        with SafeWrite(self.path, 'b') as (inventoryfile, _):
            writer = csv.writer(inventoryfile)
            data = self.inventory.items()
            data.sort(key=lambda (id, record): (record.author, record.title))
            for id, record in data:
                writer.writerow(
                    [id,
                     record.title,
                     record.author,
                     record.checked_in,
                     record.checked_out] +
                    record.extra_data)
        logger.info("Done with persisting.")

    def addBook(self, id, title, author, checked_in=1, checked_out=0):
        if id not in self:
            logger.info("Adding to the Inventory: %s", (id, title, author))
            book = InventoryRecord(title, author, checked_in, checked_out)
            self.inventory[id] = book
            self.bookAdded.emit(id, book)
        else:
            raise ValueError("%d is already contained in this inventory" % id)

    def __contains__(self, id):
        try:
            return int(id) in self.inventory
        except ValueError:
            return False

    def __getitem__(self, id):
        try:
            return self.inventory[int(id)]
        except ValueError:
            return False

    def __setitem__(self, id, book):
        self.inventory[id] = book

    def checkout(self, id):
        self.inventory[id].check_out_a_copy()

    def checkin(self, id):
        self.inventory[id].check_in_a_copy()

    def items(self):
        return self.inventory.items()
