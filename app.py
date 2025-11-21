from flask import Flask, jsonify, render_template, request
import requests

app = Flask(__name__)


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


if __name__ == '__main__':
    app.run(debug = True, host = "0.0.0.0", port = 3000)