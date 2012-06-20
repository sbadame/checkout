import goodreads

id, name = goodreads.user()

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
    elif choice == 1:
        goodreads.config[goodreads._CHECKEDIN_SHELF_KEY] = shelf_name

elif choice == 1:
    goodreads.authenticate()
elif choice == 2:
    query = raw_input("Search for: ")
    results = goodreads.search(query)
    for index, (id, title) in enumerate(results):
        print("%d: %s" % (index, title))
    response = raw_input("Which would you like to check out?")

    try:
        response_index = int(response)
        goodreads.add_to_shelf("checkedout", results[response_index][0])
    except ValueError:
        print("Didn't understand: %s. Good bye." % response)


elif choice == 3:
    print("Return")
