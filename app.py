from flask import Flask
import os

app = Flask(__name__)

@app.route("/")
def home():
    return "Hello, World! This is my first server."



if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # שימוש בפורט מ-Render או 5000 כברירת מחדל
    app.run(host="0.0.0.0", port=port, debug=True)