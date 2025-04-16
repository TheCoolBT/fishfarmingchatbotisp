import os
from openai import OpenAI
from thresholds import SOP_THRESHOLDS

# Twilio numbers of experts who should receive alerts
EXPERT_NUMBERS = ["+18027600986"]

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

def generate_recommendations(alerts):
    """Call GPT-4 (or GPT-3.5) to generate troubleshooting steps based on alerts."""
    if not alerts:
        return []

    # Prompt construction
    prompt = (
        "You are an aquaculture technician AI. Given the following out-of-range water quality readings, "
        "provide brief, actionable troubleshooting steps the farmer should take. "
        "Respond in bullet points.\n\n"
    )

    for key, val in alerts.items():
        prompt += f"- {key.upper()}: {val}\n"

    prompt += "\nOnly include actions directly related to the measurements. Keep the tone professional and concise."

    try:
        response = client.chat.completions.create(
            model="gpt-4",  # Use "gpt-3.5-turbo" if needed
            messages=[{"role": "user", "content": prompt}],
            max_tokens=250,
            temperature=0.5
        )
        content = response.choices[0].message.content
        return content.strip().split("\n")
    except Exception as e:
        return [f"⚠️ AI error: {e}"]
