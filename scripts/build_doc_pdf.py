#!/usr/bin/env python3
"""Render a Markdown document as an Authentic Style PDF.

    python3 scripts/build_doc_pdf.py docs/<name>.md [docs/<Out>.pdf]

Front matter (optional, --- fenced at the top of the file) sets the cover:

    title:    the banner line
    subtitle: the line under it
    locator:  the right-hand text in the navy band
    summary:  a paragraph under the rule

WHY A BUILDER AND NOT A ONE-OFF
-------------------------------
The product's rule for every generated document is that the Markdown is the
source and the rendered file is a build artifact (`scripts/artifacts.py`).
This review is a long strategy document that will keep changing while the
Squadron platform is planned, so it gets a builder rather than a hand-made
PDF that would be stale the next time a paragraph moves.

    python3 scripts/build_squadron_pdf.py

WHAT IT REUSES, AND WHAT IT ADDS
--------------------------------
Page furniture is `authentic.make_doc` via `aar_guide.Doc` — the same navy
band, hairline footer and type scale as every other generated document
(Authentic Style v2.1). Nothing about the look is invented here.

`course_kit.md_flowables` already walks the Markdown subset the readings use:
headings, paragraphs, bullets, bold/italic. This document also carries
TABLES, FENCED CODE BLOCKS, BLOCKQUOTES and NUMBERED LISTS — a strategy
review argues in tables — so the walker is extended for those four. The
extension lives here rather than in `course_kit` because the readings do not
need it and a shared walker that grows for one caller is how a helper turns
into a second engine.
"""
from __future__ import annotations

import datetime as _dt
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from reportlab.lib import colors                                  # noqa: E402
from reportlab.lib.units import mm                                # noqa: E402
from reportlab.platypus import (Paragraph, Spacer, Table,         # noqa: E402
                                TableStyle, KeepTogether)

from missiongen import authentic as _auth                         # noqa: E402
from missiongen.aar_guide import (Doc, esc, S_TITLE, S_SUB, S_H1,  # noqa: E402
                                  S_H2, S_P, S_SMALL, S_RIDE, NAVY, RULE)

SRC = ROOT / "docs" / "squadron-training-architecture.md"      # default
OUT = None                                                     # derived from SRC

_S = _auth.styles()
S_CELL = _S["cell"]
_F = _auth.register_fonts()
_H = _auth.hexes()
PANEL = colors.HexColor(_H["panel"])
DIM = colors.HexColor(_H["dim"])
INK = colors.HexColor(_H["ink"])
ACCENT = colors.HexColor(_H["accent"])
CAUTION = colors.HexColor(_H.get("caution", "#B45309"))

# Code and quote styles — the two roles the reading walker has no need for.
from reportlab.lib.styles import ParagraphStyle                    # noqa: E402
S_CODE = ParagraphStyle("code", fontName=_F["mono"], fontSize=7.2, leading=9.6,
                        textColor=INK)
S_QUOTE = ParagraphStyle("quote", fontName=_F["sans"], fontSize=9.2, leading=13,
                         textColor=INK)
S_HEAD = ParagraphStyle("thead", fontName=_F["subhead"], fontSize=8.2,
                        leading=10.5, textColor=NAVY)


def _inline(text: str) -> str:
    """Markdown inline -> ReportLab markup. Code spans are held aside first so
    a `**` inside backticks is not read as bold."""
    holds: list = []

    def hold(m):
        holds.append(esc(m.group(1)))
        return f"\x00{len(holds) - 1}\x00"

    t = re.sub(r"`(.+?)`", hold, text)
    t = esc(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", t)
    t = re.sub(r"\[(.+?)\]\((.+?)\)", r"\1", t)     # links: keep the words
    for i, c in enumerate(holds):
        t = t.replace(f"\x00{i}\x00", f"<font face='{_F['mono']}' size=8.4>{c}</font>")
    return t


def front_matter(md: str) -> tuple:
    """Split an optional `---` fenced YAML-ish header off the top of the file.
    Only flat `key: value` pairs — this is a cover block, not a config format."""
    if not md.startswith("---"):
        return {}, md
    end = md.find("\n---", 3)
    if end == -1:
        return {}, md
    meta = {}
    for line in md[3:end].splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, md[end + 4:].lstrip("\n")


def _image(path: Path, width: float):
    """A figure, scaled to the column and never taller than half the page so a
    diagram cannot orphan the prose that explains it."""
    from reportlab.platypus import Image as RLImage
    from PIL import Image as PILImage
    iw, ih = PILImage.open(path).size
    w = width
    h = w * ih / iw
    cap = 118 * mm
    if h > cap:
        h, w = cap, cap * iw / ih
    return RLImage(str(path), width=w, height=h)


def _cells(line: str) -> list:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _table(rows: list, width: float) -> Table:
    """A standard Authentic table: subhead header in navy over a rule, sans
    body, hairlines between rows. Column widths are proportional to the
    longest cell in each column, so a table of one-word verdicts beside a
    column of prose does not get equal thirds."""
    ncol = max(len(r) for r in rows)
    rows = [r + [""] * (ncol - len(r)) for r in rows]
    weights = [max(len(r[c]) for r in rows) ** 0.62 for c in range(ncol)]
    total = sum(weights) or 1
    widths = [max(14 * mm, width * w / total) for w in weights]
    over = sum(widths) - width
    if over > 0:                       # give the excess back to the widest column
        widths[widths.index(max(widths))] -= over
    data = [[Paragraph(_inline(c), S_HEAD if i == 0 else S_CELL) for c in r]
            for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("TEXTCOLOR", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, NAVY),
        ("LINEBELOW", (0, 1), (-1, -2), 0.3, RULE),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


_BOX = str.maketrans({"┌": "+", "┐": "+", "└": "+", "┘": "+", "├": "+",
                      "┤": "+", "┬": "+", "┴": "+", "┼": "+",
                      "─": "-", "│": "|", "═": "=", "║": "|",
                      "╔": "+", "╗": "+", "╚": "+", "╝": "+",
                      "▶": ">", "◀": "<", "▲": "^", "▼": "v"})


def _code(lines: list, width: float) -> Table:
    """A fenced block: mono on the panel tint, in a one-cell table so it keeps
    its background across a page break."""
    # Box-drawing characters are not in the embedded mono subset, so they fall
    # back to a proportional face and the diagram's right edge goes ragged.
    # Translated to ASCII they align exactly, which is the point of the block.
    lines = [l.translate(_BOX) for l in lines]
    body = "<br/>".join(esc(l).replace(" ", "&nbsp;") for l in lines)
    t = Table([[Paragraph(body, S_CODE)]], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PANEL),
        ("LINEBEFORE", (0, 0), (0, -1), 1.6, colors.HexColor(_H["navy"])),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def _quote(lines: list, width: float) -> Table:
    """A blockquote: the decisions callout. Caution rule on the left, because
    in this document every quote is Rob deciding something."""
    # A quote carrying a numbered list must keep its numbers on their own
    # lines; joined into one blob the decisions read as a wall.
    # Breaks go in AFTER the inline pass: _inline escapes markup, so a <br/>
    # inserted before it renders as the literal characters.
    body = _inline(" ".join(lines))
    body = re.sub(r"\s+(\d+\.\s)", r"<br/><br/>\1", body)
    t = Table([[Paragraph(body, S_QUOTE)]], colWidths=[width])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FDF6E9")),
        ("LINEBEFORE", (0, 0), (0, -1), 1.8, CAUTION),
        ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t


def flowables(md: str, width: float) -> list:
    out: list = []
    para: list = []
    tbl: list = []
    code: list = []
    quote: list = []
    item: list = []          # the list item being accumulated
    item_lead = [""]         # its bullet or number, kept out of the wrap
    in_code = False
    title_seen = False

    def flush_item():
        """A Markdown list item is hard-wrapped across several source lines.
        Rendered one line per Paragraph, the continuations lose the indent and
        fall back to the margin — so the item is buffered and emitted once,
        with the bullet as a real bullet so the hanging indent holds."""
        if item:
            out.append(Paragraph(_inline(" ".join(item)), _S["bullet"],
                                 bulletText=item_lead[0]))
            item.clear()

    def flush():
        flush_item()
        if para:
            out.append(Paragraph(_inline(" ".join(para)), S_P))
            para.clear()

    def flush_table():
        if tbl:
            out.append(Spacer(1, 1.5 * mm))
            out.append(_table(list(tbl), width))
            out.append(Spacer(1, 3.5 * mm))
            tbl.clear()

    def flush_quote():
        if quote:
            out.append(Spacer(1, 1 * mm))
            out.append(_quote(list(quote), width))
            out.append(Spacer(1, 3.5 * mm))
            quote.clear()

    def close():
        flush()          # flushes the pending list item first
        flush_table()
        flush_quote()

    for raw in md.splitlines():
        s = raw.rstrip()

        if s.strip().startswith("```"):
            if not in_code:
                close()
                in_code = True
            else:
                in_code = False
                out.append(Spacer(1, 1.5 * mm))
                out.append(_code(code, width))
                out.append(Spacer(1, 3.5 * mm))
                code = []
            continue
        if in_code:
            code.append(raw)
            continue

        if not s.strip():
            close()
            continue

        img = re.match(r"^!\[[^\]]*\]\(([^)]+)\)\s*$", s)
        if img:
            close()
            p = (SRC.parent / img.group(1)).resolve()
            if p.is_file():
                out.append(Spacer(1, 2 * mm))
                out.append(_image(p, width))
                out.append(Spacer(1, 4 * mm))
            continue

        if s.startswith("# "):
            if not title_seen:          # the H1 is the cover title, set below
                title_seen = True
                continue
            close()
            out.append(Paragraph(_inline(s[2:]), S_H1))
            out.append(_auth.section_rule())
        elif s.startswith("## "):
            close()
            out.append(Spacer(1, 3 * mm))
            out.append(KeepTogether([Paragraph(_inline(s[3:]), S_H1),
                                     _auth.section_rule()]))
        elif s.startswith("### "):
            close()
            out.append(Spacer(1, 1 * mm))
            out.append(Paragraph(_inline(s[4:]), S_H2))
        elif s.startswith(">"):
            flush()
            flush_table()
            # a bare ">" is a blank line INSIDE the quote, not content
            if s.strip() != ">":
                quote.append(s[2:] if s.startswith("> ") else s[1:])
        elif s.startswith("|") and s.count("|") >= 2:
            flush()
            flush_quote()
            if re.match(r"^\|[\s:|-]+\|$", s):      # the ---|--- separator
                continue
            tbl.append(_cells(s))
        elif re.match(r"^\d+\. ", s):
            close()
            n, txt = s.split(". ", 1)
            item_lead[0] = f"{n}."
            item.append(txt)
        elif s.lstrip().startswith("- "):
            close()
            item_lead[0] = "\u2022"
            item.append(s.lstrip()[2:])
        elif item and raw[:1] in (" ", "\t"):
            item.append(s.strip())          # a wrapped continuation of the item
        elif s.startswith("---"):
            close()
        elif (s.startswith("*") and s.endswith("*") and not s.startswith("**")
              and not para and not item):
            # a standalone italic line is a caption; one CONTINUING a paragraph
            # is just an italic phrase and must stay in the prose
            close()
            out.append(Paragraph(_inline(s.strip("*")), S_SMALL))
        else:
            if tbl:                     # prose after a table ends the table
                flush_table()
            if quote:
                quote.append(s.strip())
            else:
                para.append(s.strip())
    close()
    return out


def build(src: Path = None, out: Path = None) -> Path:
    global SRC
    SRC = Path(src) if src else SRC
    raw = SRC.read_text()
    meta, md = front_matter(raw)
    out = Path(out) if out else SRC.with_suffix(".pdf")

    # Front matter may carry `version:`; otherwise the document is stamped with
    # its own revision date. A paper about a SEPARATE product must not inherit
    # Sortie Starter's release number — that would date it to the wrong thing.
    stamp = meta.get("version") or _dt.date.today().isoformat()

    title = meta.get("title") or SRC.stem.replace("-", " ").title()
    ident = f"{title} — {meta['subtitle']}" if meta.get("subtitle") else title
    doc = Doc(str(out), f"{ident} · {stamp}",
              locator=meta.get("locator", "SQUADRON PLATFORM / DOCUMENT"))
    width = doc.width

    story = [Paragraph(esc(title), S_TITLE)]
    if meta.get("subtitle"):
        story.append(Paragraph(esc(meta["subtitle"]), S_SUB))
    story += [_auth.section_rule(), Spacer(1, 2 * mm)]
    if meta.get("summary"):
        story += [Paragraph(esc(meta["summary"]), S_SUB), Spacer(1, 3 * mm)]
    story += flowables(md, width)
    doc.build(story)
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    p = build(Path(a[0]) if a else None, Path(a[1]) if len(a) > 1 else None)
    print(f"wrote {p} ({p.stat().st_size:,} bytes)")
