"""صفحه‌ی نتایج نهایی با نمودار رادار"""
from typing import Any, Callable, TypeVar, cast

from nicegui import ui, app, run

from web_app.config import PAGE_CSS
from web_app.db_manager import (
    get_connection,
    get_relationships_web,
)
from web_app.components.audio_control import setup_page_audio

COMPETENCY_FA = {
    "honesty": "صداقت و یکپارچگی",
    "trustworthiness": "قابلیت اعتماد",
    "problem_solving": "حل مسئله",
    "accountability": "مسئولیت‌پذیری",
}
COMPETENCY_ORDER = list(COMPETENCY_FA.keys())


INTERPRETATIONS = {
    ("honesty", "high"):
        "پایبندی استثنایی به حقیقت و اصول اخلاقی، "
        "حتی تحت فشار.",
    ("honesty", "mid"):
        "صداقت شما موقعیت‌محور است و به شرایط "
        "وابسته می‌شود.",
    ("honesty", "low"):
        "منافع شخصی معمولاً بر ملاحظات اخلاقی اولویت "
        "می‌یابد.",
    ("trustworthiness", "high"):
        "به شکلی قابل اتکا به تعهدات و وعده‌های خود "
        "پایبندید.",
    ("trustworthiness", "mid"):
        "قابلیت اعتماد شما در شرایط عادی خوب است، اما "
        "در بحران نوسان دارد.",
    ("trustworthiness", "low"):
        "در حفظ تعهدات و شفافیت نیاز به تمرین و "
        "بازنگری دارید.",
    ("problem_solving", "high"):
        "تحلیل‌گر نظام‌مندی هستید که مسائل پیچیده را "
        "ریشه‌ای حل می‌کنید.",
    ("problem_solving", "mid"):
        "در حل مسائل توانمندید، اما در شرایط ابهام "
        "گاهی عجولانه عمل می‌کنید.",
    ("problem_solving", "low"):
        "در تشخیص ریشه مسائل و برنامه‌ریزی نظام‌مند "
        "نیاز به توسعه دارید.",
    ("accountability", "high"):
        "مسئولیت‌پذیری بالایی دارید و از اشتباهات خود "
        "درس می‌گیرید.",
    ("accountability", "mid"):
        "در پذیرش مسئولیت قابل اتکا هستید، اما از "
        "مواجهه با بازخورد تلخ دوری می‌کنید.",
    ("accountability", "low"):
        "در پاسخگویی و پذیرش پیامدها نیازمند تقویت "
        "هستید.",
}


def _level(score: float) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "mid"
    return "low"

# ============================================================
# محاسبه‌ی Consistency (CO-01، CO-02، CO-03)
# ============================================================
def _compute_pair_score(v1: float, v2: float) -> float:
    """فرمول ترکیبی ثبات + کیفیت اخلاقی."""
    similarity = 1.0 - abs(v1 - v2)
    quality = (v1 + v2) / 2.0
    return round(0.4 * similarity + 0.6 * quality, 3)


def _compute_and_save_consistency(participant_id: str):
    """
    محاسبه‌ی سه شاخص ثبات بین جفت‌سناریوها و ذخیره در web_evidence.
    (همان منطق دسکتاپ — CO-01، CO-02، CO-03)
    """
    from web_app.db_manager import get_connection

    try:
        conn = get_connection()
        c = conn.cursor()

        # اگر قبلاً محاسبه شده → پرش
        c.execute("""
            SELECT 1 FROM web_evidence
            WHERE participant_id = ? AND scenario_id = 'CO-computed'
              AND evidence_key = 'E_CO1_moral_consistency'
            LIMIT 1
        """, (participant_id,))
        if c.fetchone():
            print("   [CO] قبلاً محاسبه شده — پرش")
            conn.close()
            return

        def _read(sid: str, ev_key: str) -> float | None:
            c.execute("""
                SELECT evidence_value FROM web_evidence
                WHERE participant_id = ? AND scenario_id = ?
                  AND evidence_key = ?
                LIMIT 1
            """, (participant_id, sid, ev_key))
            row = c.fetchone()
            return float(row[0]) if row else None

        import time as _t
        now = _t.time()
        inserted = []

        # ---- CO-01: MC-01 vs MC-02 ----
        mc1 = _read("MC-01", "E_MC1_action_type")
        mc2 = _read("MC-02", "E_MC2_integrity")
        if mc1 is not None and mc2 is not None:
            co1 = _compute_pair_score(mc1, mc2)
            c.execute("""
                INSERT INTO web_evidence
                (participant_id, scenario_id, competency,
                 evidence_key, evidence_value, weight, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                participant_id, "CO-computed", "honesty",
                "E_CO1_moral_consistency", co1, 0.8, now,
            ))
            inserted.append(f"CO-01={co1:.3f}")

        # ---- CO-02: PI-01 vs RG-01 ----
        pi1 = _read("PI-01", "E_PI2_report_completeness")
        rg1 = _read("RG-01", "E_RG1_initial_tone")
        if pi1 is not None and rg1 is not None:
            co2 = _compute_pair_score(pi1, rg1)
            c.execute("""
                INSERT INTO web_evidence
                (participant_id, scenario_id, competency,
                 evidence_key, evidence_value, weight, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                participant_id, "CO-computed", "accountability",
                "E_CO2_accountability_consistency",
                co2, 0.8, now,
            ))
            inserted.append(f"CO-02={co2:.3f}")

        # ---- CO-03: CF-01 vs CF-02 ----
        cf1 = _read("CF-01", "E_CF1_delivery_success")
        cf2 = _read("CF-02", "E_CF2_quality")
        if cf1 is not None and cf2 is not None:
            co3 = _compute_pair_score(cf1, cf2)
            c.execute("""
                INSERT INTO web_evidence
                (participant_id, scenario_id, competency,
                 evidence_key, evidence_value, weight, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                participant_id, "CO-computed", "trustworthiness",
                "E_CO3_behavioral_consistency", co3, 0.8, now,
            ))
            inserted.append(f"CO-03={co3:.3f}")

        conn.commit()
        conn.close()

        if inserted:
            print(f"   [CO] ثبت شد: {', '.join(inserted)}")
        else:
            print("   [CO] داده‌ی کافی نبود — پرش")
    except Exception as e:
        print(f"   [CO] خطا: {e}")

# ============================================================
# زیرمؤلفه‌ها
# ============================================================
# نگاشت evidence_key → sub_competency
SUB_COMP_MAP = {
    # honesty
    "E_H1_transparency": "transparency",
    "E_H2_completeness": "transparency",
    "E_H3_pressure_resistance": "boundary_setting",
    "E_H4_decision_time": "transparency",
    "E_DA1_cheat_avoidance": "data_integrity",
    "E_DA2_refusal": "boundary_setting",
    "E_DA2_reporting": "boundary_setting",
    "E_MC1_action_type": "fair_judgment",
    "E_MC2_integrity": "moral_consistency",
    "E_MC2_pressure_resistance": "moral_consistency",
    "E_VH2_disclosure": "transparency",
    "E_F2_thorough_investigation": "fair_judgment",
    "E_F2_bias_resistance": "fair_judgment",
    "E_CO1_moral_consistency": "moral_consistency",
    # trustworthiness
    "E_CF1_delivery_success": "commitment_keeping",
    "E_CF2_quality": "autonomous_quality",
    "E_CF2_effort": "autonomous_quality",
    "E_TR1_disclosure_action": "responsible_disclosure",
    "E_TR2_disclosure_level": "responsible_disclosure",
    "E_BC1_decision": "resource_generosity",
    "E_BC2_sacrifice": "shared_responsibility",
    "E_CO3_behavioral_consistency": "commitment_keeping",
    # problem_solving
    "E_PID1_systems_sequence": "root_cause_analysis",
    "E_PID4_correct_root": "root_cause_analysis",
    "E_PID1_tools_usage": "pattern_recognition",
    "E_PID2_coverage": "pattern_recognition",
    "E_PID2_tool_usage": "pattern_recognition",
    "E_PID3_time_to_action": "root_cause_analysis",
    "E_SPA1_sequence_score": "sequence_planning",
    "E_SPA1_planning_time": "sequence_planning",
    "E_SPA1_efficiency": "sequence_planning",
    "E_SPA1_allocation_pattern": "resource_allocation",
    "E_SPA2_data_check": "resource_allocation",
    "E_SPA3_decision_time": "resource_allocation",
    "E_F1_fairness_under_pressure": "resource_allocation",
    "E_CFI1_unique_combinations": "creative_thinking",
    "E_CFI1_old_attempts": "creative_thinking",
    "E_CFI1_solution_time": "creative_thinking",
    "E_CFI2_perseveration": "adaptive_revision",
    "E_CFI2_exploration": "adaptive_revision",
    "E_MR1_adjustment": "adaptive_revision",
    # ToH (Tower of Hanoi)
    "E_TOH_efficiency": "sequence_planning",
    "E_TOH_invalid": "adaptive_revision",
    "E_TOH_planning_time": "sequence_planning",
    "E_TOH_solved": "sequence_planning",
    # accountability
    "E_PI1_reporting_delay": "hazard_reporting",
    "E_PI1_documentation": "hazard_reporting",
    "E_PI2_proposal": "proactive_improvement",
    "E_PI2_report_completeness": "hazard_reporting",
    "E_TC1_completion_rate": "resistance_to_temptation",
    "E_TC1_accuracy": "resistance_to_temptation",
    "E_TC1_rejected_temptation": "resistance_to_temptation",
    "E_TC2_action_taken": "task_persistence",
    "E_RG1_initial_tone": "feedback_acceptance",
    "E_RG2_attitude": "growth_mindset",
    "E_AC1_acceptance": "formal_accountability",
    "E_AC2_honesty_under_pressure": "past_action_ownership",
    "E_AC2_ownership": "past_action_ownership",
    "E_AC3_recovery_plan": "proactive_improvement",
    "E_AC4_decision_time": "formal_accountability",
    "E_CO2_accountability_consistency": "past_action_ownership",
}

# نگاشت پیش‌فرض در صورت نبود در SUB_COMP_MAP
DEFAULT_SUB = {
    "honesty": "general_honesty",
    "trustworthiness": "general_trust",
    "problem_solving": "general_problem_solving",
    "accountability": "general_accountability",
}

# ترجمه‌ی فارسی زیرمؤلفه‌ها
SUB_COMP_FA = {
    "transparency": "شفافیت",
    "boundary_setting": "تعیین مرز",
    "data_integrity": "یکپارچگی داده",
    "fair_judgment": "قضاوت منصفانه",
    "moral_consistency": "همسانی اخلاقی",
    "commitment_keeping": "پایبندی به تعهد",
    "autonomous_quality": "کیفیت خودگردان",
    "responsible_disclosure": "افشای مسئولانه",
    "resource_generosity": "سخاوت در منابع",
    "shared_responsibility": "مسئولیت مشترک",
    "root_cause_analysis": "تحلیل ریشه‌ای",
    "pattern_recognition": "شناسایی الگو",
    "sequence_planning": "برنامه‌ریزی مرحله‌ای",
    "creative_thinking": "تفکر خلاق",
    "adaptive_revision": "بازنگری انطباقی",
    "resource_allocation": "تخصیص منابع",
    "hazard_reporting": "گزارش خطر",
    "proactive_improvement": "بهبود پیش‌دستانه",
    "resistance_to_temptation": "مقاومت در برابر وسوسه",
    "task_persistence": "پایداری در وظیفه",
    "feedback_acceptance": "پذیرش بازخورد",
    "growth_mindset": "ذهنیت رشد",
    "formal_accountability": "پاسخگویی رسمی",
    "past_action_ownership": "مالکیت اعمال گذشته",
    "general_honesty": "عمومی (صداقت)",
    "general_trust": "عمومی (اعتماد)",
    "general_problem_solving": "عمومی (حل مسئله)",
    "general_accountability": "عمومی (مسئولیت)",
}


def _compute_sub_competencies(participant_id: str):
    """
    محاسبه‌ی نمره‌ی هر زیرمؤلفه از شواهد و ذخیره در دیتابیس.
    """
    from collections import defaultdict
    from web_app.db_manager import (
        get_connection, save_sub_competency_scores,
    )

    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT competency, evidence_key,
                   evidence_value, weight
            FROM web_evidence
            WHERE participant_id = ?
        """, (participant_id,))
        rows = c.fetchall()
        conn.close()

        sums = defaultdict(
            lambda: defaultdict(
                lambda: {"sum": 0.0, "weight": 0.0, "count": 0}
            )
        )

        for comp, ev_key, value, weight in rows:
            comp_str = str(comp or "")
            key_str = str(ev_key or "")
            v = float(value or 0.0)
            w = float(weight or 0.0)

            sub = SUB_COMP_MAP.get(key_str)
            if not sub:
                sub = DEFAULT_SUB.get(comp_str)
            if not sub:
                continue

            d = sums[comp_str][sub]
            d["sum"] += v * w
            d["weight"] += w
            d["count"] += 1

        final: dict = {}
        for comp, subs in sums.items():
            final[comp] = {}
            for sub, d in subs.items():
                if d["weight"] > 0:
                    score = (d["sum"] / d["weight"]) * 100
                else:
                    score = 0.0
                final[comp][sub] = {
                    "score": round(score, 2),
                    "count": int(d["count"]),
                }

        if final:
            save_sub_competency_scores(participant_id, final)
            print(
                f"   [SUB] ذخیره شد: "
                f"{sum(len(v) for v in final.values())} زیرمؤلفه"
            )
        return final
    except Exception as e:
        print(f"   [SUB] خطا: {e}")
        return {}

# ============================================================
# MRL (Moral Reasoning Level)
# ============================================================
def _compute_mrl(participant_id: str) -> dict:
    """
    محاسبه‌ی سطح استدلال اخلاقی از توزیع طرح‌واره‌ها.
    """
    from web_app.db_manager import get_schema_distribution

    dist = get_schema_distribution(participant_id)
    pi = dist.get("personal_interest", 0)
    mn = dist.get("maintaining_norms", 0)
    pc = dist.get("postconventional", 0)
    total = pi + mn + pc

    if total == 0:
        return {
            "level": "unknown",
            "score": 0.0,
            "pi": 0, "mn": 0, "pc": 0, "total": 0,
        }

    raw = (pc * 2) - (pi * 1) + (mn * 0.5)
    normalized = raw / (total * 2)

    if normalized > 0.25:
        level = "postconventional"
    elif normalized > -0.25:
        level = "maintaining_norms"
    else:
        level = "personal_interest"

    return {
        "level": level,
        "score": round(normalized, 3),
        "pi": pi, "mn": mn, "pc": pc, "total": total,
    }

def compute_scores(participant_id: str) -> dict:
    """
    محاسبه‌ی نمره‌ی هر شایستگی از شواهد ثبت‌شده.

    Returns:
        {competency: {"score": float, "count": int}}
    """
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT competency,
               SUM(evidence_value * weight) /
                   NULLIF(SUM(weight), 0) * 100 as score,
               COUNT(*) as cnt
        FROM web_evidence
        WHERE participant_id = ?
        GROUP BY competency
    """, (participant_id,))
    result = {}
    for comp, score, cnt in c.fetchall():
        result[comp] = {
            "score": round(score or 0.0, 1),
            "count": cnt,
        }
    conn.close()
    return result


# ✅ TypeVar + cast برای رفع خطای Pylance
_T = TypeVar("_T")


async def _io(func: Callable[..., _T], **kwargs: Any) -> _T:
    """
    نسخه‌ی type-safe از run.io_bound.
    Pylance را قانع می‌کند که نتیجه هم‌نوع با تابع ورودی است.
    """
    result = await run.io_bound(func, **kwargs)
    return cast(_T, result)


@ui.page('/results')
async def results_page():
    participant_id = app.storage.user.get('participant_id')
    if not participant_id:
        ui.navigate.to('/')
        return

    setup_page_audio("results")

    ui.query('body').style(PAGE_CSS)

    # ✅ ۱. محاسبه‌ی consistency (CO-01/02/03)
    await _io(
        _compute_and_save_consistency,
        participant_id=participant_id,
    )

    # ✅ ۲. محاسبه‌ی زیرمؤلفه‌ها
    sub_scores: dict = (
        await _io(
            _compute_sub_competencies,
            participant_id=participant_id,
        )
    ) or {}

    # ✅ محاسبه‌ی MRL
    mrl: dict = (
        await _io(_compute_mrl, participant_id=participant_id)
    ) or {"level": "unknown"}

    # ✅ ۳. محاسبه‌ی نمرات اصلی
    scores: dict = (
        await _io(compute_scores, participant_id=participant_id)
    ) or {}
    relationships: dict = (
        await _io(
            get_relationships_web, participant_id=participant_id
        )
    ) or {}

    values = [
        scores.get(c, {}).get("score", 0.0)
        for c in COMPETENCY_ORDER
    ]
    labels = [COMPETENCY_FA[c] for c in COMPETENCY_ORDER]

    avg = sum(values) / len(values) if values else 0.0

    # ---- تعیین برچسب کلی ----
    if avg >= 80:
        badge_text = "الگوی متعالی"
        badge_color = "#4CAF50"
    elif avg >= 65:
        badge_text = "الگوی متعادل"
        badge_color = "#4FC3F7"
    elif avg >= 45:
        badge_text = "در حال توسعه"
        badge_color = "#FF8F00"
    else:
        badge_text = "نیازمند بازنگری"
        badge_color = "#D32F2F"

    with ui.column().classes(
        'w-full max-w-3xl mx-auto p-8 gap-4'
    ):
        # ---- عنوان ----
        ui.label("نیمرخ شایستگی عملیاتی").classes(
            'text-3xl font-bold text-cyan-400 text-center'
        )
        ui.label(
            "بر اساس شواهد رفتاری ثبت‌شده در طول مأموریت"
        ).classes(
            'text-base text-gray-400 text-center mb-2'
        )

        # ---- بج کلی ----
        with ui.row().classes('w-full justify-center mb-2'):
            ui.label(badge_text).classes(
                'text-base font-bold px-4 py-2 rounded-full'
            ).style(
                f"color: #0B1D3A; background-color: {badge_color};"
            )
        ui.label(
            f"میانگین کل: {avg:.1f} از ۱۰۰"
        ).classes(
            'text-sm text-gray-300 text-center mb-4'
        )

        # ✅ بج MRL
        level_map = {
            "postconventional": (
                "🧭 استدلال پسافرا قراردادی",
                "#4CAF50",
                "تصمیم‌هایت را بر اساس اصول جهان‌شمول و "
                "عدالت گرفته‌ای — حتی وقتی هزینه داشته.",
            ),
            "maintaining_norms": (
                "⚖️ استدلال هنجارمحور",
                "#4FC3F7",
                "پایبندی به قواعد و رویه‌های سازمانی، "
                "محور تصمیم‌های تو بوده است.",
            ),
            "personal_interest": (
                "⚠️ استدلال منفعت‌محور",
                "#FF8F00",
                "در برخی تصمیم‌ها، منافع شخصی یا اجتناب "
                "از دردسر، اولویت داشته است.",
            ),
        }

        mrl_entry = level_map.get(str(mrl.get("level") or ""))
        if mrl_entry is not None:
            lbl, col, desc = mrl_entry
            with ui.row().classes(
                'w-full justify-center mb-2'
            ):
                ui.label(
                    f"{lbl}  ({mrl['pc']}/{mrl['mn']}/{mrl['pi']})"
                ).classes(
                    'text-sm font-bold px-4 py-2 rounded-full'
                ).style(
                    f"color: #FFFFFF; background-color: {col};"
                )
            ui.label(desc or "").classes(
                'text-xs text-gray-400 text-center mb-4'
            )
        else:
            ui.label(
                "— داده‌ی کافی برای ارزیابی سطح استدلال "
                "ثبت نشده."
            ).classes(
                'text-xs text-gray-500 text-center mb-4'
            )

        # ---- نمودار رادار ----
        if any(v > 0 for v in values):
            echart_opts = {
                "radar": {
                    "indicator": [
                        {"name": lbl, "max": 100}
                        for lbl in labels
                    ],
                    "radius": "62%",
                    "axisName": {
                        "color": "#FFFFFF",
                        "fontSize": 12,
                    },
                    "splitLine": {
                        "lineStyle": {"color": "#2B4A6F"},
                    },
                    "splitArea": {
                        "areaStyle": {
                            "color": [
                                "rgba(43, 74, 111, 0.1)",
                                "rgba(43, 74, 111, 0.25)",
                            ],
                        },
                    },
                    "axisLine": {
                        "lineStyle": {"color": "#2B4A6F"},
                    },
                },
                "series": [
                    {
                        "type": "radar",
                        "data": [
                            {
                                "value": values,
                                "name": "نمرات",
                                "areaStyle": {
                                    "color": (
                                        "rgba(79, 195, 247, 0.4)"
                                    ),
                                },
                                "lineStyle": {
                                    "color": "#4FC3F7",
                                    "width": 2,
                                },
                                "itemStyle": {
                                    "color": "#4FC3F7",
                                },
                            }
                        ],
                    }
                ],
                "backgroundColor": "transparent",
            }
            ui.echart(echart_opts).classes(
                'w-full'
            ).style('height: 400px;')
        else:
            ui.label(
                "داده‌ی کافی برای نمایش نمودار وجود ندارد."
            ).classes(
                'text-sm text-gray-400 text-center '
                'p-6 w-full bg-slate-800 rounded'
            )

        # ---- جزئیات هر شایستگی ----
        ui.label("جزئیات نمرات").classes(
            'text-xl font-bold text-cyan-400 mt-4 '
            'w-full text-right'
        )

        for comp in COMPETENCY_ORDER:
            data: dict = scores.get(comp, {})
            sc = data.get("score", 0.0)
            cnt = data.get("count", 0)
            fa = COMPETENCY_FA[comp]
            level = _level(sc)

            if sc >= 70:
                color = "#4CAF50"
            elif sc >= 40:
                color = "#FF8F00"
            else:
                color = "#D32F2F"

            interp = INTERPRETATIONS.get((comp, level), "")

            with ui.card().classes(
                'w-full bg-slate-800 p-4 mt-2'
            ):
                with ui.row().classes(
                    'items-center justify-between '
                    'w-full no-wrap'
                ):
                    ui.label(fa).classes(
                        'text-base text-white font-bold'
                    )
                    ui.label(f"{sc:.1f}").classes(
                        'text-2xl font-bold'
                    ).style(f"color: {color};")
                ui.linear_progress(
                    value=sc / 100.0, show_value=False,
                ).classes('w-full mt-2')
                ui.label(interp).classes(
                    'text-xs text-gray-300 w-full '
                    'text-right mt-2 leading-relaxed'
                )
                ui.label(
                    f"تعداد شواهد: {cnt}"
                ).classes(
                    'text-xs text-gray-500 w-full text-right'
                )

                # ✅ زیرمؤلفه‌ها
                comp_subs = sub_scores.get(comp, {})
                if comp_subs:
                    sorted_subs = sorted(
                        comp_subs.items(),
                        key=lambda x: -x[1]["score"],
                    )
                    with ui.expansion(
                        f'زیرمؤلفه‌ها ({len(sorted_subs)} مورد)',
                        icon='analytics',
                        value=True,
                    ).classes('w-full mt-2'):
                        for sub_key, sub_data in sorted_subs:
                            sub_fa = SUB_COMP_FA.get(
                                sub_key, sub_key
                            )
                            sub_score = sub_data["score"]
                            sub_cnt = sub_data["count"]
                            if sub_score >= 70:
                                sub_color = "#4CAF50"
                            elif sub_score >= 40:
                                sub_color = "#FF8F00"
                            else:
                                sub_color = "#D32F2F"

                            with ui.row().classes(
                                'w-full items-center '
                                'justify-between no-wrap mt-1'
                            ):
                                ui.label(
                                    str(sub_fa or "")
                                ).classes(
                                    'text-xs text-gray-300'
                                )
                                with ui.row().classes(
                                    'items-center gap-2 no-wrap'
                                ):
                                    ui.label(
                                        f"{sub_score:.0f}"
                                    ).classes(
                                        'text-xs font-bold font-mono'
                                    ).style(f"color: {sub_color};")
                                    ui.label(
                                        f"({sub_cnt})"
                                    ).classes(
                                        'text-[10px] '
                                        'text-gray-500'
                                    )
                            ui.linear_progress(
                                value=sub_score / 100.0,
                                show_value=False,
                            ).classes('w-full').style(
                                f'--nicegui-linear-progress-color: '
                                f'{sub_color}; height: 4px;'
                            )

        async def _download_pdf():
            ui.navigate.to('/download-report')
            
        ui.button(
            "📄 دانلود گزارش تفصیلی PDF",
            on_click=_download_pdf
        ).classes(
            'w-full py-3 text-lg font-bold bg-orange-600 hover:bg-orange-500 mt-4 rounded-lg'
        )


        # ---- دکمه‌ی پایان ----
        async def end_session():
            app.storage.user.clear()
            ui.navigate.to('/thank-you')

        ui.button(
            "پایان و خروج", on_click=end_session,
        ).classes(
            'w-full bg-green-600 hover:bg-green-500 '
            'text-white text-xl font-bold py-4 '
            'mt-6 rounded-lg'
        )

        ui.label(
            f"کد شرکت شما: {participant_id}"
        ).classes(
            'text-xs text-gray-500 text-center mt-4 '
            'font-mono'
        )