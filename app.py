from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from dotenv import load_dotenv
from drive import log_reading, log_weekly, upload_photo
from forms.daily_form import daily_form_en, daily_form_id
from forms.weekly_form import weekly_form_en, weekly_form_id
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import os
import re

load_dotenv()
app = Flask(__name__)
user_state = {}

# Twilio client setup
TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
client = Client(TWILIO_SID, TWILIO_AUTH)

# Simple message sender
def send_whatsapp_message(to, body):
    client.messages.create(
        from_="whatsapp:" + TWILIO_NUMBER,
        to="whatsapp:" + to,
        body=body
    )

# Scheduled reminders
def send_daily_reminder():
    recipients = ["+18027600986"]  # ← replace with real numbers
    for number in recipients:
        send_whatsapp_message(number, "🔔 It's time to fill out the daily form!\n📨 Sekarang waktunya mengisi formulir harian!")

def send_weekly_reminder():
    recipients = ["+18027600986"]
    for number in recipients:
        send_whatsapp_message(number, "📆 Weekly form reminder!\n⏰ Jangan lupa isi formulir mingguan hari ini!")

# Scheduler setup
def schedule_jobs():
    scheduler = BackgroundScheduler()
    scheduler.add_job(send_daily_reminder, 'cron', hour=22, minute=30)  # 5:30 AM UTC+7
    scheduler.add_job(send_daily_reminder, 'cron', hour=7, minute=30)   # 2:30 PM UTC+7
    scheduler.add_job(send_weekly_reminder, 'cron', day_of_week='sun', hour=5, minute=0)  # 12 PM UTC+7 Sunday
    scheduler.start()

def extract_number(text):
    match = re.search(r"[-+]?\d*\.\d+|\d+", text)
    return match.group() if match else None

def get_pending_fields(responses, form):
    return [f for f in form if f["key"] not in responses]

@app.route("/webhook", methods=["POST"])
def whatsapp_reply():
    sender = request.form.get("From")
    msg_text = request.form.get("Body", "").strip().lower()
    media_url = request.form.get("MediaUrl0")
    resp = MessagingResponse()
    msg = resp.message()

    # Reset form on "exit" or "keluar"
    if msg_text in ["exit", "keluar"]:
        user_state[sender] = {"lang": None, "form_type": None, "responses": {}, "media": {}, "stage": "lang"}
        msg.body("🔄 Form restarted.\n🌐 Please select a language / Silakan pilih bahasa:\n1. 🇮🇩 Bahasa Indonesia\n2. 🇬🇧 English")
        return str(resp)

    # Start flow with "test"
    if msg_text == "test":
        user_state[sender] = {"lang": None, "form_type": None, "responses": {}, "media": {}, "stage": "lang"}
        msg.body("🌐 Please select a language / Silakan pilih bahasa:\n1. 🇮🇩 Bahasa Indonesia\n2. 🇬🇧 English")
        return str(resp)

    if sender not in user_state:
        user_state[sender] = {"lang": None, "form_type": None, "responses": {}, "media": {}, "stage": "lang"}
        msg.body("🌐 Please select a language / Silakan pilih bahasa:\n1. 🇮🇩 Bahasa Indonesia\n2. 🇬🇧 English")
        return str(resp)

    state = user_state[sender]

    if state["stage"] == "lang":
        if msg_text in ["1", "indonesian", "bahasa indonesia"]:
            state["lang"] = "id"
            state["stage"] = "form_select"
            msg.body("📋 Pilih jenis formulir:\n1. Harian\n2. Mingguan")
        elif msg_text in ["2", "english"]:
            state["lang"] = "en"
            state["stage"] = "form_select"
            msg.body("📋 Please choose a form type:\n1. Daily\n2. Weekly")
        else:
            msg.body("❓ Reply with 1 for 🇮🇩 Bahasa Indonesia or 2 for 🇬🇧 English")
        return str(resp)

    if state["stage"] == "form_select":
        if msg_text in ["1", "daily", "harian"]:
            state["form_type"] = "daily"
            state["form"] = daily_form_en if state["lang"] == "en" else daily_form_id
            state["responses"] = {}
            state["media"] = {}
            state["stage"] = "in_progress"
            send_field_list(msg, state)
        elif msg_text in ["2", "weekly", "mingguan"]:
            state["form_type"] = "weekly"
            state["form"] = weekly_form_en if state["lang"] == "en" else weekly_form_id
            state["responses"] = {}
            state["media"] = {}
            state["step"] = 0
            state["stage"] = "weekly_in_progress"
            msg.body(state["form"][0]["prompt"])
        else:
            msg.body("❓ Balas dengan 1 untuk Harian atau 2 untuk Mingguan" if state["lang"] == "id" else "❓ Reply with 1 for Daily or 2 for Weekly")
        return str(resp)

    if state.get("stage") == "weekly_in_progress":
        form = state["form"]
        step = state["step"]
        current = form[step]
        key = current["key"]

        number = extract_number(msg_text)
        if number and key not in state["responses"]:
            state["responses"][key] = number
        if media_url and key not in state["media"]:
            state["media"][key] = media_url

        photo_required = current.get("require_photo", True)
        has_number = key in state["responses"]
        has_photo = not photo_required or key in state["media"]

        if has_number and has_photo:
            state["step"] += 1
            if state["step"] < len(form):
                msg.body(form[state["step"]]["prompt"])
            else:
                phone = sender.replace("whatsapp:", "")
                for k, url in state["media"].items():
                    link = upload_photo(field_name=k, phone=phone, date=datetime.now().strftime("%Y-%m-%d"), file_url=url)
                    if link:
                        state["responses"][f"{k}_photo"] = link
                log_weekly(phone, state["responses"])
                msg.body("✅ Terima kasih telah mengisi formulir!\n📨 Kirim pesan untuk memulai kembali." if state["lang"] == "id" else "✅ Thank you! Form submitted.\n📨 Send any message to start over.")
                user_state[sender] = {"lang": None, "form_type": None, "responses": {}, "media": {}, "stage": "lang"}
            return str(resp)
        else:
            msg.body("🔢 Masukkan angka untuk: {}".format(current["name"]) if not has_number else "📸 Unggah foto untuk: {}".format(current["name"]) if state["lang"] == "id" else "🔢 Enter number for: {}".format(current["name"]) if not has_number else "📸 Upload photo for: {}".format(current["name"]))
            return str(resp)

    form = daily_form_en if state["lang"] == "en" else daily_form_id
    pending = get_pending_fields(state["responses"], form)

    if state["stage"] == "in_progress":
        if msg_text.isdigit() and 1 <= int(msg_text) <= len(pending):
            selected = pending[int(msg_text) - 1]
            state["current"] = selected["key"]
            msg.body(selected["prompt"])
        elif "current" in state:
            key = state["current"]
            if key not in state["responses"] and extract_number(msg_text):
                state["responses"][key] = extract_number(msg_text)
            if key not in state["media"] and media_url:
                state["media"][key] = media_url

            current = next(f for f in form if f["key"] == key)
            photo_required = current.get("require_photo", True)
            has_number = key in state["responses"]
            has_photo = not photo_required or key in state["media"]

            if has_number and has_photo:
                del state["current"]
                pending = get_pending_fields(state["responses"], form)
                if pending:
                    send_field_list(msg, state)
                else:
                    phone = sender.replace("whatsapp:", "")
                    for k, url in state["media"].items():
                        link = upload_photo(field_name=k, phone=phone, date=datetime.now().strftime("%Y-%m-%d"), file_url=url)
                        if link:
                            state["responses"][f"{k}_photo"] = link
                    log_reading(phone, state["responses"])
                    msg.body("✅ Terima kasih telah mengisi formulir harian!\n📨 Kirim pesan apa pun untuk mulai ulang." if state["lang"] == "id" else "✅ Thank you for completing the daily form!\n📨 Send any message to restart.")
                    user_state[sender] = {"lang": None, "form_type": None, "responses": {}, "media": {}, "stage": "lang"}
            else:
                if not has_number:
                    msg.body("🔢 Masukkan angka untuk: {}".format(current["name"]) if state["lang"] == "id" else "🔢 Enter number for: {}".format(current["name"]))
                elif photo_required and not has_photo:
                    msg.body("📸 Unggah foto untuk: {}".format(current["name"]) if state["lang"] == "id" else "📸 Upload photo for: {}".format(current["name"]))
        else:
            send_field_list(msg, state)

    return str(resp)

def send_field_list(msg, state):
    form = state["form"] = daily_form_en if state["lang"] == "en" else daily_form_id
    pending = get_pending_fields(state["responses"], form)
    if not pending:
        return
    body = "❓ What would you like to answer next?\n" if state["lang"] == "en" else "❓ Apa yang ingin Anda jawab selanjutnya?\n"
    for i, field in enumerate(pending, 1):
        body += f"{i}. {field['name']}\n"
    msg.body(body.strip())

if __name__ == '__main__':
    send_daily_reminder()  # 🔥 Send reminder immediately on boot
    schedule_jobs()        # Then start normal cron-based jobs
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

