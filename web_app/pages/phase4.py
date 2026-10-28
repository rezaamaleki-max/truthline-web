"""صفحه‌ی فاز ۴ (روز چهارم)"""
from nicegui import ui, app
from web_app.config import (
    PAGE_CSS, PHASE_SCENARIOS, PHASE_TITLES,
)
from web_app.engine.scenario_runner import render_phase
from web_app.components.audio_control import setup_page_audio


@ui.page('/phase4')
async def phase4_page():
    participant_id = app.storage.user.get('participant_id')
    session_id = app.storage.user.get('session_id')
    if not participant_id or not session_id:
        ui.navigate.to('/')
        return

    setup_page_audio("phase4")

    ui.query('body').style(PAGE_CSS)

    with ui.column().classes(
        'w-full max-w-4xl mx-auto p-8 gap-4'
    ):
        async def on_phase4_complete():
            ui.notify(
                '✓ پایان فاز ۴. انتقال به نامه به خود...',
                type='positive', position='top',
                timeout=3000,
            )
            from web_app.navigation import next_after_phase
            ui.navigate.to(next_after_phase("phase4"))

        await render_phase(
            phase_key="phase4",
            scenarios_order=PHASE_SCENARIOS["phase4"],
            phase_title=PHASE_TITLES["phase4"],
            participant_id=participant_id,
            session_id=session_id,
            on_complete=on_phase4_complete,
        )