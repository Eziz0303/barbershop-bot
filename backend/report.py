import io
from datetime import date as date_type

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_NAME = "DejaVuSans"

pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))

STATUS_LABELS = {
    "pending": "Ожидает",
    "confirmed": "Подтверждена",
    "rejected": "Отклонена",
    "expired": "Просрочена",
    "cancelled": "Отменена",
}

HEADERS = ["Время", "Мастер", "Услуга", "Клиент", "Телефон", "Статус", "Цена"]


def generate_daily_report_pdf(rows: list[dict], report_date: date_type) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))

    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    title_style.fontName = FONT_NAME

    title = Paragraph(f"Записи на {report_date.strftime('%d.%m.%Y')}", title_style)

    data = [HEADERS]
    for r in rows:
        data.append(
            [
                r["time"],
                r["master"],
                r["service"],
                r["client"],
                r["phone"],
                STATUS_LABELS.get(r["status"], r["status"]),
                f"{r['price']} TMT",
            ]
        )
    if len(data) == 1:
        data.append(["—", "—", "—", "Записей нет", "—", "—", "—"])

    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#d4a34a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    doc.build([title, table])
    return buffer.getvalue()
