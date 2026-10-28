"""
مکانیک پازل نوآوری (CFI-01) — نسخه‌ی وب
==========================================
بازیکن با کلیک روی دو آیتم، آن‌ها را ترکیب می‌کند.
فقط ترکیب (paint + circuit) معتبر است.
"""
import time
import asyncio
from nicegui import ui, app

from web_app.config import TEST_MODE


PUZZLE_CSS_HTML = """
<style>
.puzzle-card {
    transition: transform 0.15s, border-color 0.15s,
                background-color 0.15s, box-shadow 0.15s;
    cursor: pointer;
    user-select: none;
}
.puzzle-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(79, 195, 247, 0.3);
}
.puzzle-card.selected {
    border-color: #4CAF50 !important;
    background-color: rgba(76, 175, 80, 0.15) !important;
    box-shadow: 0 4px 15px rgba(76, 175, 80, 0.5);
}
</style>
"""


def _canonical_pair(a: str, b: str) -> tuple:
    """جفت مرتب‌شده برای مقایسه"""
    return (a, b) if a < b else (b, a)


def _calc_cfi01_evidence(result: dict) -> list:
    """محاسبه‌ی شواهد CFI-01 بر اساس نتیجه."""
    total_attempts = result.get("total_attempts", 0)
    unique_attempts = result.get("unique_attempts", 0)
    old_attempts = result.get("old_solution_attempts", 0)
    sol_time = result.get("solution_time_ms", 0)
    solved = result.get("solved", False)

    # E_CFI1_old_attempts — پرهیز از تکرار راه‌حل‌های شکست‌خورده
    old_score = max(0.0, 1.0 - (old_attempts * 0.15))

    # E_CFI1_unique_combinations — ترکیبات بدیع
    # اگر با یک بار تلاش فوری حل کرد → حدس زده، امتیاز کم
    is_guessing = (total_attempts == 1 and sol_time < 10000)
    if is_guessing:
        unique_score = 0.15
    else:
        unique_score = min(1.0, unique_attempts * 0.15)

    # E_CFI1_solution_time
    if not solved:
        time_score = 0.1
    elif sol_time <= 15000:
        time_score = 0.7
    elif sol_time <= 60000:
        time_score = 1.0
    elif sol_time <= 120000:
        time_score = 0.6
    else:
        time_score = 0.3

    return [
        {
            "key": "E_CFI1_old_attempts",
            "value": round(old_score, 3),
            "weight": 0.30,
            "description": "پرهیز از تکرار راه‌حل‌های شکست‌خورده",
        },
        {
            "key": "E_CFI1_unique_combinations",
            "value": round(unique_score, 3),
            "weight": 0.35,
            "description": "تعداد ترکیبات بدیع آزمون‌شده",
        },
        {
            "key": "E_CFI1_solution_time",
            "value": round(time_score, 3),
            "weight": 0.35,
            "description": "زمان تا رسیدن به راه‌حل نوآورانه",
        },
    ]


async def render_puzzle(scenario: dict, on_complete):
    """رندر مکانیک پازل."""
    cfg = scenario.get("puzzle_config", {})
    items = cfg.get("items", [])
    valid_combos = cfg.get("valid_combinations", [])
    hint = cfg.get("solution_hint", "")
    goal = cfg.get("goal", "")

    valid_pairs = {
        _canonical_pair(p[0], p[1])
        for p in valid_combos if len(p) == 2
    }

    state = {
        "selected": None,
        "attempted_combinations": [],
        "start_time": time.time(),
        "solved": False,
        "hint_shown": False,
        "submitted": False,
    }

    item_map = {item["id"]: item for item in items}
    card_refs: dict = {}

    # ---- عنوان و هدف ----
    ui.label("🔓 در قفل‌شده").classes(
        'text-xl font-bold text-cyan-400 w-full text-right'
    )
    if goal:
        ui.label(f"🎯 هدف: {goal}").classes(
            'text-sm text-orange-400 w-full text-right mb-2'
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
            "• با کلیک روی دو آیتم، آن‌ها را ترکیب کن."
        ).classes('text-xs text-gray-300 w-full text-right')
        ui.label(
            "• فقط یک ترکیب معتبر است که در را باز می‌کند."
        ).classes('text-xs text-gray-300 w-full text-right')

    # ---- نوار وضعیت ----
    status_label = ui.label(
        "دو آیتم را برای ترکیب انتخاب کن."
    ).classes(
        'text-base text-cyan-300 w-full text-right '
        'bg-slate-800 p-3 rounded mt-2'
    )

    # ---- آیتم‌ها در گرید 2x2 ----
    # ✅ shuffle پایدار
    import random as _random
    _saved_order = app.storage.user.get("_puzzle_order")
    if (
        not _saved_order
        or not isinstance(_saved_order, list)
        or len(_saved_order) != len(items)
    ):
        _order_ids = [item["id"] for item in items]
        _random.shuffle(_order_ids)
        app.storage.user["_puzzle_order"] = _order_ids
        _saved_order = _order_ids

    _item_map = {item["id"]: item for item in items}
    _ordered_items = [
        _item_map[iid] for iid in _saved_order
        if iid in _item_map
    ]
    with ui.grid(columns=2).classes('w-full gap-3 mt-2'):
        for item in items:
            card = ui.card().classes(
                "puzzle-card bg-slate-800 border-2 "
                "border-slate-600 p-4"
            )
            card_refs[item["id"]] = card
            with card:
                with ui.row().classes(
                    'items-center gap-3 no-wrap w-full'
                ):
                    ui.label(item.get("icon", "📦")).classes(
                        'text-3xl flex-shrink-0'
                    )
                    with ui.column().classes('gap-1 flex-1'):
                        ui.label(
                            item.get("name", item["id"])
                        ).classes(
                            'text-sm text-white font-bold '
                            'w-full text-right'
                        )
                        if item.get("brief"):
                            ui.label(
                                item["brief"]
                            ).classes(
                                'text-xs text-gray-400 '
                                'w-full text-right'
                            )

    # ---- راهنمایی (پنهان) ----
    hint_btn = ui.button("🔍 راهنمایی").classes(
        'w-full bg-yellow-700 hover:bg-yellow-600 '
        'text-sm font-bold py-2 mt-3 rounded-lg'
    )
    hint_btn.set_visibility(False)

    hint_label = ui.label("").classes(
        'w-full text-sm text-yellow-300 italic '
        'bg-yellow-900/30 p-3 rounded mt-2'
    )
    hint_label.set_visibility(False)

    def _show_hint():
        if state["hint_shown"]:
            return
        state["hint_shown"] = True
        hint_label.set_text(f"💡 {hint}")
        hint_label.set_visibility(True)
        hint_btn.set_visibility(False)

    hint_btn.on_click(_show_hint)

    # ---- منطق کلیک ----
    async def _on_item_click(item_id: str):
        if state["solved"]:
            return

        # همان آیتم → لغو انتخاب
        if state["selected"] == item_id:
            state["selected"] = None
            card_refs[item_id].classes(remove="selected")
            status_label.set_text("انتخاب لغو شد.")
            return

        # آیتم اول
        if state["selected"] is None:
            state["selected"] = item_id
            card_refs[item_id].classes(add="selected")
            status_label.set_text(
                f"«{item_map[item_id]['name']}» انتخاب شد. "
                f"حالا آیتم دوم را انتخاب کن."
            )
            return

        # آیتم دوم — ترکیب
        first = state["selected"]
        second = item_id
        pair = _canonical_pair(first, second)

        state["attempted_combinations"].append(pair)
        card_refs[first].classes(remove="selected")
        card_refs[second].classes(remove="selected")
        state["selected"] = None

        if pair in valid_pairs:
            # ✅ موفق
            state["solved"] = True
            status_label.set_text("✅ ترکیب معتبر! در باز شد.")
            status_label.style("color: #4CAF50;")
            await asyncio.sleep(0.8)
            await _finalize()
        else:
            # ❌ ناموفق
            n = len(state["attempted_combinations"])
            ui.notify(
                f"❌ این ترکیب کار نکرد. ({n} تلاش)",
                type='negative', position='top', timeout=2000,
            )
            status_label.set_text(
                f"❌ این ترکیب کار نکرد. ({n} تلاش)"
            )
            status_label.style("color: #FF8F00;")

            # نمایش دکمه‌ی راهنمایی بعد از ۴ شکست
            if n >= 4 and not state["hint_shown"]:
                hint_btn.set_visibility(True)

    # اتصال کلیک به همه‌ی کارت‌ها
    for item in items:
        iid = item["id"]

        def _make_handler(item_id=iid):
            async def _h(e=None):
                await _on_item_click(item_id)
            return _h

        card_refs[iid].on('click', _make_handler())

    # ---- نهایی‌سازی ----
    async def _finalize():
        if state["submitted"]:
            return
        state["submitted"] = True

        total_attempts = len(state["attempted_combinations"])
        unique_attempts = len(set(state["attempted_combinations"]))
        sol_time = int(
            (time.time() - state["start_time"]) * 1000
        )

        # تعداد تلاش‌های شکست‌خورده
        if state["solved"]:
            old_solution_attempts = max(0, total_attempts - 1)
        else:
            old_solution_attempts = total_attempts

        result = {
            "solved": state["solved"],
            "attempted_combinations": [
                list(p) for p in state["attempted_combinations"]
            ],
            "total_attempts": total_attempts,
            "unique_attempts": unique_attempts,
            "old_solution_attempts": old_solution_attempts,
            "solution_time_ms": sol_time,
            "hint_shown": state["hint_shown"],
        }
        result["evidence_items"] = _calc_cfi01_evidence(result)

        if on_complete:
            await on_complete(result)

