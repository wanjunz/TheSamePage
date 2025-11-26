import sqlite3
from flask import Flask, flash, redirect, render_template, request, session, jsonify
import requests
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)

# Configure session 
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

def executeSQL(command, args, needCommit):
    connection = sqlite3.connect('info.db')
    db = connection.cursor()
    db.execute(command, args)
    val = db.fetchall()
    if needCommit:
        connection.commit()
    connection.close()
    return val
@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/contributions', methods=['POST'])
def contributions():
    
    return render_template("contributions.html")

@app.route('/search', methods=['POST', 'GET'])
def search():
    if request.method == "POST":
        query = request.form.get("query")
        
        # Call Google Books API
        url = f"https://www.googleapis.com/books/v1/volumes?q={query}"
        resp = requests.get(url)
        data = resp.json()

        books = []
        if "items" in data:
            for item in data["items"]:
                info = item.get("volumeInfo", {})
                books.append({
                    "title": info.get("title"),
                    "authors": info.get("authors", []),
                    "thumbnail": info.get("imageLinks", {}).get("thumbnail"),
                    "description": info.get("description")
                })

        return render_template("results.html", books=books, query=query)
    
    return render_template("search.html")

@app.route("/api/search")
def apisearch():
    q = request.args.get("q")

    if not q:
        return jsonify([])

    # Call Google Books API
    url = f"https://www.googleapis.com/books/v1/volumes?q={q}"
    data = requests.get(url).json()

    books = []
    if "items" in data:
        for item in data["items"][:10]:  # limit results like CS50 example
            info = item.get("volumeInfo", {})
            books.append({
                "title": info.get("title", "No title"),
                "authors": info.get("authors", []),
                "thumbnail": info.get("imageLinks", {}).get("thumbnail")
            })

    return jsonify(books)

@app.route('/login', methods=['POST', 'GET'])
def login():
    # log user in
    if request.method == 'GET':
        return render_template("login.html")
    else:
        # forget user_id
        session.clear()

        # Ensure no fields left blank
        if not request.form.get("username") or not request.form.get("password"):
            return render_template("login.html", message = "field left blank")
        
        # Query database for username
        rows = executeSQL("SELECT * FROM users WHERE username = ?", (request.form.get("username"),), False)

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0][2], request.form.get("password")
        ):
            return render_template("login.html", message = "invalid username/password")
        
        # Remember which user has logged in
        session["user_id"] = rows[0][0]

        # Redirect user to home page
        return redirect("/")

@app.route('/register', methods=['POST', 'GET'])
def register():
    # register user
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # render error if one of fields left blank or confirmation not password
        if not username or not password or not confirmation:
            return render_template("register.html", message = "field left blank")
        
        if confirmation != password:
            return render_template("register.html", message = "confirmation doesn't match password")
        
        # attempt to insert username
        try:
            executeSQL("INSERT INTO users (username, hash) VALUES(?, ?)", (username, generate_password_hash(password)), True)
        except:
            return render_template("register.html", message = "username taken")
        return render_template("login.html")
    if request.method == "GET":
        return render_template("register.html")

@app.route("/logout")
def logout():
    # log user out

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")
