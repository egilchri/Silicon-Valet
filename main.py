import siliconvalet_globals
import cgi
from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import urlfetch

import gdata.auth
import gdata.docs.service
import gdata.calendar.service
import gdata.alt.appengine

# new ted start test
import datetime, time
from google.appengine.ext import db
import logging
import atom.token_store
import gdata.alt.appengine
import re
import pickle


SIG_METHOD = gdata.auth.OAuthSignatureMethod.HMAC_SHA1


if (siliconvalet_globals.FEED_TYPE == 'docs'):
  client = gdata.docs.service.DocsService(source='Botcast Network-TropoTedo-v1')
  SCOPE = 'http://docs.google.com/feeds/'
else:
  client = gdata.calendar.service.CalendarService(source='Botcast Network-TropoTedo-v1')
  SCOPE = "http://www.google.com/calendar/feeds/"

client.SetOAuthInputParameters(SIG_METHOD, siliconvalet_globals.CONSUMER_KEY, consumer_secret=siliconvalet_globals.CONSUMER_SECRET)
gdata.alt.appengine.run_on_appengine(client)


class PhoneTokenStore (gdata.alt.appengine.AppEngineTokenStore):
    """Here's one of our main OAuth tricks, to adopt OAuth for the phone.
The issue is, we can\'t assume, like regular OAuth does, that the user
is logged in to the browser, in their Google account"""
    def find_token(self, url, user):
      if url is None:
        return None
      if isinstance(url, (str, unicode)):
        url = atom.url.parse_url(url)
      tokens = self.load_the_auth_tokens(user)
      # tokens = gdata.alt.appengine.TokenCollection.all()
      #tokens = gdata.alt.appengine.load_ze_auth_tokens (user)
      # real_user = users.get_current_user()
      # my_explode (user, "user")
      # my_explode (real_user, "real_user")

      # tokens = gdata.alt.appengine.load_auth_tokens ()
      for token in tokens:
        logging.info ("That be a token: %s " % token)
      logging.info ("Ok, I loaded some tokens: %s" % tokens)
      if url in tokens:
        logging.info ("This looks like a good one")
        token = tokens[url]
        if token.valid_for_scope(url):
          logging.info ("You got yourself a valid token")
          return token
        else:
          logging.info ("You dont got yourself a valid token")
          del tokens[url]
          save_auth_tokens(tokens)
      for scope, token in tokens.iteritems():
        if token.valid_for_scope(url):
          logging.info ("cool, this looks like a good token")
          return token
      return atom.http_interface.GenericToken()

    def load_the_auth_tokens(self, user):
      # user_tokens = gdata.alt.appengine.TokenCollection.all().filter('user =', user).get()
      # user = "egilchri"
      tmp = gdata.alt.appengine.TokenCollection.all().filter('user =', user)
      logging.info ("tmp: %s " % tmp)
      user_tokens = tmp.get()
      logging.info ("user_tokens: %s " % user_tokens)
      if user_tokens:
        logging.info ("Gonna return the pickle load of the tokens")
        return pickle.loads(user_tokens.pickled_tokens)
      return {}

    def load_the_auth_tokensNo(self, user):
      user_tokens = gdata.alt.appengine.TokenCollection.all().filter('user =', user).get()
      logging.info ("user_tokens: %s " % user_tokens)
      if user_tokens:
        return pickle.loads(user_tokens.pickled_tokens)
      return {}


class PhoneAuth(webapp.RequestHandler):
  """The Tropo app calls into this class, to get the retrieved Google data.
The tricky part is we have to use OAuth to authorize the user.
"""
  def get(self):
    logging.info ("Doing a GET in PhoneAuth");
    # The cellnumber is how we know who's calling
    cellnumber  = self.request.get('cellnumber')
    logging.info ("cellnumber: %s" % cellnumber)

    # We use the cellnumber to lookup the user
    user = self.get_user_from_cell (cellnumber)
    logging.info ("user: %s" % user)
    store = PhoneTokenStore()
    logging.info ("user: %s" % user)
    # Convert user to the proper data structure for what follows
    user_obj = users.User(user)

    # This is where we lookup the user's token.
    # with our specialized find_token method
    access_token =  store.find_token(SCOPE, user_obj )

    # should hava a token by now
    if access_token is None:
      logging.info ("Dang! My access token is None")
    else:
      logging.info ("Thank gosh I got a dad blasted access token!")

    logging.info ("Wait for it")
    if (1):
      # We stuff the token in the client object
      # I guess this is the Valet grabbing the key off the rack
      # and sticking it in his pocket.
      client.current_token = access_token
      client.cellnumber = cellnumber
      client.user = user
#      client.SetOAuthToken(access_token)
      if (0):
        self.response.out.write('''
        <form action="/fetch_data" method="post">
        <input type="submit" value="Get My Documents">
        </form>
        ''')
#   
      else:
        # Ok, we're all authorized, so let's fetch the user's data
        self.redirect('/fetch_data')

  def get_user_from_cell (self, cellnumber):
    """The CellUser db object associates users with cellnumbers"""
    users =  CellUser.all().filter('cellnumber =', cellnumber)
    user = users[0].id
    return user

class MyTokenStore(atom.token_store.TokenStore):
  """This is where I store the token in a db table, for later use.
"""
  def add_token(self, token):
    """Adds a new token to the store (replaces tokens with the same scope)."""
    logging.info ("Storing the old token")
    atom.token_store.TokenStore.add_token (self, token)
    

class CellUser(db.Model):
  """Basic info about the user. timezone is so we know which day it is,
locally.
"""
  id = db.StringProperty(required=True)
  cellnumber = db.StringProperty(required=False)
  timezone = db.StringProperty(required=False)
  oauth_token = db.StringProperty(required=False)

class Hello(webapp.RequestHandler):
  """Introductory greetings to our user. After the initial signup, 
the user won't have any need to come back here again. (Although later,
we should write some code to let the user edit their profile, etc.)
"""
  def get(self):
    logging.info ("Doing a GET in Hello");
    self.response.headers['Content-Type'] = 'text/html'
    self.response.out.write( """
<html>
<head>
<style type="text/css">
.different-text-color { color: blue; }
.centered {text-align: center; }
.left_justify {text-align: left; }
</style>
</head>
<body>
<img class="left_justify" src="%s/images/valet_smaller.jpg"/> <img  src="%s/images/key.jpg"/> 
<h1 class="centered">Welcome to <span class="different-text-color">Silicon Valet</span></h1>
<p class="centered">Home of the Talking Google Calendar!</p>

<ul>
<li> It's like when you park your car and you give the valet a special key that can't open the trunk.
<li> You'll give our valet your cell phone number, so you'll be recognized when you return for your calendar data.
<li> We'll also want to know your time zone. (Today in New York could be yesterday in Sydney.)
<li> During signup, you'll get to a screen where you'll be asked to authorize access to your calendar. This is where you hand over the valet key. 

<li> Look Ma, no passwords!
</ul>
<li> <a href="/register">Click this link to begin the signup process.</a>

</ul>

<p>
<img src="http://code.google.com/appengine/images/appengine-silver-120x30.gif"
alt="Powered by Google App Engine" />
<br/>
<img src="%s/images/poweredbyvoxeo-120.jpg"
alt="Powered by Voxeo" />

""" % (siliconvalet_globals.BASE_URL, siliconvalet_globals.BASE_URL, siliconvalet_globals.BASE_URL))




class Register(webapp.RequestHandler):
  """During registration, the user will need to login to our App. It's
part of the initial OAuth dance.
"""
  def get(self):
    logging.info ("Doing a GET in Register");
    if not users.get_current_user():
      self.redirect(users.create_login_url("/"))
    else:
      #self.redirect("http://www.google.com")
      self.redirect(users.create_logout_url(self.request.uri))

class MobileInstruct(webapp.RequestHandler):
  """A few instructions to give, after the initial signup.
"""
  def get(self):
    logging.info ("Doing a GET in MobileInstruct");
    self.response.headers['Content-Type'] = 'text/html'
    self.response.out.write( """
<html>
<body>
<h1><img src="%s/images/valet_smaller.jpg"/>Silicon Valet is at your service</h1> 

<p>
From now on, to access your calendar data, just dial <strong>(412)-927-0489</strong>.
""" % (siliconvalet_globals.BASE_URL))




class MainPage(webapp.RequestHandler):

  def get(self):
    logging.info ("Doing a GET in MainPage");
    if not users.get_current_user():
      self.redirect(users.create_login_url(self.request.uri))

    cellnumber = self.request.get('cellnumber')
    my_zone = self.request.get('my_zone')
    logging.info ("Cellnumber: %s" % cellnumber)

    action = None
    access_token = client.token_store.find_token(SCOPE)

    if not cellnumber:
      # ted start
      logging.info ("mighty empty Cellnumber: %s" % cellnumber)
      self.print_form()
      logging.info ("just printed form")
      # ted end
    else:
      logging.info ("mighty fine Cellnumber: %s" % cellnumber)
      # new guess
      client.cellnumber = cellnumber

    if isinstance(access_token, gdata.auth.OAuthToken):
      action = '/fetch_data'

    else:
      action = '/get_oauth_token'

    logging.info ("Will be postin get my documents, cellnumber: %s my_zone: %s action: %s" % (cellnumber, my_zone, action))
    me = users.get_current_user()
    logging.info ("me: %s" % me)
    id = me.email()
    logging.info ("id: %s" % id)
    if (id and cellnumber and my_zone):

      # New: delete old users with this cellnumber
      q = db.GqlQuery("SELECT * FROM CellUser WHERE cellnumber = :1", cellnumber)

      results = q.fetch(10)
      for result in results:
        id = result.id
        logging.info ("Deleting %s -> %s " % (id, cellnumber))
        result.delete()
      user = CellUser(cellnumber= cellnumber,
                  timezone = my_zone,
                  id = id
                  ) 
      user.put()

    if cellnumber:
      self.response.out.write("""
        <p>Think of it as you lending us your valet key <img src="%s/images/key_smaller.jpg"/>, until further notice.
        <form action="%s" method="post">
        <input type="submit" value="Save my token">
        <input type="hidden" name="cellnumber" id="cellnumber" value="%s" />
        <input type="hidden" name="my_zone" id="my_zone" value="%s" />
        </form>
        """ % (siliconvalet_globals.BASE_URL, action, cellnumber, my_zone))

#    self.response.headers['Content-Type'] = 'text/html'

  def print_form(self):
    logging.info ("trying to print the form")
    my_zone = self.request.get('my_zone')
    cellnumber = self.request.get('cellnumber')
    sess_token = self.request.get('sess_token')
    auth_token = self.request.get('auth_token')
    if (my_zone and cellnumber):
      # session_token = client.token_store.find_token(self.request.uri)
      # session_token_as_string = session_token.to_string()
      pass
    now = datetime.datetime.now()
    # -1200 -  +1300

    self.response.out.write("""<div id="wrap"><div id="header">
<h1><img src="%s/images/valet_smaller.jpg"/>Silicon Valet</h1>

    <h3>But first, a bit about your space time coordinates</h3>

    <form action="/" method="get">
    <ul>
    <li> Cell: <input type="text" name="cellnumber" id="cellnumber" onkeyup="AcceptDigits(this)" />

    <li> Select your current time: <SELECT NAME=my_zone onChange=setParam()>
          """ % (siliconvalet_globals.BASE_URL))
          
    for i in range (-12, 13):
      nowtime = datetime.datetime.now() + datetime.timedelta(hours= i)
      # prettytime = time.strftime ("%s at %I:%M %p", nowtime)
      prettytime = nowtime.ctime()
      # prettytime = """%s:%s""" % (nowtime.hour, nowtime.minute)
      self.response.out.write("""<option value=\"%s\"> %s """ % (i, prettytime))
    self.response.out.write("""
    </SELECT>
    </ul>
<input type="submit" value="Squirrel away this data"></input>
</form>
</body>""")



class GetOAuthToken(webapp.RequestHandler):

 # GET /get_oauth_token: Called coming back from the OAuth approval page.
 # e.g. the oauth_callback url.
 def get(self):
   logging.info ("Doing a GET in GetOAuthToken");
   my_zone = self.request.get('my_zone')
   cellnumber = self.request.get('cellnumber')
   logging.info ("did a GET in get_oauth_token, cellnumber: %s my_zone: %s" % (cellnumber, my_zone))
   oauth_token = gdata.auth.OAuthTokenFromUrl(self.request.uri)
   if oauth_token:
     oauth_token.secret = cgi.escape(self.request.get('oauth_token_secret'))
     oauth_token.oauth_input_params = gdata.auth.OAuthInputParams(
         SIG_METHOD, siliconvalet_globals.CONSUMER_KEY, consumer_secret=siliconvalet_globals.CONSUMER_SECRET)
     client.SetOAuthToken(oauth_token)

     # 3. Exchange the authorized request token for an access token
     client.UpgradeToOAuthAccessToken()

   access_token = client.token_store.find_token(SCOPE)

   if access_token and users.get_current_user():
     #client.token_store.add_token(access_token)
     store = MyTokenStore()
     logging.info ("Just about to store the token in my very own store: cell: %s zone: %s" % (cellnumber, my_zone))
     store.add_token (access_token)
  
     # ted wacky stuff
      # ted wacky stuff
   elif access_token:
     client.current_token = access_token
     client.SetOAuthToken(access_token)

   # self.redirect('/')
   self.redirect('/mobile_instruct')
  
 # POST /get_oauth_token: Call to fetch an initial request token.
 def post(self):
   user = users.get_current_user()
   if user:
     # 1. Fetch a request token
     req_token = client.FetchOAuthRequestToken()
     client.SetOAuthToken(req_token)

     # For HMAC, persist the token secret in order to create an OAuthToken 
     # object coming back from the approval page.
     next_url = '%s?oauth_token_secret=%s' % (self.request.uri, req_token.secret)
     approval_page_url = client.GenerateOAuthAuthorizationURL(callback_url=next_url)
     
     # 2. Redirect to user to the OAuth approval page
     self.redirect(approval_page_url)


class FetchData(webapp.RequestHandler):
  def post(self):
    if (1):
      self.response.headers['Content-Type'] = 'text/html'
    else:
      self.response.headers['Content-Type'] = 'text/xml'

    # Fetch the user's data
    if (siliconvalet_globals.FEED_TYPE == 'docs'):
      feed = client.GetDocumentListFeed()
    elif (siliconvalet_globals.FEED_TYPE == 'one_day_calendar'):
      feed = self.GetOneDayCalendar(client)
    else:
      feed = client.GetCalendarEventFeed()
      
    self.response.out.write(feed)

  def get(self):
    logging.info ("Doing a GET in FetchDate");
    self.response.headers['Content-Type'] = 'text/xml'

    # Fetch the user's data
    if (siliconvalet_globals.FEED_TYPE == 'docs'):
      feed = client.GetDocumentListFeed()
    elif (siliconvalet_globals.FEED_TYPE == 'one_day_calendar'):
      for i in range (1,15):
        feed = self.GetOneDayCalendar(client)
        if feed:
          break
    else:
      # Allow for it to fail a bunch of times
      for i in range (1,15):
        feed = client.GetCalendarEventFeed()
        if feed:
          break
    self.response.out.write(feed)

  def GetOneDayCalendar(self, client):
    cellnumber = client.cellnumber
    celluser = self.get_celluser_from_cellnumber(cellnumber)
    id = celluser.id
    my_zone = celluser.timezone
    logging.info ("my_zone1: %s " % my_zone)
    if (not my_zone):
      my_zone = 0
    my_zone = int(my_zone)
    logging.info ("my_zone2: %s " % my_zone)
    # my_zone = my_zone - 3
    now = datetime.datetime.now() + datetime.timedelta(hours= my_zone)
    zone = now.tzinfo 
    if (my_zone < 0):
      neg_zone = 0 - my_zone
      logging.info ("neg_zone: %s " % neg_zone)
      today = str (datetime.date.today() - datetime.timedelta(hours=neg_zone))
    else:
      today = str (datetime.date.today() + datetime.timedelta(hours=my_zone))
    tomorrow = str (datetime.date.today() + datetime.timedelta(days=1))
    yesterday = str (datetime.date.today() - datetime.timedelta(days=1))
    my_params = {}

    query = gdata.calendar.service.CalendarEventQuery('default', 'private', 'full', params={'orderby':'starttime', 'sortorder': 'ascending'})
    #query.orderby = "starttime" 
    real_startx = self.time_zone(my_zone)
    real_endx = self.time_zone(my_zone + 24)
    startx = self.time_zone(my_zone - 12)
    endx = self.time_zone(my_zone + 48)
    logging.info ("startx: %s endx: %s" % (startx, endx))
    query.start_min = startx
    query.start_max = endx
    query.ctz='America/New_York'
    feed = client.CalendarQuery(query)
    logging.info ("feed: %s" % feed)
    # return feed
    result = ""
    #for i, an_event in enumerate(feed.entry):
    counter = 0
    for an_event in feed.entry:
      title = an_event.title.text
      logging.info ("Here is a title: %s" % title)
      counter += 1
    if (counter == 0):
      result = "You don't have any events today. What. Ever."
      return result

    # result = "Your start time is %s" % startx
    for an_event in feed.entry:
      title = an_event.title.text
      when_count = 0
      for a_when in an_event.when:
        when_count += 1
        #print '\t\tStart time: %s' % (a_when.start_time,)
        start = a_when.start_time
        if ((start < real_startx) or (start > real_endx)):
          logging.info ("That time just is not right: %s : %s : %s :%s" % (title, start, real_startx, real_endx))
          break
        else:
          logging.info ("That time is looking good: %s : %s " % (title, start))
        #  continue
        logging.info ("starttime: %s whencount: %s" % (start, when_count))
        start = start.split(".")[0]
        try:
          start = time.strptime(start, "%Y-%m-%dT%H:%M:%S") 
        except:
          logging.info ("Don do me this way: %s" % start)
          result = "%s\nYou have an all day event called: %s." % (result, title)
          good_time = False
          break
        
        # hour = start.hour
        end = a_when.end_time
        end = end.split(".")[0]
        end = time.strptime(end, "%Y-%m-%dT%H:%M:%S") 
        start_hour = start.tm_hour
        start_min = start.tm_min
        end_hour = end.tm_hour
        end_min = end.tm_min

        if (start_min == 0):
          start_min = ""
        elif (start_min > 30):
          start_min = "%s minutes before" % (60 - start_min)
          start_hour += 1
        else:
          start_min = "%s minutes after" % start_min

        end_min = end.tm_min
        if (end_min == 0):
          end_min = ""
        elif (end_min > 30):
          end_min = "%s minutes before" % (60 - end_min)
          end_hour += 1
        else:
          end_min = "%s minutes after" % end_min

        if (start_hour > 12):
          start_hour = "%s pm" % (start_hour -12)
        else:
          start_hour = "%s am" % start_hour
        end_hour = end.tm_hour
        if (end_hour > 12):
          end_hour = "%s pm" % (end_hour -12)
        else:
          end_hour = "%s am" % end_hour

        result = "%s\nOn %s %s from %s %s to %s %s you have %s ?" % (result, start.tm_mon, start.tm_mday, start_min, start_hour, end_min, end_hour, title)
      # We are through getting one event
    return result

  def time_zone( self, offset = 0 ): # DEFAULT = GMT
    new = time.gmtime( time.time() + offset*60*60 )

# from web
# start_time = time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime())
    #return "%s-%02d-%02d" % (new[0],new[1],new[2])
    return "%s-%02d-%02dT%02d:%02d:%02d" % (new[0],new[1],new[2], 0,0,0)
    # return "Day: %s | Month: %s | Year: %s\n%s:%s:%s"%(new[2],new[1],new[0],new[3],new[4],new[5])


  def get_celluser_from_cellnumber(self, cellnumber):
    users =  CellUser.all().filter('cellnumber =', cellnumber)
    user = users[0]
    return user

class FakeTropo(webapp.RequestHandler):
  """The purpose of this class is to test code running in the Tropo class.
At least we can do some basic syntax checking.
  """
  def get(self):
    if (0):
      self.response.out.write("I am really truly not a calendar entry")
      return
    logging.info ("Doing a GET in FakeTropo");
    cellnumber = self.request.get('cellnumber')
    p = re.compile( 'http://\S+')
    if (1):
          self.response.out.write("""
<html>
<head></head>
<body>
<pre>
""")

    hello_url = "%s/googlephone.py?cellnumber=%s" % (siliconvalet_globals.BASE_URL, cellnumber)
    # hello_url = """/googlephone.py?cellnumber=%s" % cellnumber
    logging.info ("hello_url: %s" % hello_url)
    if (1):
      write = self.response.out.write
      for i in range (1,15):
        data = urlfetch.fetch(hello_url)
        content = data.content
        if content:
          break
      if (0):
        xml = minidom.parseString( content )
        stats = xml.getElementsByTagName("status")
        for stat in stats:
          textNode = (stat.getElementsByTagName("text")[0])
          user = (stat.getElementsByTagName("user")[0])
          usernNode = (user.getElementsByTagName("screen_name")[0])
          text = self.getText(textNode.childNodes)
          text = p.subn ('tiny url', text)
          name = self.getText(usernNode.childNodes)
          write ("name: %s \ntext: %s \n" % (name, text))
      logging.info ("data: " + content)
      write("""%s""" % content)
      if (1):
        self.response.out.write("""
</pre></body></html>
""")

  def getText(self, nodelist):
    rc = ""

    for node in nodelist:
      if node.nodeType == node.TEXT_NODE:
        rc = rc + node.data
    return rc




class Tropo(webapp.RequestHandler):
  """This is the class for our Tropo application. Since the GET method,
below, simply spits out Python code, I've found it convenient to create 
a corresponding class called FakeTropo, where it is easier to do basic
debugging, especially syntax checking.
"""
  def get(self):
    """This is the code the gets run when the user first calls up Tropo.It's job
is to spit out a valid Python script. Inside the Python script are special
calls to Tropo functions that perform key telephony operations.

"""
    logging.info ("Doing a GET in Tropo");
    if (0):
          self.response.out.write("""
<html>
<head></head>
<body>
<pre>
""")
    self.response.out.write("""import urllib2
from xml.dom import minidom, Node
import re

def getText(nodelist):
# This function does some basic text filtering
  dollars = re.compile( '\$\S+')
  rc = ""
  for node in nodelist:
     if node.nodeType == node.TEXT_NODE:
            rc = rc + node.data
  rc = dollars.sub ('many dollars', rc)            
  rc = rc.replace ('&', 'and')
  rc = rc.replace ('\"', '')
  return rc

p = re.compile( 'http://\S+')

answer()
s_log_prefix = "Log: "
cid = currentCall.callerID
wait (100)
say("Howdy")
# Sometimes we have to spell things funny to get them pronounced
# the way we like.
say( "Welcome to Silicon Vah Lay" )
s_xml_speak_start ="<?xml version='1.0'?><speak>"
s_say_as_speak_end = "</say-as></speak>"


#phone:
s_phone_say_as = "<say-as interpret-as='vxml:phone'>"

s_prompt = s_xml_speak_start + s_phone_say_as + cid + s_say_as_speak_end

hello_url = '%s/googlephone.py?cellnumber=' + cid
for i in range (1,15):
   urlRead  = urllib2.urlopen(hello_url)
   content = urlRead.read()
   if content:
      break
   wait(500)
log ("ze content: " + content)
   
prompt (content)
say("That's totally all.")
say( "Like." )
wait (100)
say( "Bye bye." )

hangup()


""" % (siliconvalet_globals.BASE_URL))
    if (0):
          self.response.out.write("""
</pre></body></html>
""")


def my_explode(str, label):
  logging.info ("Exploding %s" % label)
  for char in str:
    logging.info ("Char: %s" % char)

def event_sort(x, y):
  """This is how we sort the events by start time. I haven't figured 
out how to do that in the Gdata API.
"""
  logging.info ("event_sort %s %s" % (x, y))
  xtitle = x.title.text
  ytitle = y.title.text
  x_when =  x.when[0]
  y_when =  y.when[0]
  x_start = x_when.start_time
  y_start = y_when.start_time
  if (x_start > y_start):
    logging.info ("%s is greater than %s" % (xtitle, ytitle))
    return 1
  logging.info ("%s is greater than %s" % (ytitle, xtitle))
  return 0


def main():
  application = webapp.WSGIApplication([('/', MainPage),
                                        ('/register', Register),
                                        ('/hello', Hello),
                                        ('/mobile_instruct', MobileInstruct),
                                        ('/googlephone.py', PhoneAuth),
                                        ('/tropo.py', Tropo),
                                        ('/fake_tropo.py', FakeTropo),
                                        ('/get_oauth_token', GetOAuthToken),
                                        ('/fetch_data', FetchData)], debug=True)
  run_wsgi_app(application)

#comment
if __name__ == "__main__":
  main()
