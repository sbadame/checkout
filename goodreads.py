import oauth2 as oauth
import time
import urllib
import urlparse

#PROGRAM CONSTANTS
HTTP_OK = '200'
HTTP_CREATED = '201'

CONFIG_FILE_PATH = "checkout.credentials"

SITE = "http://www.goodreads.com"
REQUEST_TOKEN_URL = "%s/oauth/request_token" % SITE
AUTHORIZE_URL = "%s/oauth/authorize" % SITE
ACCESS_TOKEN_URL = "%s/oauth/access_token" % SITE

#CONSTANTS FROM CONFIG
config = {}
try:
    with open(CONFIG_FILE_PATH) as configfile:
        config.update(eval(configfile.read()))
except IOError as e:
        print("Error loading: %s (%s)" % (CONFIG_FILE_PATH, e))

DEVELOPER_KEY = config["DEVELOPER_KEY"]
DEVELOPER_SECRET = config["DEVELOPER_SECRET"]

consumer = oauth.Consumer(key = DEVELOPER_KEY, secret = DEVELOPER_SECRET)

def authorize():
    client = oauth.Client(consumer)
    response, content = client.request(REQUEST_TOKEN_URL, "GET")
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
    if response['status'] != HTTP_OK:
        raise Exception("Something went wrong getting the access token: %s" % response['status'])

    access_dict = dict(urlparse.parse_qsl(content))
    access_token = access_dict['oauth_token']
    access_secret = access_dict['oauth_secret']
    return oauth.Token(access_token, access_secret)

def goodreads(methodname, params={}, method='GET'):
    consumer = oauth.Consumer(key=DEVELOPER_KEY,
                              secret=DEVELOPER_SECRET)
    access_token = oauth.Token('D6IfrBjT8Al1yTy4zq0cA', 'J9zvylsVlKN26GTaLDAgLUcjkujN9xMvZsUvm6X4')
    client  = oauth.Client(consumer, access_token)
    body = urllib.urlencode(params)
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    resp, content = client.request(site + '/' + methodname, method, body, headers)
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


user_id = 10281211

print(goodreads("review/list", {"format":"xml", "v":2, "id":user_id, "shelf": "checkedout", "key": developer_key}))

#print(goodreads("api/auth_user"))
#print(goodreads("updates/friends.xml", {}))


