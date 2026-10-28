"""
وب‌اپ بازی Truthline — نقطه‌ی ورود
====================================
فقط مسئول راه‌اندازی و ثبت مسیرها است.
منطق صفحات در `web_app/pages/` هستند.

نسخه: 1.1.0 — افزودن CSS سراسری برای رفع ناخوانایی فرم‌ها
"""
import os
import sys
import mimetypes

# ---- اصلاح MIME Type در ویندوز (قبل از هر ایمپورت NiceGUI) ----
mimetypes.add_type('text/javascript', '.js')
mimetypes.add_type('text/javascript', '.mjs')
mimetypes.add_type('application/json', '.json')
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('image/svg+xml', '.svg')

# ✅ اضافه‌شده برای پخش صدا و ویدیو در on-air.io و سایر hosts
mimetypes.add_type('audio/mpeg', '.mp3')
mimetypes.add_type('audio/wav', '.wav')
mimetypes.add_type('audio/x-wav', '.wav')
mimetypes.add_type('audio/ogg', '.ogg')
mimetypes.add_type('audio/mp4', '.m4a')
mimetypes.add_type('video/mp4', '.mp4')
mimetypes.add_type('video/webm', '.webm')
mimetypes.add_type('image/png', '.png')
mimetypes.add_type('image/jpeg', '.jpg')
mimetypes.add_type('image/jpeg', '.jpeg')
mimetypes.add_type('image/gif', '.gif')
mimetypes.add_type('image/webp', '.webp')
mimetypes.add_type('font/ttf', '.ttf')
mimetypes.add_type('font/woff', '.woff')
mimetypes.add_type('font/woff2', '.woff2')


# ---- اضافه کردن ریشه‌ی پروژه به sys.path ----
WEB_APP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(WEB_APP_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ---- راه‌اندازی دیتابیس (قبل از ایمپورت صفحات) ----
from web_app.db_manager import init_db
init_db()

# ---- ایمپورت صفحات (دکوراتورها اجرا می‌شوند) ----
from web_app import pages  # noqa: F401

# ---- سرو فایل‌های استاتیک (تصاویر میان‌پرده و شب) ----
from nicegui import app as _ng_app
_ng_app.add_static_files(
    '/assets',
    os.path.join(PROJECT_ROOT, 'assets')
)

# ---- تزریق CSS مکانیک‌ها ----
from nicegui import ui
from web_app.components.quantum_analyzer import QUANTUM_CSS_HTML
from web_app.components.calibration import CALIBRATION_CSS_HTML
from web_app.components.diagnostic_map import DIAGNOSTIC_CSS_HTML
from web_app.components.resource_allocation import ALLOCATION_CSS_HTML
from web_app.components.dependency_board import DEPENDENCY_CSS_HTML
from web_app.components.puzzle import PUZZLE_CSS_HTML
from web_app.components.repetitive_task import (
    REPETITIVE_CSS_HTML,
)
from web_app.components.accountability_dialog import (
    ACCOUNTABILITY_CSS_HTML,
)

for _css in [
    QUANTUM_CSS_HTML,
    CALIBRATION_CSS_HTML,
    DIAGNOSTIC_CSS_HTML,
    ALLOCATION_CSS_HTML,
    DEPENDENCY_CSS_HTML,
    PUZZLE_CSS_HTML,
    REPETITIVE_CSS_HTML,
    ACCOUNTABILITY_CSS_HTML,
]:
    ui.add_head_html(_css, shared=True)


# ============================================================
# CSS سراسری: رفع ناخوانایی فرم‌ها و کرکره‌ها
# ============================================================
GLOBAL_FORM_CSS = """
<style>


/* ============================================================
   رفع هشدار writing-mode (جهت‌دهی روی ریشه سند)
   ============================================================ */
:root {
    direction: rtl;
}

body, .q-page, .q-btn, .q-field, .q-card {
    font-family: 'Vazirmatn', sans-serif !important;
}
/* ============================================================
   ۱. ورودی‌های متنی — متن سفید روی پس‌زمینه‌ی تیره
   ============================================================ */
.q-field__native,
.q-field__input,
.q-field__prefix,
.q-field__suffix,
input[type="text"],
input[type="number"],
input[type="email"],
input[type="password"],
input[type="search"],
textarea {
    color: #FFFFFF !important;
}

/* ============================================================
   ۲. متن Placeholder — خوانا
   ============================================================ */
.q-field__native::placeholder,
.q-field__input::placeholder,
input::placeholder,
textarea::placeholder {
    color: #94A3B8 !important;
    opacity: 1 !important;
}

/* ============================================================
   ۳. برچسب فیلد (label) و متن پایین
   ============================================================ */
.q-field__label,
.q-field__bottom,
.q-field__messages {
    color: #B0BEC5 !important;
}

/* ============================================================
   ۴. آیکون‌های فیلد (کرکره، تقویم و...)
   ============================================================ */
.q-field__control .q-icon,
.q-select__dropdown-icon,
.q-field__append .q-icon,
.q-field__prepend .q-icon {
    color: #4FC3F7 !important;
}

/* ============================================================
   ۵. منوی کرکره (Dropdown) — پس‌زمینه‌ی تیره، متن سفید
   ============================================================ */
.q-menu {
    background-color: #1E293B !important;
    color: #FFFFFF !important;
    border: 1px solid #4FC3F7 !important;
    border-radius: 8px !important;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.6) !important;
}

.q-menu .q-item {
    color: #FFFFFF !important;
    min-height: 40px !important;
}

.q-menu .q-item:hover,
.q-menu .q-item.q-manual-focusable--focused {
    background-color: #334155 !important;
    color: #FFFFFF !important;
}

.q-menu .q-item--active,
.q-menu .q-item.q-item--selected {
    background-color: #4FC3F7 !important;
    color: #0B1D3A !important;
    font-weight: bold !important;
}

.q-menu .q-item__label,
.q-menu .q-item__section {
    color: inherit !important;
}

/* ============================================================
   ۶. Checkbox و Radio
   ============================================================ */
.q-checkbox__label,
.q-radio__label,
.q-toggle__label {
    color: #FFFFFF !important;
}

/* ============================================================
   ۷. وضعیت Disable
   ============================================================ */
.q-field--disabled .q-field__native,
.q-field--disabled .q-field__input,
.q-field--disabled .q-field__control,
.q-field--disabled .q-field__label {
    color: #64748B !important;
    opacity: 0.8 !important;
}

/* ============================================================
   ۸. Textarea پاسخ‌های باز
   ============================================================ */
.q-textarea textarea {
    color: #FFFFFF !important;
    background-color: #1E293B !important;
    border-radius: 6px;
}

/* ============================================================
   ۹. Select — متن انتخاب‌شده
   ============================================================ */
.q-select .q-field__native span,
.q-select .q-field__native {
    color: #FFFFFF !important;
}

/* ============================================================
   ۱۰. تب‌های پرسشنامه
   ============================================================ */
.q-tab__label {
    color: #B0BEC5 !important;
}

.q-tab--active .q-tab__label {
    color: #4FC3F7 !important;
    font-weight: bold !important;
}

/* ============================================================
   ۱۱. دکمه‌ی غیرفعال
   ============================================================ */
.q-btn--disabled {
    color: #64748B !important;
    opacity: 0.5 !important;
}

/* ============================================================
   ۱۲. کارت — متن پیش‌فرض
   ============================================================ */
.q-card {
    color: #FFFFFF;
}

/* ============================================================
   ۱۳. دکمه‌های + و - در فیلد عددی
   ============================================================ */
.q-field__control .q-btn {
    color: #4FC3F7 !important;
}

/* ===== رفع مشکل منوی کرکره در موبایل ===== */
.q-dialog__inner > .q-card {
    background-color: #1E293B !important;
    color: #FFFFFF !important;
}
.q-dialog__inner .q-item {
    color: #FFFFFF !important;
}
.q-dialog__inner .q-item__label {
    color: #FFFFFF !important;
}
.q-menu {
    background-color: #1E293B !important;
}
.q-menu .q-item {
    color: #FFFFFF !important;
}
.q-field__native, .q-field__input {
    color: #FFFFFF !important;
}

/* ============================================
   رفع مشکل منوی کرکره در موبایل (QDialog)
   ============================================ */

/* پس‌زمینه‌ی پشت دیالوگ (backdrop) */
.q-dialog__backdrop,
.q-dialog .q-dialog__backdrop {
    background-color: rgba(0, 0, 0, 0.75) !important;
}

/* پنل سفید که در موبایل تمام‌صفحه می‌شود */
.q-dialog__inner,
.q-dialog .q-dialog__inner,
.q-dialog__inner > .q-card,
.q-dialog .q-card,
.q-menu {
    background-color: #1E293B !important;
    color: #FFFFFF !important;
    border: 1px solid #4FC3F7 !important;
}

/* همه‌ی آیتم‌های داخل منو */
.q-dialog__inner .q-item,
.q-dialog .q-item,
.q-menu .q-item {
    color: #FFFFFF !important;
    background-color: #1E293B !important;
}

/* حالت hover */
.q-dialog__inner .q-item:hover,
.q-dialog .q-item:hover,
.q-menu .q-item:hover,
.q-dialog__inner .q-item.q-manual-focusable--focused,
.q-menu .q-item.q-manual-focusable--focused {
    background-color: #334155 !important;
    color: #FFFFFF !important;
}

/* آیتم انتخاب‌شده */
.q-dialog__inner .q-item--active,
.q-dialog__inner .q-item.q-item--selected,
.q-menu .q-item--active,
.q-menu .q-item.q-item--selected {
    background-color: #4FC3F7 !important;
    color: #0B1D3A !important;
    font-weight: bold !important;
}

/* برچسب‌های داخل آیتم */
.q-dialog__inner .q-item__label,
.q-dialog__inner .q-item__section,
.q-menu .q-item__label,
.q-menu .q-item__section {
    color: inherit !important;
}

/* فیلد جستجو داخل دیالوگ (اگر select قابل جستجو باشد) */
.q-dialog__inner .q-field__native,
.q-dialog__inner .q-field__input,
.q-dialog__inner .q-field__control,
.q-dialog__inner .q-field__label,
.q-menu .q-field__native,
.q-menu .q-field__input,
.q-menu .q-field__control {
    color: #FFFFFF !important;
}

/* آیکون‌ها */
.q-dialog__inner .q-icon,
.q-menu .q-icon {
    color: #4FC3F7 !important;
}

/* مقدار انتخاب‌شده در ورودی اصلی (روی خود صفحه) */
.q-select .q-field__native,
.q-select .q-field__native span,
.q-select .q-field__input {
    color: #FFFFFF !important;
}

/* ناحیه‌ی اسکرول داخل دیالوگ */
.q-dialog__inner .q-virtual-scroll,
.q-dialog__inner .q-virtual-scroll__content,
.q-menu .q-virtual-scroll,
.q-menu .q-virtual-scroll__content {
    background-color: #1E293B !important;
}
</style>
"""
ui.add_head_html(GLOBAL_FORM_CSS, shared=True)
FONT_INJECT_JS = """
<script>
(function() {
    if (document.getElementById('tl-font-style')) return;
    function _assetUrl(relPath) {
        var p = window.location.pathname;
        var slash = p.lastIndexOf('/');
        var basePath = (slash >= 0)
            ? p.substring(0, slash + 1)
            : '/';
        return basePath + relPath;
    }
    var fontUrl = _assetUrl('assets/fonts/Vazirmatn-Regular.ttf');
    var style = document.createElement('style');
    style.id = 'tl-font-style';
    style.textContent =
        "@font-face { font-family: 'Vazirmatn'; " +
        "src: url('" + fontUrl + "') format('truetype'); " +
        "font-weight: normal; font-style: normal; " +
        "font-display: swap; }";
    document.head.appendChild(style);
    console.log('[Font] injected:', fontUrl);
})();
</script>
"""
ui.add_head_html(FONT_INJECT_JS, shared=True)


# ---- اجرا ----

if __name__ in {'__main__', '__mp_main__'}:
    try:
        ui.run(
            title='Truthline Web',
            host='0.0.0.0',
            port=8080,
            reload=False,
            show=False,
            storage_secret='truthline-research-secret-2024',
        )
    except KeyboardInterrupt:
        print('\n✅ سرور با موفقیت متوقف شد.')