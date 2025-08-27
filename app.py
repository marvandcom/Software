import os
import json
import base64
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
from datetime import datetime

# Load .env
load_dotenv()

# ========= Flask setup =========
app = Flask(__name__, static_folder='templates', static_url_path='')
CORS(app)

# ========= Google Sheets Auth =========
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")


def get_gspread_client():
    b64 = os.getenv("GOOGLE_CREDENTIALS")
    if not b64:
        raise ValueError("❌ GOOGLE_CREDENTIALS missing (base64 of credentials.json in .env).")
    creds_json = base64.b64decode(b64).decode("utf-8")
    info = json.loads(creds_json)
    creds = Credentials.from_service_account_info(info, scopes=SCOPE)
    return gspread.authorize(creds)


def get_sheet():
    client = get_gspread_client()
    return client.open_by_key(SPREADSHEET_ID).sheet1


# ========= API Endpoints =========
@app.route("/api/transactions", methods=["GET"])
def get_transactions():
    sheet = get_sheet()
    rows = sheet.get_all_records()
    return jsonify(rows)


@app.route("/api/transactions", methods=["POST"])
def add_transaction():
    sheet = get_sheet()
    data = request.json
    if not data:
        return jsonify({"error": "No data"}), 400

    # Incremental ID = last row count + 1
    new_id = len(sheet.get_all_values())
    tx = [
        new_id,
        data.get("date") or datetime.now().strftime("%Y-%m-%d"),
        data.get("type"),
        data.get("amount"),
        data.get("category"),
        data.get("patientName", ""),
        data.get("patientId", ""),
        data.get("phone", ""),
        data.get("payment", ""),
        data.get("notes", "")
    ]
    sheet.append_row(tx)
    return jsonify({"message": "Transaction added", "id": new_id})


@app.route("/api/transactions/<int:row_id>", methods=["DELETE"])
def delete_transaction(row_id):
    sheet = get_sheet()
    values = sheet.get_all_values()
    if row_id >= len(values):
        return jsonify({"error": "Not found"}), 404
    sheet.delete_rows(row_id + 1)  # +1 because Google Sheets is 1-indexed with headers
    return jsonify({"message": "Deleted"})


# ========= Serve frontend =========
@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


# Add this at the end of your app.py file
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)