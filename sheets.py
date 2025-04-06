import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Google Sheets API setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("google-creds.json", scope)
client = gspread.authorize(creds)

# Open your specific spreadsheet
sheet = client.open("FishFarmReadingsTest").sheet1  # Make sure this matches exactly

def log_reading(phone, data_dict):
    date = datetime.now().strftime("%Y-%m-%d")

    # Build the row in correct column order
    row = [
        date,
        phone,
        data_dict.get("do", ""),
        data_dict.get("ph", ""),
        data_dict.get("temp", "")
    ]

    # Append row to sheet
    sheet.append_row(row)

    print(f"✅ Logged row to sheet: {row}")
