"""صفحه‌ی SD3"""
from nicegui import ui, app, run
from web_app.config import PAGE_CSS
from web_app.survey_helpers import render_likert_survey
from web_app.db_manager import save_sd3_data, log_event_threadsafe
from web_app.data.items.sd3_items import (
    SD3_ITEMS, SD3_LIKERT_LABELS, compute_sd3_scores,
)
from web_app.components.audio_control import setup_page_audio


@ui.page('/sd3')
def sd3_page():
    participant_id = app.storage.user.get('participant_id')
    session_id = app.storage.user.get('session_id')
    if not participant_id or not session_id:
        ui.navigate.to('/')
        return

    setup_page_audio(None)

    ui.query('body').style(PAGE_CSS)

    with ui.column().classes('w-full max-w-4xl mx-auto p-8 gap-4'):
        with ui.row().classes('w-full justify-between items-center'):
            ui.label('SD3 — مثلث تاریک').classes('text-2xl font-bold text-cyan-400')
            ui.label(f'کد شما: {participant_id}').classes(
                'text-sm text-gray-400 font-mono bg-slate-800 px-3 py-1 rounded'
            )

        async def on_sd3_submit(answers):
            scores = compute_sd3_scores(answers)
            success = await run.io_bound(
                save_sd3_data,
                participant_id=participant_id,
                answers=answers,
                scores=scores,
            )
            if not success:
                ui.notify('خطا در ذخیره‌ی داده.', type='negative', position='top', timeout=5000)
                return
            await run.io_bound(
                log_event_threadsafe,
                participant_id=participant_id,
                session_id=session_id,
                event_type='sd3_completed',
                scenario_id='sd3',
                metadata={'scores': scores},
            )
            ui.notify('✓ پاسخ‌های SD3 ثبت شد.', type='positive', position='top', timeout=3000)
            from web_app.navigation import next_after_sd3
            ui.navigate.to(next_after_sd3())

        render_likert_survey(
            items=SD3_ITEMS,
            labels=SD3_LIKERT_LABELS,
            on_submit=on_sd3_submit,
            title='SD3 — مثلث تاریک',
            intro_text=(
                'لطفاً مشخص کنید چقدر با هر یک از جملات زیر موافقید. '
                'پاسخ صادقانه شما بسیار مهم است.'
            ),
        )