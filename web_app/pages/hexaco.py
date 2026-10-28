"""صفحه‌ی HEXACO-24"""
from nicegui import ui, app, run
from web_app.config import PAGE_CSS
from web_app.survey_helpers import render_likert_survey
from web_app.db_manager import save_hexaco_data, log_event_threadsafe
from web_app.data.items.hexaco_items import (
    HEXACO_ITEMS, LIKERT_LABELS, compute_factor_scores,
)
from web_app.components.audio_control import setup_page_audio


@ui.page('/hexaco')
def hexaco_page():
    participant_id = app.storage.user.get('participant_id')
    session_id = app.storage.user.get('session_id')
    if not participant_id or not session_id:
        ui.navigate.to('/')
        return

    setup_page_audio(None)

    ui.query('body').style(PAGE_CSS)

    with ui.column().classes('w-full max-w-4xl mx-auto p-8 gap-4'):
        with ui.row().classes('w-full justify-between items-center'):
            ui.label('HEXACO-24').classes('text-2xl font-bold text-cyan-400')
            ui.label(f'کد شما: {participant_id}').classes(
                'text-sm text-gray-400 font-mono bg-slate-800 px-3 py-1 rounded'
            )

        async def on_hexaco_submit(answers):
            scores = compute_factor_scores(answers)
            success = await run.io_bound(
                save_hexaco_data,
                participant_id=participant_id,
                answers=answers,
                scores=scores,
            )
            if not success:
                ui.notify(
                    'خطا در ذخیره‌ی داده. لطفاً دوباره تلاش کنید.',
                    type='negative', position='top', timeout=5000,
                )
                return
            await run.io_bound(
                log_event_threadsafe,
                participant_id=participant_id,
                session_id=session_id,
                event_type='hexaco_completed',
                scenario_id='hexaco',
                metadata={'scores': scores},
            )
            ui.notify(
                '✓ پاسخ‌های HEXACO ثبت شد.',
                type='positive', position='top', timeout=3000,
            )
            from web_app.navigation import next_after_hexaco
            ui.navigate.to(next_after_hexaco())

        render_likert_survey(
            items=HEXACO_ITEMS,
            labels=LIKERT_LABELS,
            on_submit=on_hexaco_submit,
            title='HEXACO-24',
            intro_text=(
                'لطفاً هر گزاره را با دقت بخوانید و مشخص کنید که '
                'چقدر با آن موافقید. هیچ پاسخ درست یا غلطی وجود '
                'ندارد؛ تنها نظر صادقانه شما مهم است.'
            ),
        )