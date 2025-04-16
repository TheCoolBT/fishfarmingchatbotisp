def generate_weekly_form(lang):
    form = []
    for i in range(1, 31):
        form.extend([
            {
                "key": f"fish_{i}_length",
                "name": f"Fish {i} Length (cm)" if lang == "en" else f"Panjang Ikan {i} (cm)",
                "prompt": f"📏 Type the length of Fish {i} in cm (e.g., 19.5)" if lang == "en" else f"📏 Ketik panjang Ikan {i} dalam cm (contoh: 19.5)",
                "require_photo": False
            },
            {
                "key": f"fish_{i}_weight",
                "name": f"Fish {i} Weight (grams)" if lang == "en" else f"Berat Ikan {i} (gram)",
                "prompt": (
                    f"⚖ Type the weight of Fish {i} and upload a photo with the fish on the scale"
                    if lang == "en" else
                    f"⚖ Bobot ikan {i}? Silakan unggah foto bersama hasil timbangan"
                ),
                "require_photo": True
            }
        ])
    return form

weekly_form_en = generate_weekly_form("en")
weekly_form_id = generate_weekly_form("id")
