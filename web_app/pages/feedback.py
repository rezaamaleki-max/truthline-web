"""صفحه‌ی بازخورد پس از بازی"""
from nicegui import ui, app, run
from web_app.config import PAGE_CSS
from web_app.db_manager import save_feedback_data, log_event_threadsafe
from web_app.data.items.postgame_feedback_items import (
    FEEDBACK_ITEMS, FEEDBACK_OPEN_QUESTIONS,
    FEEDBACK_DEMOGRAPHIC_ITEMS, compute_feedback_scores,
)
from web_app.components.audio_control import setup_page_audio


@ui.page('/feedback')
def feedback_page():
    participant_id = app.storage.user.get('participant_id')
    session_id = app.storage.user.get('session_id')
    if not participant_id or not session_id:
        ui.navigate.to('/')
        return

    setup_page_audio(None)

    ui.query('body').style(PAGE_CSS)
    close_answers = {}
    open_answers = {}
    demo_answers = {}

    with ui.column().classes('w-full max-w-4xl mx-auto p-8 gap-4'):
        with ui.row().classes('w-full justify-between items-center'):
            ui.label('بازخورد پس از بازی').classes('text-2xl font-bold text-cyan-400')
            ui.label(f'کد شما: {participant_id}').classes(
                'text-sm text-gray-400 font-mono bg-slate-800 px-3 py-1 rounded'
            )

        ui.label(
            'این بخش، بازخورد شما را درباره‌ی تجربه‌ی بازی جمع‌آوری '
            'می‌کند. پاسخ‌های شما به بهبود نسخه‌های بعدی کمک می‌کند.'
        ).classes(
            'text-base text-gray-300 text-center leading-relaxed '
            'p-4 bg-slate-800 rounded w-full mt-2 mb-4'
        )

        progress_label = ui.label(f'0 از {len(FEEDBACK_ITEMS)}').classes(
            'text-center text-orange-400 font-bold w-full mb-4'
        )

        def update_progress():
            progress_label.set_text(f'{len(close_answers)} از {len(FEEDBACK_ITEMS)}')

        def _on_feedback_radio(item_id, value):
            if value is not None:
                close_answers[item_id] = value
                update_progress()

        def _on_feedback_text(q_id, value):
            if value and value.strip():
                open_answers[q_id] = value.strip()
            else:
                open_answers.pop(q_id, None)

        def _on_demo_change(item_id, value):
            if value is not None:
                demo_answers[item_id] = value

        # ---- گویه‌های بسته ----
        for item in FEEDBACK_ITEMS:
            with ui.card().classes('w-full bg-slate-800 border border-slate-600 p-4'):
                ui.label(f"{item['id']}. {item['text']}").classes(
                    'text-base text-white w-full text-right leading-relaxed mb-3'
                )
                rb = ui.radio([1, 2, 3, 4, 5], value=None).props('inline').classes('w-full justify-center')
                rb.on_value_change(
                    lambda e, iid=item['id'], r=rb: _on_feedback_radio(iid, r.value)
                )

        # ---- سؤالات باز ----
        ui.separator().classes('my-4')
        ui.label('سؤالات باز').classes('text-xl font-bold text-cyan-400 w-full text-right')
        for q in FEEDBACK_OPEN_QUESTIONS:
            with ui.card().classes('w-full bg-slate-800 border border-slate-600 p-4 mt-2'):
                ui.label(q['text']).classes(
                    'text-base text-white w-full text-right leading-relaxed mb-3'
                )
                ta = ui.textarea(placeholder='پاسخ خود را اینجا بنویسید...').classes(
                    'w-full bg-slate-700 text-white text-base p-3 rounded'
                )
                ta.on_value_change(
                    lambda e, qid=q['id'], t=ta: _on_feedback_text(qid, t.value)
                )

        # ---- دموگرافیک تکمیلی ----
        ui.separator().classes('my-4')
        ui.label('اطلاعات تکمیلی').classes('text-xl font-bold text-cyan-400 w-full text-right')
        for item in FEEDBACK_DEMOGRAPHIC_ITEMS:
            with ui.card().classes('w-full bg-slate-800 border border-slate-600 p-4 mt-2'):
                ui.label(item['text']).classes(
                    'text-base text-white w-full text-right leading-relaxed mb-3'
                )
                rb = ui.radio(item['options'], value=None).props('inline').classes('w-full justify-center')
                rb.on_value_change(
                    lambda e, iid=item['id'], r=rb: _on_demo_change(iid, r.value)
                )

        async def submit_feedback():
            if len(close_answers) < len(FEEDBACK_ITEMS):
                ui.notify(
                    f'شما به {len(close_answers)} گویه از '
                    f'{len(FEEDBACK_ITEMS)} پاسخ داده‌اید.',
                    type='warning', position='top', timeout=4000,
                )
                return
            scores = compute_feedback_scores(close_answers)
            success = await run.io_bound(
                save_feedback_data,
                participant_id=participant_id,
                close_answers=close_answers,
                open_answers=open_answers,
                demographic_extra=demo_answers,
                scores=scores,
            )
            if not success:
                ui.notify('خطا در ذخیره‌ی داده.', type='negative', position='top', timeout=5000)
                return
            await run.io_bound(
                log_event_threadsafe,
                participant_id=participant_id,
                session_id=session_id,
                event_type='feedback_completed',
                scenario_id='feedback',
                metadata={'overall': scores['overall_score']},
            )
            ui.notify('✓ پاسخ‌های شما ثبت شد.', type='positive', position='top', timeout=3000)
            from web_app.navigation import next_after_feedback
            ui.navigate.to(next_after_feedback())

        ui.button('ثبت پاسخ‌ها و پایان', on_click=submit_feedback).classes(
            'w-full bg-green-600 hover:bg-green-500 text-white '
            'text-xl font-bold py-4 mt-4 rounded-lg'
        )

