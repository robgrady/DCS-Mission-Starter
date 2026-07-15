"""BB-1..3: airfield dressing — parked aircraft on real parking spots, ground support
equipment near occupied stands, infrastructure statics near the ramp.

Parked AIRCRAFT are placed as UNCONTROLLED flights at the terrain's own parking
slots — NOT as static objects. This is the only way to get them oriented
correctly: the DCS terrain stores each slot's parking heading in its binary and
applies it when the sim spawns an aircraft there; that heading is NOT exposed to
static placement (pydcs ParkingSlot has no heading field), so a static must guess
its facing and can also clip a building's collision mesh. An uncontrolled flight
lets DCS own both position and heading — nose-out, ready to taxi — exactly like
the AI flights that already spawn correctly. Ground equipment stays static."""
import math
import random
from dcs import mapping
from dcs.mission import StartType
import dcs.statics as statics

from .resolver import resolve, load_json
from .placement import AirfieldKeepOut

DENSITY_FILL = {"sparse": 0.25, "normal": 0.45, "busy": 0.70}
# Two ways to place parked aircraft — a genuine tradeoff (pydcs does NOT expose
# the terrain's true parking heading, so there is no free lunch):
#   "static"    — static objects. Instant render, cheap, inert, no radar
#                 contacts, no spawn-in pop-in. Facing is a best-effort per-slot
#                 guess (rows via geometry, nose toward the runway).
#   "parked_ai" — uncontrolled flights at real slots. DCS owns facing (exact,
#                 nose-out) and placement, but they cost FPS, appear as map
#                 contacts, and STREAM IN over the first seconds ("pop-in").
# Static is the default — the right tool for inert ramp clutter. The auto/
# density cap is per field and depends on mode; explicit fill % overrides it.
AUTO_CAP_PER_FIELD = {
    "static":    {"sparse": 10, "normal": 18, "busy": 28},
    "parked_ai": {"sparse": 5,  "normal": 8,  "busy": 14},
}


def resolve_theme(era, side, map_preset=None, theme_key=None, warnings=None):
    """Pick the ramp theme for a side: explicit choice > map preset > era default.

    Themes are era-gated by structure (a theme only exists under its era), so a
    WWII field can never draw a modern ramp no matter what the user selects."""
    themes = load_json("ramp_themes").get(era, {}).get(side, {})
    default_key = themes.get("default")
    key = theme_key or (map_preset or {}).get(f"{side}_theme") or default_key
    if key not in themes or key == "default":
        if theme_key and warnings is not None:
            warnings.append(f"ramp theme '{theme_key}' does not exist in the "
                            f"{era} era - using '{default_key}'")
        key = default_key
    return key, themes.get(key)


def _weighted(rng, pairs):
    """Pick from [[ref, weight], ...] or [[ref, weight, [liveries]], ...].
    Returns (ref, livery_or_None). Unknown livery ids are harmless: DCS
    falls back to the default skin."""
    idx = rng.choices(range(len(pairs)), weights=[p[1] for p in pairs], k=1)[0]
    p = pairs[idx]
    livery = rng.choice(p[2]) if len(p) > 2 and p[2] else None
    return p[0], livery


_STATIC_CATALOG = None
_LIVERY_PACK = None


_AGGR_RE = None


def _is_aggressor(livery_id):
    global _AGGR_RE
    if _AGGR_RE is None:
        import re
        _AGGR_RE = re.compile(r"aggr|agrs|adversary|aggressor", re.IGNORECASE)
    return bool(_AGGR_RE.search(livery_id or ""))


def _pick_livery(type_id, country_name, rng, style="squadron"):
    """Livery for a parked static, or None (DCS stock default).

    Curated pack (data/liveries.json), keyed types.<type_id>.<COUNTRY> with a
    'default' fallback. Fixes wrong-nation skins on statics that otherwise ship
    no livery_id (e.g. a USAF F-4E drawing a USMC scheme). Unknown ids are
    harmless — DCS falls back to the stock default — so a stale string is safe.

    style (global "livery style" control):
      squadron  — nation-correct mix (default)
      aggressors— adversary schemes where they exist, else fall back to squadron
      clean     — no override; DCS stock default skin
      random    — any scheme in the type's pack (all nations), for visual variety
    """
    if style == "clean":
        return None
    global _LIVERY_PACK
    if _LIVERY_PACK is None:
        try:
            _LIVERY_PACK = load_json("liveries").get("types", {})
        except Exception:
            _LIVERY_PACK = {}
    # callers pass the pydcs .id ("F-4E"); pack is keyed attribute-style
    # ("F_4E") to match static_catalog — normalize the hyphen/underscore.
    entry = _LIVERY_PACK.get(type_id) or _LIVERY_PACK.get(str(type_id).replace("-", "_"))
    if not entry:
        return None
    nation = entry.get(country_name) or entry.get("default")
    if style == "random":
        allv = sorted({v for k, vals in entry.items() if not k.startswith("_")
                       for v in (vals or [])})
        return rng.choice(allv) if allv else (rng.choice(nation) if nation else None)
    if style == "aggressors":
        allv = [v for k, vals in entry.items() if not k.startswith("_")
                for v in (vals or [])]
        aggr = sorted({v for v in allv if _is_aggressor(v)})
        if aggr:
            return rng.choice(aggr)
        # no aggressor scheme for this type -> fall through to squadron
    if not nation:
        return None
    return rng.choice(nation)


def _catalog_size(type_id):
    """fighter | large | helo for a catalog type; None if unknown."""
    global _STATIC_CATALOG
    if _STATIC_CATALOG is None:
        try:
            _STATIC_CATALOG = load_json("static_catalog").get("types", {})
        except Exception:
            _STATIC_CATALOG = {}
    t = _STATIC_CATALOG.get(type_id)
    return t.get("size") if t else None


def _resolve_type(type_id):
    from dcs import planes, helicopters
    for mod in (planes, helicopters):
        t = getattr(mod, type_id, None)
        if t is not None:
            return t
    raise ValueError(f"aircraft type '{type_id}' not found")


def _place_mix(airport, mix, place_fn, rng, used):
    """Ramp Composer: place an explicit {type_id: count} composition.

    Round-robin over the requested types so a field with fewer stands than the
    total truncates PROPORTIONALLY (2 of everything, not all of the first type).
    Stand-aware: helos prefer helo pads (fall back to airplane stands), heavies
    need a large/roomy stand, fighters take any airplane stand.
    """
    items = []
    for tid, cnt in mix.items():
        try:
            c = int(cnt)
        except (TypeError, ValueError):
            continue
        if c <= 0:
            continue
        try:
            ut = _resolve_type(tid)
        except Exception:
            continue
        size = _catalog_size(tid) or ("helo" if getattr(ut, "helicopter", False) else "fighter")
        items.append((ut, c, size))
    if not items:
        return 0

    free_all = [s for s in airport.parking_slots
                if s.unit_id is None and s.slot_name not in used]
    rng.shuffle(free_all)
    taken = set()

    def pick(size):
        if size == "helo":
            order = ([s for s in free_all if s.helicopter]
                     + [s for s in free_all if s.airplanes])
        elif size == "large":
            order = [s for s in free_all
                     if s.large or (s.airplanes and s.length >= 60 and s.width >= 55)]
        else:
            order = [s for s in free_all if s.airplanes]
        for s in order:
            if s.slot_name not in taken and s.unit_id is None:
                taken.add(s.slot_name)
                return s
        return None

    placed = 0
    maxc = max(c for _, c, _ in items)
    for i in range(maxc):
        for ut, c, size in items:
            if i < c:
                s = pick(size)
                if s is not None and place_fn(s, ut, None):
                    placed += 1
    return placed


def _parse_field_heading(field_heading):
    """Normalize a parking_headings.json field value into (default, slots).

    Accepts a bare number (whole-field dominant heading), a dict with optional
    "default" and "slots" (per-slot-name headings), or None. Returns
    (default_or_None, slots_dict). Per-slot values win over the default.
    """
    if field_heading is None:
        return None, {}
    if isinstance(field_heading, (int, float)):
        return float(field_heading), {}
    if isinstance(field_heading, dict):
        d = field_heading.get("default")
        d = float(d) if isinstance(d, (int, float)) else None
        slots = {k: float(v) for k, v in (field_heading.get("slots") or {}).items()
                 if isinstance(v, (int, float))}
        return d, slots
    return None, {}


def _offset(pos, meters, bearing_deg):
    b = math.radians(bearing_deg)
    return mapping.Point(pos.x + meters * math.cos(b),
                         pos.y + meters * math.sin(b), pos._terrain)


def dress_airfield(m, airport, country, era_side_cfg, density, rng: random.Random,
                   used_slot_names=None, theme=None, fill=None,
                   include_aircraft=True, include_gse=True, include_infra=True,
                   aircraft_mode="static", field_heading=None, mix=None,
                   livery_style="squadron"):
    """Fill an airfield with era/faction-correct static aircraft + ground equipment.

    Placement discipline: aircraft go on surveyed parking stands only (always
    safe); everything free-placed (GSE, infrastructure) is validated against
    the runway keep-out corridors so movement areas stay clear.

    theme: ramp theme dict from ramp_themes.json (weighted [ref, weight] lists)
           deciding WHO parks here; falls back to eras.json flat lists.
    fill: 0-100 percent of free stands to fill; None derives from density.
    include_*: user-selected object classes (aircraft / GSE / infrastructure).
    """
    used = used_slot_names or set()
    keepout = AirfieldKeepOut(airport)
    placed = 0

    # measured painted-line facing (parking_headings.json). Accept either
    #   number                -> one dominant heading for the whole field, OR
    #   {"default": n,          -> field default + exact per-spot overrides
    #    "slots": {"D15": 219,     keyed by the slot's stable name
    #              "A28": 41}}
    # Applies to AIRCRAFT statics only (GSE/infra keep their own placement).
    field_default_hdg, slot_hdg_overrides = _parse_field_heading(field_heading)

    if theme:
        plane_w = theme["planes"]
        large_w = theme["large"]
        helo_w = theme["helos"]
    else:  # legacy flat lists, weight 1
        plane_w = [[r, 1] for r in era_side_cfg["parked_planes"]]
        large_w = [[r, 1] for r in era_side_cfg["parked_large"]]
        helo_w = [[r, 1] for r in era_side_cfg["parked_helos"]]
    large_set = {p[0] for p in large_w}
    fuel_truck = resolve(era_side_cfg["fuel_truck"])
    utility = [resolve(r) for r in era_side_cfg["utility_trucks"]]

    # ELIGIBLE stands only: the fill %% must mean "this share of the aircraft
    # spots actually get a static" — a helipad on a WWII field (no helos in
    # the era list) can never be filled, so it must not dilute the math
    def _can_fill(s):
        if s.airplanes:
            return bool(plane_w or large_w)
        return bool(helo_w)          # helo-only pad
    free = [s for s in airport.parking_slots
            if s.unit_id is None and s.slot_name not in used and _can_fill(s)]
    rng.shuffle(free)
    # best-effort per-slot facing (static mode only; AI mode lets DCS decide)
    slot_hdgs = keepout.slot_headings() if (free and aircraft_mode == "static") else {}

    # --- placement body shared by theme-fill and custom-mix paths --------
    def _place(slot, unit_type, livery):
        """Place one aircraft static (or parked_ai) + its GSE. Returns placed?"""
        if slot.unit_id is not None:      # claimed by player/ambient meanwhile
            return False
        if aircraft_mode == "parked_ai":
            # EXACT facing: uncontrolled flight at the real slot (DCS aligns it to
            # the painted line). Cost: live AI unit (FPS, map contact, pop-in).
            try:
                grp = m.flight_group_from_airport(
                    country, f"RAMP {airport.name} {slot.slot_name} {unit_type.id}",
                    unit_type, airport, start_type=StartType.Cold, group_size=1,
                    parking_slots=[slot])
            except Exception:
                return False               # type can't park here — skip, no crash
            grp.uncontrolled = True
            gse_ref_hdg = keepout.away_side_bearing(slot.position)
        else:
            # STATIC. Facing priority: exact per-spot measured heading (by slot
            # name) > field-wide measured heading > per-slot geometric guess >
            # runway-axis fallback.
            if slot.slot_name in slot_hdg_overrides:
                base_hdg = slot_hdg_overrides[slot.slot_name]
            elif field_default_hdg is not None:
                base_hdg = field_default_hdg
            else:
                base_hdg = slot_hdgs.get(slot.slot_name,
                                         keepout.runway_axis_heading())
            heading = (base_hdg + rng.uniform(-3, 3)) % 360.0
            grp = m.static_group(
                country, f"ST {airport.name} {slot.slot_name} {unit_type.id}",
                _type=unit_type, position=slot.position, heading=heading)
            gse_ref_hdg = heading + rng.uniform(60, 120)
        # Explicit theme/mix livery wins; otherwise steer to a nation-correct
        # skin from the curated pack (fixes wrong-service defaults like a USAF
        # F-4E showing a USMC scheme). country.name = "USA"/"Russia"/"Israel"...
        if not livery:
            livery = _pick_livery(unit_type.id, getattr(country, "name", None),
                                  rng, livery_style)
        if livery:
            grp.units[0].livery_id = livery
        # BB-2: GSE truck on the aircraft's OWN pad — offset scaled to the stand
        # half-width (4-9 m), so it never spills into the taxilane or onto a
        # sunshade canopy the way a fixed 12-16 m offset did on small stands.
        if include_gse and rng.random() < 0.5:
            half = min(slot.length, slot.width) / 2.0
            off = max(4.0, min(0.6 * half, 9.0)) * rng.uniform(0.85, 1.0)
            gse_pos = _offset(slot.position, off, gse_ref_hdg)
            if keepout.clear(gse_pos, avoid_stands=False):
                gse_type = fuel_truck if rng.random() < 0.5 else rng.choice(utility)
                m.static_group(country, f"GSE {airport.name} {slot.slot_name}",
                               _type=gse_type, position=gse_pos,
                               heading=rng.uniform(0, 360))
        return True

    if mix and include_aircraft:
        # CUSTOM MIX (Ramp Composer): place exactly the requested types/counts.
        # fill%% is ignored — the mix IS the population. Liveries come from the
        # curated nation pack (see _place: livery None -> _pick_livery).
        placed += _place_mix(airport, mix, _place, rng, used)
    elif include_aircraft:
        if fill is not None:
            # EXPLICIT user percentage WINS — no cap (75% means 75% of stands).
            target = round(len(free) * max(0, min(100, fill)) / 100.0)
        else:
            target = min(int(len(free) * DENSITY_FILL[density]),
                         AUTO_CAP_PER_FIELD[aircraft_mode][density])
        for slot in free:
            if placed >= target:
                break
            # pick a type that fits the stand (helo lists can be empty, e.g. WWII)
            if slot.helicopter and not slot.airplanes:
                if not helo_w:
                    continue
                ref, livery = _weighted(rng, helo_w)
            elif slot.large or (slot.airplanes and slot.length >= 60 and slot.width >= 55):
                ref, livery = _weighted(rng, large_w + plane_w)
            elif slot.airplanes:
                small = [p for p in plane_w if p[0] not in large_set]
                ref, livery = _weighted(rng, small or plane_w)
            else:
                if not helo_w:
                    continue
                ref, livery = _weighted(rng, helo_w)
            if _place(slot, resolve(ref), livery):
                placed += 1

    # BB-3: infrastructure cluster near the ramp. The ramp sits BESIDE the
    # runway, so a random bearing from its centroid used to land the cluster
    # mid-runway. Now: push the anchor perpendicular to the runway axis,
    # DEEPER into the ramp side (away from the runway), then validate — the
    # cluster row runs parallel to the runway so it can never cross it.
    if free and include_infra:
        cx = sum(s.position.x for s in free) / len(free)
        cy = sum(s.position.y for s in free) / len(free)
        centroid = mapping.Point(cx, cy, airport.position._terrain)
        away = keepout.away_side_bearing(centroid)
        anchor = None
        for push in (300, 450, 600):
            cand = _offset(centroid, push, away + rng.uniform(-20, 20))
            if keepout.clear(cand, margin=60):
                anchor = cand
                break
        if anchor is None:
            anchor = keepout.find_clear(centroid, 300, 700, rng, margin=60,
                                        prefer_bearing=away)
        if anchor is not None:
            row = keepout.runway_axis_heading()   # row parallels the runway
            infra = [
                (statics.Fortification.Fuel_tank, 0),
                (statics.Fortification.Fuel_tank, 18),
                (statics.Fortification.Tent01, 60),
                (statics.Fortification.Tent03, 85),
                (statics.Fortification.Barracks_2, 130),
                (statics.Fortification.Comms_tower_M, 190),
            ]
            for i, (obj, dist) in enumerate(infra):
                pos = _offset(anchor, dist, row)
                if not keepout.clear(pos):
                    continue                      # belt and suspenders
                m.static_group(country, f"INF {airport.name} {i}", _type=obj,
                               position=pos, heading=(row + 90) % 360)

    return placed
