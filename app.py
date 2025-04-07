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

    if sender not in user_state:
        user_state[sender] = {
            "step": -2,
            "responses": {},
            "media": {},
            "lang": None,
            "form": None,
            "form_type": None
        }
        msg.body("🌐 Silakan pilih bahasa / Please select a language:\n🇮🇩 Indonesian\n🇺🇸 English")
        return str(resp)

    state = user_state[sender]

    # Language selection
    if state["step"] == -2:
        if "indonesian" in msg_text or msg_text == "1":
            state["lang"] = "id"
            state["step"] = -1
            msg.body("📋 Apakah Anda ingin mengisi formulir harian atau mingguan?")
        elif "english" in msg_text or msg_text == "2":
            state["lang"] = "en"
            state["step"] = -1
            msg.body("📋 Would you like to fill the daily or weekly form?")
        else:
            msg.body("❓ Please reply 'English' or 'Indonesian' / Balas 'English' atau 'Indonesian'")
        return str(resp)

    # Form type selection
    if state["step"] == -1:
        if "daily" in msg_text or "harian" in msg_text:
            state["form_type"] = "daily"
            state["form"] = daily_form_en if state["lang"] == "en" else daily_form_id
            state["step"] = 0
            msg.body(state["form"][0]["prompt"])
        elif "weekly" in msg_text or "mingguan" in msg_text:
            state["form_type"] = "weekly"
            state["form"] = weekly_form_en if state["lang"] == "en" else weekly_form_id
            state["step"] = 0
            msg.body(state["form"][0]["prompt"])
        else:
            msg.body("❓ Please reply 'daily' or 'weekly' / Balas 'harian' atau 'mingguan'")
        return str(resp)

    # Main form flow
    form = state["form"]
    step = state["step"]

    if step >= len(form):
        msg.body("✅ You've already completed the form.")
        return str(resp)

    current = form[step]
    key = current["key"]
    number = extract_number(msg_text)

    # Save responses
    if number and key not in state["responses"]:
        state["responses"][key] = number

    if media_url and key not in state["media"]:
        state["media"][key] = media_url

    has_number = key in state["responses"]
    has_photo = key in state["media"]

    # Wait until both number and photo are  present before moving on
    if has_number and has_photo:
        state["step"] += 1
        if state["step"] < len(form):
            next_prompt = form[state["step"]]["prompt"]
            msg.body(next_prompt)
        else:
            phone = sender.replace("whatsapp:", "")
            if state["form_type"] == "daily":
                if state["form_type"] == "daily":
                    log_reading(phone, state["responses"])
                else:
                    log_weekly(phone, state["responses"])
            for k, url in state["media"].items():
                upload_photo(field_name=k, phone=phone, date=datetime.now().strftime("%Y-%m-%d"), file_url=url)
            closing = "✅ Thank you for submitting the "
            closing += "daily form! / Terima kasih sudah mengisi formulir harian." if state["form_type"] == "daily" \
                else "weekly form! / Terima kasih sudah mengisi formulir mingguan."
            msg.body(closing)
            del user_state[sender]
    else:
        if not has_number:
            msg.body(f"🔢 Please enter a number for: {current['name']}")
        elif not has_photo:
            msg.body(f"📸 Please upload a photo for: {current['name']}")

    return str(resp)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
