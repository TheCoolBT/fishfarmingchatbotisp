from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from dotenv import load_dotenv
import os
import re
from sheets import log_reading

# Load .env variables
load_dotenv()

app = Flask(__name__)

# Store conversation state
user_state = {}

# List of readings to collect
readings_sequence = ["Dissolved Oxygen", "pH", "Temperature"]

# SOP thresholds
reading_limits = {
    "Dissolved Oxygen": (5.0, 10.0),  # Example values
    "pH": (6.5, 9.0),
    "Temperature": (25.0, 32.0)
}

# Expert number (can be your own)
EXPERT_PHONE = 'whatsapp:+18027600986'

# Twilio setup
twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_client = Client(twilio_sid, twilio_token)

# Helper: Extract first number from a message
def extract_number(text):
    match = re.search(r"[-+]?\d*\.\d+|\d+", text)
    return match.group() if match else None

# Helper: Check if values are abnormal
def check_abnormalities(data):
    problems = []
    for key, value in data.items():
        try:
            val = float(value)
            low, high = reading_limits.get(key, (None, None))
            if low is not None and (val < low or val > high):
                problems.append(f"{key} is out of range: {val}")
        except ValueError:
            problems.append(f"{key} value '{value}' is not a number")
    return problems


@app.route('/webhook', methods=['POST'])
def whatsapp_reply():
    sender = request.form.get('From')  # e.g., whatsapp:+18027600986
    incoming_msg = request.form.get('Body').strip()

    resp = MessagingResponse()
    msg = resp.message()

    # Start new session
    if sender not in user_state:
        user_state[sender] = {
            "step": 0,
            "responses": {}
        }
        msg.body(f"Hi! Let's log your farm readings.\nWhat is your {readings_sequence[0]} level?")
        return str(resp)

    # Existing session
    state = user_state[sender]
    current_step = state["step"]

    # Extract number from input
    extracted_value = extract_number(incoming_msg)

    if extracted_value:
        key = readings_sequence[current_step]
        state["responses"][key] = extracted_value
        state["step"] += 1
    else:
        msg.body(f"⚠️ I couldn't find a number in your message.\nPlease enter your {readings_sequence[current_step]} as a number (e.g., 7.2)")
        return str(resp)

    # Continue or finish
    if state["step"] < len(readings_sequence):
        next_key = readings_sequence[state["step"]]
        msg.body(f"Got it! What is your {next_key}?")
    else:
        summary = "\n".join(f"{k}: {v}" for k, v in state["responses"].items())
        msg.body("✅ Thanks! All readings collected:\n" + summary)

        # Log to Google Sheets
        log_reading(sender.replace("whatsapp:", ""), state["responses"])

        # Check for abnormalities
        problems = check_abnormalities(state["responses"])

        if problems:
            expert_msg = f"🚨 Abnormal readings from {sender.replace('whatsapp:', '')}:\n" + "\n".join(problems)
        else:
            expert_msg = f"✅ All readings normal from {sender.replace('whatsapp:', '')}"

        # Send to expert (yourself for now)
        twilio_client.messages.create(
            body=expert_msg,
            from_='whatsapp:+14155238886',  # Twilio Sandbox Number
            to=EXPERT_PHONE
        )

        # Clear session
        del user_state[sender]

    return str(resp)


if __name__ == '__main__':
    app.run(debug=True)
