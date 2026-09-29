"""Threat Dial (v1.6.0): user control over how MANY threats spawn and what LEVEL.

Two orthogonal knobs on the recipe:

- threat_intensity (1-5): COUNT. How many extra area SAM sites and enemy CAP
  flights spawn on top of the base per-airfield air defense. Each level draws a
  RANDOM count from a band off the mission seed, so re-rolls feel different.
      1 Minimal · 2 Light · 3 Moderate (default) · 4 Heavy · 5 Maximum
- threat_tier ("auto"|"light"|"heavy"|"mixed"|"guns"): LEVEL. Which systems.
      auto  = the era's standard doctrine (back-compat with pre-dial missions)
      light = older/shorter-range (SA-2/SA-3 · MiG-21/23) — trainer-friendly
      heavy = modern/long-range   (SA-10/SA-11 · Su-27/MiG-31)
      mixed = both pools, rolled per site/flight ("surprise me")
      guns  = ZERO SAM sites anywhere; the belt is AAA clusters instead
              (S-60/KS-19/ZU-23 · Vulcan/M45). The Rolling Thunder picture:
              you can fly over it high, but you have to come DOWN into it to
              hit anything. Enemy CAP uses the light pool (gun-era fighters).

Everything is era-gated: a WWII "heavy" tier still can't field an SA-10 — the
pools simply don't contain anachronisms. Selection is seeded, so a recipe+seed
always regenerates the same threat picture.
"""
import math
import random
from dcs import mapping
from dcs.unit import Skill

from .kits import SAM_KITS
from .resolver import resolve
from .dressing import _offset
from . import loadouts as _loadouts
from dcs import task as _task

# --- LEVEL: era- and side-gated system pools -------------------------------
# SAM kit keys per era/side/tier. "auto" is intentionally the era's historical
# mix so default missions are unchanged in character. Empty list = fall back to
# the era_cfg["sam_kits"] the caller already has (e.g. WWII has none).
TIER_SAMS = {
    "wwii": {
        "red":  {"light": [], "heavy": [], "auto": []},
        "blue": {"light": [], "heavy": [], "auto": []},
    },
    "coldwar": {
        "red":  {"light": ["sa2", "sa3"], "heavy": ["sa6"],
                 "auto": ["sa2", "sa3", "sa6"]},
        "blue": {"light": ["hawk"], "heavy": ["hawk"], "auto": ["hawk"]},
    },
    "modern": {
        "red":  {"light": ["sa3", "sa6"], "heavy": ["sa10", "sa11"],
                 "auto": ["sa11", "sa6"]},
        "blue": {"light": ["hawk"], "heavy": ["patriot"],
                 "auto": ["patriot", "hawk"]},
    },
    # GWOT: empty on BOTH sides, at every tier, on purpose. An insurgency has
    # no integrated air defense and the coalition needs no umbrella against an
    # enemy with no aircraft. The threat in this era is entirely in TIER_AAA —
    # guns and MANPADS, low and everywhere, which is a different flying problem
    # from a SAM ring, not a smaller one. `sam_kits_for` falls back to the
    # era's own (also empty) list, so nothing here silently reverts.
    "gwot": {
        "red":  {"light": [], "heavy": [], "auto": []},
        "blue": {"light": [], "heavy": [], "auto": []},
    },
}

# AAA gun pools for the "guns" tier (vehicles.AirDefence refs, era/side-gated —
# same anachronism discipline as everything else: no Vulcan in WWII, no radar
# SAM anywhere in this tier). Each area site is a CLUSTER of these, not one gun.
TIER_AAA = {
    "wwii": {
        "red":  ["vehicles.AirDefence.Flak38", "vehicles.AirDefence.Flak36",
                 "vehicles.AirDefence.Flak37"],
        "blue": ["vehicles.AirDefence.Bofors40", "vehicles.AirDefence.M45_Quadmount",
                 "vehicles.AirDefence.M1_37mm"],
    },
    "coldwar": {
        "red":  ["vehicles.AirDefence.ZU_23_Emplacement",
                 "vehicles.AirDefence.S_60_Type59_Artillery",
                 "vehicles.AirDefence.KS_19", "vehicles.AirDefence.ZSU_57_2"],
        "blue": ["vehicles.AirDefence.Vulcan", "vehicles.AirDefence.M45_Quadmount",
                 "vehicles.AirDefence.M1_37mm", "vehicles.AirDefence.Bofors40"],
    },
    "modern": {
        "red":  ["vehicles.AirDefence.ZU_23_Emplacement",
                 "vehicles.AirDefence.ZSU_23_4_Shilka",
                 "vehicles.AirDefence.S_60_Type59_Artillery"],
        "blue": ["vehicles.AirDefence.Vulcan", "vehicles.AirDefence.Gepard"],
    },
    # GWOT red is the insurgent gun line: truck-mounted and emplaced ZU-23,
    # with captured Shilkas where a regular army's stocks were overrun. pydcs
    # ships dedicated `_Insurgent` variants of these, which is the correct
    # model rather than dressing a regular AAA battery in a different flag.
    "gwot": {
        "red":  ["vehicles.AirDefence.Ural_375_ZU_23_Insurgent",
                 "vehicles.AirDefence.ZU_23_Insurgent",
                 "vehicles.AirDefence.ZU_23_Closed_Insurgent",
                 "vehicles.AirDefence.ZSU_23_4_Shilka"],
        "blue": ["vehicles.AirDefence.Vulcan", "vehicles.AirDefence.Gepard"],
    },
}

# CAP aircraft (pydcs plane class names) per era/side/tier.
TIER_CAP = {
    "wwii": {
        "red":  {"light": ["Bf_109K_4"], "heavy": ["FW_190D9", "FW_190A8"],
                 "auto": ["Bf_109K_4", "FW_190A8"]},
        "blue": {"light": ["P_51D"], "heavy": ["P_47D_30", "P_51D"],
                 "auto": ["P_51D", "SpitfireLFMkIX"]},
    },
    "coldwar": {
        "red":  {"light": ["MiG_21Bis"], "heavy": ["MiG_23MLD"],
                 "auto": ["MiG_21Bis", "MiG_23MLD"]},
        "blue": {"light": ["F_5E_3"], "heavy": ["F_4E"],
                 "auto": ["F_4E", "F_5E_3"]},
    },
    "modern": {
        "red":  {"light": ["MiG_29A", "MiG_23MLD"],
                 "heavy": ["Su_27", "MiG_31"], "auto": ["MiG_29S", "Su_27"]},
        "blue": {"light": ["F_16C_50"], "heavy": ["F_15C"],
                 "auto": ["F_15C", "F_16C_50"]},
    },
    # THE DEFINING FACT OF THIS ERA: red has no aircraft. Not obsolete ones,
    # not few — none. The insurgency and ISIS never contested the air, and a
    # product that quietly spawned a MiG-29 to fill the "enemy CAP" slot would
    # be teaching the wrong war.
    #
    # `add_enemy_cap` and `add_bfm_adversary` both return empty on an empty
    # pool, and `builder` warns rather than failing silently, so choosing a
    # threat intensity still means something — it scales the GUN line.
    "gwot": {
        "red":  {"light": [], "heavy": [], "auto": []},
        "blue": {"light": ["F_16C_50"], "heavy": ["F_15C"],
                 "auto": ["F_15C", "F_16C_50"]},
    },
}

# --- COUNT: intensity -> (min,max) bands + engagement skill -----------------
INTENSITY = {
    1: {"label": "Minimal", "extra_sams": (0, 0), "cap_flights": (0, 0),
        "skill": Skill.Good},
    2: {"label": "Light", "extra_sams": (0, 1), "cap_flights": (0, 1),
        "skill": Skill.Good},
    3: {"label": "Moderate", "extra_sams": (1, 2), "cap_flights": (1, 1),
        "skill": Skill.High},
    4: {"label": "Heavy", "extra_sams": (2, 3), "cap_flights": (1, 2),
        "skill": Skill.High},
    5: {"label": "Maximum", "extra_sams": (3, 5), "cap_flights": (2, 3),
        "skill": Skill.Excellent},
}

TIER_LABELS = {"auto": "Era standard", "light": "Light",
               "heavy": "Heavy", "mixed": "Mixed",
               "guns": "Guns only (AAA, no SAMs)"}


def clamp_intensity(v) -> int:
    try:
        return max(1, min(5, int(v)))
    except (TypeError, ValueError):
        return 3


def _pool(table, era, side, tier):
    node = table.get(era, {}).get(side, {})
    if tier == "mixed":
        seen, out = set(), []
        for t in ("light", "heavy", "auto"):
            for x in node.get(t, []):
                if x not in seen:
                    seen.add(x); out.append(x)
        return out
    return list(node.get(tier, node.get("auto", [])))


def sam_kits_for(era, side, tier, fallback):
    """Kit keys for this era/side/tier; fall back to the era_cfg list if empty.

    "guns" returns [] WITHOUT falling back — an empty pool is the entire point
    of that tier, not a gap to paper over."""
    if tier == "guns":
        return []
    pool = _pool(TIER_SAMS, era, side, tier)
    return pool or list(fallback or [])


def cap_types_for(era, side, tier):
    # Guns tier still gets fighters — flak never stopped the MiGs coming up —
    # but from the LIGHT pool: gun-era airframes, no lookdown-shootdown escorts.
    return _pool(TIER_CAP, era, side, "light" if tier == "guns" else tier)


def aaa_types_for(era, side):
    return list(TIER_AAA.get(era, {}).get(side, []))


def plan(intensity, rng: random.Random):
    """Roll concrete counts for this mission off the seed."""
    cfg = INTENSITY[clamp_intensity(intensity)]
    return {
        "n_extra_sams": rng.randint(*cfg["extra_sams"]),
        "n_cap": rng.randint(*cfg["cap_flights"]),
        "skill": cfg["skill"],
        "label": cfg["label"],
    }


def _land_bearing(ap, fields, enemy_center, rng: random.Random):
    """Pick an offset bearing from airfield `ap` that bets on staying over land.

    Priority (shared by the SAM belt and the AAA belt — extracted from
    add_area_sams so both make the same bet): toward the nearest other enemy
    field within 90 km (same landmass) > toward the enemy rear > along the
    runway axis (flat ground extends along the runway line) > random."""
    others = [o for o in fields
              if o is not ap and _dist(o.position, ap.position) < 90000]
    if others:
        near = min(others, key=lambda o: _dist(o.position, ap.position))
        return _bearing(ap.position, near.position)
    if _dist(ap.position, enemy_center) > 5000:
        return _bearing(ap.position, enemy_center)
    try:
        from .placement import AirfieldKeepOut
        brg = AirfieldKeepOut(ap).runway_axis_heading()
        return (brg + 180) % 360 if rng.random() < 0.5 else brg
    except Exception:
        return rng.uniform(0, 360)


def add_area_sams(m, country, era, enemy_side, tier, n, own_center, enemy_center,
                  rng: random.Random, gfx_threats=None, enemy_fields=None):
    """Place n standalone SAM sites forming the belt the player must penetrate.

    Sites are ANCHORED TO ENEMY AIRFIELDS, 4-9 km out — not interpolated on the
    own→enemy axis. Two reasons:
    1. REALISM: SAM belts defend assets. SA-2/SA-10 regiments are laid around
       airbases, ports and C2 — not scattered across empty map squares.
    2. TERRAIN SAFETY: pydcs exposes NO land/water query, so any free-floating
       coordinate can land in the sea on water-heavy maps (Marianas, Sinai,
       Kola...). Airfields are the one feature guaranteed to be on land; a
       short offset from one stays on land.
    Offset direction is another LAND BET, in priority order: toward the nearest
    other enemy airfield within 90 km (same landmass), else toward the enemy
    rear (deeper into their own territory), else along the runway axis (flat
    ground extends along the runway line). Never "toward the player" — on
    carrier maps that bearing points out to sea.
    Front-line fields (closest to the player) get sites first: that puts the
    belt between the player and the enemy heartland, same intent as before.
    Fallback: no enemy fields on the map -> old axis interpolation (rare)."""
    from .airdefense import place_sam_site
    kits = sam_kits_for(era, enemy_side, tier, [])
    if not kits or n <= 0:
        return []
    created = []
    fields = sorted(enemy_fields or [], key=lambda a: _dist(a.position, own_center))
    for i in range(n):
        if fields:
            ap = fields[i % len(fields)]
            brg = (_land_bearing(ap, fields, enemy_center, rng)
                   + rng.uniform(-35, 35)) % 360
            center = _offset(ap.position, rng.uniform(4000, 9000), brg)
        else:  # legacy fallback: no enemy airfields known
            axis = _bearing(own_center, enemy_center)
            dist = _dist(own_center, enemy_center)
            frac = rng.uniform(0.25, 0.55)
            along = mapping.Point(
                own_center.x + (enemy_center.x - own_center.x) * frac,
                own_center.y + (enemy_center.y - own_center.y) * frac,
                m.terrain)
            center = _offset(along, rng.uniform(-0.18, 0.18) * dist,
                             (axis + 90) % 360)
        kit = rng.choice(kits)
        name = f"{SAM_KITS[kit]['label']} - Area {i+1}"
        vg = place_sam_site(m, country, kit, center, rng, name)
        for u in vg.units:
            u.skill = Skill.High
        created.append(name)
        if gfx_threats is not None:
            gfx_threats.append((center, SAM_KITS[kit].get("wez_m", 25000),
                                SAM_KITS[kit]["label"]))
    return created


def place_aaa_cluster(m, country, era, side, center, rng: random.Random, name):
    """One AAA site: 3-5 guns in a loose ring, mixed calibers, single group.

    A cluster, not a lone gun — one ZU-23 is a nuisance, a battery is a threat
    picture. Ring radius 60-160 m mirrors real revetment spacing and keeps the
    whole site inside one F10 circle."""
    types = aaa_types_for(era, side)
    if not types:
        return None
    n_guns = rng.randint(3, 5)
    vg = None
    for i in range(n_guns):
        utype = resolve(rng.choice(types))
        pos = _offset(center, rng.uniform(60, 160), (360.0 / n_guns) * i
                      + rng.uniform(-25, 25))
        heading = rng.uniform(0, 360)
        if vg is None:
            vg = m.vehicle_group(country, name, utype, pos, heading=heading)
        else:
            u = m.vehicle(f"{name} {i+1}", utype)
            u.position = pos
            u.heading = heading
            vg.add_unit(u)
    if vg is not None:
        for u in vg.units:
            u.skill = Skill.High
    return vg


def add_area_aaa(m, country, era, enemy_side, n, own_center, enemy_center,
                 rng: random.Random, gfx_threats=None, enemy_fields=None):
    """The gun belt: n AAA clusters anchored to enemy airfields, 3-7 km out.

    Same anchoring discipline as add_area_sams (airfields are the one feature
    guaranteed to be on land; see that docstring), but closer in and denser —
    guns defend point targets, not airspace. WEZ ring for the F10/intel layer
    is 3.5 km: honest for 57 mm, optimistic for the 23 mm underneath it."""
    if n <= 0 or not aaa_types_for(era, enemy_side):
        return []
    created = []
    fields = sorted(enemy_fields or [], key=lambda a: _dist(a.position, own_center))
    for i in range(n):
        if fields:
            ap = fields[i % len(fields)]
            # same LAND BET as add_area_sams: bias the offset toward another
            # enemy field / the enemy rear / the runway axis, never a blind
            # random bearing (which points out to sea on coastal fields).
            brg = (_land_bearing(ap, fields, enemy_center, rng)
                   + rng.uniform(-45, 45)) % 360
            center = _offset(ap.position, rng.uniform(3000, 7000), brg)
        else:
            axis = _bearing(own_center, enemy_center)
            dist = _dist(own_center, enemy_center)
            frac = rng.uniform(0.35, 0.65)
            along = mapping.Point(
                own_center.x + (enemy_center.x - own_center.x) * frac,
                own_center.y + (enemy_center.y - own_center.y) * frac,
                m.terrain)
            center = _offset(along, rng.uniform(-0.12, 0.12) * dist,
                             (axis + 90) % 360)
        name = f"AAA - Area {i+1}"
        if place_aaa_cluster(m, country, era, enemy_side, center, rng, name):
            created.append(name)
            if gfx_threats is not None:
                gfx_threats.append((center, 3500, "AAA"))
    return created


def add_enemy_cap(m, country, era, enemy_side, tier, n, own_center, enemy_center,
                  skill, rng: random.Random, gfx=None, intensity=3,
                  fits=None, warnings=None):
    """Spawn n enemy CAP flights (2-ship) orbiting on the threat axis in the
    enemy half. Airborne (inflight) so there is no parking/pop-in interaction;
    they engage inbound air within ~55 km.

    Each flight is ARMED from data/loadouts.json before it is handed back —
    pydcs cannot supply a default server-side (see missiongen/loadouts.py), so
    without this every CAP flight in the product flies clean. `fits` collects
    one describe() record per flight for the briefing."""
    types = cap_types_for(era, enemy_side, tier)
    if not types or n <= 0:
        return []
    axis = _bearing(own_center, enemy_center)
    created = []
    for i in range(n):
        # THE ENEMY HALF, AND ONLY THE ENEMY HALF.
        #
        # Rob: "let's not add a single random red aircraft at the beginning of
        # a mission in the blue area." This band was 0.40-0.65 of the way from
        # the friendly center to the enemy center — so 40% of the roll space
        # put an enemy CAP nearer the player's own airfields than the enemy's,
        # and MEASURED over 2,000 seeds it landed on the blue side of the
        # midpoint 42% of the time. A fighter orbiting over your home plate at
        # mission start is not a threat picture, it is a mistake.
        #
        # 0.55 is past the midpoint by enough that the 40 km racetrack and the
        # lateral jitter (both PERPENDICULAR to the axis, so neither moves this
        # fraction) still leave the station in the half it defends; 0.80 stops
        # short of the enemy fields themselves, where the airbase SAMs already
        # live. They still come to you — `max_engage_distance` is 55 km — but
        # they come FROM their own side, which is the whole point of a CAP.
        frac = rng.uniform(0.55, 0.80)
        mid = mapping.Point(
            own_center.x + (enemy_center.x - own_center.x) * frac,
            own_center.y + (enemy_center.y - own_center.y) * frac,
            m.terrain)
        lateral = _offset(mid, rng.uniform(-0.15, 0.15)
                          * _dist(own_center, enemy_center), (axis + 90) % 360)
        # 40 km racetrack across the threat axis
        p1 = _offset(lateral, 20000, (axis + 90) % 360)
        p2 = _offset(lateral, 20000, (axis - 90) % 360)
        ctype = resolve_plane(rng.choice(types))
        alt = rng.choice([5000, 6000, 7500])
        name = f"CAP {'Kite Snake Viper Cobra Wolf'.split()[i % 5]} {i+1}"
        try:
            fg = m.patrol_flight(country, name, ctype, None, p1, p2,
                                 speed=800, altitude=alt,
                                 max_engage_distance=55000, group_size=2)
        except Exception:
            continue
        for u in fg.units:
            u.skill = skill
        _loadouts.arm(fg, ctype.id, _loadouts.ROLE_CAP, era, intensity,
                      warnings=warnings)
        if fits is not None:
            fits.append(_loadouts.describe(ctype.id, _loadouts.ROLE_CAP, era,
                                           intensity, count=len(fg.units)))
        created.append(f"{name} ({ctype.id})")
        if gfx is not None:
            gfx.setdefault("threats", [])
            # a light marker ring at the CAP station (advisory, on the intel layer)
            gfx.setdefault("cap_threats", []).append(
                (lateral, f"CAP {ctype.id}"))
    return created


def add_bfm_adversary(m, country, era, enemy_side, tier, player_pos, player_alt,
                      skill, rng: random.Random, guns_only=False, n=1,
                      intensity=3, fits=None, warnings=None,
                      setup="neutral", player_heading=None):
    """E2 (Quick Flight): the merge, and the three-perch BFM ladder.

    One (option two) era-correct adversary placed RELATIVE TO THE PLAYER and
    cleared hot inside 30 km, so the fight is on within seconds of mission
    start rather than after a 60-mile intercept.

    `setup` selects the ride (see bfm.SETUPS). The difficulty knob is the
    GEOMETRY, not the AI skill: the same bandit at the same skill teaches three
    different lessons depending on who starts behind whom.

        neutral      2 nm abeam, co-heading — the everyday fight
        offensive    1.2 nm ahead, 30 deg angle off — you own his six
        defensive    1.2 nm astern, slightly high — he owns yours
        high_aspect  5 nm on the nose, hot — nose-to-nose merge

    The bandit flies a STRAIGHT leg from its spawn rather than a racetrack for
    the perch setups: an orbit turns as the mission starts, so the briefed
    angle-off would be a lie by the time the pilot looked.

    Distinct from add_enemy_cap on purpose: CAP defends the enemy half of the
    map; this bandit exists only relative to the PLAYER. Type pool reuses
    TIER_CAP (era-gated, no anachronism); "guns_only" biases toward the light
    pool for the classic knife fight."""
    from . import bfm as _bfm
    types = cap_types_for(era, enemy_side, "light" if guns_only else tier)
    if not types:
        return []
    ctype = resolve_plane(rng.choice(types))
    spec = _bfm.SETUPS.get(setup) or _bfm.SETUPS[_bfm.DEFAULT_SETUP]
    # Your nose. Without a briefed heading the geometry cannot be stated, so
    # the caller passes the player's actual heading; the random fallback keeps
    # older callers working (the fight is still relative to the player).
    own_hdg = float(player_heading) if player_heading is not None else rng.uniform(0, 360)
    brg = (own_hdg + spec["bearing_off_nose"]) % 360
    spawn = _offset_pt(player_pos, spec["range_m"], brg)
    bandit_hdg = (own_hdg + spec["bandit_heading_off"]) % 360
    alt = max(1500, int(player_alt) + int(spec.get("alt_offset_m", 0)))
    if setup == "neutral":
        # unchanged legacy geometry: a short racetrack abeam
        p1 = _offset_pt(spawn, 3000, (brg + 90) % 360)
        p2 = _offset_pt(spawn, 3000, (brg - 90) % 360)
    else:
        # straight leg on the briefed heading. p1 is AHEAD of the spawn (the
        # group flies spawn -> p1 -> p2), which is what makes the bandit's
        # initial heading the briefed one; 40 km is far enough that it does
        # not reach the turn before the fight is joined.
        p1 = _offset_pt(spawn, 20000, bandit_hdg)
        p2 = _offset_pt(spawn, 40000, bandit_hdg)
    name = "Bandit BFM"
    try:
        # SPAWN EXACTLY WHERE BRIEFED. m.patrol_flight() places an in-flight
        # patrol 10 km due -x of its first orbit point (pydcs
        # `mapping.Point(pos1.x - 10*1000, pos1.y)`) — a fixed offset that
        # ignores heading entirely. Measured with it: the "2 nm abeam" neutral
        # merge actually spawned 5.9 nm away at 149 degrees off the nose, so
        # every BFM brief this product has ever printed was fiction. Build the
        # group at the real point, then attach the same orbit + engage tasking
        # patrol_flight would have.
        fg = m.flight_group_inflight(country, name, ctype, spawn, alt,
                                     maintask=_task.CAP,
                                     group_size=max(1, min(2, n)))
        m.patrol_flight_to_group(fg, p1, p2, 750, alt, 30000)
    except Exception:
        return []
    for u in fg.units:
        u.skill = skill
        # Face the briefed heading. pydcs points a patrol flight at its first
        # leg, which is right for the racetrack and wrong for a perch: on the
        # offensive ride the bandit must be pointing AWAY from you at t=0, or
        # you are not on his six, you are in a head-on pass.
        if setup != "neutral":
            u.heading = bandit_hdg % 360.0     # pydcs stores DEGREES here
    # The BFM fit is deliberately NOT the CAP fit: the merge is a short-range
    # fight, so the bandit carries IR and a gun, never the radar-missile load
    # that would kill the player 20 nm before the exercise starts.
    _loadouts.arm(fg, ctype.id, _loadouts.ROLE_BFM, era, intensity,
                  warnings=warnings)
    if fits is not None:
        fits.append(_loadouts.describe(ctype.id, _loadouts.ROLE_BFM, era,
                                       intensity, count=len(fg.units)))
    return [f"{name} ({ctype.id})"]


def _offset_pt(pos, meters, bearing_deg):
    import math
    b = math.radians(bearing_deg)
    return mapping.Point(pos.x + meters * math.cos(b),
                         pos.y + meters * math.sin(b), pos._terrain)


# --- small geo helpers (kept local to avoid import cycles) ------------------
def resolve_plane(name):
    from dcs import planes, helicopters
    for mod in (planes, helicopters):
        t = getattr(mod, name, None)
        if t is not None:
            return t
    raise ValueError(f"threat aircraft '{name}' not found")


def _bearing(a, b):
    import math
    return math.degrees(math.atan2(b.y - a.y, b.x - a.x)) % 360


def _dist(a, b):
    import math
    return math.hypot(b.x - a.x, b.y - a.y)
