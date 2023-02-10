"""
Proprietary Information of Big Investment Bank Co.
"""

from flask import Flask, request, make_response, redirect
from redis import Redis
from pickle import loads, dumps
import sys
from base64 import b64encode, b64decode

app = Flask(__name__)


def dump(obj):
    return b64encode(dumps(obj))


def load(obj):
    return loads(b64decode(obj))


def db_get(key):
    client = Redis()
    v = client.get(key)
    if v != None:
        return load(v)
    else:
        return None


def db_set(key, value):
    serialized = dump(value)
    client = Redis()
    client.set(key, serialized)


def db_has(key):
    client = Redis()
    return client.has(key)


class Account():
    def __init__(self, username, password, description):
        self.username = username
        self.password = password
        self.description = description

        self.coins = 0

    def save(self):
        db_set("account_" + self.username, self)

    def render_html(self):
        pass

    def validate_password(self, password):
        return self.password == password


class Session():
    def __init__(self, account: Account):
        self.account_name = account.username

    def account(self):
        return db_get("account_" + self.account_name)

    def valid(self):
        return True


@app.route("/login")
def login():
    username = request.args.get("username")
    password = request.args.get("password")

    account = db_get("account_" + username)
    if account == None:
        return "<html><body>Invalid Login <a href=\"/\">Home</a></body></html>"

    if not account.validate_password(password):
        return "<html><body>Invalid Password <a href=\"/\">Home</a></body></html>"

    resp = redirect("/")

    resp.set_cookie("login", dump(Session(account)))

    return resp


@app.route("/logout")
def logout():
    resp = redirect("/")

    resp.set_cookie("login", "")

    return resp


@app.route("/register")
def register():
    username = request.args.get("username")
    password = request.args.get("password")

    if username == "" or password == "":
        return "<html><body>No username or password <a href=\"/\">Home</a></body></html>"

    account = db_get("account_" + username)
    if account != None:
        return "<html><body>User already exists <a href=\"/\">Home</a></body></html>"

    # Register the new account.
    acc = Account(username, password, "")

    acc.save()

    resp = redirect("/")

    resp.set_cookie("login", dump(Session(acc)))

    return resp


def get_session():
    login_cookie = request.cookies.get("login", None)

    if login_cookie != None and login_cookie != "":
        session = load(login_cookie)

        if not session.valid():
            return None

        return session
    else:
        return None


@app.route("/accounts")
def accounts():
    session = get_session()
    if session == None:
        return redirect("/")

    resp = ""
    client = Redis()
    for key in client.scan_iter("account_*"):
        resp += f"<pre>{key}</pre><br />\n"
    return resp


@app.route("/mint")
def mint():
    session = get_session()
    if session == None:
        return redirect("/")

    acc = session.account()

    acc.coins += 100

    acc.save()

    return redirect("/")


@app.route("/transfer")
def transfer():
    session = get_session()
    if session == None:
        return redirect("/")

    return f"""<html>
<body>
<h1>Transfer</h1>

<div>You current have {session.account().coins} Coins.</div>

<form action="/do_transfer">
<input type="text" name="send_to" placeholder="Send To">
<input type="text" name="amount" placeholder="amount">
<button type="submit">Submit</button>
</form>
</body>
</html>"""


@app.route("/change_description")
def change_description():
    session = get_session()
    if session == None:
        return redirect("/")

    acc = session.account()

    acc.description = request.args.get("description")

    acc.save()

    return redirect("/")


@app.route("/do_transfer")
def do_transfer():
    session = get_session()
    if session == None:
        return redirect("/")

    send_to = request.args.get("send_to")
    amount = int(request.args.get("amount"))

    mine = session.account()

    if mine.coins < amount:
        return "<html><body>Not Enough Coins <a href=\"/\">Home</a></body></html>"

    other = db_get("account_" + send_to)

    if other == None:
        return "<html><body>Other account does not exist <a href=\"/\">Home</a></body></html>"

    mine.coins -= amount
    other.coins += amount

    mine.save()
    other.save()

    return "<html><body>Transfer Complete <a href=\"/\">Home</a></body></html>"


@app.route("/")
def home():
    session = get_session()
    if session != None:
        acc = session.account()

        return f"""<html>
<body>

<h1>Welcome {acc.username}</h1>

<div><a href="/logout">Logout</a></div>

<form action="/change_description">
<textarea name="description">{acc.description}</textarea>
<button type="submit">Submit</button>
</form>

<div>You current have {acc.coins} Coins.</div>

<div><a href="/accounts">Accounts</a></div>
<div><a href="/mint">Mint</a></div>
<div><a href="/transfer">Transfer</a></div>

</body>
</html>"""
    else:
        return """<html>

<body>
<h1>Bank Python - Welcome</h1>

<a href="/logout">Logout</a>

<form action="/login">
<input type="text" name="username" placeholder="Username">
<input type="password" name="password" placeholder="Password">
<button type="submit">Submit</button>
</form>

<form action="/register">
<input type="text" name="username" placeholder="Username">
<input type="password" name="password" placeholder="Password">
<button type="submit">Register</button>
</form>
</body>

</html>"""
