"""
صفحه‌ی آزمون برج هانوی — پروتکل تطبیقی
==========================================
- سطح ۱: ۳ دیسک (گرم‌کردن) — سقف ۲ دقیقه
- سطح ۲: ۴ دیسک (آزمون اصلی) — سقف ۵ دقیقه
- سطح ۳: ۵ دیسک (اختیاری، فقط برای عملکرد بالا) — سقف ۸ دقیقه

ثبت شواهد (۴ شاخص درخواستی):
- تعداد حرکات (کارآمدی)
- متریک‌های زمان (برنامه‌ریزی + اجرا)
- نرخ موفقیت
- تخطی از قواعد

نسخه: 2.0.0
"""
import time
from typing import Any, Callable, TypeVar, cast

from nicegui import ui, app, run

from web_app.config import PAGE_CSS, TEST_MODE
from web_app.components.audio_control import setup_page_audio
from web_app.data.items.tower_of_hanoi_items import (
    ToHLogic, compute_toh_evidence,
)
from web_app.db_manager import (
    save_tower_of_hanoi,
    log_event_threadsafe,
    log_evidence_web,
)
from web_app.audio import play_scan_sfx, play_toast_sfx


# ============================================================
# تنظیمات سطوح
# ============================================================
LEVELS = [
    {
        "disks": 3,
        "time_limit_s": 120,
        "label": "گرم‌کردن",
        "is_optional": False,
    },
    {
        "disks": 4,
        "time_limit_s": 300,
        "label": "آزمون اصلی",
        "is_optional": False,
    },
    {
        "disks": 5,
        "time_limit_s": 480,
        "label": "پیشرفته (اختیاری)",
        "is_optional": True,
    },
]


# ============================================================
# رنگ و عرض دیسک‌ها
# ============================================================
DISK_COLORS = {
    1: "#4FC3F7",   # آبی — کوچک
    2: "#81C784",   # سبز
    3: "#FFB74D",   # نارنجی
    4: "#E57373",   # قرمز
    5: "#BA68C8",   # بنفش — بزرگ
}
DISK_WIDTHS = {
    1: 50,
    2: 63,
    3: 76,
    4: 88,
    5: 100,
}
PEG_LABELS = {
    "A": "میله‌ی چپ",
    "B": "میله‌ی وسط",
    "C": "میله‌ی راست",
}


# ============================================================
# _io wrapper (TypeVar)
# ============================================================
_T = TypeVar("_T")


async def _io(func: Callable[..., _T], **kw: Any) -> _T:
    result = await run.io_bound(func, **kw)
    return cast(_T, result)


# ============================================================
# صفحه
# ============================================================
@ui.page('/tower-of-hanoi')
async def tower_of_hanoi_page():
    participant_id = app.storage.user.get('participant_id')
    session_id = app.storage.user.get('session_id')
    if not participant_id or not session_id:
        ui.navigate.to('/')
        return

    setup_page_audio(None)
    ui.query('body').style(PAGE_CSS)

    state = {
        "phase": "playing",
        "level_idx": 0,
        "levels_results": [],
        "logic": None,
        "selected_peg": None,
        "level_start_time": 0.0,
        "timed_out": False,
        "submitted": False,
    }
    refs: dict = {}
    timer_holder: dict = {"obj": None}

    # ---- تایمر ----
    def _stop_timer():
        if timer_holder["obj"] is not None:
            try:
                timer_holder["obj"].active = False
            except Exception:
                pass
            timer_holder["obj"] = None

    def _start_timer(level_spec: dict):
        _stop_timer()

        async def _tick():
            if state["phase"] != "playing":
                return
            elapsed = int(
                time.time() - state["level_start_time"]
            )
            remaining = max(
                0, level_spec["time_limit_s"] - elapsed
            )
            label = refs.get("timer_label")
            if label is None:
                return
            label.set_text(f"⏱ {remaining}s")
            if remaining <= 30:
                label.style("color: #D32F2F;")
            elif remaining <= 60:
                label.style("color: #FF8F00;")
            if remaining <= 0 and not state["timed_out"]:
                state["timed_out"] = True
                _stop_timer()
                await _on_level_complete()

        timer_holder["obj"] = ui.timer(1.0, _tick)

    # ---- شروع سطح ----
    async def _start_level(level_idx: int):
        state["level_idx"] = level_idx
        state["phase"] = "playing"
        state["selected_peg"] = None
        state["timed_out"] = False
        state["level_start_time"] = time.time()
        spec = LEVELS[level_idx]
        state["logic"] = ToHLogic(num_disks=spec["disks"])
        await _render()

    # ---- رندر ----
    async def _render():
        content.clear()
        with content:
            if state["phase"] == "playing":
                _render_playing()
            elif state["phase"] == "level_result":
                _render_level_result()
            elif state["phase"] == "final":
                _render_final()

    # ---- رندر: در حال بازی ----
    def _render_playing():
        spec = LEVELS[state["level_idx"]]
        logic: ToHLogic = state["logic"]

        ui.label(
            f"🗼 برج هانوی — {spec['disks']} دیسک"
        ).classes(
            'text-2xl font-bold text-cyan-400 '
            'w-full text-right'
        )
        ui.label(
            f"سطح {state['level_idx'] + 1} از "
            f"{len(LEVELS)} — {spec['label']}"
        ).classes(
            'text-sm text-orange-400 font-bold '
            'w-full text-right'
        )

        # راهنما
        with ui.element('div').classes(
            'w-full p-3 rounded border-2 border-cyan-500 '
            'bg-cyan-900/20 mt-2'
        ):
            ui.label(
                "🎯 همه‌ی دیسک‌ها را از میله‌ی چپ به "
                "میله‌ی راست منتقل کن."
            ).classes(
                'text-sm text-white w-full text-right '
                'font-bold'
            )
            ui.label(
                "• فقط می‌توانی دیسک بالایی هر میله را "
                "برداری."
            ).classes(
                'text-xs text-gray-300 w-full text-right'
            )
            ui.label(
                f"• دیسک بزرگ‌تر روی کوچک‌تر قرار نمی‌گیرد."
            ).classes(
                'text-xs text-gray-300 w-full text-right'
            )
            ui.label(
                f"• حداقل حرکت: {logic.MIN_MOVES} — "
                f"سقف زمان: {spec['time_limit_s']}s"
            ).classes(
                'text-xs text-gray-300 w-full text-right'
            )

        # نوار وضعیت
        with ui.row().classes(
            'w-full items-center gap-3 mt-3 no-wrap'
        ):
            refs["timer_label"] = ui.label(
                f"⏱ {spec['time_limit_s']}s"
            ).classes(
                'text-lg font-bold font-mono text-green-400 '
                'flex-1'
            )
            refs["moves_label"] = ui.label(
                f"حرکات: 0 / {logic.MIN_MOVES}"
            ).classes(
                'text-sm text-white font-bold'
            )
            refs["violations_label"] = ui.label(
                "تخطی: 0"
            ).classes(
                'text-sm text-gray-400'
            )

        # میله‌ها
        refs["pegs_container"] = ui.row().classes(
            'w-full justify-around items-end gap-3 mt-3'
        ).style(
            'min-height: 200px; padding: 12px; '
            'background: #0B1D3A; border-radius: 12px; '
            'border: 1px solid #2B4A6F;'
        )

        _render_pegs()

        # دکمه‌ی پایان دستی (برای موارد خاص)
        async def _manual_end():
            if state["phase"] != "playing":
                return
            state["timed_out"] = True
            _stop_timer()
            await _on_level_complete()

        ui.button(
            "پایان این سطح", on_click=_manual_end,
        ).classes(
            'w-full bg-slate-700 hover:bg-slate-600 '
            'text-sm py-2 mt-2 rounded-lg'
        )

        _start_timer(spec)

    def _render_pegs():
        logic: ToHLogic = state["logic"]
        container = refs.get("pegs_container")
        if container is None:
            return
        container.clear()

        with container:
            for peg_id in ("A", "B", "C"):
                is_selected = state["selected_peg"] == peg_id
                disks = logic.pegs[peg_id]
                border_color = (
                    "#FF8F00" if is_selected else "#2B4A6F"
                )

                with ui.column().classes(
                    'items-center gap-1 flex-1'
                ).style('min-width: 80px;'):
                    ui.label(PEG_LABELS[peg_id]).classes(
                        'text-xs text-cyan-400 font-bold'
                    )
                    disk_area = ui.column().classes(
                        'items-center gap-1 w-full'
                    ).style(
                        f'min-height: 160px; '
                        f'border: 2px solid {border_color}; '
                        f'border-radius: 10px; '
                        f'background: rgba(26, 42, 74, 0.5); '
                        f'padding: 6px; '
                        f'justify-content: flex-end; '
                        f'cursor: pointer; '
                        f'transition: all 0.15s;'
                    )

                    with disk_area:
                        # فضای خالی برای دیسک‌های غایب
                        for _ in range(
                            logic.num_disks - len(disks)
                        ):
                            ui.element('div').style(
                                'height: 22px;'
                            )
                        # دیسک‌ها (از پایین به بالا)
                        for disk in reversed(disks):  
                            w = DISK_WIDTHS.get(
                                disk, 50 + disk * 10
                            )
                            c = DISK_COLORS.get(
                                disk, "#4FC3F7"
                            )
                            ui.element('div').style(
                                f'width: {w}%; height: 20px; '
                                f'background: {c}; '
                                f'border-radius: 4px; '
                                f'border: 1px solid '
                                f'rgba(255,255,255,0.3);'
                            )

                    def _make_handler(pid=peg_id):
                        async def _h():
                            await _handle_peg_click(pid)
                        return _h

                    disk_area.on('click', _make_handler())

    # ---- کلیک روی میله ----
    async def _handle_peg_click(peg_id: str):
        if state["phase"] != "playing":
            return
        logic: ToHLogic = state["logic"]

        # انتخاب اول
        if state["selected_peg"] is None:
            if not logic.pegs[peg_id]:
                ui.notify(
                    "این میله خالی است",
                    type='warning', position='top',
                    timeout=1500,
                )
                return
            state["selected_peg"] = peg_id
            _render_pegs()
            return

        # لغو انتخاب
        if state["selected_peg"] == peg_id:
            state["selected_peg"] = None
            _render_pegs()
            return

        # تلاش حرکت
        source = state["selected_peg"]
        state["selected_peg"] = None
        moved, err = logic.try_move(source, peg_id)

        if not moved:
            play_scan_sfx()
            ui.notify(
                f"❌ {err}",
                type='negative', position='top',
                timeout=2000,
            )
            _render_pegs()
            _update_status_labels()
            return

        _render_pegs()
        _update_status_labels()

        if logic.is_solved:
            _stop_timer()
            await _on_level_complete()

    def _update_status_labels():
        logic: ToHLogic = state["logic"]
        metrics = logic.get_metrics()
        moves_lbl = refs.get("moves_label")
        viol_lbl = refs.get("violations_label")
        if moves_lbl is not None:
            moves_lbl.set_text(
                f"حرکات: {metrics['valid_moves']} / "
                f"{logic.MIN_MOVES}"
            )
        if viol_lbl is not None:
            v = metrics["invalid_attempts"]
            viol_lbl.set_text(f"تخطی: {v}")
            if v > 0:
                viol_lbl.style("color: #D32F2F;")

    # ---- پایان سطح ----
    async def _on_level_complete():
        if state["phase"] != "playing":
            return
        _stop_timer()

        logic: ToHLogic = state["logic"]
        metrics = logic.get_metrics()
        metrics["timed_out"] = state["timed_out"]
        metrics["num_disks"] = logic.num_disks
        metrics["min_moves"] = logic.MIN_MOVES

        # ذخیره‌ی سطح
        try:
            await _io(
                save_tower_of_hanoi,
                participant_id=participant_id,
                trial_id=logic.num_disks,
                metrics=metrics,
                move_log=logic.serialize_moves(),
            )
        except Exception as e:
            print(f"⚠️ save_tower_of_hanoi: {e}")

        # ثبت رویداد
        try:
            await _io(
                log_event_threadsafe,
                participant_id=participant_id,
                session_id=session_id,
                event_type='toh_level_completed',
                scenario_id=f"TOH-L{logic.num_disks}",
                metadata=metrics,
            )
        except Exception as e:
            print(f"⚠️ log_event: {e}")

        state["levels_results"].append(metrics)

        # تصمیم سطح بعدی
        solved = metrics["solved"]
        num_disks = logic.num_disks

        # شکست → پایان آزمون
        if not solved:
            state["phase"] = "level_result"
            await _render()
            return

        # سطح ۳ حل شد → پایان
        if num_disks == 5:
            state["phase"] = "level_result"
            await _render()
            return

        # سطح ۳ (گرم‌کردن) → همیشه ادامه
        if num_disks == 3:
            state["phase"] = "level_result"
            await _render()
            return

        # سطح ۴ → فقط اگر عملکرد بالا بود، ۵ پیشنهاد
        if num_disks == 4:
            if _should_offer_level_5(metrics):
                state["phase"] = "level_result"
                await _render()
            else:
                await _finalize()
            return

    def _should_offer_level_5(metrics: dict) -> bool:
        """آیا سطح ۵ پیشنهاد شود؟"""
        moves = metrics.get("valid_moves", 999)
        total_time_ms = (
            metrics.get("planning_time_ms", 0)
            + metrics.get("execution_time_ms", 0)
        )
        # عملکرد بالا: ≤ ۲۰ حرکت و < ۳ دقیقه
        return moves <= 20 and total_time_ms < 180_000

    # ---- رندر: نتیجه‌ی سطح ----
    def _render_level_result():
        metrics = state["levels_results"][-1]
        solved = metrics["solved"]
        timed_out = metrics.get("timed_out", False)
        num_disks = metrics["num_disks"]
        moves = metrics["valid_moves"]
        min_moves = metrics["min_moves"]
        violations = metrics["invalid_attempts"]

        if solved:
            ui.label(
                f"✅ سطح {num_disks} دیسک — حل شد!"
            ).classes(
                'text-2xl font-bold text-green-400 '
                'w-full text-right'
            )
        elif timed_out:
            ui.label(
                f"⏱ سطح {num_disks} دیسک — پایان زمان"
            ).classes(
                'text-2xl font-bold text-orange-400 '
                'w-full text-right'
            )
        else:
            ui.label(
                f"سطح {num_disks} دیسک — پایان"
            ).classes(
                'text-2xl font-bold text-gray-400 '
                'w-full text-right'
            )

        # آمار
        with ui.card().classes(
            'w-full bg-slate-800 border border-cyan-400 '
            'p-4 mt-3'
        ):
            ui.label(
                f"حرکات: {moves} (حداقل: {min_moves})"
            ).classes('text-sm text-white')
            ui.label(
                f"تخطی از قواعد: {violations}"
            ).classes('text-sm text-white')
            ui.label(
                f"زمان برنامه‌ریزی: "
                f"{metrics['planning_time_ms'] / 1000:.1f}s"
            ).classes('text-sm text-white')
            ui.label(
                f"زمان اجرا: "
                f"{metrics['execution_time_ms'] / 1000:.1f}s"
            ).classes('text-sm text-white')

        # تصمیم بعدی
        solved = metrics["solved"]
        num_disks = metrics["num_disks"]

        async def _continue():
            if num_disks == 3:
                await _start_level(1)
            elif num_disks == 4 and solved:
                if _should_offer_level_5(metrics):
                    await _offer_level_5()
                else:
                    await _finalize()
            else:
                await _finalize()

        async def _end_early():
            await _finalize()

        # سطح ۴ + پیشنهاد سطح ۵
        if num_disks == 4 and solved and _should_offer_level_5(
            metrics
        ):
            ui.label(
                "🎯 عملکرد شما درخشان بود! آیا می‌خواهید "
                "سطح پیشرفته (۵ دیسک) را نیز امتحان کنید؟"
            ).classes(
                'text-sm text-cyan-200 w-full text-right '
                'mt-4 p-3 bg-cyan-900/30 rounded'
            )
            with ui.row().classes('w-full gap-2 mt-3'):
                ui.button(
                    "پایان آزمون", on_click=_end_early,
                ).classes(
                    'flex-1 py-3 bg-slate-700 '
                    'hover:bg-slate-600'
                )
                ui.button(
                    "بله، سطح ۵", on_click=_continue,
                ).classes(
                    'flex-1 py-3 bg-green-600 '
                    'hover:bg-green-500 font-bold'
                )
            return

        # ادامه‌ی عادی
        if num_disks == 3:
            ui.button(
                "ادامه به سطح بعدی", on_click=_continue,
            ).classes(
                'w-full py-3 text-lg font-bold '
                'bg-green-600 hover:bg-green-500 mt-3'
            )
        elif num_disks == 4 and solved:
            # این بخش برای سطح ۴ است (اگر به سطح ۵ پیشنهاد نشد)
            ui.button(
                "پایان آزمون", on_click=_finalize,
            ).classes(
                'w-full py-3 text-lg font-bold '
                'bg-cyan-600 hover:bg-cyan-500 mt-3'
            )
        else:
            # شکست در سطح ۴ یا پایان سطح ۵
            ui.button(
                "ادامه", on_click=_finalize,
            ).classes(
                'w-full py-3 text-lg font-bold '
                'bg-cyan-600 hover:bg-cyan-500 mt-3'
            )

    async def _offer_level_5():
        play_toast_sfx()
        await _start_level(2)

    # ---- رندر: پایان ----
    def _render_final():
        ui.label(
            "✅ آزمون برج هانوی خاتمه یافت"
        ).classes(
            'text-2xl font-bold text-cyan-400 '
            'w-full text-center mt-6'
        )

        with ui.card().classes(
            'w-full bg-slate-800 border-2 border-cyan-400 '
            'p-4 mt-4'
        ):
            ui.label("خلاصه‌ی عملکرد:").classes(
                'text-base font-bold text-cyan-300 '
                'w-full text-right mb-2'
            )
            for r in state["levels_results"]:
                status = (
                    "✅ حل شد"
                    if r.get("solved")
                    else "❌ حل نشد"
                )
                ui.label(
                    f"• سطح {r['num_disks']} دیسک — "
                    f"{status} | {r['valid_moves']} حرکت "
                    f"({r['invalid_attempts']} تخطی)"
                ).classes(
                    'text-sm text-white w-full text-right'
                )

        async def _done():
            from web_app.navigation import next_after_toh
            ui.navigate.to(next_after_toh())

        ui.button(
            "ادامه به پرسشنامه‌ها", on_click=_done,
        ).classes(
            'w-full py-3 text-lg font-bold '
            'bg-green-600 hover:bg-green-500 mt-4'
        )

    # ---- نهایی‌سازی ----
    async def _finalize():
        if state["submitted"]:
            return
        state["submitted"] = True
        _stop_timer()

        evidence_items = compute_toh_evidence(
            state["levels_results"]
        )

        for ev in evidence_items:
            try:
                await _io(
                    log_evidence_web,
                    participant_id=participant_id,
                    scenario_id='TOH-01',
                    competency='problem_solving',
                    evidence_key=ev["key"],
                    evidence_value=ev["value"],
                    weight=ev["weight"],
                )
            except Exception as e:
                print(f"⚠️ evidence {ev['key']}: {e}")

        # ثبت رویداد نهایی
        summary = {
            "levels_attempted": len(state["levels_results"]),
            "levels_solved": sum(
                1 for r in state["levels_results"]
                if r.get("solved")
            ),
            "highest_solved": max(
                (
                    r["num_disks"]
                    for r in state["levels_results"]
                    if r.get("solved")
                ),
                default=0,
            ),
            "total_moves": sum(
                r["valid_moves"]
                for r in state["levels_results"]
            ),
            "total_violations": sum(
                r["invalid_attempts"]
                for r in state["levels_results"]
            ),
        }
        try:
            await _io(
                log_event_threadsafe,
                participant_id=participant_id,
                session_id=session_id,
                event_type='tower_of_hanoi_completed',
                scenario_id='TOH-01',
                metadata=summary,
            )
        except Exception as e:
            print(f"⚠️ final event: {e}")

        state["phase"] = "final"
        await _render()

    # ---- ساختار صفحه ----
    with ui.column().classes(
        'w-full max-w-3xl mx-auto p-6 gap-4'
    ):
        ui.label("🗼 آزمون برج هانوی").classes(
            'text-3xl font-bold text-cyan-400 '
            'w-full text-center'
        )
        content = ui.column().classes('w-full gap-3')

    # ---- شروع ----
    await _start_level(0)