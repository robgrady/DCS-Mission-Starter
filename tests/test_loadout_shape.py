"""A loadout has to look like a loadout, not a sample of the weapons rack.

Rob: "one F-4 loadout has one LGB, one fuel tank, an iron bomb and a sidewinder.
That is not a normal loadout for a strike." He was right, and it was structural
rather than random-looking-by-chance.

`derive_loadout` picked PER STATION, independently: each station took the first
class in the role's want-order that it happened to support. Stations do not all
support the same stores, so a jet with varied stations came back with a sampler.
The F-4E strike fit was 3x GBU-24 + 1x Mk-84 + 2x AIM-9 + a pod — three weapon
types, odd counts, asymmetric. Nobody has ever loaded that.

Real fits obey three rules, and these tests are those rules:

  HOMOGENEOUS   one primary weapon, not one of each
  PAIRED        even counts, because a jet is symmetric
  SYMMETRIC     what is on the left is on the right

Fixing it broke it differently first — a mirror axis inferred from min/max of
ALL stations found no pairs on the F-4E (bomb stations 1, 3, 11, 13 out of 1-14)
and the jet came back carrying no bombs at all. `test_the_primary_weapon_is_
actually_carried` is that failure, pinned.
"""
import collections

import pytest

from missiongen import loadouts as LO

# The airframes people fly, and the roles where the shape matters most.
CASES = [(ac, role) for ac in ("F-4E-45MC", "FA-18C_hornet", "F-16C_50",
                               "F-15ESE", "A-10C_2", "AV8BNA", "Su-25T",
                               "F-14B", "MiG-21Bis", "F-5E-3")
         for role in ("strike", "cas", "sead", "a2a")]
IDS = [f"{a}/{r}" for a, r in CASES]

A2A = {"arh", "sarh", "hobs", "ir"}
KIT = {"tank", "pod", "ecm", "other", "practice", "gunpod"}


def _era_for(ac):
    return "coldwar" if ac in ("F-4E-45MC", "MiG-21Bis", "F-5E-3") else "modern"


def _fit(ac, role):
    return LO.player_loadout(ac, role, _era_for(ac))


@pytest.mark.parametrize("ac,role", CASES, ids=IDS)
def test_the_primary_weapon_is_actually_carried(ac, role):
    """The regression from the first attempt at the fix: a symmetry rule strict
    enough to find no valid pairs silently produced a jet with tanks and
    nothing else, which is worse than the mixed load it replaced."""
    fit = _fit(ac, role)
    classes = [LO.store_class(c) for c in fit["pylons"].values()]
    assert classes, f"{ac} {role}: empty fit"
    assert [c for c in classes if c not in KIT], (
        f"{ac} {role} carries no weapon at all — only {sorted(set(classes))}. "
        f"{fit['label']}")


@pytest.mark.parametrize("ac,role", CASES, ids=IDS)
def test_the_fit_is_homogeneous(ac, role):
    """At most TWO weapon types besides self-defense missiles: a primary, and
    optionally a second pair (Mavericks and rockets on a Hog is a real fit).
    Three or more is a sampler."""
    fit = _fit(ac, role)
    kinds = {LO.store_class(c) for c in fit["pylons"].values()}
    primary = kinds - KIT - A2A
    assert len(primary) <= 2, (
        f"{ac} {role} carries {len(primary)} different weapon types "
        f"({sorted(primary)}) — that is a rack sample, not a loadout. "
        f"{fit['label']}")


@pytest.mark.parametrize("ac,role", CASES, ids=IDS)
def test_stores_come_in_pairs(ac, role):
    """A jet is symmetric. An odd number of anything means one wing is heavier
    than the other, which is a real handling problem and looks wrong the moment
    you glance at your own aircraft. One centreline store is the exception."""
    fit = _fit(ac, role)
    counts = collections.Counter(fit["pylons"].values())
    odd = [LO._store_names().get(c, c) for c, n in counts.items()
           if n % 2 and LO.store_class(c) not in KIT]
    assert len(odd) <= 1, (
        f"{ac} {role} hangs an odd number of {odd} — at most one store may sit "
        f"on the centreline. {fit['label']}")


@pytest.mark.parametrize("ac,role", CASES, ids=IDS)
def test_the_same_store_on_every_station_that_carries_it(ac, role):
    """Two variants of the same weapon on one jet — a CBU-87 next to a CBU-103,
    a GBU-54 single next to a GBU-54 triple — is what per-station selection
    produces and what nobody loads."""
    fit = _fit(ac, role)
    by_class = collections.defaultdict(set)
    for c in fit["pylons"].values():
        cls = LO.store_class(c)
        if cls not in KIT:
            by_class[cls].add(c)
    mixed = {k: len(v) for k, v in by_class.items() if len(v) > 1}
    # Self-defense pairs may legitimately differ from the primary A2A store
    # (wingtip rail vs fuselage well take different CLSIDs for one missile).
    mixed = {k: v for k, v in mixed.items() if k not in A2A}
    assert not mixed, (
        f"{ac} {role} carries {mixed} variants of the same weapon class. "
        f"{fit['label']}")


@pytest.mark.parametrize("ac,role", CASES, ids=IDS)
def test_the_jet_is_not_mostly_fuel(ac, role):
    """Filling every remaining station with a bag is what an unbounded loop
    produces. The F-16 came back with three tanks and two bombs."""
    fit = _fit(ac, role)
    tanks = sum(1 for c in fit["pylons"].values()
                if LO.store_class(c) == "tank")
    assert tanks <= 3, f"{ac} {role} carries {tanks} fuel tanks: {fit['label']}"
    weapons = sum(1 for c in fit["pylons"].values()
                  if LO.store_class(c) not in KIT)
    assert tanks <= weapons, (
        f"{ac} {role}: {tanks} tanks against {weapons} weapons. "
        f"{fit['label']}")


def test_the_f4e_strike_fit_specifically():
    """Rob's example, by name. A named failure is diagnosable where a
    parametrized one is a puzzle."""
    fit = _fit("F-4E-45MC", "strike")
    counts = collections.Counter(LO.store_class(c)
                                 for c in fit["pylons"].values())
    bombs = sum(n for c, n in counts.items()
                if c in ("lgb", "jdam", "bomb", "cbu"))
    assert bombs >= 2 and bombs % 2 == 0, \
        f"the Phantom carries {bombs} bombs: {fit['label']}"
    assert counts.get("bomb", 0) == 0 or counts.get("lgb", 0) == 0, \
        f"iron bombs AND laser-guided bombs on one strike fit: {fit['label']}"


def test_a_laser_guided_fit_carries_a_pod():
    """An LGB with nothing to designate it is a very expensive iron bomb."""
    for ac in ("F-4E-45MC", "F-16C_50", "A-10C_2"):
        fit = _fit(ac, "strike" if ac != "A-10C_2" else "cas")
        kinds = {LO.store_class(c) for c in fit["pylons"].values()}
        if kinds & {"lgb", "agm"}:
            assert "pod" in kinds, (
                f"{ac} carries guided weapons and no targeting pod: "
                f"{fit['label']}")


def test_derivation_is_still_deterministic():
    """The selection got a lot more logic. A share link is still a
    byte-for-byte contract."""
    for _ in range(3):
        assert (_fit("F-4E-45MC", "strike")
                == _fit("F-4E-45MC", "strike"))


# --- symmetry, per weapon class ---------------------------------------------

# Equipment, not weapons: a targeting pod has its own station and nobody
# carries two. WEAPONS get no exemption — Rob's rule is symmetric, full stop.
SINGLE_OK = {"pod", "ecm", "other"}


@pytest.mark.parametrize("ac,role", CASES, ids=IDS)
def test_each_weapon_class_sits_on_mirrored_stations(ac, role):
    """Rob downloaded a mission and found the F-4 asymmetric.

    `test_stores_come_in_pairs` checks even COUNTS, which is not the same thing:
    two bombs on stations 3 and 4 are an even count and both on the same wing.
    This checks STATIONS — for each weapon class, the stations carrying it must
    pair up about the aircraft's axis.

    Kit that is genuinely single is exempt: a targeting pod lives on its own
    station and nobody carries two. The Phantom's Pave Spike in the left forward
    Sparrow well is asymmetric on the real airplane too.
    """
    t = LO._plane_type(ac)
    stations = sorted(getattr(t, "pylons", ()) or ())
    fit = _fit(ac, role)
    by_class = collections.defaultdict(list)
    for st, clsid in fit["pylons"].items():
        by_class[LO.store_class(clsid)].append(int(st))

    # DERIVED fits only. The hand-authored AI table is human-reviewed and
    # period-correct — the MiG-21bis's classic 2x R-13M / 2x R-60 / centreline
    # tank is right, and pydcs listing 7 "stations" for a jet with 5 pylons
    # means no axis computed from the data agrees with it. Derivation is what
    # this rule governs, because derivation is what produced the asymmetry.
    node = (LO.table().get(ac) or {}).get(
        LO.KIND_ROLE.get(role, LO.ROLE_CAP)) or {}
    if node:
        pytest.skip(f"{ac} {role} comes from the authored table")
    center = (stations[0] + stations[-1]) / 2.0 if stations else None
    for cls, sts in by_class.items():
        if cls in SINGLE_OK:
            continue
        if len(sts) == 1:
            # A lone store is only ever acceptable on a TRUE centreline. On an
            # airframe with an even station count there is no midpoint station,
            # so nothing may be carried alone at all.
            assert sts[0] == center, (
                f"{ac} {role}: a single {cls} on station {sts[0]}, which is not "
                f"the centreline ({center}). {fit['label']}")
            continue
        pairs = LO._mirror_pairs(sorted(sts), stations)
        paired = {x for a, b in pairs for x in (a, b)}
        assert paired == set(sts), (
            f"{ac} {role}: {cls} on stations {sorted(sts)} does not pair up. "
            f"{fit['label']}")
        assert len(sts) % 2 == 0 or any(a == b for a, b in pairs), (
            f"{ac} {role}: {len(sts)}x {cls} with no centreline station. "
            f"{fit['label']}")


@pytest.mark.parametrize("ac,role", CASES, ids=IDS)
def test_fuel_is_never_hung_on_one_wing(ac, role):
    """The specific asymmetry found while investigating: pass 3 walked the
    stations in order and dropped a bag on whatever was free, so an F-4E
    air-to-air fit flew with one tank on station 1 and nothing opposite. A tank
    is heavy and draggy; one of them on one wing is a jet that flies sideways."""
    t = LO._plane_type(ac)
    stations = sorted(getattr(t, "pylons", ()) or ())
    fit = _fit(ac, role)
    tanks = sorted(int(st) for st, c in fit["pylons"].items()
                   if LO.store_class(c) == "tank")
    if len(tanks) <= 1:
        return                    # none, or a single centreline bag
    pairs = LO._mirror_pairs(tanks, stations)
    assert {x for a, b in pairs for x in (a, b)} == set(tanks), \
        f"{ac} {role}: tanks on {tanks} are not mirrored. {fit['label']}"
