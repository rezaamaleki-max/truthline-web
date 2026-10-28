"""
مکانیک تحلیلگر کوانتومی — نسخه‌ی وب سینمایی
=============================================
- موج سینوسی متحرک با SVG
- نمایشگر دیجیتال با افکت glow
- سه فعال‌سازی متوالی (یکی برای هر قرائت)
- افکت «فروپاشی تابع موج» (flash) در هر فعال‌سازی
- نمایش هشدار + دکمه‌ی ادامه پس از پایان همه‌ی قرائت‌ها
"""
import asyncio
import time
from nicegui import ui

from web_app.config import TEST_MODE
from web_app.audio import play_scan_sfx

# ============================================================
# CSS سراسری (یک بار در app.py تزریق می‌شود)
# ============================================================
QUANTUM_CSS_HTML = """
<style>
@keyframes tl-wave-slide {
    from { transform: translateX(0); }
    to { transform: translateX(-50%); }
}
@keyframes tl-glow-pulse {
    0%, 100% { opacity: 0.5; filter: blur(18px); }
    50% { opacity: 1; filter: blur(24px); }
}
@keyframes tl-flash {
    0% { opacity: 1; transform: scale(0.5); }
    100% { opacity: 0; transform: scale(2); }
}
@keyframes tl-reading-in {
    from { opacity: 0; transform: translateY(-10px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes tl-digit-glow {
    0%, 100% { text-shadow: 0 0 8px currentColor, 0 0 16px currentColor; }
    50% { text-shadow: 0 0 12px currentColor, 0 0 24px currentColor; }
}
@keyframes tl-scan-line {
    0% { transform: translateY(-100%); opacity: 0; }
    50% { opacity: 0.6; }
    100% { transform: translateY(200px); opacity: 0; }
}

.tl-q-visual {
    position: relative;
    width: 100%;
    height: 220px;
    background: radial-gradient(ellipse at center, #0a1a30 0%, #050A18 70%);
    border: 2px solid #4FC3F7;
    border-radius: 12px;
    overflow: hidden;
    margin: 12px 0;
    box-shadow: 
        inset 0 0 40px rgba(79, 195, 247, 0.15),
        0 0 20px rgba(79, 195, 247, 0.2);
}
.tl-q-grid {
    position: absolute; inset: 0;
    background-image: 
        linear-gradient(rgba(79, 195, 247, 0.06) 1px, transparent 1px),
        linear-gradient(90deg, rgba(79, 195, 247, 0.06) 1px, transparent 1px);
    background-size: 25px 25px;
    pointer-events: none;
}
.tl-q-scan {
    position: absolute;
    inset: 0;
    background: linear-gradient(
        to bottom,
        transparent 0%,
        rgba(79, 195, 247, 0.15) 50%,
        transparent 100%
    );
    height: 40px;
    animation: tl-scan-line 3s linear infinite;
    pointer-events: none;
}
.tl-q-glow {
    position: absolute;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    width: 320px; height: 160px;
    background: radial-gradient(ellipse, rgba(79, 195, 247, 0.35) 0%, transparent 70%);
    animation: tl-glow-pulse 2.5s ease-in-out infinite;
    pointer-events: none;
}
.tl-q-wave-container {
    position: absolute;
    top: 0; left: 0;
    width: 200%; height: 100%;
    animation: tl-wave-slide 5s linear infinite;
    pointer-events: none;
}
.tl-q-flash {
    position: absolute;
    top: 50%; left: 50%;
    width: 200px; height: 200px;
    margin-left: -100px;
    margin-top: -100px;
    background: radial-gradient(circle, rgba(255, 255, 255, 0.9) 0%, rgba(79, 195, 247, 0.6) 30%, transparent 70%);
    border-radius: 50%;
    opacity: 0;
    pointer-events: none;
    z-index: 20;
}
.tl-q-flash.active {
    animation: tl-flash 0.7s ease-out;
}
.tl-q-readout {
    position: absolute;
    top: 12px; right: 12px;
    background: rgba(5, 10, 24, 0.85);
    border: 1px solid #4FC3F7;
    border-radius: 6px;
    padding: 8px 14px;
    font-family: Consolas, 'Courier New', monospace;
    z-index: 10;
    box-shadow: 0 0 15px rgba(79, 195, 247, 0.35);
}
.tl-q-readout .label {
    color: #90A4AE;
    font-size: 9px;
    letter-spacing: 1px;
    margin-bottom: 3px;
}
.tl-q-readout .value {
    color: #4FC3F7;
    font-size: 20px;
    font-weight: bold;
    animation: tl-digit-glow 2s ease-in-out infinite;
}
.tl-q-status {
    position: absolute;
    bottom: 12px; left: 12px;
    padding: 5px 12px;
    background: rgba(5, 10, 24, 0.85);
    border: 1px solid #4FC3F7;
    border-radius: 4px;
    color: #4FC3F7;
    font-size: 10px;
    letter-spacing: 1px;
    z-index: 10;
    display: flex;
    align-items: center;
    gap: 6px;
}
.tl-q-status .dot {
    width: 6px; height: 6px;
    border-radius: 50%;
    background: #4CAF50;
    box-shadow: 0 0 8px #4CAF50;
}
.tl-q-status .dot.idle {
    background: #FF8F00;
    box-shadow: 0 0 8px #FF8F00;
    animation: tl-glow-pulse 1.5s ease-in-out infinite;
}
.tl-reading-card {
    animation: tl-reading-in 0.4s ease-out;
}
</style>
"""


# ============================================================
# HTML موج SVG
# ============================================================
QUANTUM_WAVE_HTML = """
<div class="tl-q-visual">
    <div class="tl-q-grid"></div>
    <div class="tl-q-glow"></div>
    <div class="tl-q-scan"></div>
    <svg class="tl-q-wave-container" viewBox="0 0 1600 220" preserveAspectRatio="none">
        <defs>
            <linearGradient id="tlWaveGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#4FC3F7" stop-opacity="0"/>
                <stop offset="15%" stop-color="#4FC3F7" stop-opacity="1"/>
                <stop offset="85%" stop-color="#4FC3F7" stop-opacity="1"/>
                <stop offset="100%" stop-color="#4FC3F7" stop-opacity="0"/>
            </linearGradient>
            <filter id="tlWaveGlow">
                <feGaussianBlur stdDeviation="3" result="blur"/>
                <feMerge>
                    <feMergeNode in="blur"/>
                    <feMergeNode in="SourceGraphic"/>
                </feMerge>
            </filter>
        </defs>
        <path d="M 0 110 
                 C 50 60, 100 60, 150 110 
                 S 250 160, 300 110 
                 S 400 60, 450 110 
                 S 550 160, 600 110 
                 S 700 60, 750 110 
                 S 850 160, 900 110 
                 S 1000 60, 1050 110 
                 S 1150 160, 1200 110 
                 S 1300 60, 1350 110 
                 S 1450 160, 1500 110 
                 S 1600 60, 1600 110"
              fill="none"
              stroke="url(#tlWaveGrad)"
              stroke-width="2.5"
              opacity="0.85"
              filter="url(#tlWaveGlow)"/>
        <path d="M 0 110 
                 C 50 40, 100 40, 150 110 
                 S 250 180, 300 110 
                 S 400 40, 450 110 
                 S 550 180, 600 110 
                 S 700 40, 750 110 
                 S 850 180, 900 110 
                 S 1000 40, 1050 110 
                 S 1150 180, 1200 110 
                 S 1300 40, 1350 110 
                 S 1450 180, 1500 110 
                 S 1600 40, 1600 110"
              fill="none"
              stroke="#4FC3F7"
              stroke-width="1"
              opacity="0.3"/>
    </svg>
    <div class="tl-q-flash" id="tlFlash"></div>
    <div class="tl-q-readout">
        <div class="label">دامنه موج</div>
        <div class="value" id="tlReadoutValue">—</div>
    </div>
    <div class="tl-q-status" id="tlStatus">
        <span class="dot idle"></span>
        <span>آماده</span>
    </div>
</div>
"""


# ============================================================
# تابع اصلی
# ============================================================
async def render_quantum_analyzer(
    readings: list[float],
    unit: str = "دامنه موج",
    warning_text: str = "",
    activation_button: str = "فروپاشی تابع موج",
    activation_delay_ms: int = 1400,
    on_complete=None,
):
    """
    رندر مکانیک تحلیلگر کوانتومی (نسخه‌ی سه‌فعال‌سازی).
    """
    # ---- توضیح اولیه ----
    ui.label(
        f'تحلیلگر آماده است. برای هر یک از {len(readings)} قرائت، '
        f'دکمه‌ی زیر را یک بار فشار بده.'
    ).classes('text-sm text-gray-400 text-center w-full mb-2')

    # ---- نمایشگر موج ----
    ui.html(QUANTUM_WAVE_HTML).classes('w-full')

    # ---- برچسب وضعیت (متنی) ----
    status_label = ui.label(
        f'آماده‌ی قرائت ۱ از {len(readings)}'
    ).classes(
        'text-center text-cyan-300 font-bold text-sm mt-2 w-full'
    )

    # ---- محل نمایش قرائت‌ها ----
    readings_container = ui.column().classes('w-full gap-2 mt-2')

    # ---- دکمه‌ی فعال‌سازی ----
    activate_btn = ui.button(activation_button).classes(
        'w-full py-4 text-lg font-bold '
        'bg-purple-600 hover:bg-purple-500 mt-4 '
        'shadow-lg shadow-purple-500/50'
    )

    # ---- وضعیت داخلی ----
    state = {
        "activation_count": 0,
        "collected": [],
        "start_time": 0.0,
        "is_activating": False,
        "is_done": False,
    }

    # ---- توابع کمکی برای به‌روزرسانی نمایشگر ----
    def _update_readout(value_text: str):
        ui.run_javascript(
            f"document.getElementById('tlReadoutValue').textContent = "
            f"'{value_text}';"
        )

    def _update_status(text: str, is_idle: bool):
        dot_class = "dot idle" if is_idle else "dot"
        ui.run_javascript(
            f"document.getElementById('tlStatus').innerHTML = "
            f"'<span class=\"{dot_class}\"></span>"
            f"<span>{text}</span>';"
        )

    def _trigger_flash():
        ui.run_javascript(
            "const f = document.getElementById('tlFlash');"
            "f.classList.add('active');"
            "setTimeout(() => f.classList.remove('active'), 700);"
        )

    # ---- فعال‌سازی (هر بار یک قرائت) ----
    async def _on_activate():
        if state["is_activating"] or state["is_done"]:
            return
        play_scan_sfx()  # ✅ صدای فروپاشی تابع موج
        if state["activation_count"] >= len(readings):
            return

        # ثبت زمان شروع در اولین فعال‌سازی
        if state["activation_count"] == 0:
            state["start_time"] = time.time()

        state["is_activating"] = True
        i = state["activation_count"]

        # دکمه را غیرفعال کن
        activate_btn.disable()
        activate_btn.text = f'⏳ در حال فعال‌سازی قرائت {i + 1}...'
        _update_status(
            f'در حال فعال‌سازی قرائت {i + 1}...', is_idle=False
        )

        # تاخیر فعال‌سازی
        await asyncio.sleep(activation_delay_ms / 1000)

        # افکت فروپاشی
        _trigger_flash()
        await asyncio.sleep(0.3)

        # ثبت قرائت
        r = readings[i]
        state["collected"].append(r)
        state["activation_count"] += 1
        state["is_activating"] = False

        _update_readout(f'{r}')

        # نمایش کارت قرائت
        with readings_container:
            with ui.card().classes(
                'w-full bg-slate-800 border-2 border-cyan-400 '
                'p-4 tl-reading-card'
            ):
                with ui.row().classes(
                    'items-center gap-3 no-wrap w-full'
                ):
                    ui.label('📊').classes(
                        'text-2xl flex-shrink-0'
                    )
                    with ui.column().classes('gap-0 flex-1'):
                        ui.label(
                            f'قرائت {i + 1} از {len(readings)}'
                        ).classes('text-xs text-gray-400')
                        ui.label(f'{r} {unit}').classes(
                            'text-lg text-cyan-300 font-mono font-bold'
                        )
                    with ui.column().classes(
                        'gap-0 items-end flex-shrink-0'
                    ):
                        ui.label('میانگین').classes(
                            'text-xs text-gray-400'
                        )
                        running_avg = (
                            sum(state["collected"])
                            / len(state["collected"])
                        )
                        ui.label(f'{running_avg:.2f}').classes(
                            'text-base text-orange-400 font-mono '
                            'font-bold'
                        )

        # به‌روزرسانی دکمه و وضعیت
        if state["activation_count"] < len(readings):
            next_num = state["activation_count"] + 1
            status_label.set_text(
                f'✓ قرائت {i + 1} انجام شد — آماده‌ی '
                f'قرائت {next_num} از {len(readings)}'
            )
            _update_status(
                f'آماده‌ی قرائت {next_num}', is_idle=True
            )
            activate_btn.enable()
            activate_btn.text = activation_button
        else:
            # همه‌ی قرائت‌ها انجام شد
            state["is_done"] = True
            status_label.set_text('✓ همه‌ی قرائت‌ها تکمیل شد')
            _update_status('✓ تکمیل شد', is_idle=False)
            activate_btn.set_visibility(False)
            await _show_results()

    # ---- نمایش نتایج + هشدار + دکمه‌ی ادامه ----
    async def _show_results():
        avg = sum(state["collected"]) / len(state["collected"])
        await asyncio.sleep(0.4)

        # نمایش میانگین نهایی
        with readings_container:
            with ui.card().classes(
                'w-full bg-gradient-to-br from-cyan-900/60 '
                'to-blue-900/60 border-2 border-cyan-300 '
                'p-5 tl-reading-card'
            ):
                with ui.column().classes(
                    'gap-1 items-center w-full'
                ):
                    ui.label('✓ میانگین نهایی').classes(
                        'text-sm text-cyan-200 font-bold '
                        'tracking-wider'
                    )
                    ui.label(f'{avg:.2f}').classes(
                        'text-4xl text-cyan-300 font-mono font-bold '
                        'drop-shadow-[0_0_10px_rgba(79,195,247,0.7)]'
                    )
                    ui.label(unit).classes(
                        'text-xs text-cyan-200/70'
                    )

        _update_readout(f'{avg:.2f}')

        # نمایش هشدار (اگر وجود دارد) — بعد از نتایج
        if warning_text:
            await asyncio.sleep(0.3)
            with ui.card().classes(
                'w-full bg-orange-900/30 border-2 border-orange-400 '
                'p-4 tl-reading-card mt-2'
            ):
                with ui.row().classes(
                    'items-start gap-2 no-wrap'
                ):
                    ui.label('⚠️').classes(
                        'text-2xl flex-shrink-0'
                    )
                    ui.label(warning_text).classes(
                        'text-sm text-orange-200 italic flex-1 '
                        'leading-relaxed'
                    )

        # دکمه‌ی ادامه
        await asyncio.sleep(0.3)

        async def _continue():
            total_time = int(
                (time.time() - state["start_time"]) * 1000
            )
            if on_complete:
                await on_complete(state["collected"], total_time)

        ui.button('✓ ادامه به گزارش').classes(
            'w-full py-4 text-lg font-bold '
            'bg-green-600 hover:bg-green-500 mt-3 '
            'shadow-lg shadow-green-500/50 tl-reading-card'
        ).on_click(_continue)

    # ---- اتصال دکمه ----
    activate_btn.on_click(_on_activate)

