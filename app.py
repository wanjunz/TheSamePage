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

# TODO: check if book with given information exists in google books API
def inAPI(title, authors, thumbnail, pageCount):
    return True

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route('/')
def default():
    # home page is login page if not logged in
    if session.get("user_id") is None:
        return render_template('login.html')
    # get username and lists for names of books TBR/in progress/done
    username = executeSQL("SELECT username FROM users WHERE id = ?", (session["user_id"],), False)[0][0]
    booksTBR = executeSQL("SELECT title, author, chapters.forum_id, thumbnail FROM chapters JOIN homeBooks ON homeBooks.forum_id = chapters.forum_id WHERE homeBooks.status = 'TBR' AND user_id = ?", (session["user_id"],),False)
    booksinProg = executeSQL("SELECT title, author, chapters.forum_id, thumbnail FROM chapters JOIN homeBooks ON homeBooks.forum_id = chapters.forum_id WHERE homeBooks.status = 'PROG' AND user_id = ?", (session["user_id"],),False)
    booksDone = executeSQL("SELECT title, author, chapters.forum_id, thumbnail FROM chapters JOIN homeBooks ON homeBooks.forum_id = chapters.forum_id WHERE homeBooks.status = 'DONE' AND user_id = ?", (session["user_id"],),False)
    return render_template('home.html', username = username, booksinProg = booksinProg, booksDone = booksDone, booksTBR = booksTBR)

# add book into user's TBR in home page from search page
@app.route('/add', methods=['POST'])
def addBook():
    title = request.form.get("title")   # book title passed from search.html
    authors = request.form.get("authors") # book authors passed from search.html
    thumbnail = request.form.get("thumbnail") # book thumbnail passed from search.html
    pageCount = request.form.get("pageCount") # book page count passed from search.html
    
    # get corresponding book's forum id
    row = executeSQL("SELECT * FROM chapters WHERE title = ? AND author = ? AND thumbnail = ? AND pageCount = ?", (title, authors, thumbnail, pageCount), False)
    if len(row)!=1:
        executeSQL("INSERT INTO chapters (title, author, thumbnail, pageCount) VALUES (?, ?, ?, ?)", (title, authors, thumbnail, pageCount), True)
        row = executeSQL("SELECT * FROM chapters WHERE title = ? AND author = ? AND thumbnail = ? AND pageCount = ?", (title, authors, thumbnail, pageCount), False)[0]
    else:
        row = row[0]

    # if not already in homeBooks, insert book into homeBooks as one of currently readings
    inHomeBooks = executeSQL("SELECT * FROM homeBooks WHERE forum_id = ? AND user_id = ?", (row[2], session["user_id"]), False)
    if len(inHomeBooks)!=1:
        executeSQL("INSERT INTO homeBooks (forum_id, user_id, status) VALUES (?, ?, ?)", (row[2], session["user_id"], "TBR"), True)
    return redirect("/")

# remove book from user's home page
@app.route('/deleteBook', methods = ['POST'])
def removeBook():
    forum_id = request.form.get("forum_id")
    # TODO: is it possible to have one of the hidden values be empty --> may need to account in remaining methods
    if not forum_id:
        return redirect("/")
    # check if forum_id, user_id pair exists in homeBooks table
    row = executeSQL("SELECT * FROM homeBooks WHERE forum_id = ? AND user_id = ?", (forum_id, session["user_id"]), False)
    # if exists, remove book
    if len(row)==1:
        executeSQL("DELETE FROM homeBooks WHERE forum_id = ? AND user_id = ?", (forum_id, session["user_id"]), True)
    return redirect("/")

# mark TBR book as currently reading on user's home page
@app.route('/readBook', methods = ['POST'])
def markAsReading():
    forum_id = request.form.get("forum_id")
    if not forum_id:
        return redirect("/")
    # check if forum_id, user_id pair exists in homeBooks table as TBR
    row = executeSQL("SELECT * FROM homeBooks WHERE forum_id = ? AND user_id = ? AND status = 'TBR'", (forum_id, session["user_id"]), False)
    # if exists, update to PROG
    if len(row)==1:
        executeSQL("UPDATE homeBooks SET status = 'PROG' WHERE forum_id = ? AND user_id = ?", (forum_id, session["user_id"]), True)
    return redirect("/")

# mark PROG book as done on user's home page
@app.route('/finishBook', methods = ['POST'])
def markAsDone():
    forum_id = request.form.get("forum_id")
    if not forum_id:
        return redirect("/")
    # check if forum_id, user_id pair exists in homeBooks table as TBR
    row = executeSQL("SELECT * FROM homeBooks WHERE forum_id = ? AND user_id = ? AND status = 'PROG'", (forum_id, session["user_id"]), False)
    # if exists, update to PROG
    if len(row)==1:
        executeSQL("UPDATE homeBooks SET status = 'DONE' WHERE forum_id = ? AND user_id = ?", (forum_id, session["user_id"]), True)
    return redirect("/")

@app.route('/contributions', methods=['GET'])
def contributions():
    user_id = session["user_id"]
    username = executeSQL("SELECT username FROM users WHERE id = ?", (user_id,), False)[0][0]
    user_comments = executeSQL("SELECT * FROM forums WHERE user_id = ? ORDER BY time DESC", (session["user_id"],), False)
 
    # combine user's comments and the book info associated into comments_info
    comments_info = []
    for comment in user_comments:
        book_id = comment[4]
        book_info = executeSQL("SELECT * FROM chapters WHERE forum_id = ?", (book_id,), False)
        # book_info is a list like: [('Title', 'Author')]
        if book_info:
            title = book_info[0][0]
            author = book_info[0][1]
        else:
            title = None
            author = None
        if comment[2] is not None:
            parentComment = executeSQL("SELECT comment FROM forums WHERE comment_id = ?", (comment[2],), False)[0][0]
        else:
            parentComment = None
        comments_info.append({"username":username, "comment":comment[1], "date":comment[3], "percent":comment[5] ,"title":title, "author":author, "parentComment": parentComment})
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
    else:
        row = row[0]
    # get comments for specific book
    comments = executeSQL("SELECT username, comment, parent_id, time, forum_id, percentage, comment_id FROM forums JOIN users ON users.id = forums.user_id WHERE forum_id = ? ORDER BY time DESC", (row[2],), False)
    commentReplyPairs = []
    for comment in comments:
        if comment[2] is not None:
            parentComment = executeSQL("SELECT comment FROM forums WHERE comment_id = ?", (comment[2],), False)[0][0]
        else:
            parentComment = None
        commentReplyPairs.append((comment, parentComment))
    return render_template("forum.html", title=row[0], authors=row[1], thumbnail=row[3], forumID = row[2], comments = commentReplyPairs, pageCount = row[4])

# opens forum from home page buttons
@app.route('/openForum', methods = ['POST'])
def openForum():
    forum_id = request.form.get("forum_id")
    # forum_id blank
    if not forum_id:
        return redirect("/")
    # check forum_id exists in table
    row = executeSQL("SELECT * FROM chapters WHERE forum_id = ?", (forum_id,), False)
    if len(row)!=1:
        return redirect("/")
    else:
        row = row[0]
    # get comments for specific book
    comments = executeSQL("SELECT username, comment, parent_id, time, forum_id, percentage, comment_id FROM forums JOIN users ON users.id = forums.user_id WHERE forum_id = ? ORDER BY time DESC", (row[2],), False)
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
        forum_id = request.form.get("forum_id")

        # retrieve info from 'upload comment' button in forum.html
        comment = request.form.get("comment")

        # if blank comment or forum_id, return home
        if not comment or not forum_id: 
            return redirect("/")

        # if forum info tampered with, return home
        forumIDArray = executeSQL("SELECT * FROM chapters WHERE forum_id = ? ", (forum_id,),False)
        if len(forumIDArray)!=1:
            return redirect("/")
        forumIDArray=forumIDArray[0]
            
        time = datetime.now().strftime("%m/%d/%Y, %H:%M")
        # parent_id refers to the parent reply. If empty, then it's a regular comment, not a reply to a comment
        if not parent_id:
            page = request.form.get("page")

            # general comment, no page inputted
            if not page:
                percent = 'N/A'

            # comment with page progress inputted
            else:
                # caclulate percent read
                page = float(page)
                pageCount = float(forumIDArray[4])
                percent = str(round(page * 100/pageCount))

            executeSQL("INSERT INTO forums(user_id, comment, time, forum_id, percentage) VALUES (?,?,?,?,?)", (session["user_id"], comment, time, forum_id, percent), True)   

        # reply to a comment
        else: 
            # hidden data tampered with
            parentComment = executeSQL("SELECT * FROM forums WHERE comment_id = ? AND forum_id = ?", (parent_id, forum_id), False)
            if len(parentComment)!=1:
                return redirect("/")
            parentComment=parentComment[0]
            executeSQL("INSERT INTO forums(user_id, comment, parent_id, time, forum_id, percentage) VALUES(?, ?, ?, ?, ?, ?)", (session["user_id"], comment, parent_id, time, forum_id, parentComment[5]),True)
        return openForum()
# Delete comments
@app.route("/delete", methods = ["POST"])
def delete():
    comment = request.form.get("comment")
    time = request.form.get("date")
    
    row = executeSQL("SELECT * FROM forums WHERE user_id = ? and comment = ? and time = ?", (session["user_id"], comment, time), False)
    if len(row)==1:
        executeSQL("DELETE FROM forums WHERE user_id = ? and comment = ? and time = ?", (session["user_id"], comment, time), True)

    return redirect("/contributions")