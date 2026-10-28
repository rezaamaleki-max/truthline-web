"""صفحه‌ی میان‌پرده — شامل epilogue"""
from nicegui import ui, app, run

from web_app.config import PAGE_CSS, get_interlude_next
from web_app.db_manager import (
    get_relationships_web,
    get_choice_memory,
    log_event_threadsafe,
)
from web_app.data.interludes import get_interlude
from web_app.data.epilogue import compute_epilogue
from web_app.components.dialogue_viewer import (
    render_dialogue_viewer,
)
from web_app.components.audio_control import setup_page_audio


@ui.page('/interlude/{day_key}')
async def interlude_page(day_key: str):
    participant_id = app.storage.user.get('participant_id')
    session_id = app.storage.user.get('session_id')
    if not participant_id or not session_id:
        ui.navigate.to('/')
        return

    setup_page_audio("interlude")

    ui.query('body').style(PAGE_CSS)

    # ---- بارگذاری روابط ----
    relationships = await run.io_bound(
        get_relationships_web, participant_id
    ) or {"li": 0, "rahimi": 0, "artemis": 0}

    # ---- محتوای میان‌پرده ----
    if day_key == "epilogue":
        choice_memory = await run.io_bound(
            get_choice_memory, participant_id
        ) or {}
        content = compute_epilogue(
            relationships, choice_memory
        )
    else:
        content = get_interlude(day_key, relationships)

    if not content:
        next_url = get_interlude_next(day_key)
        ui.navigate.to('/' + next_url)
        return

    # ---- ثبت رویداد ----
    await run.io_bound(
        log_event_threadsafe,
        participant_id=participant_id,
        session_id=session_id,
        event_type='interlude_started',
        scenario_id=f'interlude_{day_key}',
        metadata={'relationships': relationships},
    )

    # ---- HUD ----
    from web_app.components.hud import render_hud

    stage_key_map = {
        "day2": "interlude2",
        "day3": "interlude3",
        "day4": "interlude4",
        "epilogue": "epilogue",
    }
    await render_hud(
        stage_key=stage_key_map.get(day_key, ""),
        sub_progress=0.0,
    )

    container = ui.column().classes(
        'w-full max-w-4xl mx-auto p-8 gap-4'
    )

    async def go_to_next():
        from web_app.navigation import next_after_interlude
        ui.navigate.to(next_after_interlude(day_key))

    with container:
        await render_dialogue_viewer(
            dialogues=content.get("dialogues", []),
            on_complete=go_to_next,
            image_path=content.get("image"),
            title=content.get("title", ""),
            subtitle=content.get("subtitle", ""),
            body_text=content.get("body_text", ""),
        )