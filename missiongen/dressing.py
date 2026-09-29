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
from .placement import AirfieldKeepOut, slot_key

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


def resolve_theme(era, side, map_preset=None, theme_key=None, warnings=None,
                  airport_name=None):
    """Pick the ramp theme: explicit choice > per-FIELD default > map default.

    Themes are era-gated by structure (a theme only exists under its era), so a
    WWII field can never draw a modern ramp no matter what the user selects.

    `<side>_field_themes` names the fields on a map that aren't the map's normal
    identity. Nevada needs it: Nellis is the Red Flag ramp — the only place a
    tanker line and an E-3 belong — while Groom Lake and Tonopah Test Range are
    black-project test sites that must not inherit a surge exercise ramp just
    because they share a map with Nellis. Setting the map-wide theme to
    `red_flag` put B-1Bs and a Sentry on the Groom Lake apron, which is the
    opposite of the point.

    An explicit user choice still wins everywhere: picking a theme in the
    Builder is a deliberate act and should not be quietly overridden per field.
    """
    themes = load_json("ramp_themes").get(era, {}).get(side, {})
    default_key = themes.get("default")
    per_field = ((map_preset or {}).get(f"{side}_field_themes") or {})
    key = (theme_key
           or (per_field.get(airport_name) if airport_name else None)
           or (map_preset or {}).get(f"{side}_theme")
           or default_key)
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
_LIVERY_RAW = None


def _livery_pack() -> dict:
    global _LIVERY_RAW
    if _LIVERY_RAW is None:
        try:
            _LIVERY_RAW = load_json("liveries")
        except Exception:
            _LIVERY_RAW = {}
    return _LIVERY_RAW


def livery_pack_verified() -> bool:
    """True once the pack has been read out of a real DCS install.

    scripts/dump_liveries.py --merge writes "_verified": true. Until then the
    ids are guesses and the engine leaves livery_id unset.
    """
    return bool(_livery_pack().get("_verified"))
_AIRFRAME_DIMS = None


def _airframe_dims():
    """Cached surveyed real bounding boxes keyed by DCS type id (ignores the
    underscore comment/source keys)."""
    global _AIRFRAME_DIMS
    if _AIRFRAME_DIMS is None:
        try:
            raw = load_json("airframe_dimensions")
            _AIRFRAME_DIMS = {k: v for k, v in raw.items()
                              if not k.startswith("_") and isinstance(v, dict)
                              and "span" in v and "length" in v}
        except Exception:
            _AIRFRAME_DIMS = {}
    return _AIRFRAME_DIMS


# --------------------------------------------------------------------------
# Which aircraft fit which stand
# --------------------------------------------------------------------------
# This used to be one hardcoded guess — a stand counted as "large" if
# `slot.large or (length >= 60 and width >= 55)`. Two problems, both of which
# showed up at Nellis:
#
#   1. NTTR flags NO slot as `large`. Nellis has 247 stands and the boolean is
#      False on every one, so the whole heavy pool depended on the 60x55
#      fallback — which exactly 6 stands passed. Creech and Groom Lake passed
#      zero. A map whose entire reason to exist is Red Flag could not park a
#      tanker.
#   2. The threshold is airframe-blind. It refuses a C-130 (29.8 x 40.4) from a
#      42 x 34 stand it fits in, and would happily offer a B-52 (49 x 56.4) a
#      60 x 55 stand it does not.
#
# pydcs ships the real box on every type (`width` IS wingspan, `length` is
# fuselage), so ask the aircraft instead of guessing. `_airframe_dims()` still
# wins where a surveyed box is more honest than pydcs's (the F-14's swept-wing
# value understates its span by half).
#
# TOLERANCE is deliberate and mode-dependent. Ramp dressing in `static` mode is
# inert scenery on an apron that continues past the painted box, so a modest
# overhang looks right and harms nothing — that is how a real KC-135 sits on a
# 40 m spot with its tail over the taxi lane. In `parked_ai` mode the aircraft
# is a live uncontrolled flight that DCS may taxi, so it must actually fit.
STAND_TOLERANCE = {"static": 1.25, "parked_ai": 1.0}


def airframe_box(unit_type):
    """(length, span) in metres for a pydcs type. Surveyed box wins."""
    override = _airframe_dims().get(getattr(unit_type, "id", None))
    if override:
        return float(override["length"]), float(override["span"])
    return (float(getattr(unit_type, "length", None) or 12.0),
            float(getattr(unit_type, "width", None) or 10.0))


# How much of a field's aircraft target is held back for heavies. "auto" is the
# shipped default and is deliberately modest: a fighter base should still read
# as a fighter base. "surge" is the Red Flag / exercise look — a visible tanker
# line — and is what Nevada wants when someone is building the mission that map
# exists for.
# (share of the field's aircraft target, floor in stands, ceiling in stands).
#
# The FLOOR is what makes this work on a big base: Nellis's auto target is 18
# aircraft and 12% of 18 is two stands — one heavy block, which is how you get a
# ramp with three B-1Bs and no tanker.
#
# The CEILING is what stops it running away in the other direction. A share
# alone, at 60% fill on Nellis's 233 stands, reserved every heavy-capable stand
# on the field and parked thirty heavies including ten B-1Bs. A heavy line is a
# feature of a ramp, not the ramp; sixteen is already a very busy Red Flag.
#
# Never more than SHARE_CEILING of the target, or the fighters disappear.
RAMP_HEAVIES = {"none":  (0.00,  0,  0),
                "light": (0.06,  2,  4),
                "auto":  (0.12,  4,  8),
                "surge": (0.28, 10, 16)}
SHARE_CEILING = 0.55


def _fits_ref(ref, slot, tol):
    try:
        return stand_fits(resolve(ref), slot, tol)
    except Exception:
        return False


def stand_fits(unit_type, slot, tol=1.0):
    """Does this airframe fit this parking stand?

    `slot.large` is honored as a hard yes because a terrain author who sets it
    is telling us something we cannot measure. Everything else is the box.
    """
    if getattr(slot, "large", False):
        return True
    length, span = airframe_box(unit_type)
    return (length <= slot.length * tol) and (span <= slot.width * tol)

_SQUADRONS = None

# The most statics one squadron may put on a ramp. Past this, a NEW squadron is
# picked — the point of the block system is that a ramp reads as several units
# sharing a field, and a run of twelve identical jets in one paint scheme reads
# as a copy-paste error instead. Six is also about a real flight-line row.
SQUADRON_MAX = 6


def _squadron_id(type_id, livery, tag):
    """What counts as "one squadron" for the display cap.

    A named entry from `squadrons.json` is obviously one. For a generic theme
    block there is no name, so the identity is the thing a pilot actually sees:
    the airframe plus its paint. Two F-16 blocks in different squadron liveries
    are two squadrons on the ramp and are allowed; two in the SAME livery are
    one squadron parked twice, which is what this stops.
    """
    return tag or f"{type_id}|{livery or '-'}"


def _squadron_plan(map_key, airport_name, country_name):
    """Real squadron identities for this base (squadrons.json), as a mutable
    plan list. Entries with a 'nation' only apply when the base is owned by
    that nation (alignment can flip ownership), so the wrong side never parks
    someone else's squadron. Empty list = fall back to theme blocks."""
    global _SQUADRONS
    if _SQUADRONS is None:
        try:
            _SQUADRONS = {k: v for k, v in load_json("squadrons").items()
                          if not k.startswith("_")}
        except Exception:
            _SQUADRONS = {}
    entries = (_SQUADRONS.get(map_key) or {}).get(airport_name) or []
    return [dict(e) for e in entries
            if not e.get("nation") or e["nation"] == country_name]


_AGGR_RE = None


def _is_aggressor(livery_id):
    global _AGGR_RE
    if _AGGR_RE is None:
        import re
        _AGGR_RE = re.compile(r"aggr|agrs|adversary|aggressor", re.IGNORECASE)
    return bool(_AGGR_RE.search(livery_id or ""))


def _pending_key(type_id):
    """Roster key for a pending airframe's DCS type id ('F-14BU' -> 'F_14B_U')."""
    try:
        for key, cfg in load_json("pending_aircraft").items():
            if isinstance(cfg, dict) and cfg.get("provisional_id") == type_id:
                return key
    except Exception:
        pass
    return None


def player_livery(type_id, era, country_name=None, style="squadron"):
    """The skin on YOUR jet, or None for the DCS stock default.

    The player's aircraft has never had a livery path at all — `_pick_livery`
    only ever ran on parked ramp statics — so your jet has always worn whatever
    DCS picks first. This is that path.

    Two rules make it safe to have asked for a *specific* squadron:

      * `types.<type>.player.<era>` in liveries.json names the squadron this
        airframe should wear in that period, so a marking is never applied to a
        decade it doesn't belong to. VF-11 Red Rippers flew the F-14B from 1996
        to 2005 — correct for a modern mission, an anachronism on a 1975 one.
      * Nothing is written while the pack is unverified, exactly as for statics.
        A livery folder name is a string on someone's disk and cannot be checked
        from a server; guessing produced v1.46.4's blank aircraft. Run
        scripts/dump_liveries.py against a real install and this starts working.
    """
    if style == "clean" or not livery_pack_verified():
        return None
    # Callers pass the pydcs `.id` ("F-14BU"); the pack is keyed attribute-style
    # ("F_14B_U") to match static_catalog. Normalise, same as _pick_livery.
    types = _livery_pack().get("types") or {}
    entry = (types.get(type_id)
             or types.get(str(type_id).replace("-", "_"))
             # A pending airframe's DCS id and its roster key are not related by
             # punctuation: the F-14B(U) flies as "F-14BU" and is keyed
             # "F_14B_U" everywhere else in the project, so normalising the
             # hyphen gets "F_14BU" and misses. Ask the pending table.
             or types.get(_pending_key(type_id)) or {})
    per_era = entry.get("player") or {}
    pick = per_era.get(era) or per_era.get("*")
    if pick:
        return pick[0] if isinstance(pick, list) else pick
    # No player preference authored: fall back to the nation-correct default.
    for key in (country_name, "default"):
        if key and entry.get(key):
            return entry[key][0]
    return None


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
    # The pack ships with "_verified": false because its ids are hand-authored
    # GUESSES at DCS livery folder names, and nothing server-side can check them
    # — pydcs's liveries package is a scanner over a DCS install, not bundled
    # data. Writing a guessed livery_id is not harmless: DCS does not reliably
    # fall back to the stock skin for a name it doesn't know, so a wrong string
    # produces a wrong (or blank) aircraft rather than the default one. Until
    # scripts/dump_liveries.py --merge overwrites the pack with strings read out
    # of a real install (which sets "_verified": true), write nothing and let
    # DCS choose. Shipping a guess into someone's mission is worse than
    # shipping nothing.
    if not livery_pack_verified():
        return None
    global _LIVERY_PACK
    if _LIVERY_PACK is None:
        _LIVERY_PACK = _livery_pack().get("types", {})
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
                if s.unit_id is None and slot_key(s) not in used]
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
            if slot_key(s) not in taken and s.unit_id is None:
                taken.add(slot_key(s))
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
                   livery_style="squadron", map_key=None, ramp_heavies="auto"):
    """Fill an airfield with era/faction-correct static aircraft + ground equipment.

    Placement discipline: aircraft go on surveyed parking stands only (always
    safe); everything free-placed (GSE, infrastructure) is validated against
    the runway keep-out corridors so movement areas stay clear.

    theme: ramp theme dict from ramp_themes.json (weighted [ref, weight] lists)
           deciding WHO parks here; falls back to eras.json flat lists.
    fill: 0-100 percent of free stands to fill; None derives from density.
    include_*: user-selected object classes (aircraft / GSE / infrastructure).
    ramp_heavies: how much of the ramp is held for tankers/AWACS/transports —
           see RAMP_HEAVIES. Without a reservation the fighter pool takes the
           big stands and no tanker ever parks.
    """
    used = used_slot_names or set()
    heavy_share, heavy_floor, heavy_cap = RAMP_HEAVIES.get(
        ramp_heavies, RAMP_HEAVIES["auto"])
    keepout = AirfieldKeepOut(airport, map_key=map_key)
    placed = 0

    # --- occupancy registry (collision fix, v1.10.x) ---------------------
    # Everything this field places records a (x, y, radius) footprint, and
    # every later placement must clear it. Before this, each object class
    # only checked the runway corridors — so a GSE truck could spawn INSIDE
    # a B-52 (28 m half-span vs a 4-9 m stand-based offset) and the infra
    # cluster could land on a dispersal row. pydcs exposes real per-type
    # dimensions (width=span, length), so footprints are exact.
    _occ = []

    def _occ_register(pos, radius):
        _occ.append((pos.x, pos.y, radius))

    def _occ_clear(pos, radius):
        return all(math.hypot(pos.x - ox, pos.y - oy) > radius + orad
                   for ox, oy, orad in _occ)

    def _half_extent(unit_type):
        """Circumscribing half-extent of an aircraft footprint (m). Prefers a
        surveyed real bounding box where pydcs understates the envelope (e.g. the
        F-14's real 20.34 m span vs pydcs' 10.15 m swept value)."""
        override = _airframe_dims().get(getattr(unit_type, "id", None))
        if override:
            return max(override["span"], override["length"]) / 2.0
        w = getattr(unit_type, "width", None) or 10.0   # width = wingspan
        l = getattr(unit_type, "length", None) or 12.0
        return max(w, l) / 2.0

    # Stands already claimed by OTHER systems (player flight, ambient AI) hold
    # aircraft we didn't place and can't size — register them from the stand's
    # own dimensions so our statics/GSE/infra keep clear of them too.
    for s in airport.parking_slots:
        if s.unit_id is not None:
            _occ_register(s.position, max(s.length, s.width) / 2.0 * 0.5)

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
    # ADJACENCY ORDER, not shuffle: crossroad indexes run along the ramp rows,
    # so filling stands in slot_key order produces contiguous same-type rows —
    # the "a squadron lives here" look — instead of a shuffled yard sale.
    free = sorted([s for s in airport.parking_slots
                   if s.unit_id is None and slot_key(s) not in used and _can_fill(s)],
                  key=slot_key)
    # best-effort per-slot facing (static mode only; AI mode lets DCS decide)
    slot_hdgs = keepout.slot_headings() if (free and aircraft_mode == "static") else {}

    # --- placement body shared by theme-fill and custom-mix paths --------
    def _place(slot, unit_type, livery, tag=None):
        """Place one aircraft static (or parked_ai) + its GSE. Returns placed?"""
        if slot.unit_id is not None:      # claimed by player/ambient meanwhile
            return False
        # UNIQUE stand id — slot_name is not unique on some maps (Syria "02" ×6);
        # naming groups by it makes DCS reject the duplicate-named units and
        # silently drops aircraft. slot_key() (crossroad_idx) is unique.
        skey = slot_key(slot)
        # COLLISION GATE: a heavy on one stand can overhang its neighbors (a
        # B-52 spans 56 m). 0.6× the circumscribing half-extent allows the
        # tight wingtip-to-wingtip spacing of a real ramp while rejecting
        # gross overlap (one aircraft inside another).
        ac_half = _half_extent(unit_type)
        if not _occ_clear(slot.position, ac_half * 0.6):
            return False                   # neighbor's footprint reaches here
        if aircraft_mode == "parked_ai":
            # EXACT facing: uncontrolled flight at the real slot (DCS aligns it to
            # the painted line). Cost: live AI unit (FPS, map contact, pop-in).
            try:
                grp = m.flight_group_from_airport(
                    country, f"RAMP {airport.name} {skey} {unit_type.id}",
                    unit_type, airport, start_type=StartType.Cold, group_size=1,
                    parking_slots=[slot])
            except Exception:
                return False               # type can't park here — skip, no crash
            grp.uncontrolled = True
            gse_ref_hdg = keepout.away_side_bearing(slot.position)
        else:
            # STATIC. Facing priority: exact per-spot measured heading (by slot
            # name) > field-wide measured heading > per-slot geometric guess
            # (keyed by the unique slot_key so twins don't inherit each other's
            # facing) > runway-axis fallback.
            if slot.slot_name in slot_hdg_overrides:
                base_hdg = slot_hdg_overrides[slot.slot_name]
            elif field_default_hdg is not None:
                base_hdg = field_default_hdg
            else:
                base_hdg = slot_hdgs.get(skey, keepout.runway_axis_heading())
            heading = (base_hdg + rng.uniform(-3, 3)) % 360.0
            grp = m.static_group(
                country, f"ST {airport.name} {skey} {unit_type.id}"
                         + (f" · {tag}" if tag else ""),
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
        _occ_register(slot.position, ac_half * 0.6)
        # BB-2: GSE truck beside the aircraft — offset from the AIRCRAFT
        # FOOTPRINT, not the stand. The old stand-based 4-9 m put the truck
        # INSIDE any airframe bigger than a fighter (B-52 half-span is 28 m).
        # Clear the wingtip by 3-6 m, and verify against the registry so it
        # can't land inside a neighbor either.
        if include_gse and rng.random() < 0.5:
            off = ac_half + rng.uniform(3.0, 6.0)
            gse_pos = _offset(slot.position, off, gse_ref_hdg)
            if keepout.clear(gse_pos, avoid_stands=False) and _occ_clear(gse_pos, 3.0):
                gse_type = fuel_truck if rng.random() < 0.5 else rng.choice(utility)
                m.static_group(country, f"GSE {airport.name} {skey}",
                               _type=gse_type, position=gse_pos,
                               heading=rng.uniform(0, 360))
                _occ_register(gse_pos, 3.0)
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
        # SQUADRON BLOCKS: real ramps are rows of same-type, same-livery jets
        # (a squadron lives here), not per-stand dice rolls. Fill contiguous
        # runs: pick a type + ONE livery per block, place 4-8 (fighters),
        # 2-3 (heavies), 2-4 (helos) in adjacent stands, then start a new
        # block. Real squadron identities (squadrons.json) fill first.
        squad_plan = _squadron_plan(map_key, airport.name,
                                    getattr(country, "name", None))

        # Heavy types already given a block at this field. The reservation is
        # small — 4 stands at a default Nellis — and a heavy block is 2-3 deep,
        # so an unguarded weighted draw hands the entire heavy ramp to one type.
        # Measured: 1.8 B-1Bs per mission and 0.6 KC-135s, from a pool where the
        # two carry the SAME weight. Real ramps mix; drain the pool once before
        # repeating anything.
        heavy_used = set()
        # How many statics each squadron has already put on THIS ramp. Counted
        # at PLACEMENT, not at block creation — the first version capped the
        # block and then let the same identity be drawn again for the next one,
        # which measured at 22 aircraft from one squadron at Templin. Scoped per
        # field: one squadron appearing at two bases is fine and often true; one
        # squadron parked twice on the same flight line is not.
        squad_count = {}
        # The cap is a VARIETY rule, not a capacity rule — and an explicit fill
        # percentage outranks it. At auto/density targets (18-28 aircraft) six
        # per squadron never binds; at "fill=100" on Nellis's 233 stands it
        # binds hard: the ramp's ceiling becomes (distinct identities × 6),
        # which measured 79 of 233 — a user asked for a full ramp and got a
        # third. With the livery pack unverified it is worse still, because
        # every type collapses to ONE identity (no paint variety). So when the
        # user's explicit target still has budget and every squadron is full,
        # the cap escalates by another SQUADRON_MAX — a second wave of the same
        # units, which is also what a real surge ramp does (a deployed squadron
        # brings more than six jets; they park in more than one row). Blocks
        # stay 2-8 deep, so the rows still read as blocks, not a wall of one
        # paint. The auto path never escalates: variety keeps winning there.
        squad_cap = SQUADRON_MAX

        def _room(sid):
            return squad_cap - squad_count.get(sid, 0)

        def _draw(cls, pool):
            """Pick a squadron with room left. Returns (ref, unit, livery, sid)
            or None when every identity in the pool is full.

            An airframe gets three attempts before it is dropped from the draw,
            because the livery is chosen after the type: a type whose 1st Wing
            paint is full may still have room in another scheme. Dropping on the
            first full draw would collapse the ramp to one squadron per type
            even when the livery pack offers several.
            """
            avail, tries = list(pool), {}
            while avail:
                ref, theme_liv = _weighted(rng, avail)
                ut = resolve(ref)
                liv = theme_liv or _pick_livery(
                    ut.id, getattr(country, "name", None), rng, livery_style)
                sid = _squadron_id(ut.id, liv, None)
                if _room(sid) > 0:
                    return ref, ut, liv, sid
                tries[ref] = tries.get(ref, 0) + 1
                if tries[ref] >= 3:
                    avail = [p for p in avail if p[0] != ref]
            return None

        def _next_block(cls, pool):
            if cls == "large":
                fresh = [p for p in pool if p[0] not in heavy_used]
                if fresh:
                    pool = fresh
                else:
                    heavy_used.clear()
            while cls == "plane" and squad_plan:
                e = squad_plan.pop(0)
                ut = resolve(e["ref"])
                liv = e.get("livery") or _pick_livery(
                    ut.id, getattr(country, "name", None), rng, livery_style)
                sid = _squadron_id(ut.id, liv, e.get("name"))
                room = _room(sid)
                if room <= 0:            # already on the ramp; next squadron
                    continue
                # `count` is what the data ASKS for; SQUADRON_MAX is what the
                # ramp will show. Clamped here rather than trusted, so a data
                # edit cannot quietly reintroduce a twelve-ship block.
                n = max(1, min(room, int(e.get("count", SQUADRON_MAX))))
                return [ut, liv, e.get("name"), n, sid]
            if not pool:
                return None
            drawn = _draw(cls, pool)
            if drawn is None:
                # Every squadron this theme can field is at the current cap on
                # this ramp. At an AUTO target, stopping is the correct outcome
                # of the variety rule — an emptier ramp beats a copy-paste one.
                # At an EXPLICIT fill the caller escalates squad_cap and asks
                # again (see the slot loop): the user's percentage wins.
                return None
            ref, ut, liv, sid = drawn
            if cls == "large":
                heavy_used.add(ref)      # the pool is keyed by REF, not type id
            size = (rng.randint(2, 4) if cls == "helo"
                    else rng.randint(2, 3) if cls == "large"
                    else rng.randint(4, SQUADRON_MAX))
            return [ut, liv, None, min(size, _room(sid)), sid]

        # ---- RESERVE STANDS FOR THE HEAVIES --------------------------------
        # Heavy-capable stands used to be shared with the fighter pool
        # (`large_w + plane_w`), and fighters won them twice over: the pool
        # weights run about 11 fighter to 8 heavy, AND a fighter block is 4-8
        # aircraft deep against 2-3 for a heavy, so a single F-16 block could
        # swallow every big stand on the base. Measured at Nellis that produced
        # 0-1 heavy aircraft across the WHOLE map and, over eight seeds, not one
        # parked tanker or AWACS on the ramp of the base Red Flag is named for.
        #
        # So heavies get first call on a share of the stands they fit. The share
        # is `heavies` (see RAMP_HEAVIES); fighters still get everything else,
        # including any heavy-capable stand above the reservation.
        tol = STAND_TOLERANCE.get(aircraft_mode, 1.0)
        heavy_types = []
        for ref, _w, *_rest in [tuple(p) for p in large_w]:
            try:
                heavy_types.append(resolve(ref))
            except Exception:
                pass

        def _heavy_capable(slot):
            return slot.airplanes and any(stand_fits(t, slot, tol)
                                          for t in heavy_types)

        capable = [s for s in free if _heavy_capable(s)] if heavy_types else []
        # The floor has to scale with the field, or a 48-stand test site reserves
        # the same heavy line as Nellis's 247. AUTO_CAP flattens `target` to 18
        # for every field regardless of size, so `target` cannot carry that —
        # the field's own count of heavy-capable stands can.
        floor = min(heavy_floor, -(-len(capable) * 35 // 100)) if capable else 0
        reserve = min(max(int(round(target * heavy_share)), floor),
                      heavy_cap) if heavy_share else 0
        # Never reserve so much of a small field that the fighters vanish, and
        # never more stands than the field actually has room for.
        reserve = min(len(capable), reserve, int(target * SHARE_CEILING))
        # Prefer the ROOMIEST stands: put the heavy line where the widest
        # airframes can go, so a C-17 is not blocked by a C-130 that would have
        # fit anywhere. Ties keep slot order, so the line still reads as a row.
        capable = sorted(capable, key=lambda s: -(s.length * s.width))
        reserved = {slot_key(s) for s in capable[:reserve]}

        blocks = {}                    # stand class -> [type, livery, tag, left]
        # RESERVED STANDS GO FIRST. `free` is in adjacency order so the rows read
        # as squadron blocks, but the fill stops at `target` — and the reserved
        # stands are wherever the roomy ones happen to be, often late in that
        # order. Filling strictly in adjacency order meant the loop ran out of
        # budget before it ever reached them, so `surge` placed exactly as many
        # heavies as `auto`. Serve the reservation, then dress the rest in order.
        order = ([s for s in free if slot_key(s) in reserved]
                 + [s for s in free if slot_key(s) not in reserved])
        for slot in order:
            if placed >= target:
                break
            # classify the stand (helo lists can be empty, e.g. WWII)
            if slot.helicopter and not slot.airplanes:
                cls, pool = "helo", helo_w
            elif slot_key(slot) in reserved:
                # Held for the heavies. Only offer types that actually fit —
                # a 42x34 stand takes a C-130 and not a B-52, and the old
                # one-size threshold could not tell them apart.
                fits = [p for p in large_w
                        if _fits_ref(p[0], slot, tol)]
                cls, pool = "large", (fits or large_w)
            elif slot.airplanes:
                small = [p for p in plane_w if p[0] not in large_set]
                cls, pool = "plane", (small or plane_w)
            else:
                cls, pool = "helo", helo_w
            if not pool and not (cls == "plane" and squad_plan):
                continue
            b = blocks.get(cls)
            if not b or b[3] <= 0:
                b = _next_block(cls, pool)
                if b is None and fill is not None and placed < target:
                    # EXPLICIT fill outranks the variety cap (line one of this
                    # branch: "explicit user percentage WINS"). Every squadron
                    # is full at the current cap, the user's target is not met:
                    # open another wave and redraw. Bounded — one escalation
                    # per slot at most, and each wave adds room for every
                    # identity in the pool.
                    squad_cap += SQUADRON_MAX
                    b = _next_block(cls, pool)
                if b is None:
                    continue
                blocks[cls] = b
            # A block started on a roomy stand can run onto a tighter one. Drop
            # the block rather than clip a B-52 into a fighter spot.
            if cls == "large" and not stand_fits(b[0], slot, tol):
                blocks[cls] = None
                continue
            if _place(slot, b[0], b[1], tag=b[2]):
                placed += 1
                b[3] -= 1
                # Count against the squadron HERE, on the airplane that
                # actually reached the ramp — a block can be abandoned midway
                # (a heavy that will not fit the next stand), and charging the
                # squadron for aircraft it never parked would shrink the ramp.
                squad_count[b[4]] = squad_count.get(b[4], 0) + 1

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
                # clear of the movement area AND everything already placed —
                # the anchor is pushed off the ramp, but dispersal stands with
                # parked aircraft can sit out here too.
                if not keepout.clear(pos) or not _occ_clear(pos, 12.0):
                    continue                      # belt and suspenders
                m.static_group(country, f"INF {airport.name} {i}", _type=obj,
                               position=pos, heading=(row + 90) % 360)
                _occ_register(pos, 12.0)

    return placed
