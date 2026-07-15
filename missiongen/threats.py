"""Threat Dial (v1.6.0): user control over how MANY threats spawn and what LEVEL.

Two orthogonal knobs on the recipe:

- threat_intensity (1-5): COUNT. How many extra area SAM sites and enemy CAP
  flights spawn on top of the base per-airfield air defense. Each level draws a
  RANDOM count from a band off the mission seed, so re-rolls feel different.
      1 Minimal · 2 Light · 3 Moderate (default) · 4 Heavy · 5 Maximum
- threat_tier ("auto"|"light"|"heavy"|"mixed"): LEVEL. Which systems/aircraft.
      auto  = the era's standard doctrine (back-compat with pre-dial missions)
      light = older/shorter-range (SA-2/SA-3 · MiG-21/23) — trainer-friendly
      heavy = modern/long-range   (SA-10/SA-11 · Su-27/MiG-31)
      mixed = both pools, rolled per site/flight ("surprise me")

Everything is era-gated: a WWII "heavy" tier still can't field an SA-10 — the
pools simply don't contain anachronisms. Selection is seeded, so a recipe+seed
always regenerates the same threat picture.
"""
import random
from dcs import mapping
from dcs.unit import Skill

from .kits import SAM_KITS
from .resolver import resolve
from .dressing import _offset

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
               "heavy": "Heavy", "mixed": "Mixed"}


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
    """Kit keys for this era/side/tier; fall back to the era_cfg list if empty."""
    pool = _pool(TIER_SAMS, era, side, tier)
    return pool or list(fallback or [])


def cap_types_for(era, side, tier):
    return _pool(TIER_CAP, era, side, tier)


def plan(intensity, rng: random.Random):
    """Roll concrete counts for this mission off the seed."""
    cfg = INTENSITY[clamp_intensity(intensity)]
    return {
        "n_extra_sams": rng.randint(*cfg["extra_sams"]),
        "n_cap": rng.randint(*cfg["cap_flights"]),
        "skill": cfg["skill"],
        "label": cfg["label"],
    }


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
            others = [o for o in fields
                      if o is not ap and _dist(o.position, ap.position) < 90000]
            if others:
                near = min(others, key=lambda o: _dist(o.position, ap.position))
                base_brg = _bearing(ap.position, near.position)
            elif _dist(ap.position, enemy_center) > 5000:
                base_brg = _bearing(ap.position, enemy_center)
            else:  # single isolated field: runway axis extends over land
                try:
                    from .placement import AirfieldKeepOut
                    base_brg = AirfieldKeepOut(ap).runway_axis_heading()
                    if rng.random() < 0.5:
                        base_brg = (base_brg + 180) % 360
                except Exception:
                    base_brg = rng.uniform(0, 360)
            brg = (base_brg + rng.uniform(-35, 35)) % 360
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


def add_enemy_cap(m, country, era, enemy_side, tier, n, own_center, enemy_center,
                  skill, rng: random.Random, gfx=None):
    """Spawn n enemy CAP flights (2-ship) orbiting on the threat axis in the
    enemy half. Airborne (inflight) so there is no parking/pop-in interaction;
    they engage inbound air within ~55 km."""
    types = cap_types_for(era, enemy_side, tier)
    if not types or n <= 0:
        return []
    axis = _bearing(own_center, enemy_center)
    created = []
    for i in range(n):
        frac = rng.uniform(0.40, 0.65)
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
        created.append(f"{name} ({ctype.id})")
        if gfx is not None:
            gfx.setdefault("threats", [])
            # a light marker ring at the CAP station (advisory, on the intel layer)
            gfx.setdefault("cap_threats", []).append(
                (lateral, f"CAP {ctype.id}"))
    return created


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
