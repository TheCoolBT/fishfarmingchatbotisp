from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_recommendations(alerts):
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
        response = client.chat.completions.create(
            model="gpt-4",  # or "gpt-3.5-turbo"
            messages=[{"role": "user", "content": prompt}],
            max_tokens=250,
            temperature=0.5,
        )
        content = response.choices[0].message.content
        return content.strip().split("\n")
    except Exception as e:
        return [f"⚠️ AI error: {e}"]
