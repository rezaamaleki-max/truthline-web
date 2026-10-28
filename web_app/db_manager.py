import sqlite3
import os
import time
import json

# ✅ مسیر پوشه‌ی web_app
WEB_APP_DIR = os.path.dirname(os.path.abspath(__file__))
# ✅ دیتابیس مستقل در web_app/data/
DB_PATH = os.path.join(WEB_APP_DIR, "data", "participants_web.db")

# ✅ اطمینان از وجود پوشه
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def get_connection():
    """ساخت یک اتصال امن با تنظیمات WAL و Timeout"""
    # timeout=30 به این معنی است که اگر دیتابیس قفل بود، ۳۰ ثانیه صبر کن
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    # فعال‌سازی WAL برای خواندن و نوشتن همزمان
    conn.execute("PRAGMA journal_mode=WAL;")
    # افزایش سرعت نوشتن (اختیاری ولی مفید)
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def init_db():
    """ساخت جداول در صورت نیاز"""
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS web_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            participant_id TEXT,
            session_id TEXT,
            event_type TEXT,
            scenario_id TEXT,
            choice_id INTEGER,
            decision_time_ms INTEGER,
            metadata TEXT,
            timestamp REAL
        )
    ''')
    # ✅ جدول مخصوص شواهد (همان Evidence)
    c.execute('''
        CREATE TABLE IF NOT EXISTS web_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            participant_id TEXT,
            scenario_id TEXT,
            competency TEXT,
            evidence_key TEXT,
            evidence_value REAL,
            weight REAL,
            timestamp REAL
        )
    ''')
    # ✅ جدول جدید شرکت‌کنندگان (اطلاعات دموگرافیک)
    c.execute('''
        CREATE TABLE IF NOT EXISTS participants_web (
            participant_id TEXT PRIMARY KEY,
            session_id TEXT,
            age INTEGER,
            gender TEXT,
            education TEXT,
            field_of_study TEXT,
            work_experience TEXT,
            gaming_experience TEXT,
            technical_familiarity TEXT,
            consent INTEGER DEFAULT 0,
            created_at REAL,
            completed_at REAL
        )
    ''')
    # ✅ جدول جدید HEXACO
    c.execute('''
        CREATE TABLE IF NOT EXISTS web_hexaco (
            participant_id TEXT PRIMARY KEY,
            answers_json TEXT,
            scores_json TEXT,
            completed_at REAL,
            FOREIGN KEY (participant_id) REFERENCES participants_web(participant_id)
        )
    ''')
    # ✅ جدول CRT
    c.execute('''
        CREATE TABLE IF NOT EXISTS web_crt (
            participant_id TEXT PRIMARY KEY,
            answers_json TEXT,
            result_json TEXT,
            completed_at REAL,
            FOREIGN KEY (participant_id) REFERENCES participants_web(participant_id)
        )
    ''')
    # ✅ جدول SD3
    c.execute('''
        CREATE TABLE IF NOT EXISTS web_sd3 (
            participant_id TEXT PRIMARY KEY,
            answers_json TEXT,
            scores_json TEXT,
            completed_at REAL,
            FOREIGN KEY (participant_id) REFERENCES participants_web(participant_id)
        )
    ''')
    # ✅ جدول مطلوبیت اجتماعی
    c.execute('''
        CREATE TABLE IF NOT EXISTS web_social_desirability (
            participant_id TEXT PRIMARY KEY,
            answers_json TEXT,
            result_json TEXT,
            completed_at REAL,
            FOREIGN KEY (participant_id) REFERENCES participants_web(participant_id)
        )
    ''')
    # ✅ جدول بازخورد پس از بازی
    c.execute('''
        CREATE TABLE IF NOT EXISTS web_feedback (
            participant_id TEXT PRIMARY KEY,
            close_answers_json TEXT,
            open_answers_json TEXT,
            demographic_extra_json TEXT,
            scores_json TEXT,
            completed_at REAL,
            FOREIGN KEY (participant_id) REFERENCES participants_web(participant_id)
        )
    ''')
    # ✅ جدول روابط با شخصیت‌ها
    c.execute('''
        CREATE TABLE IF NOT EXISTS web_relationships (
            participant_id TEXT,
            character_key TEXT,
            value INTEGER DEFAULT 0,
            PRIMARY KEY (participant_id, character_key),
            FOREIGN KEY (participant_id) REFERENCES participants_web(participant_id)
        )
    ''')
    # ✅ جدول پیشرفت فازها (برای resume)
    c.execute('''
        CREATE TABLE IF NOT EXISTS web_phase_progress (
            participant_id TEXT,
            phase_key TEXT,
            current_scenario_index INTEGER DEFAULT 0,
            state_json TEXT,
            updated_at REAL,
            PRIMARY KEY (participant_id, phase_key),
            FOREIGN KEY (participant_id) REFERENCES participants_web(participant_id)
        )
    ''')
    conn.commit()
    conn.close()


def log_event_threadsafe(
    participant_id: str, session_id: str, event_type: str,
    scenario_id: str = "", choice_id: int = 0,
    decision_time_ms: int = 0, metadata: dict | None = None
):
    """
    ثبت رویداد. این تابع باید در یک Thread جداگانه (توسط NiceGUI) صدا زده شود
    تا UI را بلاک نکند.
    """
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute('''
            INSERT INTO web_events 
            (participant_id, session_id, event_type, scenario_id, choice_id, decision_time_ms, metadata, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            participant_id, session_id, event_type, scenario_id, 
            choice_id, decision_time_ms, 
            json.dumps(metadata or {}, ensure_ascii=False), 
            time.time()
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ خطا در ثبت رویداد در دیتابیس: {e}")
        return False

def create_participant(
    participant_id: str,
    session_id: str,
    demographic_data: dict | None = None,
) -> bool:
    """
    ثبت شرکت‌کننده جدید با اطلاعات دموگرافیک.
    Returns: True اگر موفق، False اگر خطا.
    """
    if demographic_data is None:
        demographic_data = {}

    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute('''
            INSERT INTO participants_web
            (participant_id, session_id, age, gender, education,
             field_of_study, work_experience, gaming_experience,
             technical_familiarity, consent, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            participant_id,
            session_id,
            int(demographic_data.get('age') or 0),
            str(demographic_data.get('gender') or ''),
            str(demographic_data.get('education') or ''),
            str(demographic_data.get('field_of_study') or ''),
            str(demographic_data.get('work_experience') or ''),
            str(demographic_data.get('gaming_experience') or ''),
            str(demographic_data.get('technical_familiarity') or ''),
            1 if demographic_data.get('consent') else 0,
            time.time(),
        ))
        conn.commit()
        conn.close()
        print(f"✓ شرکت‌کننده جدید ثبت شد: {participant_id}")
        return True
    except Exception as e:
        print(f"❌ خطا در ثبت شرکت‌کننده: {e}")
        return False


def get_participant(participant_id: str) -> dict | None:
    """
    خواندن اطلاعات یک شرکت‌کننده.
    Returns: dict یا None اگر پیدا نشد.
    """
    try:
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(
            "SELECT * FROM participants_web WHERE participant_id = ?",
            (participant_id,)
        )
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        print(f"❌ خطا در خواندن شرکت‌کننده: {e}")
        return None

def save_hexaco_data(
    participant_id: str,
    answers: dict,
    scores: dict,
) -> bool:
    """
    ذخیره‌ی پاسخ‌ها و نمرات HEXACO.
    """
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute('''
            INSERT OR REPLACE INTO web_hexaco
            (participant_id, answers_json, scores_json, completed_at)
            VALUES (?, ?, ?, ?)
        ''', (
            participant_id,
            json.dumps(answers, ensure_ascii=False),
            json.dumps(scores, ensure_ascii=False),
            time.time(),
        ))
        conn.commit()
        conn.close()
        print(f"✓ HEXACO ذخیره شد برای {participant_id}")
        return True
    except Exception as e:
        print(f"❌ خطا در ذخیره HEXACO: {e}")
        return False

def save_crt_data(participant_id: str, answers: dict, result: dict) -> bool:
    """ذخیره‌ی پاسخ‌ها و نتیجه‌ی CRT"""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute('''
            INSERT OR REPLACE INTO web_crt
            (participant_id, answers_json, result_json, completed_at)
            VALUES (?, ?, ?, ?)
        ''', (
            participant_id,
            json.dumps(answers, ensure_ascii=False),
            json.dumps(result, ensure_ascii=False),
            time.time(),
        ))
        conn.commit()
        conn.close()
        print(f"✓ CRT ذخیره شد برای {participant_id}")
        return True
    except Exception as e:
        print(f"❌ خطا در ذخیره CRT: {e}")
        return False


def save_sd3_data(participant_id: str, answers: dict, scores: dict) -> bool:
    """ذخیره‌ی پاسخ‌ها و نمرات SD3"""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute('''
            INSERT OR REPLACE INTO web_sd3
            (participant_id, answers_json, scores_json, completed_at)
            VALUES (?, ?, ?, ?)
        ''', (
            participant_id,
            json.dumps(answers, ensure_ascii=False),
            json.dumps(scores, ensure_ascii=False),
            time.time(),
        ))
        conn.commit()
        conn.close()
        print(f"✓ SD3 ذخیره شد برای {participant_id}")
        return True
    except Exception as e:
        print(f"❌ خطا در ذخیره SD3: {e}")
        return False


def save_social_desirability_data(
    participant_id: str, answers: dict, result: dict
) -> bool:
    """ذخیره‌ی پاسخ‌ها و نتیجه‌ی مطلوبیت اجتماعی"""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute('''
            INSERT OR REPLACE INTO web_social_desirability
            (participant_id, answers_json, result_json, completed_at)
            VALUES (?, ?, ?, ?)
        ''', (
            participant_id,
            json.dumps(answers, ensure_ascii=False),
            json.dumps(result, ensure_ascii=False),
            time.time(),
        ))
        conn.commit()
        conn.close()
        print(f"✓ مطلوبیت اجتماعی ذخیره شد برای {participant_id}")
        return True
    except Exception as e:
        print(f"❌ خطا در ذخیره مطلوبیت اجتماعی: {e}")
        return False


def save_feedback_data(
    participant_id: str,
    close_answers: dict,
    open_answers: dict,
    demographic_extra: dict,
    scores: dict,
) -> bool:
    """ذخیره‌ی بازخورد پس از بازی"""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute('''
            INSERT OR REPLACE INTO web_feedback
            (participant_id, close_answers_json, open_answers_json,
             demographic_extra_json, scores_json, completed_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            participant_id,
            json.dumps(close_answers, ensure_ascii=False),
            json.dumps(open_answers, ensure_ascii=False),
            json.dumps(demographic_extra, ensure_ascii=False),
            json.dumps(scores, ensure_ascii=False),
            time.time(),
        ))
        conn.commit()
        conn.close()
        print(f"✓ بازخورد ذخیره شد برای {participant_id}")
        return True
    except Exception as e:
        print(f"❌ خطا در ذخیره بازخورد: {e}")
        return False

def log_evidence_web(
    participant_id: str, scenario_id: str, competency: str,
    evidence_key: str, evidence_value: float, weight: float = 1.0,
) -> bool:
    """ثبت یک شاهد رفتاری"""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute('''
            INSERT INTO web_evidence
            (participant_id, scenario_id, competency,
             evidence_key, evidence_value, weight, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            participant_id, scenario_id, competency,
            evidence_key, evidence_value, weight, time.time(),
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ خطا در ثبت شاهد: {e}")
        return False


def update_relationship_web(
    participant_id: str, character_key: str, delta: int
) -> bool:
    """افزایش/کاهش مقدار رابطه با یک شخصیت (محدوده -3 تا +3)"""
    try:
        conn = get_connection()
        c = conn.cursor()
        # دریافت مقدار فعلی
        c.execute(
            "SELECT value FROM web_relationships "
            "WHERE participant_id = ? AND character_key = ?",
            (participant_id, character_key)
        )
        row = c.fetchone()
        current = row[0] if row else 0
        new_value = max(-3, min(3, current + delta))
        c.execute('''
            INSERT OR REPLACE INTO web_relationships
            (participant_id, character_key, value)
            VALUES (?, ?, ?)
        ''', (participant_id, character_key, new_value))
        conn.commit()
        conn.close()
        print(f"   [REL] {character_key}: {current} → {new_value}")
        return True
    except Exception as e:
        print(f"❌ خطا در ثبت رابطه: {e}")
        return False


def get_relationships_web(participant_id: str) -> dict:
    """دریافت تمام روابط فعلی"""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "SELECT character_key, value FROM web_relationships "
            "WHERE participant_id = ?",
            (participant_id,)
        )
        rows = c.fetchall()
        conn.close()
        result = {"li": 0, "rahimi": 0, "artemis": 0}
        for key, val in rows:
            result[key] = val
        return result
    except Exception as e:
        print(f"❌ خطا در خواندن روابط: {e}")
        return {"li": 0, "rahimi": 0, "artemis": 0}

def record_choice_batch(
    participant_id: str,
    session_id: str,
    scenario_id: str,
    competency: str,
    choice_id: int,
    decision_time_ms: int,
    choice_metadata: dict,
    evidence_items: list,
    relationship_deltas: dict,
) -> bool:
    """
    ثبت یکپارچه‌ی همه‌ی اثرات یک انتخاب در یک تراکنش.
    (شواهد + رویداد + روابط — همه با هم)
    """
    try:
        conn = get_connection()
        c = conn.cursor()
        now = time.time()

        # ۱. شواهد
        for ev in evidence_items:
            c.execute('''
                INSERT INTO web_evidence
                (participant_id, scenario_id, competency,
                 evidence_key, evidence_value, weight, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                participant_id, scenario_id, competency,
                ev["evidence_key"], ev["evidence_value"],
                ev["weight"], now,
            ))

        # ۲. رویداد
        c.execute('''
            INSERT INTO web_events
            (participant_id, session_id, event_type, scenario_id,
             choice_id, decision_time_ms, metadata, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            participant_id, session_id, 'choice_made', scenario_id,
            choice_id, decision_time_ms,
            json.dumps(choice_metadata, ensure_ascii=False),
            now,
        ))

        # ۳. روابط
        for char_key, delta in relationship_deltas.items():
            if delta == 0:
                continue
            c.execute(
                "SELECT value FROM web_relationships "
                "WHERE participant_id = ? AND character_key = ?",
                (participant_id, char_key),
            )
            row = c.fetchone()
            current = row[0] if row else 0
            new_value = max(-3, min(3, current + delta))
            c.execute('''
                INSERT OR REPLACE INTO web_relationships
                (participant_id, character_key, value)
                VALUES (?, ?, ?)
            ''', (participant_id, char_key, new_value))
            print(f"   [REL] {char_key}: {current} → {new_value}")

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ خطا در ثبت یکپارچه: {e}")
        return False

def get_choice_memory(participant_id: str) -> dict:
    """
    خواندن حافظه‌ی تصمیم‌ها — {scenario_id: choice_id}
    اگر یک سناریو چند بار انتخاب شده، آخرین انتخاب برگردانده می‌شود.
    """
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT scenario_id, choice_id FROM web_events
            WHERE participant_id = ?
              AND event_type = 'choice_made'
            ORDER BY timestamp ASC
        """, (participant_id,))
        result = {}
        for sid, cid in c.fetchall():
            result[sid] = cid
        conn.close()
        return result
    except Exception as e:
        print(f"❌ خطا در خواندن حافظه‌ی تصمیم: {e}")
        return {}

# ============================================================
# نامه به خود
# ============================================================
def save_self_letter(
    participant_id: str, content: str
) -> bool:
    """
    ذخیره‌ی نامه به خود در جدول web_self_letters.
    جدول در صورت نبود، خودکار ساخته می‌شود.
    """
    try:
        conn = get_connection()
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS web_self_letters (
                letter_id INTEGER PRIMARY KEY AUTOINCREMENT,
                participant_id TEXT NOT NULL,
                content TEXT,
                word_count INTEGER DEFAULT 0,
                created_at REAL
            )
        """)

        word_count = (
            len(content.split()) if content.strip() else 0
        )
        c.execute("""
            INSERT INTO web_self_letters
            (participant_id, content, word_count, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            participant_id, content, word_count, time.time(),
        ))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"⚠️ save_self_letter: {e}")
        return False


# ============================================================
# پیشرفت فاز (Resume)
# ============================================================
def save_phase_progress(
    participant_id: str,
    phase_key: str,
    scenario_index: int,
    state: dict,
) -> bool:
    """
    ذخیره‌ی وضعیت پیشرفت فاز (برای resume).
    """
    try:
        conn = get_connection()
        c = conn.cursor()

        # ساخت جدول با اسکیمای نهایی
        c.execute("""
            CREATE TABLE IF NOT EXISTS web_phase_progress (
                participant_id TEXT NOT NULL,
                phase_key TEXT NOT NULL,
                current_scenario_index INTEGER DEFAULT 0,
                state_json TEXT NOT NULL,
                updated_at REAL,
                PRIMARY KEY (participant_id, phase_key)
            )
        """)

        # Migration: اگر جدول قدیمی بدون این ستون ساخته شده بود
        try:
            c.execute(
                "ALTER TABLE web_phase_progress "
                "ADD COLUMN current_scenario_index "
                "INTEGER DEFAULT 0"
            )
        except sqlite3.OperationalError:
            pass  # ستون از قبل وجود دارد

        c.execute("""
            INSERT OR REPLACE INTO web_phase_progress
            (participant_id, phase_key, current_scenario_index,
             state_json, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            participant_id, phase_key, int(scenario_index),
            json.dumps(state, ensure_ascii=False),
            time.time(),
        ))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ خطا در ذخیره پیشرفت: {e}")
        return False


def get_phase_progress(
    participant_id: str, phase_key: str
) -> dict | None:
    """
    خواندن وضعیت پیشرفت فاز.

    Returns:
        dict با کلیدهای:
            - state_json: JSON خام
            - state: dict پارس‌شده
            - current_scenario_index: عدد
            - ... (سایر ستون‌ها)
        یا None اگر نبود.
    """
    try:
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            SELECT * FROM web_phase_progress
            WHERE participant_id = ? AND phase_key = ?
        """, (participant_id, phase_key))
        row = c.fetchone()
        conn.close()

        if not row:
            return None

        result = dict(row)
        if result.get("state_json"):
            try:
                result["state"] = json.loads(
                    result["state_json"]
                )
            except (ValueError, TypeError):
                result["state"] = {}
        return result
    except Exception as e:
        print(f"❌ خطا در خواندن پیشرفت: {e}")
        return None

# ============================================================
# زیرمؤلفه‌ها (Sub-competencies)
# ============================================================
def save_sub_competency_scores(
    participant_id: str, scores: dict
) -> bool:
    """
    ذخیره‌ی نمرات زیرمؤلفه‌ای.
    scores = {
        "honesty": {"transparency": {"score": 85.0, "count": 3}, ...},
        ...
    }
    """
    try:
        conn = get_connection()
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS web_sub_competency_scores (
                participant_id TEXT NOT NULL,
                competency TEXT NOT NULL,
                sub_competency TEXT NOT NULL,
                score REAL,
                evidence_count INTEGER,
                PRIMARY KEY (
                    participant_id, competency, sub_competency
                )
            )
        """)

        for competency, subs in scores.items():
            for sub_key, data in subs.items():
                c.execute("""
                    INSERT OR REPLACE INTO web_sub_competency_scores
                    (participant_id, competency, sub_competency,
                     score, evidence_count)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    participant_id, competency, sub_key,
                    float(data.get("score", 0.0)),
                    int(data.get("count", 0)),
                ))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"⚠️ save_sub_competency_scores: {e}")
        return False


def get_sub_competency_scores(participant_id: str) -> dict:
    """
    خواندن نمرات زیرمؤلفه‌ای.
    Returns: {competency: {sub: {"score": float, "count": int}}}
    """
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT competency, sub_competency, score, evidence_count
            FROM web_sub_competency_scores
            WHERE participant_id = ?
        """, (participant_id,))
        rows = c.fetchall()
        conn.close()
        result: dict = {}
        for comp, sub, score, cnt in rows:
            result.setdefault(comp, {})[sub] = {
                "score": float(score or 0.0),
                "count": int(cnt or 0),
            }
        return result
    except Exception as e:
        print(f"⚠️ get_sub_competency_scores: {e}")
        return {}

# ============================================================
# طرح‌واره‌های استدلالی (MRL)
# ============================================================
VALID_SCHEMAS = {
    "personal_interest",
    "maintaining_norms",
    "postconventional",
}


def log_schema_evidence(
    participant_id: str,
    scenario_id: str,
    choice_id: int,
    schema_primary: str,
    schema_secondary: str = "",
    reaction_time_ms: int = 0,
) -> bool:
    """
    ثبت طرح‌واره‌ی استدلالی برای یک انتخاب.
    """
    if schema_primary not in VALID_SCHEMAS:
        print(f"⚠️ طرح‌واره‌ی نامعتبر: {schema_primary}")
        return False

    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS web_schema_evidence (
                evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
                participant_id TEXT NOT NULL,
                scenario_id TEXT,
                choice_id INTEGER,
                schema_primary TEXT,
                schema_secondary TEXT,
                reaction_time_ms INTEGER DEFAULT 0,
                created_at REAL
            )
        """)
        c.execute("""
            INSERT INTO web_schema_evidence
            (participant_id, scenario_id, choice_id,
             schema_primary, schema_secondary,
             reaction_time_ms, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            participant_id, scenario_id, int(choice_id),
            schema_primary, schema_secondary or "",
            int(reaction_time_ms), time.time(),
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"⚠️ log_schema_evidence: {e}")
        return False


def get_schema_distribution(participant_id: str) -> dict:
    """
    توزیع طرح‌واره‌ها برای شرکت‌کننده.
    """
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT schema_primary, COUNT(*)
            FROM web_schema_evidence
            WHERE participant_id = ?
            GROUP BY schema_primary
        """, (participant_id,))
        rows = c.fetchall()
        conn.close()

        dist = {
            "personal_interest": 0,
            "maintaining_norms": 0,
            "postconventional": 0,
        }
        for key, count in rows:
            if key in dist:
                dist[key] = int(count)
        dist["total"] = sum(
            dist[k] for k in [
                "personal_interest",
                "maintaining_norms",
                "postconventional",
            ]
        )
        return dist
    except Exception as e:
        print(f"⚠️ get_schema_distribution: {e}")
        return {
            "personal_interest": 0,
            "maintaining_norms": 0,
            "postconventional": 0,
            "total": 0,
        }

# ============================================================
# آزمون برج هانوی
# ============================================================
def save_tower_of_hanoi(
    participant_id: str,
    trial_id: int,
    metrics: dict,
    move_log: list,
) -> bool:
    """ذخیره‌ی یک تلاش ToH در دیتابیس."""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS web_tower_of_hanoi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                participant_id TEXT NOT NULL,
                trial_id INTEGER,
                solved INTEGER,
                valid_moves INTEGER,
                invalid_attempts INTEGER,
                efficiency REAL,
                planning_time_ms INTEGER,
                execution_time_ms INTEGER,
                total_time_ms INTEGER,
                move_log_json TEXT,
                completed_at REAL
            )
        """)
        c.execute("""
            INSERT INTO web_tower_of_hanoi
            (participant_id, trial_id, solved, valid_moves,
             invalid_attempts, efficiency, planning_time_ms,
             execution_time_ms, total_time_ms, move_log_json,
             completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            participant_id, int(trial_id),
            1 if metrics.get("solved") else 0,
            int(metrics.get("valid_moves", 0)),
            int(metrics.get("invalid_attempts", 0)),
            float(metrics.get("efficiency", 0.0)),
            int(metrics.get("planning_time_ms", 0)),
            int(metrics.get("execution_time_ms", 0)),
            int(metrics.get("total_time_ms", 0)),
            json.dumps(move_log, ensure_ascii=False),
            time.time(),
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"⚠️ save_tower_of_hanoi: {e}")
        return False


def get_tower_of_hanoi(participant_id: str) -> dict | None:
    """آخرین تلاش ToH شرکت‌کننده."""
    try:
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT trial_id, solved, valid_moves,
                   invalid_attempts, efficiency,
                   planning_time_ms, execution_time_ms,
                   total_time_ms
            FROM web_tower_of_hanoi
            WHERE participant_id = ?
            ORDER BY id DESC LIMIT 1
        """, (participant_id,))
        row = c.fetchone()
        conn.close()
        if not row:
            return None
        return {
            "trial_id": row[0],
            "solved": bool(row[1]),
            "valid_moves": row[2],
            "invalid_attempts": row[3],
            "efficiency": row[4],
            "planning_time_ms": row[5],
            "execution_time_ms": row[6],
            "total_time_ms": row[7],
        }
    except Exception as e:
        print(f"⚠️ get_tower_of_hanoi: {e}")
        return None
