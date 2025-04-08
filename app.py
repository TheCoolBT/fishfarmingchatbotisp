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

@app.route("/webhook", methods=["POST"])
def whatsapp_reply():
    sender = request.form.get("From")
    msg_text = request.form.get("Body", "").strip().lower()
    media_url = request.form.get("MediaUrl0")
    resp = MessagingResponse()
    msg = resp.message()

    # Universal reset command
    if msg_text in ["exit", "keluar"]:
        user_state[sender] = {
            "step": -2,
            "responses": {},
            "media": {},
            "lang": None,
            "form": None,
            "form_type": None
        }
        msg.body("🔄 Form restarted.\n🌐 Please select a language / Silakan pilih bahasa:\n1. 🇮🇩 Bahasa Indonesia\n2. 🇬🇧 English")
        return str(resp)

    if sender not in user_state:
        user_state[sender] = {
            "step": -2,
            "responses": {},
            "media": {},
            "lang": None,
            "form": None,
            "form_type": None
        }
        msg.body("🌐 Please select a language / Silakan pilih bahasa:\n1. 🇮🇩 Bahasa Indonesia\n2. 🇬🇧 English")
        return str(resp)

    state = user_state[sender]

    # Language selection
    if state["step"] == -2:
        if msg_text in ["1", "indonesian", "bahasa indonesia"]:
            state["lang"] = "id"
            state["step"] = -1
            msg.body("📋 Apakah Anda ingin mengisi formulir harian atau mingguan?")
        elif msg_text in ["2", "english"]:
            state["lang"] = "en"
            state["step"] = -1
            msg.body("📋 Would you like to fill the daily or weekly form?")
        else:
            msg.body("❓ Please reply '1' for 🇮🇩 Bahasa Indonesia or '2' for 🇬🇧 English")
        return str(resp)

    # Form type selection
    if state["step"] == -1:
        if msg_text in ["daily", "harian"]:
            state["form_type"] = "daily"
            state["form"] = daily_form_en if state["lang"] == "en" else daily_form_id
            state["step"] = 0
            msg.body(state["form"][0]["prompt"])
        elif msg_text in ["weekly", "mingguan"]:
            state["form_type"] = "weekly"
            state["form"] = weekly_form_en if state["lang"] == "en" else weekly_form_id
            state["step"] = 0
            msg.body(state["form"][0]["prompt"])
        else:
            msg.body("❓ Please reply with 'daily' or 'weekly' / Balas 'harian' atau 'mingguan'")
        return str(resp)

    form = state["form"]
    step = state["step"]

    if step >= len(form):
        msg.body(
            "✅ You've already completed the form. Restarting for testing.\n\n🌐 Please select a language:\n1. 🇮🇩 Bahasa Indonesia\n2. 🇬🇧 English"
        )
        user_state[sender] = {
            "step": -2,
            "responses": {},
            "media": {},
            "lang": None,
            "form": None,
            "form_type": None
        }
        return str(resp)

    current = form[step]
    key = current["key"]
    number = extract_number(msg_text)

    # Save number
    if number and key not in state["responses"]:
        state["responses"][key] = number
        print(f"🧮 Saved number for {key}: {number}")

    # Save media
    if media_url and key not in state["media"]:
        state["media"][key] = media_url
        print(f"📷 Saved media for {key}: {media_url}")

    photo_required = current.get("require_photo", True)
    has_number = key in state["responses"]
    has_photo = not photo_required or key in state["media"]

    if has_number and has_photo:
        state["step"] += 1

        if state["step"] >= len(form):
            phone = sender.replace("whatsapp:", "")
            print(f"📤 Final submission from {phone}")

            for k, url in state["media"].items():
                link = upload_photo(field_name=k, phone=phone, date=datetime.now().strftime("%Y-%m-%d"), file_url=url)
                if link:
                    state["responses"][f"{k}_photo"] = link

            try:
                if state["form_type"] == "daily":
                    log_reading(phone, state["responses"])
                else:
                    log_weekly(phone, state["responses"])
            except Exception as e:
                print(f"❌ Spreadsheet logging error: {e}")
                msg.body("⚠️ There was a problem logging your data. Please try again.")
                return str(resp)

            thank_you = {
                "en": (
                    "✅ Thank you for completing the form!\n"
                    "📨 Send any message to start a new one, or type 'exit' to restart."
                ),
                "id": (
                    "✅ Terima kasih telah mengisi formulir!\n"
                    "📨 Kirim pesan apa pun untuk mengisi lagi, atau ketik 'keluar' untuk mulai ulang."
                )
            }

            msg.body(thank_you[state["lang"]])

            user_state[sender] = {
                "step": -2,
                "responses": {},
                "media": {},
                "lang": None,
                "form": None,
                "form_type": None
            }
        else:
            msg.body(form[state["step"]]["prompt"])
    else:
        if not has_number:
            msg.body(f"🔢 Please enter a number for: {current['name']}")
        elif photo_required and not has_photo:
            msg.body(f"📸 Please upload a photo for: {current['name']}")

    return str(resp)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
