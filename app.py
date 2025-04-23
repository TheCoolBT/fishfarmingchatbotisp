from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from dotenv import load_dotenv
from drive import log_reading, log_weekly, upload_photo
from forms.daily_form import daily_form_en, daily_form_id
from forms.weekly_form import weekly_form_en, weekly_form_id
from apscheduler.schedulers.background import BackgroundScheduler
from ai_helper import check_out_of_range, generate_recommendations, EXPERT_NUMBERS
from datetime import datetime
import random
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

def send_whatsapp_message(to, body):
    client.messages.create(
        from_="whatsapp:" + TWILIO_NUMBER,
        to="whatsapp:" + to,
        body=body
    )

def notify_experts(user_phone, data):
    alerts = check_out_of_range(data)
    all_keys = {
        "do": "DO (mg/L)",
        "ph": "pH",
        "temperature": "Suhu (°C)",
        "dead_fish": "Ikan Mati",
        "feeding_freq": "Frekuensi Pemberian Pakan",
        "feed_weight": "Berat Pakan (gram)",
        "inv_feed": "Jumlah Pakan Tersisa",
        "inv_rest": "Jumlah Pakan Baru",
    }

    summary = ""
    tanggal = format_date_indonesian()
    summary = f"📅 *{tanggal}*\n\n"

    if "UJI COBA" in user_phone:
        summary += "🧪 *PESAN INI HANYA UJI COBA*\n\n"

    summary += f"📡 *Laporan Harian* dari {user_phone}:\n"
    for key, label in all_keys.items():
        if key not in data or data[key] == "":
            continue

        value = data[key]
        emoji = "✅"
        note = ""

        if key in alerts:
            emoji = "❌"
            try:
                val = float(value)
                if val < alerts[key]["min"]:
                    note = " (terlalu rendah)"
                elif val > alerts[key]["max"]:
                    note = " (terlalu tinggi)"
            except:
                pass

        summary += f"{emoji} {label}: {value}{note}\n"

    # 🎥 Tambahkan link video jika ada
    video_link = data.get("general_video_photo")
    if video_link:
        summary += f"\n🎥 *Video Kondisi Air:*\n{video_link}"

    # 🤖 AI-generated troubleshooting (dalam bahasa Indonesia)
    recommendations = generate_recommendations(alerts, lang="id")
    if recommendations:
        rec_msg = "\n\n🧠 *Saran AI:*\n" + "\n".join(recommendations)
    else:
        rec_msg = "\n\n🧠 *Saran AI:*\nTidak ada anomali yang terdeteksi hari ini."

    # Kirim ke semua pakar
    full_message = summary + rec_msg
    for expert in EXPERT_NUMBERS:
        send_whatsapp_message(expert, full_message)


def generate_fake_daily_data():
    return {
        "do": round(random.uniform(3.0, 8.5), 1),
        "ph": round(random.uniform(6.0, 8.5), 1),
        "temperature": round(random.uniform(25, 33), 1),
        "dead_fish": random.randint(0, 5),
        "feeding_freq": random.choice([2, 3, 4]),
        "feed_weight": random.randint(80, 150),
        "inv_feed": random.randint(0, 50),
        "inv_rest": random.randint(50, 300),
        "general_video_photo": "https://drive.google.com/uc?id=fake-video-link-test"  # fake placeholder
    }


def format_date_indonesian():
    hari = {
        "Monday": "Senin",
        "Tuesday": "Selasa",
        "Wednesday": "Rabu",
        "Thursday": "Kamis",
        "Friday": "Jumat",
        "Saturday": "Sabtu",
        "Sunday": "Minggu"
    }
    bulan = {
        1: "Januari", 2: "Februari", 3: "Maret", 4: "April",
        5: "Mei", 6: "Juni", 7: "Juli", 8: "Agustus",
        9: "September", 10: "Oktober", 11: "November", 12: "Desember"
    }

    now = datetime.now()
    nama_hari = hari[now.strftime("%A")]
    nama_bulan = bulan[now.month]
    return f"{nama_hari}, {now.day:02d} {nama_bulan} {now.year}"


def send_daily_reminder():
    recipients = ["+18027600986","+628170073790"]
    for number in recipients:
        send_whatsapp_message(number, "🔔 Sekarang waktunya mengisi formulir harian!\n📨 It's time to fill out the daily form!")
        user_state[number] = {
            "lang": None,
            "form_type": "daily",
            "responses": {},
            "media": {},
            "stage": "lang_direct_daily"
        }
        send_whatsapp_message(number, "🌐 Please select a language / Silakan pilih bahasa:\n1. 🇮🇩 Bahasa Indonesia\n2. 🇬🇧 English")

def send_weekly_reminder():
    recipients = ["+18027600986","+6285692351792","+628170073790"]
    for number in recipients:
        send_whatsapp_message(number, "📆 Jangan lupa isi formulir mingguan hari ini!\n📆 Don't forget to fill out the weekly form today!")
        user_state[number] = {
            "lang": None,
            "form_type": "weekly",
            "responses": {},
            "media": {},
            "step": 0,
            "stage": "lang_direct_weekly"
        }
        send_whatsapp_message(number, "🌐 Please select a language / Silakan pilih bahasa:\n1. 🇮🇩 Bahasa Indonesia\n2. 🇬🇧 English")


def send_reactivation_reminder():
    recipients = ["+18027600986", "+628170073790"]  # Add more numbers as needed
    for number in recipients:
        send_whatsapp_message(
            number,
            "🔄 *Pengingat Aktivasi Bot*\n"
            "Silakan kirim *join sense-believed* ke bot ini untuk menjaga koneksi tetap aktif. "
            "Pengingat ini akan muncul setiap 48 jam."
        )

def schedule_jobs():
    scheduler = BackgroundScheduler()

    # Daily & weekly reminders
    scheduler.add_job(send_daily_reminder, 'cron', hour=22, minute=30)  # 5:30 AM UTC+7
    scheduler.add_job(send_daily_reminder, 'cron', hour=7, minute=30)   # 2:30 PM UTC+7
    scheduler.add_job(send_weekly_reminder, 'cron', day_of_week='sun', hour=5, minute=0)  # 12 PM UTC+7

    # 🔁 Reactivation message every 48 hours at 8:00 AM UTC+7 (which is 1:00 AM UTC)
    scheduler.add_job(
        send_reactivation_reminder,
        'interval',
        hours=48,
        start_date='2025-04-17T01:00:00'  # Start at 1:00 AM UTC = 8:00 AM UTC+7
    )

    scheduler.start()


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


@app.route("/webhook", methods=["POST"])
def whatsapp_reply():
    sender = request.form.get("From").replace("whatsapp:", "")
    msg_text = request.form.get("Body", "").strip().lower()
    media_url = request.form.get("MediaUrl0")
    resp = MessagingResponse()
    msg = resp.message()

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
            "do": "3.2",  # sengaja di bawah ambang
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

    # Harian (unordered)
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


if __name__ == '__main__':
    send_daily_reminder()
    schedule_jobs()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
