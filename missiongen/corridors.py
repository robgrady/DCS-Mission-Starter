"""Corridors: how a flight actually gets from its base to the fight, per map.

WHY
---
Rob, on NTTR: "Any mission that includes waypoints should go through the
corridors and not just a couple waypoints." Then: "let's refer to this map
detail as the Authentic standard map detail" — and asked for the Syria map.

The generic router (routing.py) draws home > WP1 > IP > TARGET > home and is
right where no structure is published. Where one is — Nellis's corridors,
the Levant's airways, FIR boundary fixes, the roads the IAF is reported to
use, the Al-Tanf deconfliction zone — every routed flight plan is threaded:

    departure > transit corridor > ENTRY GATE (= WP1) > IP > TARGET
              > EXIT GATE > recovery > home

The names WP1 / IP / TARGET are kept on the three mission points so the
timing card, the timing coach, the DTC cartridge and the say/do checks all
keep working unchanged; corridor points carry the fix's short name.

THE DATA
--------
One file per map under data/corridors/<map>.json:

  fixes      name -> lat, lon, short (<= 8 chars for the kneeboard), kind
             (airport/navaid/fix/gate/peak/landmark), src, approx, and the
             published crossing restrictions cap_ft / floor_ft
  corridors  id, name, role (departure/transit/recovery), points, block_ft,
             width_nm, notes, src, and the chart's label placement
  gates      gate fix -> what lies beyond it
  clusters   a home CLUSTER is the set of fields that share departures and
             recoveries (Nellis; Israel's northern bases; Akrotiri;
             Incirlik; the Jordanian fields). center + local_nm define its
             terminal area; join_from_outside lets a field outside every
             cluster (Creech) join the nearest cluster's transits without
             its departures
  sectors    rules that put a TARGET into a sector by lat/lon
  plans      cluster -> sector -> low/high -> out corridors, gate_in,
             gate_out, back corridor
  chart      the picture: bounds, areas, lines (coast/borders), roads,
             places, panels (terminal-area insets) — corridor_chart.py

WHAT IS DOCUMENTED AND WHAT IS CURATED
--------------------------------------
Every fix and corridor carries its source. Where a point's published
position is a chart we could not transcribe, or a road is reported by name
rather than by fix, the fix is placed by geography and flagged approx:true;
the brief lists them and the chart marks them ~. That is the rule
nav_points.json and the Berlin corridors already follow.
"""
from __future__ import annotations

import math

from dcs import mapping
from dcs.mapping import LatLng

from . import chartstyle as cs
from . import routing
from .resolver import load_json

NM = 1852.0
FT = 0.3048

MAPS = ("nevada", "syria", "germany")
_DATA: dict = {}


def maps() -> tuple:
    return MAPS


def data(map_key: str = "nevada") -> dict:
    if map_key not in _DATA:
        _DATA[map_key] = load_json(f"corridors/{map_key}")
    return _DATA[map_key]


def has(map_key: str) -> bool:
    return map_key in MAPS


def fix(name: str, map_key: str = "nevada") -> dict:
    f = data(map_key)["fixes"].get(name)
    if f is None:
        raise KeyError(f"{map_key} corridor fix {name!r} is not in corridors/{map_key}.json")
    return f


def corridor(cid: str, map_key: str = "nevada") -> dict:
    for c in data(map_key)["corridors"]:
        if c["id"] == cid:
            return c
    raise KeyError(f"{map_key} corridor {cid!r} is not in corridors/{map_key}.json")


def _pt(name: str, terrain, map_key: str):
    f = fix(name, map_key)
    return mapping.Point.from_latlng(LatLng(f["lat"], f["lon"]), terrain)


def _nm_between(lat1, lon1, lat2, lon2) -> float:
    dlat = (lat1 - lat2) * 60.0
    dlon = (lon1 - lon2) * 60.0 * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot(dlat, dlon)


# --------------------------------------------------------------------------- #
# clusters and sectors
# --------------------------------------------------------------------------- #
def cluster_for_home(home_name: str, home_lat: float, home_lon: float, map_key: str):
    """(cluster_id, in_cluster). The home's own cluster when its field is
    listed; else — only where the nearest cluster allows join_from_outside —
    that cluster with in_cluster False; else (None, False)."""
    d = data(map_key)
    for cid, c in d["clusters"].items():
        if home_name in c.get("fields", []):
            return cid, True
    best, best_d = None, 1e9
    for cid, c in d["clusters"].items():
        if not c.get("join_from_outside"):
            continue
        dd = _nm_between(home_lat, home_lon, c["center"][0], c["center"][1])
        if dd < best_d:
            best, best_d = cid, dd
    return best, False


def _rule_true(when: str, lat: float, lon: float) -> bool:
    """Evaluate 'lat >= 37.02 and lon <= -114.95' without eval()."""
    for clause in when.split(" and "):
        var, op, num = clause.split()
        v = lat if var == "lat" else lon
        n = float(num)
        ok = {"<=": v <= n, ">=": v >= n, "<": v < n, ">": v > n}[op]
        if not ok:
            return False
    return True


def sector_for(lat: float, lon: float, map_key: str = "nevada", cluster: str | None = None) -> str:
    """The target's sector by the map's rules; 'local' inside the home
    cluster's terminal area; 'none' when no rule matches."""
    d = data(map_key)
    if cluster and cluster in d["clusters"]:
        c = d["clusters"][cluster]
        if _nm_between(lat, lon, c["center"][0], c["center"][1]) <= float(c.get("local_nm", 22)):
            return "local"
    for rule in d["sectors"]["rules"]:
        if _rule_true(rule["when"], lat, lon):
            return rule["sector"]
    return d["sectors"].get("default", "none")


def mode_for(era: str) -> str:
    """'high' when the era's transit altitude is FL190 or above, else 'low'."""
    t_alt_m = routing.ERA_PROFILE.get(era, routing.DEFAULT_PROFILE)[0]
    return "high" if t_alt_m / FT >= 19000 else "low"


def _clamp_alt_m(t_alt_m: float, block_ft) -> float:
    lo, hi = block_ft
    ft = min(max(t_alt_m / FT, lo), hi)
    return round(ft / 100.0) * 100 * FT


# --------------------------------------------------------------------------- #
# the plan
# --------------------------------------------------------------------------- #
def plan_route(home_pos, target_pos, era: str, rng, terrain, map_key: str,
               home_name: str | None = None):
    """Legs for routing.apply(), threaded through the map's corridors, or
    None — meaning "use the generic router": a map without corridors, no
    target, a home outside every cluster, a target in no sector or inside
    the terminal area, or a plan the data does not have."""
    if not has(map_key) or home_pos is None or target_pos is None:
        return None
    if home_pos.distance_to_point(target_pos) < 8000:
        return None
    d = data(map_key)
    if d.get("eras") and era not in d["eras"]:
        return None                   # the structure belongs to one era (Germany: the Cold War)
    hll = home_pos.latlng()
    cluster, in_cluster = cluster_for_home(home_name or "", hll.lat, hll.lng, map_key)
    if cluster is None:
        return None
    tll = target_pos.latlng()
    sector = sector_for(tll.lat, tll.lng, map_key, cluster)
    if sector in ("local", "none"):
        return None
    mode = mode_for(era)
    plans = d["plans"].get(cluster, {})
    ps = plans.get(sector)
    if not ps:
        return None
    p = ps.get(mode) or ps.get("low") or ps.get("any")
    if not p:
        return None
    t_alt, ip_alt, atk_alt, spd = routing.ERA_PROFILE.get(era, routing.DEFAULT_PROFILE)

    # The departures belong to the cluster's fields. A field joining from
    # outside (Creech on the west road) skips them and joins the transit at
    # its first point; nothing left to join -> generic route.
    out_ids = [c for c in p["out"] if in_cluster or corridor(c, map_key)["role"] != "departure"]
    if not out_ids:
        return None
    back = corridor(p["back"], map_key)
    back_pts = list(back["points"]) if in_cluster else []

    legs, used = [], []

    def add(name, fixname, alt_m, cid=None):
        pt = _pt(fixname, terrain, map_key)
        f = fix(fixname, map_key)
        if f.get("cap_ft"):
            alt_m = min(alt_m, f["cap_ft"] * FT)
        if f.get("floor_ft"):
            alt_m = max(alt_m, f["floor_ft"] * FT)
        if legs and legs[-1]["fix"] == fixname:
            if name in ("WP1", "EXIT"):
                legs[-1]["name"] = name
            return
        taken = {l["name"] for l in legs}
        if name in taken:
            k = 2
            while f"{name[:7]}{k}" in taken:
                k += 1
            name = f"{name[:7]}{k}"
        legs.append({"name": name, "fix": fixname, "point": pt, "alt": alt_m,
                     "speed": spd, "corridor": cid})

    for cid in out_ids:
        c = corridor(cid, map_key)
        used.append(cid)
        for fx in c["points"]:
            add(fix(fx, map_key)["short"], fx, _clamp_alt_m(t_alt, c["block_ft"]), cid)

    gate_in = p["gate_in"]
    add("WP1", gate_in, _clamp_alt_m(t_alt, corridor(out_ids[-1], map_key)["block_ft"]))
    gate_pt = legs[-1]["point"]

    axis = routing._bearing(gate_pt, target_pos)
    dist = gate_pt.distance_to_point(target_pos)
    side = 1 if rng.random() < 0.5 else -1
    ip = routing._offset(target_pos, min(16000, max(9000, dist * 0.25)),
                         (axis + 180 + side * 30) % 360)
    legs.append({"name": "IP", "fix": None, "point": ip, "alt": ip_alt,
                 "speed": spd, "corridor": None})
    legs.append({"name": "TARGET", "fix": None, "point": target_pos,
                 "alt": atk_alt, "speed": spd, "corridor": None})

    if in_cluster:
        used.append(back["id"])
    gate_out = p["gate_out"]
    add("EXIT", gate_out, _clamp_alt_m(t_alt, back["block_ft"]))
    for fx in back_pts:
        add(fix(fx, map_key)["short"], fx, _clamp_alt_m(t_alt, back["block_ft"]), back["id"])

    return {"map": map_key, "legs": legs, "sector": sector, "mode": mode,
            "corridors": used, "gate_in": gate_in, "gate_out": gate_out,
            "cluster": cluster, "from_nellis": in_cluster, "in_cluster": in_cluster}


# --------------------------------------------------------------------------- #
# paperwork
# --------------------------------------------------------------------------- #
def summary(plan: dict) -> str:
    mk = plan.get("map", "nevada")
    return " / ".join(corridor(c, mk)["name"] for c in plan["corridors"])


def approx_fixes(plan: dict) -> list:
    mk = plan.get("map", "nevada")
    out = []
    for leg in plan["legs"]:
        if leg["fix"] and fix(leg["fix"], mk).get("approx") and leg["fix"] not in out:
            out.append(leg["fix"])
    return out


def sector_label(plan: dict) -> str:
    """'north ranges' / 'the Bekaa and Lebanon' - sectors.labels in the data,
    else the sector's name."""
    labels = data(plan.get("map", "nevada")).get("sectors", {}).get("labels", {})
    return labels.get(plan["sector"], plan["sector"])


def md_line(plan: dict) -> str:
    """The one-line markdown summary for the brief: text.md_line in the data
    with {summary} {sector} {mode} {gate_in} {gate_out} filled in."""
    t = data(plan.get("map", "nevada")).get("text", {})
    fmt = t.get("md_line", "**{summary}** — {sector}, {mode} road. Range entry at **{gate_in}** (WP1), "
                "exit at **{gate_out}**. The flight plan is threaded through the published structure; "
                "nobody leaves the Bravo direct to the target.")
    return fmt.format(summary=summary(plan), sector=sector_label(plan), mode=plan["mode"],
                      gate_in=plan["gate_in"], gate_out=plan["gate_out"])


def brief_lines(plan: dict) -> list:
    """The corridor block for the in-game text and the PDF."""
    mk = plan.get("map", "nevada")
    d = data(mk)
    t = d.get("text", {})
    L = [f"== {t.get('brief_title', 'CORRIDORS - HOW YOU GET TO THE FIGHT')} ==",
         f"Sector: {plan['sector'].upper()}, {plan['mode']} road, from "
         f"{d['clusters'][plan['cluster']]['label']}."]
    L += t.get("brief_intro", [])
    L.append("")
    for cid in plan["corridors"]:
        c = corridor(cid, mk)
        lo, hi = c["block_ft"]
        L.append(f"{c['name'].upper()}  {' > '.join(fix(p, mk)['short'] for p in c['points'])}"
                 f"  {lo:,}-{hi:,} ft MSL  {c['width_nm']} nm wide")
        for n in c.get("notes", []):
            L.append(f"  {n}")
    gi, go = plan["gate_in"], plan["gate_out"]
    L += ["", f"{t.get('gate_in_label', 'ENTRY GATE')} (WP1): {gi} - {d['gates'].get(gi, '')}",
          f"{t.get('gate_out_label', 'EXIT GATE')}: {go} - {d['gates'].get(go, fix(go, mk).get('src', ''))}"]
    ap = approx_fixes(plan)
    if ap:
        L += ["", "Curated positions (placed by geography where the published figure is a",
              "chart or a road is reported by name; flagged on the F10 map): "
              + ", ".join(ap) + "."]
    L += t.get("brief_sources", ["Sources: see the corridor chart and the Sources page."])
    L += ["Historical coverage: route geometry, widths and blocks are planning reconstructions.",
          "Per-segment operational validity is unknown; a source date does not certify this mission date.",
          "See /api/historical-coverage/report for evidence, dates and remaining gaps."]
    return L


def known_issue_lines(plan: dict) -> list:
    mk = plan.get("map", "nevada")
    t = data(mk).get("text", {})
    out = list(t.get("known_issues", []))
    ap = approx_fixes(plan)
    if ap:
        out.append("Corridor fixes " + ", ".join(ap) + " are curated placements, "
                   "not surveyed positions - the brief marks them.")
    return out


# --------------------------------------------------------------------------- #
# the F10 picture
# --------------------------------------------------------------------------- #
def draw(m, plan: dict | None = None, map_key: str | None = None):
    """Reconstructed lanes with diamond gates on the shared reference layer."""
    mk = map_key or (plan or {}).get("map", "nevada")
    layer = m.drawings.get_layer_by_name("Common")
    terrain = m.terrain
    used = set(plan["corridors"]) if plan else set()
    from .airspace import _draw_poly
    from . import historical_symbols as symbols
    from .historical_coverage import element
    d = data(mk)
    for c in d["corridors"]:
        metadata = element(f"network/{mk}/{c['id']}")
        col, fill, wt, st = symbols.style('reconstructed_lane', c['id'] in used)
        half = c["width_nm"] * NM / 2.0
        pts = [_pt(p, terrain, mk) for p in c["points"]]
        if len(pts) == 1:
            layer.add_circle(pts[0], radius=half, color=col, fill=fill,
                             line_thickness=wt, line_style=st)
        for a, b in zip(pts, pts[1:]):
            _draw_poly(layer, cs.corridor_polygon(a, b, half), col, fill, wt, st)
        lo, hi = c["block_ft"]
        anchor = pts[len(pts) // 2]
        cs.label(layer, anchor, f"{c['name']}\n{lo // 1000}-{hi // 1000}k planning\n{symbols.label_tag(metadata)}", col,
                 size=12 if c["id"] in used else 10)
    gcol, gfill, gwt, gst = cs.spec("zone")
    for g in d["gates"]:
        pt = _pt(g, terrain, mk)
        symbols.diamond(layer, pt, radius=2.0 * NM, approximate=bool(fix(g,mk).get('approx')))
        tag = "~" if fix(g, mk).get("approx") else ""
        cs.label(layer, pt, f"GATE {g}{tag}", gcol, size=11)
    symbols.legend(m)
