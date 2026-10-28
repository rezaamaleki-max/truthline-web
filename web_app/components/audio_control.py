"""
ویجت کنترل صدا — نسخه‌ی شناور (موبایل‌پسند)
==========================================
- فقط یک آیکون کوچک شناور در گوشه
- با کلیک، پنل باز می‌شود
"""
from nicegui import ui, app
from web_app.audio import (
    get_audio_enabled, get_audio_volume,
    set_audio_enabled, set_audio_volume,
)

MUSIC_NAMES = {
    "menu": "منوی اصلی", "intro": "مقدمه", "interlude": "میان‌پرده",
    "night": "شب ایستگاه", "phase1": "روز اول", "phase2": "روز دوم",
    "phase3": "روز سوم", "phase4": "روز چهارم", "council": "شورا",
    "results": "نتایج",
}

def render_audio_control():
    enabled = get_audio_enabled()
    volume = get_audio_volume()
    current_key = str(app.storage.user.get("audio_current_key") or "")
    current_name = MUSIC_NAMES.get(current_key, "سکوت")

    # پنل بازشو
    with ui.dialog() as dialog, ui.card().classes(
        'bg-slate-900 border border-cyan-500 p-4 w-64'
    ).style('direction: rtl; font-family: Vazirmatn;'):
        with ui.row().classes('items-center gap-2 w-full no-wrap'):
            mute_btn = ui.button('🔊' if enabled else '🔇').props('flat dense')
            vol_slider = ui.slider(min=0, max=100, value=int(volume * 100)).classes('flex-1').props('dense')
            vol_label = ui.label(f'{int(volume * 100)}%').classes('text-xs text-cyan-400 font-mono')
        
        ui.label(f'🎵 {current_name}').classes('text-xs text-gray-400 mt-2 w-full text-right')

        def _toggle_mute():
            new_val = not get_audio_enabled()
            set_audio_enabled(new_val)
            mute_btn.set_text('🔊' if new_val else '🔇')

        def _on_volume():
            val = int(vol_slider.value or 0)
            set_audio_volume(val / 100.0)
            vol_label.set_text(f'{val}%')

        mute_btn.on_click(_toggle_mute)
        vol_slider.on_value_change(_on_volume)

    # دکمه‌ی شناور کوچک
    ui.button(icon='volume_up', on_click=dialog.open).props(
        'round dense'
    ).classes(
        'fixed bottom-4 left-4 z-[1000] bg-slate-900 text-cyan-400 '
        'border border-cyan-500 shadow-lg'
    ).style('width: 44px; height: 44px;')


def setup_page_audio(music_key: str | None, show_control: bool = True):
    from web_app.audio import init_page_music
    init_page_music(music_key)
    if show_control:
        render_audio_control()