"""
مدیریت صدا — نسخه‌ی وب
============================
- پخش موسیقی پس‌زمینه با fade-in
- SFX یک‌باره (click, choice, scan, toast, transition)
- مدیریت autoplay policy (پخش بعد از اولین interaction)
- ذخیره‌ی track جاری و تنظیمات در app.storage.user

نسخه: 1.1.0 — افزودن notify_with_sound با Literal
"""
from typing import Literal

from nicegui import ui, app


# ============================================================
# نقشه‌ی صحنه → فایل موسیقی
# ============================================================
MUSIC_TRACKS = {
    "menu":      "assets/audio/menu_ambient.mp3",
    "intro":     "assets/audio/station_calm.mp3",
    "interlude": "assets/audio/station_calm.mp3",
    "night":     "assets/audio/station_calm.mp3",
    "phase1":    "assets/audio/phase_control.mp3",
    "phase2":    "assets/audio/phase_tense.mp3",
    "phase3":    "assets/audio/phase_control.mp3",
    "phase4":    "assets/audio/phase_council.mp3",
    "council":   "assets/audio/phase_council.mp3",
    "results":   "assets/audio/phase_council.mp3",
}


# ============================================================
# نقشه‌ی SFX → فایل صوتی
# ============================================================
SFX_FILES = {
    "click":      "assets/audio/click_button.mp3",
    "choice":     "assets/audio/choice_confirm.mp3",
    "toast":      "assets/audio/toast_appear.mp3",
    "scan":       "assets/audio/scan_pulse.mp3",
    "transition": "assets/audio/transition_whoosh.mp3",
}


# ============================================================
# تنظیمات (با پیش‌فرض)
# ============================================================
DEFAULT_VOLUME = 0.4
DEFAULT_ENABLED = True


def get_audio_volume() -> float:
    """حجم صدا (0..1) از storage یا پیش‌فرض."""
    val = app.storage.user.get("audio_volume")
    if val is None:
        return DEFAULT_VOLUME
    try:
        return max(0.0, min(1.0, float(val)))
    except (TypeError, ValueError):
        return DEFAULT_VOLUME


def get_audio_enabled() -> bool:
    """آیا صدا فعال است؟"""
    val = app.storage.user.get("audio_enabled")
    if val is None:
        return DEFAULT_ENABLED
    return bool(val)


def set_audio_enabled(enabled: bool):
    """فعال/غیرفعال کردن صدا (ذخیره + اعمال فوری)."""
    app.storage.user["audio_enabled"] = bool(enabled)
    js_bool = "true" if enabled else "false"
    ui.run_javascript(
        f"window._tlAudio && "
        f"window._tlAudio.setEnabled({js_bool});"
    )


def set_audio_volume(volume: float):
    """تنظیم حجم صدا (ذخیره + اعمال فوری)."""
    volume = max(0.0, min(1.0, float(volume)))
    app.storage.user["audio_volume"] = volume
    ui.run_javascript(
        f"window._tlAudio && "
        f"window._tlAudio.setVolume({volume});"
    )


# ============================================================
# نصب JS Core
# ============================================================
def install_audio_core():
    """نصب JavaScript core در head (idempotent)."""
    import json as _json

    tracks_json = _json.dumps(MUSIC_TRACKS)
    sfx_json = _json.dumps(SFX_FILES)
    volume = get_audio_volume()
    enabled = get_audio_enabled()
    vol_js = f"{volume}"
    en_js = "true" if enabled else "false"

    js = """
    (function() {
        // نسخه 1.3 — حذف preload برای جلوگیری از PoolTimeout on-air
        if (window._tlAudio && window._tlAudio.version === '1.3') {
            window._tlAudio.setEnabled(__ENABLED__);
            window._tlAudio.setVolume(__VOLUME__);
            window._tlAudio.updateTracks(
                __MUSIC_TRACKS__, __SFX_FILES__
            );
            return;
        }

        if (window._tlAudio) {
            try { window._tlAudio.stopMusic(); } catch(e) {}
        }

        function _assetUrl(relPath) {
            var p = window.location.pathname;
            var slash = p.lastIndexOf('/');
            var basePath = (slash >= 0)
                ? p.substring(0, slash + 1)
                : '/';
            return basePath + relPath;
        }

        var MUSIC_TRACKS = __MUSIC_TRACKS__;
        var SFX_FILES = __SFX_FILES__;

        var musicEl = new Audio();
        musicEl.loop = true;
        musicEl.volume = __VOLUME__;
        musicEl.preload = 'auto';

        var currentKey = null;
        var enabled = __ENABLED__;
        var pendingKey = null;
        var unlocked = false;

        // ❌ هیچ preload گروهی — هیچ setTimeout برای بارگذاری
        //    همه چیز در زمان نیاز بارگذاری می‌شود

        function _tryPlay() {
            if (!musicEl.src) return;
            var p = musicEl.play();
            if (p && p.catch) {
                p.catch(function(err) {
                    console.warn('[Audio] play failed:', err);
                });
            }
        }

        function _fadeIn(target) {
            var v = 0;
            musicEl.volume = 0;
            var step = Math.max(0.01, target / 20);
            var iv = setInterval(function() {
                v += step;
                if (v >= target) {
                    musicEl.volume = target;
                    clearInterval(iv);
                } else {
                    musicEl.volume = v;
                }
            }, 30);
        }

        function playMusic(key) {
            if (!enabled) return;
            if (!key) {
                musicEl.pause();
                musicEl.src = "";
                currentKey = null;
                return;
            }
            if (currentKey === key && !musicEl.paused) return;
            var url = MUSIC_TRACKS[key];
            if (!url) {
                musicEl.pause();
                musicEl.src = "";
                currentKey = key;
                return;
            }
            var resolvedUrl = _assetUrl(url);
            console.log('[Audio] play:', key, '->', resolvedUrl);
            musicEl.src = resolvedUrl;
            currentKey = key;
            var targetVol = parseFloat(
                localStorage.getItem('tl_audio_vol') || '0.4'
            );
            _fadeIn(targetVol);
            _tryPlay();
        }

        function stopMusic() {
            musicEl.pause();
            musicEl.src = "";
            currentKey = null;
        }

        // ✅ کش SFX: اولین بار دانلود می‌شود، بارهای بعدی از مرورگر
        var _sfxCache = {};

        function playSfx(key) {
            if (!enabled) return;
            var url = SFX_FILES[key];
            if (!url) return;
            var resolved = _assetUrl(url);
            var a = _sfxCache[resolved];
            if (!a) {
                a = new Audio(resolved);
                a.preload = 'auto';
                _sfxCache[resolved] = a;
            }
            a.volume = musicEl.volume;
            try {
                a.currentTime = 0;
            } catch(e) {}
            var p = a.play();
            if (p && p.catch) {
                p.catch(function(err) {
                    console.warn(
                        '[Audio] sfx failed:', err
                    );
                });
            }
        }

        function setEnabled(v) {
            enabled = !!v;
            if (!enabled) {
                musicEl.pause();
            } else if (currentKey) {
                _tryPlay();
            }
        }

        function setVolume(v) {
            v = Math.max(0, Math.min(1, v));
            musicEl.volume = v;
            try {
                localStorage.setItem('tl_audio_vol', v);
            } catch(e) {}
        }

        function updateTracks(newMusic, newSfx) {
            if (newMusic) {
                Object.keys(newMusic).forEach(function(k) {
                    MUSIC_TRACKS[k] = newMusic[k];
                });
            }
            if (newSfx) {
                Object.keys(newSfx).forEach(function(k) {
                    SFX_FILES[k] = newSfx[k];
                });
            }
        }

        function unlockPending(key) {
            pendingKey = key;
        }

        function _unlock() {
            if (unlocked) return;
            unlocked = true;
            var k = pendingKey;
            pendingKey = null;
            if (k) playMusic(k);
            document.removeEventListener('click', _unlock, true);
            document.removeEventListener('keydown', _unlock, true);
            document.removeEventListener(
                'touchstart', _unlock, true
            );
            try {
                var h = document.getElementById('tl-audio-hint');
                if (h) h.style.display = 'none';
            } catch(e) {}
        }
        document.addEventListener('click', _unlock, true);
        document.addEventListener('keydown', _unlock, true);
        document.addEventListener('touchstart', _unlock, true);

        document.addEventListener('click', function(e) {
            var t = e.target;
            if (!t || !t.closest) return;
            var btn = t.closest(
                'button.nicegui-btn, .q-btn, button'
            );
            if (btn && !btn.disabled) {
                playSfx('click');
            }
        }, true);

        window._tlAudioUnlock = _unlock;

        window._tlAudio = {
            version: '1.3',
            playMusic: playMusic,
            stopMusic: stopMusic,
            playSfx: playSfx,
            setEnabled: setEnabled,
            setVolume: setVolume,
            updateTracks: updateTracks,
            unlockPending: unlockPending,
            get pendingKey() { return pendingKey; },
        };

        console.log('[Audio] core 1.3 initialized');
    })();
    """

    js = js.replace("__MUSIC_TRACKS__", tracks_json)
    js = js.replace("__SFX_FILES__", sfx_json)
    js = js.replace("__VOLUME__", vol_js)
    js = js.replace("__ENABLED__", en_js)

    hint_html = """
    <style>
    #tl-audio-hint {
        position: fixed;
        bottom: 70px;
        left: 8px;
        z-index: 999;
        background: rgba(79, 195, 247, 0.15);
        border: 1px solid #4FC3F7;
        border-radius: 8px;
        padding: 6px 12px;
        color: #4FC3F7;
        font-family: Vazirmatn, sans-serif;
        font-size: 11px;
        direction: rtl;
        animation: tl-hint-pulse 2s ease-in-out infinite;
        cursor: pointer;
    }
    @keyframes tl-hint-pulse {
        0%, 100% { opacity: 0.7; }
        50% { opacity: 1; }
    }
    </style>
    <div id="tl-audio-hint" onclick="window._tlAudioUnlock && window._tlAudioUnlock()">
        🎵 برای شروع موسیقی کلیک کنید
    </div>
    """

    ui.add_head_html(hint_html)
    ui.add_head_html(f"<script>{js}</script>")


# ============================================================
# API عمومی
# ============================================================
def init_page_music(music_key: str | None):
    """مقداردهی موسیقی صفحه‌ی جاری."""
    install_audio_core()

    js_key = music_key or ""
    app.storage.user["audio_current_key"] = js_key

    ui.run_javascript(f"""
        (function() {{
            const tryPlay = () => {{
                if (window._tlAudio) {{
                    window._tlAudio.unlockPending("{js_key}");
                    window._tlAudio.playMusic("{js_key}");
                }} else {{
                    setTimeout(tryPlay, 100);
                }}
            }};
            tryPlay();
        }})();
    """)


def play_sfx(name: str):
    """پخش SFX با نام مشخص."""
    ui.run_javascript(
        f'window._tlAudio && '
        f'window._tlAudio.playSfx("{name}");'
    )


def play_choice_sfx():
    """صدای تأیید انتخاب — دینگ دینگ"""
    play_sfx("choice")


def play_scan_sfx():
    """صدای اسکن — پالس"""
    play_sfx("scan")


def play_transition_sfx():
    """صدای ترنزیشن"""
    play_sfx("transition")


def play_toast_sfx():
    """صدای اعلان کوچک — پاپ"""
    play_sfx("toast")


# ============================================================
# Helper: toast + صدا در یک خط (با Literal برای Pylance)
# ============================================================
_NotifyType = Literal[
    "positive", "negative", "warning", "info", "ongoing"
]
_NotifyPosition = Literal[
    "top-left", "top-right", "bottom-left", "bottom-right",
    "top", "bottom", "left", "right", "center",
]


def notify_with_sound(
    message: str,
    type: _NotifyType = "positive",
    position: _NotifyPosition = "top",
    timeout: int = 1500,
    close_button: bool = False,
) -> None:
    """
    نمایش toast + پخش صدای toast_appear به‌طور هم‌زمان.
    این تابع تضمین می‌کند صدای toast در همه‌ی فازها یکسان باشد.
    """
    ui.notify(
        message,
        type=type,
        position=position,
        timeout=timeout,
        close_button=close_button,
    )
    play_toast_sfx()