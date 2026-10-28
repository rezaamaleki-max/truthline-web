"""صفحه‌ی خوش‌آمد"""
from nicegui import ui, app
from web_app.config import PAGE_CSS
from web_app.db_manager import get_participant
from web_app.components.audio_control import setup_page_audio


@ui.page('/')
def index_page():
    # اگر کاربر قبلاً ثبت‌نام کرده، به فاز ۱ برود
    if app.storage.user.get('participant_id'):
        participant = get_participant(app.storage.user['participant_id'])
        if participant:
            ui.navigate.to('/phase1')
            return
        else:
            # ✅ کوکی منقضی است — پاک کن
            app.storage.user.clear()

    setup_page_audio("menu")

    ui.query('body').style(PAGE_CSS)

    with ui.column().classes('w-full max-w-3xl mx-auto p-12 items-center gap-6'):
        ui.label('TRUTHLINE').classes('text-6xl font-bold text-cyan-400 mt-16')
        ui.label('بحران ایستگاه کاسپین').classes('text-2xl text-white')
        ui.separator().classes('w-64 my-4')
        ui.label(
            'به پژوهش حاضر خوش آمدید. این یک بازی '
            'تصمیم‌گیری در محیطی شبیه‌سازی‌شده است. '
            'لطفاً با دقت و صداقت پاسخ دهید.'
        ).classes('text-lg text-gray-300 text-center max-w-xl leading-relaxed')

        with ui.card().classes('w-full bg-slate-800 border border-cyan-400 p-6 mt-6'):
            ui.label('📋 راهنما').classes('text-xl font-bold text-cyan-400 mb-3')
            with ui.column().classes('gap-2 text-gray-300'):
                ui.label('• مدت زمان تقریبی: ۳۰ تا ۴۵ دقیقه').classes('text-base')
                ui.label('• داده‌های شما به صورت محرمانه تحلیل می‌شود').classes('text-base')
                ui.label('• می‌توانید هر زمان که خواستید انصراف دهید').classes('text-base')

        ui.button(
            'شروع',
            on_click=lambda: ui.navigate.to('/demographic'),
        ).classes(
            'bg-cyan-600 hover:bg-cyan-500 text-white '
            'text-xl font-bold py-4 px-16 mt-6 rounded-lg'
        )