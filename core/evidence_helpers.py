"""
توابع کمکی برای محاسبه شواهد از فرمول‌های JSON
"""
import re
from typing import Optional


# الگوهای regex برای فرمول‌های استاندارد
_RE_TWO_COND = re.compile(
    r"^1 if choice_id == (\d+) "
    r"else \((\d+(?:\.\d+)?) if choice_id == (\d+) "
    r"else (\d+(?:\.\d+)?)\)$"
)
_RE_ONE_COND = re.compile(
    r"^1 if choice_id == (\d+) else (\d+(?:\.\d+)?)$"
)
_RE_IN_LIST = re.compile(
    r"^1 if choice_id in \((\d+),\s*(\d+)\) "
    r"else (\d+(?:\.\d+)?)$"
)


def evaluate_choice_formula(formula: str, cid: int) -> Optional[float]:
    """
    ارزیابی فرمول‌های مبتنی بر choice_id.
    
    Returns:
        مقدار محاسبه‌شده یا None اگر فرمول شناسایی نشد.
    """
    formula = formula.strip()

    # ✅ فرمول‌های deferred — پردازش در ResultsScene (نه این‌جا).
    #    این فرمول‌ها بر پایه‌ی مقایسه‌ی دو سناریو محاسبه می‌شوند
    #    و نمی‌توان مقدار ثابتی برایشان تعیین کرد.
    DEFERRED_FORMULAS = {
        "consistency_computed",
        "deferred",
        "deferred_consistency",
    }
    if formula in DEFERRED_FORMULAS:
        return None

    # 1 if choice_id == A else (B if choice_id == C else D)
    m = _RE_TWO_COND.match(formula)
    if m:
        best = int(m.group(1))
        partial_score = float(m.group(2))
        partial_id = int(m.group(3))
        default = float(m.group(4))
        if cid == best:
            return 1.0
        if cid == partial_id:
            return partial_score
        return default

    # 1 if choice_id == A else B
    m = _RE_ONE_COND.match(formula)
    if m:
        best = int(m.group(1))
        default = float(m.group(2))
        return 1.0 if cid == best else default

    # 1 if choice_id in (A, B) else C
    m = _RE_IN_LIST.match(formula)
    if m:
        a = int(m.group(1))
        b = int(m.group(2))
        default = float(m.group(3))
        return 1.0 if cid in (a, b) else default

    return None


def evaluate_time_formula(formula: str, decision_time: int) -> Optional[float]:
    """ارزیابی فرمول‌های زمان تصمیم"""
    if formula.strip() == "decision_time":
        return max(0.0, 1.0 - (decision_time / 60000.0))
    return None