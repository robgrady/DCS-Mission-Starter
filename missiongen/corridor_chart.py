"""The corridor chart — the Authentic standard map detail, per map.

WHY A CHART AND NOT JUST WAYPOINTS
----------------------------------
Rob: "as an expert military map maker and user can you add visual
representations based on real world corridors." Then: "the corridors overlap
each other and is difficult to see. They're also pixelated."

So the chart is built like a real one, in two ways.

TWO PANELS, NOT ONE. Every real local-area chart splits the terminal area
out of the range picture, because the departures and recoveries all
converge on the field and drawn at range scale they are one blue smear. The
OVERVIEW draws the range: the areas, the transit corridors (Sally, Alamo,
the west road, Mormon Mesa) as lanes, the gates — and the departures and
recoveries only as thin centerlines. The TERMINAL panel is the 40 nm around
Nellis at four times the scale, where the FLEX turnout, the FYTTR arc, STRYK,
MINTT, ARCOE, ACTON and DREAM each get their own lane. Departures are green,
recoveries amber, transits blue; the flown road is red on both panels. A
lane shared by two procedures (MINTT and ARCOE share STUDENT > DOGBONE >
HAYFORD) is drawn once and labelled twice.

ONE RENDERER, EVERY MAP. Everything drawn comes from data/corridors/<map>.json
(corridors.py): the areas, the coast and borders, the roads, the places,
the corridor lanes and the terminal panels. Nevada and Syria are the same
code with different files.

VECTOR FIRST. The drawing is a display list rendered by two backends: SVG
(the site, `/api/corridors/<map>/chart.svg`, sharp at any zoom) and PIL (the kneeboard
PNG and the brief PDF page, drawn at 3x and downsampled — the anti-aliasing
PIL's own primitives do not do). Same list, same picture.

WHAT IS SURVEYED AND WHAT IS DRAWN
----------------------------------
R-4807A and R-4808N are the legal boundary descriptions (60 FR 20635). The
other areas are curated outlines flagged approx in the data and marked ~ on
the chart. The corridors are the router's (nttr.py) — the same lanes on the
F10 map — so chart, flight plan and map cannot disagree.
"""
from __future__ import annotations

import html
import math

from PIL import Image, ImageDraw

from . import corridors as _cor
from .brand import COLORS, font as _font

PAPER = COLORS.paper
INK = COLORS.ink
NAVY = COLORS.navy
SLATE = COLORS.slate
RULE = COLORS.rule
MAGENTA = (160, 60, 170)         # MOA (sectional convention)
TRANSIT = (29, 78, 137)          # accent
TRANSIT_FILL = (221, 231, 245)
DEPART = (6, 118, 71)            # ok green
DEPART_FILL = (214, 238, 226)
RECOVER = (180, 83, 9)           # caution amber
RECOVER_FILL = (250, 230, 205)
HOT = (159, 18, 57)              # danger red — the flown road
HOT_FILL = (250, 214, 224)
BOX_FILL = (236, 230, 242)
RA_FILL = (241, 244, 248)
MOA_FILL = (248, 241, 249)
ROAD = (165, 170, 180)
GHOST = (170, 180, 195)          # a corridor drawn as centerline only
GHOST_FILL = (240, 243, 247)

ROLE_COL = {"transit": (TRANSIT, TRANSIT_FILL), "departure": (DEPART, DEPART_FILL),
            "recovery": (RECOVER, RECOVER_FILL)}

ZONE = (180, 83, 9)              # a deconfliction zone / line (caution amber, dashed)
TMA = (29, 78, 137)              # a control area / CTR (thin dashed navy-blue)
COAST = (120, 150, 190)
BORDER = (140, 140, 150)
SEA_FILL = (236, 243, 250)


def _D(mk):
    return _cor.data(mk)


def _fix(name, mk):
    return _cor.fix(name, mk)


# --------------------------------------------------------------------------- #
# projection
# --------------------------------------------------------------------------- #
class Proj:
    """Equirectangular lat/lon -> pixels, a nautical mile the same length on
    both axes at the panel's mid-latitude."""

    def __init__(self, bounds, w, h, pad=6):
        (lat0, lat1), (lon0, lon1) = bounds["lat"], bounds["lon"]
        self.lat0, self.lat1, self.lon0, self.lon1 = lat0, lat1, lon0, lon1
        self.k = math.cos(math.radians((lat0 + lat1) / 2))
        self.s = min((w - 2 * pad) / ((lon1 - lon0) * self.k), (h - 2 * pad) / (lat1 - lat0))
        self.w, self.h = w, h
        self.ox = (w - (lon1 - lon0) * self.k * self.s) / 2
        self.oy = (h - (lat1 - lat0) * self.s) / 2

    def __call__(self, lat, lon):
        return (self.ox + (lon - self.lon0) * self.k * self.s,
                self.oy + (self.lat1 - lat) * self.s)

    def px_per_nm(self):
        return self.s / 60.0

    def visible(self, lat, lon, margin=0.0):
        return (self.lat0 - margin <= lat <= self.lat1 + margin
                and self.lon0 - margin <= lon <= self.lon1 + margin)


# --------------------------------------------------------------------------- #
# the display list and its two renderers
# --------------------------------------------------------------------------- #
class Canvas:
    """Primitives in chart units (px at scale 1). Rendered to SVG text or,
    via PIL at `ss` times the size and downsampled, to an anti-aliased PNG."""

    def __init__(self, w, h):
        self.w, self.h = int(w), int(h)
        self.ops = []

    def polygon(self, pts, fill=None, stroke=None, width=1.0, dash=None):
        self.ops.append(("poly", list(pts), fill, stroke, width, dash))

    def line(self, pts, stroke, width=1.0, dash=None):
        self.ops.append(("line", list(pts), stroke, width, dash))

    def circle(self, c, r, fill=None, stroke=None, width=1.0):
        self.ops.append(("circle", c, r, fill, stroke, width))

    def text(self, xy, s, size, color, weight="normal", anchor="start", halo=True, mono=False):
        self.ops.append(("text", xy, s, size, color, weight, anchor, halo, mono))

    # ---- SVG -------------------------------------------------------------
    def svg(self, x=0.0, y=0.0):
        out = []
        for op in self.ops:
            k = op[0]
            if k == "poly":
                _, pts, fill, stroke, width, dash = op
                d = " ".join(f"{px + x:.1f},{py + y:.1f}" for px, py in pts)
                out.append(f'<polygon points="{d}" fill="{_c(fill)}" stroke="{_c(stroke)}" '
                           f'stroke-width="{width}"{_dash(dash)} stroke-linejoin="round"/>')
            elif k == "line":
                _, pts, stroke, width, dash = op
                d = " ".join(f"{px + x:.1f},{py + y:.1f}" for px, py in pts)
                out.append(f'<polyline points="{d}" fill="none" stroke="{_c(stroke)}" '
                           f'stroke-width="{width}"{_dash(dash)} stroke-linecap="round" stroke-linejoin="round"/>')
            elif k == "circle":
                _, c, r, fill, stroke, width = op
                out.append(f'<circle cx="{c[0] + x:.1f}" cy="{c[1] + y:.1f}" r="{r:.1f}" '
                           f'fill="{_c(fill)}" stroke="{_c(stroke)}" stroke-width="{width}"/>')
            elif k == "text":
                _, (tx, ty), s, size, color, weight, anchor, halo, mono = op
                fam = ("'IBM Plex Mono', Menlo, Consolas, monospace" if mono
                       else "'Source Sans 3', 'Segoe UI', Arial, sans-serif")
                wt = "700" if weight == "bold" else "400"
                base = (f'x="{tx + x:.1f}" y="{ty + y:.1f}" font-family="{fam}" font-size="{size:.1f}" '
                        f'font-weight="{wt}" text-anchor="{anchor}" dominant-baseline="middle"')
                if halo:
                    out.append(f'<text {base} fill="{_c(PAPER)}" stroke="{_c(PAPER)}" stroke-width="3" '
                               f'stroke-linejoin="round">{html.escape(s)}</text>')
                out.append(f'<text {base} fill="{_c(color)}">{html.escape(s)}</text>')
        return "\n".join(out)

    # ---- PIL ---------------------------------------------------------------
    def pil(self, ss=3) -> Image.Image:
        W, H = self.w * ss, self.h * ss
        img = Image.new("RGB", (W, H), PAPER)
        d = ImageDraw.Draw(img)
        for op in self.ops:
            k = op[0]
            if k == "poly":
                _, pts, fill, stroke, width, dash = op
                P = [(px * ss, py * ss) for px, py in pts]
                if fill and len(P) >= 3:
                    d.polygon(P, fill=fill)
                if stroke and len(P) >= 2:
                    _pil_line(d, P + [P[0]], stroke, max(1, round(width * ss)), dash, ss)
            elif k == "line":
                _, pts, stroke, width, dash = op
                P = [(px * ss, py * ss) for px, py in pts]
                if len(P) >= 2:
                    _pil_line(d, P, stroke, max(1, round(width * ss)), dash, ss)
            elif k == "circle":
                _, (cx, cy), r, fill, stroke, width = op
                d.ellipse([(cx - r) * ss, (cy - r) * ss, (cx + r) * ss, (cy + r) * ss],
                          fill=fill, outline=stroke, width=max(1, round(width * ss)) if stroke else 0)
            elif k == "text":
                _, (tx, ty), s, size, color, weight, anchor, halo, mono = op
                role = ("mono_med" if (mono and weight == "bold") else "mono" if mono
                        else "sans_bold" if weight == "bold" else "sans")
                f = _font(role, max(6, int(round(size * ss))))
                a = {"start": "lm", "middle": "mm", "end": "rm"}[anchor]
                x, y = tx * ss, ty * ss
                if halo:
                    for dx, dy in ((-ss, 0), (ss, 0), (0, -ss), (0, ss), (-ss, -ss), (ss, ss), (-ss, ss), (ss, -ss)):
                        d.text((x + dx, y + dy), s, font=f, fill=PAPER, anchor=a)
                d.text((x, y), s, font=f, fill=color, anchor=a)
        if ss != 1:
            img = img.resize((self.w, self.h), Image.LANCZOS)
        return img


def _c(col):
    return "none" if col is None else "#%02x%02x%02x" % col


def _dash(dash):
    return f' stroke-dasharray="{dash[0]},{dash[1]}"' if dash else ""


def _pil_line(d, P, color, width, dash, ss):
    if not dash:
        d.line(P, fill=color, width=width, joint="curve")
        return
    on, off = dash[0] * ss, dash[1] * ss
    for (x1, y1), (x2, y2) in zip(P, P[1:]):
        L = math.hypot(x2 - x1, y2 - y1)
        if L == 0:
            continue
        ux, uy = (x2 - x1) / L, (y2 - y1) / L
        t = 0.0
        while t < L:
            e = min(L, t + on)
            d.line([x1 + ux * t, y1 + uy * t, x1 + ux * e, y1 + uy * e], fill=color, width=width)
            t += on + off


# --------------------------------------------------------------------------- #
# chart primitives
# --------------------------------------------------------------------------- #
def _hatch(cv, poly, color, step=8, inset=6):
    """Sectional-style inward ticks along a restricted boundary."""
    n = len(poly)
    cx = sum(p[0] for p in poly) / n
    cy = sum(p[1] for p in poly) / n
    for i in range(n):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
        L = math.hypot(x2 - x1, y2 - y1)
        if L < 2:
            continue
        ux, uy = (x2 - x1) / L, (y2 - y1) / L
        nx, ny = -uy, ux
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        if (cx - mx) * nx + (cy - my) * ny < 0:
            nx, ny = -nx, -ny
        t = step / 2
        while t < L:
            px, py = x1 + ux * t, y1 + uy * t
            cv.line([(px, py), (px + nx * inset, py + ny * inset)], color, 0.8)
            t += step


def _lane(cv, a, b, half, stroke, fill):
    (x1, y1), (x2, y2) = a, b
    L = math.hypot(x2 - x1, y2 - y1) or 1.0
    nx, ny = -(y2 - y1) / L * half, (x2 - x1) / L * half
    cv.polygon([(x1 + nx, y1 + ny), (x2 + nx, y2 + ny), (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)],
               fill=fill, stroke=stroke, width=1.2)


def _arrow(cv, a, b, color, size=8):
    (x1, y1), (x2, y2) = a, b
    ang = math.atan2(y2 - y1, x2 - x1)
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    cv.polygon([(mx + size * math.cos(ang), my + size * math.sin(ang)),
                (mx + size * math.cos(ang + 2.5), my + size * math.sin(ang + 2.5)),
                (mx + size * math.cos(ang - 2.5), my + size * math.sin(ang - 2.5))], fill=color)


def _clip_poly(poly, W, H):
    """Sutherland-Hodgman clip of a projected polygon to the panel."""
    def clip(pts, inside, inter):
        out = []
        for i in range(len(pts)):
            a, b = pts[i - 1], pts[i]
            if inside(b):
                if not inside(a):
                    out.append(inter(a, b))
                out.append(b)
            elif inside(a):
                out.append(inter(a, b))
        return out

    def ix(a, b, x):
        return (x, a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0]))

    def iy(a, b, y):
        return (a[0] + (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]), y)

    for inside, inter in ((lambda p: p[0] >= 0, lambda a, b: ix(a, b, 0)),
                          (lambda p: p[0] <= W, lambda a, b: ix(a, b, W)),
                          (lambda p: p[1] >= 0, lambda a, b: iy(a, b, 0)),
                          (lambda p: p[1] <= H, lambda a, b: iy(a, b, H))):
        poly = clip(poly, inside, inter)
        if not poly:
            return []
    return poly


# --------------------------------------------------------------------------- #
# layers
# --------------------------------------------------------------------------- #
def _area_layer(cv, P, chart, labels=True, fs=1.0):
    order = {"tma": 0, "moa": 1, "alert": 2, "zone": 3, "restricted": 4, "restricted_box": 5}
    for a in sorted(chart["areas"], key=lambda a: order.get(a["kind"], 4)):
        poly = _clip_poly([P(la, lo) for la, lo in a["poly"]], P.w, P.h)
        if len(poly) < 3:
            continue
        k = a["kind"]
        if k == "moa":
            cv.polygon(poly, fill=MOA_FILL, stroke=MAGENTA, width=1.6, dash=(10, 6))
        elif k == "alert":
            cv.polygon(poly, fill=None, stroke=MAGENTA, width=1.0, dash=(5, 4))
        elif k == "tma":
            cv.polygon(poly, fill=None, stroke=TMA, width=0.9, dash=(6, 4))
        elif k == "zone":
            cv.polygon(poly, fill=(252, 244, 232), stroke=ZONE, width=1.6, dash=(8, 5))
        elif k == "restricted_box":
            cv.polygon(poly, fill=BOX_FILL, stroke=NAVY, width=1.8)
            _hatch(cv, poly, NAVY, step=7, inset=8)
            xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
            for i in range(int(min(xs) + min(ys)), int(max(xs) + max(ys)), 16):
                pts = []
                for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
                    den = (x2 - x1) + (y2 - y1)
                    if abs(den) < 1e-9:
                        continue
                    t = (i - x1 - y1) / den
                    if 0 <= t <= 1:
                        pts.append((x1 + (x2 - x1) * t, y1 + (y2 - y1) * t))
                pts.sort()
                for (xa, ya), (xb, yb) in zip(pts[0::2], pts[1::2]):
                    cv.line([(xa, ya), (xb, yb)], (205, 195, 220), 0.7)
        else:
            cv.polygon(poly, fill=RA_FILL, stroke=NAVY, width=1.0)
            _hatch(cv, poly, NAVY)
    if not labels:
        return
    for a in chart["areas"]:
        la, lo = a["label_at"]
        if not a.get("label") or not P.visible(la, lo):
            continue                  # an unlabelled sub-area rides on its neighbor's label
        cx, cy = P(la, lo)
        col = MAGENTA if a["kind"] in ("moa", "alert") else ZONE if a["kind"] == "zone" else TMA if a["kind"] == "tma" else NAVY
        lines = a["label"].split("\n") + [a["alt"] + ("  ~" if a.get("approx") else "")]
        for i, ln in enumerate(lines):
            cv.text((cx, cy + i * 13 * fs), ln, (12 if i == 0 else 10) * fs, col,
                    weight="bold" if i == 0 else "normal", anchor="middle")


def _line_layer(cv, P, chart, fs=1.0, labels=True):
    """Coast and borders - schematic polylines from the data. A
    deconfliction line's label sits at its label_at (else its midpoint) and
    only where that point is on the panel."""
    for ln in chart.get("lines", []):
        pts = [P(la, lo) for la, lo in ln["pts"]]
        if ln["kind"] == "coast":
            cv.line(pts, COAST, 1.6)
        elif ln["kind"] == "border":
            cv.line(pts, BORDER, 1.0, dash=(6, 3))
        elif ln["kind"] == "deconfliction":
            cv.line(pts, ZONE, 1.8, dash=(10, 5))
            if labels and ln.get("label") and pts:
                at = ln.get("label_at") or ln["pts"][len(ln["pts"]) // 2]
                if P.visible(*at):
                    m = P(*at)
                    cv.text((m[0] + 5, m[1] - 8), ln["label"], 9.5 * fs, ZONE, weight="bold")


def _road_layer(cv, P, chart, fs=1.0):
    for rd in chart["roads"]:
        cv.line([P(la, lo) for la, lo in rd["pts"]], ROAD, 1.6)
        vis = [(la, lo) for la, lo in rd["pts"] if P.visible(la, lo)]
        if vis:
            x, y = P(*vis[len(vis) // 2])
            cv.text((x + 4, y + 8), rd["name"], 9.5 * fs, ROAD)


def _corridor_pts(P, c, mk):
    return [P(_fix(p, mk)["lat"], _fix(p, mk)["lon"]) for p in c["points"]]


def _on_panel(P, c, mk, margin=0.15):
    return any(P.visible(_fix(p, mk)["lat"], _fix(p, mk)["lon"], margin) for p in c["points"])


def _draw_lanes(cv, P, c, mk, stroke, fill, fs, drawn):
    pts = _corridor_pts(P, c, mk)
    half = c["width_nm"] / 2.0 * P.px_per_nm()
    if len(pts) == 1:
        cv.circle(pts[0], half, fill=fill, stroke=stroke, width=1.2)
    for a, b in zip(pts, pts[1:]):
        key = tuple(sorted((tuple(round(v) for v in a), tuple(round(v) for v in b))))
        if key in drawn:
            continue                  # a shared leg is drawn once, labelled twice
        drawn.add(key)
        _lane(cv, a, b, half, stroke, fill)
    for a, b in zip(pts, pts[1:]):
        if c["role"] == "recovery":
            _arrow(cv, b, a, stroke, 7 * fs)
        elif c["role"] == "departure":
            _arrow(cv, a, b, stroke, 7 * fs)


def _corridor_layer(cv, P, D, mk, plan, lanes_for, fs=1.0, overrides=None):
    overrides = overrides or {}
    used = set(plan["corridors"]) if plan else set()
    drawn = set()
    for c in D["corridors"]:
        if c["id"] in used or not _on_panel(P, c, mk):
            continue
        stroke, fill = (GHOST, GHOST_FILL) if plan else ROLE_COL[c["role"]]
        if lanes_for(c):
            _draw_lanes(cv, P, c, mk, stroke, fill, fs, drawn)
        else:
            cv.line(_corridor_pts(P, c, mk), stroke, 1.0, dash=(4, 3))
    for c in D["corridors"]:
        if c["id"] in used and _on_panel(P, c, mk):
            _draw_lanes(cv, P, c, mk, HOT, HOT_FILL, fs, set())
    for c in D["corridors"]:
        if not _on_panel(P, c, mk, 0.0):
            continue
        hot = c["id"] in used
        if not hot and not lanes_for(c):
            continue
        if plan and not hot:
            continue
        stroke = HOT if hot else ROLE_COL[c["role"]][0]
        pts = _corridor_pts(P, c, mk)
        half = c["width_nm"] / 2.0 * P.px_per_nm()
        ov = overrides.get(c["id"], {})
        if ov.get("hide") and not hot:
            continue                  # another panel carries this label
        seg = min(ov.get("seg", c.get("label_seg", 0)), max(0, len(pts) - 2))
        if len(pts) > 1:
            a, b = pts[seg], pts[seg + 1]
            anchor = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        else:
            anchor = pts[0]
        dx, dy = ov.get("off", c.get("label_off", [1, 0]))
        nx, ny = ov.get("nudge", [0, 0])
        ax = anchor[0] + dx * (half + 8 * fs) + nx * fs
        ay = anchor[1] + dy * (half + 8 * fs) + ny * fs
        anc = "start" if dx > 0 else "end" if dx < 0 else "middle"
        lo, hi = c["block_ft"]
        cv.text((ax, ay - 6 * fs), c["name"], 11 * fs, stroke, weight="bold", anchor=anc)
        cv.text((ax, ay + 6 * fs), f"{lo // 1000}-{hi // 1000}k ft", 9.5 * fs, stroke, anchor=anc, mono=True)


def _point_layer(cv, P, D, mk, fs=1.0, terminal=False):
    gates = D["gates"]
    skip = set(D["chart"].get("hide_fixes", []))
    show_land = set(D["chart"].get("overview_landmarks", []))
    boxes = [] if terminal else [pn["bounds"] for pn in D["chart"].get("panels", []) if pn.get("declutter")]
    for name, fx in D["fixes"].items():
        if name in skip or not P.visible(fx["lat"], fx["lon"]):
            continue
        if boxes and name not in gates and fx.get("kind") != "gate" and name not in show_land and any(
                b["lat"][0] <= fx["lat"] <= b["lat"][1] and b["lon"][0] <= fx["lon"] <= b["lon"][1] for b in boxes):
            continue                  # the panel draws it; the overview stays legible
        x, y = P(fx["lat"], fx["lon"])
        kind = fx.get("kind")
        tag = "~" if fx.get("approx") else ""
        if name in gates or kind == "gate":
            r = 2.0 * P.px_per_nm()
            cv.circle((x, y), r, stroke=TRANSIT, width=1.6)
            cv.circle((x, y), 2.5, fill=TRANSIT)
            cv.text((x + r + 3, y), f"GATE {name}{tag}", 10 * fs, TRANSIT, weight="bold", mono=True)
        elif kind in ("fix", "navaid"):
            if not terminal and fx.get("minor"):
                continue
            s = 4.5 * fs
            cv.polygon([(x, y - s), (x + s, y + s), (x - s, y + s)], fill=PAPER, stroke=INK, width=1.0)
            cv.text((x + s + 2, y), name + tag, 9.5 * fs, INK, mono=True)
        elif kind == "peak":
            s = 4 * fs
            cv.polygon([(x, y - s), (x + s, y + s), (x - s, y + s)], fill=INK)
            cv.text((x + s + 2, y), name, 9.5 * fs, INK)
        elif kind == "landmark" and (terminal or name in show_land):
            cv.circle((x, y), 2.5, fill=PAPER, stroke=INK, width=1.0)
            cv.text((x + 5, y), name + tag, 9.5 * fs, INK)


def _place_layer(cv, P, chart, fs=1.0, terminal=False):
    for pl in chart["places"]:
        if not P.visible(pl["lat"], pl["lon"]) or (pl.get("minor") and not terminal):
            continue
        x, y = P(pl["lat"], pl["lon"])
        if pl["kind"] == "airfield":
            cv.circle((x, y), 4.5, fill=PAPER, stroke=NAVY, width=1.6)
            cv.line([(x - 7, y), (x + 7, y)], NAVY, 1.6)
            cv.text((x, y + 11), pl["name"], 9.5 * fs, NAVY, anchor="middle")
        elif pl["kind"] == "city":
            cv.polygon([(x - 4, y - 4), (x + 4, y - 4), (x + 4, y + 4), (x - 4, y + 4)], fill=SLATE)
            cv.text((x + 7, y), pl["name"], 11 * fs, SLATE, weight="bold")
        else:
            cv.circle((x, y), 2.3, fill=SLATE)
            cv.text((x + 5, y), pl["name"], 9.5 * fs, SLATE)


def _plan_layer(cv, P, plan, mk, fs=1.0):
    pts = []
    for leg in plan["legs"]:
        ll = leg["point"].latlng()
        pts.append((leg["name"], P(ll.lat, ll.lng), P.visible(ll.lat, ll.lng)))
    home = None
    if plan.get("in_cluster", plan.get("from_nellis")):
        cl = _D(mk)["clusters"][plan["cluster"]]
        home = P(cl["center"][0], cl["center"][1])
    seq = ([home] if home else []) + [p for _, p, _ in pts] + ([home] if home else [])
    cv.line(seq, HOT, 2.2)
    for name, (x, y), vis in pts:
        if not vis:
            continue
        if name in ("WP1", "IP", "TARGET", "EXIT"):
            cv.circle((x, y), 5, fill=HOT, stroke=PAPER, width=1.5)
            cv.text((x + 8, y - 8), name, 11 * fs, HOT, weight="bold")
        else:
            cv.circle((x, y), 2.5, fill=HOT)


def _graticule(cv, P, bounds, fs=1.0, step=0.5):
    lat = math.ceil(bounds["lat"][0] / step) * step
    while lat <= bounds["lat"][1] + 1e-9:
        x0, y = P(lat, bounds["lon"][0]); x1, _ = P(lat, bounds["lon"][1])
        cv.line([(x0, y), (x1, y)], RULE, 0.8)
        cv.text((x0 + 4, y - 7), f"{lat:g}N", 8.5 * fs, SLATE)
        lat += step
    lon = math.ceil(bounds["lon"][0] / step) * step
    while lon <= bounds["lon"][1] + 1e-9:
        x, y0 = P(bounds["lat"][1], lon); _, y1 = P(bounds["lat"][0], lon)
        cv.line([(x, y0), (x, y1)], RULE, 0.8)
        cv.text((x + 3, y1 - 8), (f"{-lon:g}W" if lon < 0 else f"{lon:g}E"), 8.5 * fs, SLATE)
        lon += step


def _furniture(cv, P, title, fs=1.0):
    nm20 = 20 * P.px_per_nm()
    bx, by = 44 * fs, P.h - 26 * fs
    cv.polygon([(bx - 8, by - 14 * fs), (bx + nm20 + 26 * fs, by - 14 * fs),
                (bx + nm20 + 26 * fs, by + 14 * fs), (bx - 8, by + 14 * fs)], fill=PAPER)
    cv.line([(bx, by), (bx + nm20, by)], INK, 1.6)
    for i in range(0, 21, 10):
        x = bx + i * P.px_per_nm()
        cv.line([(x, by - 4), (x, by + 4)], INK, 1.2)
        cv.text((x, by + 10 * fs), f"{i}", 9 * fs, INK, anchor="middle", halo=False)
    cv.text((bx + nm20 + 8, by), "nm", 9 * fs, INK, halo=False)
    nx, ny = P.w - 26 * fs, 34 * fs
    cv.line([(nx, ny + 18 * fs), (nx, ny - 4 * fs)], INK, 1.6)
    cv.polygon([(nx, ny - 9 * fs), (nx - 5 * fs, ny + 3 * fs), (nx + 5 * fs, ny + 3 * fs)], fill=INK)
    cv.text((nx, ny + 26 * fs), "N", 10 * fs, INK, weight="bold", anchor="middle")
    cv.polygon([(0.5, 0.5), (P.w - 0.5, 0.5), (P.w - 0.5, P.h - 0.5), (0.5, P.h - 0.5)], stroke=NAVY, width=1.5)
    cv.text((10, 12 * fs), title, 11 * fs, NAVY, weight="bold", mono=True)


# --------------------------------------------------------------------------- #
# the panels
# --------------------------------------------------------------------------- #
def panels(mk: str) -> list:
    return _D(mk)["chart"].get("panels", [])


def panel_for_plan(mk: str, plan: dict | None):
    """The terminal panel of the plan's home cluster, else the first."""
    ps = panels(mk)
    if not ps:
        return None
    if plan:
        for p in ps:
            if plan.get("cluster") in p.get("clusters", [p.get("cluster")]):
                return p
    return ps[0]


def _sea(cv, P, chart, bounds):
    """Sea fill inside the bounds rectangle, the land polygons back on top
    in paper. The canvas may letterbox the bounds; the margins stay paper."""
    if not chart.get("sea"):
        return
    x0, y0 = P(bounds["lat"][1], bounds["lon"][0]); x1, y1 = P(bounds["lat"][0], bounds["lon"][1])
    cv.polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], fill=SEA_FILL)
    for land in chart.get("land", []):
        poly = _clip_poly([P(la, lo) for la, lo in land], P.w, P.h)
        if len(poly) >= 3:
            cv.polygon(poly, fill=PAPER)


def overview(w, h, plan=None, fs=1.0, mk: str = "nevada") -> Canvas:
    """The theatre: areas, coast and borders, transit lanes, gates;
    departures and recoveries as centerlines. With a plan, the flown road is
    red and the rest ghosts."""
    D = _D(mk); chart = D["chart"]
    bounds = chart["bounds"]
    cv = Canvas(w, h)
    P = Proj(bounds, cv.w, cv.h)
    _sea(cv, P, chart, bounds)
    _graticule(cv, P, bounds, fs)
    _line_layer(cv, P, chart, fs)
    _area_layer(cv, P, chart, fs=fs)
    _road_layer(cv, P, chart, fs)
    _corridor_layer(cv, P, D, mk, plan, lanes_for=lambda c: c["role"] == "transit", fs=fs,
                    overrides=chart.get("labels"))
    _point_layer(cv, P, D, mk, fs)
    _place_layer(cv, P, chart, fs)
    if plan:
        _plan_layer(cv, P, plan, mk, fs)
    for pn in panels(mk):
        tb = pn["bounds"]
        tp = [P(tb["lat"][1], tb["lon"][0]), P(tb["lat"][1], tb["lon"][1]),
              P(tb["lat"][0], tb["lon"][1]), P(tb["lat"][0], tb["lon"][0])]
        cv.polygon(tp, stroke=SLATE, width=1.0, dash=(3, 3))
        cv.text((tp[0][0] + 4, tp[0][1] + 9), pn.get("tag", pn["title"]), 8.5 * fs, SLATE, mono=True)
    _furniture(cv, P, chart.get("overview_title", "OVERVIEW"), fs)
    return cv


def terminal(w, h, plan=None, fs=1.0, mk: str = "nevada", panel: dict | None = None) -> Canvas:
    """A terminal-area panel at several times the overview scale: every
    departure and recovery of that cluster as its own lane."""
    D = _D(mk); chart = D["chart"]
    pn = panel or panel_for_plan(mk, plan)
    bounds = pn["bounds"]
    lanes = set(pn.get("lanes", []))
    cv = Canvas(w, h)
    P = Proj(bounds, cv.w, cv.h)
    _sea(cv, P, chart, bounds)
    _graticule(cv, P, bounds, fs, step=pn.get("grid", 0.25))
    _line_layer(cv, P, chart, fs, labels=pn.get("area_labels", False))
    _area_layer(cv, P, chart, labels=pn.get("area_labels", False), fs=fs)
    _road_layer(cv, P, chart, fs)
    _corridor_layer(cv, P, D, mk, plan, lanes_for=lambda c: c["id"] in lanes, fs=fs, overrides=pn.get("labels"))
    _point_layer(cv, P, D, mk, fs, terminal=True)
    _place_layer(cv, P, chart, fs, terminal=True)
    if plan:
        _plan_layer(cv, P, plan, mk, fs)
    _furniture(cv, P, pn["title"], fs)
    return cv


# --------------------------------------------------------------------------- #
# pages
# --------------------------------------------------------------------------- #
def legend_lines(plan: dict | None = None, mk: str | None = None) -> list:
    mk = mk or (plan or {}).get("map", "nevada")
    t = _D(mk).get("text", {})
    L = ["Lanes: BLUE transit corridor, GREEN departure, AMBER recovery; arrow = direction. A lane two procedures share is drawn once and labelled twice."]
    L += t.get("legend", [])
    L.append("The overview draws departures and recoveries as dotted centerlines only; the terminal panels draw them at several times the scale.")
    if plan:
        L.insert(0, f"RED = this mission: {_cor.summary(plan)}; entry {plan['gate_in']}, exit {plan['gate_out']}. Other corridors are ghosted.")
    return L


def render_panel(width: int, height: int, plan: dict | None = None, bounds=None,
                 scale: float = 1.0, mk: str | None = None) -> Image.Image:
    """The overview as an anti-aliased PIL image."""
    mk = mk or (plan or {}).get("map", "nevada")
    return overview(width, height, plan, fs=scale, mk=mk).pil()


def render_terminal(width: int, height: int, plan: dict | None = None, scale: float = 1.0,
                    mk: str | None = None, panel: dict | None = None) -> Image.Image:
    mk = mk or (plan or {}).get("map", "nevada")
    return terminal(width, height, plan, fs=scale, mk=mk, panel=panel).pil()


def page_size(mk: str) -> tuple:
    """The standalone page's (width, height): chart.page in the data, else
    1600x1000. Syria carries four terminal panels and asks for more height."""
    pg = _D(mk)["chart"].get("page") or [1600, 1000]
    return int(pg[0]), int(pg[1])


def _layout(width, height, mk, scale=1.0):
    """Overview left; the terminal panels top-right in a grid of
    chart.panel_cols columns (1 = a stack); legend under. Each panel's height
    follows its bounds' aspect, capped so every row fits; as many fit as fit.
    Returns (top, pad, col_w, ow, oh, placed) with placed = [(panel, x, y, w, h)]
    relative to the column's top-left."""
    chart = _D(mk)["chart"]
    top, pad, gap = int(118 * scale), 20, 10
    col_w = int(width * float(chart.get("panel_col_frac", 0.40)))
    cols = max(1, int(chart.get("panel_cols", 1)))
    ow, oh = width - 3 * pad - col_w, height - top - pad - 24
    b = chart["bounds"]
    mid = (b["lat"][0] + b["lat"][1]) / 2
    b_aspect = ((b["lon"][1] - b["lon"][0]) * math.cos(math.radians(mid))) / (b["lat"][1] - b["lat"][0])
    oh = min(oh, int(ow / b_aspect) + 12)
    avail = int(oh * float(chart.get("panel_frac", 0.72)))
    pw = (col_w - gap * (cols - 1)) // cols
    ps = panels(mk)
    rows = [ps[i:i + cols] for i in range(0, len(ps), cols)]
    if rows:
        cap = (avail - gap * (len(rows) - 1)) // len(rows)
    placed, y = [], 0
    for row in rows:
        ths = []
        for pn in row:
            tb = pn["bounds"]
            mid = (tb["lat"][0] + tb["lat"][1]) / 2
            aspect = ((tb["lon"][1] - tb["lon"][0]) * math.cos(math.radians(mid))) / (tb["lat"][1] - tb["lat"][0])
            ths.append(int(pw / aspect))
        th = min(max(ths), cap) if cols > 1 else max(ths)
        if y + th > avail and placed:
            break
        th = min(th, avail - y) if not placed else th
        for i, pn in enumerate(row):
            placed.append((pn, i * (pw + gap), y, pw if cols > 1 else col_w, th))
        y += th + gap
    return top, pad, col_w, ow, oh, placed


def render_svg(width: int = 1600, height: int = 1000, plan: dict | None = None,
               mk: str | None = None) -> str:
    """The standalone chart as SVG: overview left, terminal panels and
    legend on the right. Vector - sharp at any zoom."""
    from . import authentic as _auth
    from .brand import rail_text
    mk = mk or (plan or {}).get("map", "nevada")
    t = _D(mk).get("text", {})
    title = t.get("chart_title", "CORRIDORS")
    top, pad, col_w, ow, oh, placed = _layout(width, height, mk)
    ov = overview(ow, oh, plan, mk=mk)
    mono = "'IBM Plex Mono', Menlo, Consolas, monospace"
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
           f'font-family="\'Source Sans 3\', \'Segoe UI\', Arial, sans-serif">',
           f'<rect width="{width}" height="{height}" fill="{_c(PAPER)}"/>',
           f'<rect width="{width}" height="40" fill="{_c(NAVY)}"/>',
           f'<text x="{pad}" y="20" fill="#fff" font-family="{mono}" font-size="12" font-weight="700" dominant-baseline="middle">{html.escape(rail_text(""))}</text>',
           f'<text x="{width - pad}" y="20" fill="#fff" font-family="{mono}" font-size="12" text-anchor="end" dominant-baseline="middle">SORTIE STARTER / {html.escape(title)}</text>',
           f'<text x="{pad}" y="76" fill="{_c(NAVY)}" font-family="Bangers, \'Barlow Condensed\', Impact, sans-serif" font-size="40" dominant-baseline="middle">{html.escape(title)}</text>',
           f'<text x="{pad}" y="104" fill="{_c(SLATE)}" font-size="14" dominant-baseline="middle">{html.escape(t.get("chart_subtitle", ""))}</text>',
           f'<g transform="translate({pad},{top})">', ov.svg(), '</g>']
    x0 = 2 * pad + ow
    y = top
    for pn, px, py, pw, th in placed:
        tm = terminal(pw, th, plan, mk=mk, panel=pn)
        out += [f'<g transform="translate({x0 + px},{top + py})">', tm.svg(), '</g>']
        y = max(y, top + py + th)
    y += 26
    out.append(f'<text x="{x0}" y="{y}" fill="{_c(NAVY)}" font-size="16" font-weight="700" dominant-baseline="middle">LEGEND</text>')
    y += 22
    for ln in legend_lines(plan, mk):
        for wl in _wrap_chars(ln, int(96 * col_w / 640)):
            out.append(f'<text x="{x0}" y="{y}" fill="{_c(INK)}" font-size="12.5" dominant-baseline="middle">{html.escape(wl)}</text>')
            y += 16
        y += 5
    out.append(f'<text x="{pad}" y="{height - 12}" fill="{_c(SLATE)}" font-family="{mono}" font-size="11" dominant-baseline="middle">'
               f'Sources: {html.escape(t.get("sources_line", ""))}  ·  {html.escape(_auth.NOT_AFFILIATED)}</text>')
    out.append("</svg>")
    return "\n".join(out)


def render_page(width: int = 1600, height: int = 1000, plan: dict | None = None,
                title: str | None = None, scale: float = 1.0, mk: str | None = None) -> Image.Image:
    """The standalone chart as an anti-aliased PNG with the SVG's layout."""
    from . import authentic as _auth
    from .brand import rail_text
    mk = mk or (plan or {}).get("map", "nevada")
    t = _D(mk).get("text", {})
    title = title or t.get("chart_title", "CORRIDORS")
    img = Image.new("RGB", (width, height), PAPER)
    d = ImageDraw.Draw(img)
    f_tiny = _font("mono", int(12 * scale)); f_banner = _font("banner", int(40 * scale))
    f_sub = _font("sans", int(14 * scale)); f_h = _font("display_bold", int(18 * scale))
    f_leg = _font("sans", int(12.5 * scale))
    _auth.pil_band(d, width, rail_text(""), f"SORTIE STARTER / {title}", f_tiny, band_h=int(40 * scale), pad=20)
    d.text((20, 56 * scale), title, font=f_banner, fill=NAVY)
    d.text((20, 96 * scale), t.get("chart_subtitle", ""), font=f_sub, fill=SLATE)
    top, pad, col_w, ow, oh, placed = _layout(width, height, mk, scale)
    img.paste(overview(ow, oh, plan, fs=scale, mk=mk).pil(), (pad, top))
    x0 = 2 * pad + ow
    y = top
    for pn, px, py, pw, th in placed:
        img.paste(terminal(pw, th, plan, fs=scale, mk=mk, panel=pn).pil(), (x0 + px, top + py))
        y = max(y, top + py + th)
    y += 18
    d.text((x0, y), "LEGEND", font=f_h, fill=NAVY); y += int(24 * scale)
    for ln in legend_lines(plan, mk):
        for wl in _wrap_px(d, ln, f_leg, col_w):
            d.text((x0, y), wl, font=f_leg, fill=INK); y += int(16 * scale)
        y += int(5 * scale)
    d.text((20, height - 20 * scale), f"Sources: {t.get('sources_line', '')}  ·  {_auth.NOT_AFFILIATED}", font=f_tiny, fill=SLATE)
    return img


def _wrap_chars(text, n):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if len(t) <= n:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def _wrap_px(d, text, font, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= width:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines
