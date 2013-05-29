import oauth2

REQUEST_TOKEN_URL = 'https://coinbase.com/oauth/token'
AUTHORIZATION_URL = 'https://coinbase.com/oauth/authorize'
ACCESS_TOKEN_URL = 'https://coinbase.com/oauth/token'
CONSUMER_KEY = 'be86ed1c5cb9a057893c3c68d0f9345a2a3c0459f7fac79eb5c15502e72235eb'
CONSUMER_SECRET = 'b0b977b925d47ce866837a6038454ac70ac6d323670c65606484e362408556ef'

consumer = oauth2.Consumer(CONSUMER_KEY, CONSUMER_SECRET)
client = oauth2.Client(consumer)
resp, content = client.request(REQUEST_TOKEN_URL, "GET")

request_token = dict(urlparse.parse_qsl(content))
print "Request Token:"
print "    - oauth_token        = %s" % request_token['oauth_token']
print "    - oauth_token_secret = %s" % request_token['oauth_token_secret']
print "Go to the following link in your browser:"
print "%s?oauth_token=%s" % (AUTHORIZATION_URL, request_token['oauth_token'])

# After the user has granted access to you, the consumer, the provider will
# redirect you to whatever URL you have told them to redirect to. You can 
# usually define this in the oauth_callback argument as well.
oauth_verifier = raw_input('What is the PIN? ')
token = oauth2.Token(request_token['oauth_token'], request_token['oauth_token_secret'])
token.set_verifier(oauth_verifier)
client = oauth2.Client(consumer, token)

resp, content = client.request(ACCESS_TOKEN_URL, "POST")
access_token = dict(urlparse.parse_qsl(content))

print "Access Token:"
print "    - oauth_token        = %s" % access_token['oauth_token']
print "    - oauth_token_secret = %s" % access_token['oauth_token_secret']
print