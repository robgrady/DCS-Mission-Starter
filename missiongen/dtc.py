"""F-14B(U) Data Transfer Cartridge (DTM/DTC) — content model, RIO setup card,
and real `.miz` injection.

Design spec: project doc `claude/f14bu-dtc-design.md`.

Schema (reverse-engineered from a plain-vs-cartridge `.miz` pair, 2026-07-21):
DCS stores the F-14B(U) cartridge as a JSON **sidecar file** inside the `.miz`
zip at `DTC/<name>.dtc`, matched to the jet by its internal `"type": "F-14BU"`
(the mission-tree group `["DTC"]` stays an empty `{}` marker). The JSON is
`{"data": {CMDS, JDAM, NAV[12], TIS, cartridge_name, name, type}, name, type}`.

We only ever populate **NAV** with battlespace REFERENCE data (north star: we set
the stage, you write the play):
  * NAV[i].additional_points  -> named reference points  {elev,lat,lon,name,x,y}
  * NAV[i].lines              -> plot lines  {closed, points:[{elev,lat,lon,x,y}]}
  * NAV[i].waypoints          -> LEFT EMPTY (never the player's route)
CMDS/JDAM/TIS come from the scrubbed `dtc_template.json` skeleton at defaults —
JDAM targets empty (no weapons), countermeasure programs at module defaults.
"""
from __future__ import annotations
import json
import zipfile
from pathlib import Path

from .resolver import load_json

# --- point / group budget (Heatblur DTM plot-line limits) ------------------
PLOT_MAX_GROUPS = 4
PLOT_MAX_PTS_PER_GROUP = 9
PLOT_MAX_TOTAL_PTS = 20
FIX_POINT_MAX = 9
THREAT_AREA_MAX = 3

_BU_KEYS = {"F_14B_U", "F_14BU", "F-14B_U"}
_BU_TYPE_ID = "F-14BU"          # verified DCS type id
_CARTRIDGE_NAME = "F-14B(U) DTC_1"       # ME's cartridge name for one B(U)
_DTC_MEMBER = f"DTC/{_CARTRIDGE_NAME}.dtc"   # sidecar path the ME uses


def install_unit_dtc():
    """Runtime-patch pydcs so a player/client unit carrying a `_dtc_cartridge`
    attribute serialises the unit-level DTC link DCS actually reads:

        ["DTC"] = { ["Cartridges"] = { [1] = { ["name"]=..., ["default"]=true } } }

    Verified against an ME-made cartridge `.miz` (2026-07-22): the sidecar file is
    matched to the jet by THIS unit reference, not by type alone. Without it the
    `DTC/*.dtc` file is an orphan and the DTM page loads empty. Vendor stays
    pristine; this wraps FlyingUnit.dict at import (idempotent)."""
    from dcs.flyingunit import FlyingUnit
    if getattr(FlyingUnit.dict, "_dtc_patched", False):
        return
    _orig = FlyingUnit.dict

    def dict_with_dtc(self):
        d = _orig(self)
        name = getattr(self, "_dtc_cartridge", None)
        if name:
            d["DTC"] = {"Cartridges": [{"name": name, "default": True}]}
        return d

    dict_with_dtc._dtc_patched = True
    FlyingUnit.dict = dict_with_dtc


def tag_player_cartridge(m, name: str = _CARTRIDGE_NAME) -> int:
    """Attach the cartridge reference to every player/client F-14B(U) unit in the
    built mission, so `m.save()` writes the unit-level DTC link that pairs with the
    injected `DTC/*.dtc` sidecar. Returns the number of units tagged."""
    from dcs.unit import Skill
    n = 0
    for coal in m.coalition.values():
        for country in coal.countries.values():
            for pg in getattr(country, "plane_group", []):
                for u in pg.units:
                    tid = getattr(getattr(u, "unit_type", None), "id", None) \
                        or getattr(u, "type", None)
                    if tid == _BU_TYPE_ID and getattr(u, "skill", None) in (
                            Skill.Player, Skill.Client):
                        u._dtc_cartridge = name
                        n += 1
    return n


def is_bu(aircraft_key: str) -> bool:
    if not aircraft_key:
        return False
    k = str(aircraft_key)
    return k in _BU_KEYS or "14B_U" in k or "14BU" in k


# --- geometry: Douglas–Peucker decimation to a point budget ----------------
def _perp_dist(pt, a, b):
    (px, py), (ax, ay), (bx, by) = pt, a, b
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    cx, cy = ax + t * dx, ay + t * dy
    return ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5


def _dp(points, epsilon):
    if len(points) < 3:
        return points
    dmax, idx = 0.0, 0
    for i in range(1, len(points) - 1):
        d = _perp_dist(points[i], points[0], points[-1])
        if d > dmax:
            dmax, idx = d, i
    if dmax > epsilon:
        return _dp(points[:idx + 1], epsilon)[:-1] + _dp(points[idx:], epsilon)
    return [points[0], points[-1]]


def simplify(points, max_points):
    """Reduce a polyline/polygon (list of (x, y)) to <= max_points, deterministically."""
    pts = [(float(x), float(y)) for x, y in points]
    if len(pts) <= max_points or max_points < 2:
        return pts if max_points >= len(pts) else pts[:max_points]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    span = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
    eps = span / 1000.0
    out = pts
    for _ in range(40):
        out = _dp(pts, eps)
        if len(out) <= max_points:
            break
        eps *= 1.6
    return out[:max_points]


# --- coordinate helpers ----------------------------------------------------
def _ll(point):
    try:
        ll = point.latlng()
        return round(ll.lat, 9), round(ll.lng, 9), ll.format_dms()
    except Exception:
        return None


def _pt_entry(name, point):
    """Full reference-point entry carrying BOTH lat/lon (card) and x/y (DTM)."""
    ll = _ll(point)
    if ll is None:
        return None
    return {"name": name, "lat": ll[0], "lng": ll[1], "dms": ll[2],
            "x": round(point.x, 3), "y": round(point.y, 3)}


# --- cartridge content model ----------------------------------------------
def build_cartridge(gfx: dict, kb_ctx: dict, recipe, terrain=None) -> dict:
    """Deterministic DTC content model assembled from mission data we already
    computed. Reference geometry only. Stable ordering for determinism."""
    cart = {"bullseye": None, "homeplate": None, "fix_points": [],
            "threat_areas": [], "support": [], "comms": [], "notes": []}

    bull = gfx.get("bullseye")
    if bull is not None:
        cart["bullseye"] = _pt_entry("BULLSEYE", bull)

    own = kb_ctx.get("own_fields") or []
    if own:
        cart["homeplate"] = _pt_entry(kb_ctx.get("home_name")
                                      or getattr(own[0], "name", "HOME"),
                                      own[0].position)

    for name, pt in sorted(kb_ctx.get("nav_points", []), key=lambda np: str(np[0])):
        e = _pt_entry(name, pt)
        if e:
            cart["fix_points"].append(e)
        if len(cart["fix_points"]) >= FIX_POINT_MAX:
            break

    threats = sorted(gfx.get("threats", []), key=lambda t: (-float(t[1]), str(t[2])))
    for pos, wez_m, label in threats[:THREAT_AREA_MAX]:
        c = _pt_entry(str(label), pos)
        if c is None:
            continue
        c["radius_nm"] = round(float(wez_m) / 1852.0, 1)
        c["ring"] = _threat_ring(pos, wez_m, terrain)
        cart["threat_areas"].append(c)
    if len(threats) > THREAT_AREA_MAX:
        cart["notes"].append(
            f"{len(threats) - THREAT_AREA_MAX} further threat ring(s) omitted "
            f"from plot lines (budget {THREAT_AREA_MAX}); see the mission map.")

    for key, tag in (("tanker", "TANKER"), ("awacs", "AWACS"), ("carrier", "CV")):
        ent = gfx.get(key)
        if not ent:
            continue
        e = _pt_entry(f"{tag} {ent[-1]}" if isinstance(ent[-1], str) else tag, ent[0])
        if e:
            cart["support"].append(e)

    comms = kb_ctx.get("comms")
    if comms is not None:
        for agency, callsign, freq, tacan, _n in getattr(comms, "entries", []):
            cart["comms"].append({"agency": agency, "callsign": callsign,
                                  "freq": freq, "tacan": tacan,
                                  "chan": comms.channels.get(agency)})
    return cart


def _threat_ring(center, radius_m, terrain, sides=8):
    """Octagon ring around a threat as full {x,y,lat,lon} points, decimated to
    the per-group budget. Needs terrain to convert the offset x/y to lat/lon."""
    import math
    try:
        cx, cy = center.x, center.y
    except AttributeError:
        return []
    raw = [(cx + radius_m * math.cos(2 * math.pi * i / sides),
            cy + radius_m * math.sin(2 * math.pi * i / sides)) for i in range(sides)]
    raw = simplify(raw, PLOT_MAX_PTS_PER_GROUP)
    out = []
    for x, y in raw:
        lat = lon = None
        if terrain is not None:
            try:
                import dcs.mapping as _m
                ll = _m.Point(x, y, terrain).latlng()
                lat, lon = round(ll.lat, 9), round(ll.lng, 9)
            except Exception:
                pass
        out.append({"x": round(x, 3), "y": round(y, 3), "lat": lat, "lon": lon})
    return out


# --- DTM JSON (the real sidecar payload) -----------------------------------
def _dtm_point(entry, elev=0):
    return {"elev": elev, "lat": entry["lat"], "lon": entry["lng"],
            "x": entry["x"], "y": entry["y"]}


def _dtm_ring_point(p, elev=0):
    return {"elev": elev, "lat": p["lat"], "lon": p["lon"], "x": p["x"], "y": p["y"]}


def build_dtm(cart: dict) -> dict:
    """Fill the scrubbed template's NAV[0] with our reference geometry and return
    the full DTM JSON object (ready to serialize as the `.dtc` sidecar)."""
    dtm = load_json("dtc_template")
    nav = dtm["data"]["NAV"]

    add_pts = []
    if cart.get("bullseye"):
        add_pts.append(dict(_dtm_point(cart["bullseye"]), name="BULLSEYE"))
    if cart.get("homeplate"):
        add_pts.append(dict(_dtm_point(cart["homeplate"]), name=cart["homeplate"]["name"]))
    for i, f in enumerate(cart.get("fix_points", []), 1):
        add_pts.append(dict(_dtm_point(f), name=f["name"][:24] or f"FP{i}"))
    for t in cart.get("threat_areas", []):
        add_pts.append(dict(_dtm_point(t), name=str(t["name"])[:24]))
    for s in cart.get("support", []):
        add_pts.append(dict(_dtm_point(s), name=str(s["name"])[:24]))

    lines = []
    for t in cart.get("threat_areas", []):
        ring = [r for r in t.get("ring", []) if r.get("lat") is not None]
        if len(ring) >= 3:
            lines.append({"closed": True, "points": [_dtm_ring_point(r) for r in ring]})

    nav[0]["name"] = "STARTER REF"
    nav[0]["additional_points"] = add_pts
    nav[0]["lines"] = lines
    nav[0]["waypoints"] = []          # never the player's route
    nav[0]["route_as_line"] = False
    return dtm


def emit_dtm(miz_path: str, cart: dict) -> int:
    """Inject the F-14B(U) cartridge into an already-saved `.miz` as the
    `DTC/*.dtc` JSON sidecar. Deterministic (sorted keys, fixed zip date).
    Returns the number of reference features written. No-op-safe: raises on I/O
    but never fabricates schema — the format is the verified one above."""
    dtm = build_dtm(cart)
    payload = json.dumps(dtm, indent=1, sort_keys=True).encode("utf-8")
    # append the sidecar member with a fixed timestamp so bytes stay deterministic
    info = zipfile.ZipInfo(_DTC_MEMBER, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    with zipfile.ZipFile(miz_path, "a") as z:
        if _DTC_MEMBER in z.namelist():
            return 0
        z.writestr(info, payload)
    nav0 = dtm["data"]["NAV"][0]
    return len(nav0["additional_points"]) + len(nav0["lines"])


# --- RIO setup card (unchanged content, still shipped) ---------------------
def cartridge_card_md(cart: dict, title: str = "F-14B(U) DTC Setup Card") -> str:
    L = [f"# {title}", "",
         "*Battlespace reference for the DTM (Data Transfer Module). Nav, threat "
         "and comm picture only — your flight plan and weapons stay yours.*", ""]
    if cart.get("bullseye"):
        b = cart["bullseye"]
        L += ["## Bullseye", f"- **{b['dms']}**  ({b['lat']:.4f}, {b['lng']:.4f})", ""]
    if cart.get("homeplate"):
        h = cart["homeplate"]
        L += ["## Homeplate", f"- **{h['name']}** — {h['dms']}", ""]
    if cart.get("fix_points"):
        L += ["## Fix points (CDNU)"]
        for i, f in enumerate(cart["fix_points"], 1):
            L.append(f"- **FP{i} {f['name']}** — {f['dms']}")
        L.append("")
    if cart.get("threat_areas"):
        L += ["## Threat areas (PTID plot lines)"]
        for t in cart["threat_areas"]:
            L.append(f"- **{t['name']}** — center {t['dms']}, radius {t['radius_nm']} NM "
                     f"({len([r for r in t.get('ring', []) if r.get('lat') is not None])}-pt ring)")
        L.append("")
    if cart.get("support"):
        L += ["## Support anchors (reference only)"]
        for s in cart["support"]:
            L.append(f"- **{s['name']}** — {s['dms']}")
        L.append("")
    if cart.get("comms"):
        L += ["## Comm / TACAN presets", "", "| CH | Agency | Callsign | Freq | TACAN |",
              "|---|---|---|---|---|"]
        for c in cart["comms"]:
            ch = c["chan"] if c["chan"] is not None else "-"
            L.append(f"| {ch} | {c['agency']} | {c['callsign']} | {c['freq']} | {c['tacan']} |")
        L.append("")
    if cart.get("notes"):
        L += ["## Notes"] + [f"- {n}" for n in cart["notes"]] + [""]
    L += ["---", "*Generated by DCS Sortie Starter. Same recipe + seed reproduces "
          "this exact cartridge.*"]
    return "\n".join(L)
