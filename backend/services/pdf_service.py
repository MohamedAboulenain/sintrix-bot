"""
PDF service:
  - extract_text()  — read PDF bytes → plain text (PyMuPDF)
  - generate_pdf()  — structured text → PDF bytes (ReportLab)
"""
from __future__ import annotations

import io
import textwrap


def extract_text(data: bytes) -> tuple[str, int]:
    """Return (full_text, page_count) from PDF bytes."""
    import fitz  # PyMuPDF
    doc = fitz.open(stream=data, filetype="pdf")
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n\n".join(pages), len(pages)


def generate_pdf(title: str, content: str) -> bytes:
    """Convert a title + markdown-ish text to a styled PDF."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
    from reportlab.lib.enums import TA_LEFT, TA_CENTER

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
    )

    styles = getSampleStyleSheet()
    NAVY = colors.HexColor("#0a0e27")
    CYAN = colors.HexColor("#22d3ee")

    title_style = ParagraphStyle(
        "KNXTitle",
        parent=styles["Title"],
        fontSize=22,
        textColor=NAVY,
        spaceAfter=6,
        alignment=TA_CENTER,
    )
    h1_style = ParagraphStyle(
        "KNXH1",
        parent=styles["Heading1"],
        fontSize=14,
        textColor=CYAN,
        spaceBefore=14,
        spaceAfter=4,
    )
    h2_style = ParagraphStyle(
        "KNXH2",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=NAVY,
        spaceBefore=10,
        spaceAfter=3,
    )
    body_style = ParagraphStyle(
        "KNXBody",
        parent=styles["Normal"],
        fontSize=10,
        leading=15,
        spaceAfter=6,
        alignment=TA_LEFT,
    )
    bullet_style = ParagraphStyle(
        "KNXBullet",
        parent=body_style,
        leftIndent=14,
        bulletIndent=0,
        spaceAfter=3,
    )

    story = []
    story.append(Paragraph(title, title_style))
    story.append(HRFlowable(width="100%", thickness=1, color=CYAN, spaceAfter=12))

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 6))
        elif stripped.startswith("## "):
            story.append(Paragraph(stripped[3:], h2_style))
        elif stripped.startswith("# "):
            story.append(Paragraph(stripped[2:], h1_style))
        elif stripped.startswith("- ") or stripped.startswith("* "):
            story.append(Paragraph(f"• {stripped[2:]}", bullet_style))
        elif stripped.startswith("**") and stripped.endswith("**"):
            story.append(Paragraph(f"<b>{stripped[2:-2]}</b>", body_style))
        else:
            # Wrap long lines
            wrapped = textwrap.fill(stripped, width=100)
            story.append(Paragraph(wrapped, body_style))

    doc.build(story)
    return buffer.getvalue()
