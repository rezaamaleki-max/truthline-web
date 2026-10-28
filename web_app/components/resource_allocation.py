"""
مکانیک تخصیص منابع (SPA-02) — نسخه‌ی اصلاح‌شده
================================================
- ۳ منبع یکتا (باتری، اکسیژن، نرم‌افزار)
- ۶ بخش، اما فقط ۳ بخش می‌توانند منبع بگیرند
- بازیکن باید انتخاب کند کدام ۳ بخش را کمک کند
- بدون نمایش «اولویت» (باید از متن info استنتاج شود)
- تایمر معکوس ۹۰ ثانیه با ui.timer
- محاسبه‌ی شواهد SPA1, SPA2, SPA3, F1 (مطابق دسکتاپ)
"""
import re
import time
from typing import Any
from nicegui import ui, app

from web_app.config import TEST_MODE


ALLOCATION_CSS_HTML = """
<style>
.alloc-section {
    transition: all 0.2s ease;
}
.alloc-section.assigned {
    border-color: #4FC3F7 !important;
    background-color: rgba(79, 195, 247, 0.05) !important;
}
.alloc-timer {
    font-family: Consolas, monospace;
    font-weight: bold;
    transition: color 0.3s;
}
.alloc-timer.danger {
    color: #D32F2F !important;
    animation: alloc-pulse 0.8s ease-in-out infinite;
}
@keyframes alloc-pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}
.res-btn {
    font-size: 11px;
    padding: 4px 8px;
    border-radius: 6px;
    border: 2px solid;
    cursor: pointer;
    transition: all 0.15s;
}
.res-btn-normal {
    background: #1A2A4A;
    border-color: #4FC3F7;
    color: #4FC3F7;
}
.res-btn-selected {
    background: #4FC3F7;
    border-color: #FFFFFF;
    color: #0B1D3A;
    font-weight: bold;
}
.res-btn-disabled {
    background: #1A1A1A;
    border-color: #444;
    color: #666;
    cursor: not-allowed;
    opacity: 0.5;
}
</style>
"""


SECTION_ICONS = {
    "medical": "🏥",
    "engineering": "🔧",
    "air_recycling": "💨",
    "navigation": "🧭",
    "command_center": "📡",
    "science_lab": "🔬",
}


def _strip_priority(text: str) -> str:
    """حذف بخش «اولویت: ...» از انتهای متن"""
    if not text:
        return text
    # حذف «. اولویت: XXX.» یا «اولویت: XXX»
    cleaned = re.sub(
        r'\.?\s*اولویت\s*:[^.]*\.?\s*$', '', text.strip()
    )
    return cleaned.strip()


# ============================================================
# محاسبه‌ی شواهد (منطق دسکتاپ)
# ============================================================
def _calc_evidence(sections, optimal, allocations, info_checked, decision_time_ms):
    # E_SPA1: تخصیص بهینه
    if not optimal:
        alloc_score = 0.0
    else:
        correct = sum(
            1 for sec, res in optimal.items()
            if allocations.get(sec) == res
        )
        penalty = 0
        for sec in allocations.keys():
            if sec not in optimal:
                if sec == "engineering":
                    penalty += 0.5
                elif sec == "command_center":
                    penalty += 0.4
                elif sec == "science_lab":
                    penalty += 0.4
                else:
                    penalty += 0.5
        alloc_score = max(
            0.0, min(1.0, (correct - penalty) / len(optimal))
        )

    # E_SPA2: بررسی اطلاعات
    total_sections = len(sections)
    if total_sections == 0:
        info_score = 0.0
    else:
        ratio = len(info_checked) / total_sections
        info_score = 1.0 if ratio >= 0.83 else min(1.0, ratio * 1.2)

    # E_SPA3: زمان تصمیم
    time_score = max(0.0, 1.0 - (decision_time_ms / 60000.0))

    # E_F1: انصاف تحت فشار
    if allocations.get("air_recycling") == "battery":
        decision_s = 1.00
    elif allocations.get("engineering") == "battery":
        decision_s = 0.20
    elif allocations.get("command_center") == "battery":
        decision_s = 0.40
    else:
        decision_s = 0.10

    if total_sections == 0:
        process_s = 0.0
    else:
        ratio = min(1.0, len(info_checked) / total_sections)
        if ratio >= 0.83:
            process_s = 1.00
        elif ratio >= 0.66:
            process_s = 0.70
        elif ratio >= 0.50:
            process_s = 0.40
        else:
            process_s = 0.10

    medical_ok = allocations.get("medical") == "oxygen"
    medical_s = 1.0 if medical_ok else 0.0

    fairness = decision_s * 0.50 + process_s * 0.30 + medical_s * 0.20
    print(
        f"   [FAIRNESS] decision={decision_s:.2f} "
        f"process={process_s:.2f} medical={medical_s:.2f} "
        f"→ total={fairness:.3f}"
    )

    return [
        {"key": "E_SPA1_allocation_pattern",
         "value": round(alloc_score, 3), "weight": 0.30,
         "description": "الگوی تخصیص بهینه"},
        {"key": "E_SPA2_data_check",
         "value": round(info_score, 3), "weight": 0.25,
         "description": "بررسی اطلاعات پیش از تصمیم"},
        {"key": "E_SPA3_decision_time",
         "value": round(time_score, 3), "weight": 0.15,
         "description": "زمان تصمیم"},
        {"key": "E_F1_fairness_under_pressure",
         "value": round(max(0.0, min(1.0, fairness)), 3), "weight": 0.30,
         "description": "انصاف تحت فشار"},
    ]


# ============================================================
# تابع اصلی
# ============================================================
async def render_resource_allocation(scenario: dict, on_complete):
    cfg = scenario.get("allocation_config", {})
    sections = cfg.get("sections", [])
    resources = cfg.get("resources", [])
    # ✅ کاهش به ۶۰ ثانیه (طبق بازخورد: ۹۰ ثانیه فشار کافی ایجاد نمی‌کرد)
    # اگر JSON مقدار متفاوتی داشت، اولویت به JSON است
    time_limit_sec = cfg.get("time_limit_sec", 60)
    # ✅ اجبار به حداکثر ۶۰ ثانیه — حتی اگر JSON مقدار بالاتری داشته باشد
    time_limit_sec = min(60, int(time_limit_sec))
    optimal = cfg.get("optimal_allocation", {})
    num_resources = len(resources)

    state = {
        "allocations": {},
        "info_checked": [],
        "info_check_times_ms": {},
        "allocation_order": [],
        "first_allocation_time": None,
        "start_time": time.time(),
        "submitted": False,
        "time_remaining": time_limit_sec,
        "investigating": set(),
    }

    section_cards = {}
    info_labels = {}
    checked_badges = {}
    section_buttons = {}   # {sec_id: {res_id: btn, "none": btn}}

    # ---- عنوان ----
    ui.label("🎯 تخصیص منابع").classes(
        'text-xl font-bold text-cyan-400 w-full text-right'
    )

    # ---- راهنما ----
    with ui.element('div').classes(
        'w-full p-3 rounded border-2 border-orange-500 '
        'bg-orange-900/20 my-2'
    ):
        ui.label("💡 راهنما").classes(
            'text-sm font-bold text-orange-400 mb-1 w-full text-right'
        )
        ui.label(
            f"• {len(sections)} بخش نیازمند کمک دارید، اما فقط "
            f"{num_resources} منبع در دسترس است."
        ).classes('text-xs text-gray-300 w-full text-right')
        ui.label(
            "• با کلیک روی «بررسی اطلاعات» متن هر بخش را بخوانید "
            "و تصمیم بگیرید کدام بخش‌ها را نجات دهید."
        ).classes('text-xs text-gray-300 w-full text-right')
        ui.label(
            f"• زمان محدود است: {time_limit_sec} ثانیه."
        ).classes('text-xs text-gray-300 w-full text-right')

    # ---- تایمر بزرگ و برجسته (چسبان در بالای صفحه) ----
    with ui.card().classes(
        'w-full bg-slate-900 border-2 border-orange-500 p-4 mb-2'
    ).style(
        'position: sticky; '
        'top: 8px; '
        'z-index: 50; '
        'box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);'
    ):
        with ui.row().classes(
            'items-center justify-between w-full no-wrap'
        ):
            with ui.row().classes('items-center gap-3 no-wrap'):
                ui.label('⏱').classes('text-3xl')
                timer_label = ui.label(
                    str(time_limit_sec)
                ).classes(
                    'alloc-timer text-4xl font-bold text-orange-400'
                )
                ui.label('ثانیه').classes(
                    'text-sm text-gray-400 self-end mb-2'
                )
            with ui.column().classes('items-end gap-0'):
                progress_info = ui.label(
                    f"0 از {num_resources} منبع تخصیص یافته"
                ).classes('text-sm text-white font-bold')
                ui.label(
                    f"{len(sections)} بخش"
                ).classes('text-xs text-gray-400')

    # ---- نوار پیشرفت ----
    progress_bar = ui.linear_progress(
        value=0.0, show_value=False
    ).classes('w-full mb-3')

    # ============================================================
    # Refs — برای دکمه‌ی Submit که بعد از بخش‌ها ساخته می‌شود
    # ============================================================
    refs: dict = {}


    def _update_progress():
        n = len(state["allocations"])
        progress_info.set_text(
            f"{n} از {num_resources} منبع تخصیص یافته"
        )
        if num_resources > 0:
            progress_bar.set_value(n / num_resources)

    # ---- پاک کردن و تخصیص ----
    def _assign_resource(section_id, resource_id):
        """تخصیص یا حذف تخصیص یک منبع به یک بخش"""
        if state["submitted"]:
            return

        if resource_id is None:
            state["allocations"].pop(section_id, None)
        else:
            # اگر منبع به بخش دیگری داده شده، از آنجا بردار
            for other_sid, other_rid in list(
                state["allocations"].items()
            ):
                if other_rid == resource_id and other_sid != section_id:
                    del state["allocations"][other_sid]
            state["allocations"][section_id] = resource_id
            if state["first_allocation_time"] is None:
                state["first_allocation_time"] = time.time()
            state["allocation_order"].append(
                (section_id, resource_id)
            )

        _refresh_buttons()
        _update_progress()

    def _refresh_buttons():
        used = set(state["allocations"].values())
        for sid, btns in section_buttons.items():
            assigned_here = state["allocations"].get(sid)
            for rid, btn in btns.items():
                if rid == "none":
                    if assigned_here is None:
                        btn.classes(replace="res-btn res-btn-selected")
                    else:
                        btn.classes(replace="res-btn res-btn-normal")
                    continue

                is_used_here = assigned_here == rid
                is_used_elsewhere = (rid in used
                                     and not is_used_here)

                if is_used_elsewhere:
                    btn.classes(replace="res-btn res-btn-disabled")
                    btn.disable()
                elif is_used_here:
                    btn.classes(replace="res-btn res-btn-selected")
                    btn.enable()
                else:
                    btn.classes(replace="res-btn res-btn-normal")
                    btn.enable()

        # فعال/غیرفعال کردن دکمه‌ی ثبت (از refs)
        btn = refs.get("submit_btn")
        if btn is not None:
            if len(state["allocations"]) == num_resources:
                btn.enable()
            else:
                btn.disable()

    # ---- بررسی اطلاعات ----
    async def _check_info(section_id):
        if section_id in state["info_checked"]:
            return
        if section_id in state["investigating"]:
            return
        if state["submitted"]:
            return

        state["investigating"].add(section_id)
        badge = checked_badges.get(section_id)
        if badge:
            badge.set_text("⏳ در حال بررسی...")
            badge.set_visibility(True)

        import asyncio
        await asyncio.sleep(1.0)

        state["info_checked"].append(section_id)
        state["info_check_times_ms"][section_id] = 1000
        state["investigating"].discard(section_id)

        if badge:
            badge.set_text("📄 خوانده شد")

        lbl = info_labels.get(section_id)
        if lbl:
            lbl.set_visibility(True)

    # ---- نهایی‌سازی ----
    timer_holder: dict[str, Any] = {"obj": None}

    async def _submit():
        if state["submitted"]:
            return
        state["submitted"] = True
        _btn = refs.get("submit_btn")
        if _btn is not None:
            _btn.disable()

        if timer_holder["obj"] is not None:
            try:
                timer_holder["obj"].active = False
            except Exception:
                pass

        total_time_ms = int(
            (time.time() - state["start_time"]) * 1000
        )
        if state["first_allocation_time"] is not None:
            tfa = int(
                (state["first_allocation_time"] - state["start_time"])
                * 1000
            )
        else:
            tfa = 0

        result = {
            "allocations": state["allocations"],
            "info_checked": state["info_checked"],
            "info_check_times_ms": state["info_check_times_ms"],
            "allocation_order": state["allocation_order"],
            "time_to_first_allocation_ms": tfa,
            "total_time_ms": total_time_ms,
            "timed_out": state["time_remaining"] <= 0,
            "submitted": True,
        }
        result["evidence_items"] = _calc_evidence(
            sections, optimal,
            state["allocations"], state["info_checked"],
            total_time_ms,
        )

        if on_complete:
            await on_complete(result)

    # ✅ on_click بعد از ساخت دکمه (پایین‌تر) — اینجا فقط تعریف می‌کنیم
    # (جایگزین on_click بعد از ساخت دکمه می‌شود)

    # ---- تایمر با ui.timer ----
    async def _on_tick():
        if state["submitted"]:
            return
        state["time_remaining"] -= 1
        timer_label.set_text(str(state["time_remaining"]))
        if state["time_remaining"] <= 10:
            timer_label.classes(add="danger")
        if state["time_remaining"] <= 0:
            await _submit()

    timer = ui.timer(1.0, _on_tick)
    timer_holder["obj"] = timer

    # ---- گرید بخش‌ها ----
    # ✅ shuffle پایدار
    import random as _random
    _saved_sec = app.storage.user.get("_alloc_order")
    if (
        not _saved_sec
        or not isinstance(_saved_sec, list)
        or len(_saved_sec) != len(sections)
    ):
        _order_ids = [s["id"] for s in sections]
        _random.shuffle(_order_ids)
        app.storage.user["_alloc_order"] = _order_ids
        _saved_sec = _order_ids

    _sec_map = {s["id"]: s for s in sections}
    _ordered_sections = [
        _sec_map[sid] for sid in _saved_sec
        if sid in _sec_map
    ]

    _saved_res = app.storage.user.get("_alloc_res_order")
    if (
        not _saved_res
        or not isinstance(_saved_res, list)
        or len(_saved_res) != len(resources)
    ):
        _res_ids = [r["id"] for r in resources]
        _random.shuffle(_res_ids)
        app.storage.user["_alloc_res_order"] = _res_ids
        _saved_res = _res_ids

    _res_map = {r["id"]: r for r in resources}
    _ordered_resources = [
        _res_map[rid] for rid in _saved_res
        if rid in _res_map
    ]
    with ui.grid(columns=2).classes('w-full gap-3'):
        for section in _ordered_sections:
            sec_id = section["id"]
            icon = SECTION_ICONS.get(sec_id, "📦")

            card = ui.card().classes(
                "alloc-section bg-slate-800 border-2 "
                "border-slate-600 p-3"
            )
            section_cards[sec_id] = card

            with card:
                # هدر
                with ui.row().classes(
                    'items-center gap-2 w-full no-wrap mb-1'
                ):
                    ui.label(icon).classes(
                        'text-xl flex-shrink-0'
                    )
                    ui.label(section["name"]).classes(
                        'text-sm text-white font-bold flex-1 text-right'
                    )
                    badge = ui.label("").classes(
                        'text-xs text-cyan-300 font-bold whitespace-nowrap'
                    )
                    badge.set_visibility(False)
                    checked_badges[sec_id] = badge

                # دکمه‌ی بررسی اطلاعات
                async def _do_check(sid=sec_id):
                    await _check_info(sid)

                ui.button("🔍 بررسی اطلاعات").classes(
                    'w-full bg-slate-600 hover:bg-slate-500 '
                    'text-xs py-1 mt-1'
                ).on_click(_do_check)

                # متن اطلاعات (پنهان تا بررسی)
                info_text = _strip_priority(
                    section.get("info", "")
                )
                detail_lbl = ui.label(info_text).classes(
                    'text-xs text-gray-300 leading-relaxed '
                    'w-full text-right mt-2 p-2 bg-slate-900 '
                    'rounded border-r-2 border-cyan-500'
                )
                detail_lbl.set_visibility(False)
                info_labels[sec_id] = detail_lbl

                # دکمه‌های تخصیص منبع
                ui.label("اختصاص منبع:").classes(
                    'text-xs text-gray-400 w-full text-right mt-2 mb-1'
                )
                btns = {}
                with ui.row().classes('gap-1 flex-wrap w-full'):
                    # دکمه‌ی «بدون منبع»
                    none_btn = ui.button("بدون منبع")
                    none_btn.classes("res-btn res-btn-selected")
                    none_btn.on_click(
                        lambda e=None, sid=sec_id: _assign_resource(
                            sid, None
                        )
                    )
                    btns["none"] = none_btn

                    for r in _ordered_resources:
                        rid = r["id"]
                        rbtn = ui.button(r["name"])
                        rbtn.classes("res-btn res-btn-normal")

                        def _make_click(sid=sec_id, rid=rid):
                            def _handler(e=None):
                                _assign_resource(sid, rid)
                            return _handler

                        rbtn.on_click(_make_click())
                        btns[rid] = rbtn

                section_buttons[sec_id] = btns

    _update_progress()
    _refresh_buttons()

    # ============================================================
    # دکمه‌ی ثبت تخصیص — حالا زیر بخش‌ها (طبق بازخورد)
    # ============================================================
    with ui.row().classes('w-full mt-4 mb-3'):
        refs["submit_btn"] = ui.button("✓ ثبت تخصیص").classes(
            'w-full py-3 text-lg font-bold '
            'bg-green-600 hover:bg-green-500'
        )
        refs["submit_btn"].disable()
        refs["submit_btn"].on_click(_submit)

    _update_progress()
    _refresh_buttons()


