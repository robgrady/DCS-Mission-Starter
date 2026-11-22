#!/usr/bin/env python3
"""Render Flightline briefs and append two lesson cards to each native FAM mission.

Run after the native First Flight build. The input archives and facts are read-only.

    python scripts/build_first_flight_documents.py /path/to/native
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile
from xml.sax.saxutils import escape, quoteattr

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor")]

from PIL import Image as PillowImage
from reportlab import rl_config
from reportlab.platypus import Image, Paragraph, Spacer

from missiongen import authentic, kneeboard


FIGURES = ROOT / "docs" / "first-flight" / "figures"
SOURCE = "U.S. Navy / CNATRA P-1212 (Rev. 02-19), Familiarization, T-45 Strike, 2019"
SOURCE_NOTES = {
    "FAM-01": {
        "file": "CNATRA-Figure-3-1.png",
        "citation": "Figure 3-1, printed p. 3-2 (PDF p. 26)",
        "title": "How the source depicts turn practice",
        "note": (
            "The turn diagram and its values come from the 2019 training source. "
            "Use the DCS lesson cues and checkpoint for First Flight."
        ),
    },
    "FAM-02": {
        "file": "CNATRA-Figure-B-2-ground-movement.png",
        "citation": "Figure B-2 (cropped), printed p. B-5 (PDF p. 115)",
        "title": "How the source depicts ground movement cues",
        "note": (
            "These ground signals appear here as historical illustrations. "
            "Follow the in-game text cues during Ramp to Air."
        ),
    },
}


def lesson_subtitle(mission):
    return f'{mission["id"]} / {mission["estimated_minutes"]} MIN / DAYLIGHT'


def completion_notes(facts, mission):
    scores = facts["scores"]
    return [
        mission["completion"],
        f'In the campaign, {scores["complete"]} completes this lesson. '
        f'A practice score of {scores["practice"]} keeps you on the current lesson.',
        mission["retry"],
    ]


def coach_reminder(facts):
    coach = facts["coach"]
    return f'Use {coach["help_label"]} in the {coach["help_menu"]} menu to repeat the current cue.'


def section(story, heading, paragraphs, styles):
    story.append(Paragraph(escape(heading.upper()), styles["h1"]))
    story.append(authentic.section_rule())
    for paragraph in paragraphs:
        story.append(Paragraph(escape(paragraph), styles["p"]))


def build_brief(path, facts, mission, illustration):
    """Use shared mission facts for both the briefing and the in-flight card."""
    aircraft = facts["aircraft"]
    notes = SOURCE_NOTES[mission["id"]]
    styles = authentic.styles()
    rl_config.invariant = 1
    doc = authentic.make_doc(
        str(path),
        f'SORTIE STARTER / {facts["campaign_title"].upper()}',
        f'{mission["id"]} / LESSON BRIEF',
        footer_left="DCS WORLD / SIMULATION LESSON",
        margins_mm=(19, 19, 15, 17),
    )

    aircraft_link = quoteattr(aircraft["source_url"])
    aircraft_name = escape(f'{aircraft["name"]} {aircraft["version"]}')
    setup = escape(f'{facts["terrain"]} / {facts["airfield"]} / {facts["pilot_mode"]}')
    story = [
        Paragraph(escape(mission["title"]), styles["title"]),
        Paragraph(escape(lesson_subtitle(mission)), styles["sub"]),
        Paragraph(
            f'{setup} / <link href={aircraft_link} color="{authentic.hexes()["accent"]}">'
            f'<u>{aircraft_name}</u></link>',
            styles["small"],
        ),
    ]
    section(story, "Before you fly", (mission["start"], mission["objective"]), styles)
    section(
        story,
        "In the mission",
        [*(f"{number}. {step}" for number, step in enumerate(mission["steps"], 1)),
         coach_reminder(facts),
         "Open the DCS kneeboard for the lesson cues and source illustration.",
         *completion_notes(facts, mission)],
        styles,
    )
    section(story, "Source study", (notes["note"],), styles)
    graphic = Image(str(illustration))
    graphic._restrictSize(doc.width - 18, 226)
    story.extend([
        graphic,
        Spacer(1, 5),
        Paragraph(escape(f'{SOURCE}. {notes["citation"]}.'), styles["small"]),
    ])
    doc.build(story)


def build_cards(facts, mission, illustration):
    notes = SOURCE_NOTES[mission["id"]]
    active = kneeboard.pages_text(
        mission["title"],
        lesson_subtitle(mission),
        ["== Objective", mission["objective"],
         "== Lesson cues",
         *(f"{number}. {step}" for number, step in enumerate(mission["steps"], 1)),
         "== Finish and retry", *completion_notes(facts, mission),
         "", coach_reminder(facts)],
    )
    if len(active) != 1:
        raise ValueError(f'{mission["id"]} cue card exceeds one page')
    study = kneeboard.page_image(
        "Source Study",
        f'{mission["id"]} / HISTORICAL REFERENCE',
        illustration,
        [notes["title"], notes["note"], SOURCE, notes["citation"]],
    )
    return [active[0], study]


def install_cards(source, destination, cards):
    with zipfile.ZipFile(source) as archive:
        existing = set(archive.namelist())
    added = {f"KNEEBOARD/IMAGES/{index:02d}_starter.png" for index in range(1, len(cards) + 1)}
    if collision := (existing & added):
        raise ValueError(f"{source.name} already contains a conflicting card: {sorted(collision)}")
    shutil.copyfile(source, destination)
    kneeboard.inject_kneeboard(destination, cards)
    with zipfile.ZipFile(destination) as archive:
        if set(archive.namelist()) != existing | added or archive.testzip():
            raise ValueError(f"Kneeboard archive validation failed for {destination.name}")


def build(native_dir, output_dir):
    facts = json.loads((native_dir / "facts.json").read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    with tempfile.TemporaryDirectory(prefix=".fam-documents-", dir=output_dir) as temp_dir:
        stage = Path(temp_dir)
        for mission in facts["missions"]:
            source = native_dir / mission["filename"]
            illustration = FIGURES / SOURCE_NOTES[mission["id"]]["file"]
            with PillowImage.open(illustration) as artwork:
                artwork.verify()
            brief = stage / f"{source.stem}-brief.pdf"
            mission_with_cards = stage / source.name
            build_brief(brief, facts, mission, illustration)
            install_cards(source, mission_with_cards, build_cards(facts, mission, illustration))
            written.extend((brief, mission_with_cards))
        for deliverable in written:
            deliverable.replace(output_dir / deliverable.name)
    return [output_dir / deliverable.name for deliverable in written]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native_dir", type=Path, help="Native mission directory with facts.json")
    parser.add_argument("--output-dir", type=Path, help="Defaults to NATIVE_DIR/illustrated")
    args = parser.parse_args()
    output_dir = args.output_dir or args.native_dir / "illustrated"
    if output_dir.resolve() == args.native_dir.resolve():
        parser.error("use a separate output directory to preserve native archives")
    for path in build(args.native_dir, output_dir):
        print(path)


if __name__ == "__main__":
    main()
