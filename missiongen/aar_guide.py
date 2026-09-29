"""The printed AAR Academy syllabus guide, built for ONE chosen combination.

WHY THIS IS GENERATED RATHER THAN WRITTEN: every word of instruction in here is
pulled from the same source the kneeboard is built from (`aar.brief_lines`,
`aar.hardware_lines`, `aar_grade.brief_lines`, and each card's own brief). A
printed guide written by hand drifts from the missions within one release and
then quietly lies. This one cannot.

WHY IT MOVED OUT OF scripts/: the Academy is now configurable — era, receiver
and tanker are the pilot's choice — so "the boom guide" is not one document.
A guide showing an F-16C sight picture to somebody flying the syllabus in a
Phantom is the say/do gap this product exists to avoid, so the guide is built
per request, for the combination actually downloaded.

reportlab is therefore a RUNTIME dependency now, not a build-time one. It is
pure Python and already needs Pillow, which ships.
"""

from pathlib import Path

from . import aar, aar_grade, aar_hud
from .resolver import load_json

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate,
                                Paragraph, Spacer, Preformatted,
                                PageBreak, KeepTogether, Image as RLImage,
                                Table, TableStyle)

ROOT = Path(__file__).parent.parent

# AUTHENTIC STYLE v2.1 (missiongen/authentic.py): the styles below are the
# one set every ReportLab document uses — this guide, the White Knights
# guide, the squadron kit. The names are kept so those importers need no
# change; the faces and colors are the specimen's.
from . import authentic as _auth

_S = _auth.styles()
_H = _auth.hexes()
INK = colors.HexColor(_H["ink"])
DIM = colors.HexColor(_H["dim"])
RULE = colors.HexColor(_H["rule"])
ACC = colors.HexColor(_H["accent"])
NAVY = colors.HexColor(_H["navy"])
PANEL = colors.HexColor(_H["panel"])

S_TITLE, S_SUB, S_H1, S_H2 = _S["title"], _S["sub"], _S["h1"], _S["h2"]
S_P, S_SMALL, S_MONO, S_RIDE = _S["p"], _S["small"], _S["mono"], _S["ride"]


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def rides_for(track_id):
    t = load_json("mission_templates")
    out = []
    for k, v in t.items():
        if k.startswith("_"):
            continue
        tr = v.get("track") or {}
        if tr.get("id") == track_id:
            out.append((tr["n"], k, v))
    return [x[1:] for x in sorted(out, key=lambda x: x[0])], \
           [x[0] for x in sorted(out, key=lambda x: x[0])]


def first_demand(brief):
    """The 'NEW DEMAND' line if the card states one, else its opening claim.
    Read from the card, never restated — a guide that paraphrases a brief is a
    second source of truth and one of them will be wrong."""
    for i, ln in enumerate(brief):
        if ln.startswith("NEW DEMAND"):
            s = ln
            j = i + 1
            while j < len(brief) and brief[j].strip():
                s += " " + brief[j].strip()
                j += 1
            return s
    return ""


def Doc(path, footer, locator="SORTIE STARTER / GUIDE"):
    """The Authentic page (navy band, hairline footer). `footer` is the
    document identity: it goes in the band on the left and, shortened, in
    the footer. Kept as a factory named Doc so callers are unchanged."""
    ident = footer.split(" — Sortie Starter")[0]
    return _auth.make_doc(path, identity=ident, locator=locator, footer_left=footer)


def build(track_id, track, version, out_dir=None, aircraft=None, tanker=None,
          era=None):
    """Render the guide for ONE combination. `aircraft`/`tanker`/`era` default
    to the track's own, which is what the committed default PDFs are."""
    cards, order = rides_for(track_id)
    lane = track["lane"]
    ac = aircraft or track["aircraft"]
    tanker = tanker or track["tanker"]
    era = era or (track.get("eras") or ["modern"])[0]
    mp = track.get("default_map") or "caucasus"
    label = track["label"]
    graded = sum(1 for _n, _k, v in
                 [(n, k, v) for n, (k, v) in zip(order, cards)]
                 if v.get("aar_grade"))
    total = len(cards)

    story = []
    A = story.append

    # ---- cover ------------------------------------------------------------
    A(Paragraph(esc(label), S_TITLE))
    A(Paragraph(f"{aircraft_label(ac)} &middot; "
                f"{esc(aar.TANKERS[tanker]['label'])} &middot; "
                f"{esc(_era_label(era))}", S_SUB))
    A(Paragraph(esc(track["premise"]), S_SUB))
    A(Paragraph(" ".join(esc(x) for x in track["blurb"]), S_P))

    A(Paragraph("How to use this", S_H1))
    A(Paragraph(
        "Fly the rides <b>in order</b>. Each one adds exactly one new demand, "
        "and the order is the point — the commonest way people fail to learn "
        "air refuelling is starting at the plug and then practicing being out "
        "of control.", S_P))
    A(Paragraph(
        "<b>Ten to twenty minutes at a time.</b> Stop after repeated large "
        "oscillations or frustration and come back later. High-quality "
        "repetitions beat an hour of survival behind a tanker, and the "
        "community figure for this skill is about thirty minutes a day for "
        "two weeks. It feels impossible until it abruptly does not.", S_P))
    A(Paragraph(
        "<b>End on something you did right</b> — a stable pre-contact, one "
        "clean plug, a controlled disconnect. And a reset is never a failed "
        "run: backing out deliberately is the procedure, not a surrender.", S_P))
    A(Paragraph(
        f"<b>What you need:</b> the {aircraft_label(ac)}, and nothing else. "
        f"Every ride in THIS copy of the syllabus is flown in it, behind a "
        f"{esc(aar.TANKERS[tanker]['label'])} at "
        f"<b>{aar.track_ias_kt(tanker, _type_id(ac))} KIAS, "
        f"{aar.track_alt_ft(tanker, mp):,} ft</b>, on free Caucasus in the "
        f"{esc(_era_label(era))} era. No mods, no scripts, no external tools.",
        S_P))
    A(Paragraph(
        "That combination was your choice at download, and this document was "
        "generated for it — the sight pictures, the track speed and the "
        "kneeboard cards below all describe the aircraft you actually picked "
        "rather than a default somebody else flew.", S_SMALL))

    A(Paragraph("What is graded, and what is not", S_H1))
    A(Paragraph(
        f"{graded} of the {total} rides are graded <b>inside the mission</b>, using "
        "Mission Editor triggers. That grader measures whether you are in the "
        "close-in envelope, whether you are on the tanker's speed, how long "
        "you hold both at once, and how often you fall out.", S_P))
    A(Paragraph(
        "It does <b>not</b> measure whether you made contact, how long you "
        "held the plug, or how much fuel you took. DCS mission triggers "
        "cannot see a refuelling event or read your fuel, and doing that "
        "would mean shipping a script inside the mission. So the grader "
        "reports what it can actually see and the briefs say so on every "
        "card. You will not be handed a certificate we did not earn.", S_P))
    A(Paragraph(
        "The tolerances are deliberately wide. A grader that calls a correct "
        "pilot wrong teaches you to ignore it, and after that every call is "
        "noise. If you fly it properly you will never be told off; if you are "
        "sloppy you may still pass. That trade is on purpose.", S_SMALL))

    A(PageBreak())

    # ---- the syllabus -----------------------------------------------------
    A(Paragraph("The syllabus", S_H1))
    A(Paragraph(
        "Ride numbers match the Academy plan's own 0-9 sequence, so the plan "
        "and the Library are talking about the same rides. Ride 10 is an "
        "extra: a variation on something the track already taught, not a new "
        "demand.", S_SMALL))

    for n, (key, v) in zip(order, cards):
        lib = v.get("library") or {}
        grade = v.get("aar_grade")
        badge = (f"graded &middot; {aar_grade.PROFILES[grade]['label']}"
                 if grade else "not graded")
        blk = [Paragraph(f"{n}. {esc(v['label'].split('— ', 1)[-1])} "
                         f"<font size=8 color='#8a5a2b'>[{badge}]</font>",
                         S_RIDE),
               Paragraph(esc(lib.get("premise", "")), S_P)]
        d = first_demand(v.get("brief") or [])
        if d:
            blk.append(Paragraph(f"<i>{esc(d)}</i>", S_SMALL))
        A(KeepTogether(blk))

    A(Paragraph("Where the numbers come from", S_H1))
    A(Paragraph(
        "Four different kinds of claim appear in these rides and they are not "
        "printed as though they were one. The stabilised-then-cleared shape at "
        "pre-contact is doctrine (ATP-56). The 1-3 kt approach closure is "
        "quoted (Stephenson, <i>Air Refueling Receiver</i>). The roughly one "
        "foot per second in the last few feet is quoted (KC-46 program "
        "literature). The 15-second gate and the 60-second standard are "
        "<b>ours</b> — no document we hold states a duration, and the guide "
        "says so rather than implying a manual.", S_P))
    A(Paragraph(
        "The tanker's speed and altitude are a tuned operating point, not a "
        "quotation: published real-world bands are wide and depend on "
        "receiver, weight and altitude. What is in the mission is a setting "
        "chosen so the receiver can actually hold contact in DCS, sitting "
        "inside the real band.", S_SMALL))

    A(Paragraph("Your tanker, and the ones you were not offered", S_H1))
    T = aar.TANKERS[tanker]
    A(Paragraph(
        f"<b>{esc(T['label'])}</b> — flying "
        f"<b>{aar.track_ias_kt(tanker, _type_id(ac))} KIAS at "
        f"{aar.track_alt_ft(tanker, mp):,} ft</b> for this receiver. "
        f"{esc(T['note'])}", S_P))
    short = aar.shortfall_kt(tanker, _type_id(ac))
    if short:
        A(Paragraph(
            f"<b>This pairing runs {short} kt under what a "
            f"{aircraft_label(ac)} wants.</b> The tanker cannot go faster; "
            f"that is the airplane, not you. If a faster tanker is offered "
            f"for this receiver, take it.", S_P))
    if aar.track_alt_ft(tanker, mp) > T["alt_ft"]:
        A(Paragraph(
            f"<b>Why the track is higher than the book figure.</b> A "
            f"{esc(T['label'].split(' (')[0])} would normally work at "
            f"{T['alt_ft']:,} ft. This map's highest ground is about "
            f"{aar.TERRAIN_MAX_FT.get(mp, (aar.TERRAIN_MAX_DEFAULT_FT,))[0]:,} ft "
            f"and you begin every ride 1,000 ft BELOW the track, so the track "
            f"is raised to {aar.track_alt_ft(tanker, mp):,} ft to keep the LOW "
            f"airplane — you — above it. Thinner air also means your indicated "
            f"airspeed buys less maneuvering margin: fly smaller corrections.",
            S_P))
    pn = aar.period_note(tanker, era)
    if pn:
        A(Paragraph(f"<b>Period note.</b> {esc(pn)}", S_SMALL))
    gone = aar.tankers_excluded_by_era(_type_id(ac), era, map_key=mp)
    if gone:
        A(Paragraph(
            "These would fuel your aircraft, but not in this era — which is "
            "the era gate working, not a missing option:", S_SMALL))
        for k, why in gone:
            A(Paragraph(f"<b>{esc(aar.TANKERS[k]['label'])}</b> — {esc(why)}",
                        S_SMALL))

    A(PageBreak())

    # ---- the shipped cards, verbatim --------------------------------------
    A(Paragraph("Kneeboard card — the procedure", S_H1))
    A(Paragraph("This is the card that ships on your kneeboard in every ride "
                "of this track. It is reproduced here so you can print it.",
                S_SMALL))
    A(Spacer(1, 3))
    A(Preformatted("\n".join(aar.brief_lines(tanker, receiver_id=_type_id(ac),
                                             map_key=mp)), S_MONO))

    A(PageBreak())
    A(Paragraph("Kneeboard card — what the grader sees", S_H1))
    A(Spacer(1, 3))
    A(Preformatted("\n".join(aar_grade.brief_lines("contact")), S_MONO))

    A(PageBreak())
    A(Paragraph("The position indicator — every state, at size", S_H1))
    A(Paragraph(
        "This is the panel that appears on the left of your screen during the "
        "coached rides. It is printed here at full size so you can learn it on "
        "the ground rather than at the boom — the whole point of it is that "
        "you recognise a state without reading it.", S_SMALL))
    A(Spacer(1, 6))
    A(_hud_sheet())
    A(Spacer(1, 4))
    A(Paragraph(
        "<b>Ball against the bars</b> = your height. <b>Chevrons</b> = "
        "fore/aft: up is closing, down is falling back. <b>Green HOLD</b> is "
        "the only state not asking you for something. <b>Red POWER OFF</b> is "
        "the safety call — act on that one immediately.", S_SMALL))

    A(PageBreak())
    A(Paragraph("Kneeboard card — the position indicator", S_H1))
    A(Spacer(1, 3))
    A(Preformatted("\n".join(aar_hud.brief_lines()), S_MONO))

    A(PageBreak())
    A(Paragraph("Kneeboard card — your hardware", S_H1))
    A(Paragraph("Read once, on the ground. Most of what stops people "
                "refuelling is set up out here, not flown in there.", S_SMALL))
    A(Spacer(1, 3))
    A(Preformatted("\n".join(aar.hardware_lines()), S_MONO))

    out = Path(out_dir or (ROOT / "docs")) / f"aar-academy-{lane}.pdf"
    Doc(str(out), f"{label} — {aircraft_label(ac)} — Sortie Starter v{version}"
        ).build(story)
    return out


def _hud_sheet():
    """The eleven indicator states as a printed legend.

    Rendered from the SAME PNGs the mission carries, not a mock-up of them —
    a legend drawn separately drifts from the artwork within one release and
    then teaches the wrong picture.
    """
    cells, row, rows = list(aar_hud.STATES), [], []
    for s in cells:
        row.append(RLImage(str(aar_hud.asset(s)), width=27 * mm,
                           height=48.6 * mm))
        if len(row) == 6:
            rows.append(row)
            row = []
    if row:
        row += [""] * (6 - len(row))
        rows.append(row)
    t = Table(rows, colWidths=[28.5 * mm] * 6)
    t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    return t


def _era_label(era):
    try:
        return load_json("eras")[era]["label"]
    except Exception:
        return era


def _type_id(roster_key):
    """Roster key -> DCS type id. `aar.brief_lines` branches on the receiver's
    id; handing it a roster key silently produces the probe-lane card for a
    Viper. Namespace confusion has bitten this module twice, so the conversion
    happens in exactly one place."""
    try:
        from .resolver import resolve
        return resolve("planes." + roster_key).id
    except Exception:
        return roster_key


def aircraft_label(key):
    """Designation AND popular name — "F-14B(U) Tomcat", not "Tomcat".

    A syllabus cover naming only the nickname is ambiguous exactly where it
    matters: three Tomcat variants can fly the probe lane and they are not the
    same airplane.
    """
    try:
        from . import acnames
        return acnames.display(key, _type_id(key))
    except Exception:
        return key.replace("_", "-")


def markdown(track_id, track, version, out_dir=None, aircraft=None,
             tanker=None, era=None):
    cards, order = rides_for(track_id)
    ac = aircraft or track["aircraft"]
    tanker = tanker or track["tanker"]
    era = era or (track.get("eras") or ["modern"])[0]
    mp = track.get("default_map") or "caucasus"
    T = aar.TANKERS[tanker]
    L = [f"# {track['label']}", "",
         f"**{aircraft_label(ac)} · {T['label']} · {_era_label(era)}**", "",
         f"*Sortie Starter v{version} — printed syllabus guide, generated for "
         f"this combination.*", "",
         track["premise"], "", " ".join(track["blurb"]), "",
         f"Track: **{aar.track_ias_kt(tanker, _type_id(ac))} KIAS at "
         f"{aar.track_alt_ft(tanker, mp):,} ft**.", "",
         "## The syllabus", "",
         "| # | Ride | Graded | What it adds |", "|---:|---|---|---|"]
    for n, (key, v) in zip(order, cards):
        g = v.get("aar_grade")
        L.append(f"| {n} | {v['label'].split('— ', 1)[-1]} | "
                 f"{aar_grade.PROFILES[g]['label'] if g else '—'} | "
                 f"{(v.get('library') or {}).get('premise','')} |")
    T = aar.TANKERS[tanker]
    L += ["", "## Your tanker, and the ones you were not offered", "",
          f"**{T['label']}** — flying "
          f"**{aar.track_ias_kt(tanker, _type_id(ac))} KIAS at "
          f"{aar.track_alt_ft(tanker, mp):,} ft** for this receiver. "
          f"{T['note']}", ""]
    short = aar.shortfall_kt(tanker, _type_id(ac))
    if short:
        L += [f"> **This pairing runs {short} kt under what a "
              f"{aircraft_label(ac)} wants.** The tanker cannot go faster. "
              f"That is the airplane, not you.", ""]
    if aar.track_alt_ft(tanker, mp) > T["alt_ft"]:
        L += [f"> **Why the track is higher than the book figure.** A "
              f"{T['label'].split(' (')[0]} would normally work at "
              f"{T['alt_ft']:,} ft. This map's highest ground is about "
              f"{aar.TERRAIN_MAX_FT.get(mp, (aar.TERRAIN_MAX_DEFAULT_FT,))[0]:,} "
              f"ft and you begin every ride 1,000 ft BELOW the track, so the "
              f"track is raised to {aar.track_alt_ft(tanker, mp):,} ft to keep "
              f"the LOW airplane — you — above it. Thinner air also means your "
              f"indicated airspeed buys less maneuvering margin: fly smaller "
              f"corrections.", ""]
    pn = aar.period_note(tanker, era)
    if pn:
        L += [f"**Period note.** {pn}", ""]
    gone = aar.tankers_excluded_by_era(_type_id(ac), era, map_key=mp)
    if gone:
        L += ["These would fuel your aircraft, but not in this era — the era "
              "gate working, not a missing option:", ""]
        L += [f"- **{aar.TANKERS[k]['label']}** — {why}" for k, why in gone]
        L += [""]
    L += ["", "## Kneeboard — the procedure", "", "```",
          "\n".join(aar.brief_lines(tanker, receiver_id=_type_id(ac),
                                    map_key=mp)),
          "```", "", "## Kneeboard — what the grader sees", "", "```",
          "\n".join(aar_grade.brief_lines("contact")), "```", "",
          "## Kneeboard — the position indicator", "", "```",
          "\n".join(aar_hud.brief_lines()), "```", "",
          "*(The eleven indicator states are printed at full size in the PDF.)*",
          "", "## Kneeboard — your hardware", "", "```",
          "\n".join(aar.hardware_lines()), "```", ""]
    out = Path(out_dir or (ROOT / "docs")) / f"aar-academy-{track['lane']}.md"
    out.write_text("\n".join(L))
    return out
