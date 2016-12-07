import os
import re
import string
import random
import hashlib

import jinja2
import webapp2

from google.appengine.ext import db

# Username: "^[a-zA-Z0-9_-]{3,20}$"
# Password: "^.{3,20}$"
# Email: "^[\S]+@[\S]+.[\S]+$"

USER_RE = re.compile("^[a-zA-Z0-9_-]{3,20}$")
PASSWORD_RE = re.compile("^.{3,20}$")
EMAIL_RE = re.compile(r"[\S]+@[\S]+\.[\S]+$")

template_dir = os.path.join(os.path.dirname(__file__), "templates")
jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir),
                                autoescape=True)

class User(db.Model):
    username = db.StringProperty(required=True)
    hashp = db.StringProperty(required=True)
    email = db.EmailProperty()

class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.write(*a, **kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **params):
        self.write(self.render_str(template, **params))

    def check_username(self, username):
        return USER_RE.match(username)

    def check_password(self, password):
        return PASSWORD_RE.match(password)

    def check_email(self, email):
        return EMAIL_RE.match(email)

    def random_salt_str(self):
        return "".join([random.choice(string.letters) for i in range(5)])

    def hash_password(self, s, salt=None):
        salt = salt if(salt) else self.random_salt_str()
        return "%s,%s" %(salt, hashlib.sha1(s+salt).hexdigest())

class RegisterHandler(Handler):
    def get(self):
        user_cookie = self.request.cookies.get("user_id", None)
        if(user_cookie):
            self.redirect("/welcome")
        self.render("signup.html")

    def post(self):
        username = self.request.get("username")
        password = self.request.get("password")
        verify = self.request.get("verify")
        email = self.request.get("email") or None


        valid_username = self.check_username(username)
        valid_password = self.check_password(password)
        valid_verify = password == verify
        valid_email = self.check_email(email) if(email) else True

        if(valid_username and valid_password and valid_verify and valid_email):
            user_exist_flag = User.gql("WHERE username = :username", username=username).count()
            if(user_exist_flag > 0):
                self.render("signup.html", user_exist=True, username=username, email=email)
            else:
                user = User(username=username, hashp=self.hash_password(password),
                            email=email)
                user_key = user.put()
                self.response.headers.add_header("Set-Cookie", "user_id=%s|%s" %(user_key.id(), user.hashp.split(",")[1]))
                self.redirect("/welcome")

        else:
            if(email == None):
                email = ""
            self.render("signup.html", valid_username=valid_username,
                        username=username, valid_password=valid_password,
                        valid_verify=valid_verify, email=email,
                        valid_email=valid_email)

class WelcomeHandler(Handler):
    def get(self):
        user_cookie = self.request.cookies.get("user_id", None)
        if(user_cookie):
            user = User.get_by_id(int(user_cookie.split("|")[0]))
            if(user and user.hashp.split(",")[1] == user_cookie.split("|")[1]):
                self.render("welcome.html", user_id=user.username)
            else:
                self.response.delete_cookie("user_id")
                self.redirect("/signup")
        else:
            self.redirect("/signup")

class LoginHandler(Handler):
    def get(self):
        self.render("login.html")

    def post(self):
        username = self.request.get("username")
        password = self.request.get("password")

        valid_username = self.check_username(username)
        valid_password = self.check_password(password)

        if(valid_username and valid_password):
            user = User.gql("WHERE username = :username", username=username)
            if(user.count() > 0):
                user = user[0]
                user_id = user.key().id()
                salt = user.hashp.split(",")[0]
                if(self.hash_password(password, salt) == user.hashp):
                    self.response.headers.add_header("Set-Cookie", str("user_id=%s|%s" %(user_id, user.hashp.split(",")[1])))
                    self.redirect("/welcome")
                else:
                    self.render("login.html", invalid_login=True, username=username)
            else:
                self.render("login.html", invalid_login=True, username=username)
        else:
            self.render("login.html", invalid_login=True, username=username)

class LogoutHandler(Handler):
    def get(self):
        self.response.delete_cookie("user_id")
        self.redirect("/signup")

app = webapp2.WSGIApplication([
    ("/signup", RegisterHandler),
    ("/welcome", WelcomeHandler),
    ("/login", LoginHandler),
    ("/logout", LogoutHandler)
], debug=True)
