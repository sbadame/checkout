import logging
import unicodecsv as csv
from safewriter import SafeWrite

LOGGER = logging.getLogger()


class InventoryRecord(object):
    """The line item of this program."""

    # Number of fields per Inventory record in the csv
    NUMBER_OF_CSV_FIELDS = 5

    def __init__(self, title, author, checked_in=1, checked_out=0,
                 extra_data=None):
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

    def check_out_a_copy(self):
        self.checked_in -= 1
        self.checked_out += 1

    def __str__(self):
        info = (self.__class__.__name__, self.title, self.author,
                int(self.checked_in), int(self.checked_out),
                str(self.extra_data))
        return (('%s(title=%s,author=%s,checked_in=%d,checked_out=%d,'
                'extra_data=%s)') % info)


def load_inventory(path):
    inventory = Inventory(path)
    with open(path, 'rb') as inventoryfile:
        LOGGER.info("Opened: " + path)
        # The book id is the key in the dictionary, but is
        # not stored in the InventoryRecord, so we need to add one for it.
        # buuut we have an extra field "extra_data" that stores the extra stuff
        # so it all works out in the end
        number_of_fields = InventoryRecord.NUMBER_OF_CSV_FIELDS
        for row in csv.reader(inventoryfile):
            id, title, author, num_in, num_out = row[0:number_of_fields]
            inventory.inventory[int(id)] = InventoryRecord(
                title,
                author,
                int(num_in),
                int(num_out),
                row[number_of_fields:])
    return inventory


def create_inventory(path, books):
    inventory = Inventory(path)
    with SafeWrite(path, 'b') as (inventoryfile, oldfile):
        writer = csv.writer(inventoryfile)
        for id, title, author in books:
            writer.writerow([id, title, author, 1, 0])
            inventory.inventory[int(id)] = InventoryRecord(title, author)
    inventory.persist_inventory()
    return inventory


class Inventory():

    def __init__(self, path):
        self.path = path
        self.inventory = {}

    def persist(self):
        with open(self.path, 'wb') as inventoryfile:
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

    def search(self, query):
        results = []
        query = query.lower()
        for id, record in self.items():
            if query in record.title.lower() or query in record.author.lower():
                results.append((id, record))
        return results
