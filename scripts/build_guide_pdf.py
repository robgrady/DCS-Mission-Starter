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
    "h3": ParagraphStyle("h3", fontName="Helvetica-Bold", fontSize=10.5, leading=14,
                         textColor=INK, spaceBefore=9, spaceAfter=2),
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
    canvas.drawString(0.9 * inch, 1.6 * inch, f"Version {APP_VERSION}  ·  July 2026")
    canvas.drawString(0.9 * inch, 1.4 * inch,
                      "Developed by Authentic Media LLC  ·  robgrady.com  ·  "
                      "provided as-is - no warranty, no liability")
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

    P("Finding your way", "h2"),
    P("The app works as a set of <b>focused screens</b>, not one long page. The <b>rail</b> on "
      "the left lists the mission's areas — click any one to switch to it, and you see just that "
      "screen. Each rail item shows its current value and turns green with a <b>✓</b> once set, "
      "so you can tell at a glance what's done. A <b>Next</b> button (with Back and a "
      "\"Step N of M\" readout) walks you through in order if you'd rather be guided. "
      "The live <b>PREVIEW</b> line and the <b>GENERATE</b> button are pinned at the bottom of "
      "every screen, so you can build the moment you're happy — there is no required order, and "
      "changing one thing and regenerating is always two clicks. Your work saves itself: close "
      "the browser mid-build and everything is exactly where you left it (\"Reset wizard\" starts "
      "fresh)."),
    shot("hero.png", "Section navigation: the rail switches screens, completion checkmarks show progress, and Generate + the live preview stay pinned."),

    PageBreak(),
    P("Screen by screen", "h1"),

    P("1 · Theater — era and map", "h2"),
    P("Start with <b>when</b>, then <b>where</b>. The era is the master filter: it decides which "
      "maps, aircraft, statics, SAMs, and support can appear — a WWII starter never offers a "
      "Hornet, a modern one never a Spitfire. Maps without content for the era grey out. All "
      "eleven theaters are here: pick WWII and the Channel, Normandy and the 1944 Marianas light "
      "up; Cold War Germany puts you on the Inner German Border; Kola covers NATO's Northern "
      "Flank; Sinai in the Cold War is October 1973. Each preset carries its major airfields on "
      "both sides — on the NTTR that includes Groom Lake and Tonopah Test Range as blue home "
      "plates (USAF fields; even the captured MiGs there flew as USAF units)."),
    shot("theater.png", "Theater: era across the top, then the maps valid for it."),

    P("2 · Flight — side, jet, home base", "h2"),
    P("Pick your side, home airfield, and aircraft from the full DCS flyable roster (period-"
      "filtered), plus single- or multiplayer slots, start type, time, weather, and world "
      "density. On coastal maps <b>the carrier</b> is offered here as a home base (last in the "
      "list); land bases are the default, so choosing the boat is a deliberate act — and doing "
      "so lights up the Carrier screen."),
    P("Variations &amp; the seed", "h3"),
    P("The <b>Variation (seed)</b> field is the one control people find mysterious, so here's "
      "the whole story: the generator makes hundreds of small random choices — which stands get "
      "aircraft, where the area SAMs sit, exactly where the tanker orbits. The <b>seed</b> is "
      "the number those choices are rolled from. <b>The same recipe and the same seed always "
      "build the exact same mission</b>, byte for byte — that's how a share link reproduces your "
      "mission precisely for a squadron-mate. If you like a mission but want to tweak one setting, "
      "<i>keep</i> the seed so everything else stays put. If you want a <i>different</i> layout of "
      "the same scenario, change the number — or just hit the <b>🎲 re-roll</b> button next to "
      "it — and generate again. You never have to think about the actual value; treat 🎲 as "
      "\"give me another version.\""),

    P("3 · Airfields — populate your ramps", "h2"),
    P("Fill your side's fields with parked aircraft, ground equipment and infrastructure. "
      "There are two ways to do it, chosen with the toggle at the top of the screen."),

    P("Two ways to fill", "h3"),
    P("<b>Ramp theme</b> auto-fills a curated, era- and base-correct mix — Nellis dresses as an "
      "Air Force base, not a Navy ramp — at a <b>fill percentage</b> you set. This is the quick "
      "path: pick a theme (or leave it on Auto) and go."),
    shot("airfields_mode.png", "The toggle picks how ramps are filled; in theme mode you get a theme dropdown and a fill slider.", max_h=2.6 * inch),

    P("Compose exact aircraft", "h3"),
    P("Switch to <b>Compose</b> for the Ramp Composer, where you pick exact aircraft and counts "
      "by role — Fighters, Bombers &amp; Heavies, Tankers, AWACS, Transport, Helicopters — with "
      "your own coalition and Red/OPFOR aggressors in separate, colour-coded sections. It starts "
      "<b>pre-populated from the selected theme</b>: pick <i>Red Flag</i> and you get Vipers, "
      "Eagles, a Tornado, a pair of B-1s, tankers and an AWACS already laid in — adjust the "
      "numbers from there. Counts are <b>per airfield</b>, era-filtered (a WWII composer offers "
      "warbirds, never a B-1), and placement is stand-aware: helos on pads, heavies on the big "
      "ramp squares, anything beyond a field's capacity skipped. The exact mix rides the share "
      "link, so a squadron-mate who clicks it gets the same ramp."),
    shot("airfields_compose.png", "The Ramp Composer, pre-populated from the Red Flag template — your coalition and Red aggressors listed separately (scrolls for more categories).", max_h=3.4 * inch),

    P("Placement mode &amp; object types", "h3"),
    P("<b>Placement mode</b> matters for performance. <b>Static objects</b> (recommended) are "
      "inert scenery — no AI pilot, so they use far less memory and CPU, load instantly, and "
      "never show as map contacts; their facing is <b>exact</b> on the surveyed maps (all but "
      "Falklands and The Channel). <b>AI aircraft</b> align to the painted line on any map but "
      "are live units that cost frames and can hurt FPS on lower-end PCs — only worth it on the "
      "two unsurveyed maps. The three checkboxes switch parked aircraft, ground equipment and "
      "the infrastructure cluster independently. Runways and taxiways always stay clear, and "
      "enemy fields dress themselves with their own era-correct theme."),
    shot("airfields_place.png", "Placement mode (Static is recommended for performance) and the object-type toggles.", max_h=2.4 * inch),

    P("4 · Threats — defenses and the Threat Dial", "h2"),
    P("Turn on <b>Air defenses</b> (era-correct SAM sites + SHORAD at every enemy field), then "
      "set the <b>Threat Dial</b>. <b>Intensity</b> (Minimal → Maximum) adds extra area SAM "
      "sites and airborne enemy CAP on top of the base defenses — the count is rolled off the "
      "seed, so re-rolls differ. <b>System level</b> sets the calibre: <i>Era standard</i>, "
      "<i>Light</i> (SA-2/3, MiG-21/23), <i>Heavy</i> (SA-10/11, Su-27/MiG-31), or <i>Mixed</i>. "
      "Everything is era-gated — a WWII field never fields an SA-10. The enemy CAP engages you "
      "inbound; the area SAMs form a belt to plan around."),
    shot("threats.png", "Threats: air defenses plus the intensity dial and system-level tiers."),

    P("5 · Support & extras", "h2"),
    P("On-station assets and briefing aids, grouped by what they do: <b>air support</b> (tanker, "
      "AWACS, ambient traffic, FARPs), <b>targets &amp; ranges</b> (strike packages, a practice "
      "range), and <b>briefing aids</b> (the comms card, in-jet kneeboards, named nav reference "
      "points). Turn on what the mission needs — sensible defaults are already set."),
    P("The <b>tanker matches your jet</b>: a boom receiver (F-16, F-15, A-10) gets a KC-135; a "
      "probe-and-drogue jet (Hornet, Tomcat, Mirage) gets a drogue tanker. Support aircraft fly "
      "under a nation that actually operates them (US AWACS/tankers, Russian A-50), added to your "
      "coalition if your lead nation doesn't — so an Israeli- or UK-led force still gets a valid, "
      "editable KC-135 and E-3 rather than an airframe its country can't fly."),

    P("6 · Carrier (when the carrier is home)", "h2"),
    P("Shown only when you chose the carrier as your home base. Pick a hull, a real-world deck "
      "state (recovery, launch, underway, packed), the aircraft spotted on deck, and optionally "
      "launch the air wing's CAP and Hawkeye. All approach systems come pre-activated."),
    shot("carrier.png", "Carrier deck configuration — hull, deck state, air wing."),

    P("7 · Map &amp; graphics (F10)", "h2"),
    P("Each layer draws real mission geometry on the F10 map: the tanker's racetrack with its "
      "freq/TACAN label, the AWACS orbit, carrier CAP and Hawkeye stations, the strike group's "
      "ops box, amber rings over targets and the range, FARP service rings, bullseye, and the "
      "intel picture — known enemy SAM rings at doctrinal radii. Friendly orbits and threat "
      "rings render on YOUR coalition's layer only, so multiplayer stays fair. Zones inform — "
      "they never route you."),

    P("8 · Template pack (optional)", "h2"),
    P("Keep the pure starter, or drop into a curated scenario (the F-14 Crew Ops packs). Crew "
      "difficulty sets whether the back-seat AI hints your next call."),

    P("9 · Review &amp; generate", "h2"),
    P("A one-glance summary of every choice. Hit <b>GENERATE .MIZ</b> (here or from the pinned "
      "bar on any screen), drop the file in <i>Saved Games/DCS/Missions/</i>, and fly — or open "
      "it in the Mission Editor and keep building. <b>Copy share link</b> gives a URL that "
      "regenerates this exact starter for anyone who clicks it; paste it in your squadron "
      "Discord."),
    shot("review.png", "Review & generate: the full picture before you build."),

    PageBreak(),
    P("Crew Ops — fly the back seat", "h1"),
    P("<b>The backseat contract: the mission flies the jet; you run the mission.</b> Crew Ops "
      "templates are player-paced through the <b>F10 CREW menu</b> — no scripts on a stopwatch. "
      "Commands appear as they become relevant, the AI crew answers your calls, and real events "
      "drive the feedback (“GOOD EFFECT ON TARGET” when your convoy dies)."),
    B("<b>F-14B(U) Pilot + Jester: IZLID Strike</b> — you fly the Tomcat; Jester (the AI RIO) "
      "puts the IZLID on the target when you call it from the crew menu. (Pre-release module.)"),
    B("<b>F-14B(U) RIO + Iceman: GCI Intercept</b> — you're the RIO; Iceman (the AI pilot) "
      "flies YOUR calls — commit, hold, recommit CAP — while you run the AWG-9. (Pre-release.)"),
    B("<b>RIO: Fleet Defense (F-14, solo or multiplayer)</b> — four Backfires inbound on the "
      "force; sort the raid in TWS and time the Phoenix shots. <b>Solo</b> (1 slot): you "
      "air-start level on CAP — trim, jump to the back seat, and Iceman holds the jet on your "
      "A-menu commands. <b>Multiplayer</b> (2 slots): human pilot up front, human RIO in back."),
    P("<b>Crew difficulty:</b> Trainee shows [CREW HINT] prompts for the next call; Qualified "
      "gives you a clean cockpit. <b>Why F-14 only?</b> Jester and Iceman are the Tomcat's crew "
      "AI. The F-4E needs none — the Phantom's back seat has full flight controls, so a WSO "
      "player simply flies from the pit.", "note"),

    P("Nav reference points", "h1"),
    P("On maps with curated landmark data (Nevada today), named references — Area 51, Belted "
      "Peak, Student Gap, Coyote Summit and more — are marked on the <b>F10 map</b>, listed in "
      "the briefing with coordinates, plotted on the kneeboard theater page, and provided as "
      "named trigger zones (<i>NAV BELTED PEAK</i>) you can build your own logic on."),

    PageBreak(),
    P("The standard comm ladder", "h1"),
    P("Every starter uses the same predefined comms, so you learn the plan once. All agency "
      "frequencies sit on the real 25 kHz radio channel raster (they end on realistic .025 "
      "increments, not round whole numbers), and Guard stays fixed at 243.000. The ladder is "
      "printed on the in-jet kneeboard and in the mission briefing."),
]

comm_rows = [
    ["AGENCY", "CALLSIGN", "FREQ (UHF)", "CHAN", "TACAN", "NOTES"],
    ["Guard", "—", "243.000", "last", "—", "monitored (fixed emergency)"],
    ["Your flight", "(varies)", "305.725", "CH1", "—", "flight common"],
    ["Tactical", "—", "254.325", "CH7", "—", "inter-flight coordination"],
    ["AWACS", "Overlord", "251.475", "CH3", "—", "land-based E-3 / A-50"],
    ["Tanker", "Texaco", "253.625", "CH4", "39Y", "speeds & altitudes per type"],
    ["Carrier", "(her callsign)", "264.425", "CH2", "hull # X", "ICLS 11 · Link4 336 · ACLS"],
    ["Plane guard", "Angel", "262.050", "CH5", "—", "Starboard Delta, flight ops"],
    ["CAP", "(squadron)", "258.175", "CH6", "—", "carrier air wing"],
    ["AEW Hawkeye", "(squadron)", "259.925", "CH3/8", "—", "CH3 if no AWACS in mission"],
    ["FARPs", "(name)", "127.525+", "—", "—", "0.25 steps per pad"],
]
story += [t(comm_rows, [1.1*inch, 0.95*inch, 0.95*inch, 0.55*inch, 0.6*inch, 2.4*inch]),
          Spacer(1, 6),
          P("<b>The comm plan is already in your jet.</b> COMM1 presets are programmed to this "
            "ladder at generation time (only for assets that exist in your mission) — Mother is "
            "CH2, gas is CH4, Guard rides the last channel. COMM2 keeps module defaults. The "
            "kneeboard's CHAN column matches the cockpit.", "note"),
          Spacer(1, 4),
          P("Carrier systems activate at mission start per hull, and every boat answers to her "
            "real name: <b>Rough Rider</b> (CVN-71), <b>Union</b> (CVN-72), <b>Warfighter</b> "
            "(CVN-73), <b>Courage</b> (CVN-74), <b>Lone Warrior</b> (CVN-75) — official voice "
            "callsigns per ACP 113. The Forrestal flies her fleet nickname <b>Fid</b> (“First In "
            "Defense”, convention). “Mother” still works — it's the brevity word for whichever "
            "boat is yours. <b>TACAN channel = hull number</b>: 73X on the George Washington, "
            "59X on the Forrestal, 5X on Invincible (pennant R05). SuperCarrier boats also "
            "radiate ICLS 11, Link4 336 and ACLS; the Forrestal has no ACLS in DCS; the 1982 "
            "Invincible is TACAN-only; the 1944 Essex is visual recovery, era-true.", "note"),
          Spacer(1, 4),
          P("Aircraft-side TACAN/ICLS/Link4 are cockpit state — DCS does not allow presetting "
            "them from a mission file; the kneeboard values are what you dial (F-14 crews: the "
            "RIO enters Link4 336.0).", "note"),

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
    ["Nav reference points", "Named landmarks (Area 51, Belted Peak...) marked on the F10 map, "
     "in the briefing, and on the kneeboard, with trigger zones for your own logic."],
]
story += [t(blocks_rows, [1.5*inch, 5.1*inch])]

story += [
    P("The carrier strike group", "h1"),
    P("Pick a hull and you get its <b>real strike group</b>. The Roosevelt sails as CSG-9 with "
      "USS Lake Erie (CG-70) and DESRON 23 destroyers; the Truman as CSG-8 with USS Gettysburg; "
      "the Forrestal as a 1980s Mediterranean battle group with USS Ticonderoga; HMS Invincible "
      "as the 1982 South Atlantic task force with her Leander frigates (and, true to history, no "
      "AEW); USS Essex as Task Force 58 with Corsairs for the 1944 Marianas. Screen stations "
      "follow doctrine: plane-guard destroyer astern, AAW cruiser on the beam, pickets on the "
      "bow quarters. The group steams into wind on BRC. On landlocked maps (Nevada) the carrier "
      "option greys out — there is no carrier water."),
    P("When the deck is set for flight ops (launch or recovery), the air wing's SAR helo is "
      "already airborne — <b>Angel</b>, an SH-60 holding in <b>Starboard Delta</b>: 300 ft and "
      "below, a quarter mile off the starboard beam, tracking the ship's course. Starboard, "
      "because the whole Case I pattern lives in left-hand turns on the port side; doctrine is "
      "\"first off, last on\" — the helo launches before the first cat shot. Each wing flies its "
      "real HS squadron (HS-6 Indians on the Roosevelt, HS-15 Red Lions on the Forrestal), up "
      "Angel common on 262.0. The 1944 Essex keeps her plane-guard destroyer astern instead — "
      "no helos in Task Force 58."),
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

          P("Templates are the one exception to the no-waypoints rule — the AI pilot needs "
            "steerpoints to fly. See the Crew Ops section for the WSO/RIO scenarios.", "note"),

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
