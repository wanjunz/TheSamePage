from flask import Flask, flash, redirect, render_template, request, session, jsonify
# libraries for API requests and search 
import requests
from urllib.parse import quote
# libraries for session management and password hashing (for login / register)
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
# library to get time
from datetime import datetime
#library for database management
import sqlite3

app = Flask(__name__)

# Configure session 
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Executes sql command with ? arguments 
# needCommit True if editing table values
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
def default():
    if session.get("user_id") is None:
        return render_template('login.html')
    # get username and lists for names of books user is reading / has read
    username = executeSQL("SELECT username FROM users WHERE id = ?", (session["user_id"],), False)[0][0]
    booksinProg = executeSQL("SELECT title, author, chapters.forum_id, thumbnail, pageCount FROM chapters JOIN homeBooks ON homeBooks.forum_id = chapters.forum_id WHERE homeBooks.status = 'PROG' AND user_id = ?", (session["user_id"],),False)
    booksRead = executeSQL("SELECT title, author, chapters.forum_id, thumbnail, pageCount FROM chapters JOIN homeBooks ON homeBooks.forum_id = chapters.forum_id WHERE homeBooks.status = 'READ' AND user_id = ?", (session["user_id"],),False)
    # create list of pairs of book information and corresponding comments for each list
    progComments = []
    readComments = []
    #for book in booksinProg:
    #    progComments.append((book, executeSQL("SELECT * FROM forums WHERE forum_id = ?", (book[2],), False)))
    #for book in booksRead:
    #    readComments.append((book, executeSQL("SELECT * FROM forums WHERE forum_id = ?", (book[2],), False)))
    
    #return render_template("forum.html", title=row[0], authors=row[1], thumbnail=row[3], forumID = row[2], comments = comments, pageCount = row[4])

    return render_template('home.html', username = username)

@app.route('/contributions', methods=['GET'])
def contributions():
    user_id = session["user_id"]
    username = executeSQL("SELECT username FROM users WHERE id = ?", (user_id,), False)[0][0]
    # TODO is it dangerous that we are calling their comments via their username rather than user_id? also, can they change the username in insepct to see other users' comments?
    user_comments = executeSQL("SELECT * FROM forums WHERE username = ?", (username,), False)
    
    # combine user's comments and the book info associated into comments_info
    comments_info = []
    for comment in user_comments:
        book_id = comment[4]
        book_info = executeSQL("SELECT * FROM chapters WHERE forum_id = ?", (book_id,), False)
        # book_row is a list like: [('Title', 'Author')]
        if book_info:
            title = book_info[0][0]
            author = book_info[0][1]
        else:
            title = None
            author = None

        comments_info.append({"username":comment[0], "comment":comment[1], "date":comment[3], "percent":comment[5] ,"title":title, "author":author})
    print(comments_info)
    return render_template("contributions.html", comments_info = comments_info)

@app.route('/search', methods=['POST', 'GET'])
def search():
    return render_template("search.html")

@app.route("/api/search")
def apisearch():
    
    q = request.args.get("q")
    # intitle: restricts search to book titles only
    q_strict = f'intitle:"{q}"'

    # if no query, return empty list
    if not q:
        return jsonify([])

    # Call Google Books API
    # quote makes the query handle spaces and special characters
    url = f"https://www.googleapis.com/books/v1/volumes?q={quote(q_strict)}&maxResults=10"
    data = requests.get(url).json()

    books = []
    if "items" in data:
        for item in data["items"][:10]:  # limit results to 10
            info = item.get("volumeInfo", {})
            # check if book cover exists, then add relevant info into books list
            if 'volumeInfo' in item and 'imageLinks' in item['volumeInfo']:
                books.append({
                    "title": info.get("title", "No title"),
                    "authors": info.get("authors", []),
                    "thumbnail": info.get("imageLinks", {}).get("thumbnail"),
                    "pageCount": info.get("pageCount", 0)
                })
            # if no cover, don't add thumbnail key
            else:
                books.append({
                    "title": info.get("title", "No title"),
                    "authors": info.get("authors", []),
                    "pageCount": info.get("pageCount", 0)
                })
    return jsonify(books)

@app.route('/forum', methods=['POST', 'GET'])
def forum():
    if request.method == 'GET':
        return render_template("forum.html")
    title = request.form.get("title")   # book title passed from search.html
    authors = request.form.get("authors") # book authors passed from search.html
    thumbnail = request.form.get("thumbnail") # book thumbnail passed from search.html
    pageCount = request.form.get("pageCount") # book page count passed from search.html

    if not thumbnail: # set image to cover not found image
        thumbnail = "../static/no-cover.jpg"
    # if not in table then add it
    row = executeSQL("SELECT * FROM chapters WHERE title = ? AND author = ? AND thumbnail = ? AND pageCount = ?", (title, authors, thumbnail, pageCount), False)
    if len(row)!=1:
        executeSQL("INSERT INTO chapters (title, author, thumbnail, pageCount) VALUES (?, ?, ?, ?)", (title, authors, thumbnail, pageCount), True)
        row = executeSQL("SELECT * FROM chapters WHERE title = ? AND author = ? AND thumbnail = ? AND pageCount = ?", (title, authors, thumbnail, pageCount), False)[0]
    
    # get comments for specific book
    comments = executeSQL("SELECT * FROM forums WHERE forum_id = ?", (row[2],), False)
    return render_template("forum.html", title=row[0], authors=row[1], thumbnail=row[3], forumID = row[2], comments = comments, pageCount = row[4])

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

@app.route("/comment", methods = ["POST"])
def comment():
    # adds user comment to database and then shows page with it on
    if request.method == "POST":
        parent_id = request.form.get("parent_id")
        # not a reply to a comment
        forum_id = request.form.get("forum_id")

        # parent_id refers to the parent reply. If empty, then it's a regular comment, not a reply to a comment
        if not parent_id:
            forumIDArray = executeSQL("SELECT * FROM chapters WHERE forum_id = ?", (forum_id,),False)
            # if invalid forum_id, return home
            if len(forumIDArray)!=1:
                return redirect("/")
            
            user_id = session["user_id"]
            username = executeSQL("SELECT username FROM users WHERE id = ?", (user_id,), False)[0][0]
            time = datetime.now().strftime("%m/%d/%Y, %H:%M")

            # retrieve info from 'upload comment' button in forum.html
            comment = request.form.get("comment")
            title = request.form.get("title")
            authors = request.form.get("authors")
            thumbnail = request.form.get("thumbnail")
            page = request.form.get("page")
            pageCount = request.form.get("pageCount")

            # general comment, no page inputted
            if not page:
                percent = 'N/A'
                executeSQL("INSERT INTO forums(username, comment, time, forum_id, percent) VALUES (?,?,?,?, ?)", (username, comment, time, forum_id, percent), True)
                comments = executeSQL("SELECT * FROM forums WHERE forum_id = ?", (forum_id,), False)
                
                # return corresponding forum.html 
                return render_template("forum.html", title=title, authors=authors, thumbnail=thumbnail, forumID = forum_id, comments = comments, perecnt=percent)
            # comment with page progress inputted
            else:
                # caclulate percent read
                page = float(page)
                pageCount = float(pageCount)
                percent = str(round(page * 100/pageCount))

                executeSQL("INSERT INTO forums(username, comment, time, forum_id, percent) VALUES (?,?,?,?,?)", (username, comment, time, forum_id, percent), True)   
                comments = executeSQL("SELECT * FROM forums WHERE forum_id = ?", (forum_id,), False)
                
                # return corresponding forum.html 
                return render_template("forum.html", title=title, authors=authors, thumbnail=thumbnail, forumID = forum_id, comments = comments)
