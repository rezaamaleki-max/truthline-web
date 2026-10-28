"""
توابع کمکی مشترک برای ساخت پرسشنامه‌ها در NiceGUI
====================================================
این توابع، الگوی تکرارشونده‌ی ساخت پرسشنامه‌های Likert را
یک‌بار برای همیشه حل می‌کنند تا در `app.py` فقط یک خط
برای هر پرسشنامه لازم باشد.
"""
from nicegui import ui


def render_likert_survey(
    items: list,
    labels: dict,
    on_submit,
    title: str = "",
    intro_text: str = "",
    scale_values: list | None = None,
) -> None:
    """
    رندر یک پرسشنامه‌ی Likert کامل.

    Args:
        items: لیست سؤالات [{"id": int, "text": str}, ...]
        labels: دیکشنری برچسب‌ها {1: "کاملاً مخالفم", ...}
        on_submit: تابع async که در پایان با answers صدا زده می‌شود
        title: عنوان پرسشنامه
        intro_text: توضیح مقدماتی
        scale_values: مقادیر Likert (پیش‌فرض: کلیدهای labels)
    """
    if scale_values is None:
        scale_values = list(labels.keys())

    # ✅ پاسخ‌ها در این دیکشنری جمع می‌شوند
    answers: dict = {}

    # ---- عنوان ----
    if title:
        ui.label(title).classes(
            'text-2xl font-bold text-cyan-400 text-center w-full'
        )

    # ---- توضیح ----
    if intro_text:
        ui.label(intro_text).classes(
            'text-base text-gray-300 text-center leading-relaxed '
            'p-4 bg-slate-800 rounded w-full mt-2 mb-4'
        )

    # ---- راهنمای مقیاس ----
    with ui.row().classes(
        'w-full justify-center gap-2 p-3 '
        'bg-slate-800 rounded flex-wrap mb-4'
    ):
        for val in scale_values:
            label_text = labels.get(val, str(val))
            ui.label(f'{val} = {label_text}').classes(
                'text-xs text-white bg-slate-700 px-2 py-1 rounded'
            )

    # ---- نوار پیشرفت ----
    progress_label = ui.label(
        f'0 از {len(items)}'
    ).classes('text-center text-orange-400 font-bold w-full mb-4')

    def update_progress():
        progress_label.set_text(
            f'{len(answers)} از {len(items)}'
        )

    # ✅ تابع مستقل برای هندل کردن تغییرات — رفع خطای Pylance
    def _on_radio_change(item_id, value):
        if value is not None:
            answers[item_id] = value
            update_progress()

    # ---- سؤالات ----
    for item in items:
        with ui.card().classes(
            'w-full bg-slate-800 border border-slate-600 p-4'
        ):
            ui.label(
                f"{item['id']}. {item['text']}"
            ).classes(
                'text-base text-white w-full text-right '
                'leading-relaxed mb-3'
            )
            
            # ✅ تغییر اعمال شده در اینجا: اضافه شدن props('inline') و flex-wrap
            radio = ui.radio(
                scale_values, value=None
            ).props('inline').classes('w-full justify-center flex-wrap gap-3')

            # ✅ استفاده از lambda برای جلوگیری از redeclaration
            radio.on_value_change(
                lambda e, iid=item['id'], r=radio:
                    _on_radio_change(iid, r.value)
            )

    # ---- دکمه‌ی ثبت ----
    async def _submit():
        if len(answers) < len(items):
            ui.notify(
                f'شما به {len(answers)} سؤال از {len(items)} '
                f'پاسخ داده‌اید. لطفاً همه را پاسخ دهید.',
                type='warning', position='top', timeout=4000,
            )
            return
        await on_submit(answers)

    ui.button('ثبت پاسخ‌ها و ادامه', on_click=_submit).classes(
        'w-full bg-green-600 hover:bg-green-500 text-white '
        'text-xl font-bold py-4 mt-4 rounded-lg'
    )

