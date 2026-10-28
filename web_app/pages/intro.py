"""
صفحه‌ی مقدمه‌ی داستانی — نسخه‌ی وب
=====================================
شبیه‌سازی کامل intro_scene.py از نسخه‌ی دسکتاپ:
- ۲۲ دیالوگ (پرولوگ شخصی + معرفی شخصیت‌ها + هشدار)
- پرتره‌ی شخصیت‌ها با تشخیص احساس
- تصویر پس‌زمینه‌ی ایستگاه
- موسیقی station_calm
- پشتیبانی کیبورد (Space/Enter) + دکمه

نسخه: 1.0.0
"""
import asyncio

from nicegui import ui, app

from web_app.config import PAGE_CSS, TEST_MODE
from web_app.character_utils import resolve_portrait_url
from web_app.components.audio_control import setup_page_audio


# ============================================================
# دیالوگ‌های مقدمه (پورت مستقیم از دسکتاپ)
# ============================================================
INTRO_DIALOGUES = [
    # ---------------- پرولوگ شخصی ----------------
    {
        "speaker": "راوی",
        "text": (
            "سه ماه پیش، پرونده‌ی بازرسی دوره‌ای ایستگاه "
            "کاسپین روی میزت قرار گرفت. اما این بار، "
            "درخواست از خودت بود."
        ),
    },
    {
        "speaker": "راوی",
        "text": (
            "تو داوطلب شدی؛ چون می‌دانستی این ایستگاه، و "
            "مردمی که در آن زندگی می‌کنند، تو را در "
            "موقعیت‌هایی قرار می‌دهند که هیچ شبیه‌ساز "
            "آموزشی نمی‌تواند بازسازی کند."
        ),
    },
    {
        "speaker": "راوی",
        "text": (
            "معیار ارتقاء تو، فقط گزارش فنی نیست. شیوه‌ی "
            "تصمیم‌گیری تو در بحران‌ها، همان چیزی است که "
            "تیم ارزیابی به دنبالش است."
        ),
    },

    # ---------------- مقدمه‌ی موجود ----------------
    {
        "speaker": "راوی",
        "text": "سال ۲۱۴۸. ایستگاه پژوهشی مداری کاسپین.",
    },
    {
        "speaker": "راوی",
        "text": "هر تصمیم، یک ردپا بر جای می‌گذارد.",
    },
    {
        "speaker": "راوی",
        "text": (
            "تو تکنسین ارشد هستی. برای بازرسی دوره‌ای به "
            "ایستگاه اعزام شده‌ای."
        ),
    },
    {
        "speaker": "راوی",
        "text": (
            "در این مأموریت، فقط یه چیز ازت می‌خوایم: "
            "خودت باش. همون‌طور که توی موقعیت‌های واقعی "
            "تصمیم می‌گیری، تصمیم بگیر. هوش و درایتت رو "
            "به کار بگیر و تا جایی که می‌تونی، مسائل رو "
            "حل کن."
        ),
    },
    {
        "speaker": "مهندس رحیمی",
        "text": (
            "به ایستگاه کاسپین خوش آمدید. من مهندس "
            "رحیمی هستم، مسئول نگهداری این ایستگاه."
        ),
    },
    {
        "speaker": "مهندس رحیمی",
        "text": (
            "بذار کسی رو معرفی کنم. این لی هست، "
            "کارآموز بخش ناوبری. چند ماه پیش اومده، "
            "سخت‌کوش و باانگیزه است."
        ),
    },
    {
        "speaker": "لی",
        "text": (
            "سلام! خوشحالم که می‌بینمتون. اگه در طول "
            "شیفت کمکی لازم داشتید، در خدمتم."
        ),
    },
    {
        "speaker": "مهندس رحیمی",
        "text": (
            "راستی تکنسین، لی این چند روز روی یه سری "
            "محاسبات ناوبری گیر کرده. اگه بعد از "
            "کارهای اولیه فرصتی داشتی، کمکش کن. لی "
            "تازه‌کاره ولی سخت‌کوشه."
        ),
    },
    {
        "speaker": "لی",
        "text": (
            "(با لبخند) ممنون مهندس. تکنسین، اگه بعد "
            "از کالیبراسیون فرصت کردید، من توی بخش "
            "ناوبری هستم. داده‌ها رو که آماده کردم، "
            "می‌تونم بیام پیش شما."
        ),
    },
    {
        "speaker": "مهندس رحیمی",
        "text": (
            "و این هم دکتر آرتمیس، مسئول تحلیل "
            "داده‌های علمی ایستگاه. یکی از دقیق‌ترین "
            "تحلیلگرهایی که توی این شبکه داریم."
        ),
    },
    {
        "speaker": "دکتر آرتمیس",
        "text": (
            "سلام... خوش آمدید. من راستش دارم روی چند "
            "آنومالی در داده‌های هفته گذشته کار می‌کنم. "
            "اگر بعد از جلسه فرصتی بود، می‌خواستم "
            "نظرتون رو بشنوم."
        ),
    },
    {
        "speaker": "مهندس رحیمی",
        "text": (
            "آرتمیس همیشه نگرانه، کارش همینه. اما "
            "جدی نگیر."
        ),
    },
    {
        "speaker": "راوی",
        "text": (
            "در راهروی منتهی به اتاق کنترل، مردی "
            "میانسال با دستکش‌های کار، مشغول تعمیر یک "
            "پنل برق است. با دیدن شما، سرش را بالا "
            "می‌آورد. لکه‌های روغن روی گونه‌اش، "
            "خط‌های عمیق کار را نشان می‌دهد."
        ),
    },
    {
        "speaker": "مهندس رحیمی",
        "text": (
            "این فرزین هست. تکنسین فنی ایستگاه. هر چی "
            "این‌جا برق مصرف می‌کنه، یه روزی از دست "
            "فرزین رد شده."
        ),
    },
    {
        "speaker": "فرزین",
        "text": (
            "(دستکش‌هایش را پایین می‌کشد، ولی دستش را "
            "برای دست دادن دراز نمی‌کند. لحنش صمیمی "
            "است، ولی نگاهش جای دیگری را می‌خواند) "
            "تکنسین. خوش آمدید. من این‌جا خیلی چیزها "
            "می‌دونم — شاید بیشتر از اونی  که "
            "به‌نظر می‌رسه لازم باشه بدونم. اگه یه "
            "روزی کمکی خواستید... فقط یه اشاره کافیه."
        ),
    },
    {
        "speaker": "راوی",
        "text": (
            "فرزین بدون اینکه منتظر جواب بماند، به کار "
            "خودش برمی‌گردد. صدای پیچ‌گوشتی برقی، در "
            "راهرو می‌پیچد. مهندس رحیمی نگاهی کوتاه "
            "به او می‌اندازد، ولی چیزی نمی‌گوید."
        ),
    },
    {
        "speaker": "مهندس رحیمی",
        "text": (
            "حالا بذار بریم اتاق کنترل؛ دیروز چند "
            "ناهنجاری در سیستم‌ها ثبت شده."
        ),
    },
    {
        "speaker": "سیستم",
        "text": (
            "هشدار: افزایش دمای مدار خنک‌کننده. "
            "توصیه می‌شود فوراً بررسی شود."
        ),
    },
    {
        "speaker": "مهندس رحیمی",
        "text": (
            "مشکل جدی‌تر از اونیه که فکر می‌کردم. "
            "باید سریع به اتاق کنترل برویم."
        ),
    },
]


# ============================================================
# صفحه
# ============================================================
@ui.page('/intro')
async def intro_page():
    participant_id = app.storage.user.get('participant_id')
    session_id = app.storage.user.get('session_id')

    if not participant_id or not session_id:
        ui.navigate.to('/')
        return

    # ✅ موسیقی مقدمه (station_calm)
    setup_page_audio("intro")

    ui.query('body').style(PAGE_CSS)

    # ---- state ----
    state = {"idx": 0, "advancing": False}

    container = ui.column().classes(
        'w-full max-w-3xl mx-auto p-6 gap-4'
    )

    # ---- توابع ----
    async def _advance():
        if state["advancing"]:
            return
        state["advancing"] = True
        try:
            state["idx"] += 1
            if state["idx"] >= len(INTRO_DIALOGUES):
                await _go_to_phase1()
                return
            await _render()
        finally:
            state["advancing"] = False

    async def _go_to_phase1():
        from web_app.audio import play_transition_sfx
        play_transition_sfx()

        # ثبت لاگ
        try:
            from web_app.db_manager import log_event_threadsafe
            from nicegui import run
            await run.io_bound(
                log_event_threadsafe,
                participant_id=participant_id,
                session_id=session_id,
                event_type='intro_completed',
                scenario_id='intro',
                metadata={
                    "total_dialogues": len(INTRO_DIALOGUES),
                },
            )
        except Exception as e:
            print(f"⚠️ intro log: {e}")

        ui.notify(
            '✓ مقدمه تکمیل شد. انتقال به روز اول...',
            type='positive', position='top', timeout=2500,
        )
        ui.navigate.to('/phase1')

    async def _render():
        container.clear()
        idx = state["idx"]

        with container:
            # ---- پس‌زمینه‌ی ایستگاه ----
            with ui.card().classes(
                'w-full bg-slate-900 border-2 border-cyan-400 '
                'p-2 overflow-hidden'
            ):
                ui.image(
                    '/assets/backgrounds/menu_hero_v01.png'
                ).classes(
                    'w-full rounded object-cover'
                ).style('max-height: 260px;')

            # ---- عنوان ----
            ui.label("ایستگاه پژوهشی مداری کاسپین").classes(
                'text-2xl font-bold text-cyan-400 '
                'text-center w-full'
            )
            ui.label("سال ۲۱۴۸").classes(
                'text-sm text-gray-400 text-center w-full mb-2'
            )

            # ---- نوار پیشرفت ----
            if idx < len(INTRO_DIALOGUES):
                with ui.row().classes(
                    'items-center gap-2 w-full justify-between'
                ):
                    ui.label("مقدمه").classes(
                        'text-xs text-cyan-400 font-bold'
                    )
                    ui.label(
                        f"{idx + 1} از {len(INTRO_DIALOGUES)}"
                    ).classes(
                        'text-xs text-gray-400 font-mono'
                    )
                ui.linear_progress(
                    value=(idx + 1) / len(INTRO_DIALOGUES),
                    show_value=False,
                ).classes('w-full mb-2')

            # ---- دیالوگ فعلی ----
            if idx < len(INTRO_DIALOGUES):
                d = INTRO_DIALOGUES[idx]
                speaker = str(d.get("speaker", "") or "")
                text = str(d.get("text", "") or "")

                # ✅ پرتره
                portrait_url = resolve_portrait_url(
                    speaker, text
                )

                with ui.card().classes(
                    'w-full bg-slate-800 border-2 border-cyan-400 '
                    'p-4'
                ):
                    with ui.row().classes(
                        'items-start gap-4 w-full no-wrap'
                    ):
                        # پرتره (راست در RTL)
                        if portrait_url:
                            with ui.element('div').classes(
                                'flex-shrink-0'
                            ):
                                ui.image(portrait_url).style(
                                    'width: 100px; height: 130px; '
                                    'border-radius: 10px; '
                                    'border: 2px solid #4FC3F7; '
                                    'object-fit: cover; '
                                    'background: #0B1D3A;'
                                )
                        # محتوا
                        with ui.column().classes(
                            'flex-1 gap-2'
                        ):
                            ui.label(
                                f"[{speaker}]"
                            ).classes(
                                'text-sm text-cyan-400 '
                                'font-bold w-full text-right'
                            )
                            ui.label(text).classes(
                                'text-base text-white '
                                'leading-relaxed w-full '
                                'text-right '
                                'whitespace-pre-line'
                            )

                # ---- دکمه‌ی ادامه ----
                is_last = (idx + 1 >= len(INTRO_DIALOGUES))
                btn_text = (
                    'ورود به روز اول' if is_last else 'ادامه'
                )
                ui.button(
                    btn_text, on_click=_advance,
                ).classes(
                    'w-full py-3 text-lg font-bold '
                    'bg-cyan-600 hover:bg-cyan-500 mt-2'
                )
                ui.label(
                    "می‌توانید کلید Space یا Enter را هم بزنید"
                ).classes(
                    'text-xs text-gray-500 text-center '
                    'w-full italic'
                )

    # ---- پشتیبانی کیبورد (Space/Enter) ----
    try:
        def _kb_handler(e):
            try:
                if (
                    e.action.keydown
                    and e.key.name in (" ", "Space", "Enter")
                ):
                    asyncio.create_task(_advance())
            except Exception:
                pass

        ui.keyboard(on_key=_kb_handler)
    except Exception as e:
        print(f"⚠️ keyboard disabled: {e}")

    # ---- رندر اولیه ----
    await _render()