"""Authentic Style v2.1 — the ONE page furniture for every generated document.

WHY
---
Rob (6 Sep 2026) supplied the full-system specimen
(`docs/brand/authentic-style-specimen.pdf`): "This is the style guide for
pdf files generated. All documentation such as mission briefs should be
generated and displayed with this style." Before this module the product
had three renderers with three furnitures — the PIL brief, the ReportLab
track guides, the user guide — each carrying its own Helvetica and its own
hex values. This file is where the specimen lives; the renderers import it.

THE SYSTEM (from the specimen, verbatim)
----------------------------------------
  Type roles
    Bangers                      banner title — H1 only
    Barlow Condensed ExtraBold   SECTION (uppercase, rule under)
    Barlow Condensed Bold        subhead / navy band
    Source Serif 4               body prose — findings, ride cards
    Source Sans 3                UI, taglines, notes, captions
    IBM Plex Mono                identifiers, flags, hashes, data

  Brand / neutrals / semantic
    Navy #00205B · Accent #1D4E89 · Paper #FFFFFF · Panel #F4F6F8
    Ink #101828 · Dim #475467 · Danger #9F1239 · Warn #B45309 · Ok #067647

  Pills / states   INFO · PASS · CAUTION · FAIL
  Chart series     Okabe–Ito, data only

  Page: a navy band across the top carrying mono white text — the document
  identity left, the locator right; the banner title below it in Bangers;
  a hairline rule footer with mono text left and "Not affiliated with
  Eagle Dynamics" right.

The colors come from `data/brand/flightline.json` (updated to v2.1), so
PIL renderers and the site read the same numbers; this module adds the
ReportLab side — font registration, paragraph styles, the page template,
pills — and the PIL band/section/pill helpers, so a brief page and a guide
page are drawn by the same hands.

FONT EMBEDDING
--------------
Source Sans 3 and Source Serif 4 are vendored as VARIABLE fonts. ReportLab
embeds a variable font's default instance (Regular), which is the weight
the specimen uses for prose; bold serif is not needed and bold sans comes
from Barlow. Every registration degrades to Helvetica rather than failing:
a document with the wrong face beats a mission that did not build.
"""
from __future__ import annotations

import functools
from pathlib import Path

from .brand import tokens

FONT_DIR = Path(__file__).parent / "data" / "brand" / "fonts"

# ReportLab font names, by role. Registered once by register_fonts().
RL = {
    "banner": "Bangers",
    "section": "BarlowCondensed-ExtraBold",
    "subhead": "BarlowCondensed-Bold",
    "serif": "SourceSerif4",
    "serif_bold": "SourceSerif4-Bold",
    "sans": "SourceSans3",
    "sans_bold": "SourceSans3-Bold",
    "mono": "IBMPlexMono",
    "mono_bold": "IBMPlexMono-Bold",
}
# Static instances of the two variable fonts, cut with fontTools
# (scripts/cut_static_fonts.py) so ReportLab — which embeds only a variable
# font's default instance — has a real bold for <b> inside prose.
_FILES = {
    "Bangers": "Bangers-Regular.ttf",
    "BarlowCondensed-ExtraBold": "BarlowCondensed-ExtraBold.ttf",
    "BarlowCondensed-Bold": "BarlowCondensed-Bold.ttf",
    "SourceSerif4": "SourceSerif4-Regular.ttf",
    "SourceSerif4-Bold": "SourceSerif4-Bold.ttf",
    "SourceSans3": "SourceSans3-Regular.ttf",
    "SourceSans3-Bold": "SourceSans3-Bold.ttf",
    "IBMPlexMono": "IBMPlexMono-Regular.ttf",
    "IBMPlexMono-Bold": "IBMPlexMono-Bold.ttf",
}
_FALLBACK = {"Bangers": "Helvetica-Bold", "BarlowCondensed-ExtraBold": "Helvetica-Bold",
             "BarlowCondensed-Bold": "Helvetica-Bold", "SourceSerif4": "Times-Roman",
             "SourceSerif4-Bold": "Times-Bold", "SourceSans3": "Helvetica",
             "SourceSans3-Bold": "Helvetica-Bold", "IBMPlexMono": "Courier",
             "IBMPlexMono-Bold": "Courier-Bold"}

NOT_AFFILIATED = "Not affiliated with Eagle Dynamics"


def hexes() -> dict:
    """The document palette as hex strings, from the token file."""
    c = tokens()["colors"]
    return {"navy": c["navy"], "accent": c["accent"], "paper": c["paper"],
            "panel": c["panel"], "ink": c["ink"], "dim": c["slate"],
            "danger": c["warning"], "warn": c["caution"], "ok": c["ok"],
            "rule": c["rule"], "white": c["white"]}


@functools.lru_cache(maxsize=1)
def register_fonts() -> dict:
    """Register the vendored faces with ReportLab. Returns {role: font name
    actually usable} — the fallback name where a file failed to load."""
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase.pdfmetrics import registerFontFamily
    out = {}
    for role, name in RL.items():
        try:
            if name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(name, str(FONT_DIR / _FILES[name])))
            out[role] = name
        except Exception:
            out[role] = _FALLBACK[name]
    # <b> inside a paragraph resolves through the family, not the face.
    try:
        registerFontFamily(out["serif"], normal=out["serif"], bold=out["serif_bold"],
                           italic=out["serif"], boldItalic=out["serif_bold"])
        registerFontFamily(out["sans"], normal=out["sans"], bold=out["sans_bold"],
                           italic=out["sans"], boldItalic=out["sans_bold"])
        registerFontFamily(out["mono"], normal=out["mono"], bold=out["mono_bold"],
                           italic=out["mono"], boldItalic=out["mono_bold"])
    except Exception:
        pass
    return out


@functools.lru_cache(maxsize=1)
def styles() -> dict:
    """ReportLab paragraph styles for every type role."""
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    f = register_fonts()
    h = hexes()
    ink, dim, navy, accent = (colors.HexColor(h[k]) for k in ("ink", "dim", "navy", "accent"))
    return {
        "title": ParagraphStyle("title", fontName=f["banner"], fontSize=27, leading=30,
                                textColor=navy, spaceAfter=3),
        "sub": ParagraphStyle("sub", fontName=f["sans"], fontSize=11.5, leading=15.5,
                              textColor=dim, spaceAfter=12),
        "h1": ParagraphStyle("h1", fontName=f["section"], fontSize=14.5, leading=17,
                             textColor=ink, spaceBefore=16, spaceAfter=6),
        "h2": ParagraphStyle("h2", fontName=f["subhead"], fontSize=11.5, leading=14,
                             textColor=navy, spaceBefore=10, spaceAfter=3),
        "p": ParagraphStyle("p", fontName=f["serif"], fontSize=9.9, leading=14.4,
                            textColor=ink, spaceAfter=6),
        "small": ParagraphStyle("small", fontName=f["sans"], fontSize=8.8, leading=12,
                                textColor=dim, spaceAfter=5),
        # table cells: sans, INK — a table is data, not a caption
        "cell": ParagraphStyle("cell", fontName=f["sans"], fontSize=8.4, leading=11,
                               textColor=ink),
        "mono": ParagraphStyle("mono", fontName=f["mono"], fontSize=7.6, leading=9.8,
                               textColor=ink),
        "ride": ParagraphStyle("ride", fontName=f["subhead"], fontSize=10.8, leading=13.5,
                               textColor=ink, spaceBefore=9, spaceAfter=1),
        "tag": ParagraphStyle("tag", fontName=f["sans"], fontSize=11, leading=15,
                              textColor=accent, spaceAfter=8),
        "note": ParagraphStyle("note", fontName=f["sans"], fontSize=9.4, leading=13,
                               textColor=dim, leftIndent=10, spaceAfter=6),
        "bullet": ParagraphStyle("bullet", fontName=f["serif"], fontSize=9.9, leading=14.4,
                                 textColor=ink, leftIndent=14, bulletIndent=4, spaceAfter=3),
    }


def section_rule():
    """The hairline under a SECTION head."""
    from reportlab.lib import colors
    from reportlab.platypus.flowables import HRFlowable
    return HRFlowable(width="100%", thickness=0.6, color=colors.HexColor(hexes()["rule"]),
                      spaceBefore=0, spaceAfter=6)


PILLS = {
    "INFO": ("panel", "accent"), "PASS": ("#E6F4EA", "ok"),
    "CAUTION": ("#FDF1DC", "warn"), "FAIL": ("#FDE7EC", "danger"),
}


def pill(text: str, kind: str = "INFO"):
    """A state pill: mono bold on a tinted panel. Kind is INFO/PASS/CAUTION/FAIL."""
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle, Paragraph
    from reportlab.lib.styles import ParagraphStyle
    f = register_fonts()
    h = hexes()
    bg, fg = PILLS.get(kind.upper(), PILLS["INFO"])
    bg = h.get(bg, bg)
    st = ParagraphStyle("pill", fontName=f["mono_bold"], fontSize=8, leading=10,
                        textColor=colors.HexColor(h[fg]))
    t = Table([[Paragraph(text, st)]], colWidths=[None])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(bg)),
                           ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                           ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                           ("ROUNDEDCORNERS", [5, 5, 5, 5])]))
    return t


def make_doc(path: str, identity: str, locator: str, footer_left: str = "",
             pagesize=None, margins_mm=(19, 19, 19, 17)):
    """A BaseDocTemplate with the Authentic page: navy band (identity left,
    locator right, mono white), hairline footer (left text, right the
    non-affiliation line, page number)."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate
    f = register_fonts()
    h = hexes()
    ps = pagesize or A4
    W, H = ps
    lm, rm, tm, bm = (x * mm for x in margins_mm)
    band = 13 * mm

    class _Doc(BaseDocTemplate):
        def __init__(self):
            super().__init__(path, pagesize=ps, leftMargin=lm, rightMargin=rm,
                             topMargin=tm + band, bottomMargin=bm,
                             title=identity, author="Sortie Starter")
            fr = Frame(lm, bm, W - lm - rm, H - tm - band - bm, id="f")
            self.addPageTemplates([PageTemplate(id="p", frames=[fr], onPage=self._deco)])
            self.footer = footer_left

        def _deco(self, c, d):
            from reportlab.pdfbase.pdfmetrics import stringWidth
            usable = W - lm - rm

            def fit(text, font, size, room):
                """Cut `text` with an ellipsis so it fits `room` points."""
                if stringWidth(text, font, size) <= room:
                    return text
                while text and stringWidth(text + "…", font, size) > room:
                    text = text[:-1]
                return text.rstrip(" ·—-") + "…"

            c.saveState()
            c.setFillColor(colors.HexColor(h["navy"]))
            c.rect(0, H - band, W, band, fill=1, stroke=0)
            c.setFillColor(colors.white)
            loc = locator.upper()
            loc_w = stringWidth(loc, f["mono"], 7.6)
            c.setFont(f["mono_bold"], 7.6)
            c.drawString(lm, H - band + 4.6 * mm,
                         fit(identity.upper(), f["mono_bold"], 7.6, usable - loc_w - 8 * mm))
            c.setFont(f["mono"], 7.6)
            c.drawRightString(W - rm, H - band + 4.6 * mm, loc)
            c.setStrokeColor(colors.HexColor(h["rule"]))
            c.setLineWidth(0.5)
            c.line(lm, 13.5 * mm, W - rm, 13.5 * mm)
            c.setFillColor(colors.HexColor(h["dim"]))
            c.setFont(f["mono"], 7.2)
            tail = f"{NOT_AFFILIATED}  ·  page {c.getPageNumber()}"
            tail_w = stringWidth(tail, f["mono"], 7.2)
            c.drawString(lm, 9.5 * mm,
                         fit(footer_left.upper(), f["mono"], 7.2, usable - tail_w - 8 * mm))
            c.drawRightString(W - rm, 9.5 * mm, tail)
            c.restoreState()

    return _Doc()


# --------------------------------------------------------------------------- #
# PIL side — the brief and the kneeboard draw the same furniture
# --------------------------------------------------------------------------- #
def pil_band(d, W, identity: str, locator: str, font_mono, band_h: int = 52,
             pad: int = 60, top: int = 0):
    """The navy band with mono white identity (left) and locator (right)."""
    from .brand import COLORS
    d.rectangle([0, top, W, top + band_h], fill=COLORS.navy)
    y = top + (band_h - font_mono.size) // 2 - 2
    d.text((pad, y), identity.upper(), font=font_mono, fill=COLORS.white)
    tw = d.textlength(locator.upper(), font=font_mono)
    d.text((W - pad - tw, y), locator.upper(), font=font_mono, fill=COLORS.white)


def pil_section(d, x, y, W, text: str, font_section, pad: int = 60) -> int:
    """SECTION head: Barlow ExtraBold uppercase with a hairline rule under.
    Returns the y below the rule."""
    from .brand import COLORS
    d.text((x, y), text.upper(), font=font_section, fill=COLORS.ink)
    yy = y + font_section.size + 10
    d.line([x, yy, W - pad, yy], fill=COLORS.rule, width=2)
    return yy + 14


def pil_pill(d, x, y, text: str, kind: str, font_mono_bold) -> int:
    """A state pill; returns the x after it."""
    from .brand import COLORS, _hex_rgb
    bg, fg = PILLS.get(kind.upper(), PILLS["INFO"])
    bgc = getattr(COLORS, bg) if not bg.startswith("#") else _hex_rgb(bg)
    fgc = getattr(COLORS, {"accent": "accent", "ok": "ok", "warn": "caution", "danger": "warning"}[fg])
    tw = d.textlength(text, font=font_mono_bold)
    h = font_mono_bold.size + 12
    d.rounded_rectangle([x, y, x + tw + 24, y + h], radius=h // 2, fill=bgc)
    d.text((x + 12, y + 5), text, font=font_mono_bold, fill=fgc)
    return int(x + tw + 24 + 10)
