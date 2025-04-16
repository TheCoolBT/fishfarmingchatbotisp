import os
import openai
from thresholds import SOP_THRESHOLDS

# Expert numbers to receive alerts
EXPERT_NUMBERS = ["+18027600986"]  # ← Add others if needed

# Load OpenAI API key from environment
openai.api_key = os.getenv("OPENAI_API_KEY")

def check_out_of_range(data):
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
    """
    Uses OpenAI's GPT model to generate troubleshooting suggestions based on alerts.
    Returns a list of bullet point strings.
    """
    if not alerts:
        return []

    prompt = (
        "You are an aquaculture technician AI. Given the following out-of-range water quality readings, "
        "provide brief, practical troubleshooting suggestions the farmer can take. Respond in bullet points.\n\n"
    )

    for key, val in alerts.items():
        prompt += f"- {key.upper()}: {val}\n"

    prompt += "\nOnly include actions that are directly related to the measurements. Keep it concise and professional."

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",  # You can switch to "gpt-3.5-turbo" if needed
            messages=[{"role": "user", "content": prompt}],
            max_tokens=250,
            temperature=0.5
        )
        content = response['choices'][0]['message']['content']
        return content.strip().split("\n")
    except Exception as e:
        return [f"⚠️ AI error: {e}"]
