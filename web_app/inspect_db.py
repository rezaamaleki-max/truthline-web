"""
بررسی جامع دیتابیس وب‌اپ
اجرا: python -m web_app.inspect_db
"""
import sqlite3
import os
import json
from collections import Counter

WEB_APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(WEB_APP_DIR, "data", "participants_web.db")

COMPETENCY_FA = {
    "honesty": "صداقت",
    "trustworthiness": "قابلیت اعتماد",
    "problem_solving": "حل مسئله",
    "accountability": "مسئولیت‌پذیری",
}


def inspect():
    if not os.path.exists(DB_PATH):
        print(f"❌ دیتابیس یافت نشد: {DB_PATH}")
        return

    print("=" * 70)
    print(f"📂 دیتابیس: {DB_PATH}")
    print("=" * 70)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    tables = [
        "participants_web", "web_events", "web_evidence",
        "web_relationships", "web_hexaco", "web_crt",
        "web_sd3", "web_social_desirability", "web_feedback",
        "web_phase_progress",
    ]
    print("\n📊 تعداد رکوردها:")
    print("-" * 40)
    for t in tables:
        try:
            cnt = cur.execute(
                f"SELECT COUNT(*) FROM {t}"
            ).fetchone()[0]
            status = "✅" if cnt > 0 else "⚠️"
            print(f"  {status} {t}: {cnt}")

        except sqlite3.OperationalError:
            print(f"  ❌ {t}: جدول نیست")

    # ---- توزیع شواهد بر اساس شایستگی ----
    print("\n🎯 توزیع شواهد بر اساس شایستگی:")
    print("-" * 40)
    try:
        cur.execute(
            "SELECT competency, COUNT(*) "
            "FROM web_evidence GROUP BY competency"
        )
        rows = cur.fetchall()
        if rows:
            for comp, cnt in rows:
                fa = COMPETENCY_FA.get(comp, comp)
                print(f"  {comp:<20} ({fa}): {cnt}")
        else:
            print("  (داده‌ای نیست)")

        # ✅ هشدار: شواهد فاز ۳ که در honesty ذخیره شده‌اند
        cur.execute("""
            SELECT COUNT(*) FROM web_evidence
            WHERE competency = 'honesty'
            AND scenario_id IN (
                'PID-02', 'MR-01', 'MR-02',
                'MC-02', 'CF-01', 'TR-01', 'TR-02',
                'BC-01', 'BC-02', 'CF-02',
                'PI-01', 'TC-02', 'PI-02',
                'RG-01', 'RG-02', 'AC-02'
            )
        """)
        wrong = cur.fetchone()[0]
        if wrong > 0:
            print()
            print(f"  🚨 {wrong} شاهد اشتباهاً در 'honesty' ثبت شده!")
            print(f"     این‌ها باید در فاز مربوطه‌ی خود باشند.")
    except sqlite3.OperationalError as e:
        print(f"  خطا: {e}")

    # ---- شواهد بر اساس سناریو ----
    print("\n📋 تعداد شواهد به تفکیک سناریو (آخرین ۲۰):")
    print("-" * 50)
    try:
        cur.execute("""
            SELECT scenario_id, competency, COUNT(*),
                   ROUND(AVG(evidence_value), 2)
            FROM web_evidence
            GROUP BY scenario_id, competency
            ORDER BY MAX(timestamp) DESC
            LIMIT 20
        """)
        for row in cur.fetchall():
            sid, comp, cnt, avg = row
            print(f"  {sid:<10} | {comp:<20} | "
                  f"count={cnt:>2} | avg={avg}")
    except Exception as e:
        print(f"  خطا: {e}")

    # ---- شرکت‌کنندگان ----
    print("\n👥 شرکت‌کنندگان (آخرین ۱۰):")
    print("-" * 50)
    try:
        cur.execute("""
            SELECT participant_id, session_id, created_at
            FROM participants_web
            ORDER BY created_at DESC LIMIT 10
        """)
        for row in cur.fetchall():
            pid, sid, ts = row
            is_test = "TEST_" if pid.startswith("TEST_") else "     "
            print(f"  {is_test}{pid[:8]}... | sid={sid[:8]}...")
    except Exception as e:
        print(f"  خطا: {e}")

    print("\n" + "=" * 70)
    conn.close()


def clear_test_data():
    """پاک کردن همه‌ی داده‌های TEST_ (قبل از تست واقعی)"""
    if not os.path.exists(DB_PATH):
        print(f"❌ دیتابیس یافت نشد: {DB_PATH}")
        return
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    tables_with_pid = [
        "web_events", "web_evidence", "web_relationships",
        "web_phase_progress",
    ]
    tables_with_pk = [
        "web_hexaco", "web_crt", "web_sd3",
        "web_social_desirability", "web_feedback",
    ]
    total = 0
    for t in tables_with_pid:
        cur.execute(
            f"DELETE FROM {t} WHERE participant_id LIKE 'TEST_%'"
        )
        total += cur.rowcount
    for t in tables_with_pk:
        cur.execute(
            f"DELETE FROM {t} WHERE participant_id LIKE 'TEST_%'"
        )
        total += cur.rowcount
    cur.execute(
        "DELETE FROM participants_web "
        "WHERE participant_id LIKE 'TEST_%'"
    )
    total += cur.rowcount
    conn.commit()
    conn.close()
    print(f"✓ {total} رکورد TEST_ پاک شد.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "clear":
        clear_test_data()
    else:
        inspect()