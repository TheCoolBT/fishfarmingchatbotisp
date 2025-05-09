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

# In-memory store for first daily reading
daily_buffer = {}

def upload_photo(field_name, phone, date, file_url):
    print(f"📸 Uploading {field_name} from {phone}")
    try:
        response = requests.get(
            file_url,
            auth=HTTPBasicAuth(TWILIO_SID, TWILIO_AUTH),
            headers={"User-Agent": "Mozilla/5.0"}
        )
        if response.status_code != 200:
            print(f"❌ Failed to download media. Status: {response.status_code}")
            return None

        # Check if it's a video
        is_video = file_url.endswith(".mp4") or "video" in response.headers.get("Content-Type", "")
        
        # Set filename
        if field_name == "general_video":
            filename = f"WATER CONDITIONS {date}.mp4"
        else:
            filename = f"{field_name.upper()} {date}.jpg"

        # Use same folder (TARGET_FOLDER_ID)
        media = MediaIoBaseUpload(io.BytesIO(response.content), mimetype='video/mp4' if is_video else 'image/jpeg')
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
    timestamp = datetime.now().strftime("%-m/%-d/%Y %H:%M:%S")
    row = [timestamp]

    for key in ["do", "ph", "temp"]:
        value = data_dict.get(key, "")
        photo = data_dict.get(f"{key}_photo", "")
        try:
            value = float(value)
        except:
            pass
        row.append(value)
        row.append(photo)

    row += ["", ""]

    for key in ["dead_fish", "feeding_freq", "feed_weight", "inv_feed", "inv_rest"]:
        value = data_dict.get(key, "")
        try:
            value = float(value)
        except:
            pass
        row.append(value)
        if key != "feeding_freq":
            photo = data_dict.get(f"{key}_photo", "")
            row.append(photo)

    print("📤 Final daily submission row:")
    print(row)
    daily_tab.append_row(row)
    print("✅ Row successfully written to Daily Survey Input")

def log_final_average(phone, reading1, reading2):
    avg = {}
    for key in ["do", "ph", "temp", "dead_fish", "feeding_freq", "feed_weight", "inv_feed", "inv_rest"]:
        try:
            avg[key] = (float(reading1.get(key, 0)) + float(reading2.get(key, 0))) / 2
        except:
            avg[key] = reading2.get(key, "")  # fallback to second if averaging fails

    for key in ["do", "ph", "temp", "dead_fish", "feed_weight", "inv_feed", "inv_rest"]:
        avg[f"{key}_photo"] = reading2.get(f"{key}_photo", "")

    log_reading(phone, avg)

def log_weekly(phone, data_dict):
    timestamp = datetime.now().strftime("%-m/%-d/%Y %H:%M:%S")
    row = [timestamp]

    for i in range(1, 31):
        photo = data_dict.get(f"fish_{i}_photo", "")
        weight = data_dict.get(f"fish_{i}_weight", "")
        length = data_dict.get(f"fish_{i}_length", "")
        try:
            weight = float(weight)
        except:
            pass
        try:
            length = float(length)
        except:
            pass
        row.extend([photo, weight, length])

    print("📤 Final weekly submission row:")
    print(row)
    weekly_tab.append_row(row)
    print("✅ Row successfully written to Weekly Survey Input")


def get_recent_trends(n=3):
    """Fetch and format last n rows of daily readings as AI prompt context."""
    try:
        records = daily_tab.get_all_records()
        if not records:
            return "No recent data available."

        recent = records[-n:]
        trend_lines = []
        for row in recent:
            timestamp = row.get("Timestamp", "Unknown time")
            do = row.get("DATA 1 - DO (mg/L)", "?")
            ph = row.get("DATA 3 - pH", "?")
            temp = row.get("DATA 5 - Temp (°C)", "?")
            deaths = row.get("DATA 9 - Fish Deaths", "?")
            trend_lines.append(
                f"{timestamp} — DO: {do}, pH: {ph}, Temp: {temp}, Deaths: {deaths}"
            )

        return "\n".join(trend_lines)
    except Exception as e:
        return f"⚠️ Error getting trends: {e}"
