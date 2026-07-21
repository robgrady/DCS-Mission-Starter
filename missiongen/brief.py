"""Mission Starter Brief — the pre-flight briefing pack (PDF + Markdown).

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
from .resolver import load_json

# A4 portrait at ~175 dpi — crisp for screen and print
W, H = 1448, 2048

# print palette (light pages, navy ink — the style-guide register)
PAPER = (250, 249, 246)
INK = (26, 31, 38)
NAVY = (13, 27, 42)
GOLD = (200, 162, 74)
DIM = (108, 117, 125)
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
    try:
        return {
            "h1": ImageFont.truetype(_F + "DejaVuSans-Bold.ttf", 64),
            "h2": ImageFont.truetype(_F + "DejaVuSans-Bold.ttf", 40),
            "h3": ImageFont.truetype(_F + "DejaVuSans-Bold.ttf", 30),
            "mono": ImageFont.truetype(_F + "DejaVuSansMono.ttf", 28),
            "mono_b": ImageFont.truetype(_F + "DejaVuSansMono-Bold.ttf", 28),
            "mono_s": ImageFont.truetype(_F + "DejaVuSansMono.ttf", 22),
            "small": ImageFont.truetype(_F + "DejaVuSans.ttf", 24),
        }
    except OSError:
        f = ImageFont.load_default()
        return {k: f for k in ("h1", "h2", "h3", "mono", "mono_b", "mono_s", "small")}


def _page(title, subtitle):
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    f = _fonts()
    d.rectangle([0, 0, W, 150], fill=NAVY)
    d.text((60, 34), title, font=f["h2"], fill=(255, 255, 255))
    d.text((60, 96), subtitle, font=f["small"], fill=(159, 176, 195))
    d.rectangle([0, 150, W, 156], fill=GOLD)
    d.text((W - 320, H - 46), f"Mission Starter v{__version__}",
           font=f["mono_s"], fill=DIM)
    return img, d, f


def _kv(d, f, x, y, label, value, vcol=INK):
    d.text((x, y), label.upper(), font=f["mono_s"], fill=DIM)
    d.text((x, y + 30), str(value), font=f["mono_b"], fill=vcol)


# ---------------------------------------------------------------- page 1: data
def page_mission_data(ctx, comms):
    r = ctx["recipe"]
    stats = ctx["stats"]
    img, d, f = _page("MISSION BRIEF", "Pre-flight briefing pack — pairs with the .miz")
    d.text((60, 210), f'{ctx["map_label"]} · {ctx["era_label"]}', font=f["h1"], fill=NAVY)
    d.text((60, 300), f'{r.coalition.upper()} · {r.aircraft} · '
                      f'{"THE CARRIER" if ctx["carrier_home"] else ctx["home"].name}',
           font=f["h3"], fill=GOLD)

    y = 420
    d.line([60, y - 20, W - 60, y - 20], fill=(223, 227, 232), width=2)
    col1, col2, col3 = 60, 540, 1010
    _kv(d, f, col1, y, "start", r.start)
    _kv(d, f, col2, y, "time of day", r.time_of_day)
    _kv(d, f, col3, y, "weather", r.weather)
    y += 110
    if ctx.get("qnh_hpa"):
        from . import pressure
        qnh = pressure.format_qnh(ctx["qnh_hpa"]).split(" / ")[0]
    else:
        qnh = "29.92 inHg std"
    _kv(d, f, col1, y, "qnh / altimeter", qnh)
    _kv(d, f, col2, y, "threat", stats.get("threat_level", "—"))
    _kv(d, f, col3, y, "variation (seed)", r.seed)
    y += 110
    _kv(d, f, col1, y, "support", ", ".join(stats.get("support", [])[:3]) or "none")
    _kv(d, f, col3, y, "template", r.template or "custom")

    # aligned nations strip
    y += 130
    if stats.get("alignment"):
        d.text((60, y), "COALITION (International Alignment)", font=f["mono_s"], fill=DIM)
        d.text((60, y + 30), " · ".join(stats["alignment"]), font=f["mono_b"], fill=CYAN)
        y += 100

    # how-to strip
    d.rectangle([60, H - 372, W - 60, H - 120], outline=GOLD, width=3)
    d.text((90, H - 344), "GET FLYING", font=f["h3"], fill=NAVY)
    for i, line in enumerate([
            "1. Drop the .miz into Saved Games/DCS/Missions",
            "2. This brief = the pre-flight read; the same charts ride in-jet on the kneeboard",
            "3. COMM1 presets are pre-tuned — channels on the COMMS page",
            f"4. Variation (seed) {r.seed}: same settings + seed rebuild THIS exact mission —",
            "   share it and a friend gets the identical flight. New seed = fresh layout."]):
        d.text((90, H - 292 + i * 34), line, font=f["small"], fill=INK)
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
    pd.text((28, PH - tb_h + 34), f"DTG {ctx['era_year']}-06-21 · {r.time_of_day.upper()}"
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
        for name, p in nav_points[:10]:
            ll = p.latlng()
            d.text((90, y), f"{name[:30]:32} {ll.lat:8.4f}  {ll.lng:9.4f}",
                   font=f["mono_s"], fill=INK)
            y += 38
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
    if stats.get("alignment"):
        L += [f"Coalition nations: {' · '.join(stats['alignment'])}", ""]
    L += ["## Comms", "", "| Agency | C/S | Freq MHz | CHAN | TACAN |",
          "|---|---|---|---|---|"]
    for agency, cs_, fq, tacan, _n in comms.entries[:15]:
        L.append(f"| {agency} | {cs_} | {fq} | {comms.chan_label(agency)} | {tacan} |")
    L += ["", "## Your side", ""]
    for ap in ctx["own_fields"]:
        star = "**★ " if (ap.name == ctx["home"].name and not ctx["carrier_home"]) else ""
        L.append(f"- {star}{ap.name}{'**' if star else ''}"
                 + (f" — {align[ap.name]}" if ap.name in align else ""))
    L += ["", "## Enemy picture", ""]
    for ap in ctx["enemy_fields"]:
        L.append(f"- {ap.name}" + (f" — {align[ap.name]}" if ap.name in align else ""))
    L += ["", f"Threat: {stats.get('threat_level', '—')}", "",
          "## Support", ""] + [f"- {s}" for s in stats.get("support", [])]
    if nav_points:
        L += ["", "## Nav reference points", ""]
        for name, p in nav_points:
            ll = p.latlng()
            L.append(f"- {name}: {ll.lat:.4f}, {ll.lng:.4f}")
    L += ["", f"*Mission Starter v{__version__} — brief pairs with the .miz; "
              "same charts ride the in-jet kneeboard.*"]
    return "\n".join(L)


def build_brief(brief_ctx, kb_ctx, pdf_path, md_path=None):
    """Render the 4-page brief PDF (+ optional markdown). Returns page count."""
    ctx = dict(brief_ctx)
    ctx["own_fields"] = kb_ctx["own_fields"]
    ctx["enemy_fields"] = kb_ctx["enemy_fields"]
    ctx["qnh_hpa"] = kb_ctx.get("qnh_hpa")
    comms = kb_ctx["comms"]
    nav_points = kb_ctx.get("nav_points") or []
    qnh = kb_ctx.get("qnh_hpa")
    pages = [
        page_mission_data(ctx, comms),
        page_theater_chart(ctx),
        page_comms_nav(ctx, comms, nav_points, qnh),
        page_forces(ctx),
    ]
    # Pillow's PDF writer JPEG-compresses RGB pages, but looks up the JPEG
    # plugin directly in Image.SAVE — which is only populated after init().
    # Without this, saving raises KeyError('JPEG') or falls back to a 20 MB+
    # ASCIIHex stream. One call fixes both.
    Image.init()
    # deterministic metadata: title from the recipe, timestamps pinned to the
    # mission date — same recipe => byte-identical brief (share-link contract)
    import time
    r = ctx["recipe"]
    stamp = time.struct_time((ctx["era_year"], 6, 21, 12, 0, 0, 0, 173, 0))
    meta = dict(
        title=f"Mission Brief - {ctx['map_label']} {ctx['era_label']} seed {r.seed}",
        author="DCS Mission Starter", producer=f"Mission Starter v{__version__}",
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
