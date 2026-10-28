"""
مدیریت تنظیمات مطالعه — کنترل از پنل ادمین
=============================================
- ذخیره در `web_app/data/admin_config.json`
- هر بخش/فاز/پرسشنامه قابل فعال/غیرفعال‌سازی است
"""
import os
import json


CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "data", "admin_config.json"
)

DEFAULT_CONFIG = {
    "admin_password": "truthline-2026",
    # ✅ بخش جدید: مسیریابی سفارشی
    # مثال: اگر بخواهید بعد از فاز ۱ به HEXACO بروید:
    # "routing": {"phase1": "/hexaco", "hexaco": "/phase2"}
    "routing": {}, 
    "sections": {
        "prologue": True,
        "interludes": True,
        "nights": True,
        "letter_to_self": True,
        "epilogue": True,
    },
    "phases": {
        "phase1": True,
        "phase2": True,
        "phase3": True,
        "phase4": True,
    },
    "questionnaires": {
        "hexaco": True,
        "crt": True,
        "tower_of_hanoi": True,
        "sd3": True,
        "sd": True,
        "feedback": True,
    },
}

def load_admin_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            return _deep_merge(DEFAULT_CONFIG, cfg)
        except Exception:
            return dict(DEFAULT_CONFIG)
    return dict(DEFAULT_CONFIG)


def _deep_merge(base, override):
    result = dict(base)
    for k, v in override.items():
        if (
            k in result
            and isinstance(result[k], dict)
            and isinstance(v, dict)
        ):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def save_admin_config(cfg: dict):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def is_phase_enabled(key: str) -> bool:
    return load_admin_config().get("phases", {}).get(key, True)


def is_section_enabled(key: str) -> bool:
    return load_admin_config().get("sections", {}).get(key, True)


def is_questionnaire_enabled(key: str) -> bool:
    return load_admin_config().get("questionnaires", {}).get(key, True)


def get_admin_password() -> str:
    return load_admin_config().get("admin_password", "truthline-2026")

def get_custom_routing(current_key: str) -> str | None:
    """
    بررسی می‌کند آیا مسیر سفارشی برای این مرحله تعریف شده است یا خیر.
    current_key می‌تواند نام فاز، پرسشنامه یا شب باشد (مثلا "phase1")
    """
    routing = load_admin_config().get("routing", {})
    return routing.get(current_key)
