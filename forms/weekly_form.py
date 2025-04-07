weekly_form_en = [
    {
        "key": f"fish_{i}_photo",
        "name": f"Fish {i} Photo",
        "prompt": f"📸 Send a photo of Fish {i}"
    }
    for i in range(1, 31)
] + [
    {
        "key": f"fish_{i}_weight",
        "name": f"Fish {i} Weight",
        "prompt": f"⚖ Then type the weight of Fish {i} in grams (e.g., 157)"
    }
    for i in range(1, 31)
] + [
    {
        "key": f"fish_{i}_length",
        "name": f"Fish {i} Length",
        "prompt": f"📏 Then type the length of Fish {i} in cm (e.g., 19.5)"
    }
    for i in range(1, 31)
]

weekly_form_id = [
    {
        "key": f"ikan_{i}_photo",
        "name": f"Foto Ikan {i}",
        "prompt": f"📸 Kirim foto Ikan {i}"
    }
    for i in range(1, 31)
] + [
    {
        "key": f"ikan_{i}_berat",
        "name": f"Berat Ikan {i}",
        "prompt": f"⚖ Lalu ketik berat Ikan {i} dalam gram (contoh: 157)"
    }
    for i in range(1, 31)
] + [
    {
        "key": f"ikan_{i}_panjang",
        "name": f"Panjang Ikan {i}",
        "prompt": f"📏 Lalu ketik panjang Ikan {i} dalam cm (contoh: 19.5)"
    }
    for i in range(1, 31)
]
