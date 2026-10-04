"""Sortie Starter Brief — the pre-flight briefing pack (PDF + Markdown).

The download that rides alongside the .miz: a printable 4-page brief with the
mission data card, a THEATER CHART drawn in the tactical chart standard
(chartstyle palette — cyan friendly, red WEZ rings + AD glyph, amber targets,
white/gold bullseye, terrain-tan ground), the comms/nav card, and the airfields
& forces picture (aligned owner nations, player start).

Rendered with PIL only (same machinery as the in-cockpit kneeboard, no new
runtime deps) and saved as a native multi-page PDF. Deterministic: same recipe,
same brief. Markdown emitted alongside for Discord/forum sharing.
"""
import math

from PIL import Image, ImageDraw, ImageFont

from . import __version__
from . import chartstyle as cs
from . import loadouts as _loadouts
from .resolver import load_json

# A4 portrait at ~175 dpi — crisp for screen and print
W, H = 1448, 2048

# MILITARY PUBLICATION register (Rob: "All the documentation should look like
# real military documentation"). The reference is a NATOPS/flight-pub page and
# the DD-175: white paper, black ink, a solid black masthead band with white
# title — the T.O. cover idiom — and NO accent color in the prose. The chart
# plates keep doctrine colors (blue own / red hostile / amber target) because
# real aeronautical charts are printed in color; everything else is what a
# squadron photocopier could reproduce.
# FLIGHTLINE TECHNICAL — all values from missiongen/brand.py (the one token
# source). NAVY is the kit's section-identity color and the masthead band is
# navy again (the black band was the v1.55.0 interim). The classification
# banner is replaced by the identity rail per the kit's explicit guidance.
from .brand import COLORS, font as _brand_font, rail_text

PAPER = COLORS.paper
INK = COLORS.ink
NAVY = COLORS.navy
GOLD = COLORS.rule            # legacy name; now the kit's rule gray
DIM = COLORS.slate
TAN = (216, 209, 187)          # terrain ground (style-guide plates)
GRID = (150, 140, 110)


def _rgb(rgba):
    return (rgba.r, rgba.g, rgba.b)

CYAN = _rgb(cs.CYAN)
RED = _rgb(cs.RED)
RED_DK = _rgb(cs.RED_ICON)
AMBER = _rgb(cs.AMBER)
VIOLET = _rgb(cs.MAGENTA)
WHITE_REF = (120, 120, 120)    # bullseye ink on tan

_F = "/usr/share/fonts/truetype/dejavu/"


def _fonts():
    """Kit roles at brief sizes. `small` — the paragraph face — becomes the
    kit's SERIF body (Source Serif 4): the brief is the product's long-form
    print document, and serif body over sans headings is the technical-manual
    convention the kit preserves. Labels/tables stay sans and mono."""
    return {
        # Authentic v2.1: Bangers is the page banner (H1 only); Barlow
        # Condensed ExtraBold is every SECTION head; Barlow Bold subheads.
        "banner": _brand_font("banner", 66),
        "h1": _brand_font("display", 50),
        "h2": _brand_font("display_bold", 40),
        "h3": _brand_font("display", 30),
        "mono": _brand_font("mono", 28),
        "mono_b": _brand_font("mono_med", 28),
        "mono_s": _brand_font("mono", 22),
        "small": _brand_font("serif", 25),
        "label": _brand_font("sans_bold", 22),
    }


def _page(title, subtitle):
    """The Authentic page (missiongen/authentic.py): navy band with the
    identity rail left and the locator right in mono; the banner title in
    Bangers below it; a Source Sans subtitle; hairline mono footer."""
    from . import authentic as _auth
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    f = _fonts()
    # Band: the identity (publication · product · revision) left, the
    # locator right. The subject goes UNDER the banner, not in the band —
    # a long subject and a locator cannot share 1,300 px of mono.
    _auth.pil_band(d, W, rail_text(""), f"SORTIE STARTER / {title}",
                   f["mono_s"], band_h=56, pad=60)
    d.text((60, 70), title.upper(), font=f["banner"], fill=NAVY)
    d.text((60, 148), subtitle, font=f["label"], fill=DIM)
    d.line([60, H - 66, W - 60, H - 66], fill=GOLD, width=2)
    d.text((60, H - 52), "DSS 1-1B  ·  FOR SIMULATION USE ONLY",
           font=f["mono_s"], fill=DIM)
    tail = f"{_auth.NOT_AFFILIATED}  ·  v{__version__}"
    d.text((W - 60 - d.textlength(tail, font=f["mono_s"]), H - 52), tail,
           font=f["mono_s"], fill=DIM)
    return img, d, f


def _kv(d, f, x, y, label, value, vcol=INK):
    d.text((x, y), label.upper(), font=f["mono_s"], fill=DIM)
    d.text((x, y + 30), str(value), font=f["mono_b"], fill=vcol)


HOUR = {"dawn": "05", "day": "12", "dusk": "18", "night": "22"}
MONTH_ABBR = "JUN"      # mission date is pinned to 21 June of the era year


def _dtg(ctx):
    """Military DTG (D-6): '210500L JUN 1978', not ISO. We set the mission
    clock, so we know it — deterministic per recipe."""
    r = ctx["recipe"]
    # A timing anchor (push/TOT) can move the mission clock off the preset;
    # when it has, the builder records the moved clock and the DTG prints it.
    moved = (ctx.get("stats") or {}).get("start_clock")
    hhmm = moved.replace(":", "") if moved else f"{HOUR.get(r.time_of_day, '12')}00"
    when = ctx.get('mission_date')
    return (f"{when.day:02d}{hhmm}L {when.strftime('%b').upper()} {when.year}" if when
            else f"21{hhmm}L {MONTH_ABBR} {ctx['era_year']}")


def _wrap(d, font, text, width_px):
    words, lines, cur = text.split(), [], ""
    for w in words:
        if d.textlength(w, font=font) > width_px:
            if cur:
                lines.append(cur)
                cur = ""
            fragment = ""
            for ch in w:
                if fragment and d.textlength(fragment + ch, font=font) > width_px:
                    lines.append(fragment)
                    fragment = ""
                fragment += ch
            cur = fragment
            continue
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) > width_px and cur:
            lines.append(cur); cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


def _smea(ctx):
    """SITUATION / MISSION / EXECUTION text (D-1): the brief opens like a
    briefing, not a settings receipt. All composed from recipe + stats —
    deterministic, and honest about what the engine actually placed."""
    from .acnames import display as _acd
    r = ctx["recipe"]; stats = ctx["stats"]
    n_enemy = len(ctx.get("enemy_fields", []))
    threat = stats.get("threat_level", "unassessed")
    tier = (r.threat_tier or "auto")

    situation = (f"{ctx['era_label']} · {ctx['map_label']}. Opposing forces "
                 f"operate from {n_enemy} known airfields; assessed air-defense "
                 f"posture: {threat}."
                 + (" All known systems are GUNS — no radar SAM threat exists "
                    "in this theater." if tier == "guns" else
                    " Threat rings and the numbered order of battle are on the "
                    "theater chart."))
    history = stats.get("historical_context", {})
    if history:
        from .historical_world import CLASSIFICATIONS
        situation += (f" Scenario date {history['date']} — "
                      f"{CLASSIFICATIONS[history['classification']]}. "
                      + "Adaptations and sources are on the historical context page.")
    # Enemy air, in the SITUATION paragraph where a real brief puts it: what
    # they fly AND what they carry. The fit changes how you fight them, so it
    # belongs in the words, not only in a table further down.
    air = _loadouts.summarize(stats.get("enemy_air"))
    if air:
        situation += (" Enemy air: "
                      + "; ".join(f"{a['count']}× {a['type']} "
                                  f"({_loadouts.ROLE_TAGS.get(a['role'], a['role'])}) "
                                  f"with {a['fit'].split(' · ')[0]}"
                                  for a in air[:3])
                      + ". Fits and what they mean are on the theater chart.")
    elif stats.get("no_enemy_air"):
        # Stated, not implied. "No enemy air listed" reads as a gap in the
        # brief; "there is no enemy air force" is the intelligence, and it is
        # what changes how the sortie is flown — nothing forces you off the
        # target but the gun line, and the gun line is why you stay high.
        situation += (" There is NO ENEMY AIR FORCE. Nothing will contest you "
                      "in the air; every threat in this theater fires from the "
                      "ground, and most of it is optically aimed.")

    tgt_labels = [t for t in stats.get("targets", [])]
    if stats.get("route"):
        mission = (f"Conduct a routed strike: {stats['route']}. "
                   f"Your flight plan is loaded — fly the black line, hit your "
                   f"TOT. The route is a starting point, not an order: the "
                   f"target is where it says and everything between it and the "
                   f"runway is yours to change.")
    elif stats.get("bfm"):
        bandit = next((a for a in air if a.get("role") == "bfm"), None)
        mission = ("Air combat training: engage and defeat your adversary "
                   f"({stats['bfm'].split('(')[-1].rstrip(')')}) at the merge. "
                   + (f"He is carrying {bandit['fit']}. {bandit['implication']} "
                      if bandit else "")
                   + "Knock it off at a kill, the deck, or bingo.")
    elif r.template == "qf_tanker":
        mission = ("Aerial refueling training: locate the tanker, fly the "
                   "join-up, and cycle contacts until fuel or patience runs out.")
    elif tgt_labels:
        mission = (f"Strike the marked package(s): {', '.join(tgt_labels[:3])} "
                   "— positions on the theater chart and the F10 map. "
                   "Routing is yours: no waypoints are placed.")
    else:
        mission = ("Open tasking. The theater is set and live; targets of "
                   "opportunity per the F10 picture. You own the flight plan — "
                   "no waypoints are placed.")

    sup = stats.get("support", [])
    execution = ((f"On station: {', '.join(sup[:4])}. " if sup else
                  "No airborne support tasked. ")
                 + "Comm ladder and TACAN on the COMMS/NAV page; the same "
                   "charts ride the in-jet kneeboard. "
                 + ("Guns defend the target — plan the run-in and off-target "
                    "turn before you commit. One pass." if tier == "guns" else
                    "Respect the WEZ rings; they are drawn to scale."))
    if stats.get("flight_composition"):
        execution += " " + stats["flight_composition"]
    return situation, mission, execution


# ---------------------------------------------------------------- page 1: brief
def page_mission_data(ctx, comms):
    from .acnames import display as _acd
    r = ctx["recipe"]
    stats = ctx["stats"]
    img, d, f = _page("MISSION BRIEF", "Pre-flight briefing pack — pairs with the .miz")
    d.text((60, 200), f'{ctx["map_label"]} · {ctx["era_label"]}', font=f["h1"], fill=NAVY)
    d.text((60, 290), f'{r.coalition.upper()} · {_acd(r.aircraft)} · '
                      f'{"THE CARRIER" if ctx["carrier_home"] else ctx["home"].name}'
                      f' · DTG {_dtg(ctx)}',
           font=f["h3"], fill=DIM)

    # ---- SITUATION / MISSION / EXECUTION (D-1) -----------------------------
    y = 390
    for head, text, col in zip(
            ("SITUATION", "MISSION", "EXECUTION"), _smea(ctx),
            (INK, NAVY, INK)):
        d.text((60, y), head, font=f["h3"], fill=INK)
        d.line([60, y + 42, W - 60, y + 42], fill=GOLD, width=2)
        y += 56
        for line in _wrap(d, f["small"], text, W - 150)[:6]:
            d.text((60, y), line, font=f["small"], fill=col)
            y += 34
        y += 26

    # ---- mission data strip (compressed; the old page was ONLY this) -------
    d.line([60, y, W - 60, y], fill=(223, 227, 232), width=2)
    y += 18
    if ctx.get("qnh_hpa"):
        from . import pressure
        qnh = pressure.format_qnh(ctx["qnh_hpa"]).split(" / ")[0]
    else:
        qnh = "29.92 inHg"
    col1, col2, col3, col4 = 60, 420, 780, 1110
    _kv(d, f, col1, y, "start", r.start)
    _kv(d, f, col2, y, "conditions", f"{r.time_of_day} / {r.weather}")
    _kv(d, f, col3, y, "qnh", qnh)
    _kv(d, f, col4, y, "variation", r.seed)
    y += 106
    if stats.get("alignment"):
        d.text((60, y), "COALITION (International Alignment)", font=f["mono_s"], fill=DIM)
        d.text((60, y + 30), " · ".join(stats["alignment"])[:80], font=f["mono_b"], fill=CYAN)

    # ---- tasking excerpt (scenario templates carry their own words) --------
    tpl_brief = []
    if r.template:
        tpl = load_json("mission_templates").get(r.template) or {}
        tpl_brief = tpl.get("brief", [])[:9]
    if tpl_brief:
        by = y + 110
        d.rectangle([60, by, W - 60, by + 44 + 34 * len(tpl_brief)],
                    outline=(223, 227, 232), width=2)
        d.text((90, by + 12), "TASKING (as briefed in the .miz)", font=f["mono_s"], fill=DIM)
        for i, line in enumerate(tpl_brief):
            d.text((90, by + 46 + i * 34), line[:88], font=f["mono_s"], fill=INK)

    # ---- get-flying strip (kept, tightened) --------------------------------
    d.rectangle([60, H - 300, W - 60, H - 120], outline=GOLD, width=3)
    d.text((90, H - 276), "GET FLYING", font=f["h3"], fill=NAVY)
    for i, line in enumerate([
            "1. Drop the .miz into Saved Games/DCS/Missions — COMM1 presets are pre-tuned",
            "2. Same charts ride in-jet on the kneeboard (RShift+K)",
            f"3. Variation {r.seed}: same settings + seed rebuild THIS exact mission — share it"]):
        d.text((90, H - 224 + i * 34), line, font=f["small"], fill=INK)
    return img


# --------------------------------------------------------------- page 2: chart
WATER = (174, 191, 199)          # style-guide plate sea
COAST = (138, 152, 158)
BLUE_INK = (31, 95, 168)
AMBER_INK = (156, 100, 16)
NM = 1852.0


def page_theater_chart(ctx):
    """Theater chart, chart-standard: land/water base, labeled graticule,
    MIL-STD-2525 friendly circles / hostile diamonds, decluttered labels,
    numbered threat order of battle, bullseye range rings, title block."""
    from dcs import mapping
    gfx = ctx["gfx"]
    r = ctx["recipe"]
    own = ctx["own_fields"]; enemy = ctx["enemy_fields"]
    terrain = ctx["home"].position._terrain
    img, d, f = _page("THEATER CHART", f'{ctx["map_label"]} — schematic · not for navigation')

    # ---- world bounds (equal scale; panel letterboxed to the data aspect) ----
    pts = [(a.position.x, a.position.y) for a in own + enemy]
    if gfx.get("bullseye"):
        pts.append((gfx["bullseye"].x, gfx["bullseye"].y))
    for p, wez, _l in gfx.get("threats", []):
        pts += [(p.x + wez, p.y + wez), (p.x - wez, p.y - wez)]
    for p, _l in gfx.get("targets", []):
        pts.append((p.x, p.y))
    if gfx.get("carrier"):
        pts.append((gfx["carrier"][0].x, gfx["carrier"][0].y))
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    pad = max(max(xs) - min(xs), max(ys) - min(ys), 1) * 0.07
    x0, x1 = min(xs) - pad, max(xs) + pad          # north span
    y0, y1 = min(ys) - pad, max(ys) + pad          # east span
    AW, AH = W - 120, H - 720                      # room below for OOB + legend
    s = min(AW / (y1 - y0), AH / (x1 - x0))
    PW, PH = int((y1 - y0) * s), int((x1 - x0) * s)
    PX0, PY0 = (W - PW) // 2, 200

    panel = Image.new("RGB", (PW, PH), TAN)
    pd = ImageDraw.Draw(panel)

    def px(x, y):
        return ((y - y0) / (y1 - y0) * PW, (1 - (x - x0) / (x1 - x0)) * PH)

    def scale(m):
        return m / (y1 - y0) * PW

    def ll(lat, lon):
        p = mapping.Point.from_latlng(mapping.LatLng(lat, lon), terrain)
        return px(p.x, p.y)

    # ---- land / water base -------------------------------------------------
    coast = load_json("coastlines").get(r.map, {})
    for poly in coast.get("water", []):
        pd.polygon([ll(a, b) for a, b in poly], fill=WATER, outline=COAST)
    for poly in coast.get("islands", []):
        pd.polygon([ll(a, b) for a, b in poly], fill=TAN, outline=COAST)

    # ---- labeled graticule at whole degrees --------------------------------
    c_sw = mapping.Point(x0, y0, terrain).latlng()
    c_ne = mapping.Point(x1, y1, terrain).latlng()
    la0, la1 = sorted((c_sw.lat, c_ne.lat)); lo0, lo1 = sorted((c_sw.lng, c_ne.lng))
    step = 1 if max(la1 - la0, lo1 - lo0) <= 7 else 2
    for la in range(int(math.floor(la0)), int(math.ceil(la1)) + 1, step):
        a = ll(la, lo0 - 1); b = ll(la, lo1 + 1)
        pd.line([a, b], fill=GRID, width=1)
        if 0 < a[1] < PH - 16:
            pd.text((8, a[1] + 3), f"N{la}°", font=f["mono_s"], fill=(107, 96, 69))
    for lo in range(int(math.floor(lo0)), int(math.ceil(lo1)) + 1, step):
        a = ll(la0 - 1, lo); b = ll(la1 + 1, lo)
        pd.line([a, b], fill=GRID, width=1)
        if 20 < a[0] < PW - 60:
            pd.text((a[0] + 4, PH - 30), f"E{lo}°", font=f["mono_s"], fill=(107, 96, 69))

    # ---- label declutter: greedy placement against occupied boxes ----------
    boxes = []

    def place_label(sx, sy, text, ink, font=None):
        font = font or f["mono_s"]
        w = pd.textlength(text, font=font); h = 26
        for dx, dy in ((16, -12), (16, 6), (-w - 16, -12), (-w - 16, 6),
                       (16, -34), (-w - 16, -34), (-w / 2, 20), (-w / 2, -42)):
            bx0, by0 = sx + dx, sy + dy
            bb = (bx0 - 3, by0 - 2, bx0 + w + 3, by0 + h)
            if bx0 < 4 or by0 < 4 or bb[2] > PW - 4 or bb[3] > PH - 4:
                continue
            if any(not (bb[2] < o[0] or bb[0] > o[2] or bb[3] < o[1] or bb[1] > o[3])
                   for o in boxes):
                continue
            boxes.append(bb)
            pd.text((bx0, by0), text, font=font, fill=ink)
            return True
        return False

    # ---- bullseye range rings (20/40/60 nm) --------------------------------
    if gfx.get("bullseye"):
        bx, by = px(gfx["bullseye"].x, gfx["bullseye"].y)
        for nmr in (20, 40, 60):
            rr = scale(nmr * NM)
            pd.arc([bx - rr, by - rr, bx + rr, by + rr], 0, 360,
                   fill=(150, 150, 150), width=2)
            pd.text((bx + rr * 0.7071 + 4, by - rr * 0.7071 - 24), f"{nmr}",
                    font=f["mono_s"], fill=(130, 130, 130))

    # ---- support orbits ----------------------------------------------------
    def stadium(p1, p2, rad_m, color):
        rr = max(scale(rad_m), 9)
        a = px(p1.x, p1.y); b = px(p2.x, p2.y)
        ang = math.atan2(b[1] - a[1], b[0] - a[0])
        nx, ny = -math.sin(ang) * rr, math.cos(ang) * rr
        pd.line([a[0] + nx, a[1] + ny, b[0] + nx, b[1] + ny], fill=color, width=4)
        pd.line([a[0] - nx, a[1] - ny, b[0] - nx, b[1] - ny], fill=color, width=4)
        for c in (a, b):
            pd.arc([c[0] - rr, c[1] - rr, c[0] + rr, c[1] + rr], 0, 360,
                   fill=color, width=4)

    for key, rad in (("tanker", 7000), ("awacs", 9000), ("aew", 8000)):
        if gfx.get(key):
            pos, hdg, race, label = gfx[key]
            p2 = mapping.Point(pos.x + race * math.cos(math.radians(hdg)),
                               pos.y + race * math.sin(math.radians(hdg)), terrain)
            stadium(pos, p2, rad, CYAN)
            sx, sy = px(pos.x, pos.y)
            place_label(sx, sy, label.split("·")[0].strip()[:16], BLUE_INK)
    if gfx.get("cap"):
        st1, st2, label = gfx["cap"]
        stadium(st1, st2, 6000, CYAN)
        sx, sy = px(st1.x, st1.y)
        place_label(sx, sy, label[:16], BLUE_INK)

    # ---- threats: scale-true WEZ + AD glyph + NUMBERED site (OOB table) ----
    threat_oob = []
    for i, (p, wez, label) in enumerate(gfx.get("threats", []), 1):
        sx, sy = px(p.x, p.y); rr = max(scale(wez), 12)
        pd.arc([sx - rr, sy - rr, sx + rr, sy + rr], 0, 360, fill=RED, width=4)
        pd.arc([sx - 14, sy - 14, sx + 14, sy + 14], 0, 360, fill=RED_DK, width=3)
        pd.line([sx - 11, sy + 6, sx, sy - 13, sx + 11, sy + 6], fill=RED_DK, width=3)
        pd.ellipse([sx + 10, sy - 30, sx + 40, sy], fill=PAPER, outline=RED_DK, width=2)
        pd.text((sx + 18 - (4 if i >= 10 else 0), sy - 28), str(i),
                font=f["mono_b"], fill=RED_DK)
        # D-3: the glyph + number bubble now claim their space, so target and
        # airfield labels stop rendering straight through them
        boxes.append((sx - 18, sy - 34, sx + 44, sy + 18))
        threat_oob.append((i, label))

    # ---- targets -----------------------------------------------------------
    for p, label in gfx.get("targets", []):
        sx, sy = px(p.x, p.y)
        pd.arc([sx - 20, sy - 20, sx + 20, sy + 20], 0, 360, fill=AMBER, width=4)
        place_label(sx, sy, label[:16], AMBER_INK)

    # ---- carrier + BRC -----------------------------------------------------
    if gfx.get("carrier"):
        anchor, brc, name = gfx["carrier"]
        sx, sy = px(anchor.x, anchor.y)
        pd.rectangle([sx - 7, sy - 16, sx + 7, sy + 16], fill=NAVY)
        ang = math.radians(brc)
        pd.line([sx, sy, sx + 46 * math.sin(ang), sy - 46 * math.cos(ang)],
                fill=BLUE_INK, width=5)
        place_label(sx, sy, f"CVN BRC {int(brc):03d}", BLUE_INK, f["mono_b"])

    # ---- airfields: 2525 — friendly circle, hostile diamond ----------------
    for ap in own:
        sx, sy = px(ap.position.x, ap.position.y)
        pd.ellipse([sx - 10, sy - 10, sx + 10, sy + 10], outline=BLUE_INK, width=4)
        boxes.append((sx - 12, sy - 12, sx + 12, sy + 12))
    for ap in enemy:
        sx, sy = px(ap.position.x, ap.position.y)
        pd.polygon([(sx, sy - 13), (sx + 13, sy), (sx, sy + 13), (sx - 13, sy)],
                   outline=RED_DK, width=4)
        boxes.append((sx - 15, sy - 15, sx + 15, sy + 15))
    for ap in own:
        sx, sy = px(ap.position.x, ap.position.y)
        place_label(sx, sy, ap.name[:16], BLUE_INK)
    for ap in enemy:
        sx, sy = px(ap.position.x, ap.position.y)
        place_label(sx, sy, ap.name[:16], RED_DK)

    # ---- home star + bullseye mark -----------------------------------------
    home = ctx["home"]
    if not ctx["carrier_home"]:
        sx, sy = px(home.position.x, home.position.y)
        for k in range(5):
            a1 = math.radians(-90 + k * 72); a2 = math.radians(-90 + k * 72 + 36)
            pd.line([sx + 19 * math.cos(a1), sy + 19 * math.sin(a1),
                     sx + 8 * math.cos(a2), sy + 8 * math.sin(a2)], fill=GOLD, width=4)
    if gfx.get("bullseye"):
        bx, by = px(gfx["bullseye"].x, gfx["bullseye"].y)
        for rr in (22, 8):
            pd.arc([bx - rr, by - rr, bx + rr, by + rr], 0, 360,
                   fill=WHITE_REF, width=4)
        place_label(bx, by, "BULLSEYE (rings nm)", WHITE_REF)

    # ---- title block (chart-margin data, mil-chart style) ------------------
    tb_w, tb_h = 430, 148
    pd.rectangle([12, PH - tb_h - 12, 12 + tb_w, PH - 12], fill=PAPER,
                 outline=NAVY, width=3)
    pd.text((28, PH - tb_h + 0), f"{ctx['map_label'].upper()} · {ctx['era_label'].upper()}",
            font=f["mono_b"], fill=NAVY)
    pd.text((28, PH - tb_h + 34), f"DTG {_dtg(ctx)}"
            f" · VARIATION {r.seed}", font=f["mono_s"], fill=INK)
    pd.text((28, PH - tb_h + 64), "SCHEMATIC · NOT FOR NAVIGATION",
            font=f["mono_s"], fill=RED_DK)
    km = max(10, int(round((y1 - y0) / 7 / 1000 / 10.0) * 10))
    bar = scale(km * 1000)
    pd.line([28, PH - 34, 28 + bar, PH - 34], fill=INK, width=5)
    for t in (0, bar / 2, bar):
        pd.line([28 + t, PH - 40, 28 + t, PH - 28], fill=INK, width=3)
    pd.text((28 + bar + 12, PH - 44), f"{km} km", font=f["mono_s"], fill=INK)
    pd.text((PW - 64, 10), "N ↑", font=f["h3"], fill=INK)

    img.paste(panel, (PX0, PY0))
    d.rectangle([PX0 - 2, PY0 - 2, PX0 + PW + 2, PY0 + PH + 2],
                outline=(120, 110, 85), width=3)

    # ---- threat order of battle (numbered) + legend under the panel --------
    y = PY0 + PH + 26
    if threat_oob:
        d.text((60, y), "THREAT ORDER OF BATTLE", font=f["h3"], fill=RED_DK)
        y += 44
        col_x, col_n = 60, 0
        for i, label in threat_oob:
            d.text((col_x, y), f"{i:>2}  {label[:30]}", font=f["mono_s"], fill=INK)
            y += 32
            col_n += 1
            if col_n == 4:
                col_n = 0; y -= 4 * 32; col_x += 460
        y = PY0 + PH + 26 + 44 + 4 * 32 + 10

    # ---- ENEMY AIR: what they fly, what they CARRY, and what that means ----
    # The order of battle above tells you where the SAMs are. This tells you
    # how to fight the jets — the half that changes your plan at the merge.
    air = _loadouts.brief_lines(ctx["stats"].get("enemy_air"))
    if air:
        d.text((60, y), "ENEMY AIR", font=f["h3"], fill=RED_DK)
        y += 44
        for who, fit, imp in air[:3]:
            d.text((60, y), who[:26], font=f["mono_s"], fill=INK)
            d.text((400, y), fit[:56], font=f["mono_s"], fill=INK)
            y += 32
            for ln in _wrap(d, f["mono_s"], imp, W - 520)[:2]:
                d.text((400, y), ln, font=f["mono_s"], fill=RED_DK)
                y += 28
            y += 10
    ly = max(y + 6, H - 120)
    items = [(BLUE_INK, "○ friendly field / orbit"), (RED_DK, "◇ hostile field"),
             (RED, "WEZ ring #n"), (AMBER_INK, "target"), (GOLD, "★ start"),
             (WHITE_REF, "◎ bullseye")]
    lx = 60
    for color, text in items:
        d.text((lx, ly), text, font=f["mono_s"], fill=color)
        lx += d.textlength(text, font=f["mono_s"]) + 46
    return img


# ---------------------------------------------------------------- page 3: comms
def page_comms_nav(ctx, comms, nav_points, qnh_hpa):
    img, d, f = _page("COMMS / NAV", "Radio ladder pre-tuned in COMM1 — CHAN = cockpit preset")
    y = 210
    d.text((60, y), "COMM LADDER", font=f["h3"], fill=NAVY); y += 56
    d.rectangle([60, y, W - 60, y + 46], fill=NAVY)
    for tx, tw in (("AGENCY", 90), ("C/S", 440), ("FREQ MHz", 700),
                   ("CHAN", 980), ("TACAN", 1180)):
        d.text((tw, y + 8), tx, font=f["mono_s"], fill=(223, 232, 241))
    y += 46
    for i, (agency, cs_, freq, tacan, _notes) in enumerate(comms.entries[:15]):
        if i % 2:
            d.rectangle([60, y, W - 60, y + 44], fill=(243, 241, 236))
        d.text((90, y + 8), str(agency)[:18], font=f["mono"], fill=INK)
        d.text((440, y + 8), str(cs_)[:13], font=f["mono"], fill=INK)
        d.text((700, y + 8), str(freq), font=f["mono_b"], fill=INK)
        d.text((980, y + 8), comms.chan_label(agency)[:8], font=f["mono_b"],
               fill=(31, 95, 168))
        d.text((1180, y + 8), str(tacan), font=f["mono"], fill=INK)
        y += 44
    y += 40
    if qnh_hpa:
        from . import pressure
        d.text((60, y), "ALTIMETER", font=f["h3"], fill=NAVY); y += 52
        d.text((90, y), pressure.format_qnh(qnh_hpa), font=f["mono_b"], fill=INK)
        y += 70
    if nav_points:
        d.text((60, y), "NAV REFERENCE POINTS", font=f["h3"], fill=NAVY); y += 52
        for name, p in nav_points[:8]:
            ll = p.latlng()
            d.text((90, y), f"{name[:30]:32} {ll.lat:8.4f}  {ll.lng:9.4f}",
                   font=f["mono_s"], fill=INK)
            y += 38
        y += 30

    # ---- ADMIN (D-5/D-7): what the deleted page 4 should always have been —
    # divert data a pilot can act on, plus fill-in fuel planning boxes.
    from . import alignment
    r = ctx["recipe"]
    align = alignment.bases(r.map, r.era)
    d.text((60, y), "ADMIN — DIVERTS", font=f["h3"], fill=NAVY); y += 52
    home = ctx["home"]
    rows = []
    if not ctx["carrier_home"]:
        for ap in ctx["own_fields"]:
            if ap.name == home.name:
                continue
            dx = ap.position.x - home.position.x
            dy = ap.position.y - home.position.y
            rng_nm = math.hypot(dx, dy) / NM
            brg = math.degrees(math.atan2(dy, dx)) % 360
            rwy = f"RWY {int(ap.runways[0].main.heading):03d}" if ap.runways else ""
            rows.append((rng_nm, ap.name, brg, rwy, align.get(ap.name, "")))
    for rng_nm, name, brg, rwy, owner in sorted(rows)[:4]:
        d.text((90, y), f"{name[:22]:<24}{int(brg):03d}° / {rng_nm:3.0f} nm   "
                        f"{rwy:<9} {owner[:14]}", font=f["mono_s"], fill=INK)
        y += 38
    if not rows:
        d.text((90, y), "Recovery: THE CARRIER — Marshal per the comm ladder",
               font=f["mono_s"], fill=INK)
        y += 38
    y += 26
    d.text((60, y), "FUEL", font=f["h3"], fill=NAVY); y += 52
    from .kneeboard import fuel_lines
    fl = fuel_lines(ctx.get("fuel_max_kg"))
    for lab in ("JOKER", "BINGO"):
        d.text((90, y + 6), lab, font=f["mono_b"], fill=INK)
        d.rectangle([260, y, 640, y + 44], outline=(180, 180, 180), width=2)
        if fl:
            d.text((276, y + 8), f"{fl[lab][0]} / {fl[lab][1]}", font=f["mono"], fill=INK)
        y += 60
    if fl:
        d.text((90, y), "plan: JOKER 50% · BINGO 33% internal — adjust for stores and range",
               font=f["mono_s"], fill=DIM)
    return img


# ------------------------------------------------------- page 4: airfield guide
def page_airfield_guide(ctx):
    """Channelization, runways, elevation, parking and the divert order for
    the fields this mission uses — read out of the terrain (fieldguide.py),
    so the page and the field DCS gives you cannot disagree."""
    from . import fieldguide as fg
    img, d, f = _page("AIRFIELD GUIDE", "ATC per DCS auto-assign · runways both ends · elevation · stands · divert order from home")
    table = fg.rows(ctx["own_fields"], None if ctx["carrier_home"] else ctx["home"],
                    ctx["enemy_fields"], map_key=ctx["recipe"].map)
    y = 210

    def header(cols):
        nonlocal y
        d.rectangle([60, y, W - 60, y + 44], fill=NAVY)
        for tx, tw in cols:
            d.text((tw, y + 8), tx, font=f["mono_s"], fill=(223, 232, 241))
        y += 44

    # One runway in the table (the first — DCS's primary); every runway with
    # both headings in the RUNWAY HEADINGS block below. Two runways in a cell
    # overran the elevation column on Nevada.
    cols = (("FIELD", 90), ("ATC UHF", 470), ("ATC VHF", 630), ("RWY", 790),
            ("ELEV FT", 940), ("STANDS", 1090), ("FROM HOME", 1200))
    d.text((60, y), "YOUR SIDE  —  home first, then by distance", font=f["h3"], fill=NAVY); y += 54
    header(cols)
    for i, r in enumerate(table["own"][:11]):
        if i % 2:
            d.rectangle([60, y, W - 60, y + 42], fill=(243, 241, 236))
        # ">" not "★": the mono face has no star and draws a box for it
        star = "> " if r["home"] else "  "
        d.text((90, y + 7), f"{star}{r['name'][:19]}", font=f["mono_b" if r["home"] else "mono"], fill=INK)
        d.text((470, y + 7), fg.fmt_mhz(r["atc"]["uhf"]), font=f["mono_b"], fill=INK)
        d.text((630, y + 7), fg.fmt_mhz(r["atc"]["vhf"]), font=f["mono"], fill=INK)
        d.text((790, y + 7), fg.fmt_rwy(r, first_only=True), font=f["mono"], fill=INK)
        d.text((940, y + 7), f"{r['elev_ft']:,}" if r["elev_ft"] is not None else "—", font=f["mono"], fill=INK)
        d.text((1090, y + 7), str(r["stands"]), font=f["mono"], fill=INK)
        # From the boat there is no "from home" — bearing is None, not 0.
        d.text((1200, y + 7), "" if (r["home"] or r["bearing"] is None)
               else f"{r['bearing']:03d}° / {r['range_nm']:3.0f} nm", font=f["mono"], fill=INK)
        y += 42
    y += 34
    d.text((60, y), "ENEMY (KNOWN)", font=f["h3"], fill=RED_DK); y += 54
    header((("FIELD", 90), ("ATC UHF", 470), ("ATC VHF", 630), ("RWY", 790),
            ("ELEV FT", 940), ("FROM HOME", 1200)))
    for i, r in enumerate(table["enemy"][:8]):
        if i % 2:
            d.rectangle([60, y, W - 60, y + 42], fill=(243, 241, 236))
        d.text((90, y + 7), f"  {r['name'][:19]}", font=f["mono"], fill=INK)
        d.text((470, y + 7), fg.fmt_mhz(r["atc"]["uhf"]), font=f["mono"], fill=INK)
        d.text((630, y + 7), fg.fmt_mhz(r["atc"]["vhf"]), font=f["mono"], fill=INK)
        d.text((790, y + 7), fg.fmt_rwy(r, first_only=True), font=f["mono"], fill=INK)
        d.text((940, y + 7), f"{r['elev_ft']:,}" if r["elev_ft"] is not None else "—", font=f["mono"], fill=INK)
        d.text((1200, y + 7), f"{r['bearing']:03d}° / {r['range_nm']:3.0f} nm" if r["bearing"] is not None else "",
               font=f["mono"], fill=INK)
        y += 42
    y += 40
    d.text((60, y), "RUNWAY HEADINGS", font=f["h3"], fill=NAVY); y += 52
    for r in table["own"][:6]:
        d.text((90, y), f"{r['name'][:22]:<24}{fg.fmt_rwy(r, with_heading=True)[:60]}",
               font=f["mono_s"], fill=INK); y += 36
    y += 30
    d.text((60, y), "NORDO", font=f["h3"], fill=NAVY); y += 52
    home_name = "THE CARRIER" if ctx["carrier_home"] else ctx["home"].name
    for ln in _wrap(d, f["mono_s"], fg.nordo_line(table, home_name), W - 150):
        d.text((90, y), ln, font=f["mono_s"], fill=INK); y += 34
    y += 24
    for ln in _wrap(d, f["small"],
                    "Headings are runway designators (magnetic, as DCS names them). "
                    "ATC frequencies are what DCS assigns the field; tune UHF or VHF to "
                    "taste. Elevations are published field elevations; a dash means none "
                    "is on record for that field. TACAN and ILS are not printed: the "
                    "terrain data this guide is read from does not carry them, and a "
                    "guessed channel is worse than a blank one.", W - 150):
        d.text((90, y), ln, font=f["small"], fill=DIM); y += 32
    return img


# -------------------------------------------------------------- page 4: forces
def page_forces(ctx):
    from . import alignment
    r = ctx["recipe"]
    stats = ctx["stats"]
    img, d, f = _page("AIRFIELDS & FORCES", "Who is where — aligned owner nations, your start, the enemy picture")
    align = alignment.bases(r.map, r.era)
    y = 210
    d.text((60, y), "YOUR SIDE", font=f["h3"], fill=(31, 95, 168)); y += 54
    for ap in ctx["own_fields"][:9]:
        owner = align.get(ap.name, "")
        star = "★ " if (ap.name == ctx["home"].name and not ctx["carrier_home"]) else "  "
        rwy = f"RWY {int(ap.runways[0].main.heading):03d}" if ap.runways else ""
        d.text((90, y), f"{star}{ap.name[:26]:28} {owner:14} {rwy}",
               font=f["mono"], fill=INK)
        y += 42
    if ctx["carrier_home"]:
        d.text((90, y), "★ THE CARRIER — you start on deck", font=f["mono_b"], fill=(31, 95, 168))
        y += 46
    y += 30
    d.text((60, y), "ENEMY PICTURE", font=f["h3"], fill=RED_DK); y += 54
    for ap in ctx["enemy_fields"][:8]:
        owner = align.get(ap.name, "")
        d.text((90, y), f"  {ap.name[:26]:28} {owner}", font=f["mono"], fill=INK)
        y += 42
    y += 20
    d.text((90, y), f"Threat: {stats.get('threat_level', '—')}", font=f["mono_b"], fill=RED_DK)
    y += 70
    d.text((60, y), "SUPPORT AIRBORNE", font=f["h3"], fill=NAVY); y += 54
    for s in stats.get("support", [])[:8]:
        d.text((90, y), f"· {s}", font=f["mono"], fill=INK); y += 40
    return img


# ------------------------------------------------------------------- markdown
def brief_markdown(ctx, comms, nav_points, qnh_hpa):
    from . import alignment, pressure
    r = ctx["recipe"]; stats = ctx["stats"]
    align = alignment.bases(r.map, r.era)
    L = [f"# Mission Brief — {ctx['map_label']} · {ctx['era_label']}", "",
         f"**{r.coalition.upper()}** · {r.aircraft} · "
         f"{'THE CARRIER' if ctx['carrier_home'] else ctx['home'].name}", "",
         f"Start {r.start} · {r.time_of_day} · {r.weather}"
         + (f" · QNH {pressure.format_qnh(qnh_hpa)}" if qnh_hpa else "")
         + f" · variation (seed) {r.seed}", "",
         f"> **Variation {r.seed}:** the same settings + seed rebuild *this exact "
         "mission* every time — share them and a friend flies the identical "
         "flight. Change the seed for a fresh layout of the same setup.", ""]
    if stats.get("flight_composition"):
        L += ["**Your flight:** " + stats["flight_composition"], ""]
    if stats.get("callsign"):
        L += [f"**Callsign {stats['callsign']}.** " + (stats.get("callsign_heritage") or ""), ""]
    if stats.get("alignment"):
        L += [f"Coalition nations: {' · '.join(stats['alignment'])}", ""]
    # THE NOTES COLUMN. It used to be dropped here (`_n`), and the kneeboard
    # PNG was the only place ICLS, Link 4, ACLS and the BRC appeared — small
    # gray text under a row, on an image, inside the .miz. Casmo flew a Case III
    # and said "I have zero idea how to do a case 3 recovery so I was flying
    # around blind." He could not have read the ICLS channel before he started,
    # because the brief he read before he started did not contain it. A boat
    # card that only exists after you are strapped in is not a boat card.
    L += ["## Comms", "", "| Agency | C/S | Freq MHz | CHAN | TACAN | Notes |",
          "|---|---|---|---|---|---|"]
    for agency, cs_, fq, tacan, note in comms.entries[:15]:
        # A stray pipe in a note would silently split the row into two cells.
        note = (note or "").replace("|", "\\|")
        L.append(f"| {agency} | {cs_} | {fq} | {comms.chan_label(agency)} "
                 f"| {tacan} | {note} |")
    if stats.get("player_loadout"):
        L += ["", "## Your loadout", "",
              f"**{stats['player_loadout']}**", "",
              "Fitted for the mission type you picked. Every store is one DCS "
              "allows on that station and one that existed in this era. "
              "Change it in the Mission Editor if you want something else.", ""]
    L += ["", "## Your side", ""]
    for ap in ctx["own_fields"]:
        star = "**★ " if (ap.name == ctx["home"].name and not ctx["carrier_home"]) else ""
        L.append(f"- {star}{ap.name}{'**' if star else ''}"
                 + (f" — {align[ap.name]}" if ap.name in align else ""))
    # The airfield guide — the same rows the PDF page and the kneeboard
    # airfield page print, out of the terrain (fieldguide.py).
    from . import fieldguide as fg
    table = fg.rows(ctx["own_fields"], None if ctx["carrier_home"] else ctx["home"],
                    ctx["enemy_fields"], map_key=ctx["recipe"].map)
    L += ["", "## Airfield guide", "",
          "| Field | ATC UHF | ATC VHF | RWY | Elev ft | Stands | From home |",
          "|---|---|---|---|---|---|---|"]
    for r in table["own"]:
        from_home = "" if (r["home"] or r["bearing"] is None) else f"{r['bearing']:03d}° / {r['range_nm']:.0f} nm"
        elev = r["elev_ft"] if r["elev_ft"] is not None else "—"
        L.append(f"| {'★ ' if r['home'] else ''}{r['name']} | {fg.fmt_mhz(r['atc']['uhf'])} | "
                 f"{fg.fmt_mhz(r['atc']['vhf'])} | {fg.fmt_rwy(r)} | {elev} | {r['stands']} | "
                 f"{from_home} |")
    home_name = "THE CARRIER" if ctx["carrier_home"] else ctx["home"].name
    L += ["", fg.nordo_line(table, home_name), "",
          "*Runway designators are magnetic as DCS names them. A dash under Elev means "
          "no elevation is on record for that field. TACAN/ILS are not printed: the "
          "terrain data this is read from does not carry them.*"]
    L += ["", "## Enemy picture", ""]
    for ap in ctx["enemy_fields"]:
        L.append(f"- {ap.name}" + (f" — {align[ap.name]}" if ap.name in align else ""))
    L += ["", f"Threat: {stats.get('threat_level', '—')}", ""]
    air = _loadouts.brief_lines(stats.get("enemy_air"))
    if air:
        L += ["## Enemy air", ""]
        for who, fit, imp in air:
            L.append(f"- **{who}** — {fit}")
            if imp:
                L.append(f"  - {imp}")
        L += [""]
    L += ["## Support", ""] + [f"- {s}" for s in stats.get("support", [])]
    if stats.get("pattern"):
        from .pattern import activity_line
        L.append(f"- {activity_line(stats['pattern'])}")
    if stats.get("nttr"):
        n = stats["nttr"]
        L += ["", f"## {n.get('title', 'Corridors')}", "", n["md_line"]]
        body = n["brief"][n["brief"].index("") + 1:]     # after the intro block
        for ln in body:
            if not ln.strip():
                continue
            L.append(("- " if not ln.startswith("  ") else "  ") + ln.strip())
        L.append("")
    if stats.get("timing"):
        # THE CLOCK ON THE CARD — the same plan the kneeboard and the in-game
        # text print, so the three cannot disagree.
        from .timing import mmss as _mmss
        t = stats["timing"]
        a = t.get("anchor", "takeoff")
        L += ["", "## Timing", ""]
        if a == "takeoff":
            L.append(f"**Anchor: TAKEOFF.** Wheels up {t.get('takeoff_clock')} "
                     f"({t.get('ground_s', 0) // 60} min after the mission clock starts).")
        else:
            L.append(f"**Anchor: {a.upper()} {t.get('anchor_clock')} at {t.get('anchor_wp')}**, "
                     f"tolerance ±{t.get('tolerance_s')} s. Wheels up {t.get('takeoff_clock')}; "
                     f"mission clock {t.get('start_clock')}.")
        if t.get("hold_s"):
            L.append(f"Hold {t['hold_s'] // 60} min at WP1 — push at the WP1 ETA, not on arrival.")
        L += ["", "| To | GS kt | Leg | Cum | ETA |", "|---|---|---|---|---|"]
        for row in t.get("rows", []):
            hold = f" (+{row['hold_s'] // 60} min hold)" if row.get("hold_s") else ""
            L.append(f"| {row['to']} | {row['gs_kt']} | {_mmss(row['leg_s'])} | "
                     f"{_mmss(row['cum_s'])} | {row['eta']}{hold} |")
        L.append("")
        L.append("First leg timed on a climb schedule; "
                 + ("groundspeeds include the mission's winds aloft."
                    if t.get("wind") else "no wind in this mission."))
        if stats.get("timing_coach_triggers"):
            L.append("The timing coach grades wheels-up, WP1, IP and TARGET "
                     "in-mission and opens a scorecard a minute after the target.")
    if stats.get("historical_context"):
        h = stats["historical_context"]
        from .historical_world import CLASSIFICATIONS
        L += ["", "## Historical context", "", f"{h['date']} — {CLASSIFICATIONS[h['classification']]}"]
        L += [f"- {n}" for n in h.get("notes", [])]
        L += ["- Recorded weapon service years and DCS station compatibility are checked. Unknown service dates, operator availability and module variants remain uncertified."]
        L += [f"- Source: {url}" for url in h.get("sources", [])]
        L += [f"- {n}" for n in stats.get("airspace_notes", []) if n]
        from .historical_library import reference_lines
        L += [f"- {n}" for n in reference_lines(stats.get('historical_references', []))]
    if stats.get("known_issues"):
        # Every expert campaign carries this page. Ours is generated per
        # mission, so the callsign line is about THIS jet.
        L += ["", "## What DCS will get wrong", ""]
        L += [f"- {k}" for k in stats["known_issues"]]
    if nav_points:
        L += ["", "## Nav reference points", ""]
        for name, p in nav_points:
            ll = p.latlng()
            L.append(f"- {name}: {ll.lat:.4f}, {ll.lng:.4f}")
    L += ["", f"*Sortie Starter v{__version__} — brief pairs with the .miz; "
              "same charts ride the in-jet kneeboard.*"]
    return "\n".join(L)


def page_nttr_chart(plan):
    from . import corridor_chart as _nc, corridors as _cor
    t = _cor.data(plan.get("map", "nevada")).get("text", {})
    img, d, f = _page(t.get("chart_title", "CORRIDORS"), t.get("brief_page_subtitle", "this mission's road in red"))
    img.paste(_nc.render_panel(W - 120, 900, plan=plan, scale=1.4), (60, 200))
    img.paste(_nc.render_terminal(W - 120, 560, plan=plan, scale=1.4), (60, 200 + 900 + 14))
    y = 200 + 900 + 14 + 560 + 26
    for ln in _nc.legend_lines(plan)[:3]:
        for wl in _wrap(d, f["small"], ln, W - 120):
            d.text((60, y), wl, font=f["small"], fill=INK)
            y += 34
        y += 6
    return img


def pages_historical(ctx, lines):
    """Paginate evidence and limitations without truncating long source URLs."""
    pages = []
    img, d, f = _page("HISTORICAL CONTEXT", ctx['map_label'])
    y = 210
    for paragraph in lines:
        for line in _wrap(d, f['small'], paragraph, W - 120):
            if y > H - 150:
                pages.append(img)
                img, d, f = _page("HISTORICAL CONTEXT", ctx['map_label'])
                y = 210
            d.text((60, y), line, font=f['small'], fill=INK)
            y += 34
        y += 16
    pages.append(img)
    return pages


def build_brief(brief_ctx, kb_ctx, pdf_path, md_path=None):
    """Render the 4-page brief PDF (+ optional markdown). Returns page count."""
    ctx = dict(brief_ctx)
    ctx["own_fields"] = kb_ctx["own_fields"]
    ctx["enemy_fields"] = kb_ctx["enemy_fields"]
    ctx["qnh_hpa"] = kb_ctx.get("qnh_hpa")
    ctx["fuel_max_kg"] = kb_ctx.get("fuel_max_kg")
    comms = kb_ctx["comms"]
    nav_points = kb_ctx.get("nav_points") or []
    qnh = kb_ctx.get("qnh_hpa")
    # D-7: the old page 4 (Airfields & Forces) duplicated page 1's support list
    # and named enemy fields with no actionable data; its useful half (diverts,
    # owners) now lives in page 3's ADMIN block. Three pages, no filler.
    pages = [
        page_mission_data(ctx, comms),
        page_theater_chart(ctx),
        page_comms_nav(ctx, comms, nav_points, qnh),
        page_airfield_guide(ctx),
    ]
    if kb_ctx.get("nttr_plan"):
        # The NTTR corridor chart: the road this mission flies, on the
        # airspace it flies through (nttr_chart.py).
        pages.append(page_nttr_chart(kb_ctx["nttr_plan"]))
    if kb_ctx.get("historical_notes"):
        pages.extend(pages_historical(ctx, kb_ctx["historical_notes"]))
    # Page locator, centered in the footer rail. The classification-style line
    # this used to print is retired with the Flightline adoption — the kit is
    # explicit about not imitating classification markings, and the _page()
    # footer already carries the form id and the simulation-use note.
    fts = _fonts()
    from . import authentic as _auth
    left_end = 60 + fts["mono_s"].getlength("DSS 1-1B  ·  FOR SIMULATION USE ONLY")
    tail_start = W - 60 - fts["mono_s"].getlength(f"{_auth.NOT_AFFILIATED}  ·  v{__version__}")
    for i, pg in enumerate(pages, 1):
        dd = ImageDraw.Draw(pg)
        loc = f"PAGE {i} OF {len(pages)}"
        lw = dd.textlength(loc, font=fts["mono_s"])
        # Centered in the GAP between the form number and the tail, not on the
        # page: centered on the page it sat on top of "Not affiliated with".
        dd.text(((left_end + tail_start - lw) / 2, H - 52), loc, font=fts["mono_s"], fill=DIM)
    # Pillow's PDF writer JPEG-compresses RGB pages, but looks up the JPEG
    # plugin directly in Image.SAVE — which is only populated after init().
    # Without this, saving raises KeyError('JPEG') or falls back to a 20 MB+
    # ASCIIHex stream. One call fixes both.
    Image.init()
    # deterministic metadata: title from the recipe, timestamps pinned to the
    # mission date — same recipe => byte-identical brief (share-link contract)
    import time
    r = ctx["recipe"]
    when = ctx.get("mission_date")
    stamp = time.struct_time((when.year, when.month, when.day, 12, 0, 0, 0, when.timetuple().tm_yday, 0)) if when else time.struct_time((ctx["era_year"], 6, 21, 12, 0, 0, 0, 173, 0))
    meta = dict(
        title=f"Mission Brief - {ctx['map_label']} {ctx['era_label']} seed {r.seed}",
        author="DCS Sortie Starter", producer=f"Sortie Starter v{__version__}",
        creationDate=stamp, modDate=stamp)
    try:
        pages[0].save(pdf_path, save_all=True, append_images=pages[1:],
                      resolution=175.0, **meta)
    except KeyError:
        # no JPEG codec at all: palettize (lossless for our flat design)
        pal = [p.convert("P", palette=Image.ADAPTIVE, colors=256) for p in pages]
        pal[0].save(pdf_path, save_all=True, append_images=pal[1:],
                    resolution=175.0, **meta)
    if md_path:
        with open(md_path, "w") as fh:
            fh.write(brief_markdown(ctx, comms, nav_points, qnh))
    return len(pages)
