# send_test.py
from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()

# Load credentials from .env
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
client = Client(account_sid, auth_token)

print("SID from .env:", account_sid)
print("Token from .env:", auth_token[:5] + "...")

message = client.messages.create(
    body="👋 Hello from your fish farm bot!",
    from_='whatsapp:+14155238886',
    to='whatsapp:+18027600986'

)

print(f"Message sent! SID: {message.sid}")
