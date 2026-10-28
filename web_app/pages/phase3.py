"""صفحه‌ی فاز ۳ (روز سوم)"""
from nicegui import ui, app
from web_app.config import PAGE_CSS, PHASE_SCENARIOS, PHASE_TITLES
from web_app.engine.scenario_runner import render_phase
from web_app.components.audio_control import setup_page_audio


@ui.page('/phase3')
async def phase3_page():
    participant_id = app.storage.user.get('participant_id')
    session_id = app.storage.user.get('session_id')
    if not participant_id or not session_id:
        ui.navigate.to('/')
        return

    setup_page_audio("phase3")

    ui.query('body').style(PAGE_CSS)

    with ui.column().classes('w-full max-w-4xl mx-auto p-8 gap-4'):
        async def on_phase3_complete():
            ui.notify(
                '✓ پایان فاز ۳. انتقال به شب سوم...',
                type='positive', position='top', timeout=3000,
            )
            from web_app.navigation import next_after_phase
            ui.navigate.to(next_after_phase("phase3"))

        await render_phase(
            phase_key="phase3",
            scenarios_order=PHASE_SCENARIOS["phase3"],
            phase_title=PHASE_TITLES["phase3"],
            participant_id=participant_id,
            session_id=session_id,
            on_complete=on_phase3_complete,
        )