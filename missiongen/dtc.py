"""F-14B(U) Data Transfer Cartridge (DTM/DTC) — content model + RIO setup card.

Design spec: project doc `claude/f14bu-dtc-design.md`.

The Heatblur F-14B(U) loads a Data Transfer Module (DTM) in the jet to
pre-populate the CDNU / TID / PTID. Almost everything worth putting in it,
Mission Starter already computes — the cartridge is a second rendering of our
mission data into the back-seater's cockpit.

Governing rule (north star): *we set the stage, you write the play.* This module
only ever emits BATTLESPACE REFERENCE data — bullseye, nav fix points, threat
areas, comm/TACAN plan, support anchors. It never emits the player's ordered
route, target run, or loadout.

Two halves:
  * build_cartridge(...) → a deterministic, schema-independent content model, and
    cartridge_card_md(...) → a printable "punch this into the DTM" RIO setup card.
    Both ship NOW (no reverse-engineering needed) and are useful on Day 0.
  * emit_dtm(...) → writes the cartridge into the .miz as a real DTM. GATED on the
    undocumented DTM byte schema (isolate it with scripts/dtc_inspect.py on a
    plain-vs-cartridge .miz pair). Deliberately a stub until then — we do NOT
    fabricate a format.
"""
from __future__ import annotations

# --- point / group budget (Heatblur DTM plot-line limits) ------------------
# Confirm exact values against the manual / in-game before shipping Tier-2 plot
# lines; kept as named constants so there is one place to correct them.
PLOT_MAX_GROUPS = 4
PLOT_MAX_PTS_PER_GROUP = 9
PLOT_MAX_TOTAL_PTS = 20
FIX_POINT_MAX = 9              # CDNU fix points we surface (FP/IP/HB/DP/HA/ST + spares)
THREAT_AREA_MAX = 3           # threat rings we render as plot-line groups

# Recipe aircraft keys that are the F-14B(U). Kept as a set + substring fallback
# so it survives however the pending module gets promoted (e.g. F_14B_U).
_BU_KEYS = {"F_14B_U", "F_14BU", "F-14B_U"}


def is_bu(aircraft_key: str) -> bool:
    """True if the recipe aircraft is the F-14B(U) (the RIO/DTS jet)."""
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
        left = _dp(points[:idx + 1], epsilon)
        right = _dp(points[idx:], epsilon)
        return left[:-1] + right
    return [points[0], points[-1]]


def simplify(points, max_points):
    """Reduce a polyline/polygon (list of (x, y)) to <= max_points, deterministically.

    Douglas–Peucker with an epsilon raised until the budget is met. Returns the
    input unchanged if already within budget. Never returns fewer than 2 points.
    """
    pts = [(float(x), float(y)) for x, y in points]
    if len(pts) <= max_points or max_points < 2:
        return pts if max_points >= len(pts) else pts[:max_points]
    # bracket epsilon by the geometry's own scale, climb until it fits
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
    """(lat, lng, 'DMS string') for a pydcs Point, or None if unconvertible."""
    try:
        ll = point.latlng()
        return round(ll.lat, 6), round(ll.lng, 6), ll.format_dms()
    except Exception:
        return None


def _fix(name, point):
    ll = _ll(point)
    if ll is None:
        return None
    return {"name": name, "lat": ll[0], "lng": ll[1], "dms": ll[2]}


# --- cartridge content model ----------------------------------------------
def build_cartridge(gfx: dict, kb_ctx: dict, recipe) -> dict:
    """Assemble the deterministic DTC content model from what we already built.

    Pure data, sorted by stable keys so the same recipe+seed yields the same
    cartridge (determinism contract). Reads only reference geometry.
    """
    cart = {"bullseye": None, "homeplate": None, "fix_points": [],
            "threat_areas": [], "support": [], "comms": [], "notes": []}

    # Bullseye — every BRAA call keys off it. Highest-value single field.
    bull = gfx.get("bullseye")
    if bull is not None:
        cart["bullseye"] = _fix("BULLSEYE", bull)

    # Homeplate — first friendly field (or the boat), as a fix point + TACAN.
    own = kb_ctx.get("own_fields") or []
    if own:
        hp = _fix(kb_ctx.get("home_name") or getattr(own[0], "name", "HOME"),
                  own[0].position)
        if hp:
            cart["homeplate"] = hp

    # Fix points from named nav reference points (BB-22). Deterministic order.
    for name, pt in sorted(kb_ctx.get("nav_points", []), key=lambda np: str(np[0])):
        f = _fix(name, pt)
        if f:
            cart["fix_points"].append(f)
        if len(cart["fix_points"]) >= FIX_POINT_MAX:
            break

    # Threat areas (Tier-2) — doctrinal SAM WEZ rings as center + radius, and a
    # budgeted plot-line ring. Sorted by radius desc so the worst threats win the
    # limited plot-line budget; the rest still list as reference points.
    threats = sorted(gfx.get("threats", []), key=lambda t: (-float(t[1]), str(t[2])))
    for pos, wez_m, label in threats[:THREAT_AREA_MAX]:
        ll = _ll(pos)
        if ll is None:
            continue
        ring = _threat_ring(pos, wez_m)
        cart["threat_areas"].append({
            "label": str(label), "lat": ll[0], "lng": ll[1], "dms": ll[2],
            "radius_nm": round(float(wez_m) / 1852.0, 1),
            "ring_points": ring})
    if len(threats) > THREAT_AREA_MAX:
        cart["notes"].append(
            f"{len(threats) - THREAT_AREA_MAX} further threat ring(s) omitted "
            f"from plot lines (budget {THREAT_AREA_MAX}); see the mission map.")

    # Support anchors — tanker / AWACS / carrier as standalone reference fixes
    # (NOT a route). Each gfx entry leads with a Point.
    for key, tag in (("tanker", "TANKER"), ("awacs", "AWACS"), ("carrier", "CV")):
        ent = gfx.get(key)
        if not ent:
            continue
        f = _fix(f"{tag} {ent[-1]}" if isinstance(ent[-1], str) else tag, ent[0])
        if f:
            cart["support"].append(f)

    # Comm / TACAN plan — mirror the generated card exactly.
    comms = kb_ctx.get("comms")
    if comms is not None:
        for agency, callsign, freq, tacan, _notes in getattr(comms, "entries", []):
            cart["comms"].append({
                "agency": agency, "callsign": callsign, "freq": freq,
                "tacan": tacan, "chan": comms.channels.get(agency)})

    return cart


def _threat_ring(center, radius_m, sides=8):
    """An octagon ring around a threat, decimated to the per-group point budget."""
    import math
    try:
        cx, cy = center.x, center.y
    except AttributeError:
        return []
    pts = [(cx + radius_m * math.cos(2 * math.pi * i / sides),
            cy + radius_m * math.sin(2 * math.pi * i / sides))
           for i in range(sides)]
    return simplify(pts, PLOT_MAX_PTS_PER_GROUP)


# --- RIO setup card (ships now) --------------------------------------------
def cartridge_card_md(cart: dict, title: str = "F-14B(U) DTC Setup Card") -> str:
    """Printable 'punch this into the DTM' reference card. Everything on it is
    reference data the RIO would otherwise transcribe by hand from the map."""
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
            L.append(f"- **{t['label']}** — center {t['dms']}, radius {t['radius_nm']} NM "
                     f"({len(t['ring_points'])}-pt ring)")
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

    L += ["---", "*Generated by DCS Mission Starter. Same recipe + seed reproduces "
          "this exact cartridge.*"]
    return "\n".join(L)


# --- .miz DTM emitter (SCHEMA-GATED — do not fabricate) --------------------
class DTMSchemaUnknown(NotImplementedError):
    pass


def emit_dtm(mission, cart: dict) -> None:
    """Write `cart` into `mission` as a real F-14B(U) DTM.

    GATED: the DTM byte schema is undocumented and must be reverse-engineered
    from a plain-vs-cartridge .miz pair via scripts/dtc_inspect.py. Until that
    lands, this raises rather than guessing a format that DCS would reject.
    When implemented, inject at save time via the vendored-unmodified path
    (keep vendor/dcs/ pristine per LGPL) and keep the write deterministic.
    """
    raise DTMSchemaUnknown(
        "DTM byte schema not yet isolated. Provide a plain-vs-cartridge .miz "
        "pair and run scripts/dtc_inspect.py (DIFF mode). Until then, ship the "
        "DTC setup card (cartridge_card_md) — same data, transcribed by hand.")
