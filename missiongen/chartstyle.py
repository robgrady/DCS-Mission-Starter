"""Shared tactical-chart style system — one visual language for every F10 overlay.

A DCS-drawing-tool subset of MIL-STD-2525D (symbols) + JP 3-52 (airspace control
measures) + FAA/ICAO charting conventions (line styles, special-use airspace).
Authenticity comes from LINE STYLE + WEIGHT + RESTRAINT + ICONS, never fill flood.
See docs/chart-authenticity-evaluation.md and the Tactical Chart Style Guide PDF.

graphics.py, airspace.py (and future overlay modules) import their colours,
weights, line styles and icons from here so the whole chart reads as one system.
"""
from dcs import mapping
from dcs.drawing.drawing import Rgba, LineStyle
from dcs.drawing.icon import StandardIcon

# --- palette: saturated line colour, near-transparent fill -------------------
RED = Rgba(224, 80, 80, 235)          # threat / hostile / no-fly
RED_ICON = Rgba(122, 31, 31, 255)     # darker glyph so it reads inside the ring
CYAN = Rgba(90, 170, 255, 235)        # friendly / controlled / corridor
MAGENTA = Rgba(180, 140, 255, 235)    # special-use / advisory
AMBER = Rgba(240, 170, 60, 235)       # deconfliction / caution
WHITE = Rgba(230, 230, 230, 235)      # neutral reference (bullseye/nav)
LABEL_BG = Rgba(0, 0, 0, 90)          # tight halo behind labels

def _fill(c, a):
    return Rgba(c.r, c.g, c.b, a)

# --- category → drawing spec (color, fill, weight, line_style) ----------------
# fill alpha stays in the 0-22 band (a chart is line-work, not colored glass).
CATEGORY = {
    "threat":        dict(color=RED,     fill=_fill(RED, 10),     weight=3, style=LineStyle.Solid),
    "no_fly":        dict(color=RED,     fill=_fill(RED, 0),      weight=6, style=LineStyle.Boundry3),
    "corridor":      dict(color=CYAN,    fill=_fill(CYAN, 15),    weight=3, style=LineStyle.Solid),
    "centerline":    dict(color=CYAN,    fill=_fill(CYAN, 0),     weight=1, style=LineStyle.DotDash),
    "zone":          dict(color=CYAN,    fill=_fill(CYAN, 20),    weight=4, style=LineStyle.Solid),
    "restricted":    dict(color=MAGENTA, fill=_fill(MAGENTA, 12), weight=3, style=LineStyle.Boundry1),
    "deconfliction": dict(color=AMBER,   fill=_fill(AMBER, 0),    weight=3, style=LineStyle.Dash),
    "bullseye":      dict(color=WHITE,   fill=_fill(WHITE, 10),   weight=2, style=LineStyle.Solid),
}


def spec(category):
    """(color, fill, weight, style) for a category — falls back to a neutral."""
    s = CATEGORY.get(category, CATEGORY["corridor"])
    return s["color"], s["fill"], s["weight"], s["style"]


def label(layer, pos, text, color, size=13, angle=0):
    layer.add_text_box(pos, text, color=color, fill=LABEL_BG,
                       font_size=size, border_thickness=0, angle=angle)


def air_defense_icon(layer, pos, scale=0.6, color=RED_ICON):
    """MIL-STD-2525 air-defense glyph at a SAM site (inside its WEZ ring)."""
    return layer.add_icon(pos, StandardIcon.AirDefense, scale=scale, color=color)


def search_radar_icon(layer, pos, scale=0.6, color=RED_ICON):
    return layer.add_icon(pos, StandardIcon.SearchRadar, scale=scale, color=color)


def corridor_polygon(p1, p2, half_width, nest_radius=0.0):
    """Four corners of a SQUARE-ended lane from p1 to p2, half_width either side.

    A corridor is a straight-sided lane, NOT a racetrack — square ends, not
    rounded (the oblong primitive was wrong for this). If nest_radius > 0 the p2
    ('to') end is pulled back by that distance so the lane tucks into a control
    zone circle of that radius instead of poking a flat wall through it.
    """
    import math
    dx, dy = p2.x - p1.x, p2.y - p1.y
    d = math.hypot(dx, dy) or 1.0
    ux, uy = dx / d, dy / d              # unit along axis
    nx, ny = -uy, ux                     # unit perpendicular
    # pull the terminating end back into the zone
    ex, ey = p2.x - ux * nest_radius, p2.y - uy * nest_radius
    t = mapping.Point(ex, ey, p1._terrain)
    hw = half_width
    return [
        mapping.Point(p1.x + nx * hw, p1.y + ny * hw, p1._terrain),
        mapping.Point(t.x + nx * hw,  t.y + ny * hw,  p1._terrain),
        mapping.Point(t.x - nx * hw,  t.y - ny * hw,  p1._terrain),
        mapping.Point(p1.x - nx * hw, p1.y - ny * hw, p1._terrain),
    ]
