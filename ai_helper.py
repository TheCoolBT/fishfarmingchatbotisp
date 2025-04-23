import os
from openai import OpenAI
from thresholds import SOP_THRESHOLDS
from drive import get_recent_trends


# Twilio numbers of experts who should receive alerts
EXPERT_NUMBERS = ["+18027600986","+628170073790","+6285692867890"]

# Initialize OpenAI client with API key from environment
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def check_out_of_range(data):
    """Check which values fall outside SOP limits."""
    alerts = {}
    for key, val in data.items():
        try:
            value = float(val)
            if key in SOP_THRESHOLDS:
                limits = SOP_THRESHOLDS[key]
                if value < limits["min"] or value > limits["max"]:
                    alerts[key] = value
        except ValueError:
            continue
    return alerts

def generate_recommendations(alerts, lang="en"):
    if not alerts:
        return []

    # Fetch sheet context
    trend_text = get_recent_trends()

    # Build the prompt
    if lang == "id":
        prompt = (
            "Kamu adalah AI teknisi akuakultur. Berdasarkan data kualitas air di bawah ini (yang berada di luar ambang batas) "
            "dan tren data terbaru dari tambak, buat hipotesis dan saran perbaikan. Jawab dalam bentuk poin-poin.\n\n"
        )
    else:
        prompt = (
            "You are an aquaculture technician AI. Based on the following out-of-range water quality readings and recent farm trends, "
            "generate hypotheses and troubleshooting actions. Respond in bullet points.\n\n"
        )

    for key, val in alerts.items():
        prompt += f"- {key.upper()}: {val}\n"

    prompt += f"\nRecent data:\n{trend_text}"
    prompt += "\n\nOnly include specific, actionable suggestions based on the trends and values."

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=250,
            temperature=0.5,
        )
        content = response.choices[0].message.content
        return content.strip().split("\n")
    except Exception as e:
        return [f"⚠️ Kesalahan AI: {e}" if lang == "id" else f"⚠️ AI error: {e}"]

