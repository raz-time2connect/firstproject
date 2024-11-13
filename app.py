from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import requests
import json
import os
import logging
from urllib.parse import urlparse
import threading
import uuid
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)  # For flash messages

FORMS_FILE = "forms.json"
lock = threading.Lock()  # Prevent race conditions with file access


# Helper: Validate URL
def is_valid_url(url):
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme)


# Helper: Generate unique field ID
def generate_field_id(name):
    return f"{name.strip().lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}"


# Load forms from a JSON file
def load_forms():
    try:
        with open(FORMS_FILE, "r") as file:
            data = file.read()
            logging.debug(f"Loaded raw forms data: {data}")
            if not data.strip():  # בדוק אם הקובץ ריק
                logging.warning("forms.json is empty. Initializing empty dictionary.")
                return {}
            loaded_data = json.loads(data)  # טען את התוכן כ-JSON
            logging.debug(f"Parsed forms data: {loaded_data}")
            return loaded_data
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from {FORMS_FILE}: {e}")
        return {}  # מחזיר מילון ריק במקרה של שגיאה
    except FileNotFoundError:
        logging.warning(f"{FORMS_FILE} not found. Initializing empty dictionary.")
        return {}  # מחזיר מילון ריק אם הקובץ לא קיים



# Save forms to a JSON file
def save_forms(forms):
    try:
        logging.debug(f"Saving forms data: {forms}")
        with open(FORMS_FILE, "w") as file:
            json.dump(forms, file, indent=4)
            logging.debug(f"Forms saved successfully to {FORMS_FILE}.")
    except Exception as e:
        logging.error(f"Error saving forms to {FORMS_FILE}: {e}")


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

        # Validate inputs
        if not is_valid_url(webhook_url):
            flash("Invalid Webhook URL. Please provide a valid URL.", "danger")
            return redirect(url_for("create_form"))

        fields = [
            {
                "name": field_name,
                "id": generate_field_id(field_name),
                "type": field_type
            }
            for field_name, field_type in zip(
                request.form.getlist("field_name"), request.form.getlist("field_type")
            )
        ]

        forms = load_forms()
        forms[form_name] = {
            "webhook_url": webhook_url,
            "fields": fields,
            "created_at": datetime.now().isoformat()  # Add creation time
        }
        save_forms(forms)

        flash("Form created successfully!", "success")
        return redirect(url_for("manage_forms"))

    return render_template("create_form.html")



@app.route("/delete_form/<form_name>", methods=["POST"])
def delete_form(form_name):
    forms = load_forms()
    if form_name in forms:
        del forms[form_name]
        save_forms(forms)
        flash("Form deleted successfully!", "success")
    else:
        flash("Form not found.", "danger")
    return redirect(url_for("manage_forms"))


@app.route("/form/<form_name>", methods=["GET", "POST"])
def form(form_name):
    forms = load_forms()
    form_data = forms.get(form_name)

    if not form_data:
        flash("Form not found.", "danger")
        return redirect(url_for("manage_forms"))

    if request.method == "POST":
        # Collect field data
        data = {field["id"]: request.form.get(field["id"]) for field in form_data["fields"]}
        
        # Add submission time
        data["submitted_at"] = datetime.now().isoformat()

        # Adjust URL if necessary
        webhook_url = form_data["webhook_url"]
        if not is_valid_url(webhook_url):
            flash("Invalid Webhook URL.", "danger")
            return redirect(url_for("form", form_name=form_name))

        # Send data to webhook
        headers = {'Content-Type': 'application/json'}
        try:
            response = requests.post(webhook_url, json=data, headers=headers)
            logging.debug(f"Webhook URL: {webhook_url}")
            logging.debug(f"Data to be sent: {data}")
            logging.debug(f"Status Code: {response.status_code}, Response Body: {response.text}")

            if response.ok:
                flash("Form submitted successfully!", "success")
            else:
                flash("Failed to submit the form.", "danger")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error sending data: {e}")
            flash("Network error while submitting the form.", "danger")

    return render_template("form.html", form_name=form_name, fields=form_data["fields"], form_data=form_data)

@app.route("/edit_form/<form_name>", methods=["GET", "POST"])
def edit_form(form_name):
    forms = load_forms()
    form_data = forms.get(form_name)

    if not form_data:
        flash("Form not found.", "danger")
        return redirect(url_for("manage_forms"))

    logging.debug(f"Original form data before editing: {form_data}")

    if request.method == "POST":
        new_form_name = request.form.get("form_name")
        webhook_url = request.form.get("webhook_url")

        # Validate inputs
        if not is_valid_url(webhook_url):
            flash("Invalid Webhook URL. Please provide a valid URL.", "danger")
            return redirect(url_for("edit_form", form_name=form_name))

        fields = [
            {"name": field_name, "id": generate_field_id(field_name), "type": field_type}
            for field_name, field_type in zip(
                request.form.getlist("field_name"), request.form.getlist("field_type")
            )
        ]

        # שמור את created_at אם הוא קיים, אחרת צור אותו מחדש
        created_at = form_data.get("created_at", datetime.now().isoformat())
        
        # עדכן את updated_at בזמן שמירה
        updated_at = datetime.now().isoformat()

        logging.debug(f"Preserved created_at: {created_at}")
        logging.debug(f"New updated_at: {updated_at}")

        # עדכון שם הטופס
        if form_name != new_form_name:
            del forms[form_name]

        # עדכן את הנתונים
        forms[new_form_name] = {
            "webhook_url": webhook_url,
            "fields": fields,
            "created_at": created_at,
            "updated_at": updated_at
        }

        logging.debug(f"Updated form data for {new_form_name}: {forms[new_form_name]}")

        save_forms(forms)

        # בדוק שהשדות נשמרו
        logging.debug(f"Saved forms data after update: {forms}")

        flash("Form updated successfully!", "success")
        return redirect(url_for("manage_forms"))

    return render_template("edit_form.html", form_name=form_name, form_data=form_data)




if __name__ == '__main__':
    # Use the environment variable PORT if available, otherwise default to 5001 for local
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=False)