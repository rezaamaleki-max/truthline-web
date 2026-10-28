"""
نمایشگر دنباله‌ی دیالوگ با تصویر، عنوان، و زیرعنوان
(مشترک بین میان‌پرده و شب)

نسخه: 1.2.0 — رفع تکرار body_text در هر دیالوگ

تغییرات نسبت به 1.1.0:
- ساختار پایه (title, subtitle, image, body_text) فقط یک بار ساخته می‌شود.
- فقط ناحیه‌ی دیالوگ در هر گام عوض می‌شود (مثل الگوی دسکتاپ).
"""
from nicegui import ui

from web_app.character_utils import resolve_portrait_url


async def render_dialogue_viewer(
    dialogues: list,
    on_complete,
    image_path: str | None = None,
    title: str = "",
    subtitle: str = "",
    body_text: str = "",
):
    """
    رندر دنباله‌ی دیالوگ با تصویر اختیاری.

    ساختار پایه (title، subtitle، image، body_text) یک‌بار ساخته می‌شود.
    فقط ناحیه‌ی دیالوگ در هر گام عوض می‌شود — دقیقاً مثل دسکتاپ.
    """

    # ============================================================
    # ساختار پایه — یک‌بار ساخته می‌شود
    # ============================================================
    if title:
        ui.label(title).classes(
            'text-3xl font-bold text-cyan-400 '
            'text-center w-full'
        )
    if subtitle:
        ui.label(subtitle).classes(
            'text-xl text-orange-400 text-center w-full'
        )

    if image_path:
        with ui.card().classes(
            'w-full bg-slate-800 border-2 border-cyan-400 '
            'p-2 overflow-hidden'
        ):
            ui.image(image_path).classes(
                'w-full rounded object-cover'
            ).style('max-height: 320px;')

    if body_text:
        with ui.card().classes(
            'w-full bg-slate-800 border border-slate-600 '
            'p-4'
        ):
            ui.label(body_text).classes(
                'text-base text-gray-300 leading-relaxed '
                'w-full text-right whitespace-pre-line'
            )

    # ============================================================
    # ناحیه‌ی دیالوگ — فقط این بخش در هر گام عوض می‌شود
    # ============================================================
    dialogue_container = ui.column().classes('w-full gap-4')
    state = {"idx": 0}

    async def _render_dialogue():
        dialogue_container.clear()
        idx = state["idx"]

        if idx >= len(dialogues):
            await on_complete()
            return

        with dialogue_container:
            d = dialogues[idx]
            speaker = d.get("speaker", "")
            text = d.get("text", d.get("text_fa", ""))
            portrait_url = resolve_portrait_url(
                speaker, text, d.get("emotion")
            )

            with ui.card().classes(
                'w-full bg-slate-800 border-2 border-cyan-400 '
                'p-4'
            ):
                with ui.row().classes(
                    'items-start gap-4 w-full no-wrap'
                ):
                    # پرتره (سمت راست در RTL)
                    if portrait_url:
                        with ui.element('div').classes(
                            'flex-shrink-0'
                        ):
                            ui.image(portrait_url).style(
                                'width: 100px; '
                                'height: 130px; '
                                'border-radius: 10px; '
                                'border: 2px solid #4FC3F7; '
                                'object-fit: cover; '
                                'background: #0B1D3A;'
                            )

                    # محتوا
                    with ui.column().classes(
                        'flex-1 gap-2'
                    ):
                        with ui.row().classes(
                            'items-center '
                            'justify-between w-full'
                        ):
                            ui.label(
                                f"[{speaker}]"
                            ).classes(
                                'text-sm text-cyan-400 '
                                'font-bold'
                            )
                            ui.label(
                                f'{idx + 1} از '
                                f'{len(dialogues)}'
                            ).classes(
                                'text-xs text-gray-400 '
                                'font-mono'
                            )
                        ui.label(text).classes(
                            'text-base text-white '
                            'leading-relaxed w-full '
                            'text-right '
                            'whitespace-pre-line'
                        )

            is_last = (idx + 1 >= len(dialogues))
            btn_text = (
                'ادامه به مرحله بعد' if is_last else 'ادامه'
            )

            async def _next():
                state["idx"] += 1
                if state["idx"] >= len(dialogues):
                    await on_complete()
                else:
                    await _render_dialogue()

            ui.button(btn_text, on_click=_next).classes(
                'w-full py-3 text-lg font-bold '
                'bg-cyan-600 hover:bg-cyan-500 mt-4'
            )

    await _render_dialogue()