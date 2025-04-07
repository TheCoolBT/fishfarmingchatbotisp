import os
import io
import json
import base64
import gspread
import requests
from datetime import datetime
from requests.auth import HTTPBasicAuth
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# === Auth credentials ===
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

if "GOOGLE_CREDS_BASE64" in os.environ:
    creds_json = base64.b64decode(os.environ["GOOGLE_CREDS_BASE64"])
    creds_dict = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
else:
    creds = service_account.Credentials.from_service_account_file("google-creds.json", scopes=SCOPES)

# === Google Sheets ===
gc = gspread.authorize(creds)
dashboard = gc.open("Test Version of Dashboard")
daily_tab = dashboard.worksheet("Daily Survey Input")
weekly_tab = dashboard.worksheet("Weekly Survey Input")

# === Google Drive ===
drive_service = build('drive', 'v3', credentials=creds)
TARGET_FOLDER_ID = "1Fgh_v_CG2tYWsQjadY-8Eu832hVHTz_P"
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH_TOKEN")

def upload_photo(field_name, phone, date, file_url):
    print(f"📸 Uploading photo for {field_name} from {phone}")
    try:
        response = requests.get(
            file_url,
            auth=HTTPBasicAuth(TWILIO_SID, TWILIO_AUTH),
            headers={"User-Agent": "Mozilla/5.0"}
        )
        if response.status_code != 200:
            print(f"❌ Failed to download image. Status: {response.status_code}")
            return None

        filename = f"{field_name.upper()} {date}.jpg"
        media = MediaIoBaseUpload(io.BytesIO(response.content), mimetype='image/jpeg')
        file_metadata = {'name': filename, 'parents': [TARGET_FOLDER_ID]}
        uploaded_file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        file_id = uploaded_file['id']
        drive_service.permissions().create(
            fileId=file_id,
            body={'role': 'reader', 'type': 'anyone'},
        ).execute()

        link = f"https://drive.google.com/uc?id={file_id}"
        print(f"✅ Uploaded {filename} → {link}")
        return link

    except Exception as e:
        print(f"❌ Upload error: {e}")
        return None

def log_reading(phone, data_dict):
    """Log daily form data to daily survey tab"""
    timestamp = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
    row = [timestamp]

    keys = [
        "do", "ph", "temp",
        "dead_fish", "feeding_freq", "feed_weight", "inv_feed", "inv_rest"
    ]

    for key in keys:
        value = data_dict.get(key, "")
        photo = data_dict.get(f"{key}_photo", "")
        row.extend([value, photo])  # Value in one cell, photo link in the next

    daily_tab.append_row(row)
    print(f"✅ Logged daily row to spreadsheet:\n{row}")

def log_weekly(phone, data_dict):
    """Log weekly form data to weekly survey tab"""
    timestamp = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
    row = [timestamp]

    for i in range(1, 31):
        weight = data_dict.get(f"fish_{i}_weight", "")
        length = data_dict.get(f"fish_{i}_length", "")
        photo = data_dict.get(f"fish_{i}_photo", "")
        row.extend([weight, length, photo])

    weekly_tab.append_row(row)
    print(f"✅ Logged weekly row to spreadsheet:\n{row}")
