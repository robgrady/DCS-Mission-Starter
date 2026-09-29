"""BB-19: kneeboard nav charts — rendered server-side, injected into the .miz.

DCS loads mission kneeboard pages from KNEEBOARD/IMAGES/ inside the .miz.
Pages (3:4 portrait, 1024x1366):
  01 comms/nav card          02 airfield data           03 theater overview
No player waypoints anywhere — charts are reference, not routing (boundary principle).
"""
import io
import re
import zipfile
from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 1366

# FLIGHTLINE TECHNICAL (Rob's adopted design system, 12 Aug 2026). Every value
# here comes from missiongen/brand.py -> data/brand/flightline.json — the one
# token source the site and every document share. Do not add local colors.
#
# What changed from the v1.55.0 interim register, and why:
#   * white -> warm PAPER, black -> INK: the kit's manual stock, kinder for
#     sustained reading and true to the F-4E source scans.
#   * the classification banner is GONE, replaced by the identity rail. The
#     kit's research is explicit: do not imitate classification markings. The
#     rail answers better questions anyway — what publication, what subject,
#     what revision, where am I.
#   * a NAVY title band (the kit's section-identity color) instead of rules
#     alone; warning red and caution amber become semantic, never decorative.
from .brand import COLORS, font as _bfont, rail_text

BG = COLORS.paper
FG = COLORS.ink
DIM = COLORS.slate
ACCENT = COLORS.navy          # section identity — never safety
BLUE = COLORS.navy            # chart: own forces
RED = COLORS.warning          # chart + safety: hostile / danger ONLY
LINE = COLORS.rule
NAVY = COLORS.navy

FORM_NO = "DSS 1-1K"           # obviously-fictional publication id


def _fonts():
    """Kit type roles, sized for a 1024x1366 kneeboard page. Keys keep their
    historical names so forty call sites do not churn; the FACES are the
    kit's: condensed display, humanist sans, Plex Mono data."""
    return {
        "banner": _bfont("banner", 54),        # the page title, Bangers (H1 only)
        "h1": _bfont("display", 46),
        "h2": _bfont("display", 30),           # SECTION: Barlow Condensed ExtraBold
        "mono": _bfont("mono", 26),
        "mono_b": _bfont("mono_med", 26),
        "small": _bfont("sans", 21),
        "tiny": _bfont("mono", 16),
    }


def _page(title, subtitle):
    """The Flightline page frame: identity rail top, navy title band, plain
    rule footer with the form number. Pages draw content inside; the frame is
    the identity."""
    from . import authentic as _auth
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    f = _fonts()
    # Authentic v2.1: the navy band carries the identity rail (left) and the
    # locator (right) in mono; the page banner sits under it in Bangers.
    _auth.pil_band(d, W, rail_text(""), f"SORTIE STARTER / {title}",
                   f["tiny"], band_h=44, pad=28)
    d.text((28, 54), title.upper(), font=f["banner"], fill=NAVY)
    if subtitle:
        d.text((W - 28 - d.textlength(subtitle, font=f["tiny"]), 118), subtitle,
               font=f["tiny"], fill=DIM)
    # footer: rule + form number + the non-affiliation line
    d.line([28, H - 64, W - 28, H - 64], fill=LINE, width=1)
    d.text((28, H - 52), FORM_NO + "  ·  FOR SIMULATION USE ONLY",
           font=f["tiny"], fill=DIM)
    tail = _auth.NOT_AFFILIATED
    d.text((W - 28 - d.textlength(tail, font=f["tiny"]), H - 52), tail,
           font=f["tiny"], fill=DIM)
    return img, d, f


def _wrap(d, font, text, width_px):
    """Greedy word wrap to a pixel width (the PDF brief has its own copy —
    kept local so the kneeboard never imports the brief renderer)."""
    words, lines, cur = (text or "").split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) > width_px and cur:
            lines.append(cur); cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


def fuel_lines(fuel_max_kg):
    """JOKER/BINGO planning defaults from internal fuel (Rob: the blank boxes
    'probably need to be fixed'). Rule-of-thumb: JOKER = 50% internal (decide
    to come off target), BINGO = 33% (leave NOW, land with reserve). Printed
    as a plan, in the units each side's gauges read; box stays for overrides."""
    if not fuel_max_kg:
        return None
    lb = fuel_max_kg * 2.20462
    return {
        "JOKER": (f"{round(lb * 0.50 / 100) * 100:,.0f} lb", f"{round(fuel_max_kg * 0.50 / 50) * 50:,.0f} kg"),
        "BINGO": (f"{round(lb * 0.33 / 100) * 100:,.0f} lb", f"{round(fuel_max_kg * 0.33 / 50) * 50:,.0f} kg"),
    }


def page_comms(comms, map_label, era_label, home_name, qnh_hpa=None,
               own_fields=None, home_pos=None, fuel_max_kg=None, routed=False):
    img, d, f = _page("COMMS / NAV", f"{map_label}  ·  {era_label}  ·  home: {home_name}")
    y = 150
    if qnh_hpa:
        from .pressure import format_qnh
        d.text((40, y), f"ALTIMETER (QNH)  {format_qnh(qnh_hpa)}",
               font=f["mono_b"], fill=ACCENT)
        y += 50
    has_ch = bool(getattr(comms, "channels", None))
    # CHAN column is 9 wide: "last ch" is 7 chars, so the old <6 pad ran it
    # straight into the TACAN column — the "last ch-" smudge (D-6).
    ch_hdr = f"{'CHAN':<9}" if has_ch else ""
    d.text((40, y), f"{'AGENCY':<14}{'C/S':<14}{'FREQ':<10}{ch_hdr}{'TACAN'}",
           font=f["mono_b"], fill=ACCENT)
    y += 44
    for agency, cs, freq, tacan, notes in comms.entries:
        ch = f"{comms.chan_label(agency):<9}" if has_ch else ""
        d.text((40, y), f"{agency:<14}{cs:<14}{freq:<10}{ch}{tacan}", font=f["mono"], fill=FG)
        if notes:
            d.text((60, y + 30), notes, font=f["small"], fill=DIM)
            y += 30
        y += 46
        d.line([40, y - 8, W - 40, y - 8], fill=LINE, width=1)

    # ---- ADMIN block (D-5): divert table + fill-in fuel boxes --------------
    # A kneeboard with blank space and no divert data isn't finished. Diverts:
    # nearest friendly fields by range from home, with runway heading.
    y += 26
    d.text((40, y), "DIVERTS", font=f["h2"], fill=ACCENT); y += 44
    if own_fields and home_pos is not None:
        import math as _m
        rows = []
        for ap in own_fields:
            if ap.name == home_name:
                continue
            dx = ap.position.x - home_pos.x
            dy = ap.position.y - home_pos.y
            rng_nm = _m.hypot(dx, dy) / 1852.0
            brg = (_m.degrees(_m.atan2(dy, dx))) % 360
            rwy = f"{int(ap.runways[0].main.heading):03d}" if ap.runways else "  -"
            rows.append((rng_nm, ap.name, brg, rwy))
        for rng_nm, name, brg, rwy in sorted(rows)[:3]:
            d.text((40, y), f"{name[:20]:<22}{int(brg):03d}° / {rng_nm:3.0f} nm   RWY {rwy}",
                   font=f["mono"], fill=FG)
            y += 40
    else:
        d.text((40, y), "— see AIRFIELD DATA page", font=f["mono"], fill=DIM); y += 40
    y += 22
    d.text((40, y), "FUEL", font=f["h2"], fill=ACCENT); y += 44
    # planning defaults printed IN the boxes (50% / 33% internal); the box
    # outline stays so a grease pencil can still override the plan
    fl = fuel_lines(fuel_max_kg)
    for lab in ("JOKER", "BINGO"):
        d.text((40, y + 8), lab, font=f["mono_b"], fill=FG)
        d.rectangle([180, y, 520, y + 44], outline=LINE, width=2)
        if fl:
            d.text((196, y + 9), f"{fl[lab][0]} / {fl[lab][1]}", font=f["mono"], fill=FG)
        y += 58
    if fl:
        d.text((40, y), "plan: JOKER 50% · BINGO 33% internal — adjust for your loadout",
               font=f["small"], fill=DIM)
        y += 30

    # The footer has to tell the truth about THIS mission. It said "no waypoints
    # placed" on every page ever rendered, which stopped being true the moment
    # a pilot switched on automatic waypoints — a card that misdescribes the
    # mission it is bound into is worse than no footer.
    d.text((44, H - 128),
           "DCS SORTIE STARTER — flight plan on the FLIGHT PLAN page; edit it freely"
           if routed else
           "DCS SORTIE STARTER — no waypoints placed; you own the flight plan",
           font=f["small"], fill=DIM)
    return img


def page_airfields(own_fields, enemy_fields, era_year, enemy_air=None):
    img, d, f = _page("AIRFIELD DATA", f"friendly and known enemy fields · circa {era_year}")
    y = 150
    for label, fields, color in (("FRIENDLY", own_fields, BLUE), ("ENEMY (KNOWN)", enemy_fields, RED)):
        d.text((40, y), label, font=f["h2"], fill=color)
        y += 52
        d.text((40, y), f"{'FIELD':<22}{'RWY':<8}{'STANDS'}", font=f["mono_b"], fill=ACCENT)
        y += 40
        for ap in fields:
            rwys = "/".join(f"{int(round(r.heading/10)):02d}" for r in ap.runways) or "-"
            d.text((40, y), f"{ap.name[:21]:<22}{rwys:<8}{len(ap.parking_slots)}",
                   font=f["mono"], fill=FG)
            y += 40
        y += 30

    # ENEMY AIR: the fit, in the jet, on the page you can actually reach in
    # flight. Knowing he only has rear-quarter IR is a decision you make at
    # the merge — no use to you if it only exists on a PDF on the desktop.
    from . import loadouts as _lo
    air = _lo.brief_lines(enemy_air)
    if air:
        d.text((40, y), "ENEMY AIR", font=f["h2"], fill=RED); y += 52
        for who, fit, imp in air[:3]:
            if y > H - 200:
                break
            d.text((40, y), who, font=f["mono_b"], fill=FG); y += 36
            for ln in _wrap(d, f["mono"], fit, W - 140)[:2]:
                d.text((70, y), ln, font=f["mono"], fill=FG); y += 34
            for ln in _wrap(d, f["small"], imp, W - 140)[:3]:
                d.text((70, y), ln, font=f["small"], fill=RED); y += 28
            y += 16
    return img


def page_stores(pylons, label, role, aircraft_id, fuel=None):
    """What is actually hanging on your jet, station by station.

    The engine has composed this fit since v1.48.0 and printed it in exactly
    one place — the PDF brief, which lives on the desktop behind the sim. In
    the cockpit you had to look at the rearm screen or guess. Every other
    kneeboard tool leads with a loadout card because it is the page a pilot
    checks in the air ("do I still have a Maverick, and where is it?").

    Station numbers are DCS's own, so they match the rearm dialog and the
    weapons page — no invented left/right naming to reconcile.
    """
    img, d, f = _page("STORES", f"{aircraft_id}  ·  {role} fit")
    y = 150
    d.text((40, y), "STATION", font=f["mono_b"], fill=ACCENT)
    d.text((190, y), "STORE", font=f["mono_b"], fill=ACCENT)
    y += 42
    for station, name in pylons:
        d.text((40, y), f"{station:>2d}", font=f["mono_b"], fill=FG)
        for i, ln in enumerate(_wrap(d, f["mono"], name, W - 240)[:2]):
            d.text((190, y), ln, font=f["mono"], fill=FG)
            y += 34
            if i:
                break
        else:
            pass
        y += 6
    y += 10
    d.line([40, y, W - 40, y], fill=LINE, width=2)
    y += 24
    for ln in _wrap(d, f["mono"], label or "", W - 80)[:3]:
        d.text((40, y), ln, font=f["mono"], fill=DIM)
        y += 34
    if fuel:
        y += 20
        d.text((40, y), "FUEL", font=f["h2"], fill=ACCENT)
        y += 50
        for k, (lb, kg) in fuel.items():
            d.text((40, y), f"{k:<8}{lb:>12}   {kg:>10}", font=f["mono"], fill=FG)
            y += 36
    y += 24
    for ln in _wrap(d, f["small"],
                    "Station numbers are DCS's own — they match the rearm "
                    "dialog. Change anything you like in the Mission Editor or "
                    "on the ramp; this card describes what you were given, not "
                    "what you must carry.", W - 80):
        d.text((40, y), ln, font=f["small"], fill=DIM)
        y += 30
    return img


def page_route(rows, target_label, home_name, timing=None, timed_elsewhere=False):
    """Leg-by-leg card for an auto-generated flight plan (`bb_route`).

    Only rendered when the user asked for a route, so the no-waypoints default
    is untouched: a mission without `bb_route` has no such page and the
    kneeboard is the three reference pages it has always been.

    This exists because the flight plan in the jet is not enough on its own.
    Half the roster has no moving map — a Sabre, a Spitfire, a MiG-15 pilot
    flies headings and a stopwatch — and the numbers here are the ones that
    survive when the nav system does not.
    """
    img, d, f = _page("FLIGHT PLAN", f"{home_name} -> {target_label} -> {home_name}")
    y = 150
    d.text((40, y), "LEG", font=f["h2"], fill=ACCENT)
    y += 52
    d.text((40, y), f"{'FROM':<9}{'TO':<9}{'HDG(T)':<7}{'DIST':<9}{'ALT':<10}{'IAS':<7}{'TIME'}",
           font=f["mono_b"], fill=ACCENT)
    y += 40
    tot_nm = tot_min = 0.0
    # A corridor plan on NTTR is a dozen legs, not three: tighten the leading
    # so the timing column still fits under it on one page.
    step = 40 if len(rows) <= 7 else 32
    for r in rows:
        d.text((40, y),
               f"{r['from'][:8]:<9}{r['to'][:8]:<9}{r['heading']:03d}    "
               f"{r['nm']:>5.1f} nm {r['alt_ft']:>7,d} ft {r['kt']:>3d} kt "
               f"{r['min']:>4.1f}",
               font=f["mono"], fill=FG)
        y += step
        tot_nm += r["nm"]
        tot_min += r["min"]
    y += 14
    d.line([40, y, W - 40, y], fill=LINE, width=2)
    y += 24
    d.text((40, y), f"OUTBOUND  {tot_nm:.0f} nm   {tot_min:.0f} min",
           font=f["mono_b"], fill=FG)
    y += 60
    if timing:
        y = _timing_block(d, f, y, timing)
    for ln in _wrap(d, f["small"],
                    "HEADINGS ARE TRUE. Apply your theater's magnetic "
                    "variation before you fly them off the compass — we do not "
                    "publish a variation figure we cannot verify against the "
                    "sim. " + ("ETAs are timed on a climb schedule for the first "
                               "leg and include the mission's winds aloft; " if timing
                               else ("The clock is on the next page; " if timed_elsewhere
                                     else "Times are at briefed speeds with no wind; "))
                    + "no join-up and no rejoin: plan fuel against the "
                    "JOKER/BINGO card, not against this. The route is a "
                    "suggestion — the target is where it says, everything "
                    "between is yours to change.",
                    W - 80):
        d.text((40, y), ln, font=f["small"], fill=DIM)
        y += 30
    return img


def page_nttr_chart(plan):
    """The NTTR corridor chart with this mission's road drawn hot
    (nttr_chart.py). Portrait: the panel on top, the legend under it."""
    from . import corridor_chart as _nc, corridors as _cor
    t = _cor.data(plan.get("map", "nevada")).get("text", {})
    img, d, f = _page(t.get("chart_title", "CORRIDORS"), t.get("kneeboard_subtitle", "your road in red"))
    img.paste(_nc.render_panel(W - 56, 560, plan=plan), (28, 150))
    img.paste(_nc.render_terminal(W - 56, 380, plan=plan), (28, 150 + 560 + 10))
    y = 150 + 560 + 10 + 380 + 14
    for ln in _nc.legend_lines(plan)[:2]:
        for wl in _wrap(d, f["small"], ln, W - 56):
            d.text((28, y), wl, font=f["small"], fill=DIM)
            y += 25
        y += 3
    return img


def page_timing(timing, target_label, home_name):
    """The clock on its own page, for a plan too long to share one with the
    legs (the NTTR corridor plans)."""
    img, d, f = _page("TIMING", f"{home_name} -> {target_label} -> {home_name}")
    y = 150
    y = _timing_block(d, f, y, timing)
    for ln in _wrap(d, f["small"],
                    "ETAs are timed on a climb schedule for the first leg and "
                    "include the mission's winds aloft. The corridor points are "
                    "on the clock too: BLACKJACK vectors you, the card tells "
                    "you when.", W - 80):
        d.text((40, y), ln, font=f["small"], fill=DIM)
        y += 30
    return img


def _timing_block(d, f, y, timing):
    if True:
        # THE CLOCK. Same plan the brief printed (timing.py): groundspeed,
        # leg, cumulative and ETA per point, and the anchor the whole card
        # hangs on. This is the column Reflected's card has and ours lacked.
        from .timing import mmss as _mmss
        a = timing.get("anchor", "takeoff")
        head = (f"TIMING  anchor {a.upper()}"
                + (f" {timing.get('anchor_clock')} at {timing.get('anchor_wp')}"
                   f"  +/-{timing.get('tolerance_s')} s" if a != "takeoff" else ""))
        d.text((40, y), head, font=f["mono_b"], fill=ACCENT)
        y += 36
        d.text((40, y), f"WHEELS UP {timing.get('takeoff_clock') or _mmss(timing.get('takeoff_s', 0))}",
               font=f["mono_b"], fill=ACCENT)
        y += 40
        d.text((40, y), f"{'TO':<9}{'GS':>4}  {'LEG':>5}  {'CUM':>6}  {'ETA':<9}",
               font=f["mono_b"], fill=ACCENT)
        y += 36
        tstep = 36 if len(timing.get("rows", [])) <= 7 else 30
        for t in timing.get("rows", []):
            hold = f"  hold {t['hold_s'] // 60} min" if t.get("hold_s") else ""
            d.text((40, y),
                   f"{t['to'][:8]:<9}{t['gs_kt']:>4}  {_mmss(t['leg_s']):>5}  "
                   f"{_mmss(t['cum_s']):>6}  {t['eta']:<9}{hold}",
                   font=f["mono"], fill=FG)
            y += tstep
        y += 20
    return y


def page_theater(own_fields, enemy_fields, bullseye, map_label, support_names,
                 nav_points=None, threats=None, targets=None):
    img, d, f = _page("THEATER OVERVIEW", f"{map_label} · schematic, not to scale for nav")
    nav_points = nav_points or []
    threats = threats or []
    targets = targets or []
    pts = [(a.position.x, a.position.y) for a in own_fields + enemy_fields] + [
        (bullseye["x"], bullseye["y"])] + [(p.x, p.y) for _n, p in nav_points] + [
        (p.x, p.y) for p, _w, _l in threats] + [(p.x, p.y) for p, _l in targets]
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    pad = max((max(xs) - min(xs)), (max(ys) - min(ys)), 1) * 0.18
    x0, x1 = min(xs) - pad, max(xs) + pad
    y0, y1 = min(ys) - pad, max(ys) + pad

    def px(x, y):
        # DCS: x = north, y = east  ->  screen: east right, north up
        sx = 60 + (y - y0) / (y1 - y0) * (W - 120)
        sy = 160 + (1 - (x - x0) / (x1 - x0)) * (H - 320)
        return sx, sy

    def scale(m):
        return m / (y1 - y0) * (W - 120)

    # ---- label declutter (D-3): greedy candidate offsets vs occupied boxes.
    # The old fixed +16px offset triple-stacked Tbilisi/Vaziani/Soganlug into
    # an unreadable smear. Deterministic: same inputs, same placement.
    boxes = []

    def place(sx, sy, text, ink):
        w = d.textlength(text, font=f["small"]); h = 24
        for dx, dy in ((16, -12), (16, 8), (-w - 16, -12), (-w - 16, 8),
                       (16, -34), (-w / 2, 16), (-w / 2, -38), (-w - 16, -34)):
            bx0, by0 = sx + dx, sy + dy
            bb = (bx0 - 2, by0 - 2, bx0 + w + 2, by0 + h)
            if bx0 < 4 or by0 < 120 or bb[2] > W - 4 or bb[3] > H - 100:
                continue
            if any(not (bb[2] < o[0] or bb[0] > o[2] or bb[3] < o[1] or bb[1] > o[3])
                   for o in boxes):
                continue
            boxes.append(bb)
            d.text((bx0, by0), text, font=f["small"], fill=ink)
            return
        # every candidate collided: draw at the default spot anyway (rare)
        d.text((sx + 16, sy - 12), text, font=f["small"], fill=ink)

    # ---- threat rings FIRST (D-4): the PDF chart had them, the page you'd
    # actually glance at under fire didn't. Same data, same rings.
    for p, wez, _label in threats:
        sx, sy = px(p.x, p.y)
        rr = max(scale(wez), 10)
        d.ellipse([sx - rr, sy - rr, sx + rr, sy + rr], outline=RED, width=3)
        d.line([sx - 8, sy + 5, sx, sy - 9, sx + 8, sy + 5], fill=RED, width=3)

    # targets: amber diamonds
    # Darkened for the paper page: the old (240,176,50) was tuned against a
    # near-black background and is nearly invisible on off-white.
    AMB = (166, 104, 0)
    for p, label in targets:
        sx, sy = px(p.x, p.y)
        d.polygon([(sx, sy - 12), (sx + 12, sy), (sx, sy + 12), (sx - 12, sy)],
                  outline=AMB, width=3)
        place(sx, sy, label[:16], AMB)

    # nav reference points: gold triangles
    GOLD = (140, 106, 10)
    for name, p in nav_points:
        sx, sy = px(p.x, p.y)
        d.polygon([(sx, sy - 8), (sx - 7, sy + 6), (sx + 7, sy + 6)], outline=GOLD, width=2)
        place(sx, sy, name.split("/")[0].strip()[:16], GOLD)

    for ap, color in [(a, BLUE) for a in own_fields] + [(a, RED) for a in enemy_fields]:
        sx, sy = px(ap.position.x, ap.position.y)
        d.ellipse([sx - 10, sy - 10, sx + 10, sy + 10], outline=color, width=4)
        boxes.append((sx - 12, sy - 12, sx + 12, sy + 12))
    for ap, color in [(a, BLUE) for a in own_fields] + [(a, RED) for a in enemy_fields]:
        sx, sy = px(ap.position.x, ap.position.y)
        place(sx, sy, ap.name[:18], FG)
    bx, by = px(bullseye["x"], bullseye["y"])
    for r in (18, 10):
        d.ellipse([bx - r, by - r, bx + r, by + r], outline=GOLD, width=3)
    place(bx, by, "BULLSEYE", GOLD)
    d.text((44, H - 156), "N ↑   " + (" · ".join(support_names) if support_names else ""),
           font=f["small"], fill=DIM)
    d.text((44, H - 126), "⌀ red ring = gun/SAM WEZ · ◇ amber = target · freqs on COMMS page",
           font=f["small"], fill=DIM)
    return img


def pages_text(title, subtitle, lines, first_page_no=1):
    """Paginate a long generated card across as many kneeboard pages as it
    needs.

    THE REASON THIS EXISTS. The White Knights cards were landing in the mission
    BRIEFING only, and a briefing is something you read on the ground. In a
    Phantom at three hundred feet with a WSO calling turns you have a kneeboard
    and nothing else, so a card that only lives in the briefing is a card the
    pilot cannot use at the moment it matters.

    Lines that open with `==` are treated as headings and start a new visual
    block; lines that are already column-formatted (leading spaces, or a run of
    two or more spaces) are drawn in mono UNWRAPPED, because wrapping a table
    destroys the only thing that made it a table.
    """
    pages, out = [], None
    img = d = f = None
    y = 0
    body_top, body_bottom = 148, H - 84

    def _new(n):
        nonlocal img, d, f, y
        img, d, f = _page(title if n == 1 else f"{title} ({n})", subtitle)
        y = body_top
        pages.append(img)

    _new(1)
    for ln in (lines or []):
        raw = ln.rstrip()
        if not raw.strip():
            y += 12
            continue
        head = raw.startswith("==")
        # MONO for anything indented or columnar; TABULAR only when the line
        # has a real column gap in it. That distinction matters: a numbered
        # rule like " 12. The wingman will always remain within 90 degrees of
        # lead's heading." is indented but is PROSE, and drawing it unwrapped
        # ran it off the right edge and clipped the sentence — which on a
        # kneeboard means the pilot reads half a rule and believes it.
        indented = raw.startswith(" ") or raw.startswith("-")
        tabular = bool(re.search(r"\S {3,}\S", raw))
        mono = indented or tabular
        font = f["h2"] if head else (f["mono"] if mono else f["small"])
        step = 36 if head else (30 if mono else 27)
        if head:
            chunks = [raw.strip("= ").upper()]
        elif tabular:
            chunks = [raw]
        elif mono:
            # hanging indent, so a wrapped rule still reads as one rule
            pad = len(raw) - len(raw.lstrip())
            # MEASURE the pad, do not guess it. A hard-coded 12 px per space
            # under-counted a 26 px mono face and let the longest rule run a
            # word off the right edge — which is the same defect as before,
            # just smaller.
            padpx = d.textlength(" " * (pad + 4), font=font)
            body = _wrap(d, font, raw.strip(), W - 96 - padpx)
            chunks = [(" " * pad) + body[0]] + \
                     [(" " * (pad + 4)) + x for x in body[1:]]
        else:
            chunks = _wrap(d, font, raw, W - 96)
        need = step * len(chunks) + (14 if head else 0)
        if y + need > body_bottom:
            _new(len(pages) + 1)
            font = f["h2"] if head else (f["mono"] if tabular else f["small"])
        if head:
            y += 10
        for c in chunks:
            d.text((48, y), c, font=font,
                   fill=(NAVY if head else FG))
            y += step
        if head:
            d.line([48, y + 2, W - 48, y + 2], fill=LINE, width=1)
            y += 12
    return pages


def page_image(title, subtitle, img_path, caption=None):
    """A framed kneeboard page carrying one picture.

    Used for the 70 TFS attack diagrams. The image is fitted INSIDE the body
    area and never scaled up: an 850 px scan stretched to 1024 turns line art
    into fuzz, and a fuzzy diagram at three hundred feet is worse than a small
    sharp one.
    """
    img, d, f = _page(title, subtitle)
    top = 148
    bottom = H - 84
    cap_h = 0
    caption = [c for c in (caption or []) if c.strip()]
    if caption:
        cap_h = 26 * sum(max(1, len(_wrap(d, f["small"], c, W - 96)))
                         for c in caption) + 14
    box_w, box_h = W - 96, (bottom - top) - cap_h
    try:
        pic = Image.open(img_path).convert("L").convert("RGB")
    except Exception:
        return img
    scale = min(box_w / pic.width, box_h / pic.height, 1.0)
    pic = pic.resize((max(1, int(pic.width * scale)),
                      max(1, int(pic.height * scale))), Image.LANCZOS)
    x = (W - pic.width) // 2
    img.paste(pic, (x, top))
    y = top + pic.height + 12
    for c in caption:
        for ln in _wrap(d, f["small"], c, W - 96):
            d.text((48, y), ln, font=f["small"], fill=DIM)
            y += 26
        y += 4
    return img


def inject_kneeboard(miz_path, pages):
    """Append rendered pages into the saved .miz under KNEEBOARD/IMAGES/.

    Fixed date_time (same convention as the DTC sidecar): the kneeboard was
    the last zip member carrying wall-clock, which is why identical recipes
    produced byte-different .miz files. Content was always identical; now the
    bytes are too."""
    with zipfile.ZipFile(miz_path, "a", zipfile.ZIP_DEFLATED) as z:
        for i, img in enumerate(pages, 1):
            buf = io.BytesIO()
            img.save(buf, "PNG", optimize=True)
            zi = zipfile.ZipInfo(f"KNEEBOARD/IMAGES/{i:02d}_starter.png",
                                 date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, buf.getvalue())


def build_kneeboard(miz_path, comms, own_fields, enemy_fields, bullseye,
                    map_label, era_label, era_year, home_name, support_names,
                    nav_points=None, qnh_hpa=None, threats=None, targets=None,
                    fuel_max_kg=None, enemy_air=None, route=None,
                    route_target=None, pylons=None, loadout_label=None,
                    loadout_role=None, aircraft_id=None, card=None,
                    card_title=None, diagram=None, diagram_caption=None,
                    timing=None, nttr_plan=None):
    home_pos = next((a.position for a in own_fields if a.name == home_name), None)
    pages = [
        page_comms(comms, map_label, era_label, home_name, qnh_hpa,
                   own_fields=own_fields, home_pos=home_pos,
                   fuel_max_kg=fuel_max_kg, routed=bool(route)),
        page_airfields(own_fields, enemy_fields, era_year, enemy_air=enemy_air),
        page_theater(own_fields, enemy_fields, bullseye, map_label, support_names,
                     nav_points, threats=threats, targets=targets),
    ]
    # Optional pages APPEND. The three reference pages keep the numbers they
    # have always had — a pilot who knows the theater page is 03 should not
    # find a flight plan there because he ticked a box on another screen.
    # Stores before route: it is the page you check first and most often.
    if pylons:
        pages.append(page_stores(pylons, loadout_label, loadout_role or "combat",
                                 aircraft_id or "your aircraft",
                                 fuel_lines(fuel_max_kg)))
    if route:
        # A corridor plan on NTTR is a dozen legs: the legs and the clock no
        # longer share a page, so the clock gets its own (page_timing).
        long_plan = len(route) > 7
        pages.append(page_route(route, route_target or "TARGET", home_name,
                                timing=None if long_plan else timing,
                                timed_elsewhere=bool(long_plan and timing)))
        if long_plan and timing:
            pages.append(page_timing(timing, route_target or "TARGET", home_name))
    if nttr_plan:
        # THE CHART. A corridor plan on NTTR gets the picture of the airspace
        # it flies through, with its own road drawn hot.
        pages.append(page_nttr_chart(nttr_plan))
    # A generated ride card APPENDS, after everything else, for the same reason
    # the optional pages do: a pilot who knows the theater page is 03 must not
    # find something else there because a different card was flown.
    if card:
        pages.extend(pages_text(card_title or "RIDE CARD", map_label, card))
    # The diagram goes LAST, so it is the page you flip to and stay on. The
    # text pages are read once on the ground; the picture is read in the pop.
    if diagram:
        pages.append(page_image(card_title or "ATTACK", map_label, diagram,
                                diagram_caption))
    inject_kneeboard(miz_path, pages)
    return len(pages)
