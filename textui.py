import csv
import goodreads
from datetime import datetime

id, name = goodreads.user()
checkoutrecord = csv.writer(open('checkout.csv', 'ab'))

choice = None
while choice not in [0, 1, 2, 3]:
    try:
        choice = int(raw_input("""Hello %s. What would you like to do?
    0) Config
    1) Re-authenticate
    2) Search for a book
    3) Return a book
""" % name))
    except ValueError:
        print("%s is not a valid choice." % choice)

if choice == 0:
    choice = ""
    try:
        choice = raw_input("""What setting would you like to change?
0) The checkedout shelf (Currently: %s)
1) The checkedin shelf (Currently: %s)
""" % (goodreads.CHECKEDOUT_SHELF, goodreads.CHECKEDIN_SHELF))
        choice = int(choice)
    except ValueError:
        print("%s is not a valid choice." % choice)

    shelves = goodreads.shelves()
    for index, shelf in enumerate(shelves):
        print("%d: %s" % (index, shelf))
    print("%d: Create a new shelf" % len(shelves))

    index = int(raw_input("What shelf should be used?"))

    if index == len(shelves):
        shelf_name = raw_input("What should the new shelf be named?")
        goodreads.add_shelf(shelf_name)
    else:
        shelf_name = shelves[index]

    if choice == 0:
        goodreads.config[goodreads._CHECKEDOUT_SHELF_KEY] = shelf_name
        goodreads.CHECKEDOUT_SHELF = shelf_name
    elif choice == 1:
        goodreads.config[goodreads._CHECKEDIN_SHELF_KEY] = shelf_name
        goodreads.CHECKEDIN_SHELF = shelf_name

elif choice == 1:
    goodreads.authenticate()

elif choice == 2:
    print(goodreads.listbooks(goodreads.CHECKEDIN_SHELF))
    query = raw_input("Search for: ")
    results = goodreads.search(query, goodreads.CHECKEDIN_SHELF)
    for index, (id, title, author) in enumerate(results):
        print("%d: %s" % (index, title))
    response = raw_input("Which would you like to check out?")

    try:
        goodreads.checkout(results[int(response)][0])
        date = datetime.now().strftime("%m/%d/%Y %I:%M%p")
        name = raw_input("What's your name?")
        checkoutrecord.writerow([date, name, "checked out", title])
    except ValueError:
        print("Didn't understand: %s. Good bye." % response)

elif choice == 3:
    print(goodreads.listbooks(goodreads.CHECKEDOUT_SHELF))
    query = raw_input("Search for: ")
    results = goodreads.search(query, goodreads.CHECKEDOUT_SHELF)

    for index, (id, title, author) in enumerate(results):
        print("%d: %s" % (index, title))
    response = raw_input("Which would you like to return?")

    try:
        goodreads.checkin(results[int(response)][0])
        date = datetime.now().strftime("%m/%d/%Y %I:%M%p")
        name = raw_input("What's your name?")
        checkoutrecord.writerow([date, name, "checked in", title])
    except ValueError:
        print("Didn't understand %s" % response)

elif choice == 3:
    print("Return")
