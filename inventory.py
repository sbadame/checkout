from collections import namedtuple
import unicodecsv as csv

# How we represent books stored in the inventory csv
InventoryRecord = namedtuple('InventoryRecord',
    ['title', 'author', 'checked_in', 'checked_out', 'extra_data'])


def load_inventory(path):
    inventory = Inventory(path)
    with open(path, 'rb') as inventoryfile:
        print("Opened: " + path)
        # The book id is the key in the dictionary, but is
        # not stored in the InventoryRecord, so we need to add one for it.
        # buuut we have an extra field "extra_data" that stores the extra stuff
        # so it all works out in the end
        number_of_fields = len(InventoryRecord._fields)
        for row in csv.reader(inventoryfile):
            id, title, author, num_in, num_out = row[0:number_of_fields]
            inventory.inventory[int(id)] = InventoryRecord(
                title, author, int(num_in), int(num_out), row[number_of_fields:])
    return inventory

def create_inventory(path, books):
    inventory = Inventory(path)
    with SafeWrite(path, 'b') as (inventoryfile, oldfile):
        for id, title, author in books:
            writer.writerow([id, title, author, 1, 0])
            inventory.inventory[int(id)] = InventoryRecord(title, author, 1, 0, [])
        writer = csv.writer(inventoryfile)
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
            data.sort(key = lambda (id, record): (record.author, record.title))
            for id, record in data:
                writer.writerow([id, record.title, record.author, record.checked_in, record.checked_out] +
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
        old = self.inventory[id]
        self.inventory[id] = old._replace(
            checked_in = old.checked_in - 1,
            checked_out = old.checked_out + 1)

    def checkin(self, id):
        old = self.inventory[id]
        self.inventory[id] = old._replace(
            checked_in = old.checked_in + 1,
            checked_out = old.checked_out - 1)

    def items(self):
        return self.inventory.items()

    def search(self, query):
        query = query.lower()
        for record in self.inventory.itervalues():
            if query in record.title.lower() or query in record.author.lower():
                yield record

