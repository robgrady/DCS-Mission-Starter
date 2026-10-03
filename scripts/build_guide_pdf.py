#!/usr/bin/env python3
"""Build the professional PDF user guide (docs/DCS_Mission_Starter_Guide.pdf).
Rerun whenever docs content changes: python scripts/build_guide_pdf.py"""
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph,
                                Spacer, Table, TableStyle, PageBreak,
                                KeepTogether, Image as RLImage)
from PIL import Image as PILImage
import sys as _sys
_sys.path.insert(0, str(Path(__file__).parent.parent))
_sys.path.insert(0, str(Path(__file__).parent.parent / "vendor"))
from missiongen import __version__ as APP_VERSION

OUT = Path(__file__).parent.parent / "docs" / "DCS_Mission_Starter_Guide.pdf"
IMG = Path(__file__).parent.parent / "docs" / "img"

# AUTHENTIC STYLE v2.1 — palette and faces from missiongen/authentic.py, the
# same furniture every other generated document draws.
from missiongen import authentic as _auth
_H = _auth.hexes()
_F = _auth.register_fonts()
NAVY = HexColor(_H["navy"])
NAVY2 = HexColor(_H["accent"])
GOLD = HexColor(_H["dim"])     # legacy name; the specimen's Dim — no gold accent
BLUE = HexColor(_H["accent"])
INK = HexColor(_H["ink"])
DIM = HexColor(_H["dim"])
LINE = HexColor(_H["rule"])
PANEL = HexColor(_H["panel"])
W, H = letter

_S = _auth.styles()
styles = {
    "h1": _S["h1"],
    "h2": _S["h2"],
    "h3": ParagraphStyle("h3", fontName=_F["subhead"], fontSize=10.5, leading=14,
                         textColor=INK, spaceBefore=9, spaceAfter=2),
    "body": _S["p"],
    "bullet": _S["bullet"],
    "note": _S["note"],
    "tagline": _S["tag"],
}


def header_footer(canvas, doc):
    canvas.saveState()
    # the navy band: identity left, locator right, mono white
    canvas.setFillColor(NAVY)
    canvas.rect(0, H - 0.55 * inch, W, 0.55 * inch, fill=1, stroke=0)
    canvas.setFillColor(white)
    canvas.setFont(_F["mono_bold"], 8)
    canvas.drawString(0.75 * inch, H - 0.34 * inch, f"DCS SORTIE STARTER  ·  V{APP_VERSION}  ·  USER GUIDE")
    canvas.setFont(_F["mono"], 8)
    canvas.drawRightString(W - 0.75 * inch, H - 0.34 * inch, "SORTIE STARTER / GUIDE")
    # footer: hairline, mono
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(0.75 * inch, 0.62 * inch, W - 0.75 * inch, 0.62 * inch)
    canvas.setFillColor(DIM)
    canvas.setFont(_F["mono"], 7.4)
    canvas.drawString(0.75 * inch, 0.45 * inch,
                      "SELECT, DON'T SEARCH  ·  WE SET THE STAGE — YOU WRITE THE PLAY")
    canvas.drawRightString(W - 0.75 * inch, 0.45 * inch,
                           f"{_auth.NOT_AFFILIATED}  ·  page {doc.page}")
    canvas.restoreState()


def cover(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)
    canvas.setFillColor(NAVY2)
    canvas.rect(0, H - 4.4 * inch, W, 2.6 * inch, fill=1, stroke=0)
    canvas.setStrokeColor(white)
    canvas.setLineWidth(1)
    canvas.line(0.9 * inch, H - 4.55 * inch, W - 0.9 * inch, H - 4.55 * inch)
    canvas.setFillColor(white)
    canvas.setFont(_F["banner"], 40)
    canvas.drawString(0.9 * inch, H - 2.85 * inch, "DCS SORTIE")
    canvas.drawString(0.9 * inch, H - 3.45 * inch, "STARTER")
    canvas.setFont(_F["section"], 15)
    canvas.drawString(0.9 * inch, H - 4.05 * inch, "USER GUIDE")
    canvas.setFillColor(HexColor("#C7D2E6"))
    canvas.setFont(_F["sans"], 12)
    canvas.drawString(0.9 * inch, H - 5.1 * inch,
                      "Pick a map, an era, and an aircraft — fly a living world in minutes.")
    canvas.drawString(0.9 * inch, H - 5.35 * inch,
                      "Airfields dressed. SAMs up. The strike group at sea. Your flight plan stays yours.")
    canvas.setFont(_F["mono"], 9)
    canvas.setFillColor(HexColor("#9DB0CC"))
    canvas.drawString(0.9 * inch, 1.6 * inch, f"VERSION {APP_VERSION}")
    canvas.drawString(0.9 * inch, 1.4 * inch,
                      "Developed by Authentic Media LLC  ·  robgrady.com  ·  "
                      "provided as-is - no warranty, no liability  ·  " + _auth.NOT_AFFILIATED)
    canvas.restoreState()


def t(data, widths, header=True):
    tbl = Table(data, colWidths=widths, hAlign="LEFT")
    style = [
        ("FONTNAME", (0, 0), (-1, -1), _F["sans"]),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, PANEL]),
    ]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), NAVY),
                  ("TEXTCOLOR", (0, 0), (-1, 0), white),
                  ("FONTNAME", (0, 0), (-1, 0), _F["subhead"])]
    tbl.setStyle(TableStyle(style))
    return tbl


def P(text, s="body"):
    return Paragraph(text, styles[s])


def shot(name, caption, width=6.6 * inch, max_h=8.1 * inch):
    """Screenshot with caption, scaled to width but capped in height so tall
    single-screen captures still fit on the page, kept together."""
    path = IMG / name
    if not path.exists():
        return Spacer(1, 1)
    w, h = PILImage.open(path).size
    disp_w, disp_h = width, width * h / w
    if disp_h > max_h:                      # scale down to fit the page height
        disp_h, disp_w = max_h, max_h * w / h
    img = RLImage(str(path), width=disp_w, height=disp_h)
    cap = Paragraph(caption, ParagraphStyle(
        "cap", fontName=_F["sans"], fontSize=8.5, leading=11,
        textColor=DIM, alignment=TA_CENTER, spaceBefore=3, spaceAfter=10))
    return KeepTogether([img, cap])


def B(text):
    return Paragraph(f"•  {text}", styles["bullet"])


def inline(text):
    """Render the manual's Markdown inline grammar with escaped PDF markup."""
    import html, re
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<font name='" + _F["mono"] + r"'>\1</font>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", text)
    text = re.sub(r"\[([^]]+)\]\((https?://[^)]+)\)", r'<link href="\2" color="'+_H["accent"]+r'">\1</link>', text)
    return text


def manual_story(path):
    """The Markdown manual is the sole prose source for the download."""
    import re
    rows = path.read_text().splitlines()
    result = [PageBreak()]
    paragraph = []
    def flush():
        if paragraph:
            result.append(P(inline(' '.join(paragraph))))
            paragraph.clear()
    i = 0
    while i < len(rows):
        line = rows[i].strip()
        if not line:
            flush(); i += 1; continue
        if line.startswith('|'):
            flush(); data = []
            while i < len(rows) and rows[i].strip().startswith('|'):
                cells = rows[i].strip().strip('|').split('|')
                if not all(re.fullmatch(r'[: -]+', c) for c in cells):
                    data.append([P(inline(c.strip()), 'note') for c in cells])
                i += 1
            if data:
                widths = [(W - 1.5 * inch) / len(data[0])] * len(data[0])
                result.append(t(data, widths)); result.append(Spacer(1, 8))
            continue
        if line.startswith('```'):
            flush(); i += 1
            while i < len(rows) and not rows[i].strip().startswith('```'):
                result.append(P(inline('`'+rows[i]+'`'), 'note')); i += 1
            i += 1; continue
        heading = re.match(r'^(#{1,3}) +(.+)', line)
        if heading:
            flush()
            if len(heading[1]) > 1:
                result.append(P(inline(heading[2]), 'h'+str(len(heading[1])-1)))
            i += 1; continue
        bullet = re.match(r'^(?:[-*] |(\d+)\. )(.+)', line)
        if bullet:
            flush(); text = bullet[2]; i += 1
            while i < len(rows) and rows[i].startswith('   ') and rows[i].strip():
                text += ' ' + rows[i].strip(); i += 1
            result.append(P(inline((bullet[1]+'. ' if bullet[1] else '• ')+text), 'bullet'))
            continue
        paragraph.append(line); i += 1
    flush()
    result += [PageBreak(), P('Builder reference', 'h1'),
               shot('hero.png', 'The Builder: choose the theater and era.'),
               PageBreak(), shot('review.png', 'Review the recipe before generating your mission kit.')]
    return result

story = manual_story(OUT.parent / 'USER_GUIDE.md')

doc = BaseDocTemplate(str(OUT), pagesize=letter,
                      leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                      topMargin=0.85 * inch, bottomMargin=0.8 * inch,
                      title=f"DCS Sortie Starter — User Guide v{APP_VERSION}",  # version in
                      # the PDF metadata so a test can assert the shipped guide
                      # matches the release without needing a PDF text parser
                      author="Rob Grady")
frame = Frame(0.75 * inch, 0.8 * inch, W - 1.5 * inch, H - 1.65 * inch, id="main")
doc.addPageTemplates([
    PageTemplate(id="cover", frames=[Frame(0, 0, W, H)], onPage=cover),
    PageTemplate(id="page", frames=[frame], onPage=header_footer),
])

from reportlab.platypus import NextPageTemplate
story.insert(0, NextPageTemplate("page"))
doc.build(story)
print(f"built {OUT} ({OUT.stat().st_size} bytes)")
