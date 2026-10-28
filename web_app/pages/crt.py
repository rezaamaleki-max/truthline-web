"""صفحه‌ی CRT7"""
from nicegui import ui, app, run
from web_app.config import PAGE_CSS
from web_app.db_manager import save_crt_data, log_event_threadsafe
from web_app.data.items.crt_items import CRT_ITEMS, score_crt
from web_app.components.audio_control import setup_page_audio


@ui.page('/crt')
def crt_page():
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
            ui.label('CRT7 — تأمل شناختی').classes('text-2xl font-bold text-cyan-400')
            ui.label(f'کد شما: {participant_id}').classes(
                'text-sm text-gray-400 font-mono bg-slate-800 px-3 py-1 rounded'
            )

        ui.label(
            'این بخش شامل ۷ سؤال کوتاه است. لطفاً با دقت بخوانید و '
            'پاسخ خود را در کادر مقابل بنویسید.'
        ).classes(
            'text-base text-gray-300 text-center leading-relaxed '
            'p-4 bg-slate-800 rounded w-full mt-2 mb-4'
        )

        progress_label = ui.label(f'0 از {len(CRT_ITEMS)}').classes(
            'text-center text-orange-400 font-bold w-full mb-4'
        )

        def update_progress():
            progress_label.set_text(f'{len(answers)} از {len(CRT_ITEMS)}')

        def _on_crt_numeric(item_id, value):
            if value and value.strip():
                answers[item_id] = value.strip()
            else:
                answers.pop(item_id, None)
            update_progress()

        def _on_crt_choice(item_id, value):
            if value is not None:
                answers[item_id] = value
                update_progress()

        for item in CRT_ITEMS:
            with ui.card().classes('w-full bg-slate-800 border border-slate-600 p-4'):
                ui.label(f"{item['id']}. {item['text']}").classes(
                    'text-base text-white w-full text-right leading-relaxed mb-3'
                )
                if item['type'] == 'numeric':
                    inp = ui.input(placeholder='پاسخ عددی...').classes(
                        'w-full bg-slate-700 text-white text-lg p-3 rounded'
                    )
                    inp.on_value_change(
                        lambda e, iid=item['id'], i=inp: _on_crt_numeric(iid, i.value)
                    )
                else:
                    opts = [o[1] for o in item['options']]
                    rb = ui.radio(opts, value=None).props('inline').classes('w-full justify-center')
                    rb.on_value_change(
                        lambda e, iid=item['id'], r=rb: _on_crt_choice(iid, r.value)
                    )

        async def submit_crt():
            if len(answers) < len(CRT_ITEMS):
                ui.notify(
                    f'شما به {len(answers)} سؤال از {len(CRT_ITEMS)} '
                    f'پاسخ داده‌اید.',
                    type='warning', position='top', timeout=4000,
                )
                return
            result = score_crt(answers)
            success = await run.io_bound(
                save_crt_data,
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
                event_type='crt_completed',
                scenario_id='crt',
                metadata={'score': result['score']},
            )
            ui.notify('✓ پاسخ‌های CRT ثبت شد.', type='positive', position='top', timeout=3000)
            # ✅ حالا به آزمون برج هانوی
            from web_app.navigation import next_after_crt
            ui.navigate.to(next_after_crt())

        ui.button('ثبت پاسخ‌ها و ادامه', on_click=submit_crt).classes(
            'w-full bg-green-600 hover:bg-green-500 text-white '
            'text-xl font-bold py-4 mt-4 rounded-lg'
        )

