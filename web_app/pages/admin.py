"""
پنل ادمین — کنترل تنظیمات مطالعه (با رمز)
"""
from nicegui import ui, app

from web_app.config import PAGE_CSS
from web_app.admin_config import (
    load_admin_config,
    save_admin_config,
    get_admin_password,
)


@ui.page('/admin')
def admin_page():
    ui.query('body').style(PAGE_CSS)
    state = {"authenticated": False}

    container = ui.column().classes(
        'w-full max-w-3xl mx-auto p-8 gap-4'
    )

    def _render_login():
        container.clear()
        with container:
            ui.label("🔒 پنل ادمین").classes(
                'text-3xl font-bold text-cyan-400 '
                'text-center w-full mt-16'
            )
            ui.label(
                "برای دسترسی، رمز عبور را وارد کنید."
            ).classes(
                'text-sm text-gray-400 text-center w-full mb-4'
            )
            pwd = ui.input(
                placeholder="رمز عبور",
                password=True,
                password_toggle_button=True,
            ).classes('w-full text-lg p-3')

            def _login():
                if pwd.value == get_admin_password():
                    state["authenticated"] = True
                    _render_panel()
                else:
                    ui.notify(
                        "رمز عبور نادرست است",
                        type='negative', position='top',
                    )

            ui.button(
                "ورود", on_click=_login,
            ).classes(
                'w-full py-3 text-lg font-bold '
                'bg-cyan-600 hover:bg-cyan-500'
            )
            pwd.on('keydown.enter', _login)

    def _render_panel():
        container.clear()
        with container:
            # هدر
            with ui.row().classes(
                'w-full items-center justify-between'
            ):
                ui.label("⚙️ پنل کنترل مطالعه").classes(
                    'text-2xl font-bold text-cyan-400'
                )
                ui.button(
                    "🚪 خروج", on_click=_render_login,
                ).classes(
                    'bg-red-600 hover:bg-red-500 text-sm'
                )

            cfg = load_admin_config()

            # ============ بخش ۱: فازها ============
            with ui.card().classes(
                'w-full bg-slate-800 border border-cyan-400 p-4'
            ):
                ui.label("📅 فازها (روزهای اصلی)").classes(
                    'text-lg font-bold text-cyan-300 mb-3'
                )
                phase_boxes = {}
                phase_labels = {
                    "phase1": "روز اول — سکوت",
                    "phase2": "روز دوم — سایه‌ها",
                    "phase3": "روز سوم — معمای داده‌ها",
                    "phase4": "روز چهارم — شورا",
                }
                for key, label in phase_labels.items():
                    phase_boxes[key] = ui.checkbox(
                        label,
                        value=cfg["phases"].get(key, True),
                    ).classes('text-base text-white')

            # ============ بخش ۲: بخش‌های روایی ============
            with ui.card().classes(
                'w-full bg-slate-800 border border-orange-400 p-4'
            ):
                ui.label("🎬 بخش‌های روایی").classes(
                    'text-lg font-bold text-orange-300 mb-3'
                )
                section_boxes = {}
                section_labels = {
                    "prologue": "پرولوگ در مقدمه",
                    "interludes": "میان‌پرده‌ها",
                    "nights": "شب‌های ایستگاه",
                    "letter_to_self": "نامه به خود",
                    "epilogue": "پایان روایی (Epilogue)",
                }
                for key, label in section_labels.items():
                    section_boxes[key] = ui.checkbox(
                        label,
                        value=cfg["sections"].get(key, True),
                    ).classes('text-base text-white')

            # ============ بخش ۳: پرسشنامه‌ها ============
            with ui.card().classes(
                'w-full bg-slate-800 border border-purple-400 p-4'
            ):
                ui.label("📝 پرسشنامه‌ها و آزمون‌ها").classes(
                    'text-lg font-bold text-purple-300 mb-3'
                )
                q_boxes = {}
                q_labels = {
                    "hexaco": "HEXACO-24",
                    "crt": "CRT7 (تأمل شناختی)",
                    "tower_of_hanoi": "برج هانوی (تطبیقی)",
                    "sd3": "SD3 (مثلث تاریک)",
                    "sd": "SD (مطلوبیت اجتماعی)",
                    "feedback": "بازخورد پس از بازی",
                }
                for key, label in q_labels.items():
                    q_boxes[key] = ui.checkbox(
                        label,
                        value=cfg["questionnaires"].get(key, True),
                    ).classes('text-base text-white')

            # ============ بخش ۴: رمز عبور ============
            with ui.card().classes(
                'w-full bg-slate-800 border border-red-400 p-4'
            ):
                ui.label("🔐 تغییر رمز عبور").classes(
                    'text-lg font-bold text-red-300 mb-3'
                )
                new_pwd = ui.input(
                    label="رمز جدید (حداقل ۸ کاراکتر)",
                    password=True,
                    value="",
                ).classes('w-full')

            # ============ بخش ۴: مسیریابی سفارشی ============
            with ui.card().classes(
                'w-full bg-slate-800 border border-green-400 p-4'
            ):
                ui.label("🗺️ مسیریابی سفارشی (Flow)").classes(
                    'text-lg font-bold text-green-300 mb-1'
                )
                ui.label(
                    "برای تغییر ترتیب، کلید مرحله‌ی فعلی و آدرس مقصد را وارد کنید. "
                    "(مثال: phase1 -> /hexaco). اگر خالی باشد، حالت پیش‌فرض اجرا می‌شود."
                ).classes('text-xs text-gray-400 mb-3')
                
                routing_container = ui.column().classes('w-full gap-2')
                current_routing = cfg.get("routing", {})
                
                routing_inputs = {}
                for k, v in current_routing.items():
                    with ui.row().classes('w-full gap-2 no-wrap'):
                        ui.label(k).classes('w-1/3 text-white font-mono text-sm mt-2')
                        routing_inputs[k] = ui.input(value=v).classes('flex-1')
                
                # افزودن ردیف جدید
                with ui.row().classes('w-full gap-2 no-wrap mt-2'):
                    new_key = ui.input(placeholder="کلید (مثلا phase1)").classes('w-1/3')
                    new_val = ui.input(placeholder="مقصد (مثلا /hexaco)").classes('flex-1')
                    
                    def _add_route():
                        if new_key.value and new_val.value:
                            routing_inputs[new_key.value] = ui.input(value=new_val.value).classes('flex-1')
                            # رسم مجدد پنل
                            _render_panel()
                    
                    ui.button("+", on_click=_add_route).classes('bg-green-600')

            # ============ ذخیره ============
            def _save():
                new_cfg = load_admin_config()
                new_cfg["phases"] = {
                    k: b.value for k, b in phase_boxes.items()
                }
                new_cfg["sections"] = {
                    k: b.value for k, b in section_boxes.items()
                }
                new_cfg["questionnaires"] = {
                    k: b.value for k, b in q_boxes.items()
                }
                if new_pwd.value and len(new_pwd.value) >= 8:
                    new_cfg["admin_password"] = new_pwd.value
                save_admin_config(new_cfg)
                ui.notify(
                    "✓ تنظیمات ذخیره شد",
                    type='positive', position='top',
                )
                # ✅ ذخیره مسیریابی
                new_routing = {}
                for k, inp in routing_inputs.items():
                    if inp.value:
                        new_routing[k] = inp.value
                new_cfg["routing"] = new_routing


            def _reset_defaults():
                from web_app.admin_config import DEFAULT_CONFIG
                save_admin_config(dict(DEFAULT_CONFIG))
                ui.notify(
                    "✓ به حالت پیش‌فرض بازگشت",
                    type='positive', position='top',
                )
                _render_panel()

            with ui.row().classes('w-full gap-2 mt-4'):
                ui.button(
                    "💾 ذخیره تنظیمات", on_click=_save,
                ).classes(
                    'flex-2 py-3 text-lg font-bold '
                    'bg-green-600 hover:bg-green-500'
                )
                ui.button(
                    "↺ پیش‌فرض", on_click=_reset_defaults,
                ).classes(
                    'flex-1 py-3 bg-slate-700 hover:bg-slate-600'
                )

            # هشدار
            ui.label(
                "⚠️ توجه: تغییر تنظیمات روی شرکت‌کنندگان فعال اثر "
                "نمی‌گذارد؛ فقط جلسات جدید از این تنظیمات استفاده "
                "می‌کنند."
            ).classes(
                'text-xs text-yellow-300 italic w-full '
                'text-right mt-2'
            )

    _render_login()