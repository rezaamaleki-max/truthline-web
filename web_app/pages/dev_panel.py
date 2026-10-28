"""
پنل توسعه‌دهنده — فقط در TEST_MODE فعال است
=============================================
امکان پرش سریع به هر بخش، بدون نیاز به تکمیل فرم‌ها.
"""
import uuid
from nicegui import ui, app
from web_app.config import (
    PAGE_CSS, TEST_MODE, TEST_PARTICIPANT_PREFIX,
)
from web_app.db_manager import get_participant, create_participant
from web_app.components.audio_control import setup_page_audio


def _get_or_create_test_participant() -> tuple[str, str] | None:
    """ایجاد یا استفاده‌ی مجدد از شرکت‌کننده‌ی تست"""
    pid = app.storage.user.get('participant_id')
    session_id = app.storage.user.get('session_id')

    if pid and pid.startswith(TEST_PARTICIPANT_PREFIX) and session_id:
        if get_participant(pid):
            return pid, session_id

    new_pid = f"{TEST_PARTICIPANT_PREFIX}{str(uuid.uuid4())[:8]}"
    new_session = str(uuid.uuid4())[:12]
    success = create_participant(
        participant_id=new_pid,
        session_id=new_session,
        demographic_data={
            'age': 25,
            'gender': 'زن',
            'education': 'کارشناسی',
            'field_of_study': 'مهندسی',
            'work_experience': 'بدون سابقه کار',
            'gaming_experience': 'متوسط',
            'technical_familiarity': 'متوسط',
            'consent': True,
        },
    )
    if not success:
        return None

    app.storage.user['participant_id'] = new_pid
    app.storage.user['session_id'] = new_session
    return new_pid, new_session


@ui.page('/dev')
def dev_panel():
    if not TEST_MODE:
        ui.navigate.to('/')
        return

    setup_page_audio("menu")

    ui.query('body').style(PAGE_CSS)

    with ui.column().classes('w-full max-w-3xl mx-auto p-8 gap-4'):
        ui.label('🧪 پنل توسعه‌دهنده').classes(
            'text-3xl font-bold text-orange-400 text-center'
        )
        ui.label(
            'این پنل فقط در حالت TEST_MODE فعال است. '
            'برای غیرفعال کردن در محیط واقعی، '
            'TEST_MODE را در config.py روی False بگذارید.'
        ).classes('text-sm text-gray-400 text-center mb-4')

        # ---- نمایش وضعیت فعلی ----
        current_pid = app.storage.user.get('participant_id', '—')
        with ui.card().classes('w-full bg-slate-800 p-3'):
            ui.label('وضعیت فعلی:').classes('text-sm text-gray-400')
            ui.label(f'شناسه: {current_pid}').classes(
                'text-base font-mono text-cyan-400'
            )
            if current_pid and current_pid.startswith(TEST_PARTICIPANT_PREFIX):
                ui.label('✓ شرکت‌کننده‌ی تست').classes(
                    'text-xs text-green-400'
                )

        # ---- دکمه‌های پرش سریع ----
        def jump_to(path: str):
            result = _get_or_create_test_participant()
            if not result:
                ui.notify(
                    'خطا در ساخت شرکت‌کننده‌ی تست',
                    type='negative', position='top',
                )
                return
            ui.navigate.to(path)

        # ============================================================
        # بخش ۱: شروع و دموگرافیک
        # ============================================================
        ui.label('شروع:').classes(
            'text-lg font-bold text-white mt-4 mb-2'
        )
        with ui.grid(columns=2).classes('w-full gap-2'):
            ui.button(
                'شروع از اول (خوش‌آمد)',
                on_click=lambda: (
                    app.storage.user.clear(),
                    ui.navigate.to('/'),
                ),
            ).classes('bg-slate-600 hover:bg-slate-500 text-white p-4')
            ui.button(
                'دموگرافیک',
                on_click=lambda: jump_to('/demographic'),
            ).classes('bg-slate-600 hover:bg-slate-500 text-white p-4')
            ui.button(
                '🎬 مقدمه (intro)',
                on_click=lambda: jump_to('/intro'),
            ).classes(
                'bg-purple-600 hover:bg-purple-500 text-white '
                'p-4 font-bold'
            )

        # ============================================================
        # بخش ۲: فازهای بازی
        # ============================================================
        ui.label('فازهای بازی:').classes(
            'text-lg font-bold text-white mt-4 mb-2'
        )
        with ui.grid(columns=2).classes('w-full gap-2'):
            ui.button(
                'فاز ۱ — صداقت',
                on_click=lambda: jump_to('/phase1'),
            ).classes('bg-cyan-600 hover:bg-cyan-500 text-white p-4')
            ui.button(
                'فاز ۲ — قابلیت اعتماد',
                on_click=lambda: jump_to('/phase2'),
            ).classes('bg-cyan-600 hover:bg-cyan-500 text-white p-4')
            ui.button(
                'فاز ۳ — حل مسئله',
                on_click=lambda: jump_to('/phase3'),
            ).classes('bg-cyan-600 hover:bg-cyan-500 text-white p-4')
            ui.button(
                'فاز ۴ — مسئولیت‌پذیری',
                on_click=lambda: jump_to('/phase4'),
            ).classes('bg-cyan-600 hover:bg-cyan-500 text-white p-4')

        # ============================================================
        # بخش ۳: شب‌ها و میان‌پرده‌ها
        # ============================================================
        ui.label('شب‌ها و میان‌پرده‌ها:').classes(
            'text-lg font-bold text-white mt-4 mb-2'
        )
        with ui.grid(columns=3).classes('w-full gap-2'):
            ui.button(
                'شب ۱',
                on_click=lambda: jump_to('/night/1'),
            ).classes('bg-purple-600 hover:bg-purple-500 text-white p-3')
            ui.button(
                'شب ۲',
                on_click=lambda: jump_to('/night/2'),
            ).classes('bg-purple-600 hover:bg-purple-500 text-white p-3')
            ui.button(
                'شب ۳',
                on_click=lambda: jump_to('/night/3'),
            ).classes('bg-purple-600 hover:bg-purple-500 text-white p-3')
            ui.button(
                'میان‌پرده روز ۲',
                on_click=lambda: jump_to('/interlude/day2'),
            ).classes('bg-purple-600 hover:bg-purple-500 text-white p-3')
            ui.button(
                'میان‌پرده روز ۳',
                on_click=lambda: jump_to('/interlude/day3'),
            ).classes('bg-purple-600 hover:bg-purple-500 text-white p-3')
            ui.button(
                'میان‌پرده روز ۴',
                on_click=lambda: jump_to('/interlude/day4'),
            ).classes('bg-purple-600 hover:bg-purple-500 text-white p-3')

        # ============================================================
        # بخش ۴: پرسشنامه‌ها
        # ============================================================
        ui.label('پرسشنامه‌ها:').classes(
            'text-lg font-bold text-white mt-4 mb-2'
        )
        with ui.grid(columns=2).classes('w-full gap-2'):
            ui.button(
                'HEXACO-24',
                on_click=lambda: jump_to('/hexaco'),
            ).classes('bg-cyan-600 hover:bg-cyan-500 text-white p-4')
            ui.button(
                'CRT7',
                on_click=lambda: jump_to('/crt'),
            ).classes('bg-cyan-600 hover:bg-cyan-500 text-white p-4')

            ui.button(
                '🗼 برج هانوی',
                on_click=lambda: jump_to('/tower-of-hanoi'),
            ).classes(
                'bg-purple-600 hover:bg-purple-500 '
                'text-white p-4 font-bold'
            )

            ui.button(
                'SD3 (مثلث تاریک)',
                on_click=lambda: jump_to('/sd3'),
            ).classes('bg-cyan-600 hover:bg-cyan-500 text-white p-4')
            ui.button(
                'SD (مطلوبیت اجتماعی)',
                on_click=lambda: jump_to('/sd'),
            ).classes('bg-cyan-600 hover:bg-cyan-500 text-white p-4')
            ui.button(
                'بازخورد پس از بازی',
                on_click=lambda: jump_to('/feedback'),
            ).classes('bg-cyan-600 hover:bg-cyan-500 text-white p-4')

        # ============================================================
        # بخش ۵: اختتامیه و نتایج
        # ============================================================
        ui.label('اختتامیه و نتایج:').classes(
            'text-lg font-bold text-white mt-4 mb-2'
        )
        with ui.grid(columns=2).classes('w-full gap-2'):
            ui.button(
                '🎬 اختتامیه (epilogue)',
                on_click=lambda: jump_to('/interlude/epilogue'),
            ).classes(
                'bg-amber-600 hover:bg-amber-500 text-white '
                'p-4 font-bold'
            )
            ui.button(
                '📊 نتایج نهایی',
                on_click=lambda: jump_to('/results'),
            ).classes(
                'bg-amber-600 hover:bg-amber-500 text-white '
                'p-4 font-bold'
            )
            ui.button(
                '✅ صفحه‌ی تشکر',
                on_click=lambda: jump_to('/thank-you'),
            ).classes('bg-green-600 hover:bg-green-500 text-white p-4')
            ui.button(
                '✉️ نامه به خود',
                on_click=lambda: jump_to('/letter-to-self'),
            ).classes(
                'bg-cyan-600 hover:bg-cyan-500 text-white '
                'p-4 font-bold'
            )

        ui.separator().classes('my-4')

        # ============================================================
        # ابزارهای دیگر
        # ============================================================
        ui.label('ابزارهای دیگر:').classes(
            'text-lg font-bold text-white mb-2'
        )

        def reset_state():
            app.storage.user.clear()
            ui.notify(
                'وضعیت پاک شد', type='positive', position='top'
            )

        ui.button(
            'پاک کردن وضعیت جلسه',
            on_click=reset_state,
        ).classes('bg-red-600 hover:bg-red-500 text-white p-3')

        # ============================================================
        # راهنما
        # ============================================================
        with ui.card().classes('w-full bg-slate-800 p-4 mt-4'):
            ui.label('💡 راهنما:').classes(
                'text-sm text-cyan-400 font-bold mb-2'
            )
            ui.label(
                '• شرکت‌کننده‌ی تست به‌طور خودکار با پیشوند TEST_ '
                'ساخته می‌شود تا در داده‌های نهایی قابل تفکیک باشد.'
            ).classes('text-xs text-gray-400')
            ui.label(
                '• دکمه‌ی «شروع از اول» وضعیت جلسه را پاک می‌کند '
                'و از صفحه‌ی خوش‌آمد شروع می‌کند.'
            ).classes('text-xs text-gray-400')
            ui.label(
                '• هر بار که از این پنل استفاده می‌کنید، '
                'همان شرکت‌کننده‌ی تست قبلی استفاده می‌شود '
                '(تا زمانی که وضعیت پاک نشود).'
            ).classes('text-xs text-gray-400')
            ui.label(
                '• «اختتامیه» را می‌توانید مستقیماً باز کنید، '
                'ولی برای دیدن نتایج معنادار، ابتدا باید '
                'چند فاز را بازی کنید تا شواهد ثبت شوند.'
            ).classes('text-xs text-gray-400')