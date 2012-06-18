import oauth2 as oauth
import time
import urlparse
import webbrowser

consumer_key = "OWT16QIggdjflRNPeqK8Zg"
consumer_secret = "zeBhib5d7203cRD3PjnsBqbm6Wi6JeoTLIxeWmCwRdY"

site = "http://www.goodreads.com"
request_token_url = "%s/oauth/request_token/" % site
authorize_url = "%s/oauth/authorize" % site
access_token_url = "%s/oauth/access_token" % site

consumer = oauth.Consumer(consumer_key, consumer_secret)
client = oauth.Client(consumer)
resp, content = client.request(request_token_url, "GET")

time.sleep(2)
print("1 Response %s." % resp['status'])

request_token = dict(urlparse.parse_qsl(content))
print("oauth_token  = %s" % request_token['oauth_token'])
print("oauth_token_secret = %s" % request_token['oauth_token_secret'])

authorize_url = "%s?oauth_token=%s" % (authorize_url, request_token['oauth_token'])
webbrowser.open(authorize_url)
time.sleep(10)

token = oauth.Token(request_token['oauth_token'], request_token['oauth_token_secret'])

#
# Example
#

import urllib

client  = oauth.Client(consumer, token)
body = urllib.urlencode({'name': 'checkedout', 'book_id':13284343})
headers = {'content-type': 'application/x-www-form-urlencoded'}
resp, content = client.request('%s/shelf/add_to_shelf.xml' % site, 'POST', body, headers)

if resp['status'] != '201':
    raise Exception('Cannot create resource: %s' % response['status'])
else:
    print 'Book added'
