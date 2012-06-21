import oauth2 as oauth
import time
import urllib
import urlparse
import json
import xml.etree.ElementTree as ET

#PROGRAM CONSTANTS
HTTP_OK = '200'
HTTP_CREATED = '201'

#Config Constants
_CHECKEDOUT_SHELF_KEY = 'CHECKEDOUT_SHELF'
_CHECKEDIN_SHELF_KEY = 'CHECKEDIN_SHELF'

CONFIG_FILE_PATH = "checkout.credentials"

SITE = "http://www.goodreads.com"
REQUEST_TOKEN_URL = "%s/oauth/request_token" % SITE
AUTHORIZE_URL = "%s/oauth/authorize" % SITE
ACCESS_TOKEN_URL = "%s/oauth/access_token" % SITE


class Config(dict):
    def __init__(self, filepath, *args):
        self.filepath = filepath
        super(Config, self).__init__(self, *args)

    @staticmethod
    def load_from_file(fp):
        c = Config(fp.name)
        for k,v in json.load(fp).items():
            c.__setitem__withoutwrite(k, v)
        return c

    def __setitem__withoutwrite(self, key, val):
        super(Config, self).__setitem__(key, val)

    def __setitem__(self, key, val):
        super(Config, self).__setitem__(key, val)
        with open(self.filepath, "w") as configfile:
            json.dump(self, configfile)

#CONSTANTS FROM CONFIG
try:
    with open(CONFIG_FILE_PATH, "r") as configfile:
        config = Config.load_from_file(configfile)
except IOError as e:
        print("Error loading: %s (%s)" % (CONFIG_FILE_PATH, e))
        config = Config(CONFIG_FILE_PATH)

if "DEVELOPER_KEY" not in config:
    config["DEVELOPER_KEY"] = raw_input("No developer key found: What is the app's developer key?")
    config["DEVELOPER_SECRET"] = raw_input("What is the app's developer key secret?")

DEVELOPER_KEY = config["DEVELOPER_KEY"]
DEVELOPER_SECRET = config["DEVELOPER_SECRET"]

if _CHECKEDOUT_SHELF_KEY in config:
    CHECKEDOUT_SHELF = config[_CHECKEDOUT_SHELF_KEY]
else:
    CHECKEDOUT_SHELF = "checkedout"

if _CHECKEDIN_SHELF_KEY in config:
    CHECKEDIN_SHELF = config[_CHECKEDIN_SHELF_KEY]
else:
    CHECKEDIN_SHELF = "checkedin"

consumer = oauth.Consumer(key = DEVELOPER_KEY, secret = DEVELOPER_SECRET)

def authenticate(waitfunction=lambda:raw_input("Press enter once authorized.")):
    """ Grabs a new set of keys from goodreads.
        Opens the authorization link in a new browser window.
        Calls the waitfunction() once the browser is opened. 
        The waitfunction should return only when the user has authorized the app"""

    client = oauth.Client(consumer)
    response, content = client.request(REQUEST_TOKEN_URL, "GET")
    time.sleep(1)
    if response['status'] != HTTP_OK:
        raise Exception("Something wrong with the developer keys or goodreads: " + response['status'])

    request_token_dict = dict(urlparse.parse_qsl(content))
    request_token = request_token_dict['oauth_token']
    request_token_secret = request_token_dict['oauth_token_secret']

    authorize_link = "%s?oauth_token=%s" % (AUTHORIZE_URL, request_token)
    import webbrowser
    webbrowser.open(authorize_link)
    waitfunction()

    request_token = oauth.Token(request_token, request_token_secret)
    client = oauth.Client(consumer, request_token)
    response, content = client.request(ACCESS_TOKEN_URL, 'POST')
    time.sleep(1)
    if response['status'] != HTTP_OK:
        raise Exception("Something went wrong getting the access token: %s" % response['status'])

    access_dict = dict(urlparse.parse_qsl(content))
    access_token = access_dict['oauth_token']
    access_secret = access_dict['oauth_token_secret']
    return (access_token, access_secret)

if "ACCESS_KEY" not in config:
    config["ACCESS_KEY"], config["ACCESS_SECRET"] = authenticate()

ACCESS_KEY = config["ACCESS_KEY"]
ACCESS_SECRET = config["ACCESS_SECRET"]

access_token = oauth.Token(ACCESS_KEY, ACCESS_SECRET)


def _request(methodname, params={}, method='GET', success=HTTP_OK):
    consumer = oauth.Consumer(key=DEVELOPER_KEY,
                              secret=DEVELOPER_SECRET)
    client  = oauth.Client(consumer, access_token)
    body = urllib.urlencode(params)
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    resp, content = client.request(SITE + '/' + methodname, method, body, headers)
    if resp['status'] != success:
        raise Exception('Did not get expected HTTP status: %s' % resp['status'])

    return content

_user_id = None
def _cached_user_id():
    if not _user_id:
        user()
    return _user_id

def user():
    global _user_id
    response = _request("api/auth_user")
    xml = ET.fromstring(response)
    user = xml.find("user")
    _user_id, user_name = int(user.get("id")), user.findtext("name")
    return _user_id, user_name

def search(query, shelf):
    params = {
        "v":2,
        "shelf": shelf,
        "key": DEVELOPER_KEY,
    }
    if query:
        params["search[query]"] = query

    response = _request("review/list/%d.xml" % _cached_user_id(), params)
    xml = ET.fromstring(response)
    results = []
    for review in xml.findall("reviews/review"):
        if any([s.get("name") == shelf for s in review.findall("shelves/shelf")]):
            results.append((
                int(review.findtext("book/id")),
                review.findtext("book/title"),
                review.findtext("book/authors/author/name")
            ))
    return results

def listbooks(shelf):
    return search(None, shelf)

def add_to_shelf(shelf, book_id):
    params = {
        "name": shelf,
        "book_id": book_id
    }
    _request("shelf/add_to_shelf.xml", params, 'POST', HTTP_CREATED)

def remove_from_shelf(shelf, book_id):
    params = {
        "name": shelf,
        "book_id": book_id,
        "a": "remove"
    }
    _request("shelf/add_to_shelf.xml", params, method='POST')


def checkout(book_id):
    add_to_shelf(CHECKEDOUT_SHELF, book_id)
    remove_from_shelf(CHECKEDIN_SHELF, book_id)

def checkin(book_id):
    add_to_shelf(CHECKEDIN_SHELF, book_id)
    remove_from_shelf(CHECKEDOUT_SHELF, book_id)

def shelves():
    params = {"key":DEVELOPER_KEY, "user_id":_cached_user_id()}
    xml = ET.fromstring(_request("shelf/list.xml", params))
    return [name.text for name in xml.findall("shelves/user_shelf/name")]

def add_shelf(name):
    return _request("user_shelves.xml", {"user_shelf[name]": name}, 'POST')

if __name__ == '__main__':
    pass
