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

OUT = Path(__file__).parent.parent / "docs" / "DCS_Mission_Starter_Guide.pdf"
IMG = Path(__file__).parent.parent / "docs" / "img"

# palette — dark naval blue + gold accent
NAVY = HexColor("#0e1a2b")
NAVY2 = HexColor("#16283f")
GOLD = HexColor("#c9a227")
BLUE = HexColor("#2f6db3")
INK = HexColor("#1a2330")
DIM = HexColor("#5c6b7d")
LINE = HexColor("#d5dce4")
PANEL = HexColor("#f2f5f8")

W, H = letter

styles = {
    "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=17, leading=21,
                         textColor=NAVY, spaceBefore=18, spaceAfter=6),
    "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=12.5, leading=16,
                         textColor=BLUE, spaceBefore=12, spaceAfter=4),
    "body": ParagraphStyle("body", fontName="Helvetica", fontSize=10, leading=14.5,
                           textColor=INK, spaceAfter=6),
    "bullet": ParagraphStyle("bullet", fontName="Helvetica", fontSize=10, leading=14.5,
                             textColor=INK, leftIndent=14, bulletIndent=4, spaceAfter=4),
    "note": ParagraphStyle("note", fontName="Helvetica-Oblique", fontSize=9.5,
                           leading=13, textColor=DIM, spaceAfter=6),
    "tagline": ParagraphStyle("tag", fontName="Helvetica-Bold", fontSize=11,
                              leading=15, textColor=GOLD, spaceAfter=2),
}


def header_footer(canvas, doc):
    canvas.saveState()
    # header band
    canvas.setFillColor(NAVY)
    canvas.rect(0, H - 0.55 * inch, W, 0.55 * inch, fill=1, stroke=0)
    canvas.setFillColor(white)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(0.75 * inch, H - 0.36 * inch, "DCS MISSION STARTER")
    canvas.setFillColor(GOLD)
    canvas.setFont("Helvetica", 9)
    canvas.drawRightString(W - 0.75 * inch, H - 0.36 * inch, "USER GUIDE")
    # footer
    canvas.setFillColor(DIM)
    canvas.setFont("Helvetica", 8.5)
    canvas.drawString(0.75 * inch, 0.45 * inch,
                      "Select, don't search  ·  We set the stage — you write the play")
    canvas.drawRightString(W - 0.75 * inch, 0.45 * inch, f"Page {doc.page}")
    canvas.setStrokeColor(LINE)
    canvas.line(0.75 * inch, 0.62 * inch, W - 0.75 * inch, 0.62 * inch)
    canvas.restoreState()


def cover(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)
    canvas.setFillColor(NAVY2)
    canvas.rect(0, H - 4.4 * inch, W, 2.6 * inch, fill=1, stroke=0)
    # deck stripe motif
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(3)
    canvas.line(0.9 * inch, H - 4.55 * inch, W - 0.9 * inch, H - 4.55 * inch)
    canvas.setDash(14, 10)
    canvas.setLineWidth(2)
    canvas.line(0.9 * inch, 2.1 * inch, W - 0.9 * inch, 2.1 * inch)
    canvas.setDash()
    canvas.setFillColor(white)
    canvas.setFont("Helvetica-Bold", 34)
    canvas.drawString(0.9 * inch, H - 2.85 * inch, "DCS MISSION")
    canvas.drawString(0.9 * inch, H - 3.4 * inch, "STARTER")
    canvas.setFillColor(GOLD)
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawString(0.9 * inch, H - 4.05 * inch, "USER GUIDE")
    canvas.setFillColor(HexColor("#9fb2c8"))
    canvas.setFont("Helvetica", 12)
    canvas.drawString(0.9 * inch, H - 5.1 * inch,
                      "Pick a map, an era, and an aircraft — fly a living world in minutes.")
    canvas.drawString(0.9 * inch, H - 5.35 * inch,
                      "Airfields dressed. SAMs up. The strike group at sea. No waypoints, ever.")
    canvas.setFont("Helvetica", 10)
    canvas.setFillColor(HexColor("#6d7f95"))
    canvas.drawString(0.9 * inch, 1.6 * inch, "Version 1.0  ·  July 2026")
    canvas.drawString(0.9 * inch, 1.4 * inch, "robgrady.com")
    canvas.restoreState()


def t(data, widths, header=True):
    tbl = Table(data, colWidths=widths, hAlign="LEFT")
    style = [
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
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
                  ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
    tbl.setStyle(TableStyle(style))
    return tbl


def P(text, s="body"):
    return Paragraph(text, styles[s])


def shot(name, caption, width=6.6 * inch):
    """Screenshot with caption, scaled to width, kept together."""
    path = IMG / name
    if not path.exists():
        return Spacer(1, 1)
    w, h = PILImage.open(path).size
    img = RLImage(str(path), width=width, height=width * h / w)
    cap = Paragraph(caption, ParagraphStyle(
        "cap", fontName="Helvetica-Oblique", fontSize=8.5, leading=11,
        textColor=DIM, alignment=TA_CENTER, spaceBefore=3, spaceAfter=10))
    return KeepTogether([img, cap])


def B(text):
    return Paragraph(f"•  {text}", styles["bullet"])


story = [PageBreak()]

story += [
    P("Welcome aboard", "h1"),
    P("<b>Select, don't search.</b> The DCS Mission Starter builds a living world for you: "
      "airfields dressed with period-correct aircraft and equipment, working SAM sites, "
      "support flights on station, and a carrier strike group with a properly spotted deck. "
      "You download a ready <b>.miz</b> file and build <i>your</i> mission on top in the "
      "DCS Mission Editor."),
    P("<b>We set the stage — you write the play.</b> The Starter never places your waypoints. "
      "Flight planning is always yours."),

    shot("hero.png", "The Mission Starter wizard."),

    PageBreak(),
    P("Step by step", "h1"),

    P("Step 1 — Pick a map", "h2"),
    P("Choose your theater. Maps that don't support the selected era are greyed out."),
    shot("step1_map.png", "Step 1: map selection — six theaters, era-aware."),

    P("Step 2 — Pick an era", "h2"),
    P("The era is a <b>hard filter</b>: it decides which aircraft, statics, SAMs, and support "
      "assets can appear. A WWII starter will not offer a Hornet, and a modern starter will "
      "not offer a Spitfire."),
    shot("step2_era.png", "Step 2: era selection — WWII is greyed out because the selected map has no WWII preset."),

    P("Step 3 — Coalition, basing & aircraft", "h2"),
    P("Pick your side, home airfield, and aircraft from the full DCS flyable roster (period-"
      "filtered). Set single-player or multiplayer slots, start type, time, weather, and world "
      "density."),
    shot("step3_basing.png", "Step 3: side, home plate, aircraft, and mission conditions."),

    PageBreak(),
    P("Step 4 — Choose building blocks", "h2"),
    P("Everything is optional and defaults are sensible. Each block is described in the "
      "reference table later in this guide."),
    shot("step4_blocks.png", "Step 4: the building-block toggles."),

    PageBreak(),
    P("Step 4b — Configure the carrier (optional)", "h2"),
    P("With the carrier block enabled, pick a hull, a real-world deck state, the aircraft "
      "spotted on deck, and optionally launch the air wing's CAP and Hawkeye."),
    shot("step5_carrier.png", "Step 4b: the Roosevelt with a recovery deck, full airwing, CAP and AAW Hawkeye."),

    P("Step 5 — Template pack (optional), then Generate", "h2"),
    P("Pick a curated scenario or keep the pure starter, then hit <b>GENERATE .MIZ</b>. Drop "
      "the file in <i>Saved Games/DCS/Missions/</i> and fly, or open it in the Mission Editor "
      "and keep building. <b>Copy share link</b> gives you a URL that regenerates this exact "
      "starter for anyone who clicks it — paste it in your squadron Discord."),
    shot("step6_template.png", "Step 5: template packs — era-gated like everything else."),
    shot("step7_generate.png", "The generate bar: share link and download."),

    PageBreak(),
    P("The standard comm ladder", "h1"),
    P("Every starter uses the same predefined comms, so you learn the plan once. The ladder is "
      "printed on the in-jet kneeboard and in the mission briefing."),
]

comm_rows = [
    ["AGENCY", "CALLSIGN", "FREQ (UHF)", "TACAN", "NOTES"],
    ["Guard", "—", "243.00", "—", "monitored"],
    ["Your flight", "(varies)", "305.00", "—", "flight common"],
    ["Tactical", "—", "254.00", "—", "inter-flight coordination"],
    ["AWACS", "Overlord", "251.00", "—", "land-based E-3 / A-50"],
    ["Tanker", "Texaco", "253.00", "39Y", "speeds & altitudes per type"],
    ["Carrier", "Mother", "264.00", "71X", "ICLS 11 · Link4 336 · ACLS on"],
    ["CAP", "(squadron)", "258.00", "—", "carrier air wing"],
    ["AEW Hawkeye", "(squadron)", "259.00", "—", "carrier air wing"],
    ["FARPs", "(name)", "127.50+", "—", "0.25 steps per pad"],
]
story += [t(comm_rows, [1.15*inch, 1.05*inch, 1.0*inch, 0.7*inch, 2.7*inch]),
          Spacer(1, 6),
          P("All carrier approach systems come pre-activated — TACAN 71X “STN”, ICLS channel 11, "
            "Link4 on 336, and ACLS. Tune and go.", "note"),

          PageBreak(),
          P("Building blocks", "h1")]

blocks_rows = [
    ["BLOCK", "WHAT YOU GET"],
    ["Airfield dressing", "Era- and faction-correct static aircraft on real parking stands, ground "
     "support equipment, fuel farms, tents, comms towers. Density: sparse / normal / busy."],
    ["Air defenses", "Complete, functional SAM sites with doctrinal layouts — SA-2/3/6/11, Hawk, "
     "Patriot by era and side — plus SHORAD at the fields. WWII gets flak, not SAMs."],
    ["Tanker / AWACS", "On station behind friendly lines on the standard freqs. Not available in "
     "WWII — the era gate is strict."],
    ["Carrier strike group", "A real CSG with a doctrine-spotted deck. See the next section."],
    ["Ambient air traffic", "AI transports starting up and flying between friendly fields."],
    ["Functional FARPs", "Pads with the fuel, ammo, command, and comms vehicles required for "
     "rearm and refuel to actually work."],
    ["Strike targets", "Depot, convoy, and C2 packages in the enemy rear — each with a trigger "
     "zone ready for your own mission logic."],
    ["Practice range", "Bombing ring and strafe line in the friendly rear."],
    ["Nav kneeboard", "Comms card, airfield data, and a theater overview rendered into the "
     "jet's kneeboard."],
]
story += [t(blocks_rows, [1.5*inch, 5.1*inch])]

story += [
    P("The carrier strike group", "h1"),
    P("Pick a hull and you get its <b>real strike group</b>. The Roosevelt sails as CSG-9 with "
      "USS Lake Erie (CG-70) and DESRON 23 destroyers; the Truman as CSG-8 with USS Gettysburg; "
      "the Forrestal as a 1980s Mediterranean battle group with USS Ticonderoga. Screen stations "
      "follow doctrine: plane-guard destroyer astern, AAW cruiser on the beam, pickets on the "
      "bow quarters. The group steams into wind on BRC."),
    P("Deck configuration", "h2"),
]
deck_rows = [
    ["DECK STATE", "WHAT IT LOOKS LIKE"],
    ["Recovery", "Landing area clear (angle, waist cats, EL4, port stern). The bow is the pack: "
     "tight uniform herringbone rows across the cat tracks, E-2s nose-out on the point, helos "
     "in the corral, tails over the round-down on the starboard fantail."],
    ["Launch", "Cats, JBDs, and taxi flow clear; spares spotted aft in uniform rows."],
    ["Packed", "Port-visit deck. Everything fouled including the angle. No-fly."],
]
story += [t(deck_rows, [1.2*inch, 5.4*inch]), Spacer(1, 6),
          P("Check the aircraft types you want on deck — rows are spotted one squadron per row, "
            "with tugs, MJ-1 loaders, and crash gear at their real stations. Optionally launch the "
            "air wing's <b>CAP</b> (two-ship on the threat axis at 25,000 ft — e.g. VFA-146 Blue "
            "Diamonds) and an <b>E-2 Hawkeye</b> AEW orbit covering the force."),

          P("Template packs", "h1"),
          B("<b>Backseat Ops: IZLID Designation (F-4E)</b> — you fly the back seat; Iceman flies the "
            "jet and Jester lases a convoy with the IZLID on a scripted timeline."),
          B("<b>Backseat Ops: GCI Intercept (F-4E, experimental)</b> — Iceman holds CAP, GCI commits "
            "you onto inbound Backfires; you run the intercept from the pit."),
          P("Templates are the one exception to the no-waypoints rule — the AI pilot needs "
            "steerpoints to fly.", "note"),

          P("Share links and recipes", "h1"),
          P("A starter is defined by its <b>recipe</b> — your wizard selections plus a seed. Share "
            "links encode the recipe, not the file: the same link always regenerates the same "
            "mission, even after DCS updates. Change the seed to reroll the details while keeping "
            "your selections."),

          P("FAQ", "h1"),
          P("<b>The mission won't load or units are missing.</b> Make sure you own the map. Carrier "
            "decks with CVN-71/72/73/75 need the Supercarrier module; the Stennis deck works in the "
            "base game, and the Forrestal comes with the F-14."),
          P("<b>Can I edit the starter?</b> Yes — that's the point. Open it in the Mission Editor; "
            "everything is ordinary groups and statics you can move, delete, or build on."),
          P("<b>Why can't I pick aircraft X in era Y?</b> Hard era gate by service window — the "
            "Hornet entered service in 1987, so it can't appear in a Cold War (1965–1985) starter. "
            "This keeps every starter period-authentic."),
]

doc = BaseDocTemplate(str(OUT), pagesize=letter,
                      leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                      topMargin=0.85 * inch, bottomMargin=0.8 * inch,
                      title="DCS Mission Starter — User Guide",
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
