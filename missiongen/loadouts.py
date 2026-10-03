"""AI armament: era- and role-correct loadouts for the aircraft we spawn.

WHY THIS MODULE EXISTS
----------------------
pydcs can set a "default loadout" for a task, but it reads the payload `.lua`
files out of a DCS *installation* (`Saved Games/DCS/MissionEditor/UnitPayloads`
and the game's own payload dirs). A server has no DCS install, so
`FlyingType.load_payloads()` returns `{}` for every airframe and
`load_task_default_loadout()` is a silent no-op. The result shipped for a long
time: every CAP flight and every BFM bandit spawned as a CLEAN airframe —
a competent intercept flown by a jet with nothing to shoot.

That cannot be fixed by calling pydcs differently. It is a missing data source,
so we bring our own: `data/loadouts.json`.

WHAT MAKES IT TRUSTWORTHY
-------------------------
pydcs *does* ship the per-airframe, per-pylon legal-store lists that DCS itself
generates (`MiG_21Bis.Pylon1` and friends). Every entry in our table is checked
against those lists by `tests/test_loadouts.py`, so a loadout that DCS would
reject cannot reach a player's cockpit. Era discipline is checked the same way
against `data/weapon_service.json`.

DESIGN
------
The user never picks the enemy's loadout — era and mission type imply it. What
the user *does* get is the fit BRIEFED: knowing the MiG-21 has two R-13Ms and a
gun changes how you fight it, and that is the half a pilot actually notices.
`describe()` turns a resolved loadout into the intel line the brief prints.

The PLAYER's aircraft is armed here too, from the mission kind they picked.
That is new in v1.48.0 and it corrects a long-standing misdescription: the
player's jet spawning clean was written up as "your loadout is yours to set in
the Mission Editor", but it was the same missing payload data that left the
bandits clean, not a decision. Hand-authoring 75 airframes x 7 kinds x 3 eras x
3 weights is not viable, so a player fit is COMPOSED from pydcs's per-pylon
legal-store lists (see derive_loadout) and an authored entry always wins.
It is still yours to change in the Mission Editor, and `player_arm=False`
turns it off.
"""
import functools

from .resolver import load_json

# Roles are what an aircraft is FOR in this engine, not DCS task names.
# The first two arm the AI; the rest arm the PLAYER, chosen from the mission
# kind they picked in the Builder.
ROLE_CAP = "cap"
ROLE_BFM = "bfm"
ROLE_STRIKE = "strike"
ROLE_CAS = "cas"
ROLE_SEAD = "sead"
ROLE_ANTISHIP = "antiship"
ROLE_TRAINING = "training"

# What the Builder's mission kinds ask the player's jet to do. `open` tasking
# gets the air-to-air fit with a bomb or two — the historical "we don't know
# what you'll find" load — rather than a specialist fit for a job nobody named.
KIND_ROLE = {
    "open": ROLE_CAP,
    "a2a": ROLE_CAP,
    "strike": ROLE_STRIKE,
    "cas": ROLE_CAS,
    "sead": ROLE_SEAD,
    "carrier": ROLE_CAP,
    "training": ROLE_TRAINING,
}

# How much the jet carries. This is the whole "loadout" UI: no per-pylon picker,
# because the pylon picker already exists and it is called the Mission Editor.
WEIGHTS = ("light", "standard", "heavy")

# Missiles that can be cued well off the nose. Called out separately because
# the tactical implication genuinely changes: against a boresight-only IR shot
# you can deny the rear quarter and be safe, against these you cannot.
HOBS_CLSIDS = frozenset({
    "{FBC29BFE-3D24-4C64-B81D-941239D12249}",   # R-73 Archer
    "{5CE2FF2A-645A-4197-B48D-8720AC69394F}",   # AIM-9X
})

# Ordered worst-first: the implication line reports the HIGHEST class carried.
_CLASS_ORDER = ("arh", "sarh", "hobs", "ir", "guns")

_IMPLICATION = {
    "arh": "Active radar — fire-and-forget beyond visual range. Assume he "
           "shoots first and plan the defensive turn before the merge.",
    "sarh": "Semi-active radar — he must hold the lock all the way to impact. "
            "Beam or notch him and the shot goes stupid.",
    "hobs": "High-off-boresight IR — he can shoot across the circle without "
            "pointing at you. Do not take this one into the phone booth.",
    "ir": "Short-range IR, boresight only — he has to get his nose on you. "
          "Deny the rear quarter and he has nothing but the gun.",
    "guns": "Guns only. He has to arrive at your six and stay there — "
            "energy and the turn circle decide this one.",
}


# ---------------------------------------------------------------- data access
@functools.lru_cache(maxsize=1)
def table() -> dict:
    """The loadout table, comment keys ('_comment', '_keys'...) stripped."""
    return {k: v for k, v in load_json("loadouts").items()
            if not k.startswith("_")}


@functools.lru_cache(maxsize=1)
def service_windows() -> dict:
    return {k: v for k, v in load_json("weapon_service").items()
            if not k.startswith("_")}


@functools.lru_cache(maxsize=1)
def _service_families() -> tuple:
    """[(designation, window)] longest-first, for matching against store names.

    A single missile has many CLSIDs — the bare store plus every rack variant
    ("AIM-9M", "LAU-7 AIM-9M", "LAU-115 with 1 x LAU-127 AIM-9M ...") — so
    hand-keying windows per CLSID left 105 air-to-air stores unwindowed. With no
    window a store is era-legal forever, which is how a 1959 RS-2US beam-rider
    got selected for a MODERN MiG-21.
    """
    fam = (load_json("weapon_service").get("_families") or {})
    return tuple(sorted(fam.items(), key=lambda kv: -len(kv[0])))


def window_for(clsid: str):
    """Service window for a store: exact CLSID first, then designation family."""
    win = service_windows().get(clsid)
    if win:
        return win
    low = _store_names().get(clsid, "").lower()
    if not low:
        return None
    for designation, w in _service_families():
        if designation.lower() in low:
            return w
    return None


@functools.lru_cache(maxsize=1)
def _store_names() -> dict:
    """CLSID -> display name, for classifying what a loadout actually threatens.

    Two sources, because neither is complete on its own: `Weapons` carries the
    bare stores, while the pylon classes carry the rack-mounted variants (an
    R-3S on an APU-13U-2 has a different CLSID from the bare missile). Built
    once and cached — this walks every pylon class of every airframe we arm.
    """
    idx = {}
    try:
        from dcs.weapons_data import Weapons
        for attr in dir(Weapons):
            if attr.startswith("_"):
                continue
            v = getattr(Weapons, attr)
            if isinstance(v, dict) and "clsid" in v:
                idx.setdefault(v["clsid"], v.get("name", ""))
    except Exception:
        pass
    for type_id in table():
        t = _plane_type(type_id)
        if t is None:
            continue
        for p in getattr(t, "pylons", ()):
            for _clsid, _name in _pylon_stores(t, p).items():
                idx.setdefault(_clsid, _name)
    for ident, stores in load_json("scenario_stores").items():
        if ident.startswith("_"):
            continue
        for store in stores.values():
            idx.setdefault(store["clsid"], store["name"])
    return idx


@functools.lru_cache(maxsize=1)
def _plane_index() -> dict:
    """pydcs aircraft `id` ('MiG-21Bis') -> class. Ids, not python names,
    because that is what the engine has in hand at spawn time."""
    from dcs import planes, helicopters
    idx = {}
    for mod in (planes, helicopters):
        for attr in dir(mod):
            t = getattr(mod, attr, None)
            tid = getattr(t, "id", None)
            if isinstance(tid, str) and hasattr(t, "pylons"):
                idx.setdefault(tid, t)
    return idx


def _plane_type(type_id: str):
    t = _plane_index().get(type_id)
    if t is not None:
        return t
    return _pending_base(type_id)


@functools.lru_cache(maxsize=8)
def _pending_base(type_id: str):
    """Pylon donor for an aircraft pydcs has no class for yet.

    A pending airframe (the F-14B(U)) is registered at runtime as a subclass of
    the released jet it inherits from, so it never appears in `_plane_index()`
    keyed by its own provisional id — and a derived loadout came back EMPTY,
    which on the Tomcat means no Phoenix. It carries the same stores on the same
    stations as its donor, so ask the donor.
    """
    try:
        from .resolver import resolve
        for cfg in load_json("pending_aircraft").values():
            if not isinstance(cfg, dict):
                continue
            if cfg.get("provisional_id") == type_id and cfg.get("inherits"):
                return resolve(cfg["inherits"])
    except Exception:
        pass
    return None


def _pylon_stores(plane_type, pylon: int) -> dict:
    """CLSID -> name for every store DCS permits on this pylon of this jet."""
    cls = getattr(plane_type, f"Pylon{pylon}", None)
    if cls is None:
        return {}
    out = {}
    for attr in dir(cls):
        if attr.startswith("_"):
            continue
        v = getattr(cls, attr, None)
        if (isinstance(v, tuple) and len(v) == 2 and isinstance(v[1], dict)
                and "clsid" in v[1]):
            out[v[1]["clsid"]] = v[1].get("name", "")
    return out


# ------------------------------------------------------------------ selection
def loadout_for(type_id: str, role: str, era: str, intensity=3, *, year=None):
    """Resolve a loadout record. NEVER raises and never blocks a build.

    Resolution order — exact, then progressively looser:
        table[type][role][era]      the era-correct fit
        table[type][role]["*"]      the role default (most airframes: they
                                    only ever appear in one era, because the
                                    threat pools are already era-gated)
        table[type]["cap"][era|*]   A2A fallback, so a new role inherits
                                    something sane instead of flying clean
        None                        clean airframe + a warning in stats

    Threat Dial intensity 1-2 takes the 'light' variant where one is authored:
    the dial should change the character of the fight, not just the count.
    """
    ac = table().get(type_id)
    if not ac:
        return None
    for r in (role, ROLE_CAP):
        node = ac.get(r)
        if not node:
            continue
        entry = node.get(era) or node.get("*")
        if entry:
            try:
                light = int(intensity) <= 2
            except (TypeError, ValueError):
                light = False
            if light and isinstance(entry.get("light"), dict):
                entry = entry["light"]
            fit = {"label": entry.get("label", ""),
                   "pylons": dict(entry.get("pylons") or {})}
            return dated_fit(fit, type_id, year) if year is not None else fit
    return None


# ------------------------------------------------------- derived player fits
# WHY THESE ARE DERIVED AND NOT AUTHORED
# --------------------------------------
# The player can fly 75 airframes across 7 mission kinds, 3 eras and 3 weights.
# Hand-authoring that matrix is not 75 entries, it is thousands, and every one
# would be a chance to hang a store on a station DCS refuses or a weapon on a
# war it postdates. Hand-authoring is the right tool for the sixteen AI threat
# airframes above — a small, fixed, curated set — and the wrong one here.
#
# So the player's fit is COMPOSED from the same source of truth the tests check
# against: pydcs's per-airframe `PylonN` legal-store lists, which DCS itself
# generates. A derived fit cannot be illegal, because the only stores it can
# choose from are the ones the aircraft is allowed to carry on that station.
# Era discipline comes from `weapon_service.json` where a store is listed.
#
# An authored entry always wins. Anything that comes out wrong gets pinned in
# loadouts.json and stays pinned.
#
# DETERMINISM: no rng anywhere in here. A share link is a byte-for-byte
# contract, so selection is by a stable sort on (preference, name, clsid) and
# the same inputs always compose the same fit.

# Wingtip/outboard AAM rails should carry the short-range missile even on a
# strike jet: nobody flies into a war without something to defend with.
_SELF_DEFENSE = ("hobs", "ir")

# How many stations of the primary weapon each weight setting fills. The rest
# take self-defense AAMs, a pod if the jet wants one, and tanks.
_WEIGHT_STATIONS = {"light": 2, "standard": 4, "heavy": 8}

# How many stations may carry air-to-air missiles. Without a cap, pass 1 filled
# every AAM-capable station and a "strike" F-15E came back with eight AMRAAMs
# and two bombs — a jet that has not been sent to do the job the user picked.
# A CAP fit is allowed to fill the airplane; everyone else carries a pair for
# self-defense and spends the rest of the jet on the tasking.
_AAM_STATIONS = {ROLE_CAP: 99, ROLE_BFM: 99}
_AAM_STATIONS_DEFAULT = {"light": 2, "standard": 2, "heavy": 4}


def _era_ok(clsid: str, era: str, year=None) -> bool:
    """A store is era-legal unless its service window says otherwise.

    Unlisted stores pass. That is deliberate: `weapon_service.json` covers the
    air-to-air missiles where anachronism is most visible and most complained
    about, and a missing entry must not silently empty a pylon.
    """
    win = window_for(clsid)
    if not win:
        return True
    if year is not None:
        return (win[0] or 0) <= year <= (win[1] or 9999)
    eras = load_json("eras")
    if era not in eras:
        return True
    e_lo, e_hi = eras[era]["window"]
    w_lo, w_hi = (win[0] or 0), (win[1] or 9999)
    return not (w_lo > e_hi or w_hi < e_lo)


# Air-to-air classes in capability order, for stations that can carry nothing
# else. Used when the role's own preferences don't apply to that station.
_A2A_ORDER = ("arh", "sarh", "hobs", "ir")

# Never counts as "a weapon" when deciding what a station is FOR.
_NOT_WEAPONS = ("tank", "pod", "ecm", "other", "practice")


def _rank(clsid: str, name: str) -> tuple:
    """Stable preference key: the LATEST store of a class wins.

    Sorting on the name alone gets this wrong in both directions — it picks the
    AIM-120B over the AIM-120C because B sorts first, and it would pick the
    AIM-9P over the AIM-9M even though the P is the older missile. The service
    window carries the actual answer, so use the in-service year and fall back
    to the name only when there is no window.
    """
    win = window_for(clsid) or []
    year = -(win[0] or 0) if win else 0
    return (year, name.lower(), clsid)


def _pylon_candidates(plane_type, pylon: int, era: str, year=None) -> dict:
    """{store class: [clsid, ...]} of era-legal stores on this station."""
    out = {}
    for clsid, name in sorted(_pylon_stores(plane_type, pylon).items(),
                              key=lambda kv: _rank(kv[0], kv[1])):
        if not _era_ok(clsid, era, year):
            continue
        out.setdefault(store_class(clsid), []).append(clsid)
    return out


def _rank_index(cand, clsid) -> int:
    """Position of `clsid` in its own candidate list — lower is a later mark,
    because `_pylon_candidates` already sorted by service year."""
    for stores in cand.values():
        for lst in stores.values():
            if clsid in lst:
                return lst.index(clsid)
    return 99


def _mirror_pairs(carriers, stations):
    """[(inner_left, inner_right), ...] station pairs, innermost first.

    pydcs does not publish station GEOMETRY, so true left/right cannot be read
    off the data. The first attempt inferred a mirror axis from min/max of ALL
    stations — but station numbering includes centerline and fuselage points, so
    on the F-4E (stations 1-14, bomb-capable on 1, 3, 11, 13) nothing mirrored
    anything and the jet came back carrying no bombs at all. That is a worse
    answer than the mixed load it replaced.

    Pairing the CARRIER LIST inward from both ends is symmetric by construction
    and needs no geometry: first with last, second with second-last. A lone
    middle station is the centerline and may be loaded on its own.
    """
    cs = sorted(set(carriers))
    pairs = []
    i, j = 0, len(cs) - 1
    while i < j:
        pairs.append((cs[i], cs[j]))
        i += 1
        j -= 1
    if i == j:
        # A lone store is ONLY allowed on a true centerline — the exact
        # midpoint of the station range. On an airframe with an even number of
        # stations there is no such station, and the odd store was being hung
        # on whichever one happened to be nearest the middle: a single tank on
        # F-4E station 7 (of 1-14, midpoint 7.5) is on one side of the aircraft,
        # not down its spine. Rob asked for symmetric, full stop, so when there
        # is no centerline the odd store is simply not carried.
        if stations and cs[i] == (min(stations) + max(stations)) / 2.0:
            pairs.append((cs[i], cs[i]))
    # Innermost first: heavy stores belong on the strong inboard stations, and
    # it keeps the outer rails free for self-defense missiles.
    pairs.sort(key=lambda ab: ab[1] - ab[0])
    return pairs


def derive_loadout(type_id: str, role: str, era: str, weight="standard", *, year=None) -> dict:
    """Compose a fit for `type_id` from what DCS says it can carry.

    Returns {"label": str, "pylons": {station: clsid}} — possibly empty pylons
    for a gun-only airframe, which is a real answer and not a failure.
    """
    t = _plane_type(type_id)
    if t is None:
        return {"label": "", "pylons": {}}
    wants = ROLE_WANTS.get(role) or ROLE_WANTS[ROLE_CAP]
    budget = _WEIGHT_STATIONS.get(weight, _WEIGHT_STATIONS["standard"])

    stations = sorted(getattr(t, "pylons", ()) or ())
    cand = {p: _pylon_candidates(t, p, era, year) for p in stations}

    # Pass 1 — AIR-TO-AIR on the stations that can do nothing else.
    # A station whose only weapons are AAMs is a wingtip rail or a fuselage
    # well; filling it first means a strike fit never spends its centerline on
    # a Sidewinder, and — more importantly — that nobody flies into a war with
    # empty tip rails because the primary weapon used up the budget.
    pylons, used_classes = {}, []
    aam_budget = _AAM_STATIONS.get(
        role, _AAM_STATIONS_DEFAULT.get(weight, 2))
    # Outboard first: on a jet with more AAM stations than the cap allows, the
    # pair that survives should be the wingtip rails, which is where a
    # self-defense missile actually lives.
    # Mirrored PAIRS of rails, outermost first. Taking "the outermost two"
    # picked two stations on the same wing whenever the outer pair was not
    # AAM-only, which is one of the ways an asymmetric jet got out of here.
    rails = [p for p in stations
             if (lambda w: w and all(c in _A2A_ORDER for c in w))(
                 [c for c in cand[p] if c not in _NOT_WEAPONS])]
    if role != ROLE_TRAINING:
        for a, b in reversed(_mirror_pairs(rails, stations)):
            if aam_budget <= 0:
                break
            targets = [a] if a == b else [a, b]
            if any(str(x) in pylons for x in targets):
                continue
            for x in targets:
                for c in list(wants) + list(_A2A_ORDER):
                    if cand[x].get(c):
                        pylons[str(x)] = cand[x][c][0]
                        used_classes.append(c)
                        aam_budget -= 1
                        break

    # Pass 2 — ONE primary weapon, loaded symmetrically.
    #
    # This used to pick per station, independently: each station took the first
    # class in `wants` that it happened to support. Stations do not all support
    # the same things, so the result was a sampler rather than a loadout — an
    # F-4E strike fit came back as three GBU-24s, one Mk-84, two Sidewinders and
    # a pod. Nobody has ever loaded that. Real fits are HOMOGENEOUS (one primary
    # store), SYMMETRIC (left mirrors right) and carried in PAIRS.
    #
    # So: choose one class, then one store within it — the one the most stations
    # can carry, which is by definition the jet's standard fit for that job —
    # and hang it on mirrored pairs of stations.
    def _pick(exclude=()):
        """(class, clsid, [stations]) for the best remaining primary."""
        for c in wants:
            if c in exclude:
                continue
            by_store = {}
            for p in stations:
                if str(p) in pylons:
                    continue
                for clsid in cand[p].get(c, ()):
                    by_store.setdefault(clsid, []).append(p)
            if not by_store:
                continue
            best = max(by_store, key=lambda cl: (len(by_store[cl]),
                                                 -_rank_index(cand, cl), cl))
            if len(by_store[best]) >= 2 or c in ("agm", "ashm", "arm"):
                return c, best, sorted(by_store[best])
        return None, None, []

    primary_class, primary_clsid, carriers = None, None, []
    for c in wants:
        # Count stations per candidate store, so the winner is the store this
        # airframe is actually built around rather than whatever sorted first.
        by_store = {}
        for p in stations:
            if str(p) in pylons:
                continue
            for clsid in cand[p].get(c, ()):
                by_store.setdefault(clsid, []).append(p)
        if not by_store:
            continue
        # Most stations wins; ties break on the store rank (newest mark first),
        # and finally on clsid so this stays deterministic.
        best = max(by_store, key=lambda cl: (len(by_store[cl]),
                                             -_rank_index(cand, cl), cl))
        if len(by_store[best]) >= 2 or c in ("agm", "ashm", "arm"):
            primary_class, primary_clsid = c, best
            carriers = sorted(by_store[best])
            break
        # LAST RESORT: some armament is position-specific, so no single store
        # can reach two stations. A Chinook's door guns are a different CLSID
        # per door, and requiring one store everywhere left it completely
        # unarmed. Take the class and let each station carry its own variant.
        if len(by_store) >= 2:
            primary_class = c
            per_station = {p: cand[p][c][0] for p in stations
                           if cand[p].get(c) and str(p) not in pylons}
            for st, clsid in sorted(per_station.items()):
                if budget <= 0:
                    break
                pylons[str(st)] = clsid
                used_classes.append(c)
                budget -= 1
            break

    def _load(cls_name, clsid, carrier_list):
        nonlocal budget
        for a, b in _mirror_pairs(carrier_list, stations):
            if budget <= 0:
                return
            pair = [x for x in (a, b) if str(x) not in pylons]
            if a == b:
                pair = pair[:1]
            # PAIRS ONLY, except a true centerline. An odd store hung on one
            # wing is an asymmetric jet — a real handling problem, and it looks
            # wrong the moment you glance at your own airplane.
            if len(pair) == 2 or (len(pair) == 1 and a == b):
                for x in pair:
                    pylons[str(x)] = clsid
                    used_classes.append(cls_name)
                    budget -= 1

    if primary_clsid:
        _load(primary_class, primary_clsid, carriers)
        # A SECOND type, if the primary ran out of stations and there is budget
        # left. Real close-air-support fits ARE mixed — Mavericks and rockets —
        # but mixed as pairs of each, never as one of everything.
        if budget > 0:
            c2, cl2, carr2 = _pick(exclude=(primary_class,))
            if cl2:
                _load(c2, cl2, carr2)

    # Pass 3 — a targeting pod if the primary weapon needs one to be usable,
    # then fuel on what is left. A JDAM does not need a pod; a laser-guided
    # bomb is inert without one.
    # Two bags and a centerline is a long-range fit; a tank on every station
    # that will take one is what an empty loop produces, not what anyone loads.
    tanks_left = 3 if weight == "heavy" else 2
    # Every weapon actually loaded, not just the primary. Checking only the
    # primary sent an F-16C out with JDAMs (no pod needed) plus a pair of
    # GBU-24s (very much pod-needed) and nothing to designate them with.
    needs_pod = any(c in ("lgb", "agm") for c in used_classes)
    if needs_pod and not any(
            cand[p].get("pod") for p in stations if str(p) not in pylons):
        needs_pod = False
    # A targeting pod is legitimately a single store — it lives on its own
    # station and nobody carries two. Everything else pairs.
    if needs_pod:
        for p in stations:
            if str(p) not in pylons and cand[p].get("pod"):
                pylons[str(p)] = cand[p]["pod"][0]
                used_classes.append("pod")
                break

    # FUEL IN PAIRS. This loop used to walk the stations in order and fill
    # whatever was free, which is where the asymmetry Rob reported came from:
    # a single bag on station 1 with nothing opposite it. A tank is heavy and
    # draggy, and one of them on one wing is a jet that flies sideways.
    tankable = [p for p in stations
                if str(p) not in pylons and cand[p].get("tank")]
    for a, b in _mirror_pairs(tankable, stations):
        if tanks_left <= 0:
            break
        targets = [a] if a == b else [a, b]
        if any(str(x) in pylons for x in targets) or len(targets) > tanks_left:
            continue
        for x in targets:
            pylons[str(x)] = cand[x]["tank"][0]
            used_classes.append("tank")
            tanks_left -= 1

    return {"label": _label(pylons), "pylons": pylons}


_CLASS_WORDS = {
    "arh": "active-radar AAM", "sarh": "radar AAM", "hobs": "IR AAM",
    "ir": "IR AAM", "arm": "anti-radiation missile", "ashm": "anti-ship missile",
    "agm": "guided air-to-ground missile", "jdam": "GPS-guided bomb",
    "lgb": "laser-guided bomb", "cbu": "cluster bomb", "bomb": "bomb",
    "rocket": "rocket pod", "gunpod": "gun pod", "pod": "targeting pod",
    "tank": "fuel tank", "practice": "practice store", "torpedo": "torpedo",
}


def _label(pylons: dict) -> str:
    """'2x AIM-120C, 2x AIM-9M, 1x fuel tank' — what the brief prints."""
    counts, order = {}, []
    for clsid in pylons.values():
        name = _store_names().get(clsid) or _CLASS_WORDS.get(
            store_class(clsid), "store")
        # Trim DCS's descriptive tail: 'AIM-9M Sidewinder IR AAM' -> 'AIM-9M'.
        short = name.split(" - ")[0].strip()
        if short not in counts:
            order.append(short)
        counts[short] = counts.get(short, 0) + 1
    return ", ".join(f"{counts[n]}x {n}" if counts[n] > 1 else n
                     for n in order)


def dated_fit(fit, type_id, year):
    """Correct known service windows using legal DCS stations, without guessing
    operator availability. Unknown windows remain explicitly uncertified.
    Replacement stays in the same AAM guidance class and has a known window.
    """
    if year is None:
        return fit
    out = {**fit, 'pylons': dict(fit.get('pylons', {}))}
    aircraft = _plane_type(type_id)
    changed = False
    for station, clsid in list(out['pylons'].items()):
        if _era_ok(clsid, '', year):
            continue
        changed = True
        klass = store_class(clsid)
        candidates = _pylon_stores(aircraft, int(station)) if aircraft else {}
        legal = [(c, n) for c, n in candidates.items()
                 if klass in _A2A_ORDER and store_class(c) == klass
                 and window_for(c) and _era_ok(c, '', year)]
        if legal:
            out['pylons'][station] = min(legal, key=lambda cn: _rank(*cn))[0]
        else:
            del out['pylons'][station]
    if changed:
        out['label'] = f'Date-filtered DCS fit ({year}): ' + ', '.join(
            n for _s, n in station_list(out)) if out['pylons'] else f'Date-filtered fit ({year}) — clean'
    return out


def player_loadout(type_id: str, mission_kind: str, era: str,
                   weight="standard", *, year=None) -> dict:
    """The player's fit for the mission they asked for.

    Authored entries win; anything else is derived. Both go through the same
    legality checks in the test suite.
    """
    role = KIND_ROLE.get(mission_kind, ROLE_CAP)
    # Only an EXACT authored role counts. `loadout_for` deliberately falls back
    # to the `cap` entry so a new AI role inherits something sane, but that is
    # wrong here: it handed the F-16C's authored CAP fit to every SEAD, CAS and
    # strike mission, so picking a mission type changed nothing on the sixteen
    # airframes that happen to be in the AI table.
    node = (table().get(type_id) or {}).get(role) or {}
    if node.get(era) or node.get("*"):
        authored = loadout_for(type_id, role, era, year=year)
        if authored and authored.get("pylons"):
            # An entry authored for THIS era is authoritative. A wildcard one is
            # not: the AI table's "*" fits were written for the era each threat
            # pool actually fields the jet in, and the pools are already
            # era-gated, so nobody ever checked them against another decade.
            # The player can fly a MiG-21Bis in the modern era, and the wildcard
            # fit hangs 1974 R-13Ms on it — out of service since 1995.
            if node.get(era) or all(_era_ok(c, era, year)
                                    for c in authored["pylons"].values()):
                return authored

    # Fall back through jobs the airframe CAN do rather than handing back a
    # clean jet. A Mustang asked for SEAD has no anti-radiation anything, but it
    # has rockets and bombs and should fly the CAS fit; a Tomcat asked for CAS
    # should still come back with missiles. Only an airframe that carries
    # nothing at all — the Yak-52, the Christen Eagle, a stock Huey with no
    # pylons — ends up genuinely empty, which is the correct answer for it.
    chain = [role]
    if role in (ROLE_SEAD, ROLE_STRIKE, ROLE_ANTISHIP):
        chain += [ROLE_CAS, ROLE_CAP]
    elif role == ROLE_CAS:
        chain += [ROLE_STRIKE, ROLE_CAP]
    elif role == ROLE_TRAINING:
        chain += [ROLE_CAP, ROLE_CAS]
    else:
        chain += [ROLE_CAS]
    for r in chain:
        fit = derive_loadout(type_id, r, era, weight, year=year)
        if fit.get("pylons"):
            return fit
    return {"label": "", "pylons": {}}


# ------------------------------------------------------------------- applying
def arm(group, type_id: str, role: str, era: str, intensity=3, warnings=None, *, year=None):
    """Load the resolved fit onto every unit in `group`; return its label.

    Returns None (and appends to `warnings`) when the table has no entry —
    the mission still builds, it just builds today's clean airframe. A gap in
    the data must degrade, never explode: a new airframe added to a threat pool
    should not be able to break generation.
    """
    fit = loadout_for(type_id, role, era, intensity, year=year)
    if fit is None:
        if warnings is not None:
            warnings.append(
                f"No loadout authored for {type_id} ({role}, {era}) — that "
                f"flight spawns clean. Add it to missiongen/data/loadouts.json.")
        return None
    return apply_fit(group, fit, type_id, warnings)


def station_list(fit) -> list:
    """[(station, store name), ...] in station order, for the kneeboard.

    Reads the SAME `fit["pylons"]` dict that `apply_fit` hangs on the aircraft,
    so the card cannot describe a jet other than the one you are sitting in.
    Deriving the card from the label string instead would have been a second
    source of truth, and the label is lossy — it collapses "2x" without saying
    which two stations.
    """
    if not fit:
        return []
    names = _store_names()
    out = []
    for pylon_s, clsid in sorted((fit.get("pylons") or {}).items(),
                                 key=lambda kv: int(kv[0])):
        out.append((int(pylon_s),
                    names.get(clsid) or str(clsid)))
    return out


def apply_fit(group, fit, type_id="", warnings=None):
    """Hang a resolved fit on every unit in `group`; return its label."""
    if not fit:
        return None
    for pylon_s, clsid in sorted(fit.get("pylons", {}).items(),
                                 key=lambda kv: int(kv[0])):
        try:
            group.load_pylon((int(pylon_s), {"clsid": clsid}), int(pylon_s))
        except Exception as e:          # illegal station, renamed store...
            if warnings is not None:
                warnings.append(
                    f"{type_id} pylon {pylon_s} rejected {clsid}: {e}")
    return fit.get("label")


# ---------------------------------------------------------------- description
def weapon_class(clsid: str) -> str:
    """'arh' | 'sarh' | 'hobs' | 'ir' | 'tank' | 'other'.

    Classified off the store's own display name, which carries the guidance
    type verbatim ('Active Rdr', 'Semi-Act Rdr', 'IR AAM', 'Infra Red'). Reading
    the game's own words beats a hand-maintained second table that can drift.
    """
    if clsid in HOBS_CLSIDS:
        return "hobs"
    low = _store_names().get(clsid, "").lower()
    if "tank" in low:                          # fuel/slipper/drop tanks
        return "tank"
    if "semi-act laser" in low or "semi-active laser" in low:
        return "other"      # laser-guided AGM; store_class() classes it properly
    if "semi-act" in low or "semi act" in low or "semi-active" in low:
        return "sarh"
    if "active r" in low:          # 'Active Rdr' / 'Active Radar AAM'
        return "arh"
    if "infra red" in low or "ir aam" in low or "ir guided" in low:
        return "ir"
    if "beam-rider" in low or "beam rider" in low:
        return "sarh"
    return "other"


# Air-to-ground and everything else. Kept OUT of `weapon_class` on purpose:
# that function feeds `implication()`, which answers "what can this bandit do to
# me" and whose `_CLASS_ORDER` is deliberately air-to-air only. A bomb is not a
# threat to the player, and folding the two vocabularies together would make the
# ENEMY AIR brief start reasoning about Mavericks.
#
# Same principle as the A2A classifier though: DCS's own store names carry the
# class verbatim ("- 500lb Laser Guided Bomb", "JDAM, 2000lb GPS Guided Bomb",
# "High Speed Anti-Radiation Missile", "UnGd Rkts"), and reading the game's
# words beats a hand-maintained second table that drifts every module update.
# Ordered: the FIRST match wins, so the specific patterns come before the loose
# ones ("Practice Laser Guided Bomb" must land on `practice`, not `lgb`).
_STORE_PATTERNS = (
    ("practice", ("practice bomb", "bdu-33", "bdu-45", "captive", "acmi",
                  "tcts", "dummy", "training round", "trg round", "tgm-")),
    ("other",    ("travel pod", "luggage", "cargo", "baggage",
                  "empty pylon", "empty launcher", "empty mer", "empty ter",
                  "launcher rack (empty)", "sand filter", "ir deflector",
                  "smoke", "grenade", "tald", "aesthetic", "camera",
                  "fire control radar", "data link pod", "data-link pod")),
    ("pod",      ("targeting pod", "fpu-", "recon", "datalink pod", "tgp",
                  "designator", "flir", "litening", "atflir", "sniper",
                  "damocles", "thales", "navigation pod")),
    ("ecm",      ("ecm", "jammer", "jamming", "countermeasure", "chaff",
                  "flare dispenser")),
    ("arm",      ("ld-10", "anti-radiation", "anti radiation", "antiradar",
                  "anti-radar", "harm", "kh-58", "kh-25mp", "kh-31p",
                  "alarm", "armat", "shrike", "standard arm")),
    ("ashm",     ("ashm", "anti-ship", "antiship", "harpoon", "penguin",
                  "kh-35", "kh-41", "exocet", "sea eagle")),
    ("agm",      ("maverick", "agm-", "kh-25", "kh-29", "kh-66", "as-",
                  "vikhr", "ataka", "hellfire", "brimstone", "atgm",
                  "guided weapon", "tv guided", "laser guided missile")),
    ("cbu",      ("cbu", "bomblet", "rockeye", "cluster", "rbk-", "bl-755",
                  "dispenser")),
    ("jdam",     ("jdam", "gps guided", "gbu-31", "gbu-38", "gbu-54",
                  "jsow", "kab-500s")),
    ("lgb",      ("laser guided bomb", "paveway", "gbu-10", "gbu-12",
                  "gbu-16", "gbu-24", "kab-500kr", "kab-1500")),
    ("rocket",   ("ungd rkts", "unguided rocket", "rockets", " rkts",
                  "hydra", "zuni", "s-8", "s-13", "s-24", "s-25", "sneb",
                  "hvar", "rs-82", "launcher lau-", "ub-16", "ub-32", "b-8")),
    ("bomb",     ("gp bomb", "bomb", "mk-8", "mk-1", "fab-", "sc ", "sd ",
                  "chute retarded", "napalm", "incendiary", "ods")),
    ("gunpod",   ("gun pod", "gunpod", "gsh-23", "spprk", "suu-")),
    ("tank",     ("fuel tank", "drop tank", "external tank", "tank")),
)

# Which classes belong on which player role. A CAP jet does not want a Maverick
# and a CAS jet does not want an AMRAAM on every station.
ROLE_WANTS = {
    ROLE_CAP:      ("arh", "sarh", "hobs", "ir"),
    ROLE_BFM:      ("hobs", "ir"),
    ROLE_STRIKE:   ("jdam", "lgb", "agm", "bomb", "cbu"),
    ROLE_CAS:      ("agm", "rocket", "cbu", "lgb", "bomb", "gunpod"),
    ROLE_SEAD:     ("arm", "agm", "cbu"),
    ROLE_ANTISHIP: ("ashm", "agm", "lgb", "bomb"),
    ROLE_TRAINING: ("practice", "rocket", "ir"),
}


# Designation fallback. Some CLSIDs carry the DESCRIPTIVE name ("AIM-7M Sparrow
# Semi-Active Radar") and some carry only the bare designation ("AIM-7M") —
# usually the bare store versus its rack-mounted variant, both of which are real
# CLSIDs on real pylons. The descriptive patterns above miss the bare ones, and
# the miss that matters is the AIM-54 Phoenix: the Tomcat's whole reason for
# existing was classifying as 'other' and would never have been selected.
#
# Checked AFTER the descriptive patterns, so a "Trg Round for Mav D" stays
# practice instead of becoming an AGM.
_DESIGNATION_PATTERNS = (
    ("arh",    ("aim-54", "aim-120", "mica rf", "pl-12", "sd-10", "r-77",
                "meteor")),
    ("sarh",   ("aim-7", "super 530", "s530", "r530f em", "matra super",
                "r-27r", "r-27er", "r-24r", "aspide", "skyflash")),
    ("ir",     ("aim-9", "k-13", "mica ir", "magic ii", "r530f ir", "pl-5",
                "pl-8", "r-27t", "r-27et", "r-24t", "r-60", "r-73", "r-3s",
                "r-55", "r-13m", "python", "shafrir", "atam", "mistral",
                "fim-92", "sidearm")),
    ("torpedo", ("torpedo", "mk46", "mark 46", "yu-6", "g7a", "ltf 5b")),
    ("ashm",   ("rb-04", "rb-15", "kormoran", "c-802", "cm-802", "cm802",
                "yj-12", "yj-83", "c-701")),
    ("agm",    ("kh-101", "kh-555", "kd-20", "kd-63", "cm-400", "spike",
                "hj-12", "akd-10", "gb-6", "ls-6", "type-200a",
                "tgm-65")),
    ("lgb",    ("gbu-27", "gbu-28", "gbu-39", "gbu-43")),
    ("cbu",    ("mk-20", "mak79", "belouga", "dws39", "bkf", "blu-107",
                "bap-100")),
    ("rocket", ("rp-3", "oro-57k", "hf20", "matra type 155", "werfer-granate",
                "s-5m")),
    ("gunpod", ("giat m621", "defa-553", "hmp400", "gpu-5", "m134", "m60",
                "m240", "m3m", "m3p", "kord", "pkt", "pk-3", "guv-",
                "browning", "minigun", "hmg", "gpmg", "mmg", "cannon")),
    ("pod",    ("lantirn", "pavetack", "mercury", "elint", "kopyo",
                "tangazh", "camera", "refuelling", "travel pod",
                "luggage", "sand filter")),
    ("ecm",    ("eclair", "mps-410", "kg-600", "alq-", "smoke", "dipole",
                "smokewinder")),
    ("bomb",   ("mk 84", "mk84", "bdu-50", "gp mk.i")),
    ("practice", ("trg round", "training", "zell booster")),
)


def store_class(clsid: str) -> str:
    """Full store taxonomy: air-to-air classes from `weapon_class`, plus
    'arm' | 'ashm' | 'agm' | 'jdam' | 'lgb' | 'cbu' | 'bomb' | 'rocket' |
    'gunpod' | 'pod' | 'ecm' | 'practice' | 'tank' | 'other'.
    """
    a2a = weapon_class(clsid)
    if a2a not in ("other", "tank"):
        return a2a
    low = _store_names().get(clsid, "").lower()
    if not low:
        return "other"
    for cls, needles in _STORE_PATTERNS:
        if any(n in low for n in needles):
            return cls
    for cls, needles in _DESIGNATION_PATTERNS:
        if any(n in low for n in needles):
            return cls
    return "other"


def implication(clsids) -> str:
    """The one-sentence tactical implication — the half a pilot actually uses.

    Reports the HIGHEST-capability class carried, because that is what sets the
    plan: two R-60s under an R-27ER do not make the fight a knife fight.
    """
    classes = {weapon_class(c) for c in clsids}
    top = next((c for c in _CLASS_ORDER if c in classes), "guns")
    line = _IMPLICATION[top]
    # A radar-missile shooter that ALSO carries high-off-boresight IR is the
    # case where "highest class wins" would mislead: you survive the BVR phase
    # and then die in the turn. Worth the extra clause.
    if top in ("arh", "sarh") and "hobs" in classes:
        line += (" He also carries high-off-boresight IR — surviving to the "
                 "merge is not the same as surviving.")
    return line


def describe(type_id: str, role: str, era: str, intensity=3, count=1, *, year=None) -> dict:
    """Everything the brief needs about one enemy flight, in one record."""
    fit = loadout_for(type_id, role, era, intensity, year=year)
    label = (fit or {}).get("label") or "Fit unknown — assume guns"
    clsids = list((fit or {}).get("pylons", {}).values())
    return {"type": type_id, "count": int(count), "role": role,
            "fit": label, "implication": implication(clsids)}


def summarize(records) -> list:
    """Collapse per-flight records into one row per (type, fit) with a total
    count — a brief that lists 'MiG-29S' three times is a receipt, not intel.
    Insertion order is preserved, so the output is deterministic."""
    out, seen = [], {}
    for rec in records or []:
        key = (rec.get("type"), rec.get("fit"), rec.get("role"))
        if key in seen:
            seen[key]["count"] += int(rec.get("count") or 0)
        else:
            row = dict(rec)
            row["count"] = int(rec.get("count") or 0)
            seen[key] = row
            out.append(row)
    return out


ROLE_TAGS = {ROLE_CAP: "CAP", ROLE_BFM: "merge"}


def brief_lines(records) -> list:
    """[(who, fit, implication)] for the documents.

    The role tag matters: a mission can field the same airframe as both a
    standing CAP and the merge bandit with DIFFERENT fits, and two rows reading
    'MiG-21Bis' twice is a receipt, not intel. One data line and one
    implication line, kept separate — the implication IS the feature, so it
    never gets folded into the fit string.
    """
    lines, said = [], set()
    for row in summarize(records):
        n = row.get("count") or 0
        tag = ROLE_TAGS.get(row.get("role"))
        who = f"{n}× {row['type']}" if n else row["type"]
        imp = row.get("implication") or ""
        # Say each implication ONCE. A CAP MiG-21 and a merge MiG-21 threaten
        # you the same way; printing the identical sentence twice turns intel
        # back into boilerplate, which is how people learn to skip the block.
        if imp in said:
            imp = ""
        else:
            said.add(imp)
        lines.append((f"{who} ({tag})" if tag else who,
                      row.get("fit") or "", imp))
    return lines
