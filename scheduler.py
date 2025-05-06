from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
from ai_helper import check_out_of_range, generate_recommendations, EXPERT_NUMBERS
from forms.daily_form import daily_form_id
from forms.weekly_form import weekly_form_id
from drive import log_reading, log_weekly, upload_photo
import random
import os

from twilio.rest import Client
from dotenv import load_dotenv
load_dotenv()

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
client = Client(TWILIO_SID, TWILIO_AUTH)

user_state = {}
last_activity = {}
last_reactivation_times = {}

scheduler = BackgroundScheduler()
scheduler.start()


def send_whatsapp_message(to, body):
    client.messages.create(
        from_="whatsapp:" + TWILIO_NUMBER,
        to="whatsapp:" + to,
        body=body
    )


def format_date_indonesian():
    hari = {
        "Monday": "Senin", "Tuesday": "Selasa", "Wednesday": "Rabu",
        "Thursday": "Kamis", "Friday": "Jumat", "Saturday": "Sabtu", "Sunday": "Minggu"
    }
    bulan = {
        1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
        7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"
    }
    now = datetime.now()
    return f"{hari[now.strftime('%A')]}, {now.day:02d} {bulan[now.month]} {now.year}"


def notify_experts(user_phone, data):
    alerts = check_out_of_range(data)
    all_keys = {
        "do": "DO (mg/L)", "ph": "pH", "temperature": "Suhu (°C)",
        "dead_fish": "Ikan Mati", "feeding_freq": "Frekuensi Pemberian Pakan",
        "feed_weight": "Berat Pakan (gram)", "inv_feed": "Jumlah Pakan Tersisa",
        "inv_rest": "Jumlah Pakan Baru",
    }

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

    video_link = data.get("general_video_photo")
    if video_link:
        summary += f"\n🎥 *Video Kondisi Air:*\n{video_link}"

    recommendations = generate_recommendations(alerts, lang="id")
    if recommendations:
        rec_msg = "\n\n🧠 *Saran AI:*\n" + "\n".join(recommendations)
    else:
        rec_msg = "\n\n🧠 *Saran AI:*\nTidak ada anomali yang terdeteksi hari ini."

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
        "general_video_photo": "https://drive.google.com/uc?id=fake-video-link-test"
    }


def send_daily_reminder():
    recipients = ["+18027600986", "+628170073790"]
    for number in recipients:
        send_whatsapp_message(number, "🔔 Sekarang waktunya mengisi formulir harian!\n📨 It's time to fill out the daily form!")
        user_state[number] = {
            "lang": None, "form_type": "daily", "responses": {},
            "media": {}, "stage": "lang_direct_daily"
        }
        send_whatsapp_message(number, "🌐 Please select a language / Silakan pilih bahasa:\n1. 🇮🇩 Bahasa Indonesia\n2. 🇬🇧 English")


def send_weekly_reminder():
    print("📆 Sending weekly reminder...")
    recipients = ["+18027600986", "+6285692351792", "+628170073790"]
    for number in recipients:
        send_whatsapp_message(
            number,
            "📆 *Jangan lupa isi formulir mingguan hari ini!*\nSilakan balas pesan ini untuk memulai pengisian."
        )
        user_state[number] = {
            "lang": None, "form_type": "weekly", "responses": {},
            "media": {}, "step": 0, "stage": "lang_direct_weekly"
        }
        send_whatsapp_message(number, "🌐 Please select a language / Silakan pilih bahasa:\n1. 🇮🇩 Bahasa Indonesia\n2. 🇬🇧 English")


def send_sandbox_reactivation_warning(phone):
    send_whatsapp_message(
        phone,
        "⚠️ *Pengingat Aktivasi WhatsApp Bot*\n"
        "Dalam 1 jam koneksi akan kedaluwarsa.\n"
        "Segera kirim pesan *join sense-believed* untuk menjaga koneksi tetap aktif."
    )


def update_last_reactivation(phone):
    last_reactivation_times[phone] = datetime.utcnow()
    job_id = f"sandbox_reactivation_{phone}"
    # Remove any previous job for this user
    try:
        scheduler.remove_job(job_id)
    except:
        pass
    run_time = datetime.utcnow() + timedelta(hours=71)
    scheduler.add_job(
        send_sandbox_reactivation_warning,
        'date',
        run_date=run_time,
        args=[phone],
        id=job_id
    )


def update_last_activity(phone):
    last_activity[phone] = datetime.utcnow()
    schedule_sandbox_reminder(phone)


def schedule_sandbox_reminder(phone):
    job_id = f"sandbox_activity_reminder_{phone}"
    for job in scheduler.get_jobs():
        if job.id == job_id:
            scheduler.remove_job(job_id)
    run_time = datetime.utcnow() + timedelta(seconds=10)
    scheduler.add_job(
        send_sandbox_reactivation_warning,
        'date',
        run_date=run_time,
        args=[phone],
        id=job_id
    )


def schedule_jobs():
    scheduler.add_job(send_daily_reminder, 'cron', hour=22, minute=30)
    scheduler.add_job(send_daily_reminder, 'cron', hour=7, minute=30)
    scheduler.add_job(send_weekly_reminder, 'cron', day_of_week='sun', hour=5, minute=0)
