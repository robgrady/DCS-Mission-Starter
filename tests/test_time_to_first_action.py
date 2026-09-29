"""Fly Now's promise, as a number the build can check.

Rob: "Fly Now should probably provide the user with instant action. Maybe that
starts in the air."

Measured before this existed (Caucasus, modern, A-10A, seed 42):

    BFM Merge      airborne, bandit 6.1 km    ~25 s     ✅
    Tanker Time    airborne, FL200            ~1 min    ✅
    Kill the Guns  RAMP, target 133 km        ~18 min   ✗
    Beat the SAM   RAMP, ring 104 km          ~13 min   ✗

Two of the four cards quietly kept ramp starts while the other two got air
starts — nothing failed, because nothing measured it. That is the drift this
file exists to stop.

The promise, stated as a property: **every Fly Now card puts you airborne,
within 90 seconds of the action, at your own airplane's cruise speed.** The
speed clause matters — 100 km is two minutes in a Viper and eight in a Warthog,
so a distance-only threshold would pass the fast jets and fail the pilots who
most need the ride to be short.
"""
import math
import os
import tempfile
import zipfile

import pytest

import dcs.lua as lua
from missiongen import Recipe, generate
from missiongen.resolver import load_json

# The four Quick Flight cards, and the aircraft/map they are flown with here.
# The A-10 is deliberate: it is the SLOWEST realistic pick, so it is the worst
# case for a time-based promise. A test that only ever flies an F-16 would pass
# with the ramp starts still in place.
CARDS = ["qf_tanker", "qf_bfm", "qf_guns", "qf_sam"]
CEILING_SECONDS = 90.0


def _templates():
    return {k: v for k, v in load_json("mission_templates").items()
            if not k.startswith("_")}


def _build(card, aircraft="A_10A", mapk="caucasus", era="modern", seed=42):
    """Exactly what the app builds — the template's own recipe block is merged
    server-side now, so the bare recipe is what a share link carries."""
    rc = dict(template=card, map=mapk, era=era, aircraft=aircraft,
              coalition="blue", slots=1, seed=seed)
    out = os.path.join(tempfile.mkdtemp(), f"{card}.miz")
    generate(Recipe.from_dict(rc), out)
    with zipfile.ZipFile(out) as z:
        return lua.loads(z.read("mission").decode())["mission"]


def _player(mission):
    """(x, y, alt_m, speed_kmh, first_route_action) for the player's flight."""
    for coal in mission["coalition"].values():
        if not isinstance(coal, dict):
            continue
        for c in coal.get("country", {}).values():
            for kind in ("plane", "helicopter"):
                for g in c.get(kind, {}).get("group", {}).values():
                    units = list(g["units"].values())
                    if not any(u.get("skill") in ("Player", "Client") for u in units):
                        continue
                    u = units[0]
                    pts = list(g.get("route", {}).get("points", {}).values())
                    p0 = pts[0] if pts else {}
                    return (u["x"], u["y"], u.get("alt") or 0,
                            (p0.get("speed") or 0) * 3.6, p0.get("action"))
    return None


def _nearest_opposing(mission, side="red"):
    """Distance in meters to the closest thing on the other side that a pilot
    would call 'the action' — a vehicle (target/SAM/AAA) or an aircraft."""
    best = None
    for c in mission["coalition"].get(side, {}).get("country", {}).values():
        for kind in ("vehicle", "plane", "helicopter", "ship"):
            for g in c.get(kind, {}).get("group", {}).values():
                for u in g["units"].values():
                    best = (u["x"], u["y"]) if best is None else best
                    yield u["x"], u["y"]


def _time_to_action_seconds(mission):
    p = _player(mission)
    assert p, "no player flight in the mission"
    px, py, alt, kmh, action = p
    reds = list(_nearest_opposing(mission))
    if not reds:
        return None, p
    d = min(math.hypot(px - x, py - y) for x, y in reds)
    kmh = kmh or 400.0
    return d / (kmh * 1000.0 / 3600.0), p


@pytest.mark.parametrize("card", CARDS)
def test_every_fly_now_card_starts_airborne(card):
    """No taxiing on the instant-action screen. 'From Parking Area' — hot or
    cold — is the exact string that meant an 18-minute commute."""
    m = _build(card)
    px, py, alt, kmh, action = _player(m)
    assert action == "Turning Point", f"{card} spawns as {action!r}, not airborne"
    assert alt > 0, f"{card} spawns at {alt} m"


# Not every card means the same thing by "the action", and pretending they do
# produces a wrong test rather than a strict one:
#
#   ARRIVE cards (BFM, Kill the Guns) — you go to the fight, so the property is
#       travel time: <= 90 s at your own cruise.
#   ENGAGED card (Beat the SAM) — the fight comes to YOU. The mission begins
#       when the RWR chirps, which is at spawn. Measuring flight time to the
#       emitter would measure the wrong thing, and "fixing" a failure by moving
#       closer would delete the standoff that IS the exercise. The property is
#       geometry: outside the ring (so the first move is yours), inside about
#       1.5x it (so it is immediate).
#   TANKER card — the objective is friendly; covered by its own test.
ARRIVE_CARDS = ["qf_bfm", "qf_guns"]


@pytest.mark.parametrize("card", ARRIVE_CARDS)
def test_the_action_is_within_ninety_seconds(card):
    m = _build(card)
    secs, (px, py, alt, kmh, action) = _time_to_action_seconds(m)
    assert secs is not None, f"{card}: nothing opposing in the mission at all"
    assert secs <= CEILING_SECONDS, (
        f"{card}: {secs:.0f}s to the nearest threat at {kmh/1.852:.0f} kt — "
        f"the card promises instant action, not a {secs/60:.1f}-minute commute")


@pytest.mark.parametrize("mapk,era", [("caucasus", "modern"), ("syria", "modern")])
def test_beat_the_sam_spawns_just_outside_the_ring(mapk, era):
    """The standoff is sized from the SAM's own envelope, so the card is the
    same exercise whether the map fields an SA-3 (22 km) or an SA-6 (24 km).

    An earlier version measured this from the TARGET and put the spawn 16 km
    from a 22 km SA-3 — already engaged, an ambush rather than a drill."""
    from missiongen.kits import SAM_KITS
    m = _build("qf_sam", mapk=mapk, era=era)
    px, py, alt, kmh, action = _player(m)
    # find the nearest SAM group and the WEZ of the kit it belongs to
    best = None
    for c in m["coalition"].get("red", {}).get("country", {}).values():
        for g in c.get("vehicle", {}).get("group", {}).values():
            name = (g.get("name") or "")
            wez = next((k["wez_m"] for k in SAM_KITS.values()
                        if k.get("label") and name.startswith(k["label"])), None)
            if not wez:
                continue
            for u in g["units"].values():
                d = math.hypot(px - u["x"], py - u["y"])
                if best is None or d < best[0]:
                    best = (d, wez, name)
    assert best, f"{mapk}: the SAM card built no recognisable SAM site"
    d, wez, name = best
    assert d > wez, (
        f"{mapk}: spawned {d/1000:.1f} km from {name} whose envelope is "
        f"{wez/1000:.0f} km — inside the ring is an ambush, not a drill")
    assert d <= wez * 1.5, (
        f"{mapk}: spawned {d/1000:.1f} km from a {wez/1000:.0f} km ring — "
        f"too far out for the RWR to be talking at spawn")


def test_the_tanker_card_spawns_near_its_tanker():
    m = _build("qf_tanker")
    px, py, alt, kmh, action = _player(m)
    tankers = []
    for c in m["coalition"].get("blue", {}).get("country", {}).values():
        for g in c.get("plane", {}).get("group", {}).values():
            name = (g.get("name") or "").upper()
            if "TANKER" in name or "TEXACO" in name or "SHELL" in name or "ARCO" in name:
                for u in g["units"].values():
                    tankers.append((u["x"], u["y"]))
    assert tankers, "the tanker card built no tanker"
    d = min(math.hypot(px - x, py - y) for x, y in tankers)
    secs = d / ((kmh or 400) * 1000.0 / 3600.0)
    assert secs <= 180, f"tanker join-up is {secs/60:.1f} minutes away"


@pytest.mark.parametrize("aircraft,mapk,era", [
    ("A_10A", "caucasus", "modern"),     # slow jet — the worst case
    ("F_16C_50", "caucasus", "modern"),  # fast jet
    ("A_10A", "syria", "modern"),        # a different map's geometry
])
def test_the_promise_holds_across_airframes_and_maps(aircraft, mapk, era):
    """A 90-second ceiling measured only on one jet and one map is a ceiling
    that will be broken by the next map someone adds."""
    for card in ARRIVE_CARDS:
        m = _build(card, aircraft=aircraft, mapk=mapk, era=era)
        secs, (px, py, alt, kmh, action) = _time_to_action_seconds(m)
        assert action == "Turning Point", f"{card}/{aircraft}/{mapk}: ramp start"
        assert secs <= CEILING_SECONDS, \
            f"{card}/{aircraft}/{mapk}: {secs:.0f}s to the action"
    # the SAM card still has to be airborne everywhere, whatever its geometry
    m = _build("qf_sam", aircraft=aircraft, mapk=mapk, era=era)
    assert _player(m)[4] == "Turning Point", f"qf_sam/{aircraft}/{mapk}: ramp start"


def test_spawn_numbers_are_scaled_to_the_airframe():
    """The air start used to be a fixed 4,500 m at 800 km/h for everything —
    a fast-jet number that a warbird cannot fly and an A-10 does not cruise at.
    formation.cruise_for() derives both from the airframe."""
    fast = _player(_build("qf_bfm", aircraft="F_16C_50"))
    slow = _player(_build("qf_bfm", aircraft="A_10A"))
    assert fast[3] > slow[3], (
        f"F-16 spawns at {fast[3]:.0f} km/h and A-10 at {slow[3]:.0f} — "
        f"the spawn speed is not scaled to the airplane")
    assert slow[3] < 500, f"A-10 spawning at {slow[3]:.0f} km/h is a fast-jet number"


def test_the_target_relative_cards_declare_their_geometry():
    """The two new spawn modes are data, not a hidden constant: a future card
    can ask for them by name."""
    tpl = _templates()
    assert tpl["qf_guns"]["air_start"] == "roll_in"
    assert tpl["qf_sam"]["air_start"] == "outside_the_ring"
    from missiongen.builder import StarterBuilder
    assert set(StarterBuilder.AIR_START_ON_TARGET) == {"roll_in", "outside_the_ring"}


def test_an_api_caller_gets_the_same_mission_as_the_ui():
    """The template's recipe block used to be merged only in the browser, so
    POST /api/generate with just a template produced a ramp start. Anything
    that is not our own frontend got a different mission for the same card."""
    r = Recipe.from_dict(dict(template="qf_bfm", map="caucasus", era="modern",
                              aircraft="A_10A", coalition="blue", seed=1))
    assert r.start == "air" and r.bb_bfm is True


def test_an_explicit_choice_still_beats_the_template_default():
    """The merge is DEFAULTS. Someone who deliberately asks for a ramp start —
    or an old share link that encoded one — must still get it."""
    r = Recipe.from_dict(dict(template="qf_bfm", map="caucasus", era="modern",
                              aircraft="A_10A", coalition="blue", seed=1,
                              start="cold"))
    assert r.start == "cold"
