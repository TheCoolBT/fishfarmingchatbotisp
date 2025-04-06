from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from requests.auth import HTTPBasicAuth
import requests
import os
import io
from datetime import datetime

# Google Drive setup
SCOPES = ['https://www.googleapis.com/auth/drive']
creds = service_account.Credentials.from_service_account_file("google-creds.json", scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=creds)

# ✅ Your shared folder ID
TARGET_FOLDER_ID = "1Fgh_v_CG2tYWsQjadY-8Eu832hVHTz_P"

# Twilio credentials from .env
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

        file_metadata = {
            'name': filename,
            'parents': [TARGET_FOLDER_ID]
        }

        media = MediaIoBaseUpload(io.BytesIO(response.content), mimetype='image/jpeg')

        drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        print(f"✅ Uploaded {filename} to Google Drive.")

    except Exception as e:
        print(f"❌ Error uploading photo: {e}")
