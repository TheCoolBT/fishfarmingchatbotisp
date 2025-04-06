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
sheet = gc.open("FishFarmReadingsTest").sheet1

def log_reading(phone, data_dict):
    date = datetime.now().strftime("%Y-%m-%d")
    row = [
        date,
        phone,
        data_dict.get("do", ""),
        data_dict.get("ph", ""),
        data_dict.get("temp", "")
    ]
    sheet.append_row(row)
    print(f"✅ Logged row to sheet: {row}")

# === Google Drive ===
drive_service = build('drive', 'v3', credentials=creds)
TARGET_FOLDER_ID = "1Fgh_v_CG2tYWsQjadY-8Eu832hVHTz_P"

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH_TOKEN")

def upload_photo(field_name, phone, date, file_url):
    print(f"📸 Uploading photo for {field_name} from {phone}")
    print(f"🔗 Attempting to fetch from: {file_url}")

    try:
        response = requests.get(
            file_url,
            auth=HTTPBasicAuth(TWILIO_SID, TWILIO_AUTH),
            headers={"User-Agent": "Mozilla/5.0"}
        )

        if response.status_code != 200:
            print(f"❌ Failed to download image. HTTP Status: {response.status_code}")
            return

        filename = f"{field_name.upper()} {date}.jpg"
        file_metadata = {'name': filename, 'parents': [TARGET_FOLDER_ID]}
        media = MediaIoBaseUpload(io.BytesIO(response.content), mimetype='image/jpeg')

        drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        print(f"✅ Uploaded {filename} to Google Drive.")

    except Exception as e:
        print(f"❌ Error uploading photo: {e}")
