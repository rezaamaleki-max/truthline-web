"""
پایان روایی بازی — نسخه‌ی وب
=============================
بر اساس روابط و تصمیم‌های کلیدی، پنج پایان مختلف تولید می‌شود.
"""

TIERS = [
    {"min": 6, "max": 100, "code": "belonging",
     "subtitle": "بازگشت"},
    {"min": 2, "max": 5, "code": "warm_farewell",
     "subtitle": "بدرقه‌ی گرم"},
    {"min": -1, "max": 1, "code": "neutral",
     "subtitle": "بازنگری"},
    {"min": -5, "max": -2, "code": "cold_exit",
     "subtitle": "فاصله"},
    {"min": -100, "max": -6, "code": "exile",
     "subtitle": "خروج"},
]


DECISION_CALLBACKS = {
    ("MC-01", 1): {
        "li": "لی هنوز گزارش رسمی را فراموش نکرده، "
              "ولی احترامش به انصاف تو را حفظ کرده.",
    },
    ("MC-01", 2): {
        "li": "لی همیشه به یاد دارد که تو اولین کسی "
              "بودی که به او فرصت دادی.",
    },
    ("MC-01", 3): {
        "li": "لی می‌داند تو از کنار خطایش گذشتی — و "
              "این او را مدیون تو کرده.",
    },
    ("TR-01", 1): {
        "rahimi": "مهندس رحیمی هنوز از این‌که بدون "
                  "هماهنگی با او گزارش دادی دلگیر است.",
    },
    ("TR-01", 2): {
        "rahimi": "مهندس رحیمی از این‌که اول با او "
                  "مشورت کردی، احساس اعتماد می‌کند.",
    },
    ("TR-01", 3): {
        "rahimi": "مهندس رحیمی هنوز نفهمیده که تو "
                  "نقص را دیده بودی — و همین او را "
                  "آسوده نگه داشته.",
    },
    ("AC-02", 1): {
        "artemis": "دکتر آرتمیس برای صداقت تو در برابر "
                   "شورا، احترام عمیقی قائل است.",
    },
    ("AC-02", 2): {
        "artemis": "دکتر آرتمیس به یاد دارد که چطور در "
                   "برابر شورا از پذیرش مسئولیت طفره رفتی.",
    },
    ("AC-02", 3): {
        "artemis": "دکتر آرتمیس دید که چگونه مسئولیت "
                   "را به ساختار منتقل کردی — و این او "
                   "را نگران کرد.",
    },
}


BASE_MESSAGES = {
    "belonging": {
        "li": "لی نوشته: «اگه یه روزی برگشتی، من "
              "اولین کسی هستم که بهت سلام می‌کنه.»",
        "rahimi": "مهندس رحیمی نوشته: «تو متعلق به این "
                  "ایستگاهی. این‌جا همیشه جای تو خالیه.»",
        "artemis": "دکتر آرتمیس نوشته: «روش تحلیل تو رو "
                   "توی دفترچه‌ی خودم یادداشت کردم.»",
        "narrator_close": "شاتل از سکوی پرتاب جدا "
                          "می‌شود. پشت سرت، ایستگاه کاسپین "
                          "مثل یک نقطه‌ی نور گرم در سیاهی "
                          "فضا می‌تابد.",
    },
    "warm_farewell": {
        "li": "لی نوشته: «بعضی روزها دلم برات تنگ "
              "می‌شه، ولی می‌دونم که جای دیگه‌ای "
              "منتظرته.»",
        "rahimi": "مهندس رحیمی نوشته: «ایستگاه با تو یه "
                  "فصل دیگه‌ای داشت.»",
        "artemis": "دکتر آرتمیس نوشته: «وقتی برگشتی، یک "
                   "نسخه از داده‌های خام تو رو نگه داشتم.»",
        "narrator_close": "شاتل از سکوی پرتاب جدا "
                          "می‌شود. سه ماه کار در کنار سه "
                          "انسان، به یک خاطره بدل می‌شود.",
    },
    "neutral": {
        "li": "لی نوشته: «بعضی وقتا فکر می‌کنم می‌شد "
              "بهتر باشیم، ولی باز هم ممنونم.»",
        "rahimi": "مهندس رحیمی نوشته: «تجربه‌ی این چند "
                  "روز، تجربه‌ی هر دوی ماست.»",
        "artemis": "دکتر آرتمیس نوشته: «تحلیلت جای بحث "
                   "داشت، ولی هیچ‌وقت متوقف نشد.»",
        "narrator_close": "شاتل از سکوی پرتاب جدا "
                          "می‌شود. ایستگاه پشت سرت به یک "
                          "رقم در لاگ تبدیل می‌شود.",
    },
    "cold_exit": {
        "li": "لی نوشته: «کاش فرصت بیشتری داشتیم که "
              "همدیگه رو بهتر بشناسیم.»",
        "rahimi": "مهندس رحیمی پیامی کوتاه فرستاده: "
                  "«موفق باشی.»",
        "artemis": "دکتر آرتمیس پیامی نفرستاده.",
        "narrator_close": "شاتل از سکوی پرتاب جدا "
                          "می‌شود. سه ماه کار، بدون یک "
                          "خاطره‌ی گرم.",
    },
    "exile": {
        "li": "لی نوشته: «امیدوارم دفعه‌ی بعد، توی یه "
              "تیم دیگه باشیم.»",
        "rahimi": "مهندس رحیمی نوشته: «پرونده‌ات کامل "
                  "است.»",
        "artemis": "دکتر آرتمیس پیامی نفرستاده.",
        "narrator_close": "شاتل از سکوی پرتاب جدا "
                          "می‌شود. ایستگاه کاسپین دیگر "
                          "خانه‌ی تو نیست.",
    },
}


def _find_tier(total: int) -> dict:
    for tier in TIERS:
        if tier["min"] <= total <= tier["max"]:
            return tier
    return TIERS[2]


def _collect_callbacks(choice_memory: dict) -> dict:
    callbacks = {"li": [], "rahimi": [], "artemis": []}
    for (scenario_id, choice_id), addons in (
        DECISION_CALLBACKS.items()
    ):
        actual = choice_memory.get(scenario_id)
        if actual == choice_id:
            for char, text in addons.items():
                if char in callbacks:
                    callbacks[char].append(text)
    return callbacks


def compute_epilogue(
    relationships: dict, choice_memory: dict
) -> dict:
    """
    تولید محتوای میان‌پرده‌ی epilogue.

    Args:
        relationships: {"li": int, "rahimi": int, "artemis": int}
        choice_memory: {scenario_id: choice_id}

    Returns:
        dict آماده برای render_dialogue_viewer
    """
    li_r = relationships.get("li", 0)
    rahimi_r = relationships.get("rahimi", 0)
    artemis_r = relationships.get("artemis", 0)
    total = li_r + rahimi_r + artemis_r

    tier = _find_tier(total)
    code = tier["code"]
    subtitle = tier["subtitle"]
    base = BASE_MESSAGES.get(code, BASE_MESSAGES["neutral"])
    callbacks = _collect_callbacks(choice_memory)

    li_msg = base["li"]
    rahimi_msg = base["rahimi"]
    artemis_msg = base["artemis"]

    if callbacks["li"]:
        li_msg += "\n\n" + "\n".join(callbacks["li"])
    if callbacks["rahimi"]:
        rahimi_msg += "\n\n" + "\n".join(callbacks["rahimi"])
    if callbacks["artemis"]:
        artemis_msg += "\n\n" + "\n".join(callbacks["artemis"])

    dialogues = [
        {
            "speaker": "راوی",
            "text": (
                "شاتل بازگشت به مدار زمین نزدیک می‌شود. "
                "سه ماه بعد از آن چهار روز."
            ),
        },
        {"speaker": "راوی", "text": li_msg},
        {"speaker": "راوی", "text": rahimi_msg},
        {"speaker": "راوی", "text": artemis_msg},
        {"speaker": "راوی", "text": base["narrator_close"]},
    ]

    return {
        "title": "چهل و هشت ساعت بعد",
        "subtitle": subtitle,
        "body_text": "",
        "image": "/assets/videos/interlude_epilogue.png",
        "dialogues": dialogues,
    }