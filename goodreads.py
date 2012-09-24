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
    def __init__(self, dev_key=None, dev_secret=None, waitfunction=DEFAULT_WAIT, log=NOOP_LOG):
        self.log = log
        self.dev_key = dev_key
        self.consumer = oauth.Consumer(key = dev_key, secret = dev_secret)
        self.access_token = self.authenticate(waitfunction)
        self._user_id, self.user_name = self.user()

    def authenticate(self, waitfunction=DEFAULT_WAIT):
        """ Grabs a new set of keys from goodreads.
            Opens the authorization link in a new browser window.
            Calls the waitfunction() once the browser is opened. 
            The waitfunction should return only when the user has authorized the app"""
        self.log("Authenticating")

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
            # This happens if we're not authenticated (ie, the user doesn't load the URL for the token)
            raise Exception("Something went wrong getting the access token: %s" % response['status'])

        access_dict = dict(urlparse.parse_qsl(content))
        token = oauth.Token(access_dict['oauth_token'], access_dict['oauth_token_secret'])
        return token

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
                self.log("Accessing: " + methodname + " failed. Trying again: " + str(attempt_count))

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
        return int(user.get("id")), user.findtext("name")

    def _cached_user_id(self):
        if not self._user_id:
            self.user()
        return self._user_id

    def search(self, query, *shelves):
        results = []

        for shelf in shelves:
            page = 1
            params = {
                "v":2,
                "shelf": shelf,
                "key": self.dev_key,
                "page": page,
                "per_page": 200
            }

            if query:
                params["search[query]"] = query

            #We may need to load multiple pages of reponse we only get a max of 200 books per page
            load_next_page = True
            while load_next_page:
                response = self._request("review/list/%d.xml" % self._cached_user_id(), params)

                try:
                    xml = ET.fromstring(response)
                except ET.ParseError:
                    time.sleep(1)
                    self.log("Got malformed XML, retrying")
                    continue

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

    def listbooks(self, shelf, *shelves):
        books =  self.search(None, shelf)
        for s in shelves:
            books += self.search(None, s)
        return books

    def shelves(self):
        params = {"key":self.dev_key, "user_id":self._cached_user_id()}
        xml = ET.fromstring(self._request("shelf/list.xml", params))
        return [name.text for name in xml.findall("shelves/user_shelf/name")]

    def add_shelf(self, name):
        return self._request("user_shelves.xml", {"user_shelf[name]": name}, 'POST')

if __name__ == '__main__':
    pass
