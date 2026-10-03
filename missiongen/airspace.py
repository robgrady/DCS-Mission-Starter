"""Historical airspace overlays — Theater Identity pillar 3.

Real corridors / no-fly zones / deconfliction lines for a map+era, drawn on the
F10 *Common* draw layer (shared, published airspace — both sides see it) and
returned as a briefing block. All styling comes from chartstyle.py so the whole
chart reads as one system. INFORMATION — no player waypoints, ever.

Corridors are SQUARE-ended lanes (not racetrack oblongs), nested into their
control zone at the terminating end; zones are circles; deconfliction is a dashed
line. Data: data/historical_airspace.json (lat/lon geometry; widths in statute miles).
"""
from dcs import mapping
from dcs.mapping import LatLng

from . import chartstyle as cs
from .resolver import load_json
from .historical_world import Validity

SM = 1609.34  # one statute mile in metres (the historical unit for Berlin airspace)


def _ll(lat, lon, terrain):
    return mapping.Point.from_latlng(LatLng(lat, lon), terrain)


def _mid(p1, p2, terrain):
    return mapping.Point((p1.x + p2.x) / 2, (p1.y + p2.y) / 2, terrain)


def _draw_poly(layer, abs_pts, color, fill, weight, style):
    """add_freeform_polygon wants position=first-point-absolute, points relative
    (first = 0,0), closed — same convention add_oblong uses internally."""
    p0 = abs_pts[0]
    rel = [mapping.Point(p.x - p0.x, p.y - p0.y, p0._terrain) for p in abs_pts]
    rel.append(mapping.Point(rel[0].x, rel[0].y, p0._terrain))  # close
    layer.add_freeform_polygon(mapping.Point(p0.x, p0.y, p0._terrain), rel,
                               color=color, fill=fill,
                               line_thickness=weight, line_style=style)


def _draw_line(layer, abs_pts, color, weight, style):
    p0 = abs_pts[0]
    rel = [mapping.Point(p.x - p0.x, p.y - p0.y, p0._terrain) for p in abs_pts]
    layer.add_line_segments(mapping.Point(p0.x, p0.y, p0._terrain), rel,
                            color=color, line_thickness=weight, line_style=style)


def _arrow_head(layer, frm, to, color, frac=0.14, lo=6000.0, hi=18000.0):
    """Filled arrowhead at `to`, pointing along frm->to.

    DCS's Arrow shape runs along +Y (due EAST) at angle 0 and its angle field is
    degrees clockwise, so a compass bearing is rebased by -90. `position` is the
    arrow's TAIL, so it sits back one head-length from the terminus."""
    import math as _m
    d = _m.hypot(to.x - frm.x, to.y - frm.y)
    if d < 1000:
        return None
    head = max(lo, min(hi, frac * d))
    brg = _m.degrees(_m.atan2(to.y - frm.y, to.x - frm.x)) % 360
    b = _m.radians(brg)
    tail = mapping.Point(to.x - head * _m.cos(b), to.y - head * _m.sin(b),
                         to._terrain)
    return layer.add_arrow(tail, (brg - 90) % 360, head,
                           color=color, fill=color, line_thickness=2)


def _zone_radius_m(overlay):
    """Control-zone radius (m) if the overlay has a zone — used to nest corridors."""
    for f in overlay.get("features", []):
        if f["kind"] == "zone":
            return f["radius_sm"] * SM
    return 0.0


def add_historical_airspace(m, map_key, era, overlay_ids=None, only_always=False):
    """Draw every historical-airspace overlay valid for map_key+era.

    only_always=True draws just the overlays marked "always": true — standing
    real-world airspace that must appear on EVERY mission on the map regardless
    of the Historical airspace toggle (the R-4808N Groom box on Nevada: even
    Red Flag players are briefed to stay out of the Box in real life).

    Returns (drawn_overlay_ids, briefing_lines). Safe to call unconditionally —
    returns ([], []) when the map/era has no overlay.
    """
    data = load_json("historical_airspace").get(map_key, {})
    if not data:
        return [], []
    layer = m.drawings.get_layer_by_name("Common")
    terrain = m.terrain
    drawn, briefs = [], []

    for oid, ov in data.items():
        if not Validity.from_data(ov).contains(m.start_time.date()):
            continue
        if era not in ov.get("eras", []):
            continue
        if only_always and not ov.get("always"):
            continue
        if overlay_ids is not None and oid not in overlay_ids:
            continue

        nest = _zone_radius_m(ov)

        for f in ov["features"]:
            kind = f["kind"]
            if kind == "corridor":
                col, fill, wt, st = cs.spec("corridor")
                p1 = _ll(f["from"][0], f["from"][1], terrain)
                p2 = _ll(f["to"][0], f["to"][1], terrain)
                half = f["width_sm"] * SM / 2.0
                corners = cs.corridor_polygon(p1, p2, half, nest_radius=nest)
                _draw_poly(layer, corners, col, fill, wt, st)
                # dot-dash centerline from the start to the nested terminus
                import math
                dx, dy = p2.x - p1.x, p2.y - p1.y
                d = math.hypot(dx, dy) or 1.0
                end = mapping.Point(p2.x - dx / d * nest, p2.y - dy / d * nest, terrain)
                cc, _cf, cw, csl = cs.spec("centerline")
                _draw_line(layer, [p1, end], cc, cw, csl)
                # Direction of transit, as a real filled arrowhead rather than a
                # bare line. The corridor data carries from/to, so the lane has
                # an authored direction and the chart should say so.
                _arrow_head(layer, p1, end, cc)
                cs.label(layer, _mid(p1, end, terrain),
                         f"» {f['name']}  ≤{f['ceiling_ft']:,} ft", col)
            elif kind == "zone":
                col, fill, wt, st = cs.spec("zone")
                c = _ll(f["center"][0], f["center"][1], terrain)
                layer.add_circle(c, radius=f["radius_sm"] * SM, color=col,
                                 fill=fill, line_thickness=wt, line_style=st)
                cs.label(layer, c, f"⬡ {f['name']}", col)
                m.triggers.add_triggerzone(c, radius=f["radius_sm"] * SM,
                                           name=f"AIRSPACE {f['name']}")
            elif kind == "box":
                # Restricted-area box, VFR-chart style: boundary polygon from
                # corner lat/lons + the sectional's data panel as the label
                # (designator on top, then ALTITUDE / TIME OF USE / agency —
                # the same fields a Las Vegas sectional prints for R-4808).
                col, fill, wt, st = cs.spec(f.get("category", "restricted"))
                pts = [_ll(v[0], v[1], terrain) for v in f["corners"]]
                _draw_poly(layer, pts, col, fill, wt, st)
                cx = sum(p.x for p in pts) / len(pts)
                cy = sum(p.y for p in pts) / len(pts)
                center = mapping.Point(cx, cy, terrain)
                panel = [f"▨ {f['name']}"] + f.get("panel", [])
                cs.label(layer, center, "\n".join(panel), col)
                # trigger zone so scripts/designers can hook violations
                import math as _math
                rad = max(_math.hypot(p.x - cx, p.y - cy) for p in pts)
                m.triggers.add_triggerzone(center, radius=rad,
                                           name=f"AIRSPACE {f['name']}")
            elif kind == "line":
                col, _fill, wt, st = cs.spec(f.get("category", "deconfliction"))
                pts = [_ll(v[0], v[1], terrain) for v in f["points"]]
                _draw_line(layer, pts, col, wt, st)
                midi = pts[len(pts) // 2]
                cs.label(layer, midi, f"— {f['name']}", col, size=12)

        briefs.append("")
        briefs.append(f"== {ov.get('brief_title', ov['label'])} ==")
        briefs.extend(ov.get("brief", []))
        drawn.append(oid)

    return drawn, briefs
