"""
مقیاس مطلوبیت اجتماعی — فرم کوتاه 9 گویه‌ای
Crowne & Marlowe (1960) — نسخه‌ی فارسی سرمدی و همکاران (1392)

پاسخ‌ها: درست (True) / غلط (False)
نمره‌گذاری:
  - گویه‌های 1, 3, 4, 6, 9: پاسخ "درست" = 1 نمره
  - گویه‌های 2, 5, 7, 8: پاسخ "غلط" = 1 نمره
دامنه: 0 تا 9
"""

SD_ITEMS = [
    {"id": 1, "score_on_true": True,
     "text": "قبل از انتخاب یا رای دادن، شرایط و خصوصیات همه نامزدهای "
             "انتخاباتی را بررسی می‌کنم."},
    {"id": 2, "score_on_true": False,
     "text": "موقعیت‌هایی بوده است که من از شخصی بهره‌برداری "
             "کرده‌ام."},
    {"id": 3, "score_on_true": True,
     "text": "هرگز بغض و نفرت از کسی نداشته‌ام."},
    {"id": 4, "score_on_true": True,
     "text": "صرف‌نظر از این‌که با چه کسی صحبت می‌کنم، همیشه "
             "شنونده‌ی خوبی هستم."},
    {"id": 5, "score_on_true": False,
     "text": "اگر بتوانم بدون دادن بلیت وارد سینمایی بشوم و "
             "مطمئن باشم که کسی مرا نمی‌بیند، احتمالاً این کار "
             "را می‌کنم."},
    {"id": 6, "score_on_true": True,
     "text": "هرگاه اشتباهی می‌کنم، همیشه مشتاقانه به آن "
             "اعتراف می‌کنم."},
    {"id": 7, "score_on_true": False,
     "text": "گاه‌به‌گاه سعی می‌کنم بیشتر تسویه حساب کنم تا "
             "گذشت یا فراموش کنم."},
    {"id": 8, "score_on_true": False,
     "text": "گاه فکر می‌کنم که مردم هنگامی که دچار مصیبتی "
             "می‌شوند در واقع مستحق آن بوده‌اند."},
    {"id": 9, "score_on_true": True,
     "text": "هرگز آگاهانه چیزی نگفته‌ام که موجب رنجش احساسات "
             "فردی دیگر شوم."},
]


def compute_sd_score(answers: dict) -> dict:
    """
    محاسبه‌ی نمره‌ی مطلوبیت اجتماعی.
    answers: {item_id: True/False}
    Returns: {"score": 0-9}
    """
    score = 0
    per_item = {}
    for item in SD_ITEMS:
        iid = item["id"]
        val = answers.get(iid)
        if val is None:
            per_item[iid] = 0
            continue
        # ✅ پاسخ "درست" = True ، "غلط" = False
        if item["score_on_true"] and val is True:
            per_item[iid] = 1
            score += 1
        elif (not item["score_on_true"]) and val is False:
            per_item[iid] = 1
            score += 1
        else:
            per_item[iid] = 0
    return {"score": score, "max_score": 9, "per_item": per_item}