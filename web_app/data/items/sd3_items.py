"""
مقیاس مثلث تاریک کوتاه (SD3)
Jones & Webster (2010), Journal of Research in Personality
ترجمه‌ی فارسی: Jonason et al. (2014)

27 گویه، 5 نقطه‌ای (1=کاملاً مخالفم تا 5=کاملاً موافقم)
هر زیرمقیاس: 9 گویه
دامنه هر زیرمقیاس: 9 تا 45
"""

SD3_LIKERT_LABELS = {
    1: "کاملاً مخالفم",
    2: "مخالفم",
    3: "نه موافقم و نه مخالفم",
    4: "موافقم",
    5: "کاملاً موافقم",
}

SD3_FACTORS = {
    "machiavellianism": "ماکیاولیسم",
    "narcissism": "خودشیفتگی",
    "psychopathy": "سایکوپاتی",
}


SD3_ITEMS = [
    # ---------- ماکیاولیسم (9 گویه) ----------
    {"id": 1, "factor": "machiavellianism", "reverse": False,
     "text": "به زبان آوردن اسرار خود کار عاقلانه‌ای نیست."},
    {"id": 2, "factor": "machiavellianism", "reverse": False,
     "text": "برای باز کردن راه خودم دوست دارم دیگران را دستکاری کنم."},
    {"id": 3, "factor": "machiavellianism", "reverse": False,
     "text": "هر کاری که لازم است باید انجام داد تا افراد مهم طرف شما را بگیرند."},
    {"id": 4, "factor": "machiavellianism", "reverse": False,
     "text": "از تعارض مستقیم با افراد باید اجتناب کرد، چون ممکن است در آینده به درد بخورند."},
    {"id": 5, "factor": "machiavellianism", "reverse": False,
     "text": "نگه‌داشتن اطلاعاتی که می‌شود از آن‌ها علیه افراد استفاده کرد، کار عاقلانه‌ای است."},
    {"id": 6, "factor": "machiavellianism", "reverse": False,
     "text": "آدم باید صبر کند تا فرصت مناسب برای تلافی کردن پیش بیاید."},
    {"id": 7, "factor": "machiavellianism", "reverse": False,
     "text": "چیزهایی هست که برای حفظ حسن شهرت خود باید از دیگران مخفی نگه داشت."},
    {"id": 8, "factor": "machiavellianism", "reverse": False,
     "text": "مطمئن بشوید که برنامه‌های شما برای خودتان سودمند باشد و نه دیگران."},
    {"id": 9, "factor": "machiavellianism", "reverse": False,
     "text": "بیشتر آدم‌ها را می‌شود دستکاری کرد و سرکار گذاشت."},

    # ---------- خودشیفتگی (9 گویه) ----------
    {"id": 10, "factor": "narcissism", "reverse": False,
     "text": "دیگران مرا به‌عنوان یک رهبر مادرزاد می‌بینند."},
    {"id": 11, "factor": "narcissism", "reverse": True,
     "text": "از این‌که مرکز توجه‌ها باشم، متنفرم."},
    {"id": 12, "factor": "narcissism", "reverse": False,
     "text": "خیلی از فعالیت‌های گروهی به نظر من احمقانه است."},
    {"id": 13, "factor": "narcissism", "reverse": False,
     "text": "من می‌دانم که فرد بخصوصی هستم، چون دیگران هم دایم به من همین را می‌گویند."},
    {"id": 14, "factor": "narcissism", "reverse": False,
     "text": "دوست دارم با افراد مهم آشنا و حشر و نشر داشته باشم."},
    {"id": 15, "factor": "narcissism", "reverse": True,
     "text": "اگر کسی از من تعریف کند، احساس خجالت می‌کنم."},
    {"id": 16, "factor": "narcissism", "reverse": False,
     "text": "من با افراد مشهور مقایسه شده‌ام و می‌شوم."},
    {"id": 17, "factor": "narcissism", "reverse": True,
     "text": "من یک آدم معمولی هستم."},
    {"id": 18, "factor": "narcissism", "reverse": False,
     "text": "روی گرفتن احترامی که شایسته آن هستم از دیگران اصرار می‌کنم."},

    # ---------- سایکوپاتی (9 گویه) ----------
    {"id": 19, "factor": "psychopathy", "reverse": False,
     "text": "دوست دارم از افراد صاحب قدرت انتقام بگیرم."},
    {"id": 20, "factor": "psychopathy", "reverse": True,
     "text": "از موقعیت‌های خطرناک اجتناب می‌کنم."},
    {"id": 21, "factor": "psychopathy", "reverse": False,
     "text": "تلافی باید سریع و شدید باشد."},
    {"id": 22, "factor": "psychopathy", "reverse": False,
     "text": "مردم اغلب به من می‌گویند که قابل کنترل نیستم."},
    {"id": 23, "factor": "psychopathy", "reverse": False,
     "text": "این حقیقت دارد که من می‌توانم با دیگران بی‌ادبانه رفتار کنم."},
    {"id": 24, "factor": "psychopathy", "reverse": False,
     "text": "کسانی که با من در می‌افتند همیشه پشیمان می‌شوند."},
    {"id": 25, "factor": "psychopathy", "reverse": True,
     "text": "من هیچ‌وقت با جرایم و مسایل قانونی درگیر نبوده‌ام."},
    {"id": 26, "factor": "psychopathy", "reverse": False,
     "text": "از ارتباط جنسی با افرادی که حتی به سختی می‌شناسم، لذت می‌برم."},
    {"id": 27, "factor": "psychopathy", "reverse": False,
     "text": "برای رسیدن به خواسته‌ام، هر چیزی که لازم باشد می‌گویم."},
]


def compute_sd3_scores(answers: dict) -> dict:
    """
    محاسبه‌ی نمره‌ی سه زیرمقیاس SD3.
    answers: {item_id: value in 1..5}
    """
    factor_values = {k: [] for k in SD3_FACTORS.keys()}

    for item in SD3_ITEMS:
        iid = item["id"]
        if iid not in answers:
            continue
        raw = answers[iid]
        value = (6 - raw) if item["reverse"] else raw
        factor_values[item["factor"]].append(value)

    scores = {}
    for code, values in factor_values.items():
        if values:
            scores[code] = round(sum(values) / len(values), 2)
        else:
            scores[code] = 0.0
    return scores