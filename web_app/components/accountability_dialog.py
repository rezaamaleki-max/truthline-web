"""
مکانیک بازخواست شورا (AC-01) — نسخه‌ی وب
==========================================
تغییرات نسخه 2.0:
- ✅ تحلیل‌گر گفتار (به‌جای تاس)
- ✅ توزیع منصفانه فشار: هر بازیکن دقیقاً یک بار فشار ۱، ۲، ۳
   (فقط ترتیب توزیع بین اعضا تصادفی است — random.sample)
- ✅ پرتره‌ی اعضای شورا در همه‌ی مراحل
- ✅ نمایش توجیه منطقی (در حالت inner)
- ✅ نوار پیشرفت
- ✅ انیمیشن ورود کارت عضو

نسخه: 2.0.0
"""
import asyncio
import random
import re
import time
from nicegui import ui, app

from web_app.config import TEST_MODE
from web_app.character_utils import resolve_portrait_url


ACCOUNTABILITY_CSS_HTML = """
<style>
.council-member {
    background: linear-gradient(135deg,
        rgba(26, 42, 74, 0.9),
        rgba(11, 29, 58, 0.9));
    border: 2px solid #4FC3F7;
    border-radius: 12px;
}
.council-choice {
    transition: all 0.15s;
    cursor: pointer;
}
.council-choice:hover {
    background-color: #2B4A6F !important;
    border-color: #FFFFFF !important;
}
.pressure-segment {
    height: 18px;
    border-radius: 4px;
    background-color: #1A2A4A;
    border: 1px solid #444444;
    transition: all 0.3s ease;
    flex: 1;
}
.pressure-segment.rolling {
    background-color: #2B4A6F !important;
    border-color: #4FC3F7 !important;
    animation: pulse-segment 0.6s ease-in-out infinite;
}
@keyframes pulse-segment {
    0%, 100% { opacity: 0.5; }
    50% { opacity: 1; }
}
.pressure-segment.level-1 {
    background-color: #4FC3F7 !important;
    border-color: #4FC3F7 !important;
}
.pressure-segment.level-2 {
    background-color: #FF8F00 !important;
    border-color: #FF8F00 !important;
}
.pressure-segment.level-3 {
    background-color: #D32F2F !important;
    border-color: #D32F2F !important;
}
@keyframes member-fade-in {
    from { opacity: 0; transform: translateX(30px); }
    to { opacity: 1; transform: translateX(0); }
}
.member-card-animated {
    animation: member-fade-in 0.32s ease-out;
}
.thought-bubble {
    background-color: rgba(79, 195, 247, 0.08);
    border-right: 3px solid #4FC3F7;
    border-radius: 6px;
    padding: 6px 10px;
    margin-bottom: 8px;
}
</style>
"""


# ============================================================
# متادیتای سطح فشار
# ============================================================
PRESSURE_META = {
    1: {
        "label": "کم",
        "color": "#4FC3F7",
        "icon": "🌤",
        "desc": "شورا عمدتاً توضیح می‌خواهد",
    },
    2: {
        "label": "متوسط",
        "color": "#FF8F00",
        "icon": "⛅",
        "desc": "شورا شروع به انتقاد می‌کند",
    },
    3: {
        "label": "زیاد",
        "color": "#D32F2F",
        "icon": "⛈",
        "desc": "شورا خشمگین است و بازخواست شدید می‌کند",
    },
}


# ============================================================
# واکنش‌های خنثی (fallback)
# ============================================================
NEUTRAL_REACTIONS = {
    "member_1": (
        "دکتر فربد مهرانی",
        "(نگاهی به پرونده می‌اندازد و در آن یادداشتی می‌نویسد.)",
    ),
    "member_2": (
        "خانم سارا آذری",
        "(سرش را آرام تکان می‌دهد و به صفحه نگاه می‌کند.)",
    ),
    "member_3": (
        "جناب آقای پرویز کیانی",
        "(در پرونده‌ای که مقابلش است، خطی می‌کشد.)",
    ),
}


# ============================================================
# جدا کردن توجیه منطقی از متن
# ============================================================
_THOUGHT_PATTERN = re.compile(
    r"\n\n\(توجیه منطقی:\s*(.+?)\)\s*$",
    re.DOTALL,
)


def _split_thought(text: str) -> tuple[str, str]:
    """جدا کردن (متن اصلی، توجیه) از متن choice."""
    if not text:
        return text, ""
    m = _THOUGHT_PATTERN.search(text)
    if m:
        thought = m.group(1).strip()
        clean = _THOUGHT_PATTERN.sub("", text).strip()
        return clean, thought
    return text, ""


# ============================================================
# امتیازدهی
# ============================================================
def _score_acceptance(choice_id, pressure):
    base = 1.0 if choice_id == 1 else (
        0.5 if choice_id == 2 else 0.0
    )
    if pressure == 3:
        if choice_id == 1:
            return 1.0
        if choice_id == 2:
            return 0.6
    elif pressure == 1:
        if choice_id == 1:
            return 0.9
    return base


def _score_honesty(choice_id, pressure):
    base = 1.0 if choice_id == 1 else (
        0.3 if choice_id == 2 else 0.0
    )
    if pressure == 3:
        if choice_id == 1:
            return 1.0
        if choice_id == 2:
            return 0.4
    elif pressure == 1:
        if choice_id == 1:
            return 0.9
    return base


def _score_recovery(choice_id, pressure):
    return 1.0 if choice_id == 1 else (
        0.3 if choice_id == 2 else 0.0
    )


def _calc_evidence(rounds_data):
    """محاسبه‌ی ۴ شاهد AC-01."""
    if len(rounds_data) < 3:
        return []

    r1 = rounds_data[0]
    r2 = rounds_data[1]
    r3 = rounds_data[2]

    v1 = _score_acceptance(r1["choice_id"], r1["pressure"])
    v2 = _score_honesty(r2["choice_id"], r2["pressure"])
    v3 = _score_recovery(r3["choice_id"], r3["pressure"])

    avg_time = sum(
        r["decision_time_ms"] for r in rounds_data
    ) / len(rounds_data)
    v4 = max(0.0, 1.0 - avg_time / 60000.0)

    return [
        {
            "key": "E_AC1_acceptance",
            "value": round(v1, 3),
            "weight": 0.35,
            "description": "پذیرش مسئولیت",
        },
        {
            "key": "E_AC2_honesty_under_pressure",
            "value": round(v2, 3),
            "weight": 0.30,
            "description": "صداقت تحت فشار",
        },
        {
            "key": "E_AC3_recovery_plan",
            "value": round(v3, 3),
            "weight": 0.20,
            "description": "پیشنهاد جبران",
        },
        {
            "key": "E_AC4_decision_time",
            "value": round(v4, 3),
            "weight": 0.15,
            "description": "زمان تصمیم",
        },
    ]


# ============================================================
# تابع اصلی
# ============================================================
async def render_accountability_dialog(scenario, on_complete):
    rounds_spec = scenario.get("rounds", [])
    analyzer_cfg = scenario.get("analyzer_config", {})
    button_label = analyzer_cfg.get(
        "button_label", "شروع بازخواست"
    )
    delay_ms = analyzer_cfg.get("activation_delay_ms", 1500)

    # ✅ توزیع منصفانه: هر بازیکن دقیقاً یک بار فشار ۱، ۲، ۳
    pressure_plan = random.sample([1, 2, 3], 3)
    print(f"   [COUNCIL] pressure plan: {pressure_plan}")

    state = {
        "round_idx": 0,
        "rounds_data": [],
        "current_pressure": 0,
        "round_start_time": 0.0,
        "submitted": False,
    }

    container = ui.column().classes('w-full gap-4')

    # ----------------------------------------------------------
    def _portrait_url(member_name: str):
        return resolve_portrait_url(
            member_name, "", "neutral"
        )

    # ============================================================
    # مرحله ۱: تحلیل‌گر آماده
    # ============================================================
    async def _show_analyzer_ready():
        idx = state["round_idx"]
        if idx >= len(rounds_spec):
            await _finalize()
            return

        round_spec = rounds_spec[idx]
        member_name = round_spec.get("member_name", "—")
        member_role = round_spec.get("member_role", "")
        member_icon = round_spec.get("member_icon", "👤")
        portrait_url = _portrait_url(member_name)

        container.clear()
        with container:
            # هدر
            ui.label("⚖️ شورای عالی ایستگاه").classes(
                'text-xl font-bold text-cyan-400 '
                'w-full text-right'
            )
            ui.label(
                f"دور {idx + 1} از {len(rounds_spec)}"
            ).classes(
                'text-sm text-orange-400 font-bold '
                'w-full text-right'
            )

            # نوار پیشرفت
            ui.linear_progress(
                value=idx / len(rounds_spec),
                show_value=False,
            ).classes('w-full mt-1 mb-2')

            # کارت عضو با پرتره
            with ui.element('div').classes(
                'council-member member-card-animated '
                'w-full p-4 mt-1'
            ):
                with ui.row().classes(
                    'items-center gap-4 no-wrap w-full'
                ):
                    if portrait_url:
                        with ui.element('div').classes(
                            'flex-shrink-0'
                        ):
                            ui.image(portrait_url).style(
                                'width: 80px; height: 110px; '
                                'border-radius: 10px; '
                                'border: 2px solid #4FC3F7; '
                                'object-fit: cover; '
                                'background: #0B1D3A;'
                            )
                    else:
                        ui.label(member_icon).classes(
                            'text-4xl flex-shrink-0'
                        )

                    with ui.column().classes(
                        'gap-1 flex-1'
                    ):
                        ui.label(member_name).classes(
                            'text-lg font-bold text-white '
                            'w-full text-right'
                        )
                        ui.label(member_role).classes(
                            'text-xs text-gray-400 '
                            'w-full text-right'
                        )

            # پنل تحلیل‌گر
            with ui.card().classes(
                'w-full bg-slate-900 border-2 '
                'border-cyan-400 p-4 mt-2'
            ):
                with ui.row().classes(
                    'items-center gap-2 w-full '
                    'mb-2 no-wrap'
                ):
                    ui.label("🎯").classes(
                        'text-2xl flex-shrink-0'
                    )
                    ui.label("تحلیل‌گر گفتار").classes(
                        'text-base font-bold text-cyan-300 '
                        'flex-1 text-right'
                    )
                    status_label = ui.label(
                        "آماده"
                    ).classes(
                        'text-xs text-gray-400 font-bold'
                    )

                # ۳ بخش فشار
                with ui.row().classes(
                    'gap-2 w-full mt-2 no-wrap'
                ):
                    segments: list = []
                    for _ in range(3):
                        seg = ui.element('div').classes(
                            'pressure-segment'
                        )
                        segments.append(seg)

                ui.label(
                    "برای شروع، دکمه‌ی زیر را بزن. "
                    "تحلیل‌گر شواهد گفتاری را می‌سنجد و "
                    "سطح فشار شورا را مشخص می‌کند."
                ).classes(
                    'text-xs text-gray-400 w-full '
                    'text-right mt-3 italic'
                )

            async def _activate():
                await _run_analysis(
                    idx, round_spec,
                    segments, status_label,
                )

            ui.button(
                button_label, on_click=_activate,
            ).classes(
                'w-full py-4 text-lg font-bold '
                'bg-purple-600 hover:bg-purple-500 mt-2'
            )

    # ============================================================
    # مرحله ۲: در حال تحلیل
    # ============================================================
    async def _run_analysis(idx, round_spec,
                             segments, status_label):
        for seg in segments:
            seg.classes(add='rolling')
        status_label.set_text("⏳ در حال تحلیل...")
        status_label.style("color: #FF8F00;")

        await asyncio.sleep(delay_ms / 1000.0)

        # صدای اعلام فشار
        try:
            from web_app.audio import play_scan_sfx
            play_scan_sfx()
        except Exception:
            pass

        # ✅ فشار از پیش‌تعیین‌شده (منصفانه)
        pressure = pressure_plan[idx]
        state["current_pressure"] = pressure
        state["round_start_time"] = time.time()

        for seg in segments:
            seg.classes(remove='rolling')
        for i, seg in enumerate(segments):
            if i < pressure:
                seg.classes(add=f'level-{pressure}')

        meta = PRESSURE_META[pressure]
        status_label.set_text(
            f"{meta['icon']} فشار {meta['label']}"
        )
        status_label.style(f"color: {meta['color']};")

        await asyncio.sleep(0.8)
        await _show_question(idx, round_spec, pressure)

    # ============================================================
    # مرحله ۳: نمایش سؤال
    # ============================================================
    async def _show_question(idx, round_spec, pressure):
        member_name = round_spec.get("member_name", "—")
        member_role = round_spec.get("member_role", "")
        member_icon = round_spec.get("member_icon", "👤")
        portrait_url = _portrait_url(member_name)
        meta = PRESSURE_META[pressure]

        question_map = round_spec.get(
            "question_by_pressure", {}
        )
        question = question_map.get(
            str(pressure),
            question_map.get(pressure, "—"),
        )

        container.clear()
        with container:
            ui.label("⚖️ شورای عالی ایستگاه").classes(
                'text-xl font-bold text-cyan-400 '
                'w-full text-right'
            )
            ui.label(
                f"دور {idx + 1} از {len(rounds_spec)}"
            ).classes(
                'text-sm text-orange-400 font-bold '
                'w-full text-right'
            )

            # کارت عضو
            with ui.element('div').classes(
                'council-member w-full p-3 mt-1'
            ):
                with ui.row().classes(
                    'items-center gap-3 no-wrap w-full'
                ):
                    if portrait_url:
                        with ui.element('div').classes(
                            'flex-shrink-0'
                        ):
                            ui.image(portrait_url).style(
                                'width: 60px; height: 80px; '
                                'border-radius: 8px; '
                                'border: 2px solid '
                                f'{meta["color"]}; '
                                'object-fit: cover; '
                                'background: #0B1D3A;'
                            )
                    else:
                        ui.label(member_icon).classes(
                            'text-3xl flex-shrink-0'
                        )
                    with ui.column().classes(
                        'gap-1 flex-1'
                    ):
                        ui.label(member_name).classes(
                            'text-base font-bold text-white '
                            'w-full text-right'
                        )
                        ui.label(member_role).classes(
                            'text-xs text-gray-400 '
                            'w-full text-right'
                        )

            # بج فشار
            with ui.row().classes(
                'items-center gap-2 w-full mt-2'
            ):
                ui.label(
                    f"{meta['icon']}  سطح فشار:"
                ).classes('text-sm text-white')
                ui.label(meta["label"]).classes(
                    'text-sm font-bold px-3 py-1 rounded'
                ).style(
                    f"color: {meta['color']}; "
                    f"background-color: {meta['color']}20;"
                )

            # سؤال
            with ui.card().classes(
                'w-full bg-slate-800 border-2 '
                'border-cyan-400 p-4 mt-2'
            ):
                ui.label(question).classes(
                    'text-base text-white leading-relaxed '
                    'w-full text-right'
                )

            ui.label("پاسخ شما:").classes(
                'text-sm text-gray-400 w-full '
                'text-right mt-3'
            )

            # گزینه‌ها
            import random as _random
            choices = round_spec.get("choices", [])
            member_id = round_spec.get("member_id", "")
            _shuffle_key = (
                f"_ac_shuffle_{member_id}_{idx}"
            )
            _saved_order = app.storage.user.get(_shuffle_key)

            if (
                not _saved_order
                or not isinstance(_saved_order, list)
                or len(_saved_order) != len(choices)
            ):
                _order_ids = [c.get("id", 0) for c in choices]
                _random.shuffle(_order_ids)
                app.storage.user[_shuffle_key] = _order_ids
                _saved_order = _order_ids

            _choice_map = {c.get("id", 0): c for c in choices}
            _ordered = [
                _choice_map[cid] for cid in _saved_order
                if cid in _choice_map
            ]

            for choice in _ordered:
                raw = choice.get("text_fa", "")
                ctext, thought = _split_thought(raw)

                def _make_handler(ch=choice):
                    async def _h():
                        await _on_choice(ch)
                    return _h

                with ui.element('div').classes(
                    'council-choice w-full p-3 '
                    'bg-slate-800 border-2 border-cyan-400 '
                    'rounded-lg mt-2'
                ).on('click', _make_handler()):
                    if thought:
                        with ui.element('div').classes(
                            'thought-bubble w-full'
                        ):
                            ui.label(
                                f"💭  {thought}"
                            ).classes(
                                'text-xs text-gray-400 '
                                'italic leading-relaxed '
                                'w-full text-right'
                            )
                    ui.label(ctext).classes(
                        'text-sm text-white '
                        'w-full text-right leading-relaxed'
                    )

    # ============================================================
    # مرحله ۴: ثبت انتخاب + واکنش
    # ============================================================
    async def _on_choice(choice):
        idx = state["round_idx"]
        round_spec = rounds_spec[idx]
        pressure = state["current_pressure"]
        decision_time = int(
            (time.time() - state["round_start_time"]) * 1000
        )
        state["rounds_data"].append({
            "round_index": idx,
            "member_id": round_spec.get("member_id", ""),
            "pressure": pressure,
            "choice_id": choice.get("id", 0),
            "decision_time_ms": decision_time,
        })

        # ✅ صدای ثبت پاسخ در شورا (toast، نه choice)
        try:
            from web_app.audio import play_toast_sfx
            play_toast_sfx()
        except Exception:
            pass

        # واکنش
        member_id = round_spec.get("member_id", "")
        member_name = round_spec.get("member_name", "—")
        member_role = round_spec.get("member_role", "")
        portrait_url = _portrait_url(member_name)

        reactions_map = round_spec.get(
            "reactions_by_choice", {}
        ) or {}
        reactions = reactions_map.get(
            str(choice.get("id", 0)), []
        )

        if reactions:
            speakers = []
            texts = []
            for r in reactions:
                sp = r.get("speaker", "")
                if sp and sp not in speakers:
                    speakers.append(sp)
                texts.append(r.get("text_fa", ""))
            reaction_speaker = " / ".join(speakers)
            reaction_text = "\n\n".join(texts)
        else:
            sp, txt = NEUTRAL_REACTIONS.get(
                member_id,
                ("شورا",
                 "(سرش را تکان می‌دهد و به پرونده "
                 "نگاه می‌کند.)"),
            )
            reaction_speaker = sp
            reaction_text = txt

        container.clear()
        with container:
            ui.label("⚖️ شورای عالی ایستگاه").classes(
                'text-xl font-bold text-cyan-400 '
                'w-full text-right'
            )
            ui.label(
                f"دور {idx + 1} از {len(rounds_spec)}"
            ).classes(
                'text-sm text-orange-400 font-bold '
                'w-full text-right'
            )

            ui.label(
                "✓ پاسخ شما ثبت شد"
            ).classes(
                'text-base text-green-400 font-bold '
                'w-full text-center p-3 mt-2'
            )

            # واکنش با پرتره
            with ui.card().classes(
                'w-full bg-slate-800 border-2 '
                'border-cyan-400 p-4 mt-2'
            ):
                with ui.row().classes(
                    'items-start gap-3 no-wrap w-full'
                ):
                    if portrait_url:
                        with ui.element('div').classes(
                            'flex-shrink-0'
                        ):
                            ui.image(portrait_url).style(
                                'width: 70px; height: 90px; '
                                'border-radius: 8px; '
                                'border: 2px solid #4FC3F7; '
                                'object-fit: cover; '
                                'background: #0B1D3A;'
                            )
                    with ui.column().classes(
                        'gap-1 flex-1'
                    ):
                        ui.label(
                            f"[{reaction_speaker}]"
                        ).classes(
                            'text-sm text-cyan-400 font-bold '
                            'w-full text-right'
                        )
                        ui.label(reaction_text).classes(
                            'text-base text-gray-300 '
                            'leading-relaxed w-full text-right '
                            'whitespace-pre-line'
                        )

            # دکمه‌ی ادامه (با تأخیر ۶۰۰ms)
            async def _continue():
                if not refs.get("can_continue"):
                    return
                state["round_idx"] += 1
                await _show_analyzer_ready()

            refs: dict = {"can_continue": False}
            btn = ui.button(
                "ادامه", on_click=_continue,
            ).classes(
                'w-full py-3 text-lg font-bold '
                'bg-cyan-600 hover:bg-cyan-500 mt-3'
            )
            btn.disable()

            def _enable():
                try:
                    refs["can_continue"] = True
                    btn.enable()
                except Exception:
                    pass

            asyncio.get_event_loop().call_later(0.6, _enable)

    # ============================================================
    # نهایی‌سازی
    # ============================================================
    async def _finalize():
        if state["submitted"]:
            return
        state["submitted"] = True

        rounds_data = state["rounds_data"]
        evidence = _calc_evidence(rounds_data)
        total_time = sum(
            r["decision_time_ms"] for r in rounds_data
        )

        result = {
            "rounds": rounds_data,
            "total_time_ms": total_time,
            "evidence_items": evidence,
        }

        if on_complete:
            await on_complete(result)

    # ---- شروع ----
    await _show_analyzer_ready()

