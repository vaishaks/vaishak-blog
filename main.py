import webapp2
import os
import jinja2
from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape=True)

class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)
    
    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)
    
    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

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
        
class Post(db.Model):
    subject = db.StringProperty(required=True)
    content = db.TextProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    last_modified = db.DateTimeProperty(auto_now=True)
    
    def render(self):
        self._render_text = self.content.replace('\n', '<br>')
        return render_str("post.html", p = self)


app = webapp2.WSGIApplication([('/', MainPage),
                               ('/blog', BlogHandler),
                               ('/blog/newpost', NewPost),
                               ('/blog/([0-9]+)', PostHandler)],
                              debug=True)
