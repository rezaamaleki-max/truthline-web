"""
مکانیک کار تکراری (TC-01) — نسخه‌ی وب
==========================================
- ۲۰ لاگ تکراری
- ✅ تأخیر اسپینر ۶۰۰ms برای هر بررسی
- ✅ ۳ وسوسه با متن هم‌راستا با دسکتاپ
- ✅ دکمه‌های خنثی: «ادامه بررسی دستی» / «بررسی خودکار»

نسخه: 2.0.1 — رفع باگ _finalize is unbound
"""
import asyncio
import time
from nicegui import ui

from web_app.config import TEST_MODE


REPETITIVE_CSS_HTML = """
<style>
.rep-row {
    transition: background-color 0.15s, opacity 0.15s;
    cursor: pointer;
    border-radius: 6px;
}
.rep-row:hover {
    background-color: #2B4A6F;
}
.rep-row.checked {
    background-color: rgba(76, 175, 80, 0.10);
    opacity: 0.75;
}
.rep-row.checked .rep-label {
    color: #4CAF50;
}
@keyframes rep-spin {
    to { transform: rotate(360deg); }
}
.rep-spinner {
    display: inline-block;
    animation: rep-spin 0.6s linear infinite;
}
</style>
"""


SPINNER_MS = 600


LOG_ENTRIES = [
    {"id": 1, "ts": "23:01:14", "code": "INFO",
     "text": "دمای کابین: 21.3°C — عادی"},
    {"id": 2, "ts": "23:01:32", "code": "INFO",
     "text": "فشار هوای کابین: 101.2 kPa — عادی"},
    {"id": 3, "ts": "23:02:07", "code": "INFO",
     "text": "سیستم ناوبری: به‌روزرسانی مسیر انجام شد"},
    {"id": 4, "ts": "23:02:45", "code": "INFO",
     "text": "راکتور: پایداری 98.2% — عادی"},
    {"id": 5, "ts": "23:03:11", "code": "WARN",
     "text": "ارتباط ماهواره‌ای: نویز جزئی شناسایی شد"},
    {"id": 6, "ts": "23:04:02", "code": "INFO",
     "text": "سیستم پشتیبان: فعال"},
    {"id": 7, "ts": "23:04:38", "code": "INFO",
     "text": "دمای کابین: 21.4°C — عادی"},
    {"id": 8, "ts": "23:05:19", "code": "INFO",
     "text": "بازچرخانی هوا: عملکرد عادی"},
    {"id": 9, "ts": "23:06:00", "code": "INFO",
     "text": "لاگ دسترسی: ۳ کاربر فعال"},
    {"id": 10, "ts": "23:06:47", "code": "WARN",
     "text": "شبکه برق: نوسان گذرا — ثبت شد"},
    {"id": 11, "ts": "23:07:22", "code": "INFO",
     "text": "سیستم خنک‌کننده: دمای 21.0°C — عادی"},
    {"id": 12, "ts": "23:08:05", "code": "INFO",
     "text": "سنسور ارتعاش: 0.02mm — عادی"},
    {"id": 13, "ts": "23:08:43", "code": "INFO",
     "text": "داده‌های تحقیقاتی: ذخیره‌سازی انجام شد"},
    {"id": 14, "ts": "23:09:18", "code": "INFO",
     "text": "درمانگاه: ۳ خدمه در حالت پایدار"},
    {"id": 15, "ts": "23:10:01", "code": "WARN",
     "text": "سنسور دما: اختلاف 0.2°C — ثبت شد"},
    {"id": 16, "ts": "23:10:42", "code": "INFO",
     "text": "کنترلر اصلی: پاسخ عادی"},
    {"id": 17, "ts": "23:11:29", "code": "INFO",
     "text": "پشتیبان‌گیری خودکار: موفق"},
    {"id": 18, "ts": "23:12:14", "code": "INFO",
     "text": "مدار خنک‌کننده: فشار 2.1 bar — عادی"},
    {"id": 19, "ts": "23:13:08", "code": "INFO",
     "text": "چراغ‌های اضطراری: تست شد"},
    {"id": 20, "ts": "23:13:51", "code": "INFO",
     "text": "وضعیت کلی ایستگاه: پایدار"},
]


TEMPTATION_ROWS = [4, 9, 14]


TEMPTATIONS = {
    4: {
        "name": "مهندس رحیمی",
        "icon": "🔧",
        "message": (
            "تکنسین، یه لحظه. لی رو دیدی؟ راستش، من "
            "نگرانشم. امروز صبح خیلی پریشون بود. اگه "
            "یه سر بهش بزنی، شاید بهتر بشه. این لاگ‌ها "
            "رو بعداً هم می‌تونی بررسی کنی."
        ),
        "manual_label": "ادامه بررسی دستی",
        "auto_label": "بررسی خودکار",
    },
    9: {
        "name": "دکتر آرتمیس",
        "icon": "🔬",
        "message": (
            "تکنسین، یه آنومالی جدید توی داده‌ها پیدا "
            "کردم. نیاز دارم همین الان بیای. لاگ‌ها رو "
            "بذار برای بعد — این فوری‌تره."
        ),
        "manual_label": "ادامه بررسی دستی",
        "auto_label": "بررسی خودکار",
    },
    14: {
        "name": "مهندس رحیمی",
        "icon": "🔧",
        "message": (
            "تکنسین، جلسه‌ی شورا فرداست. بذار این رو "
            "به یکی دیگه بسپاریم و بریم گزارش رو برای "
            "شورا آماده کنیم. تمرکزت روی اون مهم‌تره."
        ),
        "manual_label": "ادامه بررسی دستی",
        "auto_label": "بررسی خودکار",
    },
}


def _calc_tc01_evidence(result: dict) -> list:
    """محاسبه‌ی شواهد TC-01."""
    total_rows = result.get("total_rows", 20)
    honest_checked = result.get("honest_checked", 0)
    completion_rate = (
        honest_checked / total_rows if total_rows > 0 else 0.0
    )
    cheat_used = result.get("cheat_used", False)
    rejected_temptation = result.get(
        "rejected_temptation", False
    )
    accuracy = 1.0 if not cheat_used else 0.3

    return [
        {
            "key": "E_TC1_completion_rate",
            "value": round(completion_rate, 3),
            "weight": 0.45,
            "description": "نسبت لاگ‌های بررسی‌شده",
        },
        {
            "key": "E_TC1_accuracy",
            "value": accuracy,
            "weight": 0.30,
            "description": "کیفیت بررسی (پرهیز از میان‌بر)",
        },
        {
            "key": "E_TC1_rejected_temptation",
            "value": 1.0 if rejected_temptation else 0.0,
            "weight": 0.25,
            "description": "مقاومت در برابر وسوسه",
        },
    ]


async def render_repetitive_task(scenario: dict, on_complete):
    """رندر مکانیک کار تکراری."""
    cfg = scenario.get("repetitive_task_config", {})
    default_name = cfg.get("npc_name", "مهندس رحیمی")
    default_msg = cfg.get("npc_message", "")

    state = {
        "checked": set(),
        "cheat_used": False,
        "cheat_trigger_row": -1,
        "temptations_shown": 0,
        "temptations_rejected": 0,
        "temptations_accepted": 0,
        "start_time": time.time(),
        "submitted": False,
        "npc_shown": set(),
        "is_checking": False,
        "checking_row": -1,
    }

    checked_badges = {}
    refs: dict = {}

    # ============================================================
    # ۱. توابع پایه (قبل از استفاده تعریف می‌شوند)
    # ============================================================
    def _update_progress():
        n = len(state["checked"])
        progress_label.set_text(
            f"{n} از {len(LOG_ENTRIES)} بررسی‌شده"
        )
        progress_bar.set_value(n / len(LOG_ENTRIES))
        btn = refs.get("submit_btn")
        if btn is not None:
            if n >= len(LOG_ENTRIES):
                btn.enable()
            else:
                btn.disable()

    async def _finalize():
        """✅ قبل از همه تعریف می‌شود تا در closures معتبر باشد."""
        if state["submitted"]:
            return
        state["submitted"] = True
        btn = refs.get("submit_btn")
        if btn is not None:
            btn.disable()

        total_time = int(
            (time.time() - state["start_time"]) * 1000
        )
        honest_checked = (
            len(LOG_ENTRIES)
            if state["cheat_used"]
            else len(state["checked"])
        )

        result = {
            "total_rows": len(LOG_ENTRIES),
            "honest_checked": honest_checked,
            "auto_checked": (
                len(LOG_ENTRIES) - honest_checked
            ),
            "completion_rate": round(
                honest_checked / len(LOG_ENTRIES), 3
            ),
            "cheat_used": state["cheat_used"],
            "cheat_trigger_row": state["cheat_trigger_row"],
            "temptations_shown": state["temptations_shown"],
            "temptations_rejected": state[
                "temptations_rejected"
            ],
            "temptations_accepted": state[
                "temptations_accepted"
            ],
            "rejected_temptation": (
                state["temptations_accepted"] == 0
            ),
            "total_time_ms": total_time,
        }
        result["evidence_items"] = _calc_tc01_evidence(result)

        if on_complete:
            await on_complete(result)

    # ============================================================
    # ۲. توابع وابسته (می‌توانند به _finalize ارجاع دهند)
    # ============================================================
    async def _accept_temptation(row_idx: int):
        state["cheat_used"] = True
        state["cheat_trigger_row"] = row_idx
        state["temptations_accepted"] += 1

        for entry in LOG_ENTRIES:
            state["checked"].add(entry["id"])
            badge = checked_badges.get(entry["id"])
            if badge is not None:
                badge.set_text("✓")
                badge.style(
                    "color: #4CAF50; font-weight: bold;"
                )
                try:
                    badge.parent_slot.parent.classes(
                        replace="rep-row checked p-2"
                    )
                except Exception:
                    pass

        _update_progress()
        ui.notify(
            "بررسی خودکار فعال شد — همه‌ی لاگ‌ها ثبت شدند",
            type='info', position='top', timeout=2500,
        )
        await asyncio.sleep(1.2)
        await _finalize()

    def _reject_temptation(row_idx: int):
        state["temptations_rejected"] += 1
        ui.notify(
            "به بررسی دستی ادامه بده...",
            type='info', position='top', timeout=1500,
        )

    def _show_npc_dialog(row_idx: int):
        t = TEMPTATIONS.get(row_idx)
        if not t:
            t = {
                "name": default_name,
                "icon": "👤",
                "message": default_msg,
                "manual_label": "ادامه بررسی دستی",
                "auto_label": "بررسی خودکار",
            }

        with ui.dialog() as dlg, ui.card().classes(
            'bg-slate-800 border-2 border-orange-400 '
            'p-5 max-w-lg'
        ):
            with ui.row().classes(
                'items-center gap-2 w-full mb-3 no-wrap'
            ):
                ui.label(t["icon"]).classes('text-2xl')
                ui.label(f"{t['name']}:").classes(
                    'text-lg font-bold text-orange-400'
                )
            ui.label(t["message"]).classes(
                'text-base text-white leading-relaxed '
                'w-full text-right mb-4'
            )

            async def _on_manual():
                dlg.close()
                _reject_temptation(row_idx)

            async def _on_auto():
                dlg.close()
                await _accept_temptation(row_idx)

            with ui.row().classes(
                'w-full justify-end gap-2 mt-2'
            ):
                ui.button(
                    t["manual_label"],
                    on_click=_on_manual,
                ).classes('bg-slate-600 hover:bg-slate-500')
                ui.button(
                    t["auto_label"],
                    on_click=_on_auto,
                ).classes(
                    'bg-cyan-600 hover:bg-cyan-500'
                )

        dlg.open()

    async def _on_row_click(entry_id: int, row_idx: int):
        if state["is_checking"]:
            return
        if state["cheat_used"] or state["submitted"]:
            return
        if entry_id in state["checked"]:
            return

        state["is_checking"] = True
        state["checking_row"] = row_idx
        badge = checked_badges.get(entry_id)
        if badge is not None:
            badge.set_text("◐")
            badge.style(
                "color: #FF8F00; font-weight: bold; "
                "font-size: 14px; min-width: 20px;"
            )
            try:
                badge.classes(add="rep-spinner")
            except Exception:
                pass

        await asyncio.sleep(SPINNER_MS / 1000.0)

        if badge is not None:
            try:
                badge.classes(remove="rep-spinner")
            except Exception:
                pass
            badge.set_text("✓")
            badge.style(
                "color: #4CAF50; font-weight: bold; "
                "font-size: 14px; min-width: 20px;"
            )
            try:
                badge.parent_slot.parent.classes(
                    replace="rep-row checked p-2"
                )
            except Exception:
                pass

        state["checked"].add(entry_id)
        state["is_checking"] = False
        state["checking_row"] = -1
        _update_progress()

        if (row_idx in TEMPTATION_ROWS
                and not state["cheat_used"]
                and row_idx not in state["npc_shown"]):
            state["npc_shown"].add(row_idx)
            state["temptations_shown"] += 1
            _show_npc_dialog(row_idx)

    # ============================================================
    # ۳. UI
    # ============================================================
    ui.label("📋 لاگ‌های بی‌پایان").classes(
        'text-xl font-bold text-cyan-400 w-full text-right'
    )

    with ui.element('div').classes(
        'w-full p-3 rounded border-2 border-orange-500 '
        'bg-orange-900/20 my-2'
    ):
        ui.label("💡 راهنما").classes(
            'text-sm font-bold text-orange-400 mb-1 '
            'w-full text-right'
        )
        ui.label(
            f"• {len(LOG_ENTRIES)} لاگ را یکی‌یکی بررسی کن. "
            f"روی هر لاگ کلیک کن تا جزئیاتش را ببینی، "
            f"سپس آن را تیک بزن."
        ).classes('text-xs text-gray-300 w-full text-right')
        ui.label(
            "• هر بررسی کمی طول می‌کشد — بخش‌های خودکار "
            "نمی‌توانند الگوهای خاص را تشخیص دهند؛ "
            "فقط چشم انسان."
        ).classes('text-xs text-gray-300 w-full text-right')

    with ui.card().classes(
        'w-full bg-slate-800 border-2 border-orange-400 p-3'
    ):
        with ui.row().classes(
            'items-center justify-between w-full'
        ):
            ui.label("📊 پیشرفت:").classes(
                'text-sm text-orange-400 font-bold'
            )
            progress_label = ui.label(
                f"0 از {len(LOG_ENTRIES)} بررسی‌شده"
            ).classes('text-sm text-white font-bold')
        progress_bar = ui.linear_progress(
            value=0.0, show_value=False
        ).classes('w-full mt-2')

    # لیست لاگ‌ها
    with ui.column().classes(
        'w-full gap-1 bg-slate-900 p-3 rounded '
        'border border-slate-700 mt-3'
    ):
        for idx, entry in enumerate(LOG_ENTRIES):
            with ui.row().classes(
                'rep-row p-2 items-center gap-3 no-wrap '
                'w-full'
            ) as row_widget:
                badge = ui.label("○")
                badge.style(
                    "color: #666666; font-weight: bold; "
                    "font-size: 14px; min-width: 20px;"
                )
                checked_badges[entry["id"]] = badge

                ui.label(
                    f"[{entry['code']}]"
                ).classes(
                    'text-xs font-mono flex-shrink-0'
                ).style(
                    "color: #4FC3F7; min-width: 50px;"
                )
                ui.label(entry["ts"]).classes(
                    'text-xs font-mono text-gray-500 '
                    'flex-shrink-0'
                ).style("min-width: 70px;")

                ui.label(entry["text"]).classes(
                    'rep-label text-sm text-white flex-1 '
                    'text-right'
                )

            def _make_handler(eid=entry["id"], ridx=idx):
                async def _h(e=None):
                    await _on_row_click(eid, ridx)
                return _h

            row_widget.on('click', _make_handler())

    _update_progress()

    # دکمه‌ی ثبت — _finalize از قبل تعریف شده
    with ui.row().classes('w-full mt-3'):
        refs["submit_btn"] = ui.button(
            "✓ ثبت بررسی",
        ).classes(
            'w-full py-3 text-lg font-bold '
            'bg-green-600 hover:bg-green-500'
        )
        refs["submit_btn"].disable()
        refs["submit_btn"].on_click(_finalize)

