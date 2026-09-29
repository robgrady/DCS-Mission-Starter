"""The squadron kit: how a virtual squadron takes a course away.

WHAT IS IN IT, AND WHY NOT THE MISSIONS
---------------------------------------
    Program.pdf     the printed syllabus — cover, how it works, every
                      school / phase / unit in order with what is graded,
                      what is planned and why, and the readings verbatim
    Gradesheet.csv    one row per ride and reading, columns for a grade,
                      an instructor's initials and a date — the thing a
                      training officer actually keeps
    readings/*.md     the chapters, as markdown, for the squadron's own
                      wiki or Discord

No .miz files. v1.78.1 took the in-request mission build out of the
product because eleven missions built inside a download brought the server
down; a course is forty-five rides. The missions come from each track's own
download and each card's own button, which also means the squadron always
gets the current build rather than a zip that aged on a shared drive.

The readings are rendered into the PDF by a small markdown walker below —
headings, paragraphs, bullets, bold/italic — because the chapters are prose
and a PDF that only linked to them would be a program without the ground
school in it.
"""
from __future__ import annotations

import csv
import io
import re
import zipfile
from pathlib import Path

from . import courses as _courses
from .aar_guide import (Doc, esc, S_TITLE, S_SUB, S_H1, S_H2, S_P, S_SMALL,
                        S_MONO, S_RIDE, NAVY, RULE)
from . import authentic as _auth
S_CELL = _auth.styles()["cell"]

from reportlab.platypus import Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.units import mm
from reportlab.lib import colors

# The USAF item scale, and the check-ride result. The sim's coaches print
# the same letters (checkride.py, timing_coach in check mode), so the card
# in the cockpit and the row on this sheet speak one language.
GRADE_SCALE = ("U — out of parameters, not corrected", "F — out, recognised and corrected",
               "G — in parameters, small timely corrections", "E — in, corrections almost invisible")
CHECK_SCALE = ("Q — qualified", "Q- — qualified with discrepancies", "U — re-fly")


# --------------------------------------------------------------------------- #
# markdown -> flowables (the subset the readings use)
# --------------------------------------------------------------------------- #
def _inline(text: str) -> str:
    t = esc(text)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", t)
    t = re.sub(r"`(.+?)`", r"<font face='IBMPlexMono'>\1</font>", t)
    return t


def md_flowables(md: str) -> list:
    out, para = [], []

    def flush():
        if para:
            out.append(Paragraph(_inline(" ".join(para)), S_P))
            out.append(Spacer(1, 2 * mm))
            para.clear()

    for line in md.splitlines():
        s = line.rstrip()
        if not s.strip():
            flush()
            continue
        if s.startswith("# "):
            flush()
            out.append(Paragraph(_inline(s[2:]), S_H1))
            out.append(_auth.section_rule())
        elif s.startswith("## "):
            flush()
            out.append(Spacer(1, 2 * mm))
            out.append(Paragraph(_inline(s[3:]), S_H2))
        elif s.startswith("### "):
            flush()
            out.append(Paragraph(_inline(s[4:]), S_RIDE))
        elif s.lstrip().startswith("- "):
            flush()
            out.append(Paragraph("•&nbsp;&nbsp;" + _inline(s.lstrip()[2:]), S_P))
        elif s.startswith("*") and s.endswith("*") and not s.startswith("**"):
            flush()
            out.append(Paragraph(_inline(s), S_SMALL))
            out.append(Spacer(1, 2 * mm))
        else:
            para.append(s.strip())
    flush()
    return out


# --------------------------------------------------------------------------- #
# the program
# --------------------------------------------------------------------------- #
def program_pdf(course: dict, version: str, out_path: Path) -> Path:
    doc = Doc(str(out_path), f"{course['label']} — Sortie Starter v{version}",
              locator="SORTIE STARTER / SQUADRON KIT")
    F = []
    A = F.append
    A(Paragraph(esc(course["label"]), S_TITLE))
    A(Paragraph(f"Training program · {esc(course.get('module') or '')} · "
                f"Sortie Starter v{version}", S_SUB))
    A(Spacer(1, 4 * mm))
    A(Paragraph(esc(course.get("premise", "")), S_P))
    if course.get("blurb"):
        A(Paragraph(esc(" ".join(course["blurb"])), S_P))
    c = course["counts"]
    A(Spacer(1, 3 * mm))
    A(Paragraph(f"{c['units']} units · {c['rides']} rides · {c['readings']} readings · "
                f"{c['planned']} planned (shown, not hidden).", S_SMALL))

    # --- the syllabus table ------------------------------------------------ #
    A(Spacer(1, 5 * mm))
    A(Paragraph("The syllabus", S_H1))
    A(_auth.section_rule())
    A(Paragraph("Fly the schools in order; a school's rides assume the one "
                "before it. A unit marked GRADED carries a coach in the "
                "mission and opens a scorecard; every other unit is graded "
                "by the instructor against the brief.", S_P))
    for s in course["schools"]:
        A(Spacer(1, 3 * mm))
        A(Paragraph(f"School {s['n']} — {esc(s['label'])}", S_H2))
        A(Paragraph(f"<i>{esc(s.get('tagline', ''))}</i> {esc(s.get('intro', ''))}", S_P))
        rows = [["Phase", "Unit", "Rides", "Graded"]]
        for p in s["phases"]:
            for u in p["units"]:
                ph = Paragraph(esc(p["label"]), S_CELL)
                if u["kind"] == "planned":
                    rows.append([ph, Paragraph(f"PLANNED — {esc(u['label'])}. <i>{esc(u.get('why', ''))}</i>", S_CELL), "—", "—"])
                elif u["kind"] == "reading":
                    rows.append([ph, Paragraph(f"Reading — {esc(u['label'])}", S_CELL),
                                 f"{u.get('minutes') or ''} min", "—"])
                else:
                    lab = esc(u["label"])
                    if u.get("check"):
                        lab = f"CHECK RIDE — {lab}"
                    rows.append([ph, Paragraph(lab, S_CELL),
                                 str(u.get("rides", 1)), "yes" if u.get("graded") else "IP"])
        t = Table(rows, colWidths=[34 * mm, 104 * mm, 14 * mm, 16 * mm], repeatRows=1)
        t.setStyle(TableStyle([
            ("FONT", (0, 0), (-1, 0), _auth.register_fonts()["subhead"], 8.5),
            ("FONT", (0, 1), (-1, -1), _auth.register_fonts()["sans"], 8),
            ("TEXTCOLOR", (0, 0), (-1, 0), NAVY),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, 0), 0.8, NAVY),
            ("LINEBELOW", (0, 1), (-1, -1), 0.3, RULE),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("TOPPADDING", (0, 0), (-1, -1), 3),
        ]))
        A(t)

    # --- the gradesheet ---------------------------------------------------- #
    A(PageBreak())
    A(Paragraph("Gradesheet", S_H1))
    A(_auth.section_rule())
    A(Paragraph("One row per ride, graded per item the way an instructor "
                "grades: U / F / G / E against the brief on the ride. Where the "
                "mission opens its own card — the coached rides' score, or a "
                "check ride's letters — record it in the Sim column; the IP "
                "column is for what the sim cannot see (line, corrections, the "
                "radio, the brief). A check ride's overall result is Q, Q- or U. "
                "The same rows ship as Gradesheet.csv.", S_P))
    A(Paragraph(" · ".join(GRADE_SCALE), S_SMALL))
    A(Paragraph(" · ".join(CHECK_SCALE), S_SMALL))
    A(Spacer(1, 3 * mm))
    rows = [["#", "Unit", "Ride", "Sim", "IP", "Q/Q-/U", "Date"]]
    for i, r in enumerate(_courses.gradesheet_rows(course), start=1):
        if r["kind"] == "planned":
            continue
        rows.append([str(i), Paragraph(esc(r["unit"]), S_MONO),
                     Paragraph(("CHECK — " if r["check"] else "") + esc(r["label"]), S_CELL),
                     "", "", "", ""])
    t = Table(rows, colWidths=[8 * mm, 40 * mm, 72 * mm, 12 * mm, 12 * mm, 12 * mm, 16 * mm],
              repeatRows=1)
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), _auth.register_fonts()["subhead"], 8.5),
        ("FONT", (0, 1), (-1, -1), _auth.register_fonts()["sans"], 8),
        ("TEXTCOLOR", (0, 0), (-1, 0), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.3, RULE),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    A(t)

    # --- the readings, verbatim ------------------------------------------- #
    for s in course["schools"]:
        for p in s["phases"]:
            for u in p["units"]:
                if u["kind"] != "reading":
                    continue
                md = _courses.reading_text(u["doc"]) or ""
                A(PageBreak())
                F += md_flowables(md)

    A(PageBreak())
    A(Paragraph("Where the missions are", S_H1))
    A(_auth.section_rule())
    A(Paragraph("This kit deliberately carries no mission files. Each track "
                "has its own one-click download of every ride as a .miz with "
                "a printed brief, and each card generates on its own button — "
                "so the squadron always flies the current build rather than a "
                "zip that aged on a shared drive. Open the pipeline page, click "
                "a unit, download.", S_P))
    doc.build(F)
    return out_path


def gradesheet_csv(course: dict) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["n", "school", "phase", "unit", "kind", "ride_key", "label",
                "check_ride", "sim_grade_UFGE", "ip_grade_UFGE", "check_result_Q_Qminus_U",
                "instructor", "date", "notes"])
    for i, r in enumerate(_courses.gradesheet_rows(course), start=1):
        w.writerow([i, r["school"], r["phase"], r["unit"], r["kind"], r["ride"],
                    r["label"], "yes" if r["check"] else "", "", "", "", "", "", ""])
    return buf.getvalue()


def build_kit(course_id: str, version: str, out_dir: Path) -> Path:
    """Program.pdf + Gradesheet.csv + readings/*.md, zipped. Returns the zip."""
    course = _courses.resolve(course_id)
    if not course:
        raise ValueError(f"unknown course {course_id!r}")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf = program_pdf(course, version, out_dir / "Program.pdf")
    zpath = out_dir / f"{course_id}_kit.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(pdf, "Program.pdf")
        z.writestr("Gradesheet.csv", gradesheet_csv(course))
        for s in course["schools"]:
            for p in s["phases"]:
                for u in p["units"]:
                    if u["kind"] == "reading":
                        z.writestr(f"readings/{u['doc']}.md", _courses.reading_text(u["doc"]) or "")
        z.writestr("README.txt",
                   f"{course['label']} — squadron kit, Sortie Starter v{version}\n\n"
                   "Program.pdf   the printed syllabus, gradesheet and readings\n"
                   "Gradesheet.csv  one row per ride, for the training officer\n"
                   "readings/       the chapters as markdown\n\n"
                   "No missions in here on purpose: download each track and card from the "
                   "pipeline page so you always fly the current build.\n")
    return zpath
