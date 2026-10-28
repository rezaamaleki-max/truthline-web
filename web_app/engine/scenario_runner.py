"""
موتور اجرای فازها در وب — نسخه‌ی پارامتری
==========================================
پشتیبانی از همه‌ی مکانیک‌ها:
- quantum_analyzer, calibration_sliders
- diagnostic_map, resource_allocation, dependency_board
- innovation_puzzle
- repetitive_task, accountability_dialog
"""
import time
from typing import Any, Callable, TypeVar, cast

from nicegui import ui, app, run

from web_app.config import (
    load_scenario,
    parse_inner_thoughts,
    calculate_evidence_value,
    SUPPORTED_MECHANICS,
    PENDING_MECHANICS,
    should_skip_evidence,
    SHOW_CHOICE_TOAST,
)
from web_app.engine.relationship_rules import (
    get_relationship_deltas,
)
from web_app.db_manager import (
    log_event_threadsafe,
    log_evidence_web,
    update_relationship_web,
    log_schema_evidence,
)

from web_app.audio import (
    play_choice_sfx,
    play_scan_sfx,
    play_transition_sfx,
    play_toast_sfx,
    notify_with_sound,
)

# ============================================================
# ✅ Wrapper برای run.io_bound با type hint صریح
#    (رفع خطای Pylance: "None is not awaitable")
# ============================================================
_T = TypeVar("_T")


async def _io(
    func: Callable[..., _T],
    **kwargs: Any,
) -> _T:
    """
    معادل run.io_bound با type hint صریح.
    Pylance را قانع می‌کند که نتیجه قابل await است.
    """
    result = await run.io_bound(func, **kwargs)
    return cast(_T, result)


# ============================================================
# ✅ پیش‌فرض شایستگی بر اساس فاز
# ============================================================
PHASE_DEFAULT_COMPETENCY = {
    "phase1": "honesty",
    "phase2": "trustworthiness",
    "phase3": "problem_solving",
    "phase4": "accountability",
}


def _default_state() -> dict:
    return {
        "scenario_index": 0,
        "dialogue_index": 0,
        "result_index": 0,
        "state": "dialogue",
        "quantum_readings": [],
        "calibration_result": {},
    }


def _state_key(phase_key: str, participant_id: str) -> str:
    return f"{phase_key}_state_{participant_id}"


def _load_state(phase_key: str, participant_id: str) -> dict:
    key = _state_key(phase_key, participant_id)
    state = app.storage.user.get(key)
    if not state:
        # ✅ تلاش برای بازیابی از دیتابیس (پس از refresh)
        try:
            from web_app.db_manager import get_phase_progress
            db_row = get_phase_progress(
                participant_id, phase_key
            )
            if db_row and isinstance(db_row, dict):
                db_state = db_row.get("state")
                if isinstance(db_state, dict):
                    state = db_state
                    print(
                        f"   [RESUME] بازیابی {phase_key} از "
                        f"دیتابیس: scenario_index="
                        f"{state.get('scenario_index', 0)}"
                    )
        except Exception as e:
            print(f"   [RESUME] خطا در بازیابی: {e}")

        if not state:
            state = _default_state()
        app.storage.user[key] = state
    return state


def _save_state(phase_key: str, participant_id: str, state: dict):
    app.storage.user[_state_key(phase_key, participant_id)] = state

    # ✅ ذخیره‌ی best-effort در دیتابیس (fire-and-forget)
    try:
        import asyncio
        from web_app.db_manager import save_phase_progress

        scenario_index = int(state.get("scenario_index", 0))
        # snapshot برای جلوگیری از race
        state_snapshot = dict(state)

        async def _persist():
            try:
                await asyncio.to_thread(
                    save_phase_progress,
                    participant_id,
                    phase_key,
                    scenario_index,
                    state_snapshot,
                )
            except Exception as e:
                print(f"   [SAVE] خطا در ذخیره: {e}")

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_persist())
        except RuntimeError:
            # اگر event loop در دسترس نیست، سینک انجام بده
            save_phase_progress(
                participant_id,
                phase_key,
                scenario_index,
                state_snapshot,
            )
    except Exception as e:
        print(f"   [SAVE] خطا در آماده‌سازی: {e}")


async def record_choice_effects(
    scenario: dict, choice: dict, decision_time: int,
    participant_id: str, session_id: str,
    phase_key: str,
):
    """ثبت شواهد، رویداد و روابط."""
    scenario_id = scenario["scenario_id"]

    # ✅ اولویت: competency_override → پیش‌فرض فاز
    competency = scenario.get(
        "competency_override",
        PHASE_DEFAULT_COMPETENCY.get(phase_key, "honesty"),
    )

    for ev_id, ev_def in scenario.get(
        "evidence_model", {}
    ).items():
        formula = ev_def.get("formula", "")
        if should_skip_evidence(formula):
            print(
                f"   [SKIP] {ev_id}: deferred "
                f"— در ResultsScene"
            )
            continue
        weight = ev_def.get("weight", 1.0)
        value = calculate_evidence_value(
            formula, choice, decision_time
        )
        await _io(
            log_evidence_web,
            participant_id=participant_id,
            scenario_id=scenario_id,
            competency=competency,
            evidence_key=ev_id,
            evidence_value=value,
            weight=weight,
        )

    await _io(
        log_event_threadsafe,
        participant_id=participant_id,
        session_id=session_id,
        event_type='choice_made',
        scenario_id=scenario_id,
        choice_id=choice.get("id", 0),
        decision_time_ms=decision_time,
        metadata={
            "choice_text": choice.get("text_fa", ""),
            "thought": choice.get("thought", ""),
            "phase": phase_key,
        },
    )

    deltas = get_relationship_deltas(
        phase_key, scenario_id, choice.get("id", 0)
    )
    for char_key, delta in deltas.items():
        await _io(
            update_relationship_web,
            participant_id=participant_id,
            character_key=char_key,
            delta=delta,
        )
    # ✅ ثبت طرح‌واره‌ی استدلالی (MRL)
    schema = choice.get("schema")
    if schema and isinstance(schema, dict):
        primary = schema.get("primary", "")
        if primary in (
            "personal_interest",
            "maintaining_norms",
            "postconventional",
        ):
            await _io(
                log_schema_evidence,
                participant_id=participant_id,
                scenario_id=scenario_id,
                choice_id=choice.get("id", 0),
                schema_primary=primary,
                schema_secondary=schema.get("secondary") or "",
                reaction_time_ms=decision_time,
            )

def _advance_to_next_scenario(state: dict):
    state["scenario_index"] += 1
    state["dialogue_index"] = 0
    state["result_index"] = 0
    state["state"] = "dialogue"
    state["quantum_readings"] = []
    state["calibration_result"] = {}
    for k in [
        "_current_choice", "_current_root_cause",
        "_allocation_result", "_dependency_result",
        "_calibration_values", "_choice_start_time",
        "_puzzle_result",
    ]:
        state.pop(k, None)


def _get_result_dialogues(
    scenario: dict, state: dict
) -> list:
    """
    دیالوگ‌های نتیجه — با fallback هوشمند.

    ترتیب اولویت:
    ۱. اگر root_cause موجود و دیالوگ دارد
    ۲. اگر choice موجود و دیالوگ دارد
    ۳. fallback به دیالوگ عمومی (مثل کالیبراسیون)
    """
    # ۱. دیالوگ بر اساس علت ریشه‌ای (برای PID-01)
    if "result_dialogue_by_root_cause" in scenario:
        root_cause = state.get("_current_root_cause", "")
        dialogues = scenario[
            "result_dialogue_by_root_cause"
        ].get(root_cause, [])
        if dialogues:
            return dialogues

    # ۲. دیالوگ بر اساس انتخاب (برای سناریوهای دیالوگ‌محور)
    current_choice = state.get("_current_choice")
    if (
        "result_dialogue_by_choice" in scenario
        and current_choice
    ):
        cid_str = str(current_choice.get("id", 0))
        dialogues = scenario[
            "result_dialogue_by_choice"
        ].get(cid_str, [])
        if dialogues:
            return dialogues

    # ۳. fallback به دیالوگ عمومی
    #    (برای کالیبراسیون، کوانتومی، و سایر مکانیک‌ها)
    if "result_dialogue" in scenario:
        return scenario["result_dialogue"] or []

    return []


def _calc_dependency_evidence(
    ev_id: str, result: dict
) -> float:
    if ev_id == "E_SPA1_sequence_score":
        return result["sequence_score"]
    if ev_id == "E_SPA1_planning_time":
        t = result["planning_time_ms"]
        if 5000 <= t <= 30000:
            return 1.0
        if t < 5000:
            return 0.4
        if t <= 60000:
            return 0.6
        return 0.3
    if ev_id == "E_SPA1_efficiency":
        return result["sequence_score"]
    return 0.5


def _advance_after_dialogues(
    state: dict, mechanic, scenario: dict
):
    if mechanic is None:
        state["state"] = "choice"
    elif mechanic == "quantum_analyzer":
        state["state"] = "quantum"
    elif mechanic == "calibration_sliders":
        state["state"] = "calibration"
    elif mechanic == "diagnostic_map":
        state["state"] = "diagnostic"
    elif mechanic == "resource_allocation":
        state["state"] = "allocation"
    elif mechanic == "dependency_board":
        state["state"] = "dependency"
    elif mechanic == "innovation_puzzle":
        state["state"] = "puzzle"
    elif mechanic == "repetitive_task":
        state["state"] = "repetitive"
    elif mechanic == "accountability_dialog":
        state["state"] = "accountability"
    elif mechanic in PENDING_MECHANICS:
        if scenario.get("choices"):
            print(
                f"   ⚠️ مکانیک '{mechanic}' پیاده‌نشده — "
                f"نمایش گزینه‌ها"
            )
            state["state"] = "choice"
        else:
            print(
                f"   ⚠️ مکانیک '{mechanic}' پیاده‌نشده "
                f"و گزینه‌ای هم نیست — پرش"
            )
            _advance_to_next_scenario(state)
    else:
        state["state"] = "choice"


async def render_phase(
    phase_key: str,
    scenarios_order: list,
    phase_title: str,
    participant_id: str,
    session_id: str,
    on_complete,
):
    """رندر یک فاز."""
    state = _load_state(phase_key, participant_id)
    container = ui.column().classes('w-full gap-4')

    async def _re_render():
        container.clear()
        with container:
            await _render_view()

    async def _render_view():
        if state["scenario_index"] >= len(scenarios_order):
            # ✅ صدای transition در پایان فاز
            play_transition_sfx()
            await on_complete()
            return

        scenario_id = scenarios_order[
            state["scenario_index"]
        ]
        scenario = load_scenario(scenario_id, phase=phase_key)
        parse_inner_thoughts(scenario)

        dialogues = (
            scenario.get("intro_sequence", [])
            + scenario.get("dialogue_sequence", [])
        )
        mechanic = scenario.get("special_mechanic")

        # ---- HUD (جایگزین هدر قدیمی) ----
        from web_app.components.hud import render_hud
        sub_prog = (
            state["scenario_index"]
            / max(1, len(scenarios_order))
        )
        await render_hud(
            stage_key=phase_key,
            sub_progress=sub_prog,
            scenario_current=state["scenario_index"],
            scenario_total=len(scenarios_order),
            objective=scenario.get('title_fa', ''),
        )
        # ✅ عنوان سناریو فقط در HUD نمایش داده می‌شود
        # (طبق بازخورد کاربر: حذف از بدنه‌ی صفحه)

        # ---- هندلرها ----
        async def handle_next_dialogue():
            idx = state["dialogue_index"]
            if idx + 1 >= len(dialogues):
                _advance_after_dialogues(
                    state, mechanic, scenario
                )
            else:
                state["dialogue_index"] = idx + 1
            _save_state(phase_key, participant_id, state)
            await _re_render()

        async def handle_next_result():
            scenario_ = load_scenario(
                scenarios_order[state["scenario_index"]],
                phase=phase_key,
            )
            result_dialogues = _get_result_dialogues(
                scenario_, state
            )
            idx = state["result_index"]
            if idx + 1 >= len(result_dialogues):
                # ✅ اگر بازیکن هنوز انتخاب نکرده و سناریو گزینه دارد
                #    → برو به گزینه‌ها (نه به سناریوی بعدی)
                #    این حالت برای کالیبراسیون، تشخیص، و کوانتومی است
                if (
                    not state.get("_current_choice")
                    and scenario_.get("choices")
                ):
                    state["state"] = "choice"
                    state["_choice_start_time"] = time.time()
                else:
                    _advance_to_next_scenario(state)
            else:
                state["result_index"] = idx + 1
            _save_state(phase_key, participant_id, state)
            await _re_render()

        async def handle_choice_picked(choice):
            start_t = state.get("_choice_start_time")
            if start_t:
                decision_time = int(
                    (time.time() - start_t) * 1000
                )
            else:
                decision_time = 1500

            # ✅ بازخورد فوری: toast با صدای استاندارد توست
            if SHOW_CHOICE_TOAST:
                notify_with_sound(
                    '✓ انتخاب شما ثبت شد',
                    type='positive',
                    timeout=1500,
                )

            await record_choice_effects(
                scenario, choice, decision_time,
                participant_id, session_id, phase_key,
            )

            state["_current_choice"] = choice
            result_dialogues = _get_result_dialogues(
                scenario, state
            )
            if result_dialogues:
                state["state"] = "result_dialogue"
                state["result_index"] = 0
                _save_state(
                    phase_key, participant_id, state
                )
            else:
                _advance_to_next_scenario(state)
                _save_state(
                    phase_key, participant_id, state
                )
            await _re_render()

        current = state["state"]

        # ---- ۱. دیالوگ ----
        if current == "dialogue":
            idx = state["dialogue_index"]
            if idx < len(dialogues):
                d = dialogues[idx]
                _speaker = d.get('speaker', '')
                _text = d.get('text_fa', '')

                # ✅ حل پرتره
                from web_app.character_utils import (
                    resolve_portrait_url,
                )
                _portrait = resolve_portrait_url(
                    _speaker, _text, d.get('emotion')
                )

                with ui.card().classes(
                    'w-full bg-slate-800 border-2 '
                    'border-cyan-400 p-4'
                ):
                    with ui.row().classes(
                        'items-start gap-4 w-full no-wrap'
                    ):
                        if _portrait:
                            with ui.element('div').classes(
                                'flex-shrink-0'
                            ):
                                ui.image(_portrait).style(
                                    'width: 100px; '
                                    'height: 130px; '
                                    'border-radius: 10px; '
                                    'border: 2px solid #4FC3F7; '
                                    'object-fit: cover; '
                                    'background: #0B1D3A;'
                                )
                        with ui.column().classes(
                            'flex-1 gap-2'
                        ):
                            ui.label(
                                f"[{_speaker}]"
                            ).classes(
                                'text-sm text-cyan-400 '
                                'font-bold w-full text-right'
                            )
                            ui.label(_text).classes(
                                'text-base text-white '
                                'leading-relaxed w-full '
                                'text-right '
                                'whitespace-pre-line'
                            )
                ui.button(
                    'ادامه', on_click=handle_next_dialogue,
                ).classes(
                    'w-full py-3 text-lg font-bold '
                    'bg-cyan-600 hover:bg-cyan-500 mt-4'
                )

        # ---- ۲. کوانتومی ----
        elif current == "quantum":
            cfg = scenario.get("quantum_config", {})
            readings = cfg.get(
                "readings", [7.8, 8.2, 7.5]
            )
            unit = cfg.get("unit", "دامنه موج")
            warning = cfg.get("warning_text", "")
            activation_button = cfg.get(
                "activation_button", "فروپاشی تابع موج"
            )
            activation_delay = cfg.get(
                "activation_delay_ms", 1400
            )

            ui.label('⚛️ تحلیلگر کوانتومی').classes(
                'text-xl font-bold text-cyan-400 '
                'w-full text-right mb-4'
            )

            async def on_quantum_complete(
                final_readings: list, total_time: int
            ):
                play_toast_sfx()  
                state["quantum_readings"] = final_readings
                state["quantum_total_time"] = total_time
                avg = (
                    sum(final_readings)
                    / len(final_readings)
                )

                await _io(
                    log_event_threadsafe,
                    participant_id=participant_id,
                    session_id=session_id,
                    event_type='quantum_readings_completed',
                    scenario_id=scenario_id,
                    metadata={
                        'readings': final_readings,
                        'average': round(avg, 2),
                        'total_reading_time_ms': total_time,
                        'reading_count': len(final_readings),
                    },
                )

                state["state"] = "choice"
                _save_state(
                    phase_key, participant_id, state
                )
                await _re_render()

            from web_app.components.quantum_analyzer import (
                render_quantum_analyzer,
            )
            await render_quantum_analyzer(
                readings=readings,
                unit=unit,
                warning_text=warning,
                activation_button=activation_button,
                activation_delay_ms=activation_delay,
                on_complete=on_quantum_complete,
            )

        # ---- ۳. کالیبراسیون ----
        elif current == "calibration":
            sensors = scenario.get(
                "calibration_config", {}
            ).get("sensors", [])

            async def on_calibration_complete(result: dict):
                play_toast_sfx()  # ✅ صدای خروج (طبق درخواست شما)
                state["calibration_result"] = result
                await _io(
                    log_event_threadsafe,
                    participant_id=participant_id,
                    session_id=session_id,
                    event_type='calibration_completed',
                    scenario_id=scenario_id,
                    metadata=result,
                )
                # ✅ بررسی دیالوگ نتیجه
                result_dialogues = scenario.get("result_dialogue", [])
                if result_dialogues:
                    state["state"] = "result_dialogue"
                    state["result_index"] = 0
                else:
                    state["state"] = "choice"
                _save_state(phase_key, participant_id, state)
                await _re_render()

            # ✅✅✅ این سه خط حیاتی — جا افتاده بود!
            from web_app.components.calibration import (
                render_calibration,
            )
            await render_calibration(
                sensors=sensors,
                on_complete=on_calibration_complete,
            )

        # ---- ۴. نقشه تشخیصی ----
        elif current == "diagnostic":
            async def on_diagnostic_complete(result: dict):
                play_toast_sfx() 
                for ev in result["evidence_items"]:
                    await _io(
                        log_evidence_web,
                        participant_id=participant_id,
                        scenario_id=scenario_id,
                        competency="problem_solving",
                        evidence_key=ev["key"],
                        evidence_value=ev["value"],
                        weight=ev["weight"],
                    )
                await _io(
                    log_event_threadsafe,
                    participant_id=participant_id,
                    session_id=session_id,
                    event_type='diagnosis_completed',
                    scenario_id=scenario_id,
                    metadata={
                        "chosen_root_cause":
                            result["chosen_root_cause"],
                        "systems_investigated":
                            result["systems_investigated"],
                        "total_investigated":
                            result["total_investigated"],
                        "perseveration_count":
                            result["perseveration_count"],
                        "time_to_first_action_ms":
                            result["time_to_first_action_ms"],
                    },
                )
                state["diagnostic_result"] = result
                state["_current_root_cause"] = result[
                    "chosen_root_cause"
                ]
                state["state"] = "result_dialogue"
                state["result_index"] = 0
                _save_state(
                    phase_key, participant_id, state
                )
                await _re_render()

            from web_app.components.diagnostic_map import (
                render_diagnostic_map,
            )
            await render_diagnostic_map(
                scenario, on_diagnostic_complete
            )

        # ---- ۵. تخصیص منابع ----
        elif current == "allocation":
            async def on_allocation_complete(result: dict):
                play_toast_sfx()
                for ev in result["evidence_items"]:
                    await _io(
                        log_evidence_web,
                        participant_id=participant_id,
                        scenario_id=scenario_id,
                        competency="problem_solving",
                        evidence_key=ev["key"],
                        evidence_value=ev["value"],
                        weight=ev["weight"],
                    )
                await _io(
                    log_event_threadsafe,
                    participant_id=participant_id,
                    session_id=session_id,
                    event_type='allocation_completed',
                    scenario_id=scenario_id,
                    metadata={
                        "allocations":
                            result["allocations"],
                        "info_checked":
                            result["info_checked"],
                        "total_time_ms":
                            result["total_time_ms"],
                    },
                )
                state["_allocation_result"] = result
                state["state"] = "result_dialogue"
                state["result_index"] = 0
                _save_state(
                    phase_key, participant_id, state
                )
                await _re_render()

            from web_app.components.resource_allocation import (
                render_resource_allocation,
            )
            await render_resource_allocation(
                scenario, on_allocation_complete
            )

        # ---- ۶. تخته وابستگی ----
        elif current == "dependency":
            async def on_dependency_complete(result: dict):
                play_toast_sfx()
                for ev_id, ev_def in scenario.get(
                    "evidence_model", {}
                ).items():
                    value = _calc_dependency_evidence(
                        ev_id, result
                    )
                    await _io(
                        log_evidence_web,
                        participant_id=participant_id,
                        scenario_id=scenario_id,
                        competency="problem_solving",
                        evidence_key=ev_id,
                        evidence_value=value,
                        weight=ev_def.get("weight", 1.0),
                    )
                await _io(
                    log_event_threadsafe,
                    participant_id=participant_id,
                    session_id=session_id,
                    event_type='dependency_board_completed',
                    scenario_id=scenario_id,
                    metadata=result,
                )
                state["_dependency_result"] = result
                state["state"] = "result_dialogue"
                state["result_index"] = 0
                _save_state(
                    phase_key, participant_id, state
                )
                await _re_render()

            from web_app.components.dependency_board import (
                render_dependency_board,
            )
            await render_dependency_board(
                scenario, on_dependency_complete
            )

        # ---- ۷. پازل نوآوری ----
        elif current == "puzzle":
            async def on_puzzle_complete(result: dict):
                play_toast_sfx()
                for ev in result["evidence_items"]:
                    await _io(
                        log_evidence_web,
                        participant_id=participant_id,
                        scenario_id=scenario_id,
                        competency="problem_solving",
                        evidence_key=ev["key"],
                        evidence_value=ev["value"],
                        weight=ev["weight"],
                    )
                await _io(
                    log_event_threadsafe,
                    participant_id=participant_id,
                    session_id=session_id,
                    event_type='puzzle_completed',
                    scenario_id=scenario_id,
                    metadata=result,
                )
                print("=" * 60)
                print("[CFI-01] نتیجه:")
                print(f"  solved: {result['solved']}")
                print(
                    f"  total_attempts: "
                    f"{result['total_attempts']}"
                )
                print(
                    f"  unique_attempts: "
                    f"{result['unique_attempts']}"
                )
                print(
                    f"  old_solution_attempts: "
                    f"{result['old_solution_attempts']}"
                )
                print(
                    f"  solution_time_ms: "
                    f"{result['solution_time_ms']}"
                )
                for ev in result["evidence_items"]:
                    print(
                        f"  {ev['key']}: {ev['value']} "
                        f"(w={ev['weight']})"
                    )
                print("=" * 60)

                state["_puzzle_result"] = result
                state["state"] = "result_dialogue"
                state["result_index"] = 0
                _save_state(
                    phase_key, participant_id, state
                )
                await _re_render()

            from web_app.components.puzzle import (
                render_puzzle,
            )
            await render_puzzle(scenario, on_puzzle_complete)

        # ---- ۸. کار تکراری ----
        elif current == "repetitive":
            async def on_repetitive_complete(result: dict):
                play_toast_sfx()
                for ev in result["evidence_items"]:
                    await _io(
                        log_evidence_web,
                        participant_id=participant_id,
                        scenario_id=scenario_id,
                        competency="accountability",
                        evidence_key=ev["key"],
                        evidence_value=ev["value"],
                        weight=ev["weight"],
                    )
                await _io(
                    log_event_threadsafe,
                    participant_id=participant_id,
                    session_id=session_id,
                    event_type='repetitive_task_completed',
                    scenario_id=scenario_id,
                    metadata=result,
                )
                print("=" * 60)
                print("[TC-01] نتیجه:")
                print(
                    f"  completion_rate: "
                    f"{result['completion_rate']}"
                )
                print(
                    f"  cheat_used: {result['cheat_used']}"
                )
                print(
                    f"  rejected_temptation: "
                    f"{result['rejected_temptation']}"
                )
                for ev in result["evidence_items"]:
                    print(
                        f"  {ev['key']}: {ev['value']} "
                        f"(w={ev['weight']})"
                    )
                print("=" * 60)

                state["_repetitive_result"] = result
                state["state"] = "result_dialogue"
                state["result_index"] = 0
                _save_state(
                    phase_key, participant_id, state
                )
                await _re_render()

            from web_app.components.repetitive_task import (
                render_repetitive_task,
            )
            await render_repetitive_task(
                scenario, on_repetitive_complete
            )

        # ---- ۹. شورا ----
        elif current == "accountability":
            async def on_accountability_complete(
                result: dict
            ):
                play_toast_sfx()
                for ev in result["evidence_items"]:
                    await _io(
                        log_evidence_web,
                        participant_id=participant_id,
                        scenario_id=scenario_id,
                        competency="accountability",
                        evidence_key=ev["key"],
                        evidence_value=ev["value"],
                        weight=ev["weight"],
                    )
                await _io(
                    log_event_threadsafe,
                    participant_id=participant_id,
                    session_id=session_id,
                    event_type='accountability_completed',
                    scenario_id=scenario_id,
                    metadata=result,
                )
                print("=" * 60)
                print("[AC-01] نتیجه:")
                for r in result["rounds"]:
                    print(
                        f"  دور {r['round_index'] + 1}: "
                        f"فشار={r['pressure']}، "
                        f"انتخاب={r['choice_id']}"
                    )
                for ev in result["evidence_items"]:
                    print(
                        f"  {ev['key']}: {ev['value']} "
                        f"(w={ev['weight']})"
                    )
                print("=" * 60)

                # ✅ ثبت schema برای هر دور از شورا (MRL)
                rounds_result = result.get("rounds", [])
                scenario_rounds = scenario.get("rounds", [])
                for r in rounds_result:
                    r_idx = int(r.get("round_index", -1))
                    r_cid = int(r.get("choice_id", 0))
                    if 0 <= r_idx < len(scenario_rounds):
                        round_choices = (
                            scenario_rounds[r_idx]
                            .get("choices", [])
                        )
                        for c in round_choices:
                            if int(c.get("id", 0)) != r_cid:
                                continue
                            sch = c.get("schema")
                            if (
                                isinstance(sch, dict)
                                and sch.get("primary") in (
                                    "personal_interest",
                                    "maintaining_norms",
                                    "postconventional",
                                )
                            ):
                                await _io(
                                    log_schema_evidence,
                                    participant_id=participant_id,
                                    scenario_id=scenario_id,
                                    choice_id=r_cid,
                                    schema_primary=sch["primary"],
                                    schema_secondary=(
                                        sch.get("secondary") or ""
                                    ),
                                    reaction_time_ms=int(
                                        r.get(
                                            "decision_time_ms", 0
                                        )
                                    ),
                                )
                            break

                state["_accountability_result"] = result
                result_dialogues = _get_result_dialogues(
                    scenario, state
                )
                if result_dialogues:
                    state["state"] = "result_dialogue"
                    state["result_index"] = 0
                else:
                    print(
                        "   [AC-01] بدون دیالوگ نتیجه "
                        "— پرش به سناریوی بعد"
                    )
                    _advance_to_next_scenario(state)
                _save_state(
                    phase_key, participant_id, state
                )
                await _re_render()

            from web_app.components.accountability_dialog import (
                render_accountability_dialog,
            )
            await render_accountability_dialog(
                scenario, on_accountability_complete
            )

        # ---- ۱۰. انتخاب ----
        elif current == "choice":
            _choices = scenario.get("choices", [])
            if not _choices:
                print(f"   ⚠️ {scenario_id}: بدون گزینه — پرش")
                _advance_to_next_scenario(state)
                _save_state(phase_key, participant_id, state)
                await _re_render()
                return

            if "_choice_start_time" not in state:
                state["_choice_start_time"] = time.time()
                _save_state(phase_key, participant_id, state)

            ui.label('تصمیم بگیرید:').classes(
                'text-base text-gray-400 w-full text-right'
            )

            # ✅ shuffle پایدار در app.storage.user
            import random as _random
            _shuffle_key = f"_shuffle_{phase_key}_{scenario_id}"
            _saved_order = app.storage.user.get(_shuffle_key)

            if (
                not _saved_order
                or not isinstance(_saved_order, list)
                or len(_saved_order) != len(_choices)
            ):
                _order_ids = [c.get("id", 0) for c in _choices]
                _random.shuffle(_order_ids)
                app.storage.user[_shuffle_key] = _order_ids
                _saved_order = _order_ids

            _choice_map = {c.get("id", 0): c for c in _choices}
            _ordered = [
                _choice_map[cid] for cid in _saved_order
                if cid in _choice_map
            ]

            for c in _ordered:
                c_text = c.get("text_fa", "")
                thought = c.get("thought", "")

                def _make_handler(ch=c):
                    async def _h():
                        await handle_choice_picked(ch)
                    return _h

                with ui.card().classes(
                    'w-full bg-slate-700 hover:bg-slate-600 '
                    'border border-slate-500 '
                    'cursor-pointer p-4 mt-2'
                ).on('click', _make_handler()):
                    if thought:
                        with ui.element('div').classes(
                            'w-full p-2 mb-2 rounded'
                        ).style(
                            'background-color: rgba(79, 195, 247, 0.08); '
                            'border-right: 3px solid #4FC3F7;'
                        ):
                            ui.label(f'💭 {thought}').classes(
                                'text-sm text-gray-400 italic '
                                'w-full text-right leading-relaxed'
                            )
                    ui.label(c_text).classes(
                        'text-base text-white '
                        'w-full text-right leading-relaxed'
                    )

        # ---- ۱۱. دیالوگ نتیجه ----
        elif current == "result_dialogue":
            result_dialogues = _get_result_dialogues(
                scenario, state
            )
            idx = state["result_index"]
            if idx < len(result_dialogues):
                d = result_dialogues[idx]
                _speaker = str(d.get('speaker', '') or '')
                _text = str(d.get('text_fa', '') or '')

                # ✅ جایگزینی placeholder ها با مقادیر واقعی
                data = {}
                if "calibration_result" in state:
                    cal = state["calibration_result"]
                    if "total_count" in cal and "in_zone_count" in cal:
                        cal["out_zone_count"] = cal["total_count"] - cal["in_zone_count"]
                    data.update(cal)
                if state.get("_current_root_cause"):
                    data["chosen_root_cause"] = state["_current_root_cause"]
                for k, v in data.items():
                    _text = _text.replace("{" + k + "}", str(v))

                # ✅ حل پرتره
                from web_app.character_utils import (
                    resolve_portrait_url,
                )
                _portrait = resolve_portrait_url(
                    _speaker, _text, d.get('emotion')
                )

                with ui.card().classes(
                    'w-full bg-slate-800 border-2 '
                    'border-cyan-400 p-4'
                ):
                    with ui.row().classes(
                        'items-start gap-4 w-full no-wrap'
                    ):
                        # ✅ پرتره (سمت راست در RTL)
                        if _portrait:
                            with ui.element('div').classes(
                                'flex-shrink-0'
                            ):
                                ui.image(_portrait).style(
                                    'width: 100px; '
                                    'height: 130px; '
                                    'border-radius: 10px; '
                                    'border: 2px solid #4FC3F7; '
                                    'object-fit: cover; '
                                    'background: #0B1D3A;'
                                )

                        # ✅ محتوا
                        with ui.column().classes(
                            'flex-1 gap-2'
                        ):
                            ui.label(
                                f"[{_speaker}]"
                            ).classes(
                                'text-sm text-cyan-400 '
                                'font-bold w-full text-right'
                            )
                            ui.label(_text).classes(
                                'text-base text-white '
                                'leading-relaxed w-full '
                                'text-right '
                                'whitespace-pre-line'
                            )

                ui.button(
                    'ادامه', on_click=handle_next_result,
                ).classes(
                    'w-full py-3 text-lg font-bold '
                    'bg-cyan-600 hover:bg-cyan-500 mt-4'
                )

    await _re_render()


# ============================================================
# سازگاری با کد قبلی
# ============================================================
async def render_phase1(
    participant_id: str, session_id: str, on_complete
):
    from web_app.config import PHASE_SCENARIOS, PHASE_TITLES
    await render_phase(
        phase_key="phase1",
        scenarios_order=PHASE_SCENARIOS["phase1"],
        phase_title=PHASE_TITLES["phase1"],
        participant_id=participant_id,
        session_id=session_id,
        on_complete=on_complete,
    )