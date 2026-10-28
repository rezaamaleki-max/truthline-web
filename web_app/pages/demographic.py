"""صفحه‌ی دموگرافیک"""
import uuid
from nicegui import ui, app, run
from web_app.config import PAGE_CSS
from web_app.db_manager import (
    create_participant, get_participant, log_event_threadsafe,
)
from web_app.components.audio_control import setup_page_audio


@ui.page('/demographic')
def demographic_page():
    if app.storage.user.get('participant_id'):
        participant = get_participant(
            app.storage.user['participant_id']
        )
        if participant:
            ui.navigate.to('/phase1')
            return
        else:
            app.storage.user.clear()

    setup_page_audio("menu")

    ui.query('body').style(PAGE_CSS)

    with ui.column().classes(
        'w-full max-w-3xl mx-auto p-8 gap-6'
    ):
        ui.label('اطلاعات دموگرافیک').classes(
            'text-3xl font-bold text-cyan-400 text-center'
        )
        ui.label(
            'لطفاً اطلاعات زیر را با دقت تکمیل کنید. '
            'این اطلاعات محرمانه بوده و فقط برای تحلیل '
            'آماری پژوهش استفاده می‌شود.'
        ).classes(
            'text-base text-gray-400 text-center '
            'mb-4 leading-relaxed'
        )

        with ui.card().classes(
            'w-full bg-slate-800 border border-cyan-400 p-6'
        ):
            with ui.column().classes('gap-4 w-full'):
                # ---- سن ----
                ui.label('سن:').classes(
                    'text-base text-white font-bold'
                )
                age_input = ui.select(
                    [str(i) for i in range(18, 66)],
                    value='25',
                ).classes(
                    'w-full bg-slate-700 text-white '
                    'text-lg p-3 rounded'
                )

                # ---- جنسیت ----
                ui.label('جنسیت:').classes(
                    'text-base text-white font-bold mt-2'
                )
                gender_input = ui.select(
                    ['زن', 'مرد'], value='زن',
                ).classes(
                    'w-full bg-slate-700 text-white '
                    'text-lg p-3 rounded'
                )

                # ---- مقطع تحصیلی ----
                ui.label('مقطع تحصیلی:').classes(
                    'text-base text-white font-bold mt-2'
                )
                edu_input = ui.select(
                    ['زیردیپلم', 'دیپلم', 'کاردانی',
                     'کارشناسی', 'کارشناسی ارشد',
                     'دکتری', 'بالاتر از دکتری'],
                    value='کارشناسی',
                ).classes(
                    'w-full bg-slate-700 text-white '
                    'text-lg p-3 rounded'
                )

                # ---- رشته تحصیلی ----
                ui.label('رشته تحصیلی:').classes(
                    'text-base text-white font-bold mt-2'
                )
                field_input = ui.select(
                    ['مهندسی',
                     'علوم پایه (ریاضی/فیزیک/شیمی/زیست)',
                     'علوم انسانی',
                     'پزشکی و علوم وابسته',
                     'هنر و معماری',
                     'کشاورزی و منابع طبیعی',
                     'سایر'],
                    value='مهندسی',
                ).classes(
                    'w-full bg-slate-700 text-white '
                    'text-lg p-3 rounded'
                )

                # ---- سابقه کار ----
                ui.label('سابقه کار:').classes(
                    'text-base text-white font-bold mt-2'
                )
                work_input = ui.select(
                    ['بدون سابقه کار', 'کمتر از ۱ سال',
                     '۱ تا ۳ سال', '۳ تا ۵ سال',
                     '۵ تا ۱۰ سال', 'بیش از ۱۰ سال'],
                    value='بدون سابقه کار',
                ).classes(
                    'w-full bg-slate-700 text-white '
                    'text-lg p-3 rounded'
                )

                # ---- آشنایی با ادبیات علمی-تخیلی ----
                ui.label(
                    'میزان آشنایی با ادبیات علمی-تخیلی '
                    'و مهندسی فضایی:'
                ).classes(
                    'text-base text-white font-bold mt-2'
                )
                tech_input = ui.select(
                    ['اصلاً آشنایی ندارم', 'خیلی کم', 'کم',
                     'متوسط', 'زیاد', 'خیلی زیاد'],
                    value='اصلاً آشنایی ندارم',
                ).classes(
                    'w-full bg-slate-700 text-white '
                    'text-lg p-3 rounded'
                )

                # ---- رضایت‌نامه ----
                ui.separator().classes('my-4')
                consent_input = ui.checkbox(
                    'اینجانب با شرکت داوطلبانه در این '
                    'پژوهش موافقم و می‌دانم که داده‌هایم '
                    'به صورت محرمانه تحلیل خواهد شد.'
                ).classes('text-base text-white')

        async def submit_form():
            if not consent_input.value:
                ui.notify(
                    'برای ادامه، لطفاً تیک رضایت‌نامه را '
                    'فعال کنید.',
                    type='warning', position='top',
                    timeout=4000,
                )
                return

            try:
                age_val = int(age_input.value or 25)
            except (TypeError, ValueError):
                age_val = 25

            data = {
                'age': age_val,
                'gender': str(gender_input.value),
                'education': str(edu_input.value),
                'field_of_study': str(field_input.value),
                'work_experience': str(work_input.value),
                'technical_familiarity': str(
                    tech_input.value
                ),
                'consent': True,
            }
            participant_id = str(uuid.uuid4())[:8]
            session_id = str(uuid.uuid4())[:12]

            success = await run.io_bound(
                create_participant,
                participant_id=participant_id,
                session_id=session_id,
                demographic_data=data,
            )
            if not success:
                ui.notify(
                    'خطا در ثبت اطلاعات. لطفاً دوباره '
                    'تلاش کنید.',
                    type='negative', position='top',
                    timeout=5000,
                )
                return

            app.storage.user['participant_id'] = participant_id
            app.storage.user['session_id'] = session_id
            app.storage.user['demographic'] = data

            await run.io_bound(
                log_event_threadsafe,
                participant_id=participant_id,
                session_id=session_id,
                event_type='demographic_completed',
                scenario_id='demographic',
                metadata=data,
            )

            ui.notify(
                f'اطلاعات ثبت شد. کد شما: {participant_id}',
                type='positive', position='top',
                timeout=3000,
            )
            ui.navigate.to('/intro')

        ui.button(
            'شروع مأموریت', on_click=submit_form,
        ).classes(
            'w-full bg-green-600 hover:bg-green-500 '
            'text-white text-xl font-bold py-4 mt-2 '
            'rounded-lg'
        )