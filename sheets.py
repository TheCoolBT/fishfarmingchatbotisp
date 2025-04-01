# sheets.py
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Setup auth
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("google-creds.json", scope)
client = gspread.authorize(creds)

# Open your sheet
sheet = client.open("FishFarmReadings").sheet1  # Replace with exact sheet name if different

def log_reading(phone, data_dict):
    date = datetime.now().strftime("%Y-%m-%d")
    row = [date, phone]
    for field in ["Dissolved Oxygen", "pH", "Temperature"]:
        row.append(data_dict.get(field, ""))
    sheet.append_row(row)
