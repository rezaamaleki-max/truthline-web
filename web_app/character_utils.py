"""
ابزارهای شخصیت — برای نمایش پرتره در وب
==========================================
- تشخیص احساس از متن (پورت‌شده از نسخه‌ی دسکتاپ)
- حل مسیر پرتره با زنجیره‌ی fallback

نسخه: 1.0.0
"""
import os

# مسیر assets
_ASSETS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "assets",
)


# ============================================================
# نگاشت نام گوینده → پوشه‌ی پرتره
# ============================================================
CHARACTER_PORTRAITS = {
    "مهندس رحیمی": "rahimi",
    "دکتر آرتمیس": "artemis",
    "لی": "lee",
    "سیستم": "os_caspian",
    "OS-CASPIAN": "os_caspian",
    "فرزین": "farzin",
    "فرزین (تکنسین فنی)": "farzin",
    "جناب آقای پرویز کیانی": "council_chair",
    "دکتر فربد مهرانی": "council_science",
    "خانم سارا آذری": "council_ethics",
}


# ============================================================
# تشخیص احساس از متن (پورت از character_registry.py دسکتاپ)
# ============================================================
EMOTION_KEYWORDS = [
    ("stress",    ["وحشت", "فاجعه", "فرار", "دستپاچه",
                   "با وحشت", "نگرانی شدید", "با استرس",
                   "رگولاتور اصلی داره می‌سوزه",
                   "صدای خش‌دار"]),
    ("anger",     ["خشم", "با لحن سرد", "با لحن تند", "عصبان",
                   "با عصبانیت", "خشمگین"]),
    ("cold",      ["با لحن خشک", "با لحن رسمی", "با لحن سرد",
                   "خشک و بی‌احساس", "با لحن محکم"]),
    ("flustered", ["رنگ می‌پراند", "دستپاچه", "گیج شد",
                   "جا خورد"]),
    ("satisfied", ["با رضایت", "با خرسندی", "رضایت‌بخش",
                   "با لبخند کم‌رنگ"]),
    ("urgent",    ["فوری", "سریع", "باید همین الان",
                   "اضطرار", "با عجله", "زود باش"]),
    ("surprised", ["متعجب", "شوکه", "غافلگیر", "با تعجب",
                   "چی؟", "باورم نمی‌شه"]),
    ("sad",       ["متأسف", "افسوس", "متأسفانه", "دلگیر",
                   "با ناراحتی"]),
    ("worried",   ["دلواپس", "خیلی نگرانم", "بیمناک"]),
    ("concern",   ["نگران", "هشدار", "خطرناک", "مشکل",
                   "با نگرانی", "احتیاط"]),
    ("thinking",  ["فکر می‌کنم", "بررسی", "تحلیل", "شاید",
                   "به نظرم", "باید ببینم"]),
    ("attentive", ["گوش می‌دم", "دقت می‌کنم", "متوجهم"]),
    ("serious",   ["جدی", "رسمی", "قاطع", "با صدای جدی",
                   "با لحن جدی"]),
    ("grateful",  ["ممنون", "سپاسگزار", "لطف کردی",
                   "قدرت رو می‌دونم"]),
    ("relief",    ["آسودگی", "خوب شد", "راحت شدم",
                   "با آسودگی", "خدا رو شکر"]),
    ("warm",      ["خوش آمد", "با لبخند", "خوشحال",
                   "با احترام", "صمیمانه"]),
]


EMOTION_FALLBACK = {
    "warm":      ["warm", "neutral"],
    "satisfied": ["satisfied", "warm", "neutral"],
    "grateful":  ["grateful", "warm", "neutral"],
    "relief":    ["relief", "warm", "neutral"],
    "concern":   ["concern", "neutral"],
    "worried":   ["worried", "concern", "neutral"],
    "sad":       ["sad", "concern", "neutral"],
    "stress":    ["stress", "concern", "neutral"],
    "anger":     ["anger", "stress", "concern", "neutral"],
    "urgent":    ["urgent", "stress", "neutral"],
    "flustered": ["flustered", "stress", "neutral"],
    "cold":      ["cold", "concern", "neutral"],
    "serious":   ["serious", "cold", "concern", "neutral"],
    "thinking":  ["thinking", "neutral"],
    "attentive": ["attentive", "neutral"],
    "surprised": ["surprised", "stress", "neutral"],
    "neutral":   ["neutral"],
}


def detect_emotion(text: str) -> str:
    """تشخیص احساس از متن دیالوگ."""
    if not text:
        return "neutral"
    for emotion, keywords in EMOTION_KEYWORDS:
        for kw in keywords:
            if kw in text:
                return emotion
    return "neutral"


# ============================================================
# حل مسیر پرتره
# ============================================================
def resolve_portrait_url(
    speaker: str, text: str = "", emotion: str | None = None
) -> str | None:
    """
    مسیر URL تصویر پرتره را برمی‌گرداند یا None.
    """
    pdir = CHARACTER_PORTRAITS.get(speaker)
    if not pdir:
        return None

    if emotion is None:
        emotion = detect_emotion(text)

    chain = EMOTION_FALLBACK.get(emotion, [emotion, "neutral"])
    seen: set = set()
    unique_chain = []
    for emo in chain:
        if emo not in seen:
            seen.add(emo)
            unique_chain.append(emo)

    base_fs = os.path.join(
        _ASSETS_DIR, "characters", pdir, "portraits"
    )
    base_url = f"/assets/characters/{pdir}/portraits"

    for emo in unique_chain:
        for ext in ("png", "jpg", "jpeg"):
            fname = f"{pdir}_{emo}_v01.{ext}"
            if os.path.exists(os.path.join(base_fs, fname)):
                return f"{base_url}/{fname}"

    # جستجوی آخرین راه
    if os.path.isdir(base_fs):
        try:
            for fname in sorted(os.listdir(base_fs)):
                lower = fname.lower()
                if lower.startswith(pdir.lower() + "_"):
                    if lower.endswith((".png", ".jpg", ".jpeg")):
                        return f"{base_url}/{fname}"
        except Exception:
            pass

    return None