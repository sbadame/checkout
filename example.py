
#snagged from: https://gist.github.com/537923

import oauth2 as oauth
import time
import urlparse

HTTP_OK = '200'
HTTP_CREATED = '201'
site = "http://www.goodreads.com"
request_token_url = "%s/oauth/request_token" % site
authorize_url = "%s/oauth/authorize" % site
access_token_url = "%s/oauth/access_token" % site


def authorize():
    
    response, content = client.request(request_token_url, "GET")

    time.sleep(1)
    if response['status'] != HTTP_CREATED:
        raise Exception("Something wrong with the developer keys or goodreads: " + response['status'])

    request_token = dict(urlparse.parse_qsl(content))
    oauth_token = request_token['oauth_token']
    oauth_token_secret = request_token['oauth_token_secret']
    print("token, secret = %s, %s" % (oauth_token, oauth_token_secret))

    authorize_link = "%s?oauth_token=%s" % (authorize_url, oauth_token)
    print(authorize_link)
    time.sleep(10)
    return oauth.Token(oauth_token, oauth_token_secret)

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

def goodreads(methodname, params={}, method='GET'):
    import urllib
    consumer = oauth.Consumer(key="OWT16QIggdjflRNPeqK8Zg",
                              secret="zeBhib5d7203cRD3PjnsBqbm6Wi6JeoTLIxeWmCwRdY")
    access_token = oauth.Token('D6IfrBjT8Al1yTy4zq0cA', 'J9zvylsVlKN26GTaLDAgLUcjkujN9xMvZsUvm6X4')
    client  = oauth.Client(consumer, access_token)
    body = urllib.urlencode(params)
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    resp, content = client.request(site + '/' + methodname, method, body, headers)

    if resp['status'] != HTTP_OK:
        raise Exception('Non HTTP OK status returned: %s' % resp['status'])

    return content

print(goodreads("api/auth_user"))
#print(goodreads("updates/friends.xml", {}))

#
# Example
#

#print(goodreads("shelf/add_to_shelf.xml", params={'name': 'checkedout', 'book_id':13284343}, method='POST'))
#print(goodreads("api/auth_user", {}))

#print(goodreads("updates/friends.xml", {}))
#print()

