from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
from drive import log_reading, log_weekly, upload_photo
from forms.daily_form import daily_form_en, daily_form_id
from forms.weekly_form import weekly_form_en, weekly_form_id
from datetime import datetime
import os
import re

load_dotenv()
app = Flask(__name__)
user_state = {}

def extract_number(text):
    match = re.search(r"[-+]?\d*\.\d+|\d+", text)
    return match.group() if match else None

def format_task_list(pending_fields, lang):
    lines = []
    for i, field in enumerate(pending_fields, 1):
        lines.append(f"{i}. {field['name']}")
    if lang == "en":
        return "What would you like to report next?\n" + "\n".join(lines)
    else:
        return "Apa yang ingin Anda laporkan selanjutnya?\n" + "\n".join(lines)

@app.route("/webhook", methods=["POST"])
def whatsapp_reply():
    sender = request.form.get("From")
    msg_text = request.form.get("Body", "").strip().lower()
    media_url = request.form.get("MediaUrl0")
    resp = MessagingResponse()
    msg = resp.message()

    if msg_text in ["exit", "keluar"]:
        user_state[sender] = {
            "step": -2,
            "responses": {},
            "media": {},
            "lang": None,
            "form_type": None,
            "pending": [],
            "current": None
        }
        msg.body("🔄 Form restarted.\n🌐 Please select a language / Silakan pilih bahasa:\n1. 🇮🇩 Bahasa Indonesia\n2. 🇬🇧 English")
        return str(resp)

    if sender not in user_state:
        user_state[sender] = {
            "step": -2,
            "responses": {},
            "media": {},
            "lang": None,
            "form_type": None,
            "pending": [],
            "current": None
        }
        msg.body("🌐 Please select a language / Silakan pilih bahasa:\n1. 🇮🇩 Bahasa Indonesia\n2. 🇬🇧 English")
        return str(resp)

    state = user_state[sender]

    if state["step"] == -2:
        if msg_text in ["1", "bahasa indonesia"]:
            state["lang"] = "id"
            state["step"] = -1
            msg.body("📋 Pilih jenis formulir:\n1. Harian\n2. Mingguan")
        elif msg_text in ["2", "english"]:
            state["lang"] = "en"
            state["step"] = -1
            msg.body("📋 Please choose a form type:\n1. Daily\n2. Weekly")
        else:
            msg.body("❓ Reply with 1 for 🇮🇩 Bahasa Indonesia or 2 for 🇬🇧 English")
        return str(resp)

    if state["step"] == -1:
        if msg_text in ["1", "daily", "harian"]:
            state["form_type"] = "daily"
            form = daily_form_en if state["lang"] == "en" else daily_form_id
            state["pending"] = form.copy()
            state["step"] = 0
            msg.body(format_task_list(state["pending"], state["lang"]))
        elif msg_text in ["2", "weekly", "mingguan"]:
            msg.body("⛔ Weekly form must be filled in order.")
        else:
            msg.body("❓ Reply 1 for Daily / Harian or 2 for Weekly / Mingguan")
        return str(resp)

    # If no current task is active, expect a number to select next field
    if not state["current"]:
        try:
            idx = int(msg_text) - 1
            state["current"] = state["pending"].pop(idx)
            msg.body(state["current"]["prompt"])
        except:
            msg.body(format_task_list(state["pending"], state["lang"]))
        return str(resp)

    current = state["current"]
    key = current["key"]
    number = extract_number(msg_text)
    lang = state["lang"]

    if number and key not in state["responses"]:
        state["responses"][key] = number
    if media_url and key not in state["media"]:
        state["media"][key] = media_url

    require_photo = current.get("require_photo", True)
    has_number = key in state["responses"]
    has_photo = not require_photo or key in state["media"]

    if has_number and has_photo:
        state["current"] = None
        if state["pending"]:
            msg.body(format_task_list(state["pending"], lang))
        else:
            phone = sender.replace("whatsapp:", "")
            for k, url in state["media"].items():
                link = upload_photo(field_name=k, phone=phone, date=datetime.now().strftime("%Y-%m-%d"), file_url=url)
                if link:
                    state["responses"][f"{k}_photo"] = link
            try:
                log_reading(phone, state["responses"])
                thank_you = {
                    "en": "✅ Thank you for completing the daily form!\n📨 Send any message to start a new one.",
                    "id": "✅ Terima kasih telah mengisi formulir harian!\n📨 Kirim pesan apa pun untuk mengisi lagi."
                }
                msg.body(thank_you[lang])
            except Exception as e:
                print(f"❌ Spreadsheet logging error: {e}")
                msg.body("⚠️ Error saving your data. Try again later.")
            user_state[sender] = {
                "step": -2,
                "responses": {},
                "media": {},
                "lang": None,
                "form_type": None,
                "pending": [],
                "current": None
            }
    else:
        if not has_number:
            msg.body({
                "en": f"🔢 Please enter a number for: {current['name']}",
                "id": f"🔢 Masukkan angka untuk: {current['name']}"
            }[lang])
        elif require_photo and not has_photo:
            msg.body({
                "en": f"📸 Please upload a photo for: {current['name']}",
                "id": f"📸 Silakan unggah foto untuk: {current['name']}"
            }[lang])

    return str(resp)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
