import oauth2 as oauth
import time
import urllib
import urlparse
import json

#PROGRAM CONSTANTS
HTTP_OK = '200'
HTTP_CREATED = '201'

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

for item in config.items(): print("%s=%s" % item)

if "DEVELOPER_KEY" not in config:
    config["DEVELOPER_KEY"] = raw_input("No developer key found: What is the app's developer key?")
    config["DEVELOPER_SECRET"] = raw_input("What is the app's developer key secret?")

DEVELOPER_KEY = config["DEVELOPER_KEY"]
DEVELOPER_SECRET = config["DEVELOPER_SECRET"]

consumer = oauth.Consumer(key = DEVELOPER_KEY, secret = DEVELOPER_SECRET)

def get_access():
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
    raw_input("Press enter once authorized.")

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
    config["ACCESS_KEY"], config["ACCESS_SECRET"] = get_access()

ACCESS_KEY = config["ACCESS_KEY"]
ACCESS_SECRET = config["ACCESS_SECRET"]

access_token = oauth.Token(ACCESS_KEY, ACCESS_SECRET)


def goodreads(methodname, params={}, method='GET'):
    consumer = oauth.Consumer(key=DEVELOPER_KEY,
                              secret=DEVELOPER_SECRET)
    client  = oauth.Client(consumer, access_token)
    body = urllib.urlencode(params)
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    resp, content = client.request(SITE + '/' + methodname, method, body, headers)
    if resp['status'] != HTTP_OK:
        raise Exception('Non HTTP OK status returned: %s' % resp['status'])

    return content

#consumer = oauth.Consumer(key="OWT16QIggdjflRNPeqK8Zg",
#                          secret="zeBhib5d7203cRD3PjnsBqbm6Wi6JeoTLIxeWmCwRdY")
#client = oauth.Client(consumer)
#response, content = client.request(request_token_url, "GET")
#if response['status'] != HTTP_OK:
#    raise Exception("Something wrong with the developer keys or goodreads: " + response['status'])
#
#request_token_dict = dict(urlparse.parse_qsl(content))
#request_oauth_token = request_token_dict['oauth_token']
#request_oauth_token_secret = request_token_dict['oauth_token_secret']
#
#authorize_link = "%s?oauth_token=%s" % (authorize_url, request_oauth_token)
#print(authorize_link)
#raw_input("Press enter once authorized")
#
#request_token = oauth.Token(request_oauth_token, request_oauth_token_secret)
#client = oauth.Client(consumer, request_token)
#response, content = client.request(access_token_url, "POST")
#if response['status'] != HTTP_OK:
#    raise Exception("Something wrong getting the access token" + response['status'])
#
#access_token = dict(urlparse.parse_qsl(content))
#access_oauth_token, access_oauth_token_secret = access_token['oauth_token'], access_token['oauth_token_secret']
#print( "access_token = %s\naccess_token_secret = %s" % (access_oauth_token, access_oauth_token_secret) )


if __name__ == '__main__':
    user_id = 10281211

    print(goodreads("review/list", {"format":"xml", "v":2, "id":user_id, "shelf": "checkedout", "key": DEVELOPER_KEY}))

#print(goodreads("api/auth_user"))
#print(goodreads("updates/friends.xml", {}))


