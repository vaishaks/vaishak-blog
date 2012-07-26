import webapp2
import os
import jinja2
import re
import hashlib
import hmac
import random
import string
from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape=True)

secret ="fire"

class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
    
    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)
    
    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))
        
    def set_secure_cookie(self, name, val):
        secure_val = make_secure_val(val)
        self.response.headers.add_header('Set-Cookie', '%s=%s Path=/' % (name, secure_val))

    def read_secure_cookie(self, name):
        secure_cookie_val = self.request.cookies.get(name)
        if secure_cookie_val:
            cookie_val = check_secure_val(secure_cookie_val)
            if cookie_val:
                return cookie_val

class MainPage(Handler):   
    def get(self):
        self.render("main.html")

class BlogHandler(Handler):
    def get(self):
        posts = db.GqlQuery("SELECT * FROM Post ORDER BY created DESC LIMIT 10")
        self.render("posts.html", posts=posts)

class NewPost(Handler):
    def get(self):
        self.render("newpost.html")
  
    def post(self):
        subject = self.request.get('subject')
        content = self.request.get('content')
        if subject and content:
            a = Post(subject=subject, content=content)
            a.put()
            x = str(a.key().id())
            self.redirect('/blog/%s' %x)
        else:
            error = "Please enter both the subject and title of the blog post!"
            self.render("newpost.html", error=error)

class PostHandler(Handler):
    def get(self, post_id):
        p = Post.get_by_id(int(post_id))
        if p:
            self.render("post.html", p=p)
        else:
            self.render("404.html")

class Signup(Handler):
    def get(self):
        self.render("signup.html")
        
    def post(self):
        user_username = self.request.get('username')
        user_password = self.request.get('password')
        user_verify = self.request.get('verify')
        user_email = self.request.get('email')
        username_error = ""
        password_error = ""
        verify_error = ""
        email_error = ""
        flag = 0
        if not valid_username(user_username):
            username_error = "This is not a valid Username."
            flag = 1
        if not valid_password(user_password):
            password_error = "This is not a valid password."
            flag = 1
        if user_password != user_verify:
            verify_error = "The password don't match."
            flag = 1
        if not valid_email(user_email):
            if user_email != "":
                email_error = "This not a valid Email Address."
                flag = 1
        if flag == 1:
            self.render("signup.html", username_error=username_error, password_error=password_error, verify_error=verify_error, email_error=email_error)
        elif User.by_name(user_username):
            username_error = "Sorry, this username is already taken."
            self.render("signup.html", username_error=username_error)
        else:
            self.register(user_username, user_password, user_email)
            
    def register(self, username, password, email=""):
        u = User.Register(username, password, email)
        u.put()
        self.set_secure_cookie("user_id", str(u.key().id()))
        self.redirect('/welcome')

class WelcomeHandler(Handler):
    def get(self):
        user_id = self.read_secure_cookie("user_id")
        u = User.by_id(int(user_id))
        self.response.out.write("Welcome, " + u.username)

class Post(db.Model):
    subject = db.StringProperty(required=True)
    content = db.TextProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    last_modified = db.DateTimeProperty(auto_now=True)
    

class User(db.Model):
    username = db.StringProperty(required=True)
    password = db.StringProperty(required=True)
    email = db.StringProperty()
    
    @classmethod
    def Register(cls, username, password, email=""):
        pw_hash = make_pw_hash(username,password)
        return User(username=username, password=pw_hash, email=email)
    
    @classmethod
    def by_name(cls,username):
        #u = User.all().filter('username =', username).get()
        u = db.GqlQuery("SELECT * FROM User WHERE username = :username", username=username).get()
        return u
    
    @classmethod
    def by_id(cls, user_id):
        return User.get_by_id(user_id)
    
USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
    return USER_RE.match(username)

PASS_RE = re.compile(r"^.{3,20}$")
def valid_password(password):
    return PASS_RE.match(password)

EMAIL_RE = re.compile(r"^[\S]+@[\S]+\.[\S]+$")
def valid_email(email):
    return EMAIL_RE.match(email)

def make_salt():
    return "".join(random.choice(string.ascii_lowercase) for x in xrange(5))

def make_pw_hash(username, password, salt=None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(username+password+salt).hexdigest()
    return h+",%s" %salt

def valid_pw(username, password, h):
    s = h.split(',')
    H = make_pw_hash(username, password, s[1])
    return h == H

def hash_str(s):
    return hmac.new(secret, s).hexdigest()

def make_secure_val(s):
    h = hash_str(s)
    return s+"|%s" %h

def check_secure_val(h):
    s = h.split('|')
    H = make_secure_val(s[0])
    if h == H:
        return s[0]

app = webapp2.WSGIApplication([('/', MainPage),
                               ('/blog', BlogHandler),
                               ('/blog/newpost', NewPost),
                               ('/blog/([0-9]+)', PostHandler),
                               ('/blog/signup', Signup),
                               ('/welcome', WelcomeHandler)],
                              debug=True)
