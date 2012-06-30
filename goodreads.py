import oauth2 as oauth
import time
import urllib
import urlparse
import xml.etree.ElementTree as ET

#PROGRAM CONSTANTS
HTTP_OK = '200'
HTTP_CREATED = '201'
HTTP_NOT_FOUND = '404'
HTTP_BAD_GATEWAY = '502'

SITE = "http://www.goodreads.com"
REQUEST_TOKEN_URL = "%s/oauth/request_token" % SITE
AUTHORIZE_URL = "%s/oauth/authorize" % SITE
ACCESS_TOKEN_URL = "%s/oauth/access_token" % SITE

DEFAULT_WAIT = lambda: raw_input("Press enter once authorized.")

def SIMPLE_LOG(description):
    print("Log: " + description)

def NOOP_LOG(description):
    pass

class GoodReads:
    def __init__(self, config, waitfunction=DEFAULT_WAIT, log=NOOP_LOG):
        self.config = config
        self.log = log

        if 'CHECKEDOUT_SHELF' in config:
            self.checkedout_shelf = config['CHECKEDOUT_SHELF']
        if 'CHECKEDIN_SHELF' in config:
            self.checkedin_shelf = config['CHECKEDIN_SHELF']

        DEV_KEY = config["DEVELOPER_KEY"]
        DEV_SECRET = config["DEVELOPER_SECRET"]
        self.consumer = oauth.Consumer(key = DEV_KEY, secret = DEV_SECRET)

        if "ACCESS_KEY" not in config or "ACCESS_SECRET" not in config:
            self.authenticate(waitfunction)
        else:
            self.access_token = oauth.Token(config["ACCESS_KEY"], config["ACCESS_SECRET"])

        self._user_id = None

    def authenticate(self, waitfunction=DEFAULT_WAIT):
        self.log("Authenticating")
        """ Grabs a new set of keys from goodreads.
            Opens the authorization link in a new browser window.
            Calls the waitfunction() once the browser is opened. 
            The waitfunction should return only when the user has authorized the app"""

        client = oauth.Client(self.consumer)
        self.log("Getting request token")
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
        client = oauth.Client(self.consumer, request_token)
        self.log("Getting access token")
        response, content = client.request(ACCESS_TOKEN_URL, 'POST')
        time.sleep(1)
        if response['status'] != HTTP_OK:
            raise Exception("Something went wrong getting the access token: %s" % response['status'])

        access_dict = dict(urlparse.parse_qsl(content))
        self.config["ACCESS_KEY"], self.config["ACCESS_SECRET"] = access_dict['oauth_token'], access_dict['oauth_token_secret']
        self.access_token = oauth.Token(self.config["ACCESS_KEY"], self.config["ACCESS_SECRET"])
        self.user()

    def _request(self, methodname, params={}, method='GET', success=HTTP_OK):
        MAX_ATTEMPTS = 5
        self.log("Accessing: " + methodname)
        client  = oauth.Client(self.consumer, self.access_token)
        body = urllib.urlencode(params)
        headers = {'content-type': 'application/x-www-form-urlencoded'}
        url = SITE + '/' + methodname

        try_again = True
        time.sleep(1)
        attempt_count = 0
        while try_again and attempt_count < MAX_ATTEMPTS:
            resp, content = client.request(url, method, body, headers)
            if resp['status'] != HTTP_BAD_GATEWAY:
                try_again = False
            else:
                time.sleep(1)
                attempt_count += 1
                self.log("Accessing: " + methodname + " failed. Trying again: " + attempt_count)

        if attempt_count >= MAX_ATTEMPTS:
            self.log("Giving up on %s after %d attempts." % (url, MAX_ATTEMPTS))


        if resp['status'] != success:
            if resp['status'] == HTTP_NOT_FOUND:
                raise Exception("URL: \"%s\" not found. %s" % (url, params))
            else:
                raise Exception('Did not get expected HTTP status: %s' % resp['status'])

        return content

    def user(self):
        response = self._request("api/auth_user")
        xml = ET.fromstring(response)
        user = xml.find("user")
        self._user_id, user_name = int(user.get("id")), user.findtext("name")
        return self._user_id, user_name

    def _cached_user_id(self):
        if not self._user_id:
            self.user()
        return self._user_id

    def search(self, query, shelf, page=1):
        params = {
            "v":2,
            "shelf": shelf,
            "key": self.config["DEVELOPER_KEY"],
            "page": page,
            "per_page": 200
        }

        if query:
            params["search[query]"] = query

        results = []

        #We may need to load multiple pages of reponse we only get a max of 200 books per page
        load_next_page = True
        while load_next_page:
            response = self._request("review/list/%d.xml" % self._cached_user_id(), params)

            xml = ET.fromstring(response)
            reviews = xml.findall("reviews/review")
            if reviews:
                for review in reviews:
                    if any([s.get("name") == shelf for s in review.findall("shelves/shelf")]):
                        results.append((
                            int(review.findtext("book/id")),
                            review.findtext("book/title"),
                            review.findtext("book/authors/author/name")
                        ))
                params["page"] += 1
                self.log("Grabbing page %d" % params["page"])
            else:
                load_next_page = False
        return results

    def listbooks(self, shelf):
        return self.search(None, shelf)

    def add_to_shelf(self, shelf, book_id):
        params = {
            "name": shelf,
            "book_id": book_id
        }
        self._request("shelf/add_to_shelf.xml", params, 'POST', HTTP_CREATED)

    def remove_from_shelf(self, shelf, book_id):
        params = {
            "name": shelf,
            "book_id": book_id,
            "a": "remove"
        }
        self._request("shelf/add_to_shelf.xml", params, method='POST')

    def checkout(self, book_id):
        self.add_to_shelf(self.checkedout_shelf, book_id)
        self.remove_from_shelf(self.checkedin_shelf, book_id)

    def checkin(self, book_id):
        self.add_to_shelf(self.checkedin_shelf, book_id)
        self.remove_from_shelf(self.checkedout_shelf, book_id)

    def shelves(self):
        params = {"key":self.config["DEVELOPER_KEY"], "user_id":self._cached_user_id()}
        xml = ET.fromstring(self._request("shelf/list.xml", params))
        return [name.text for name in xml.findall("shelves/user_shelf/name")]

    def add_shelf(self, name):
        return self._request("user_shelves.xml", {"user_shelf[name]": name}, 'POST')

if __name__ == '__main__':
    pass
