import os
import json
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
)
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display

from web_app.db_manager import get_connection


BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
FONT_PATH = os.path.join(
    BASE_DIR, "assets", "fonts", "Vazirmatn-Regular.ttf"
)

try:
    pdfmetrics.registerFont(TTFont("Vazirmatn", FONT_PATH))
except Exception as e:
    print(f"⚠️ خطا در بارگذاری فونت: {e}")


def fa(text) -> str:
    if not text:
        return ""
    reshaped = arabic_reshaper.reshape(str(text))
    result = get_display(reshaped)
    if isinstance(result, bytes):
        return result.decode("utf-8")
    return str(result)


def _get_columns(cur, table: str) -> list:
    try:
        cur.execute(f"PRAGMA table_info({table})")
        return [row[1] for row in cur.fetchall()]
    except Exception:
        return []


def _read_row(cur, table: str, participant_id: str) -> dict | None:
    try:
        cols = _get_columns(cur, table)
        if not cols:
            return None
        cur.execute(
            f"SELECT * FROM {table} WHERE participant_id = ?",
            (participant_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return dict(zip(cols, row))
    except Exception as e:
        print(f"   [PDF] خطا در {table}: {e}")
        return None


def _extract_from_json(
    row: dict, json_keys: list, score_keys: list,
):
    for k in json_keys:
        if k in row and row[k]:
            try:
                data = json.loads(row[k])
                if isinstance(data, dict):
                    for sk in score_keys:
                        if sk in data:
                            return data[sk]
                elif isinstance(data, (int, float)):
                    return data
            except Exception:
                pass
    for sk in score_keys:
        if sk in row and row[sk] is not None:
            return row[sk]
    return None


def generate_pdf_report(participant_id: str) -> str | None:
    try:
        os.makedirs("reports", exist_ok=True)
        filepath = f"reports/Truthline_Report_{participant_id}.pdf"

        doc = SimpleDocTemplate(
            filepath, pagesize=A4,
            rightMargin=40, leftMargin=40,
            topMargin=40, bottomMargin=40,
        )
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            name="TitleStyle",
            parent=styles["Heading1"],
            fontName="Vazirmatn", fontSize=20,
            alignment=2, spaceAfter=20,
            textColor=colors.HexColor("#0B1D3A"),
        )
        h2_style = ParagraphStyle(
            name="H2Style",
            parent=styles["Heading2"],
            fontName="Vazirmatn", fontSize=14,
            alignment=2, spaceBefore=15, spaceAfter=10,
            textColor=colors.HexColor("#0B1D3A"),
        )
        body_style = ParagraphStyle(
            name="BodyStyle",
            parent=styles["Normal"],
            fontName="Vazirmatn", fontSize=11,
            alignment=2, spaceAfter=8, leading=18,
        )

        story = []
        story.append(Paragraph(fa("گزارش ارزیابی شایستگی‌های عملیاتی"), title_style))
        story.append(Paragraph(fa(f"شناسه شرکت‌کننده: {participant_id}"), body_style))
        story.append(Paragraph(fa(f"تاریخ: {datetime.now().strftime('%Y-%m-%d')}"), body_style))
        story.append(Spacer(1, 15))

        conn = get_connection()
        cur = conn.cursor()

        # ---- ۱. شایستگی‌ها ----
        story.append(Paragraph(fa("۱. نمرات شایستگی‌های اصلی (از ۱۰۰)"), h2_style))
        cur.execute("""
            SELECT competency,
                   SUM(evidence_value * weight) /
                       NULLIF(SUM(weight), 0) * 100 as score,
                   COUNT(*) as cnt
            FROM web_evidence
            WHERE participant_id = ?
            GROUP BY competency
        """, (participant_id,))
        comps = cur.fetchall()
        comp_names = {
            "honesty": "صداقت و یکپارچگی",
            "trustworthiness": "قابلیت اعتماد",
            "problem_solving": "حل مسئله",
            "accountability": "مسئولیت‌پذیری",
        }
        for comp, score, count in comps:
            score_val = score or 0
            story.append(Paragraph(
                fa(f"• {comp_names.get(comp, comp)}: {score_val:.1f} (بر اساس {count} شاهد)"),
                body_style,
            ))
        story.append(Spacer(1, 10))

        # ---- ۲. پرسشنامه‌ها ----
        story.append(Paragraph(fa("۲. خلاصه نتایج پرسشنامه‌ها"), h2_style))

        row = _read_row(cur, "web_hexaco", participant_id)
        if row:
            print(f"   [PDF-DEBUG] web_hexaco: {list(row.keys())}")
            scores = _extract_from_json(
                row,
                ["scores_json", "hexaco_scores", "data_json"],
                ["H", "E", "X", "A", "C", "O"],
            )
            if isinstance(scores, dict):
                story.append(Paragraph(
                    fa(
                        f"• HEXACO: صداقت-تواضع: {scores.get('H', 0)} | "
                        f"هیجان‌پذیری: {scores.get('E', 0)} | "
                        f"برون‌گرایی: {scores.get('X', 0)} | "
                        f"خوشایندی: {scores.get('A', 0)} | "
                        f"وظیفه‌شناسی: {scores.get('C', 0)} | "
                        f"گشودگی: {scores.get('O', 0)}"
                    ),
                    body_style,
                ))

        row = _read_row(cur, "web_crt", participant_id)
        if row:
            print(f"   [PDF-DEBUG] web_crt: {list(row.keys())}")
            crt_score = _extract_from_json(
                row,
                ["crt_data", "result_json", "data_json", "crt_data_json"],
                ["score", "crt_score", "total_score"],
            )
            if crt_score is not None:
                story.append(Paragraph(
                    fa(f"• آزمون تأمل شناختی (CRT): {crt_score} از ۷"),
                    body_style,
                ))

        row = _read_row(cur, "web_sd3", participant_id)
        if row:
            print(f"   [PDF-DEBUG] web_sd3: {list(row.keys())}")
            scores = _extract_from_json(
                row,
                ["scores_json", "sd3_scores", "data_json"],
                ["machiavellianism", "narcissism", "psychopathy"],
            )
            if isinstance(scores, dict):
                story.append(Paragraph(
                    fa(
                        f"• SD3: ماکیاولیسم: {scores.get('machiavellianism', 0)} | "
                        f"خودشیفتگی: {scores.get('narcissism', 0)} | "
                        f"سایکوپاتی: {scores.get('psychopathy', 0)}"
                    ),
                    body_style,
                ))

        row = _read_row(cur, "web_social_desirability", participant_id)
        if row:
            print(f"   [PDF-DEBUG] web_social_desirability: {list(row.keys())}")
            sd_score = _extract_from_json(
                row,
                ["result_json", "sd_data", "data_json", "social_desirability"],
                ["score", "total_score"],
            )
            if sd_score is not None:
                story.append(Paragraph(
                    fa(f"• مطلوبیت اجتماعی: {sd_score} از ۹"),
                    body_style,
                ))

        story.append(Spacer(1, 10))

        # ---- ۳. تفسیر ----
        story.append(Paragraph(fa("۳. جمع‌بندی و پیشنهادات"), h2_style))
        if comps:
            avg = sum((s or 0) for _, s, _ in comps) / len(comps)
            if avg >= 70:
                advice = "پروفایل شما بسیار قوی است. توصیه می‌شود در موقعیت‌های رهبری نقش فعال‌تری بپذیرید."
            elif avg >= 50:
                advice = "پروفایل شما متعادل است. با تمرکز بر نقاط قابل بهبود، می‌توانید به سطوح بالاتری دست یابید."
            else:
                advice = "توصیه می‌شود در تصمیم‌گیری‌ها زمان بیشتری صرف کنید و از بازخورد همکاران استفاده نمایید."
            story.append(Paragraph(fa(advice), body_style))

        conn.close()
        doc.build(story)
        print(f"   [PDF] ✓ ساخته شد: {filepath}")
        return filepath
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"⚠️ خطا در تولید PDF: {e}")
        return None