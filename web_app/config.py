"""
تنظیمات و توابع کمکی مشترک بین صفحات وب
"""
import os
import json
import re

# استایل سراسری
PAGE_CSS = (
    "background-color: #0B1D3A; "
    "color: white; "
    "direction: rtl; "
    "font-family: Vazirmatn, Tahoma; "
)

# مسیر پوشه‌ی web_app
WEB_APP_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# حالت تست — در محیط واقعی False کنید
# ============================================================
TEST_MODE = True

# نمایش toast بازخورد فوری هنگام انتخاب گزینه.
# ⚠️ در مطالعه‌ی نهایی (که نباید بازخورد فوری داده شود)
#    مقدار را روی False بگذارید.
SHOW_CHOICE_TOAST = True

# پیشوند شناسه‌ی شرکت‌کننده در حالت تست
TEST_PARTICIPANT_PREFIX = "TEST_"


def load_scenario(scenario_id: str, phase: str = "phase1") -> dict:
    """بارگذاری JSON سناریو. اول _inner، سپس ساده."""
    inner = os.path.join(
        WEB_APP_DIR, "data", "scenarios", phase,
        f"{scenario_id}_inner.json"
    )
    simple = inner.replace("_inner.json", ".json")
    path = inner if os.path.exists(inner) else simple
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_inner_thoughts(scenario: dict) -> None:
    """استخراج توجیه منطقی از متن گزینه‌ها"""
    pattern = re.compile(
        r"\n\n\(توجیه منطقی:\s*(.+?)\)\s*$", re.DOTALL
    )
    for choice in scenario.get("choices", []):
        text = choice.get("text_fa", "")
        if not text:
            continue
        m = pattern.search(text)
        if m:
            choice["thought"] = m.group(1).strip()
            choice["text_fa"] = pattern.sub("", text).strip()
        else:
            choice.setdefault("thought", "")


def calculate_evidence_value(
    formula: str, choice: dict, decision_time: int
) -> float:
    """ارزیابی فرمول‌های شاهد"""
    from core.evidence_helpers import (
        evaluate_choice_formula, evaluate_time_formula,
    )
    cid = choice.get("id", 0)
    v = evaluate_choice_formula(formula, cid)
    if v is not None:
        return v
    v = evaluate_time_formula(formula, decision_time)
    if v is not None:
        return v
    return 1.0 if cid == 1 else (0.5 if cid == 2 else 0.0)

# ============================================================
# تعریف فازها
# ============================================================
PHASE_SCENARIOS = {
    "phase1": ["VH-01", "DA-01", "DA-02", "MC-01", "VH-02", "F-02"],
    "phase2": ["CF-01", "TR-01", "TR-02", "BC-01", "BC-02", "CF-02"],
    "phase3": ["PID-01", "MC-02", "PID-02", "SPA-01",
               "CFI-01", "MR-01", "SPA-02", "MR-02"],
    "phase4": ["PI-01", "TC-01", "TC-02", "PI-02",
               "RG-01", "RG-02", "AC-02", "AC-01"],
}

PHASE_TITLES = {
    "phase1": "فاز ۱ — روز اول",
    "phase2": "فاز ۲ — روز دوم",
    "phase3": "فاز ۳ — روز سوم",
    "phase4": "فاز ۴ — روز چهارم",
}

# مکانیک‌هایی که در وب پیاده‌سازی شده‌اند
SUPPORTED_MECHANICS = {
    "quantum_analyzer",
    "calibration_sliders",
    "diagnostic_map",
    "resource_allocation",
    "dependency_board",
    "innovation_puzzle",
    "repetitive_task",           # ✅ جدید
    "accountability_dialog",     # ✅ جدید
}
PENDING_MECHANICS = set()  # ✅ همه پیاده شدند


def get_phase_config(phase_key: str) -> dict:
    """پیکربندی یک فاز"""
    return {
        "scenarios": PHASE_SCENARIOS.get(phase_key, []),
        "title": PHASE_TITLES.get(phase_key, phase_key),
    }

# ============================================================
# پیکربندی جریان داستان
# ============================================================
# ✅ فازهایی که در وب پیاده‌سازی شده‌اند
#    وقتی فاز ۳ را ساختید، "phase3" را اضافه کنید
#    وقتی فاز ۴ را ساختید، "phase4" را اضافه کنید
AVAILABLE_PHASES = {"phase1", "phase2", "phase3", "phase4"} 

# بعد از هر شب چه صفحه‌ای؟
NIGHT_NEXT = {
    "1": "interlude/day2",
    "2": "interlude/day3",
    "3": "interlude/day4",
}

# نگاشت میان‌پرده به فاز بعدی
_INTERLUDE_TO_PHASE = {
    "day2": "phase2",
    "day3": "phase3",
    "day4": "phase4",
    "epilogue": "results",
}


def get_interlude_next(day_key: str) -> str:
    """
    تعیین صفحه‌ی بعدی بعد از میان‌پرده.
    اگر فاز مربوطه پیاده‌سازی نشده باشد، به پرسشنامه می‌رود.
    """
    next_phase = _INTERLUDE_TO_PHASE.get(day_key, "hexaco")
    if next_phase in ("phase2", "phase3", "phase4"):
        if next_phase not in AVAILABLE_PHASES:
            return "hexaco"
    return next_phase


def load_night_data(night_num: str) -> dict:
    """بارگذاری داده‌های یک شب از night_dialogues.json"""
    path = os.path.join(
        WEB_APP_DIR, "data", "night_dialogues.json"
    )
    if not os.path.exists(path):
        print(f"⚠️ فایل شب‌ها یافت نشد: {path}")
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            all_nights = json.load(f)
        return all_nights.get(f"night_{night_num}", {})
    except Exception as e:
        print(f"⚠️ خطا در بارگذاری شب {night_num}: {e}")
        return {}


# ============================================================
# فرمول‌های deferred (در ResultsScene محاسبه می‌شوند)
# ============================================================
DEFERRED_FORMULAS = {
    "consistency_computed",
    "deferred",
    "deferred_consistency",
}


def should_skip_evidence(formula: str) -> bool:
    """آیا این شاهد باید در فاز بعد محاسبه شود؟"""
    return formula.strip() in DEFERRED_FORMULAS

