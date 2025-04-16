# force rebuild
from thresholds import SOP_THRESHOLDS

EXPERT_NUMBERS = ["+18027600986"]

def check_out_of_range(data):
    alerts = {}
    for key, val in data.items():
        try:
            value = float(val)
            if key in SOP_THRESHOLDS:
                limits = SOP_THRESHOLDS[key]
                if value < limits["min"] or value > limits["max"]:
                    alerts[key] = value
        except:
            continue
    return alerts

def generate_recommendations(alerts):
    suggestions = {
        "do": "🌀 Dissolved Oxygen is out of range. Try increasing aeration, checking pump clogging, or reducing biomass density.",
        "ph": "💧 pH level is abnormal. Consider partial water replacement or adding buffer agents like baking soda.",
        "temperature": "🌡️ Temperature is abnormal. Check for excessive sunlight exposure or adjust pond shading."
    }
    return [suggestions[key] for key in alerts if key in suggestions]
