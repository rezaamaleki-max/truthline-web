"""
HUD سراسری — نوار وضعیت چسبان بالای صفحه (نسخه‌ی موبایل‌پسند)
==========================================
- در صفحه‌های بزرگ: یک ردیف افقی
- در صفحه‌های کوچک: دو ردیف (اطلاعات اصلی + نوار پیشرفت)
- شناسه شرکت‌کننده truncate می‌شود
- برند ایستگاه در موبایل مخفی می‌شود
"""
from nicegui import ui, app


# ============================================================
# دنباله‌ی مراحل بازی و وزن هر مرحله
# ============================================================
GAME_STAGES = [
    ("phase1",     "روز اول — سکوت",           0.12),
    ("night1",     "شب اول",                    0.02),
    ("interlude2", "میان‌پرده روز دوم",          0.01),
    ("phase2",     "روز دوم — سایه‌ها",         0.15),
    ("night2",     "شب دوم",                    0.02),
    ("interlude3", "میان‌پرده روز سوم",          0.01),
    ("phase3",     "روز سوم — معمای داده‌ها",   0.20),
    ("night3",     "شب سوم",                    0.02),
    ("interlude4", "میان‌پرده روز چهارم",        0.01),
    ("phase4",     "روز چهارم — آستانه‌ی شورا", 0.20),
    ("hexaco",     "HEXACO-24",                 0.05),
    ("crt",        "CRT7",                      0.02),
    ("sd3",        "SD3",                       0.03),
    ("sd",         "SD",                        0.02),
    ("feedback",   "بازخورد",                   0.02),
    ("epilogue",   "اختتامیه",                  0.05),
    ("results",    "نتایج",                     0.05),
]


_STAGE_INDEX = {k: i for i, (k, _, _) in enumerate(GAME_STAGES)}


def _total_progress(stage_key: str, sub: float) -> float:
    """محاسبه‌ی درصد پیشرفت کل (0..100)"""
    idx = _STAGE_INDEX.get(stage_key)
    if idx is None:
        return 0.0
    prev = sum(w for _, _, w in GAME_STAGES[:idx])
    curr = GAME_STAGES[idx][2]
    sub = max(0.0, min(1.0, sub))
    return (prev + curr * sub) * 100.0


async def render_hud(
    stage_key: str,
    sub_progress: float = 0.0,
    objective: str = "",
    scenario_current: int = 0,
    scenario_total: int = 0,
):
    """
    نوار HUD را در بالای صفحه رندر می‌کند.
    روی موبایل، به‌طور خودکار به دو ردیف تبدیل می‌شود.
    """
    idx = _STAGE_INDEX.get(stage_key)
    if idx is None:
        return

    stage_name = GAME_STAGES[idx][1]
    total_pct = _total_progress(stage_key, sub_progress)

    with ui.card().classes(
        'w-full bg-slate-900 border-b-2 border-cyan-400 '
        'px-3 py-2 rounded-none'
    ).style(
        'position: sticky; top: 0; z-index: 50; '
        'margin-bottom: 8px; '
        'overflow-x: hidden;'   # ✅ جلوگیری از سرریز افقی
    ):
        # ============================================================
        # ردیف ۱: اطلاعات اصلی (wrap می‌شود)
        # ============================================================
        with ui.row().classes(
            'items-center gap-2 w-full flex-wrap'
        ).style('row-gap: 4px;'):
            # برند ایستگاه — در موبایل مخفی
            ui.label("🚀 ایستگاه کاسپین").classes(
                'text-sm text-cyan-400 font-bold '
                'whitespace-nowrap hidden sm:inline'
            )
            ui.label("•").classes(
                'text-cyan-600 whitespace-nowrap hidden sm:inline'
            )

            # نام مرحله
            ui.label(stage_name).classes(
                'text-sm text-white font-bold'
            ).style('max-width: 200px; overflow: hidden; '
                    'text-overflow: ellipsis; white-space: nowrap;')

            # شماره‌ی سناریو
            if scenario_total > 0:
                ui.label(
                    f"• {scenario_current + 1}/{scenario_total}"
                ).classes(
                    'text-xs text-orange-400 font-bold '
                    'whitespace-nowrap'
                )

            # درصد پیشرفت
            ui.label(
                f"{total_pct:.0f}%"
            ).classes(
                'text-xs text-cyan-400 font-mono '
                'font-bold whitespace-nowrap'
            )

            # شناسه شرکت‌کننده — truncate شده
            pid = app.storage.user.get('participant_id', '')
            if pid:
                ui.label(pid).classes(
                    'text-xs text-gray-500 font-mono '
                    'bg-slate-800 px-2 py-0.5 rounded '
                    'truncate'
                ).style('max-width: 90px;')

        # ============================================================
        # ردیف ۲: هدف + نوار پیشرفت
        # ============================================================
        with ui.row().classes(
            'items-center gap-2 w-full no-wrap mt-1'
        ):
            # هدف جاری
            if objective:
                ui.label(objective).classes(
                    'text-xs text-gray-400 flex-1 truncate'
                )
            else:
                ui.element('div').classes('flex-1')

            # نوار پیشرفت — کوچک‌تر در موبایل
            with ui.element('div').style(
                'width: 80px; flex-shrink: 0;'
            ):
                ui.linear_progress(
                    value=total_pct / 100.0,
                    show_value=False,
                ).classes('w-full')