"""
پرسشنامه‌ی بازخورد پس از بازی — نسخه‌ی کوتاه‌شده
==================================================
هدف: سنجش تجربه‌ی شرکت‌کننده از بازی

ساختار:
- 12 گویه‌ی بسته (لیکرت 5 نقطه‌ای)
- 2 سؤال باز
- 1 سؤال دموگرافیک تکمیلی

نکته‌ی پژوهشی:
- نسخه‌ی اقتباسی از پرسشنامه‌ی 25 گویه‌ای
- ID های اصلی حفظ شده‌اند (برای سازگاری با داده‌های قبلی)
- پس از جمع‌آوری داده، آلفای کرونباخ هر زیرمقیاس را محاسبه کنید
"""

# ============================================================
# مقیاس لیکرت
# ============================================================
FEEDBACK_LIKERT_LABELS = {
    1: "کاملاً مخالفم",
    2: "مخالفم",
    3: "نه موافقم و نه مخالفم",
    4: "موافقم",
    5: "کاملاً موافقم",
}

# ============================================================
# زیرمقیاس‌ها
# ============================================================
FEEDBACK_SUBSCALES = {
    "realism": "واقع‌گرایی",
    "engagement": "درگیری و انگیزه",
    "empathy": "همدلی با شخصیت‌ها",
    "perceived_validity": "ادراک از اعتبار",
    "internal_consistency": "درستی درونی",
}

# ============================================================
# گویه‌های بسته (12 گویه)
# ============================================================
FEEDBACK_ITEMS = [
    # ---------- واقع‌گرایی (3 گویه) ----------
    {"id": 1, "subscale": "realism", "reverse": False,
     "text": "سناریوهای بازی، شبیه موقعیت‌های واقعی محیط کار بودند."},
    {"id": 4, "subscale": "realism", "reverse": False,
     "text": "تصمیم‌هایی که از من خواسته شد، در محیط کار واقعی "
             "هم اتفاق می‌افتد."},
    {"id": 5, "subscale": "realism", "reverse": False,
     "text": "فضای داستان (ایستگاه فضایی)، حس باورپذیری داشت."},

    # ---------- درگیری و انگیزه (3 گویه) ----------
    {"id": 6, "subscale": "engagement", "reverse": False,
     "text": "هنگام بازی، کاملاً غرق در داستان شدم."},
    {"id": 8, "subscale": "engagement", "reverse": False,
     "text": "هنگام تصمیم‌گیری، احساس می‌کردم واقعاً مهم است."},
    {"id": 9, "subscale": "engagement", "reverse": True,
     "text": "بازی برایم خسته‌کننده بود."},

    # ---------- همدلی با شخصیت‌ها (2 گویه) ----------
    {"id": 11, "subscale": "empathy", "reverse": False,
     "text": "با لی احساس همدلی کردم."},
{"id": 14, "subscale": "empathy", "reverse": False,
 "text": "تصمیم‌های داستان باعث شد به عواقب انتخاب‌هایم در دنیای واقعی فکر کنم."},

    # ---------- ادراک از اعتبار (2 گویه) ----------
{"id": 16, "subscale": "perceived_validity", "reverse": False,
 "text": "فکر می‌کنم این بازی می‌تواند شیوه‌ی تصمیم‌گیری افراد در موقعیت‌های واقعی را به‌خوبی نشان دهد."},
    {"id": 20, "subscale": "perceived_validity", "reverse": False,
     "text": "اگر یک سازمان از این بازی برای انتخاب کارمند "
             "استفاده کند، به نظر من منصفانه است."},

    # ---------- درستی درونی (2 گویه) ----------
    {"id": 22, "subscale": "internal_consistency", "reverse": False,
     "text": "تصمیم‌هایم با ارزش‌های واقعی من همخوان بود."},
   {"id": 25, "subscale": "internal_consistency", "reverse": True,
 "text": "اگر در موقعیت ارزیابی استخدامی باشم شاید تصمیم‌های متفاوتی نشان بدهم."},
]

# ============================================================
# سؤالات باز (2 سؤال)
# ============================================================
FEEDBACK_OPEN_QUESTIONS = [
    {
        "id": "open_1",
        "text": "کدام سناریو بیش‌ترین تأثیر را روی شما گذاشت؟ چرا؟",
    },
    {
        "id": "open_5",
        "text": "چه پیشنهادی برای بهبود بازی دارید؟",
    },
]

# ============================================================
# اطلاعات دموگرافیک تکمیلی (1 سؤال)
# ============================================================
FEEDBACK_DEMOGRAPHIC_ITEMS = [
    {
        "id": "prior_gaming",
        "text": "تجربه‌ی قبلی با بازی‌های ویدیویی:",
        "options": [
            "هیچ", "کم", "متوسط", "زیاد", "خیلی زیاد",
        ],
    },
]


def compute_feedback_scores(answers: dict) -> dict:
    """
    محاسبه‌ی نمره‌ی هر زیرمقیاس.
    answers: {item_id: value in 1..5}
    Returns: {
        "subscale_scores": {code: mean},
        "overall_score": mean of means
    }
    """
    subscale_values = {k: [] for k in FEEDBACK_SUBSCALES.keys()}

    for item in FEEDBACK_ITEMS:
        iid = item["id"]
        if iid not in answers:
            continue
        raw = answers[iid]
        value = (6 - raw) if item["reverse"] else raw
        subscale_values[item["subscale"]].append(value)

    scores = {}
    for code, values in subscale_values.items():
        if values:
            scores[code] = round(sum(values) / len(values), 2)
        else:
            scores[code] = 0.0

    valid = [v for v in scores.values() if v > 0]
    overall = round(sum(valid) / len(valid), 2) if valid else 0.0

    return {
        "subscale_scores": scores,
        "overall_score": overall,
    }