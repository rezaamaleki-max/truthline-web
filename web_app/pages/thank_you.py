"""صفحه‌ی تشکر"""
from nicegui import ui, app
from web_app.config import PAGE_CSS
from web_app.components.audio_control import setup_page_audio


@ui.page('/thank-you')
def thank_you_page():
    participant_id = app.storage.user.get('participant_id')
    setup_page_audio("menu")
    ui.query('body').style(PAGE_CSS)

    with ui.column().classes('w-full max-w-2xl mx-auto p-12 items-center gap-6'):
        ui.label('✓').classes('text-8xl text-green-400 mt-16')
        ui.label('از همکاری شما سپاسگزاریم').classes('text-3xl font-bold text-white')
        ui.label(
            'پاسخ‌های شما با موفقیت ثبت شد. می‌توانید این صفحه را ببندید.'
        ).classes('text-lg text-gray-400 text-center')
        if participant_id:
            ui.label(f'کد شرکت شما: {participant_id}').classes(
                'text-sm text-gray-500 font-mono mt-4'
            )
        ui.button(
            'شروع مجدد',
            on_click=lambda: (app.storage.user.clear(), ui.navigate.to('/')),
        ).classes(
            'bg-cyan-600 hover:bg-cyan-500 text-white '
            'text-lg font-bold py-3 px-8 mt-6 rounded'
        )