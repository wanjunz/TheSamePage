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
    # creates database connection
    connection = sqlite3.connect('info.db')
    # creates cursor object to execute commands/get data
    db = connection.cursor()
    # run command with args (safe from SQL injection attacks)
    db.execute(command, args)
    # gets rows from resulting query as a list
    val = db.fetchall()
    # saves changes to database if data was edited
    if needCommit:
        connection.commit()
    # closes connection to database
    connection.close()
    return val

# checks if a volumeID is valid (in API) and if it is, inserts the book's data into chapters table
def checkVolumeID(volumeID):
    # no volume ID inputted
    if not volumeID:
        return False
    
    # Confirm the volume ID exists in Google Books
    url = f"https://www.googleapis.com/books/v1/volumes/{volumeID}"
    data = requests.get(url).json()

    if "error" in data:
        return False
    
    # Extract book information if volumeID is valid
    info = data.get("volumeInfo", {})
    title = info.get("title", "Unknown Title")
    authors_list = info.get("authors", "Unknown") 
    authors = ", ".join(authors_list)
    pageCount = int(info.get("pageCount", "1"))
    thumbnail = info.get("imageLinks", {}).get("thumbnail", '')
    
    # set image to cover not found image if none in database
    if not thumbnail:
        thumbnail = "/static/no-cover.jpg"
    
    # if book not in table, then add it
    row = executeSQL("SELECT * FROM chapters WHERE forum_id = ?", (volumeID,), False)
    if len(row)!=1:
        executeSQL("INSERT INTO chapters (title, author, forum_id, thumbnail, pageCount) VALUES (?, ?, ?, ?, ?)", (title, authors, volumeID, thumbnail, pageCount), True)
        row = executeSQL("SELECT * FROM chapters WHERE forum_id = ?", (volumeID,), False)[0]
    else:
        row = row[0]
    
    return row
    

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
    volumeID = request.form.get("volumeID") # book volumeID passed from search.html
    # if volumeID is valid and 
    if checkVolumeID(volumeID) is not False:
        # if not already in homeBooks, insert book into homeBooks as one of currently readings
        inHomeBooks = executeSQL("SELECT * FROM homeBooks WHERE forum_id = ? AND user_id = ?", (volumeID, session["user_id"]), False)
        if len(inHomeBooks)!=1:
            executeSQL("INSERT INTO homeBooks (forum_id, user_id, status) VALUES (?, ?, ?)", (volumeID, session["user_id"], "TBR"), True)
    return redirect("/")

# remove book from user's home page
@app.route('/deleteBook', methods = ['POST'])
def removeBook():
    forum_id = request.form.get("forum_id")
    # forum_id not blank
    if not(not forum_id):
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
    # forum_id not blank
    if not(not forum_id):
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
    # forum_id not blank
    if not(not forum_id):
        # check if forum_id, user_id pair exists in homeBooks table as PROG
        row = executeSQL("SELECT * FROM homeBooks WHERE forum_id = ? AND user_id = ? AND status = 'PROG'", (forum_id, session["user_id"]), False)
        # if exists, update to DONE
        if len(row)==1:
            executeSQL("UPDATE homeBooks SET status = 'DONE' WHERE forum_id = ? AND user_id = ?", (forum_id, session["user_id"]), True)
    return redirect("/")

@app.route('/contributions', methods=['GET'])
def contributions():
    username = executeSQL("SELECT username FROM users WHERE id = ?", (session["user_id"],), False)[0][0]
    user_comments = executeSQL("SELECT * FROM forums WHERE user_id = ? ORDER BY time DESC", (session["user_id"],), False)
 
    # combine user's comments and the book info associated into comments_info
    comments_info = []
    for comment in user_comments:
        book_info = executeSQL("SELECT * FROM chapters WHERE forum_id = ?", (comment[4],), False)
        # get comment current comment is replying to if applicable
        if comment[2] is not None:
            parentComment = executeSQL("SELECT comment FROM forums WHERE comment_id = ?", (comment[2],), False)[0][0]
        else:
            parentComment = None
        comments_info.append({"username":username, "comment_id": comment[6], "comment":comment[1], "date":comment[3], "percent":comment[5] ,"title":book_info[0][0], "author":book_info[0][1], "parentComment": parentComment})
    return render_template("contributions.html", comments_info = comments_info)

# get search page
@app.route('/search', methods=['GET'])
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
                    "pageCount": info.get("pageCount", 1), #if no page count, set to 1 to avoid division by 0 later
                    "volumeID": item.get("id")
                })
            # if no cover, don't add thumbnail key
            else:
                books.append({
                    "title": info.get("title", "No title"),
                    "authors": info.get("authors", []),
                    "pageCount": info.get("pageCount", 1),
                    "volumeID": item.get("id")
                })
    return jsonify(books)

# opens forum from home page or search page button
@app.route('/forum', methods=['POST', 'GET'])
def forum():
    volumeID = request.args.get("volumeID") # passed from forum.html when user filters
    if volumeID is None: 
        volumeID = request.form.get("volumeID") # passed from search.html or from comments being posted
    # verify volumeID hasn't been tampered with
    row = checkVolumeID(volumeID)
    print("row:", row)
    if row == False:
        return redirect("/")

    pageCount = int(row[4])
    # Compute filter percentage
    print("pageCount:", pageCount)
    page_filter = request.args.get("page_filter")  # user-entered page number
    if page_filter and page_filter.isdigit():
        page_filter = int(page_filter)
        filter_percent = int((page_filter / pageCount) * 100)
    else:
        filter_percent = None
    print("filter_percent:", filter_percent)
    # RETRIEVE FILTERED COMMENTS 
    if filter_percent is not None:
        comments = executeSQL(
            "SELECT username, comment, parent_id, time, forum_id, percentage, comment_id "
            "FROM forums JOIN users ON users.id = forums.user_id "
            "WHERE forum_id = ? AND percentage <= ? AND comment != '[deleted comment]'"
            "ORDER BY time DESC",
            (volumeID, filter_percent),
            False
        )
    else:
        comments = executeSQL(
            "SELECT username, comment, parent_id, time, forum_id, percentage, comment_id "
            "FROM forums JOIN users ON users.id = forums.user_id "
            "WHERE forum_id = ? AND comment != '[deleted comment]'"
            "ORDER BY time DESC",
            (volumeID,),
            False
        )
    commentReplyPairs = []
    for comment in comments:
        if comment[2] is not None:
            parentComment = executeSQL("SELECT comment FROM forums WHERE comment_id = ?", (comment[2],), False)[0][0]
        else:
            parentComment = None
        commentReplyPairs.append((comment, parentComment))
    return render_template("forum.html", title=row[0], authors=row[1], thumbnail=row[3], forumID = volumeID, comments = commentReplyPairs, pageCount = pageCount, filter_percent = filter_percent)

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
    # open register page
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
        forum_id = request.form.get("volumeID")

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
                pageCount = float(forumIDArray[4])
                # caclulate percent read iff page is a number between 0 and pageCount (inclusive)
                if not(page.isdigit() and float(page) <= pageCount):
                    return forum()
                page = float(page)
                percent = str(round(page * 100/pageCount))        
            executeSQL("INSERT INTO forums(user_id, comment, time, forum_id, percentage) VALUES (?,?,?,?,?)", (session["user_id"], comment, time, forum_id, percent), True)   

        # reply to a comment
        else: 
            # check if hidden data tampered with
            parentComment = executeSQL("SELECT * FROM forums WHERE comment_id = ? AND forum_id = ?", (parent_id, forum_id), False)
            if len(parentComment)!=1:
                return redirect("/")
            parentComment=parentComment[0]
            # if parentid, forumid pair exist then add reply into forums table
            executeSQL("INSERT INTO forums(user_id, comment, parent_id, time, forum_id, percentage) VALUES(?, ?, ?, ?, ?, ?)", (session["user_id"], comment, parent_id, time, forum_id, parentComment[5]),True)
        # open corresponding forum
        return forum()

# Delete comments
@app.route("/deleteContribution", methods = ["POST"])
def deleteContribution():
    comment_id = request.form.get("comment_id")
    # Check if the comment exists first for the user, then update the value
    row = executeSQL("SELECT * FROM forums WHERE comment_id = ? AND user_id = ?", (comment_id,session["user_id"]), False)  
    if len(row)==1:
        executeSQL("UPDATE forums SET comment = '[deleted comment]' WHERE comment_id = ?", (comment_id,), True)
    return redirect("/contributions")