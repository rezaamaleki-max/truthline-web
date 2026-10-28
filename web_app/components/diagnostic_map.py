"""
مکانیک نقشه تشخیصی (PID-01) — نسخه‌ی ۲
==========================================
بهبود بر اساس بازخورد: راهنمای گام‌به‌گام مکانیک، نشانگرهای
بصری واضح، بازخورد پیشرفت هدایت‌کننده، و راهنمای وضعیت سیستم‌ها.

- نمایش ۶ سیستم با کارت
- راهنمای ۳ مرحله‌ای در بالا
- نشانگر وضعیت رنگی (warning/failure/ok)
- کلیک روی هر سیستم → ۱.۵ ثانیه بررسی → نمایش جزئیات
- پیشرفت هدایت‌کننده (پیام‌های تشویقی)
- شمارش perseveration (کلیک تکراری)
- تشخیص نهایی: انتخاب علت اصلی

نسخه: 2.0.0
"""
import asyncio
import time
from nicegui import ui, app

from web_app.config import TEST_MODE
from web_app.audio import play_scan_sfx

DIAGNOSTIC_CSS_HTML = """
<style>
.diag-card {
    transition: all 0.2s ease;
    cursor: pointer;
}
.diag-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(79, 195, 247, 0.3);
}
.diag-card.investigating {
    border-color: #FF8F00 !important;
    background-color: rgba(255, 143, 0, 0.1) !important;
}
.diag-card.investigated {
    border-color: #4CAF50 !important;
    background-color: rgba(76, 175, 80, 0.08) !important;
}
.diag-spinner {
    display: inline-block;
    width: 16px;
    height: 16px;
    border: 2px solid rgba(255, 143, 0, 0.3);
    border-top-color: #FF8F00;
    border-radius: 50%;
    animation: diag-spin 0.8s linear infinite;
}
@keyframes diag-spin {
    to { transform: rotate(360deg); }
}
.diag-step {
    transition: all 0.3s;
}
</style>
"""


# ============================================================
# نشانگر وضعیت سیستم
# ============================================================
STATUS_META = {
    "ok": {
        "label": "عادی",
        "color": "#4CAF50",
        "bg": "rgba(76, 175, 80, 0.15)",
        "icon": "✓",
    },
    "warning": {
        "label": "هشدار",
        "color": "#FF8F00",
        "bg": "rgba(255, 143, 0, 0.15)",
        "icon": "⚠",
    },
    "failure": {
        "label": "نقص",
        "color": "#D32F2F",
        "bg": "rgba(211, 47, 47, 0.15)",
        "icon": "✗",
    },
}


def _calc_evidence(result: dict) -> list:
    """محاسبه شواهد بر اساس نتیجه‌ی تشخیص"""
    total_inv = result["total_investigated"]
    total = result["total_systems"]
    pers = result["perseveration_count"]
    tfa = result["time_to_first_action_ms"]
    root = result["chosen_root_cause"]

    # عمق بررسی
    depth = min(1.0, total_inv / max(1, total - 1))

    # تعداد سیستم‌ها
    if total_inv >= 5: count_s = 1.0
    elif total_inv >= 3: count_s = 0.7
    elif total_inv >= 2: count_s = 0.4
    elif total_inv >= 1: count_s = 0.2
    else: count_s = 0.0

    # زمان تا اولین اقدام
    if tfa == 0: time_s = 0.0
    elif tfa < 1000: time_s = 0.3
    elif tfa <= 8000: time_s = 1.0
    elif tfa <= 15000: time_s = 0.7
    else: time_s = 0.4

    # تشخیص درست
    if root == "power_grid": root_s = 1.0
    elif root == "cooling": root_s = 0.1
    elif root == "communications": root_s = 0.3
    else: root_s = 0.2

    # perseveration
    if total_inv == 0: pers_s = 0.0
    else:
        ratio = pers / max(1, total_inv)
        if ratio == 0: pers_s = 1.0
        elif ratio <= 0.5: pers_s = 0.8
        elif ratio <= 1.0: pers_s = 0.5
        else: pers_s = 0.2

    # اکتشاف
    expl_s = min(1.0, total_inv / max(1, total))

    return [
        {"key": "E_PID1_systems_sequence", "value": depth, "weight": 0.40, "description": "عمق بررسی سیستم‌ها"},
        {"key": "E_PID2_tool_usage", "value": count_s, "weight": 0.25, "description": "تعداد سیستم‌های بررسی‌شده"},
        {"key": "E_PID3_time_to_action", "value": time_s, "weight": 0.20, "description": "زمان تا اولین اقدام"},
        {"key": "E_PID4_correct_root", "value": root_s, "weight": 0.15, "description": "تشخیص درست علت"},
        {"key": "E_CFI2_perseveration", "value": pers_s, "weight": 0.10, "description": "انعطاف در تغییر راهبرد"},
        {"key": "E_CFI2_exploration", "value": expl_s, "weight": 0.10, "description": "دامنه اکتشاف"},
    ]


async def render_diagnostic_map(scenario: dict, on_complete):
    """رندر مکانیک نقشه تشخیصی — نسخه‌ی ۲"""
    cfg = scenario.get("diagnostic_config", {})
    systems = cfg.get("systems", [])
    npc_hint = cfg.get("npc_hint", "")
    inv_time_ms = cfg.get("investigation_time_ms", 1500)

    state = {
        "systems_investigated": [],
        "investigation_times_ms": {},
        "total_clicks": 0,
        "perseveration_count": 0,
        "first_click_time": None,
        "start_time": time.time(),
        "is_investigating": False,
    }

    card_refs = {}
    detail_refs = {}
    investigated_badges = {}
    step_refs = {}

    # ============================================================
    # راهنمای گام‌به‌گام (بخش اصلی improvement)
    # ============================================================
    with ui.card().classes(
        'w-full bg-slate-800 border-2 border-cyan-400 p-4 mb-3'
    ):
        with ui.row().classes(
            'items-center gap-2 w-full no-wrap mb-3'
        ):
            ui.label("📋").classes('text-2xl')
            ui.label("چطور این مرحله را حل کنی؟").classes(
                'text-base font-bold text-cyan-300'
            )

        # ۳ گام با نشانگر فعال/غیرفعال
        with ui.grid(columns=3).classes(
            'w-full gap-3'
        ):
            # گام ۱
            with ui.element('div').classes(
                'diag-step p-3 rounded border-2 '
                'border-cyan-400 bg-cyan-900/20'
            ) as s1:
                with ui.row().classes(
                    'items-center gap-2 no-wrap mb-1'
                ):
                    ui.label("①").classes(
                        'text-xl text-cyan-400 font-bold'
                    )
                    ui.label("بررسی").classes(
                        'text-sm font-bold text-white'
                    )
                ui.label(
                    "روی هر کارت کلیک کن تا جزئیات سیستم را ببینی."
                ).classes(
                    'text-xs text-gray-300 leading-relaxed'
                )

            # گام ۲
            with ui.element('div').classes(
                'diag-step p-3 rounded border-2 '
                'border-slate-600 bg-slate-900/30'
            ) as s2:
                with ui.row().classes(
                    'items-center gap-2 no-wrap mb-1'
                ):
                    ui.label("②").classes(
                        'text-xl text-slate-500 font-bold'
                    )
                    ui.label("مقایسه").classes(
                        'text-sm font-bold text-slate-400'
                    )
                ui.label(
                    "بین الگوهای سیستم‌ها ارتباط پیدا کن — "
                    "کدام یک علت مشترک است؟"
                ).classes(
                    'text-xs text-gray-400 leading-relaxed'
                )

            # گام ۳
            with ui.element('div').classes(
                'diag-step p-3 rounded border-2 '
                'border-slate-600 bg-slate-900/30'
            ) as s3:
                with ui.row().classes(
                    'items-center gap-2 no-wrap mb-1'
                ):
                    ui.label("③").classes(
                        'text-xl text-slate-500 font-bold'
                    )
                    ui.label("تشخیص").classes(
                        'text-sm font-bold text-slate-400'
                    )
                ui.label(
                    "دکمه‌ی «🎯 تشخیص نهایی» (پایین گرید) "
                    "را بزن و علت اصلی را انتخاب کن."
                ).classes(
                    'text-xs text-gray-400 leading-relaxed'
                )

        step_refs["s1"] = s1
        step_refs["s2"] = s2
        step_refs["s3"] = s3


    # ============================================================
    # هشدار NPC
    # ============================================================
    if npc_hint:
        with ui.card().classes(
            'w-full bg-cyan-900/30 border-2 border-cyan-400 p-3 mb-3'
        ):
            with ui.row().classes('items-start gap-2 no-wrap'):
                ui.label('💡').classes('text-xl flex-shrink-0')
                ui.label(npc_hint).classes(
                    'text-sm text-cyan-200 leading-relaxed flex-1 text-right'
                )

    # ============================================================
    # نوار پیشرفت
    # ============================================================
    with ui.card().classes(
        'w-full bg-slate-800 border-2 border-orange-500 p-3 mb-3'
    ):
        with ui.row().classes(
            'items-center justify-between w-full mb-1'
        ):
            ui.label('📊 پیشرفت بررسی:').classes(
                'text-sm text-orange-400 font-bold'
            )
            progress_label = ui.label(
                f"0 از {len(systems)} سیستم"
            ).classes('text-sm text-white font-bold')
        progress_bar = ui.linear_progress(
            value=0.0, show_value=False
        ).classes('w-full')

        # پیام هدایت‌کننده زیر نوار پیشرفت
        progress_hint = ui.label(
            "برای شروع، روی هر کارتی که می‌خواهی کلیک کن."
        ).classes(
            'text-xs text-gray-400 w-full text-right mt-2 italic'
        )

    # ============================================================
    # Refs — برای دسترسی به دکمه‌ها که بعد از گرید ساخته می‌شوند
    # ============================================================
    refs: dict = {}


    # ============================================================
    # توابع به‌روزرسانی
    # ============================================================
    def _update_ui():
        n = len(state["systems_investigated"])
        total = len(systems)
        progress_label.set_text(f"{n} از {total} سیستم")
        if total > 0:
            progress_bar.set_value(n / total)

        # ---- پیام هدایت‌کننده ----
        if n == 0:
            progress_hint.set_text(
                "برای شروع، روی هر کارتی که می‌خواهی کلیک کن."
            )
            progress_hint.style("color: #90A4AE;")
        elif n == 1:
            progress_hint.set_text(
                "خوب! حالا سیستم‌های دیگر را هم ببین تا "
                "الگوها را مقایسه کنی."
            )
            progress_hint.style("color: #4FC3F7;")
            # گام ۲ فعال
            _activate_step("s2")
        elif n == 2:
            progress_hint.set_text(
                "داری الگوها را می‌بینی. سیستم‌های بیشتری "
                "را بررسی کن تا یقین حاصل شود."
            )
            progress_hint.style("color: #4FC3F7;")
        elif n >= 3 and n < total - 1:
            progress_hint.set_text(
                f"تا حالا {n} سیستم را دیده‌ای. برای "
                f"اطمینان بیشتر، به بقیه هم نگاه کن."
            )
            progress_hint.style("color: #FF8F00;")
        elif n >= total - 1:
            progress_hint.set_text(
                "✓ تقریباً همه‌ی سیستم‌ها را دیدی. "
                "حالا علت ریشه‌ای را تشخیص بده."
            )
            progress_hint.style("color: #4CAF50;")
            # گام ۳ فعال
            _activate_step("s3")

        # ---- Hint پویا (پویا بر اساس پیشرفت) ----
        dh = refs.get("dynamic_hint")
        if dh is not None:
            if n == 0:
                dh.set_text(
                    "👆 روی یکی از کارت‌های بالا کلیک کن تا "
                    "اولین سیستم را بررسی کنی"
                )
                dh.style("color: #4FC3F7;")
            elif n < 3:
                dh.set_text(
                    f"✅ {n} سیستم بررسی شد. حالا "
                    f"کارت‌های دیگر را هم بررسی کن تا "
                    f"الگوها را مقایسه کنی"
                )
                dh.style("color: #4FC3F7;")
            elif n < total:
                dh.set_text(
                    f"🔍 {n} از {total} سیستم بررسی شد. "
                    f"می‌توانی بقیه را هم ببینی یا دکمه‌ی "
                    f"«تشخیص نهایی» را بزنی"
                )
                dh.style("color: #FF8F00;")
            else:
                dh.set_text(
                    "🎯 همه‌ی سیستم‌ها بررسی شد. "
                    "حالا دکمه‌ی «تشخیص نهایی» را بزن"
                )
                dh.style("color: #4CAF50;")

        # ---- دکمه‌ی Submit ----
        btn = refs.get("submit_btn")
        if btn is not None:
            if n >= 1:
                btn.enable()
            else:
                btn.disable()

    def _activate_step(step_key: str):
        """فعال کردن بصری یک گام"""
        el = step_refs.get(step_key)
        if el is None:
            return
        if step_key == "s2":
            el.classes(
                replace=(
                    'diag-step p-3 rounded border-2 '
                    'border-cyan-400 bg-cyan-900/20'
                )
            )
            # تغییر رنگ عدد و عنوان
            try:
                children = el.default_slot.children
                if children:
                    # child 0 = row, child 1 = label
                    row = children[0]
                    row_children = row.default_slot.children
                    if row_children:
                        row_children[0].style("color: #4FC3F7;")
                        row_children[1].style("color: #FFFFFF;")
                    if len(children) > 1:
                        children[1].style("color: #D1D5DB;")
            except Exception:
                pass
        elif step_key == "s3":
            el.classes(
                replace=(
                    'diag-step p-3 rounded border-2 '
                    'border-green-400 bg-green-900/20'
                )
            )
            try:
                children = el.default_slot.children
                if children:
                    row = children[0]
                    row_children = row.default_slot.children
                    if row_children:
                        row_children[0].style("color: #4CAF50;")
                        row_children[1].style("color: #FFFFFF;")
                    if len(children) > 1:
                        children[1].style("color: #D1D5DB;")
            except Exception:
                pass

    # ============================================================
    # بررسی سیستم
    # ============================================================
    async def _investigate(system_id: str):
        if state["is_investigating"]:
            return
        play_scan_sfx()

        if state["first_click_time"] is None:
            state["first_click_time"] = time.time()

        state["total_clicks"] += 1

        # perseveration — قبلاً بررسی شده
        if system_id in state["systems_investigated"]:
            state["perseveration_count"] += 1
            from web_app.audio import notify_with_sound
            notify_with_sound(
                "این سیستم را قبلاً بررسی کردی — "
                "سیستم‌های دیگر را هم ببین",
                type="warning", timeout=2000,
            )
            return

        state["is_investigating"] = True
        card = card_refs[system_id]
        card.classes(
            replace=(
                "diag-card bg-slate-800 border-2 border-orange-500 "
                "p-3 investigating"
            )
        )
        detail_lbl = detail_refs[system_id]
        detail_lbl.set_visibility(True)
        detail_lbl.set_text(
            "⏳ در حال بررسی جزئیات سیستم..."
        )

        await asyncio.sleep(inv_time_ms / 1000)

        state["systems_investigated"].append(system_id)
        state["investigation_times_ms"][system_id] = inv_time_ms
        state["is_investigating"] = False

        card.classes(
            replace=(
                "diag-card bg-slate-800 border-2 border-green-500 "
                "p-3 investigated"
            )
        )
        detail = next(
            s["detail"] for s in systems if s["id"] == system_id
        )
        detail_lbl.set_text(detail)

        if system_id in investigated_badges:
            badge = investigated_badges[system_id]
            badge.set_text("✓ بررسی شد")
            badge.set_visibility(True)

        _update_ui()

    # ============================================================
    # گرید ۶ سیستم
    # ============================================================
    # ✅ shuffle پایدار
    import random as _random
    _saved_order = app.storage.user.get("_diag_order")
    if (
        not _saved_order
        or not isinstance(_saved_order, list)
        or len(_saved_order) != len(systems)
    ):
        _order_ids = [s["id"] for s in systems]
        _random.shuffle(_order_ids)
        app.storage.user["_diag_order"] = _order_ids
        _saved_order = _order_ids

    _sys_map = {s["id"]: s for s in systems}
    _ordered_systems = [
        _sys_map[sid] for sid in _saved_order
        if sid in _sys_map
    ]

    with ui.grid(columns=2).classes('w-full gap-3'):
        for system in _ordered_systems:
            card = ui.card().classes(
                "diag-card bg-slate-800 border "
                "border-slate-600 p-3"
            )
            card_refs[system["id"]] = card

            with card:
                # هدر: آیکون + نام
                with ui.row().classes(
                    'items-center gap-2 w-full mb-1 no-wrap'
                ):
                    ui.label(system.get("icon", "🔧")).classes(
                        'text-2xl flex-shrink-0'
                    )
                    ui.label(system["name"]).classes(
                        'text-sm text-white font-bold flex-1 '
                        'text-right'
                    )

                # ردیف وضعیت بررسی
                with ui.row().classes(
                    'items-center justify-between w-full mb-1'
                ):
                    ui.label(system.get("brief", "")).classes(
                        'text-xs text-gray-400 flex-1 text-right'
                    )
                    inv_badge = ui.label("").classes(
                        'text-xs text-green-300 font-bold '
                        'whitespace-nowrap flex-shrink-0 ml-2'
                    )
                    inv_badge.set_visibility(False)
                    investigated_badges[system["id"]] = inv_badge

                # جزئیات (پنهان)
                detail_lbl = ui.label("").classes(
                    'text-xs text-cyan-200 leading-relaxed '
                    'w-full text-right mt-2 p-2 bg-slate-900 '
                    'rounded border-r-2 border-cyan-500'
                )
                detail_lbl.set_visibility(False)
                detail_refs[system["id"]] = detail_lbl

                # دکمه‌ی بررسی (به‌جای متن ساده)
                inspect_btn = ui.button("🔍 بررسی این سیستم").classes(
                    'w-full text-xs py-1 mt-2 bg-slate-700 '
                    'hover:bg-slate-600 border border-cyan-600'
                )

            # کلیک روی کارت یا دکمه
            async def _card_click(sid=system["id"]):
                await _investigate(sid)

            card.on('click', _card_click)

    _update_ui()

    # ============================================================
    # Hint پویا (بالای دکمه) + دکمه‌ی تشخیص نهایی
    # ============================================================
    refs["dynamic_hint"] = ui.label(
        "👆 روی یکی از کارت‌های بالا کلیک کن تا اولین "
        "سیستم را بررسی کنی"
    ).classes(
        'w-full text-sm text-cyan-300 text-center '
        'p-3 bg-cyan-900/20 rounded '
        'border border-cyan-500 mb-2'
    )

    with ui.row().classes('w-full mb-3'):
        refs["submit_btn"] = ui.button("🎯 تشخیص نهایی").classes(
            'w-full py-3 text-lg font-bold '
            'bg-cyan-600 hover:bg-cyan-500'
        )
        refs["submit_btn"].disable()

    _update_ui()


    # ============================================================
    # دیالوگ تشخیص نهایی
    # ============================================================
    async def _on_submit():
        with ui.dialog() as dialog, ui.card().classes(
            'bg-slate-800 border-2 border-cyan-400 p-6 max-w-2xl'
        ):
            ui.label("🎯 تشخیص نهایی").classes(
                'text-lg font-bold text-cyan-400 mb-2 w-full text-right'
            )
            ui.label(
                "کدام سیستم را علت اصلی همه‌ی هشدارها می‌دانی؟"
            ).classes(
                'text-sm text-gray-300 mb-4 w-full text-right'
            )
            ui.label(
                "با انتخاب خودت، گزارش نهایی به شورا ارسال می‌شود."
            ).classes(
                'text-xs text-gray-400 mb-4 w-full text-right italic'
            )

            # گزینه‌ها با نشانگر وضعیت
            radio = ui.radio(
                options={
                    s["id"]: f"{s.get('icon', '')}  {s['name']}"
                    for s in systems
                },
                value=None,
            ).classes('w-full text-right')

            async def _confirm():
                if radio.value is None:
                    ui.notify(
                        "لطفاً یک سیستم را انتخاب کن",
                        type="warning", position="top", timeout=2000,
                    )
                    return
                dialog.close()
                await _finalize(radio.value)

            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button("انصراف").on_click(dialog.close).classes(
                    'bg-slate-600 hover:bg-slate-500'
                )
                ui.button("✓ تأیید تشخیص").on_click(_confirm).classes(
                    'bg-green-600 hover:bg-green-500'
                )

        dialog.open()

    refs["submit_btn"].on_click(_on_submit)

    # ============================================================
    # نهایی‌سازی
    # ============================================================
    async def _finalize(chosen_root: str):
        systems_investigated = state["systems_investigated"]
        total_inv = len(systems_investigated)
        total_sys = len(systems)
        pers = state["perseveration_count"]

        if state["first_click_time"] is not None:
            tfa = int(
                (state["first_click_time"] - state["start_time"])
                * 1000
            )
        else:
            tfa = 0

        total_time_ms = int(
            (time.time() - state["start_time"]) * 1000
        )

        result = {
            "chosen_root_cause": chosen_root,
            "systems_investigated": systems_investigated,
            "investigation_times_ms": state["investigation_times_ms"],
            "time_to_first_action_ms": tfa,
            "total_time_ms": total_time_ms,
            "total_investigated": total_inv,
            "total_systems": total_sys,
            "perseveration_count": pers,
        }
        result["evidence_items"] = _calc_evidence(result)

        if on_complete:
            await on_complete(result)

