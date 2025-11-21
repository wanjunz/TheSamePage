from flask import Flask, render_template, request

app = Flask(__name__)


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/contributions', methods=['POST'])
def contributions():
    
    return render_template("contributions.html")

@app.route('/search', methods=['POST'])
def search():
    
    return render_template("search.html")


if __name__ == '__main__':
    app.run(debug = True, host = "0.0.0.0", port = 3000)