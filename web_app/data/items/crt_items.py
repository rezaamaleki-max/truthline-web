"""
آزمون تأمل شناختی (CRT7)
Toplak, West & Stanovich (2014), Journal of Applied Research
in Memory and Cognition, 3, 147-168.

نسخه‌ی هفت‌سؤالی: 3 سؤال اصلی Frederick (2005) + 4 سؤال جدید
نمره‌گذاری: هر پاسخ درست = 1، دامنه‌ی نمره 0 تا 7
پاسخ شهودی (غلط جذاب) = 0 نمره، ولی به‌عنوان شاخص
«تفکر بخیلانه» ثبت می‌شود.

نسخه: 2.0.0 — اصلاح‌شده بر اساس مقاله‌ی اصلی
"""
import re

# ============================================================
# گویه‌ها
# ============================================================
CRT_ITEMS = [
    {
        "id": 1,
        "type": "numeric",
        "text": (
            "یک چوب بیسبال و یک توپ در مجموع ۱۱۰۰ تومان "
            "قیمت دارند. چوب بیسبال ۱۰۰۰ تومان از توپ "
            "گران‌تر است. قیمت توپ چند تومان است؟"
        ),
        "hint": "پاسخ را به تومان بنویسید",
        "correct": 50,
        "intuitive": 100,
    },
    {
        "id": 2,
        "type": "numeric",
        "text": (
            "اگر ۵ دستگاه، ۵ دقیقه وقت بگیرند تا ۵ قطعه "
            "بسازند، ۱۰۰ دستگاه چقدر وقت می‌گیرند تا ۱۰۰ "
            "قطعه بسازند؟"
        ),
        "hint": "پاسخ را به دقیقه بنویسید",
        "correct": 5,
        "intuitive": 100,
    },
    {
        "id": 3,
        "type": "numeric",
        "text": (
            "در دریاچه‌ای، لکه‌ای از برگ نیلوفر آبی وجود "
            "دارد. هر روز اندازه‌ی لکه دو برابر می‌شود. "
            "اگر ۴۸ روز طول بکشد تا لکه کل دریاچه را "
            "بپوشاند، چند روز طول می‌کشد تا نصف دریاچه "
            "را بپوشاند؟"
        ),
        "hint": "پاسخ را به روز بنویسید",
        "correct": 47,
        "intuitive": 24,
    },
    {
        "id": 4,
        "type": "numeric",
        "text": (
            "اگر کاوه یک بشکه آب را در ۶ روز بنوشد و "
            "شیرین همان بشکه را در ۱۲ روز، اگر با هم "
            "بنوشند چند روز طول می‌کشد؟"
        ),
        "hint": "پاسخ را به روز بنویسید",
        "correct": 4,
        "intuitive": 9,
    },
    {
        "id": 5,
        "type": "numeric",
        "text": (
            "رضا هم پانزدهمین نمره‌ی بالاترین و هم "
            "پانزدهمین نمره‌ی پایین‌ترین کلاس را گرفت. "
            "چند دانش‌آموز در کلاس هستند؟"
        ),
        "hint": "پاسخ را به تعداد دانش‌آموز بنویسید",
        "correct": 29,
        "intuitive": 30,
    },
    {
        "id": 6,
        "type": "numeric",
        "text": (
            "کشاورزی گوسفندی را ۶۰ هزار تومان می‌خرد، "
            "۷۰ هزار تومان می‌فروشد، ۸۰ هزار تومان "
            "می‌خرد و در نهایت ۹۰ هزار تومان می‌فروشد. "
            "چقدر سود کرده؟"
        ),
        "hint": "پاسخ را به هزار تومان بنویسید",
        "correct": 20,
        "intuitive": 10,
    },
    {
        "id": 7,
        "type": "choice",
        "text": (
            "سیاوش ۸ هزار تومان در بورس سرمایه‌گذاری کرد. "
            "شش ماه بعد، ارزش سهامش ۵۰٪ کاهش یافت. از آن "
            "زمان تا سه ماه بعد، ۷۵٪ افزایش یافت. در این "
            "لحظه، سیاوش:"
        ),
        "hint": "",
        "options": [
            ("a", "سربه‌سر شده"),
            ("b", "سود کرده"),
            ("c", "ضرر کرده"),
        ],
        "correct": "c",       # پاسخ درست: 8000 → 4000 → 7000
        "intuitive": "b",     # پاسخ شهودی
    },
]


# ============================================================
# نمره‌گذاری
# ============================================================
def _extract_number(value) -> int | None:
    """
    استخراج عدد از متن آزاد.
    مثال: '50 تومان' → 50، '۵۰' → 50، '۵۰.۰' → 50
    """
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    # ✅ تبدیل ارقام فارسی/عربی به انگلیسی
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    translate_map = {}
    for i, ch in enumerate(persian_digits):
        translate_map[ord(ch)] = str(i)
    for i, ch in enumerate(arabic_digits):
        translate_map[ord(ch)] = str(i)
    text = text.translate(translate_map)

    # ✅ استخراج اولین عدد صحیح
    match = re.search(r"-?\d+", text)
    if match:
        try:
            return int(match.group())
        except ValueError:
            return None
    return None


def score_crt(answers: dict) -> dict:
    """
    محاسبه‌ی نمره‌ی CRT7.

    Args:
        answers: {item_id: value}
            - for numeric: int یا str (شامل '۵۰' یا '50 تومان')
            - for choice: 'a' / 'b' / 'c'

    Returns:
        {
            "score": 0..7,                # تعداد پاسخ‌های درست
            "max_score": 7,
            "intuitive_count": 0..7,       # تعداد پاسخ‌های شهودی
            "other_count": int,             # سایر پاسخ‌ها
            "per_item": {item_id: 1/0},
            "intuitive_per_item": {item_id: 1/0},
        }
    """
    score = 0
    intuitive_count = 0
    other_count = 0
    per_item = {}
    intuitive_per_item = {}

    for item in CRT_ITEMS:
        iid = item["id"]
        val = answers.get(iid)
        correct = item["correct"]
        intuitive = item.get("intuitive")

        if val is None or val == "":
            per_item[iid] = 0
            intuitive_per_item[iid] = 0
            continue

        if item["type"] == "numeric":
            num = _extract_number(val)
            if num is not None and num == correct:
                per_item[iid] = 1
                intuitive_per_item[iid] = 0
                score += 1
            elif num is not None and num == intuitive:
                per_item[iid] = 0
                intuitive_per_item[iid] = 1
                intuitive_count += 1
            else:
                per_item[iid] = 0
                intuitive_per_item[iid] = 0
                other_count += 1
        else:  # choice
            choice_str = str(val).strip().lower()
            if choice_str == correct:
                per_item[iid] = 1
                intuitive_per_item[iid] = 0
                score += 1
            elif choice_str == intuitive:
                per_item[iid] = 0
                intuitive_per_item[iid] = 1
                intuitive_count += 1
            else:
                per_item[iid] = 0
                intuitive_per_item[iid] = 0
                other_count += 1

    return {
        "score": score,
        "max_score": 7,
        "intuitive_count": intuitive_count,
        "other_count": other_count,
        "per_item": per_item,
        "intuitive_per_item": intuitive_per_item,
    }