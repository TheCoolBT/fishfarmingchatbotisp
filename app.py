from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
from forms.daily_form import daily_form_id
from forms.weekly_form import weekly_form_id
from drive import log_reading, log_weekly, upload_photo
from scheduler import (
    send_whatsapp_message,
    notify_experts,
    generate_fake_daily_data,
    send_daily_reminder,
    schedule_jobs,
    update_last_activity
)
import os
import re
from datetime import datetime

load_dotenv()
app = Flask(__name__)
user_state = {}

# === Utilities ===

def extract_number(text):
    match = re.search(r"[-+]?\d*\.\d+|\d+", text)
    return match.group() if match else None

def get_pending_fields(responses, form):
    return [f for f in form if f["key"] not in responses]

def send_field_list(msg, state):
    form = state["form"]
    pending = get_pending_fields(state["responses"], form)
    if not pending:
        return
    body = "❓ Apa yang ingin Anda jawab selanjutnya?\n"
    for i, field in enumerate(pending, 1):
        body += f"{i}. {field['name']}\n"
    msg.body(body.strip())

# === Webhook Route ===

@app.route("/webhook", methods=["POST"])
def whatsapp_reply():
    sender = request.form.get("From").replace("whatsapp:", "")
    msg_text = request.form.get("Body", "").strip().lower()
    media_url = request.form.get("MediaUrl0")
    resp = MessagingResponse()
    msg = resp.message()

    update_last_activity(sender)

    if msg_text in ["exit", "keluar"]:
        user_state[sender] = {"lang": None, "form_type": None, "responses": {}, "media": {}, "stage": "lang"}
        msg.body("🔄 Formulir diulang.\n🌐 Pilih bahasa:\n1. 🇮🇩 Bahasa Indonesia")
        return str(resp)

    if msg_text == "test":
        user_state[sender] = {"lang": None, "form_type": None, "responses": {}, "media": {}, "stage": "lang"}
        msg.body("🌐 Pilih bahasa:\n1. 🇮🇩 Bahasa Indonesia")
        return str(resp)

    if msg_text == "test troubleshoot":
        fake_data = {
            "do": "3.2",
            "ph": "7.2",
            "temperature": "28.0"
        }
        notify_experts(sender, fake_data)
        msg.body("✅ Pengujian alert teknisi terkirim dengan nilai DO = 3.2")
        return str(resp)

    if msg_text == "test health status":
        fake_data = generate_fake_daily_data()
        notify_experts(sender + " (UJI COBA)", fake_data)
        msg.body("✅ Laporan uji coba kesehatan harian dikirim ke teknisi.")
        return str(resp)

    if sender not in user_state:
        msg.body("❓ Tunggu pengingat terjadwal atau ketik 'test' untuk memulai secara manual.")
        return str(resp)

    state = user_state[sender]

    # === Language Selection Stage ===
    if state["stage"].startswith("lang"):
        if msg_text in ["1", "indonesian", "bahasa indonesia"]:
            state["lang"] = "id"
        else:
            msg.body("❓ Balas dengan 1 untuk Bahasa Indonesia")
            return str(resp)

        if state["stage"] == "lang":
            state["stage"] = "form_select"
            msg.body("📋 Pilih jenis formulir:\n1. Harian\n2. Mingguan")
        elif state["stage"] == "lang_direct_daily":
            state["form"] = daily_form_id
            state["stage"] = "in_progress"
            send_field_list(msg, state)
        elif state["stage"] == "lang_direct_weekly":
            state["form"] = weekly_form_id
            state["stage"] = "weekly_in_progress"
            state["step"] = 0
            msg.body(state["form"][0]["prompt"])
        return str(resp)

    # === Form Selection Stage ===
    if state["stage"] == "form_select":
        if msg_text in ["1", "daily", "harian"]:
            state["form_type"] = "daily"
            state["form"] = daily_form_id
            state["stage"] = "in_progress"
            send_field_list(msg, state)
        elif msg_text in ["2", "weekly", "mingguan"]:
            state["form_type"] = "weekly"
            state["form"] = weekly_form_id
            state["stage"] = "weekly_in_progress"
            state["step"] = 0
            msg.body(state["form"][0]["prompt"])
        else:
            msg.body("❓ Balas dengan 1 untuk Harian atau 2 untuk Mingguan")
        return str(resp)

    # === Weekly Form (Ordered) ===
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
                for k, url in state["media"].items():
                    link = upload_photo(field_name=k, phone=sender, date=datetime.now().strftime("%Y-%m-%d"), file_url=url)
                    if link:
                        state["responses"][f"{k}_photo"] = link
                log_weekly(sender, state["responses"])
                msg.body("✅ Terima kasih! Formulir mingguan selesai.\n📨 Kirim pesan apa pun untuk mulai ulang.")
                user_state[sender] = {"lang": None, "form_type": None, "responses": {}, "media": {}, "stage": "lang"}
            return str(resp)
        else:
            msg.body("🔢 Masukkan angka untuk: {}".format(current["name"]) if not has_number else "📸 Unggah foto untuk: {}".format(current["name"]))
            return str(resp)

    # === Daily Form (Unordered) ===
    form = daily_form_id
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
                    for k, url in state["media"].items():
                        link = upload_photo(field_name=k, phone=sender, date=datetime.now().strftime("%Y-%m-%d"), file_url=url)
                        if link:
                            state["responses"][f"{k}_photo"] = link
                    log_reading(sender, state["responses"])
                    notify_experts(sender, state["responses"])
                    msg.body("✅ Terima kasih telah mengisi formulir harian!\n📨 Kirim pesan apa pun untuk mulai ulang.")
                    user_state[sender] = {"lang": None, "form_type": None, "responses": {}, "media": {}, "stage": "lang"}
            else:
                if key == "general_video" and not has_photo:
                    msg.body("📹 Silakan unggah video air kolam.")
                elif not has_number:
                    msg.body("🔢 Masukkan angka untuk: {}".format(current["name"]))
                elif photo_required and not has_photo:
                    msg.body("📸 Unggah foto untuk: {}".format(current["name"]))
        else:
            send_field_list(msg, state)

    return str(resp)

# === App Entry Point ===

if __name__ == '__main__':
    send_daily_reminder()  # optional manual start
    schedule_jobs()        # load all reminders
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
