from flask import Flask, render_template, request, session
from flask_session import Session

app = Flask(__name__)

# Configure session 
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

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

@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'GET':
        return render_template("login.html")
    

if __name__ == '__main__':
    app.run(debug = True, host = "0.0.0.0", port = 3000)