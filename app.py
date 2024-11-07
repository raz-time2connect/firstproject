from flask import Flask, render_template, request, jsonify
import os
import requests

app = Flask(__name__)

# עמוד הבית
@app.route('/')
def home():
    return render_template('home.html')

# עמוד הטופס
@app.route('/form', methods=['GET', 'POST'])
def form():
    if request.method == 'POST':
        # קבלת הנתונים מהטופס
        name = request.form.get('name')
        email = request.form.get('email')
        # עיבוד הנתונים (לדוגמה, שמירה למסד נתונים או שליחה לוובהוק)
        print(f"Name: {name}, Email: {email}")
        return jsonify({"status": "success", "message": "Form submitted successfully!"})
    return render_template('form.html')


@app.route('/submit', methods=['POST'])
def submit():
    data = request.form.to_dict()
    print(f"Received data: {data}")

    webhook_url = "https://your-webhook-url.com"  # החלף בכתובת שלך
    response = requests.post(webhook_url, json=data)

    if response.ok:
        return jsonify({"status": "success", "message": "Data sent to webhook"}), 200
    else:
        return jsonify({"status": "error", "message": "Failed to send data"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)