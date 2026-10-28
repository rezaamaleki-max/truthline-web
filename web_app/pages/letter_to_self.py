"""
صفحه‌ی نامه به خود
====================
- یک متن آزاد پیش از پایان مأموریت
- ذخیره در جدول web_self_letters
- در حالت TEST_MODE قابل پرش است

نسخه: 1.0.0
"""
from nicegui import ui, app, run

from web_app.config import PAGE_CSS, TEST_MODE
from web_app.db_manager import (
    save_self_letter, log_event_threadsafe,
)
from web_app.components.audio_control import setup_page_audio


@ui.page('/letter-to-self')
def letter_to_self_page():
    participant_id = app.storage.user.get('participant_id')
    session_id = app.storage.user.get('session_id')

    if not participant_id or not session_id:
        ui.navigate.to('/')
        return

    setup_page_audio(None)

    ui.query('body').style(PAGE_CSS)

    # ---- HUD ----
    from web_app.components.hud import render_hud
    # letter_to_self جزو GAME_STAGES نیست، پس HUD نمی‌گذاریم
    # یا می‌توانیم از مرحله‌ی قبلی استفاده کنیم
    # await render_hud(stage_key="phase4", sub_progress=1.0)

    # ---- container ----
    with ui.column().classes(
        'w-full max-w-3xl mx-auto p-8 gap-4'
    ):
        # سرصفحه
        with ui.row().classes(
            'w-full justify-between items-center'
        ):
            ui.label('نامه به خود').classes(
                'text-3xl font-bold text-cyan-400'
            )
            ui.label(
                f'کد شما: {participant_id}'
            ).classes(
                'text-sm text-gray-400 font-mono '
                'bg-slate-800 px-3 py-1 rounded'
            )

        # مقدمه
        ui.label(
            'پیش از دیدن نتایج نهایی، این لحظه فقط مال '
            'خودت است. اگر بخواهی به خودت، به آن کسی '
            'که در این چهار روز تصمیم گرفت، یک جمله '
            'بگویی، آن جمله چیست؟'
        ).classes(
            'text-base text-gray-300 text-center '
            'leading-relaxed p-4 bg-slate-800 rounded '
            'w-full mt-2 mb-4'
        )

        # textarea
        letter_input = ui.textarea(
            placeholder=(
                'اینجا بنویس... (اگر نمی‌خواهی، '
                'می‌توانی خالی بگذاری)'
            )
        ).classes('w-full text-base p-3 rounded').style(
            'min-height: 220px; font-family: Vazirmatn;'
        )

        # شمارنده
        counter_label = ui.label('۰ کلمه').classes(
            'text-xs text-gray-400 w-full text-right'
        )

        def _update_counter():
            text = letter_input.value or ''
            words = len(text.split()) if text.strip() else 0
            counter_label.set_text(f'{words} کلمه')

        letter_input.on_value_change(
            lambda e: _update_counter()
        )

        # ---- دکمه‌ها ----
        async def _save_and_continue():
            text = (letter_input.value or '').strip()
            try:
                await run.io_bound(
                    save_self_letter,
                    participant_id=participant_id,
                    content=text,
                )
            except Exception as e:
                print(f'⚠️ خطا در ذخیره‌ی نامه: {e}')

            try:
                await run.io_bound(
                    log_event_threadsafe,
                    participant_id=participant_id,
                    session_id=session_id,
                    event_type='letter_submitted',
                    scenario_id='letter_to_self',
                    metadata={
                        'word_count': (
                            len(text.split()) if text else 0
                        ),
                        'char_count': len(text),
                    },
                )
            except Exception as e:
                print(f'⚠️ خطا در لاگ: {e}')

            ui.notify(
                '✓ نامه ذخیره شد. انتقال به پرسشنامه‌ها...',
                type='positive', position='top', timeout=2500,
            )
            ui.navigate.to('/hexaco')

        async def _skip():
            try:
                await run.io_bound(
                    save_self_letter,
                    participant_id=participant_id,
                    content='',
                )
            except Exception as e:
                print(f'⚠️ خطا در ذخیره‌ی رد کردن: {e}')

            try:
                await run.io_bound(
                    log_event_threadsafe,
                    participant_id=participant_id,
                    session_id=session_id,
                    event_type='letter_skipped',
                    scenario_id='letter_to_self',
                    metadata={},
                )
            except Exception as e:
                print(f'⚠️ خطا در لاگ: {e}')

            ui.notify(
                'رد شد — ادامه به پرسشنامه‌ها',
                type='info', position='top', timeout=2000,
            )
            ui.navigate.to('/hexaco')

        with ui.row().classes('w-full gap-3 mt-2'):
            ui.button(
                'رد کردن', on_click=_skip,
            ).classes(
                'flex-1 bg-slate-700 hover:bg-slate-600 '
                'text-white text-base font-bold py-3 '
                'rounded-lg'
            )
            ui.button(
                'ذخیره و ادامه', on_click=_save_and_continue,
            ).classes(
                'flex-[2] bg-green-600 hover:bg-green-500 '
                'text-white text-base font-bold py-3 '
                'rounded-lg'
            )

