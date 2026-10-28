# main.py — نقطه‌ی ورود وب‌اپ Truthline
import os
import mimetypes
import sys

# ---- اصلاح MIME Type (قبل از هر ایمپورت) ----
mimetypes.add_type('text/javascript', '.js')
mimetypes.add_type('text/javascript', '.mjs')
mimetypes.add_type('application/json', '.json')
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('image/svg+xml', '.svg')
mimetypes.add_type('audio/mpeg', '.mp3')
mimetypes.add_type('audio/wav', '.wav')
mimetypes.add_type('audio/ogg', '.ogg')
mimetypes.add_type('video/mp4', '.mp4')
mimetypes.add_type('video/webm', '.webm')
mimetypes.add_type('image/png', '.png')
mimetypes.add_type('image/jpeg', '.jpg')
mimetypes.add_type('font/ttf', '.ttf')
mimetypes.add_type('font/woff', '.woff')
mimetypes.add_type('font/woff2', '.woff2')

# ---- اضافه کردن ریشه به sys.path ----
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ---- اجرای ماژول اپ ----
if __name__ in {'__main__', '__mp_main__'}:
    from web_app.app import *  # noqa: F401,F403