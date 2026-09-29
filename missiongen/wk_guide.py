"""The printed syllabus for the White Knights tracks.

A SEPARATE BUILDER FROM `aar_guide`, ON PURPOSE
-----------------------------------------------
The obvious move was to generalise `aar_guide.build()` to take either kind of
track. It takes `aircraft`, `tanker` and `era` and threads them through thirty
paragraphs of refuelling prose; a White Knights track has no tanker to pick and
no wizard behind it. Generalising would have meant a builder with two disjoint
halves and a flag deciding which half runs — which is the twin-function shape
that has already produced two live defects in this codebase.

So: shared PAGE FURNITURE (imported, one definition), separate BODY.

WHAT IS IN IT
-------------
The cover, the syllabus table, and then every ride's kneeboard card, verbatim
from `wk.brief_lines()`. Verbatim matters — a guide that paraphrases a brief is
a second source of truth, and one of the two will drift.
"""
from pathlib import Path

from . import wk
from .aar_guide import (Doc, esc, S_TITLE, S_SUB, S_H1, S_H2, S_P, S_SMALL,
                        S_MONO, S_RIDE)
from .resolver import load_json

from reportlab.platypus import Paragraph, Spacer, PageBreak, Image as RLImage
from reportlab.lib.units import mm


MAP_LABEL = {"germany": "Cold War Germany", "sinai": "Sinai",
             "caucasus": "Caucasus", "nevada": "Nevada (NTTR)"}


def _rides(track_id):
    return wk.rides_in(track_id)


def _fit(path, max_w, max_h):
    """Scale a diagram into the frame without ever enlarging it. An 850 px
    scan blown up to fill a page turns line art into fuzz."""
    from PIL import Image as PILImage
    with PILImage.open(path) as im:
        w, h = im.size
    k = min(max_w / float(w), max_h / float(h))
    return w * k, h * k


def _map_for(track: dict, map_key: str) -> str:
    return map_key or track.get("default_map") or "germany"


def _maps_offered(track_id: str) -> list:
    """Every map at least one ride in this track can be flown on, in order."""
    seen = []
    for _n, key, _r in _rides(track_id):
        from .templates import maps_for
        for m in maps_for(key):
            if m not in seen:
                seen.append(m)
    return seen


def build(track_id, track, version, out_dir=None, map_key=""):
    """The PDF. Returns the path written."""
    mp = _map_for(track, map_key)
    out = Path(out_dir or ".") / f"{track.get('guide') or track_id}.pdf"
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = Doc(str(out), f"{track['label']} — Sortie Starter v{version}",
              locator="SORTIE STARTER / SYLLABUS")
    F = []
    A = F.append

    # ---- cover ----------------------------------------------------------- #
    A(Paragraph(esc(track["label"]), S_TITLE))
    A(Paragraph(f"{wk.SQUADRON} — “{wk.NICKNAME}” · "
                f"{wk.WING} · {wk.STATION}", S_SUB))
    A(Paragraph(f"F-4E Phantom II, tail code {wk.TAILCODE}. "
                f"Squadron commander {esc(wk.COMMANDER)}; wing commander "
                f"{esc(wk.WING_COMMANDER)}.", S_SMALL))
    A(Spacer(1, 5 * mm))
    A(Paragraph(f"<i>Sortie Starter v{version} — printed syllabus, "
                f"generated for {MAP_LABEL.get(mp, mp)}.</i>", S_SMALL))
    A(Spacer(1, 4 * mm))
    A(Paragraph(esc(track.get("premise", "")), S_P))
    if track.get("blurb"):
        A(Paragraph(esc(" ".join(track["blurb"])), S_P))

    # ---- where every number came from ------------------------------------ #
    A(Paragraph("The four documents", S_H1))
    A(Paragraph(
        "Everything in this syllabus comes out of paper a new arrival at the "
        "70th was handed in January and February 1980. Nothing below is "
        "rounded, modernised or corrected.", S_P))
    for k in ("lowlevel", "tactics", "standards", "wis1"):
        name, date = wk.DOCS[k]
        A(Paragraph(f"<b>{esc(name)}</b> — {date}", S_SMALL))
    A(Spacer(1, 3 * mm))
    A(Paragraph(
        "<b>The provenance rule.</b> Almost every other number this product "
        "prints is either our own estimate or a published citation. These are "
        "neither: they are a squadron's own working document, which is a "
        "stronger provenance than anything else we ship. Where a number cannot "
        "be flown as written in a given theatre, the card prints BOTH and says "
        "which governs. It never silently substitutes — that would be "
        "putting words in a dead man's mouth.", S_SMALL))

    # ---- what is deliberately absent ------------------------------------- #
    A(Paragraph("What is not here, and why", S_H1))
    for head, body in (
        ("Moody AFB.", "It is not in DCS. Every ride is staged, and every card "
         "says where."),
        ("The range they used in January 1980.", "Moody's own Grand Bay Range "
         "was not established until 1985, and Townsend Range was closed from "
         "1972 until 1981. Which range the squadron actually used is not in "
         "any source we could reach, so the delivery syllabus lives on the "
         "Proud Phantom track, where the base IS documented."),
        ("Any European deployment in the Phantom.", "There wasn't one. The "
         "347th was drafted into NATO contingency plans and committed to the "
         "Rapid Deployment Joint Task Force, and flew to Nellis, Cold Lake and "
         "Cairo West. The Germany track is the war it was ASSIGNED, briefed as "
         "the plan."),
    ):
        A(Paragraph(f"<b>{head}</b> {body}", S_SMALL))

    # ---- the syllabus ---------------------------------------------------- #
    A(Paragraph("The syllabus", S_H1))
    tpl = load_json("mission_templates")
    for n, key, ride in _rides(track_id):
        prem = ((tpl.get(key) or {}).get("library") or {}).get("premise", "")
        A(Paragraph(f"{n}. {esc(ride['title'])}", S_RIDE))
        A(Paragraph(esc(prem), S_SMALL))
        only = wk.maps_for(key)
        if only and len(only) == 1 and len(_maps_offered(track_id)) > 1:
            A(Paragraph(f"<i>{MAP_LABEL.get(only[0], only[0])} only.</i>",
                        S_SMALL))

    # ---- the counterpart -------------------------------------------------- #
    A(Paragraph("About your counterpart", S_H1))
    for ln in wk.WINGMAN_NOTE[1:]:
        if ln.strip():
            A(Paragraph(esc(ln), S_P))

    # ---- the cards -------------------------------------------------------- #
    for n, key, ride in _rides(track_id):
        A(PageBreak())
        A(Paragraph(f"{n}. {esc(ride['title'])}", S_H1))
        ride_map = (wk.maps_for(key) or [mp])
        use = mp if mp in ride_map else ride_map[0]
        if use != mp:
            A(Paragraph(f"<i>This ride is "
                        f"{MAP_LABEL.get(use, use)} only — the card below "
                        f"is written for it.</i>", S_SMALL))
        for ln in wk.brief_lines(key, use):
            if not ln.strip():
                A(Spacer(1, 2.1 * mm))
            elif ln.startswith("=="):
                A(Paragraph(esc(ln.strip("= ")), S_H2))
            elif ln.startswith(" ") or ln.startswith("  "):
                A(Paragraph(esc(ln), S_MONO))
            else:
                A(Paragraph(esc(ln), S_SMALL))
        atk = ride.get("attack")
        dp = wk.diagram_path(atk) if atk else None
        if dp:
            A(PageBreak())
            A(Paragraph(f"{esc(ride['title'])} — the squadron's diagram", S_H1))
            iw, ih = _fit(dp, 168 * mm, 205 * mm)
            A(RLImage(str(dp), width=iw, height=ih))
            for ln in wk.diagram_note(atk):
                A(Paragraph(esc(ln), S_SMALL))

    doc.build(F)
    return out


def markdown(track_id, track, version, out_dir=None, map_key=""):
    """The same syllabus as text.

    THIS IS THE TWIN THAT HAS BURNED THIS CODEBASE TWICE. It shares its BODY
    with the PDF by construction: both walk `wk.brief_lines()` and neither
    restates a card. The only thing written twice is the furniture around it,
    and `tests/test_wk_guide.py` compares the two outputs ride by ride.
    """
    mp = _map_for(track, map_key)
    out = Path(out_dir or ".") / f"{track.get('guide') or track_id}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    tpl = load_json("mission_templates")
    L = [f"# {track['label']}", "",
         f"**{wk.SQUADRON} — \"{wk.NICKNAME}\" · {wk.WING} · {wk.STATION}**",
         "",
         f"F-4E Phantom II, tail code {wk.TAILCODE}. Squadron commander "
         f"{wk.COMMANDER}; wing commander {wk.WING_COMMANDER}.", "",
         f"*Sortie Starter v{version} — printed syllabus, generated for "
         f"{MAP_LABEL.get(mp, mp)}.*", "",
         track.get("premise", ""), "",
         " ".join(track.get("blurb") or []), "",
         "## The four documents", ""]
    for k in ("lowlevel", "tactics", "standards", "wis1"):
        name, date = wk.DOCS[k]
        L.append(f"- **{name}** — {date}")
    L += ["", "Everything in this syllabus comes out of paper a new arrival at "
          "the 70th was handed in January and February 1980. Nothing is "
          "rounded, modernised or corrected. Where a number cannot be flown as "
          "written in a given theatre, the card prints BOTH and says which "
          "governs.", "",
          "## The syllabus", "",
          "| # | Ride | What it adds |", "|---:|---|---|"]
    for n, key, ride in _rides(track_id):
        prem = ((tpl.get(key) or {}).get("library") or {}).get("premise", "")
        only = wk.maps_for(key)
        tag = ""
        if only and len(only) == 1 and len(_maps_offered(track_id)) > 1:
            tag = f" *({MAP_LABEL.get(only[0], only[0])} only)*"
        L.append(f"| {n} | {ride['title']}{tag} | {prem} |")
    L += ["", "## About your counterpart", ""]
    L += [ln for ln in wk.WINGMAN_NOTE[1:] if ln.strip()]
    for n, key, ride in _rides(track_id):
        ride_map = (wk.maps_for(key) or [mp])
        use = mp if mp in ride_map else ride_map[0]
        L += ["", f"## {n}. {ride['title']}", "", "```"]
        L += wk.brief_lines(key, use)
        L += ["```"]
        atk = ride.get("attack")
        if atk and wk.diagram_path(atk):
            L += ["", f"![{ride['title']} diagram]"
                      f"(../missiongen/data/wk/{wk.DIAGRAMS[atk]})", ""]
            L += wk.diagram_note(atk)
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    return out
