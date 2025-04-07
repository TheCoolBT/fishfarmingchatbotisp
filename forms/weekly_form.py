def generate_weekly_form(lang):
    form = []
    for i in range(1, 31):
        form.extend([
            {
                "key": f"fish_{i}_photo",
                "name": f"Fish {i} Photo" if lang == "en" else f"Foto Ikan {i}",
                "prompt": f"📸 Send a photo of Fish {i}" if lang == "en" else f"📸 Kirim foto Ikan {i}",
                "require_photo": True
            },
            {
                "key": f"fish_{i}_weight",
                "name": f"Fish {i} Weight (grams)" if lang == "en" else f"Berat Ikan {i} (gram)",
                "prompt": f"⚖ Type the weight of Fish {i} in grams (e.g., 157)" if lang == "en" else f"⚖ Ketik berat Ikan {i} dalam gram (contoh: 157)",
                "require_photo": False
            },
            {
                "key": f"fish_{i}_length",
                "name": f"Fish {i} Length (cm)" if lang == "en" else f"Panjang Ikan {i} (cm)",
                "prompt": f"📏 Type the length of Fish {i} in cm (e.g., 19.5)" if lang == "en" else f"📏 Ketik panjang Ikan {i} dalam cm (contoh: 19.5)",
                "require_photo": False
            }
        ])
    return form

weekly_form_en = generate_weekly_form("en")
weekly_form_id = generate_weekly_form("id")
