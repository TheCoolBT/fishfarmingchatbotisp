#  Fish Farm WhatsApp Chatbot

A bilingual ( Indonesian +  English) WhatsApp chatbot for Indonesian fish farmers to submit daily and weekly reports.  
Built with Flask, Twilio Sandbox, Google Sheets, and Google Drive.  
Includes expert alerts, automatic reminders, and reactivation warnings for Twilio Sandbox.

---

##  Project Structure

project-root/
│
├── app.py # Main Flask app: handles webhook and conversation
├── scheduler.py # Background tasks: reminders, sandbox tracking
├── drive.py # Handles Google Sheets + Drive logging
├── ai_helper.py # Out-of-range alerts + AI troubleshooting
├── forms/
│ ├── daily_form.py # Daily form fields (English and Indonesian)
│ └── weekly_form.py # Weekly form fields (English and Indonesian)
│
├── requirements.txt # Python dependencies
├── .env # Environment variables (see below)
└── Procfile # For Heroku deployment


---

## Environment Setup

Create a `.env` file:

TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=+14155238886 # Twilio sandbox number
GOOGLE_CREDS_BASE64=base64_encoded_google_creds.json


> Use `base64 google-creds.json` to encode your credentials file.

---

## How It Works

- 🌐 Users message `test` to start the form manually
- ⏰ Scheduled jobs send daily + weekly reminders via WhatsApp
- 📥 Responses are parsed, validated, and uploaded to Google Sheets
- 📸 Photos and videos are stored in Google Drive
- 📡 Expert alerts are sent when values are abnormal
- 🔁 Bot tracks last activity and warns users to send `join sense-believed` before sandbox timeout

---

## How to Modify Features

###Add or Remove Form Questions

Edit the files in `forms/`:
- `daily_form.py`
- `weekly_form.py`

Each form field follows:
```python
{
  "key": "do",
  "name": "DO (mg/L)",
  "prompt": "Berapa nilai DO hari ini?",
  "require_photo": True
}
Adjust Alert Thresholds
Edit ai_helper.py:

ALERT_THRESHOLDS = {
  "do": {"min": 4.0, "max": 7.5},
  "ph": {"min": 6.5, "max": 8.5},
  ...
}
Update Reminder Schedule
Edit scheduler.py → schedule_jobs():

scheduler.add_job(send_daily_reminder, 'cron', hour=7, minute=30)
scheduler.add_job(send_weekly_reminder, 'cron', day_of_week='sun', hour=5, minute=0)
All times are in UTC.

Change Sandbox Timeout Behavior
In scheduler.py → update_last_reactivation():

run_time = datetime.utcnow() + timedelta(hours=1)
This schedules a reminder 1 hour before sandbox expiration. You can adjust this to any time before the 72-hour limit.

Test Commands

Command	Behavior
test	Manually start the form
test troubleshoot	Sends fake out-of-range data to experts
test health status	Sends a full test report with video
join sense-believed	Updates sandbox reactivation tracking
Deployment Instructions

One-Time Heroku Setup
heroku create
heroku buildpacks:set heroku/python
heroku config:set $(cat .env | xargs)
git push heroku main
Redeploy After Changes
git add .
git commit -m "Your message"
git push heroku main
