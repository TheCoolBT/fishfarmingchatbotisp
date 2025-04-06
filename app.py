from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from dotenv import load_dotenv
import os
from datetime import datetime
from drive import log_reading, upload_photo
import re

load_dotenv()
app = Flask(__name__)
user_state = {}

form_sequence = [
    {"name": "Dissolved Oxygen", "key": "do", "prompt": "💧 Please submit the DO (mg/L) *with a photo of the reading*."},
    {"name": "pH", "key": "ph", "prompt": "🔬 Please submit the pH *with a photo of the pH meter*."},
    {"name": "Temperature", "key": "temp", "prompt": "🌡️ Please submit the water temperature (°C) *with a photo of the thermometer*."}
]

def extract_number(text):
    match = re.search(r"[-+]?\d*\.\d+|\d+", text)
    return match.group() if match else None

@app.route('/webhook', methods=['POST'])
def whatsapp_reply():
    sender = request.form.get('From')
    msg_text = request.form.get('Body').strip()
    media_url = request.form.get('MediaUrl0')

    resp = MessagingResponse()
    msg = resp.message()

    # Start session if new user
    if sender not in user_state:
        user_state[sender] = {"step": 0, "responses": {}, "media": {}}
        current = form_sequence[0]
        msg.body(f"👋 Hi! Let's begin.\n\n{current['prompt']}")
        return str(resp)

    # Load session
    state = user_state[sender]
    step = state["step"]
    current = form_sequence[step]
    key = current["key"]
    responses = state["responses"]
    media = state["media"]

    # Try to extract number
    number = extract_number(msg_text)

    # Save number if it's valid and not saved yet
    if key not in responses and number:
        responses[key] = number
        print(f"🧮 Saved number for {key}: {number}")

    # Save media if not saved yet
    if key not in media and media_url:
        media[key] = media_url
        print(f"📷 Saved media for {key}: {media_url}")

    # If both are now saved, confirm and move on
    if key in responses and key in media:
        msg.body(f"✅ {current['name']} saved.\n")

        state["step"] += 1

        if state["step"] < len(form_sequence):
            next_field = form_sequence[state["step"]]
            msg.body(f"{next_field['prompt']}")
        else:
            # All complete — log & upload
            log_reading(sender.replace("whatsapp:", ""), responses)
            for k, url in media.items():
                upload_photo(field_name=k, phone=sender.replace("whatsapp:", ""), date=datetime.now().strftime("%Y-%m-%d"), file_url=url)

            # Check for abnormal values
            do = float(responses.get("do", 0))
            ph = float(responses.get("ph", 0))
            temp = float(responses.get("temp", 0))

            abnormalities = []
            if do < 4 or do > 8:
                abnormalities.append(f"❗ DO is {do} (Expected: 4–8 mg/L)")
            if ph < 6.5 or ph > 9:
                abnormalities.append(f"❗ pH is {ph} (Expected: 6.5–9)")
            if temp < 26 or temp > 32:
                abnormalities.append(f"❗ Temperature is {temp}°C (Expected: 26–32°C)")

            if abnormalities:
                msg.body("⚠️ Thank you for submitting all readings.\nSome readings are outside normal range:\n\n" + "\n".join(abnormalities))
            else:
                msg.body("✅ All readings submitted and within normal range. Thank you!")

            # Send expert report (currently to you)
            twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
            twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
            client = Client(twilio_sid, twilio_token)

            expert_number = "whatsapp:+18027600986"  # You for now
            report = "\n".join(abnormalities) if abnormalities else "✅ All values normal."

            client.messages.create(
                body=f"📋 Report from {sender.replace('whatsapp:', '')} ({datetime.now().strftime('%Y-%m-%d')}):\n\n{report}",
                from_="whatsapp:+14155238886",
                to=expert_number
            )

            del user_state[sender]

    else:
        # Missing something — remind them
        if key not in responses and not number:
            msg.body(f"⚠️ Please send a *number* for {current['name']}.")
        elif key not in media and not media_url:
            msg.body(f"⚠️ Please send a *photo* of the {current['name']}.")
        else:
            # One is now present, waiting for the other
            needed = []
            if key not in responses:
                needed.append("number")
            if key not in media:
                needed.append("photo")
            msg.body(f"📩 Waiting for your {current['name']} {', and a '.join(needed)}.")

    return str(resp)

if __name__ == '__main__':
    app.run(debug=True)
