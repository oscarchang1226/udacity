import os

import jinja2
import webapp2

from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__), "templates")
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),
                                autoescape=True)

class Entry(db.Model):
    subject = db.StringProperty(required=True)
    content = db.TextProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)


class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.write(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **params):
        self.write(self.render_str(template, **params))

class RootHandler(Handler):
    def get(self):
        entries = db.GqlQuery("SELECT * FROM Entry ORDER BY created desc")
        self.render("front.html", entries=entries)

class NewPostHandler(Handler):
    def get(self):
        self.render("form.html")

    def post(self):
        subject = self.request.get("subject")
        content = self.request.get("content")

        if(subject and content):
            entry = Entry(subject=subject, content=content)
            entry_key = entry.put()

            self.redirect("/blog/%s" % entry_key.id())
        else:
            error = "Both subject and content is required."
            self.render("form.html", subject=subject, content=content,
                        error=error)

class EntryHandler(Handler):
    def get(self, entry_id):
        entry = Entry.get_by_id(int(entry_id))
        self.render("entry.html", entry=entry)

app = webapp2.WSGIApplication([
    ("/blog", RootHandler),
    ("/blog/newpost", NewPostHandler),
    ("/blog/(\d+)", EntryHandler)
], debug=True)
