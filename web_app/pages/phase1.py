"""صفحه‌ی فاز ۱ (بازی)"""
from nicegui import ui, app
from web_app.config import PAGE_CSS
from web_app.engine.scenario_runner import render_phase1
from web_app.components.audio_control import setup_page_audio


@ui.page('/phase1')
async def phase1_page():
    participant_id = app.storage.user.get('participant_id')
    session_id = app.storage.user.get('session_id')
    if not participant_id or not session_id:
        ui.navigate.to('/')
        return

    setup_page_audio("phase1")

    ui.query('body').style(PAGE_CSS)

    with ui.column().classes('w-full max-w-4xl mx-auto p-8 gap-4'):
        async def on_phase1_complete():
            from web_app.navigation import next_after_phase
            ui.notify(
                '✓ پایان فاز ۱. انتقال به شب اول...',
                type='positive', position='top', timeout=3000,
            )
            ui.navigate.to('/night/1')

        await render_phase1(participant_id, session_id, on_phase1_complete)