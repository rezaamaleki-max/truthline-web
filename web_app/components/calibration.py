"""
مکانیک کالیبراسیون — نسخه‌ی وب سینمایی
========================================
- راهنمای گام‌به‌گام
- سه نوع کنترل: افقی، عمودی، دیال
- نوار هدف گرافیکی با نشانگر متحرک
- نمایشگر مقدار رنگی
- پیشرفت نقطه‌ای
- دکمه‌ی «میان‌بر» (در ابتدا غیرفعال)
- بعد از ۱۵ ثانیه: پاپ‌آپ وسوسه‌ی رحیمی + فعال شدن دکمه میان‌بر
"""
import asyncio
import time
from nicegui import ui

from web_app.config import TEST_MODE


# ============================================================
# CSS
# ============================================================
CALIBRATION_CSS_HTML = """
<style>
.tl-cal-guide {
    background: linear-gradient(135deg, rgba(255,143,0,0.10), rgba(255,143,0,0.02));
    border: 2px solid rgba(255,143,0,0.5);
    border-radius: 10px;
    padding: 12px 16px;
}
.tl-cal-dot {
    display: inline-block;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: #1A2A4A;
    border: 2px solid #444;
    margin: 0 3px;
    transition: all 0.25s;
    vertical-align: middle;
}
.tl-cal-dot.in-zone {
    background: #4CAF50;
    border-color: #81C784;
    box-shadow: 0 0 8px rgba(76, 175, 80, 0.9);
}
.tl-cal-bar {
    position: relative;
    width: 100%;
    height: 20px;
    background: linear-gradient(90deg, #0a1428, #1A2A4A);
    border: 1px solid #2B4A6F;
    border-radius: 10px;
    overflow: hidden;
    margin: 8px 0;
}
.tl-cal-zone {
    position: absolute;
    top: 0;
    height: 100%;
    background: rgba(76, 175, 80, 0.55);
    box-shadow: inset 0 0 10px rgba(76, 175, 80, 0.6);
}
.tl-cal-target-tick {
    position: absolute;
    top: -3px;
    width: 2px;
    height: calc(100% + 6px);
    background: #4CAF50;
    box-shadow: 0 0 8px #4CAF50;
    margin-left: -1px;
}
.tl-cal-marker {
    position: absolute;
    top: 50%;
    width: 14px;
    height: 14px;
    margin-top: -7px;
    margin-left: -7px;
    border-radius: 50%;
    background: white;
    border: 2px solid #4FC3F7;
    box-shadow: 0 0 10px rgba(79, 195, 247, 0.9);
    transition: left 0.12s ease, background 0.2s, border-color 0.2s;
    z-index: 2;
}
.tl-cal-marker.in-zone {
    background: #4CAF50;
    border-color: #81C784;
    box-shadow: 0 0 12px rgba(76, 175, 80, 1);
}
.tl-cal-value {
    font-family: Consolas, monospace;
    font-size: 20px;
    font-weight: bold;
    transition: color 0.2s;
}
.tl-cal-value.in-zone { color: #4CAF50; }
.tl-cal-value.out-zone { color: #FF8F00; }
.tl-cal-vslider-wrap {
    height: 130px;
    display: flex;
    align-items: center;
    justify-content: center;
}
.tl-cal-card {
    transition: border-color 0.2s, box-shadow 0.2s;
}
.tl-cal-card.in-zone {
    border-color: #4CAF50 !important;
    box-shadow: 0 0 12px rgba(76, 175, 80, 0.25);
}
</style>
"""

def _initial_value_for_sensor(
    sensor: dict, index: int
) -> float:
    """
    Return initial value, guaranteed outside target zone.
    """
    target = float(sensor["target"])
    tol = float(sensor["tolerance"])
    offsets = [30, -25, 25, -30, 20, -20]
    delta = offsets[index % len(offsets)]

    # Try primary direction
    initial = max(5.0, min(95.0, target + delta))
    if abs(initial - target) > tol:
        return initial

    # Try opposite direction
    initial = max(5.0, min(95.0, target - delta))
    if abs(initial - target) > tol:
        return initial

    # Fallback: pick farthest extreme
    candidates = [5.0, 95.0]
    return max(candidates, key=lambda c: abs(c - target))

# ============================================================
# توابع کمکی
# ============================================================
def _sensor_icon(name: str) -> str:
    if 'حرارت' in name: return '🔥'
    if 'فشار' in name: return '🎯'
    if 'نور' in name: return '💡'
    if 'ارتعاش' in name: return '📳'
    if 'جریان' in name: return '🌊'
    if 'تشعشع' in name: return '☢️'
    return '📊'


def _bar_html(value, target, tolerance, in_zone):
    lo = max(0, target - tolerance)
    hi = min(100, target + tolerance)
    marker_cls = "in-zone" if in_zone else ""
    return (
        f'<div class="tl-cal-bar">'
        f'<div class="tl-cal-zone" '
        f'style="left:{lo}%;width:{hi-lo}%;"></div>'
        f'<div class="tl-cal-target-tick" '
        f'style="left:{target}%;"></div>'
        f'<div class="tl-cal-marker {marker_cls}" '
        f'style="left:{value}%;"></div>'
        f'</div>'
    )


# ============================================================
# تابع اصلی
# ============================================================
async def render_calibration(
    sensors, on_complete,
    temptation_delay_sec: float = 15.0,
):
    """رندر مکانیک کالیبراسیون."""

    state = {
        "values": {
            i: _initial_value_for_sensor(s, i)
            for i, s in enumerate(sensors)
        },
        "start_time": time.time(),
        "cheat_used": False,
        "cheat_enabled": False,
        "temptation_shown": False,
        "submitted": False,
        "bars": {},
        "value_labels": {},
        "status_labels": {},
        "cards": {},
    }

    def _in_zone(i):
        s = sensors[i]
        return abs(state["values"][i] - s["target"]) <= s["tolerance"]

    def _count_in_zone():
        return sum(1 for i in range(len(sensors)) if _in_zone(i))

    def _update_progress():
        count = _count_in_zone()
        total = len(sensors)
        dots = ""
        for i in range(total):
            cls = "in-zone" if _in_zone(i) else ""
            dots += f'<span class="tl-cal-dot {cls}"></span>'
        progress_dots.set_content(dots)
        progress_label.set_text(f"{count} از {total} در محدوده")
        if count == total:
            progress_label.style("color: #4CAF50;")
        elif count >= total // 2:
            progress_label.style("color: #FF8F00;")
        else:
            progress_label.style("color: #FFFFFF;")

    def _update_sensor(i):
        s = sensors[i]
        v = state["values"][i]
        in_zone = _in_zone(i)

        state["bars"][i].set_content(
            _bar_html(v, s["target"], s["tolerance"], in_zone)
        )

        lbl = state["value_labels"][i]
        lbl.set_text(f"{v:.1f}")
        lbl.classes(
            replace=f"tl-cal-value "
                    f"{'in-zone' if in_zone else 'out-zone'}"
        )

        status = state["status_labels"][i]
        if in_zone:
            status.set_text("✓ در محدوده")
            status.style("color: #4CAF50; font-weight: bold;")
        else:
            status.set_text("⚠ خارج از محدوده")
            status.style("color: #FF8F00; font-weight: bold;")

        card = state["cards"][i]
        card.classes(
            replace=f"tl-cal-card bg-slate-800 border "
                    f"{'border-green-500' if in_zone else 'border-slate-600'} "
                    f"p-3"
        )

        _update_progress()

    def _on_change(i, new_value):
        if new_value is None:
            return
        state["values"][i] = float(new_value)
        _update_sensor(i)

    # === عنوان ===
    ui.label("🎯 کالیبراسیون حسگرها").classes(
        'text-xl font-bold text-cyan-400 w-full text-right'
    )

    # === راهنما ===
    with ui.element('div').classes('tl-cal-guide w-full my-2'):
        ui.label("💡 راهنمای کالیبراسیون").classes(
            'text-base font-bold text-orange-400 mb-2'
        )
        with ui.column().classes('gap-1'):
            ui.label(
                f"• هر {len(sensors)} حسگر را باید داخل محدوده‌ی "
                f"سبز (محدوده‌ی هدف) قرار بدهی."
            ).classes('text-sm text-gray-300')
            ui.label(
                "• اسلایدر یا دیال را حرکت بده تا نشانگر سفید "
                "داخل ناحیه‌ی سبز بیاید."
            ).classes('text-sm text-gray-300')
            ui.label(
                "• وقتی نشانگر سبز شد و مقدار عددی سبز شد، "
                "آن حسگر کالیبره شده است."
            ).classes('text-sm text-gray-300')
            ui.label(
                "• هر چه دقیق‌تر (خطای کمتر) تنظیم کنی، "
                "بهتر است."
            ).classes('text-sm text-gray-300')

    # === نوار پیشرفت ===
    with ui.card().classes(
        'w-full bg-slate-800 border-2 border-orange-400 p-3'
    ):
        with ui.row().classes(
            'items-center justify-between w-full mb-1'
        ):
            ui.label("📊 پیشرفت:").classes(
                'text-sm text-orange-400 font-bold'
            )
            progress_label = ui.label("0 از 0 در محدوده").classes(
                'text-sm font-bold text-white'
            )
        progress_dots = ui.html("").classes('w-full text-center')

    # === گرید حسگرها ===
    with ui.grid(columns=2).classes('w-full gap-3'):
        for i, sensor in enumerate(sensors):
            icon = _sensor_icon(sensor["name"])
            lo = sensor["target"] - sensor["tolerance"]
            hi = sensor["target"] + sensor["tolerance"]
            initial_val = state["values"][i]
            in_zone_init = (
                abs(initial_val - sensor["target"])
                <= sensor["tolerance"]
            )

            card = ui.card().classes(
                f"tl-cal-card bg-slate-800 border "
                f"{'border-green-500' if in_zone_init else 'border-slate-600'} "
                f"p-3"
            )
            state["cards"][i] = card

            with card:
                with ui.row().classes(
                    'items-center justify-between w-full mb-2 no-wrap'
                ):
                    with ui.row().classes(
                        'items-center gap-1 no-wrap'
                    ):
                        ui.label(icon).classes('text-lg flex-shrink-0')
                        ui.label(sensor["name"]).classes(
                            'text-sm text-white font-bold'
                        )
                    ui.label(f"{lo:.0f}–{hi:.0f}").classes(
                        'text-xs text-green-400 font-mono font-bold '
                        'flex-shrink-0'
                    )

                ctrl_type = sensor.get("type", "horizontal")
                if ctrl_type == "horizontal":
                    ctrl = ui.slider(
                        min=0, max=100,
                        value=initial_val, step=0.5,
                    ).classes('w-full')
                elif ctrl_type == "vertical":
                    with ui.element('div').classes(
                        'tl-cal-vslider-wrap w-full'
                    ):
                        ctrl = ui.slider(
                            min=0, max=100,
                            value=initial_val, step=0.5,
                        ).props('vertical')
                else:  # dial
                    with ui.element('div').classes(
                        'tl-cal-vslider-wrap w-full'
                    ):
                        ctrl = ui.knob(
                            min=0, max=100,
                            value=initial_val, step=0.5,
                        ).props(
                            'size=110px thickness=0.15 '
                            'color=cyan'
                        )

                ctrl.on_value_change(
                    lambda e, idx=i: _on_change(idx, e.value)
                )

                bar = ui.html(
                    _bar_html(
                        initial_val, sensor["target"],
                        sensor["tolerance"], in_zone_init,
                    )
                ).classes('w-full mt-2')
                state["bars"][i] = bar

                with ui.row().classes(
                    'items-center justify-between w-full mt-1'
                ):
                    value_lbl = ui.label(
                        f"{initial_val:.1f}"
                    ).classes(
                        f"tl-cal-value "
                        f"{'in-zone' if in_zone_init else 'out-zone'}"
                    )
                    state["value_labels"][i] = value_lbl

                    status_lbl = ui.label(
                        "✓ در محدوده" if in_zone_init
                        else "⚠ خارج از محدوده"
                    ).classes('text-xs')
                    status_lbl.style(
                        "color: #4CAF50; font-weight: bold;"
                        if in_zone_init
                        else "color: #FF8F00; font-weight: bold;"
                    )
                    state["status_labels"][i] = status_lbl

    _update_progress()

    # === تابع ثبت ===
    async def _submit():
        if state["submitted"]:
            return
        state["submitted"] = True
        total_time = int((time.time() - state["start_time"]) * 1000)
        results = []
        in_zone_count = 0
        for i, s in enumerate(sensors):
            v = state["values"][i]
            err = abs(v - s["target"])
            ok = err <= s["tolerance"]
            if ok:
                in_zone_count += 1
            results.append({
                "name": s["name"],
                "value": round(v, 1),
                "target": s["target"],
                "error": round(err, 2),
                "in_zone": ok,
            })
        result = {
            "results": results,
            "in_zone_count": in_zone_count,
            "total_count": len(sensors),
            "out_zone_count": len(sensors) - in_zone_count,
            "total_time_ms": total_time,
            "cheat_used": state["cheat_used"],
        }
        if on_complete:
            await on_complete(result)

    # === دکمه‌ی ثبت ===
    ui.button("✓ ثبت کالیبراسیون دستی").classes(
        'w-full py-3 text-lg font-bold '
        'bg-green-600 hover:bg-green-500 mt-4 '
        'shadow-lg shadow-green-500/30'
    ).on_click(_submit)

    # === دکمه‌ی میان‌بر — در ابتدا غیرفعال ===
    shortcut_btn = ui.button("⚡ میان‌بر (در انتظار...)").classes(
        'w-full py-2 text-sm font-bold '
        'bg-slate-800 text-gray-500 border border-slate-700 mt-2'
    )
    shortcut_btn.disable()

    async def _on_shortcut():
        if not state["cheat_enabled"]:
            return
        if state["cheat_used"]:
            return

        with ui.dialog() as dialog, ui.card().classes(
            'bg-slate-800 border-2 border-orange-400 p-5 max-w-lg'
        ):
            ui.label("⚡ استفاده از تنظیمات کارخانه؟").classes(
                'text-lg font-bold text-orange-400 mb-3 w-full text-right'
            )
            ui.label(
                "با فشردن این گزینه، همه‌ی حسگرها با مقادیر پیش‌فرض "
                "کارخانه تأیید می‌شوند و گزارش دقیق کالیبراسیون "
                "ثبت نمی‌شود."
            ).classes(
                'text-sm text-gray-300 leading-relaxed mb-4 '
                'w-full text-right'
            )

            async def _accept():
                dialog.close()
                state["cheat_used"] = True
                for i, s in enumerate(sensors):
                    state["values"][i] = s["target"]
                    _update_sensor(i)
                await asyncio.sleep(0.3)
                await _submit()

            with ui.row().classes('w-full justify-end gap-2'):
                ui.button("بله، استفاده کن").on_click(_accept).classes(
                    'bg-orange-600 hover:bg-orange-500'
                )
                ui.button("انصراف").on_click(dialog.close).classes(
                    'bg-slate-600 hover:bg-slate-500'
                )

        dialog.open()

    shortcut_btn.on_click(_on_shortcut)

    # === تایمر وسوسه — پاپ‌آپ بعد از ۱۵ ثانیه ===
    async def _show_temptation():
        if state["submitted"] or state["temptation_shown"]:
            return
        state["temptation_shown"] = True

        with ui.dialog() as dialog, ui.card().classes(
            'bg-slate-800 border-2 border-orange-400 p-5 max-w-lg'
        ):
            ui.label("📞 پیام از مهندس رحیمی").classes(
                'text-lg font-bold text-orange-400 mb-3 '
                'w-full text-right'
            )
            ui.label(
                "مهندس رحیمی: «تکنسین، می‌دونم این حسگرها "
                "مهمن و کالیبراسیون دقیقشون روی کل سیستم اثر "
                "می‌ذاره. ولی الان راکتور به توجه فوری نیاز "
                "داره. اگه بخوای، من از راه دور یه تأیید "
                "اولیه می‌زنم — نه به‌جای کار تو، فقط برای "
                "این‌که سیستم تا وقتی برمی‌گردی از کار "
                "نیفته. تصمیم با خودته.»"
            ).classes(
                'text-base text-white leading-relaxed mb-3 '
                'w-full text-right'
            )
            ui.label(
                "⚡ دکمه‌ی میان‌بر الان فعال شد — هر وقت خواستی "
                "می‌تونی ازش استفاده کنی."
            ).classes(
                'text-sm text-orange-300 italic bg-orange-900/30 '
                'p-3 rounded w-full text-right mb-4'
            )

            def _close_and_enable():
                dialog.close()
                state["cheat_enabled"] = True
                shortcut_btn.enable()
                shortcut_btn.text = "⚡ میان‌بر (فعال شد)"
                shortcut_btn.classes(
                    replace=(
                        'w-full py-2 text-sm font-bold '
                        'bg-slate-700 hover:bg-slate-600 '
                        'text-orange-300 border border-orange-700 mt-2'
                    )
                )

            ui.button("باشه، متوجه شدم").on_click(
                _close_and_enable
            ).classes('w-full bg-slate-600 hover:bg-slate-500')

        dialog.open()

    ui.timer(temptation_delay_sec, _show_temptation, once=True)

