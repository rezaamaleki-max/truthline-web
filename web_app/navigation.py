"""
مسیریابی هوشمند — بر اساس تنظیمات ادمین
"""
from web_app.admin_config import (
    is_phase_enabled,
    is_section_enabled,
    is_questionnaire_enabled,
    get_custom_routing,
)

PHASE_ORDER = ["phase1", "phase2", "phase3", "phase4"]


def next_after_phase(phase_key: str) -> str:
    """بعد از اتمام یک فاز، کجا برویم؟"""
    custom = get_custom_routing(phase_key)
    if custom:
        return custom

    if phase_key == "phase4":
        if is_section_enabled("letter_to_self"):
            return "/letter-to-self"
        return next_after_phases()

    if phase_key not in PHASE_ORDER:
        return next_after_phases()

    idx = PHASE_ORDER.index(phase_key)

    if is_section_enabled("nights"):
        return f"/night/{idx + 1}"

    if is_section_enabled("interludes") and idx < 3:
        return f"/interlude/day{idx + 2}"

    for later in PHASE_ORDER[idx + 1:]:
        if is_phase_enabled(later):
            return f"/{later}"

    return next_after_phases()


def next_after_phase_simple(phase_key: str) -> str:
    if phase_key not in PHASE_ORDER:
        return next_after_phases()
    idx = PHASE_ORDER.index(phase_key)
    for later in PHASE_ORDER[idx + 1:]:
        if is_phase_enabled(later):
            return f"/{later}"
    return next_after_phases()


def next_after_phases() -> str:
    custom = get_custom_routing("phases_end")
    if custom:
        return custom
    if is_questionnaire_enabled("hexaco"):
        return "/hexaco"
    return next_after_hexaco()


def next_after_hexaco() -> str:
    custom = get_custom_routing("hexaco")
    if custom:
        return custom
    if is_questionnaire_enabled("crt"):
        return "/crt"
    return next_after_crt()


def next_after_crt() -> str:
    custom = get_custom_routing("crt") # ✅ اصلاح شد
    if custom:
        return custom
    if is_questionnaire_enabled("tower_of_hanoi"):
        return "/tower-of-hanoi"
    return next_after_toh()


def next_after_toh() -> str:
    custom = get_custom_routing("tower_of_hanoi") # ✅ اصلاح شد
    if custom:
        return custom
    if is_questionnaire_enabled("sd3"):
        return "/sd3"
    return next_after_sd3()


def next_after_sd3() -> str:
    custom = get_custom_routing("sd3") # ✅ اصلاح شد
    if custom:
        return custom
    if is_questionnaire_enabled("sd"):
        return "/sd"
    return next_after_sd()


def next_after_sd() -> str:
    custom = get_custom_routing("sd") # ✅ اصلاح شد
    if custom:
        return custom
    if is_questionnaire_enabled("feedback"):
        return "/feedback"
    return next_after_feedback()


def next_after_feedback() -> str:
    custom = get_custom_routing("feedback") # ✅ اصلاح شد
    if custom:
        return custom
    if is_section_enabled("epilogue"):
        return "/interlude/epilogue"
    return "/results"


def next_after_night(night_num: int) -> str:
    custom = get_custom_routing(f"night{night_num}") # ✅ اصلاح شد
    if custom:
        return custom

    if is_section_enabled("interludes") and night_num <= 3:
        return f"/interlude/day{night_num + 1}"
    next_phase = f"phase{night_num + 1}"
    if is_phase_enabled(next_phase):
        return f"/{next_phase}"
    return next_after_phase_simple(f"phase{night_num}")


def next_after_interlude(day_key: str) -> str:
    custom = get_custom_routing(day_key) # ✅ اصلاح شد
    if custom:
        return custom

    mapping = {
        "day2": "phase2",
        "day3": "phase3",
        "day4": "phase4",
        "epilogue": "/results",
    }
    target = mapping.get(day_key)
    if not target:
        return "/results"
    if target.startswith("/"):
        return target
    if is_phase_enabled(target):
        return f"/{target}"
    return next_after_phase_simple(target)