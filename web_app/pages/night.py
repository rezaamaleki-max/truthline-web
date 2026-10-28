"""صفحه‌ی شب ایستگاه"""
from nicegui import ui, app, run

from web_app.config import (
    PAGE_CSS, NIGHT_NEXT, load_night_data,
)
from web_app.db_manager import (
    update_relationship_web, log_event_threadsafe,
    get_relationships_web,
)
from web_app.components.dialogue_viewer import (
    render_dialogue_viewer,
)
from web_app.components.audio_control import setup_page_audio


@ui.page('/night/{night_num}')
async def night_page(night_num: str):
    participant_id = app.storage.user.get('participant_id')
    session_id = app.storage.user.get('session_id')
    if not participant_id or not session_id:
        ui.navigate.to('/')
        return

    setup_page_audio("night")

    ui.query('body').style(PAGE_CSS)

    # ---- HUD ----
    from web_app.components.hud import render_hud
    await render_hud(
        stage_key=f"night{night_num}",
        sub_progress=0.0,
    )

    night_data = load_night_data(night_num)
    if not night_data:
        # داده‌ی این شب نبود — مستقیم برو به بعدی
        from web_app.navigation import next_after_night
        ui.navigate.to(next_after_night(int(night_num)))
        return

    container = ui.column().classes(
        'w-full max-w-4xl mx-auto p-8 gap-4'
    )

    async def go_to_next():
        from web_app.navigation import next_after_night
        ui.navigate.to(next_after_night(int(night_num)))

    async def render_choices():
        container.clear()
        with container:
            # ---- هدر ----
            ui.label(night_data.get("title", "")).classes(
                'text-3xl font-bold text-cyan-400 '
                'text-center w-full'
            )
            ui.label(night_data.get("subtitle", "")).classes(
                'text-xl text-orange-400 text-center w-full'
            )

            # ---- مقدمه ----
            if night_data.get("intro"):
                with ui.card().classes(
                    'w-full bg-slate-800 border border-slate-600 '
                    'p-4 mt-2'
                ):
                    ui.label(
                        night_data["intro"]
                    ).classes(
                        'text-base text-gray-300 leading-relaxed '
                        'w-full text-right whitespace-pre-line'
                    )

            # ---- دستور ----
            ui.label(
                "این شب را چطور می‌گذرانی؟"
            ).classes(
                'text-lg font-bold text-white w-full text-right mt-4'
            )

            # ---- فعالیت‌ها ----
            activities = night_data.get("activities", {})
            order = ["li", "artemis", "stars"]

            for key in order:
                activity = activities.get(key)
                if not activity:
                    continue

                async def _pick(k=key):
                    await on_activity_chosen(k)

                with ui.card().classes(
                    'w-full bg-slate-700 hover:bg-slate-600 '
                    'border-2 border-slate-500 cursor-pointer p-4 mt-2'
                ).on('click', _pick):
                    with ui.column().classes('gap-1 w-full'):
                        ui.label(
                            activity.get("label", key)
                        ).classes(
                            'text-base text-white font-bold '
                            'w-full text-right'
                        )
                        if activity.get("hint"):
                            ui.label(
                                activity["hint"]
                            ).classes(
                                'text-sm text-gray-400 italic '
                                'w-full text-right'
                            )

    async def on_activity_chosen(activity_key: str):
        activity = night_data.get("activities", {}).get(
            activity_key
        )
        if not activity:
            return

        # ✅ صدای انتخاب
        from web_app.audio import play_choice_sfx
        play_choice_sfx()

        # ---- اعمال اثر بر روابط ----
        effect = activity.get("effect", {}) or {}
        for char, delta in effect.items():
            await run.io_bound(
                update_relationship_web,
                participant_id=participant_id,
                character_key=char,
                delta=int(delta),
            )

        # ---- ثبت رویداد ----
        await run.io_bound(
            log_event_threadsafe,
            participant_id=participant_id,
            session_id=session_id,
            event_type='night_activity_chosen',
            scenario_id=f'night_{night_num}',
            metadata={
                'activity': activity_key,
                'effect': effect,
            },
        )

        # ---- نمایش دیالوگ‌های فعالیت ----
        container.clear()
        with container:
            await render_dialogue_viewer(
                dialogues=activity.get("dialogues", []),
                on_complete=go_to_next,
                title=night_data.get("title", ""),
                subtitle=night_data.get("subtitle", ""),
            )

    await render_choices()