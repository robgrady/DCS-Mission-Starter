"""Air-to-air refuelling: the right tanker, at a speed the receiver can fly.

WHY THIS MODULE EXISTS.

Until v1.73.0 every tanker in this product flew at one speed and one altitude:
`speed=550` (pydcs takes km/h here) at 6,096 m. Measured out of a generated
mission that is **152.8 m/s — 297 kt TAS, about 217 KIAS at 20,000 ft.**

A KC-135 at 217 KIAS is not a refuelling track, it is an endurance
demonstration. Real boom AAR for fighters runs in the high 200s to low 300s
KIAS, and 217 puts an F-16 mushing behind the boom on the back side of the drag
curve, fighting the jet instead of flying the position. It is the single reason
a pilot would conclude our tanker "feels wrong", and it was wrong for every
receiver, every era, every map.

So the speed is no longer a constant. It is a per-tanker INDICATED airspeed,
converted to the true airspeed the mission file wants using the density ratio
at that tanker's own altitude — because the thing a pilot flies is IAS and the
thing DCS stores is TAS, and pretending they are the same is how you get 217.

ON THE PASS CRITERIA, which are four different kinds of claim and must not be
printed as though they were one:

  * The STABILISED-THEN-CLEARED shape at pre-contact is doctrine (ATP-56).
  * 1-3 kt approach closure is quoted (Stephenson, *Air Refueling Receiver*).
  * ~1 ft/sec in the final few feet is quoted (KC-46 program literature).
    One knot is 1.688 ft/sec, so this is roughly a THIRD of the approach
    figure — the card used to print only the approach number, which asked a
    pilot to arrive at the boom two to five times faster than the source it
    was implicitly leaning on. Both are now printed, phase-labelled.
  * 15 s stabilised is a GATE. 60 s hands-steady is OUR proficiency standard
    and is labelled as ours; no document in the library states a duration.

ON THE NUMBERS, honestly. Published real-world AAR airspeed bands are wide and
depend on receiver, gross weight and altitude, and no document in our source
library states them. What is in the table below is therefore **an operating
point chosen so the receiver can actually hold contact in DCS**, sitting inside
the real band for that tanker/receiver pair. That is a different kind of claim
from the BFM perches (which are quoted from a syllabus) and it is labelled as
one: `basis` on every entry says whether it is doctrine or a tuned setting.
"""
from dcs import planes

# --- the tankers ----------------------------------------------------------
#
# `ias_kt`   what the pilot flies, and what the brief prints.
# `alt_ft`   the track altitude.
# `boom`     True = flying boom (USAF receptacle), False = probe-and-drogue.
# `basis`    where the operating point comes from. Read this before quoting it.
TANKERS = {
    "kc135": {
        "type": planes.KC_135,
        "label": "KC-135 Stratotanker (boom)",
        "boom": True,
        "ias_kt": 300,
        "max_ias_kt": 315,
        "alt_ft": 20000,
        "max_alt_ft": 35000,
        "callsign": "Texaco",
        "service": [1957, None],
        "eras": ["coldwar", "modern", "gwot"],
        "naval": False,
        "basis": "tuned for DCS, inside the real boom-AAR band for fighters",
        "note": "The USAF standard. You fly formation on the tanker and the "
                "boom operator flies the boom to you.",
    },
    "kc135mprs": {
        "type": planes.KC135MPRS,
        "label": "KC-135MPRS (wing drogues)",
        "boom": False,
        "ias_kt": 280,
        "max_ias_kt": 300,
        "alt_ft": 20000,
        "max_alt_ft": 35000,
        "callsign": "Arco",
        "service": [1980, None],
        "eras": ["modern", "gwot"],
        "naval": False,
        "basis": "tuned for DCS; drogue work runs slower than boom",
        "note": "Two wing baskets. You fly the probe into the basket — the "
                "basket does nothing to help you.",
    },
    "kc130": {
        "type": planes.KC130,
        "label": "KC-130 Hercules (drogues)",
        "boom": False,
        "ias_kt": 230,
        "max_ias_kt": 235,
        "alt_ft": 15000,
        "max_alt_ft": 24000,
        "callsign": "Shell",
        "service": [1962, None],
        "eras": ["coldwar", "modern", "gwot"],
        "naval": True,
        "basis": "tuned for DCS; a Hercules cannot hold jet tanker speeds",
        "note": "Slow and low. Comfortable for a Hornet or a Harrier, and the "
                "only tanker a helicopter has any business behind.",
    },
    "s3b": {
        "type": planes.S_3B_Tanker,
        "label": "S-3B Viking (carrier organic)",
        "boom": False,
        "ias_kt": 250,
        "max_ias_kt": 260,
        "alt_ft": 12000,
        "max_alt_ft": 28000,
        "callsign": "Texaco",
        "service": [1981, 2009],
        "eras": ["modern", "gwot"],
        "naval": True,
        "organic": True,
        "basis": "tuned for DCS; the boat's own tanker works low and slow",
        "note": "The recovery tanker. Small, close to the boat, and the "
                "difference between a bolter and a swim.",
    },
    "ka6d": {
        "type": planes.A6E,
        # THE ONLY TANKER IN THIS TABLE THAT NEEDS A STORE FITTED. Every other
        # entry has a built-in refuelling system; the A-6E carries a D-704 pod
        # on a pylon, and pydcs's `refuel_flight` does not fit one. It shipped
        # with `["pylons"] = {}` — a tanker on a track, on frequency, with a
        # TACAN and a briefing, that could not give anybody fuel. That is the
        # say/do gap this product exists to avoid, in its purest form.
        "store": ("Pylon3", "D_704_Refuelling_Pod"),
        "label": "KA-6D / A-6E buddy store (carrier organic)",
        "boom": False,
        "ias_kt": 290,
        "max_ias_kt": 310,
        "alt_ft": 15000,
        "max_alt_ft": 30000,
        "callsign": "Texaco",
        "service": [1970, 1997],
        "eras": ["coldwar", "modern"],
        "naval": True,
        "organic": True,
        "basis": "tuned for DCS; the Cold War air wing's own gas",
        "note": "Before the Viking, the air wing tanked itself with an Intruder "
                "carrying a buddy pack. Same job, less of it.",
    },
    "il78": {
        "type": planes.IL_78M,
        "label": "IL-78M (drogues)",
        "boom": False,
        "ias_kt": 280,
        "max_ias_kt": 300,
        "alt_ft": 18000,
        "max_alt_ft": 35000,
        "callsign": "Kuznets",
        "service": [1984, None],
        "eras": ["modern", "gwot"],
        "naval": False,
        "basis": "tuned for DCS",
        "note": "Red side. Three baskets, same probe-and-drogue problem.",
    },
}

# --- who can actually take fuel -------------------------------------------
#
# THIS USED TO BE A DENY-LIST AND IT FAILED OPEN.
#
# `NO_AAR` held exact DCS type ids — "P-51D", "SpitfireLFMkIX", "P-47D-30",
# "MiG-15bis", "F-86F Sabre", "L-39C", "C-101EB". The roster ships
# "P-51D-30-NA", "SpitfireLFMkIXCW", "P-47D-30bl1", "MiG-15bis_FC",
# "F-86F_FC", "L-39ZA", "C-101CC". Almost none of those strings matched, so
# `can_refuel()` returned True for a Mustang, a Huey, a Ka-50 and an F-5E.
# Only era gating hid it: the warbird eras have no tanker in the table, so the
# pool came back empty by luck rather than by design. In Cold War and modern
# it did not — an F-5E, a Gazelle or a Hind would get a KC-130 on station and
# a two-page refuelling card for a capability it does not have.
#
# So it is an ALLOW-LIST now, and it FAILS CLOSED. An aircraft nobody has
# confirmed gets no tanker and a warning, which is the safe direction to be
# wrong in: a missing tanker is a bug report, an impossible one is a pilot
# concluding they cannot refuel.
#
# ON THE PROVENANCE, honestly: no published table maps DCS modules to
# refuelling systems. ED's own scripting docs define the two system types and
# stop there, and the community threads we can reach discuss technique rather
# than capability. **This list is OURS** — curated from module documentation
# and the real aircraft — and it is the kind of claim that should be corrected
# by a pilot who finds it wrong rather than defended. Additions are cheap;
# each one is a line here.
BOOM, PROBE = "boom", "probe"

AAR_RECEIVERS = {
    # --- flying boom, USAF receptacle ---
    "F-16C_50": BOOM,
    "F-15C": BOOM,            # FC3
    "F-15E": BOOM,
    "F-15ESE": BOOM,
    "A-10A": BOOM,            # FC3
    "A-10C": BOOM,
    "A-10C_2": BOOM,
    "F-4E-45MC": BOOM,        # Heatblur; boom receptacle behind the cockpit
    "F-16A": BOOM,
    "F-16A MLU": BOOM,
    "B-1B": BOOM,             # AI only, but the pairing logic still needs it
    "B-52H": BOOM,
    "F-117A": BOOM,
    # --- probe and drogue ---
    "FA-18C_hornet": PROBE,
    "F-14A-95-GR": PROBE,
    "F-14A-135-GR": PROBE,
    "F-14A-135-GR-Early": PROBE,
    "F-14B": PROBE,
    # THE ID IN THE MISSION FILE, not the display label. The F-14B(U) has
    # three spellings in this codebase — roster key `F_14B_U`, display label
    # `F-14B(U)`, and DCS type id `F-14BU` — and only the third one ever
    # reaches `can_refuel`. Keying this on the label meant the wizard offered
    # the Tomcat and the mission then contained no tanker at all.
    "F-14BU": PROBE,
    "AV8BNA": PROBE,
    "M-2000C": PROBE,
    "JF-17": PROBE,
    "Su-33": PROBE,
    "Tornado IDS": PROBE,
    "Tornado GR4": PROBE,
}

# Kept as a derived view so existing call sites and tests keep working.
BOOM_RECEIVERS = {k for k, v in AAR_RECEIVERS.items() if v == BOOM}


# --- what the RECEIVER wants to fly ---------------------------------------
#
# THE BUG THIS FIXES, reported from the cockpit: "the tankers are way too slow
# for the jet aircraft." They were, and the reason is that the speed was a
# property of the TANKER alone. A KC-130 at 210 KIAS is a comfortable track for
# a Harrier and a bad afternoon for a Tomcat, and the table could not tell the
# difference because it never asked who was joining.
#
# So each receiver carries a comfortable BAND, and the track is the tanker's
# operating point clamped into it — then clamped again by what the tanker's own
# airframe can actually hold. Three real consequences:
#
#   * A KC-135 SLOWS DOWN for an A-10. 300 KIAS is a fine boom track for a
#     Viper and impossible for a Hog, and the real tanker slows down too.
#   * A KC-130 SPEEDS UP for a fast jet, as far as it can, and then runs out
#     of airplane — at which point the brief SAYS SO rather than leaving the
#     pilot to conclude they cannot fly formation.
#   * `choose()` now prefers a tanker that can actually meet the receiver's
#     floor, so a Tomcat gets the MPRS or the Viking ahead of the Hercules.
#
# ON THE NUMBERS: ours, like the tanker table. Published AAR bands are wide and
# depend on weight, altitude and stores. These are operating points chosen so
# the receiver is not on the back of the drag curve and not running out of
# control authority — the two ways a track speed makes formation impossible.
RECEIVER_IAS = {
    # --- fast jets: want speed, and the Phantom wants the most of it ---
    "F-4E-45MC": (270, 325),
    "F-16C_50": (260, 320),
    "F-15C": (260, 320),
    "F-15E": (260, 320),
    "F-15ESE": (260, 320),
    # 230, not 250: a Hornet tanks off a Hercules routinely and is comfortable
    # doing it. Setting this to a Tomcat's floor produced a warning on the most
    # ordinary pairing in the Navy, which is how a real caveat gets ignored.
    "FA-18C_hornet": (230, 300),
    # 270, not 250. Reported from the cockpit: at 270 the KA-6D was "still
    # slow for the F-14 to line up with it". A Tomcat on a drogue wants to be
    # well clear of the back of the drag curve, and a floor set below where the
    # airplane is comfortable makes the shortfall warning silent exactly when
    # it should be speaking.
    "F-14A-95-GR": (270, 315),
    "F-14A-135-GR": (270, 315),
    "F-14A-135-GR-Early": (270, 315),
    "F-14B": (270, 315),
    "F-14BU": (270, 315),
    "Su-33": (250, 300),
    "JF-17": (250, 300),
    "M-2000C": (250, 300),
    # --- slower airframes: a fast track is the problem, not the fix ---
    "AV8BNA": (200, 250),
    "A-10A": (190, 220),
    "A-10C": (190, 220),
    "A-10C_2": (190, 220),
    # AI-only heavies keep the tanker's own point; no entry means no clamp.
}

# Below this much shortfall we say nothing; at or above it the brief warns,
# because a receiver flying 15 kt under its comfortable minimum is a pilot
# about to blame themselves for the airplane.
SHORTFALL_WARN_KT = 15


def track_ias_kt(key: str, receiver_id: str = "") -> int:
    """The INDICATED airspeed this pairing actually flies.

    The tanker's operating point, clamped into the receiver's comfortable band,
    then clamped by what the tanker itself can hold. Order matters: the
    receiver states a preference, the tanker has the final say, because it is
    the one that has to fly it.
    """
    t = TANKERS[key]
    ias = t["ias_kt"]
    band = RECEIVER_IAS.get(receiver_id)
    if band:
        lo, hi = band
        ias = max(lo, min(ias, hi))
    return int(min(ias, t.get("max_ias_kt", ias)))


def shortfall_kt(key: str, receiver_id: str = "") -> int:
    """How far under the receiver's comfortable minimum this track ends up.

    Zero for every pairing that works. Positive means the tanker physically
    cannot go fast enough for this jet — which is a fact about the pairing, not
    a defect, and belongs in the brief rather than in a silent compromise.
    """
    band = RECEIVER_IAS.get(receiver_id)
    if not band:
        return 0
    return max(0, band[0] - track_ias_kt(key, receiver_id))


# --- terrain: an AAR track has to be ABOVE the ground -----------------------
#
# REPORTED FROM THE COCKPIT: "the altitude seems too low for the terrain." It
# was. The KC-130 and the KA-6D flew a 15,000 ft track and the S-3B a 12,000 ft
# one, and the pre-contact air start puts the receiver a further 1,000 ft
# BELOW that. **Mount Elbrus is 18,510 ft and sits on the free Caucasus map**,
# so a Hercules track could be four thousand feet under the highest ground a
# pilot might be orbiting over. On Afghanistan it is worse: Noshaq is 24,580 ft.
#
# pydcs carries NO terrain elevation — no heightmap, no airfield altitudes — so
# the engine cannot ask how high the ground is under the tanker. The honest
# substitute is the highest ground ON THE WHOLE MAP: a track that clears that
# cannot be below terrain anywhere, which is the safe direction to be
# approximate in.
#
# ON THE NUMBERS: real-world elevations of the highest point inside each map's
# coverage. `cited` entries have a source in docs/SOURCES.md; the rest are OURS
# and are the kind of claim a pilot should correct rather than trust. Being
# wrong HIGH costs a slightly unrealistic track; being wrong LOW puts a
# training mission inside a mountain.
TERRAIN_MAX_FT = {
    "caucasus": (18510, "cited"),        # Mt Elbrus 5,642 m
    "afghanistan": (24580, "cited"),     # Noshaq 7,492 m, Afghanistan's highest
    "iraq": (11850, "ours"),             # Cheekha Dar, Zagros, ~3,611 m
    "nevada": (13150, "ours"),           # Boundary Peak ~4,007 m
    "persiangulf": (14000, "ours"),      # Zagros inside the map area
    "syria": (9230, "ours"),             # Mt Hermon ~2,814 m
    "sinai": (8630, "ours"),             # Mt Catherine ~2,629 m
    "germany": (3750, "ours"),           # central-German uplands
    "kola": (4000, "ours"),              # Khibiny massif
    "falklands": (3000, "ours"),         # islands plus the coastal strip
    "marianas": (1350, "ours"),          # Mt Lamlam
    "normandy": (1200, "ours"),
    "thechannel": (1200, "ours"),
}

# How far above the highest ground the TRACK sits. The receiver starts 1,000 ft
# BELOW the track at pre-contact, so this is clearance for the RECEIVER rather
# than the tanker: 3,000 ft leaves 2,000 under the pilot who is actually low.
#
# It was 5,000 for one draft and that was too much. Clearing the map's highest
# peak by five thousand feet put a Hercules at 23,500 ft on Caucasus — near its
# ceiling, at 230 KIAS, which is its own kind of unflyable. The guarantee that
# matters is "cannot be below terrain anywhere on this map", and 3,000 buys it
# without pushing an airframe to the edge of its envelope to get there.
TERRAIN_CLEARANCE_FT = 3000

# Unknown map -> assume the worst we know about. Failing closed here means an
# unlisted map gets a high track, which is unrealistic; failing open means it
# gets a track inside a mountain. Those are not comparable costs.
TERRAIN_MAX_DEFAULT_FT = max(v[0] for v in TERRAIN_MAX_FT.values())


def terrain_floor_ft(map_key: str) -> int:
    """The lowest track altitude that clears this map's highest ground.

    Rounded UP to the next thousand, because this number is printed on a
    kneeboard and "22,000 ft" is a briefing altitude while "21,510 ft" is a
    calculation somebody has to read twice.
    """
    hi = TERRAIN_MAX_FT.get(map_key, (TERRAIN_MAX_DEFAULT_FT, "assumed"))[0]
    raw = hi + TERRAIN_CLEARANCE_FT
    return int(-(-raw // 1000) * 1000)


def track_alt_ft(key: str, map_key: str = "") -> int:
    """The track altitude actually flown: the tanker's own, raised if the
    terrain demands it and the airplane can reach it."""
    t = TANKERS[key]
    alt = t["alt_ft"]
    if not map_key:
        return int(alt)
    return int(min(max(alt, terrain_floor_ft(map_key)),
                   t.get("max_alt_ft", alt)))


def clears_terrain(key: str, map_key: str) -> bool:
    """Can this tanker get above this map's highest ground at all?

    A KC-130 cannot fly a 29,580 ft track over the Hindu Kush, and pretending
    otherwise puts a Hercules at an altitude it cannot hold. Where the answer
    is no, the tanker is not offered for that map and the reason is stated —
    the same rule the era gate follows.
    """
    if not map_key:
        return True
    return TANKERS[key].get("max_alt_ft", TANKERS[key]["alt_ft"]) >= \
        terrain_floor_ft(map_key)


def ias_to_tas_kt(ias_kt: float, alt_ft: float) -> float:
    """Indicated -> true, ISA. The whole reason the old tanker was slow.

    A pilot flies IAS; a DCS mission file stores TAS. At 20,000 ft the two
    differ by about 37 %, so a table written in IAS and dropped into the file
    unconverted produces a tanker that is a third too slow — which is exactly
    what shipped."""
    sigma = (1.0 - 2.25577e-5 * (alt_ft * 0.3048)) ** 4.2559
    return ias_kt / (sigma ** 0.5)


def track_speed_kmh(key: str, receiver_id: str = "", map_key: str = "") -> float:
    """What pydcs's `refuel_flight(speed=...)` wants: km/h TRUE.

    `receiver_id` is optional so every existing caller keeps working, but every
    caller that KNOWS the receiver must pass it — otherwise the tanker flies one
    speed and the brief, the grader and the indicator quote another.
    """
    return ias_to_tas_kt(track_ias_kt(key, receiver_id),
                         track_alt_ft(key, map_key)) * 1.852


def track_alt_m(key: str, map_key: str = "") -> float:
    """Metres, terrain-aware. `map_key` is optional so old callers keep
    working, but every caller that KNOWS the map must pass it — otherwise the
    tanker flies one altitude and the brief prints another."""
    return track_alt_ft(key, map_key) * 0.3048


def can_refuel(receiver_id: str) -> bool:
    """Fails CLOSED: unknown means no tanker. See AAR_RECEIVERS for why."""
    return receiver_id in AAR_RECEIVERS


def lane_of(receiver_id: str) -> str | None:
    """"boom" | "probe" | None. The single place that answers which kind of
    refuelling an airframe does, so nothing else has to know the sets."""
    return AAR_RECEIVERS.get(receiver_id)


def compatible(key: str, receiver_id: str) -> bool:
    """A boom tanker and a probe receiver is not a hard error in DCS — it is
    worse. The mission builds, the tanker flies, the pilot joins, and nothing
    happens. Match them here so that never reaches a briefing."""
    lane = lane_of(receiver_id)
    if lane is None:
        return False
    return TANKERS[key]["boom"] == (lane == BOOM)


def receivers_for(lane: str, era: str, service: dict, era_cfg: dict,
                  keyed: dict) -> list:
    """Roster KEYS of flyable aircraft in `lane` that are era-legal.

    Takes its data as arguments rather than importing the roster, because this
    module is the one place that must not grow a dependency on the web layer.

    `keyed` maps roster key -> DCS type id, which is the whole reason this
    function exists: AAR_RECEIVERS is keyed by TYPE ID and every recipe is
    keyed by ROSTER KEY, and mixing the two silently returns nothing. That has
    now bitten this module twice.
    """
    window = era_cfg.get("window")
    out = []
    for key, type_id in keyed.items():
        if AAR_RECEIVERS.get(type_id) != lane:
            continue
        svc = service.get(key)
        if svc and window:
            frm, to = svc
            if not (frm <= window[1] and (to is None or to >= window[0])):
                continue
        out.append(key)
    return sorted(out)


def tankers_for(receiver_id: str, era: str, include_red: bool = False,
                map_key: str = "") -> list:
    """Every tanker key that will actually fuel this receiver in this era —
    and, if a map is given, get above its terrain."""
    return sorted(k for k, t in TANKERS.items()
                  if era in t["eras"] and compatible(k, receiver_id)
                  and (include_red or t["callsign"] != "Kuznets")
                  and clears_terrain(k, map_key))


def period_note(key: str, era: str) -> str:
    """"" if this tanker served through the whole era, else why it did not.

    THE INCONSISTENCY THIS REPLACES: the S-3B retired in 2009 and was offered
    in the modern era (2000-2030); the KA-6D retired in 1997 and was not
    offered at all. Both are retired carrier-organic tankers and neither covers
    the whole window — the difference was a hand-applied judgement, not a rule.
    Now it is a rule, and a tanker whose service only PARTLY covers an era is
    offered with a label rather than hidden.

    Hiding it costs the user a real DCS asset; labelling it costs nothing and
    tells the truth. That is the same trade the honest-numbers rule makes
    everywhere else in this module.
    """
    from .resolver import load_json
    t = TANKERS[key]
    svc = t.get("service")
    win = (load_json("eras").get(era) or {}).get("window")
    if not svc or not win:
        return ""
    frm, to = svc
    late = frm > win[0]
    early = to is not None and to < win[1]
    if not late and not early:
        return ""
    if to is not None and to < win[0]:
        return (f"Left service in {to}, before this era begins. Offered anyway "
                f"because the era buckets are coarse — Cold War ends in "
                f"{load_json('eras')['coldwar']['window'][1]} and modern "
                f"starts in {load_json('eras')['modern']['window'][0]}, so "
                f"this tanker's last years fall in the gap. Period-correct for "
                f"a sortie set around {to}.")
    if early and late:
        return f"In service {frm}-{to}, part of this era."
    if early:
        return f"Left service in {to}, part-way through this era."
    return f"Entered service in {frm}, part-way through this era."


def tankers_excluded_by_era(receiver_id: str, era: str,
                            include_red: bool = False,
                            map_key: str = "") -> list:
    """[(key, reason)] — tankers that COULD fuel this receiver but not here.

    An interface that simply omits a tanker looks like a missing feature, and
    somebody has to ask. Naming the absence and its reason turns a suspected
    bug into a history lesson, which is the point of era gating.

    The reason is DERIVED from the service window, not written by hand, so it
    cannot disagree with the availability rule beside it.
    """
    from .resolver import load_json
    win = (load_json("eras").get(era) or {}).get("window") or [0, 9999]
    out = []
    for k, t in sorted(TANKERS.items()):
        if not compatible(k, receiver_id):
            continue
        if not include_red and t["callsign"] == "Kuznets":
            continue
        if era in t["eras"]:
            # In era, so the only thing that can still drop it is the ground.
            # A tanker that vanishes because the map has a mountain in it owes
            # the same explanation as one that vanishes because of a date —
            # otherwise the terrain fix reintroduces the KA-6D complaint.
            if map_key and not clears_terrain(k, map_key):
                out.append((k, (
                    f"Cannot hold the {terrain_floor_ft(map_key):,} ft track "
                    f"this map needs (its ceiling is "
                    f"{t.get('max_alt_ft', t['alt_ft']):,} ft)."
                )))
            continue
        svc = t.get("service")
        if svc and svc[1] is not None and svc[1] < win[0]:
            why = f"Left service in {svc[1]}; this era begins in {win[0]}."
        elif svc and svc[0] > win[1]:
            why = f"Entered service in {svc[0]}; this era ends in {win[1]}."
        else:
            why = (f"Not offered in this era (available in: "
                   f"{', '.join(t['eras'])}).")
        out.append((k, why))
    return out
def choose(receiver_id: str, era: str, carrier: bool = False,
           preferred: str = None, map_key: str = "") -> str | None:
    """The tanker for this receiver, honoring the pilot's pick when it works.

    An explicit choice is never silently overridden — if it is incompatible the
    caller gets None and warns, because quietly swapping the KC-130 a pilot
    asked for is how you get a bug report about the wrong tanker."""
    if not can_refuel(receiver_id):
        return None
    if preferred:
        t = TANKERS.get(preferred)
        if not t or era not in t["eras"] or not compatible(preferred, receiver_id):
            return None
        return preferred
    pool = [k for k, t in TANKERS.items()
            if era in t["eras"] and compatible(k, receiver_id)
            and t["callsign"] != "Kuznets"]
    # A tanker that cannot get above this map's highest ground is not a
    # candidate at all. A KC-130 asked for a 28,000 ft track over the Hindu
    # Kush is a Hercules at an altitude it cannot hold.
    high_enough = [k for k in pool if clears_terrain(k, map_key)]
    if high_enough:
        pool = high_enough
    if not pool:
        return None
    # A tanker that can actually reach this receiver's comfortable speed beats
    # one that cannot, ahead of every other consideration. This is the fix for
    # "the tankers are way too slow for the jet aircraft": the probe lane used
    # to hand a Tomcat the Hercules because it sorted on altitude, and the
    # Hercules physically cannot fly a Tomcat's track.
    fast_enough = [k for k in pool if shortfall_kt(k, receiver_id) == 0]
    if fast_enough:
        pool = fast_enough
    if carrier:
        # The air wing's OWN tanker first. A Hornet off the boat should meet a
        # Viking, not a Hercules — an altitude tie-break used to hand it the
        # Hercules, which is a land-based asset it would rarely see.
        organic = [k for k in pool if TANKERS[k].get("organic")]
        if organic:
            return sorted(organic, key=lambda k: TANKERS[k]["alt_ft"])[0]
        naval = [k for k in pool if TANKERS[k]["naval"]]
        if naval:
            return sorted(naval, key=lambda k: TANKERS[k]["alt_ft"])[0]
    # Ashore, the air wing's own tanker is the wrong answer: an S-3B or a
    # KA-6D belongs to a boat. Sorting purely on altitude used to hand a
    # land-based Hornet a Viking because the Viking flies lowest.
    return sorted(pool, key=lambda k: (bool(TANKERS[k].get("organic")),
                                       not TANKERS[k]["boom"],
                                       TANKERS[k]["alt_ft"]))[0]


# --- the kneeboard card ---------------------------------------------------

def brief_lines(key: str, receiver_id: str = "", freq: str = "", tacan: str = "",
                map_key: str = ""):
    """The AAR procedure card, generated for THIS tanker and THIS receiver.

    Written as a sequence of positions rather than a list of tips, because that
    is how the task is actually flown and how it is actually taught: you are
    always in exactly one of four places, and each one has a single job."""
    t = TANKERS[key]
    boom = t["boom"]
    # The number the MISSION flies, not the tanker's default — they differ
    # whenever the receiver's band clamps it, which is most of the time.
    ias = track_ias_kt(key, receiver_id)
    alt_ft = track_alt_ft(key, map_key)
    raised = map_key and alt_ft > t["alt_ft"]
    short = shortfall_kt(key, receiver_id)
    L = ["=" * 66,
         f"AIR REFUELLING — {t['label']}",
         "=" * 66,
         f"TRACK: {ias} KIAS at {alt_ft:,} ft"
         + (f" · {freq}" if freq else "")
         + (f" · TACAN {tacan}" if tacan else ""),
         "TYPE: " + ("FLYING BOOM — the boom operator flies the boom to you"
                     if boom else
                     "PROBE AND DROGUE — you fly the probe into the basket"),
         "",
         "THE FOUR POSITIONS. You are always in exactly one of them.",
         "",
         "1. RENDEZVOUS — behind and BELOW, 1 nm.",
         f"   Match {ias} KIAS before you are close, not after. Closure",
         "   you have not noticed is closure you cannot stop. Below the track,",
         "   always: if it goes wrong you descend away, and down is safe.",
         "",
         "2. OBSERVATION — line abreast the wing, stepped down.",
         "   Stabilise here. If you cannot hold this position hands-steady for",
         "   thirty seconds you are not ready for the next one, and going",
         "   anyway is how people hit tankers.",
         "",
         "3. PRE-CONTACT — astern, 10-20 ft back"
         + (", boom stowed." if boom else ", basket in sight."),
         "   This is the position that decides the sortie. Everything from here",
         "   is FORMATION FLYING, not aiming.",
         "",
         "4. CONTACT.",
        ]
    if boom:
        L += [
         "   Fly formation on the TANKER — not on the boom. Pick a reference on",
         "   the tanker's belly or the pod and hold it still. The operator will",
         "   fly the boom into your receptacle; your only job is to stop moving.",
         "   Director lights or the operator's calls will walk you fore and aft.",
        ]
    else:
        L += [
         "   Fly the PROBE to the basket with a closure of a few knots and do",
         "   not stop flying formation on the tanker to do it. The basket is",
         "   not a target you aim at — chasing it is the single most common way",
         "   to spend twenty minutes not getting fuel.",
         "   A miss is normal. Back out to pre-contact, stabilise, come again.",
        ]
    L += [
         "",
         "BEFORE YOU FLY THIS: CHECK YOUR STICK.",
         "The most common fix for 'I cannot refuel' is not technique, it is a",
         "control curve. A plastic ball gimbal has center play; a mechanical",
         "one does not; a longer stick is a mechanical curve already. So there",
         "is NO right number and anyone who gives you one is guessing about",
         "your hardware. The principle: add pitch and roll curve until small",
         "corrections stop overshooting, and no further — curve buys you",
         "precision at center and sells you precision at the edges. Deadzone",
         "is a defect compensator, not a technique aid: set it just past your",
         "stick's measured center noise, usually 0-3, and leave it there.",
         "Do NOT curve the throttle. Anticipate instead — the spool is the lag.",
         "",
         "WHY IT OSCILLATES, WHICH IS NOT A CHARACTER FLAW.",
         "What you are doing when you chase the basket has a name: pilot-",
         "induced oscillation. You correct for where you ARE instead of where",
         "you are GOING; the correction arrives after a lag; it overshoots; you",
         "correct harder. Push it far enough and your inputs land 180 degrees",
         "out of phase with the airplane and the oscillation grows instead of",
         "damping. Human reaction time puts the worst band at roughly one",
         "correction a second — which is exactly the rate people correct at",
         "when they are tense.",
         "",
         "That reframes the whole problem. You do not need to be better. You",
         "need LESS GAIN, and there are four levers:",
         "  1. Relax your grip. Tension is gain you did not ask for.",
         "  2. One input, then wait. Waiting is a technique, not hesitation.",
         "  3. Look at the tanker, not the boom or basket. The basket has its",
         "     own oscillation — watching it puts a second oscillator inside",
         "     your control loop. This is not a comfort tip; it is removing a",
         "     noise source.",
         "  4. Curve the axis. That is gain reduction in software.",
         "The F-16 does lever 4 for you in hardware: opening the AR door drops",
         "the flight-control gains. The jet agrees with the diagnosis.",
         "",
         "THE THREE MISTAKES, in the order people make them:",
         " - CHASING. You correct, it overshoots, you correct harder. Stop",
         "   correcting. Freeze the stick, let it settle, then make ONE small",
         "   input.",
         " - STARING. Looking at the boom or the basket makes you fly it.",
         "   Look at the TANKER, wide, the way you look at a lead in formation.",
         " - THROTTLE STEPS. Big handfuls of power arrive late and leave late.",
         "   Think in single percent, and lead the correction.",
         "",
         "IF IT IS NOT WORKING: back out to pre-contact and breathe. Nobody has",
         "ever fixed a bad approach by pressing it. The tanker is not going",
         "anywhere.",
    ]
    if not boom:
        L += ["",
              "PROBE NOTE: a basket that is oscillating is one you drove into.",
              "Give it a few seconds to settle before the next attempt."]
    if raised:
        hi = TERRAIN_MAX_FT.get(map_key, (TERRAIN_MAX_DEFAULT_FT, ""))[0]
        L += ["",
              f"WHY THE TRACK IS HIGH: this map's highest ground is about",
              f"{hi:,} ft, and you start the sortie 1,000 ft BELOW the track.",
              f"The track sits at {alt_ft:,} so the LOW airplane — you —",
              f"still clears it. A refuelling track you can fly into a",
              f"mountain is not a training aid."]
    if short:
        band = RECEIVER_IAS.get(receiver_id, (0, 0))
        L += ["",
              f"THIS TANKER CANNOT FLY YOUR SPEED, and you should know that",
              f"before you blame your hands. This airframe wants about",
              f"{band[0]} KIAS to sit comfortably; a {t['label'].split(' (')[0]}",
              f"tops out around {t.get('max_ias_kt', ias)}. You are refuelling",
              f"{short} knots slow.",
              "",
              "WHAT THAT ACTUALLY FEELS LIKE: you sit higher on the power, the",
              "controls go soft, and small corrections need bigger inputs than",
              "they should. That is the airplane, not you. Fly it, but if a",
              "faster tanker is offered for this receiver, take it."]
    elif ias <= 220:
        L += ["",
              f"SLOW-TANKER NOTE: {ias} KIAS is comfortable for the",
              "tanker and near the low end for a fast jet. Expect to sit high",
              "on the power and be ready for it to feel sloppy."]
    L += [
         "",
         "WHAT GOOD LOOKS LIKE — pass criteria, so you can stop guessing:",
         " - PRE-CONTACT, THE GATE: stabilised with zero closure for 15",
         "   seconds. That is the minimum before you move forward, and it is",
         "   the doctrinal shape of the clearance — stabilised first, then",
         "   cleared. Fifteen seconds is a gate, not a score.",
         " - PRE-CONTACT, THE STANDARD: hold that same position for 60 seconds",
         "   without a correction you did not intend. That is not the gate and",
         "   it is not quoted from anyone — it is OUR proficiency mark, set",
         "   where a pilot who can do it will not be surprised by anything in",
         "   contact.",
         " - CLOSURE, APPROACH: 1 to 3 knots over the tanker. Not 10. At",
         f"   {ias} KIAS that is a needle's width. (One knot is about",
         "   1.7 feet per second, which is the unit the next line is in.)",
         " - CLOSURE, LAST FEW FEET: bleed it to about ONE FOOT PER SECOND —",
         "   roughly half a knot, slower than the approach by a factor of",
         "   three. This is the number people miss: the closure that gets you",
         "   to the position is not the closure that makes the connection.",
         " - IN CONTACT: hold roughly a three-foot box. Small.",
         " - PROGRESSION: from 1-3 second connections, to a plug you can hold,",
         "   to a full transfer. Count them and write the number down.",
         "",
         "HOW LONG THIS TAKES, honestly: about thirty minutes a day for two",
         "weeks. That is the figure the community converges on, and marathon",
         "sessions make it worse, not better. It feels impossible until it",
         "abruptly does not. You are not the exception.",
         "",
         t["note"]]
    return L


def hardware_lines():
    """The hardware page. Separate from the procedure card because it is read
    ONCE, on the ground, and then never again — whereas the procedure card is
    read before every sortie.

    Two things in here are corrections rather than tips. Force feedback has no
    evidence behind it for this task and our own curve advice is wrong for it;
    and VR helps for a narrower reason than people say. Both are stated as
    findings, including the negative one, because "we looked and there is
    nothing" is information."""
    return [
     "=" * 66,
     "AIR REFUELLING — YOUR HARDWARE",
     "=" * 66,
     "Read once, on the ground. Most of what stops people refuelling is set",
     "up out here, not flown in there.",
     "",
     "--- THE THROTTLE MATTERS MORE THAN THE STICK ------------------------",
     "Under-appreciated, and consistent across every source: the bottleneck is",
     "usually throttle RESOLUTION, not stick precision. A separate throttle",
     "unit wins on travel alone — a twist-stick slider cannot give you the",
     "movement range to make a one-percent change.",
     " - Think in taps. 'A slight tap forward', 'half a tap back'.",
     " - On a Warthog-style throttle, tune out the afterburner detent bump",
     "   near 90 % — it is a sensitivity discontinuity in the middle of the",
     "   task.",
     " - Speedbrake moves the engine into a more responsive RPM band. Free",
     "   throttle authority — but it also changes drag and, in some aircraft,",
     "   pitch. Use it where your aircraft's technique supports it. It is not",
     "   a universal beginner trick.",
     " - Expect to add power as fuel transfers. You are getting heavier.",
     "",
     "--- PULSE AND COUNTER-PULSE: HOW THE THROTTLE IS ACTUALLY FLOWN -----",
     "The stick puts you in the right vertical and lateral picture. The",
     "throttle controls the fore/aft TREND, and it is the part almost nobody",
     "is taught.",
     "",
     "First find your BASELINE: the power setting that produces zero fore/aft",
     "drift once you are matched. Everything else is a movement away from it",
     "and back.",
     "  1. Drifting aft? Add a small pulse of power.",
     "  2. BEFORE the closure becomes obvious, take most of it back out.",
     "     That is the counter-pulse, and skipping it is the whole problem.",
     "  3. Watch the new trend. Make the next small correction.",
     "  4. Reverse the pattern for forward drift.",
     "Pilots call it walking the throttle. The goal is NOT a motionless",
     "throttle — it is a series of small, early corrections around a baseline",
     "you know.",
     "",
     "WHY EARLY MATTERS, in numbers: one knot of mismatch is about 1.7 feet",
     "per second. A difference too small to see becomes an aircraft length in",
     "ten seconds, and by the time the drift is obvious the engine lag means",
     "you need a big correction — which then leaves you accelerating the",
     "other way.",
     "",
     "THE FIVE THROTTLE ERRORS:",
     " - Waiting for a large error before correcting.",
     " - Leaving the correction in, so you sail through zero into an",
     "   overshoot.",
     " - Chasing indicated airspeed. The number is a cross-check; relative",
     "   motion against the tanker is the control problem.",
     " - Large alternating movements — fore/aft PIO with the stick perfectly",
     "   steady.",
     " - Freezing a memorised setting during transfer. You are getting",
     "   heavier; the baseline moves.",
     "",
     "THE DRILL, before any contact attempt. From a safe in-trail position:",
     "close 20-30 ft, stop the closure without changing your vertical or",
     "lateral picture, drift aft 20-30 ft, stop that, return to the original",
     "picture. THREE smooth cycles and you are ready for pre-contact. It",
     "teaches engine response and counter-pulsing with nothing at stake.",
     "",
     "ON THROTTLE CURVES: start LINEAR and stay there. Eagle Dynamics'",
     "own controller guidance treats linear as the realistic baseline and",
     "curves as compensation for gaming-hardware limits — and warns that",
     "softening the center amplifies input everywhere else. Add a throttle",
     "curve only if a short throw or a detent genuinely compresses the AAR",
     "power band on YOUR hardware, and never because you copied someone",
     "else's. Throttle length, detents, friction, engine model, tanker speed",
     "and stores all change which part of the axis you are actually using.",
     "",
     "FRICTION: set it so the throttle stays where you released it but still",
     "moves from the fingers without a sticky breakout. Anchor your forearm",
     "or the heel of your hand if the hardware lets you, and move from the",
     "fingers.",
     "",
     "--- FEET OFF THE PEDALS ---------------------------------------------",
     "One instruction, no dissent found anywhere: keep your feet completely",
     "off the rudder pedals at the boom. Unintended yaw is a correction you",
     "did not know you made.",
     "",
     "--- FORCE FEEDBACK: WE LOOKED, AND THERE IS NO EVIDENCE -------------",
     "You would expect a direct-drive FFB base to help — no cam breakout at",
     "center, so micro-inputs should be cleaner. Nobody has written down that",
     "it does. Searching the ED forums, the VPforce documentation and the",
     "review sites turns up long discussions of FFB for helicopters, warbirds",
     "and stall buffet, and essentially nothing on refuelling or formation.",
     "The one thread asking the question directly ended with the community",
     "diagnosing the pilot's TANKER SPEED, not his stick.",
     "",
     "ONE HOLE IN THAT SEARCH, and it is a real one: we could not reach",
     "REDDIT. r/hoggit is one of the largest DCS venues and none of it was",
     "readable from where this was researched. So the honest claim is 'no",
     "evidence in everything we could search', not 'no evidence anywhere'.",
     "If you have seen a good r/hoggit thread on FFB and refuelling, that is",
     "genuinely new information and we would rather know.",
     "",
     "So: if you have one, good. If you are considering buying one to fix",
     "your refuelling, that is not a supported reason.",
     "",
     "BUT IF YOU DO HAVE FFB, ONE THING ON THIS CARD IS WRONG FOR YOU:",
     "the advice to add an axis curve. VPforce's own documentation says",
     "curves and saturation are incompatible with FFB and must be disabled.",
     "The reason is structural — on a spring stick DCS only READS position,",
     "so a curve is a harmless remap; on FFB, DCS also WRITES position to",
     "represent the trim point, and a curve desynchronises the two.",
     "Use these instead:",
     " - SPRING GRADIENT up. More force per degree means a smaller",
     "   displacement for the same hand force. This is the honest substitute",
     "   for a curve.",
     " - DAMPING up. Resistance proportional to how fast you are moving the",
     "   stick — so it suppresses the fast, panicky input and leaves the slow",
     "   deliberate one alone. That is rate-dependent gain reduction, which is",
     "   arguably better than a curve rather than merely different.",
     " - NOT friction, and NOT inertia. Friction adds a breakout you have to",
     "   overcome, which recreates the step-input problem you were escaping.",
     "   Inertia adds lag to reversals, and reversals are the whole task.",
     "   (That last paragraph is reasoning from the effect definitions, not a",
     "   quoted source. Nobody has published AAR-specific FFB settings.)",
     "",
     "FFB TRIM GOTCHA, and it is a real one: your stick physically moves to",
     "the trim point. Trim BEFORE you go to pre-contact, never at the boom —",
     "otherwise the stick relocates under a hand that is trying to hold it",
     "still. Modules with genuine per-module FFB are the F-14, F-4E and",
     "Mirage F1; the F-16 and F/A-18 have little beyond trim.",
     "",
     "--- VR: IT HELPS, BUT NOT WHERE YOU THINK ---------------------------",
     "VR is genuinely better for this, and the mechanism is stereo depth —",
     "which has a range limit worth knowing, because depth resolution falls",
     "off as the SQUARE of distance.",
     "",
     "The US Navy's own simulator requirement asks for accurate depth",
     "judgement between 5 and 100 ft. That is the number to hold on to:",
     " - Inside ~100 ft, stereo is doing real work. At 20 ft it can resolve a",
     "   few centimetres.",
     " - At 1 nm astern it resolves kilometres. It is contributing NOTHING.",
     "Which means: VR does not help you find the tanker or fly the rejoin.",
     "Out there you are using angular size, perspective and closure rate, and",
     "those are all available on a flat screen. VR helps in the last hundred",
     "feet, which happens to be the part that is hard.",
     "",
     "This is not just a sim opinion. The KC-46's Remote Vision System — real",
     "boom operators working from camera displays instead of a window — has",
     "spent a decade failing on exactly this, and a study of stereo displays",
     "for it found that adding stereo and hyper-stereo improved refuelling",
     "performance.",
     "",
     "VR TIPS THAT ARE ACTUALLY SPECIFIC TO VR:",
     " - HOLD YOUR HEAD STILL at contact. Head movement is its own input.",
     "   Flat-screen pilots have been known to switch head tracking OFF for",
     "   the plug; you cannot, so the discipline replaces the switch.",
     " - DO NOT ZOOM at the boom. Zoom changes the projection and corrupts",
     "   the stereo cue you came to VR for. Use it to read the tanker's",
     "   lights, then drop it before you move forward.",
     " - The DCS VR 'IPD' setting is WORLD SCALE, not your eye spacing.",
     "   Community values run 45-55, calibrated by lining your real shoulder",
     "   and elbow up with the virtual pilot's. Worth knowing that a larger",
     "   value is effectively hyper-stereo — the thing that improved the",
     "   KC-46 results. Whether that helps at the boom is UNTESTED; if you",
     "   try it, change one thing at a time.",
     " - Approaching at about 45 degrees off gives better closure perception",
     "   in VR than coming straight up the tail.",
     " - The RIGHT basket is harder, and not because of you: you are looking",
     "   away from the tanker's lights and structure, so your references go.",
     "",
     "SET UP BEFORE YOU FLY, NOT AT THE BOOM:",
     " - Get your headset's PHYSICAL lens spacing right and find the optical",
     "   sweet spot. That is a different setting from the DCS world-scale",
     "   value above, and getting the physical one wrong makes every sight",
     "   picture slightly untrue in a way you will blame on your flying.",
     " - Bind RECENTER VR HEADSET, and recenter sitting naturally with square",
     "   shoulders looking straight ahead. Then set virtual seat height so the",
     "   tanker reference, boom markings or hose pod stay visible without a",
     "   crouch. Use the seat adjustment, not your neck — you cannot hold a",
     "   duck for ten minutes.",
     " - Bind EVERYTHING you need from observation through disconnect. Taking",
     "   a hand off the HOTAS to hunt for the mouse is bad anywhere and much",
     "   worse blind.",
     " - Favor steady frame timing and a clear tanker silhouette over visual",
     "   extras. VR pixel density is expensive, and stuttering at contact is a",
     "   flying problem, not a graphics preference.",
     "",
     "IF A TUTORIAL'S SIGHT PICTURE DOES NOT WORK FOR YOU, do not go straight",
     "to your stick curves. Check the things that actually differ first: your",
     "virtual eye height, fore/aft seat position, which tanker it was, which",
     "hose station, and your headset scale. A picture recorded from a",
     "different viewpoint is not a picture of your problem.",
     "",
     "AND IF TRACKING DROPS, the image stutters, or your eyes start to ache —",
     "back out. Twenty feet from a tanker is the wrong place to troubleshoot a",
     "headset.",
     "",
     "ONE KNOWN DCS DEFECT, so you stop blaming your eyes: the KC-135's",
     "director lights ARE NOT LIGHTS. They are a pre-rendered texture — an ED",
     "beta tester confirmed it and the file is in the KC-135 texture pack. In",
     "VR and on large displays they are hard to read, it has been reported",
     "since 2021, and it is still open. A community texture mod exists that",
     "brightens them. (For what it is worth, a real KC-135 receiver",
     "instructor says they are difficult to see in the airplane too.)",
     "",
     "--- FLAT SCREEN -----------------------------------------------------",
     "Set your field of view GEOMETRICALLY CORRECT before you practice this.",
     "On a flat screen your only closure cue is angular size growth, so a",
     "wrong FOV systematically miscalibrates the one thing you are trying to",
     "judge. Rule of thumb: when your monitor's width equals your viewing",
     "distance, correct FOV is about 60 degrees; scale from there.",
    ]
