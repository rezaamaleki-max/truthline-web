"""صفحه‌ی مطلوبیت اجتماعی"""
from nicegui import ui, app, run
from web_app.config import PAGE_CSS
from web_app.db_manager import save_social_desirability_data, log_event_threadsafe
from web_app.data.items.social_desirability_items import SD_ITEMS, compute_sd_score
from web_app.components.audio_control import setup_page_audio


@ui.page('/sd')
def sd_page():
    participant_id = app.storage.user.get('participant_id')
    session_id = app.storage.user.get('session_id')
    if not participant_id or not session_id:
        ui.navigate.to('/')
        return

    setup_page_audio(None)

    ui.query('body').style(PAGE_CSS)
    answers = {}

    with ui.column().classes('w-full max-w-4xl mx-auto p-8 gap-4'):
        with ui.row().classes('w-full justify-between items-center'):
            ui.label('مطلوبیت اجتماعی').classes('text-2xl font-bold text-cyan-400')
            ui.label(f'کد شما: {participant_id}').classes(
                'text-sm text-gray-400 font-mono bg-slate-800 px-3 py-1 rounded'
            )

        ui.label(
            'با پاسخ گفتن به هر یک از ماده‌های زیر، درباره‌ی شخصیتتان '
            'پی ببرید. هر جمله را بخوانید و تعیین کنید که آیا در مورد '
            'شما درست است یا غلط.'
        ).classes(
            'text-base text-gray-300 text-center leading-relaxed '
            'p-4 bg-slate-800 rounded w-full mt-2 mb-4'
        )

        progress_label = ui.label(f'0 از {len(SD_ITEMS)}').classes(
            'text-center text-orange-400 font-bold w-full mb-4'
        )

        def update_progress():
            progress_label.set_text(f'{len(answers)} از {len(SD_ITEMS)}')

        def _on_sd_change(item_id, value):
            if value is not None:
                answers[item_id] = (value == 'درست')
                update_progress()

        for item in SD_ITEMS:
            with ui.card().classes('w-full bg-slate-800 border border-slate-600 p-4'):
                ui.label(f"{item['id']}. {item['text']}").classes(
                    'text-base text-white w-full text-right leading-relaxed mb-3'
                )
                rb = ui.radio(['درست', 'غلط'], value=None).props('inline').classes('w-full justify-center')
                rb.on_value_change(
                    lambda e, iid=item['id'], r=rb: _on_sd_change(iid, r.value)
                )

        async def submit_sd():
            if len(answers) < len(SD_ITEMS):
                ui.notify(
                    f'شما به {len(answers)} گویه از {len(SD_ITEMS)} '
                    f'پاسخ داده‌اید.',
                    type='warning', position='top', timeout=4000,
                )
                return
            result = compute_sd_score(answers)
            success = await run.io_bound(
                save_social_desirability_data,
                participant_id=participant_id,
                answers=answers,
                result=result,
            )
            if not success:
                ui.notify('خطا در ذخیره‌ی داده.', type='negative', position='top', timeout=5000)
                return
            await run.io_bound(
                log_event_threadsafe,
                participant_id=participant_id,
                session_id=session_id,
                event_type='sd_completed',
                scenario_id='sd',
                metadata={'score': result['score']},
            )
            ui.notify('✓ پاسخ‌ها ثبت شد.', type='positive', position='top', timeout=3000)
            from web_app.navigation import next_after_sd
            ui.navigate.to(next_after_sd())

        ui.button('ثبت پاسخ‌ها و ادامه', on_click=submit_sd).classes(
            'w-full bg-green-600 hover:bg-green-500 text-white '
            'text-xl font-bold py-4 mt-4 rounded-lg'
        )

