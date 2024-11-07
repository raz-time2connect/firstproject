from flask import Flask, render_template, request, redirect, url_for, jsonify
import requests
import json
import os

app = Flask(__name__)

FORMS_FILE = "forms.json"

# טען את הטפסים מקובץ JSON
def load_forms():
    if os.path.exists(FORMS_FILE):
        with open(FORMS_FILE, "r") as file:
            return json.load(file)
    return {}

# שמור את הטפסים לקובץ JSON
def save_forms(forms):
    with open(FORMS_FILE, "w") as file:
        json.dump(forms, file, indent=4)

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/manage_forms")
def manage_forms():
    forms = load_forms()
    return render_template("manage_forms.html", forms=forms)

@app.route("/create_form", methods=["GET", "POST"])
def create_form():
    if request.method == "POST":
        form_name = request.form.get("form_name")
        webhook_url = request.form.get("webhook_url")

        fields = [
            {
                "name": field_name,
                "id": field_name.strip().lower().replace(" ", "_"),
                "type": field_type
            }
            for field_name, field_type in zip(
                request.form.getlist("field_name"), request.form.getlist("field_type")
            )
        ]

        forms = load_forms()
        forms[form_name] = {"webhook_url": webhook_url, "fields": fields}
        save_forms(forms)

        return redirect(url_for("manage_forms"))
    return render_template("create_form.html")

@app.route("/delete_form/<form_name>", methods=["POST"])
def delete_form(form_name):
    forms = load_forms()
    if form_name in forms:
        del forms[form_name]
        save_forms(forms)
    return redirect(url_for("manage_forms"))
@app.route("/form/<form_name>", methods=["GET", "POST"])
def form(form_name):
    forms = load_forms()  # טוען את כל הטפסים מ-forms.json
    form_data = forms.get(form_name)  # מקבל את פרטי הטופס הנוכחי

    if not form_data:
        return "Form not found", 404  # אם הטופס לא קיים, החזר 404

    if request.method == "POST":
        # איסוף הנתונים שהוזנו בטופס
        data = {field["id"]: request.form.get(field["id"]) for field in form_data["fields"]}
        print(f"Data received: {data}")

        # שליחת הנתונים ל-Webhook
        response = requests.post(form_data["webhook_url"], json=data)
        if response.ok:
            return jsonify({"status": "success", "message": "Data sent successfully!"}), 200
        else:
            return jsonify({"status": "error", "message": "Failed to send data"}), 500

    # הוספת form_data ל-render_template
    return render_template(
        "form.html",
        form_name=form_name,
        fields=form_data["fields"],
        form_data=form_data  # הוספת form_data לתבנית
    )

@app.route("/edit_form/<form_name>", methods=["GET", "POST"])
def edit_form(form_name):
    forms = load_forms()  # טוען את כל הטפסים
    form_data = forms.get(form_name)  # שולף את הטופס לעריכה

    if not form_data:
        return "Form not found", 404

    if request.method == "POST":
        # עדכון שם הטופס (אם שונה)
        new_form_name = request.form.get("form_name")
        webhook_url = request.form.get("webhook_url")
        fields = [
            {"name": field_name, "id": field_name.strip().lower().replace(" ", "_"), "type": field_type}
            for field_name, field_type in zip(
                request.form.getlist("field_name"), request.form.getlist("field_type")
            )
        ]

        # מחיקת הטופס הישן אם השם שונה
        if form_name != new_form_name:
            del forms[form_name]

        # שמירת הטופס החדש או המעודכן
        forms[new_form_name] = {"webhook_url": webhook_url, "fields": fields}
        save_forms(forms)

        return redirect(url_for("manage_forms"))

    return render_template("edit_form.html", form_name=form_name, form_data=form_data)



if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)