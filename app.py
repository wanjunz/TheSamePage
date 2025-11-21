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

@app.route('/search', methods=['POST'])
def search():
    
    return render_template("search.html")

@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'GET':
        return render_template("login.html")
    

if __name__ == '__main__':
    app.run(debug = True, host = "0.0.0.0", port = 3000)