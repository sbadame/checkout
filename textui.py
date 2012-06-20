import goodreads

id, name = goodreads.user()

choice = ""

while choice not in [1, 2, 3]:
    try:
        choice = int(raw_input("""Hello %s. What would you like to do?
    1) Re-authenticate
    2) Search for a book
    3) Return a book
""" % name))
    except ValueError:
        print("%s is not a valid choice." % choice)

if choice == 1:
    print("Reauthenticate")
elif choice == 2:
    print("Search")
elif choice == 3:
    print("Return")
