"""The BFM ladder — the picture must be the one the card briefs.

A standards card that says "1.2 nm off your nose, 30 degrees angle off" is a
promise about geometry. If the sim hands the pilot something else, the card is
worse than useless: they will believe it, fly the wrong exercise, and debrief
against numbers that never applied.

This file measures the actual .miz. It exists because the first implementation
was wrong twice, in ways nothing else would have caught:

  1. `m.patrol_flight()` spawns an in-flight patrol 10 km due -x of its first
     orbit point — a fixed offset that ignores heading. The "2 nm abeam"
     neutral merge measured 5.9 nm at 149 degrees off the nose, which means
     every BFM brief this product shipped before v1.66.0 was fiction.
  2. pydcs recomputes a unit's heading on save from the bearing between
     waypoints 0 and 1 unless the group sets `manualHeading`. The player
     spawned pointing at their next waypoint (5.6 degrees when the brief said
     318.9), so "off your nose" was measured from a nose that wasn't there.

Both are the same class of bug: a library default quietly overriding a
deliberate value. Geometry that is briefed must be geometry that is asserted.
"""
import json
import math
import os
import tempfile
import zipfile

import pytest

import dcs.lua as lua
from missiongen import Recipe, generate, bfm
from missiongen.resolver import load_json

TOL_NM = 0.15          # spawn jitter tolerance
TOL_DEG = 12           # aspect tolerance


def _build(setup, aircraft="F_16C_50", mapk="caucasus", era="modern", seed=42):
    tpl = load_json("mission_templates")["qf_bfm"]
    rc = dict(tpl.get("recipe", {}))
    rc.update(template="qf_bfm", map=mapk, era=era, aircraft=aircraft,
              coalition="blue", slots=1, seed=seed, bfm_setup=setup)
    out = os.path.join(tempfile.mkdtemp(), f"bfm_{setup}.miz")
    generate(Recipe.from_dict(rc), out)
    with zipfile.ZipFile(out) as z:
        return lua.loads(z.read("mission").decode())["mission"]


def _picture(mission):
    """What the pilot actually sees at t=0, in the terms the card uses."""
    player = bandit = None
    for coal in mission["coalition"].values():
        if not isinstance(coal, dict):
            continue
        for c in coal.get("country", {}).values():
            for g in c.get("plane", {}).get("group", {}).values():
                units = list(g["units"].values())
                if any(u.get("skill") in ("Player", "Client") for u in units):
                    player = units[0]
                elif "Bandit BFM" in (g.get("name") or ""):
                    bandit = units[0]
    assert player is not None, "no player flight"
    assert bandit is not None, "no BFM bandit"
    dx, dy = bandit["x"] - player["x"], bandit["y"] - player["y"]
    brg = math.degrees(math.atan2(dy, dx)) % 360
    phdg = math.degrees(player.get("heading", 0)) % 360
    bhdg = math.degrees(bandit.get("heading", 0)) % 360
    off = (brg - phdg) % 360
    if off > 180:
        off -= 360
    return {
        "range_nm": math.hypot(dx, dy) / 1852.0,
        "off_nose": off,                       # 0 = ahead, +/-180 = astern
        "aspect": (bhdg - phdg) % 360,         # 0 = co-heading, 180 = head-on
        "alt_delta_m": (bandit.get("alt") or 0) - (player.get("alt") or 0),
    }


def _close(a, b, tol):
    d = abs((a - b + 180) % 360 - 180)
    return d <= tol


# --------------------------------------------------------------- the three rides
def test_offensive_perch_puts_you_on_his_six():
    """The whole point of the ride: he is AHEAD of you and does not yet know."""
    p = _picture(_build("offensive"))
    assert abs(p["range_nm"] - 1.2) <= TOL_NM, p
    assert _close(p["off_nose"], 0, TOL_DEG), f"bandit not off the nose: {p}"
    assert _close(p["aspect"], 30, TOL_DEG), f"angle off is not 30 deg: {p}"


def test_defensive_perch_puts_him_on_yours():
    """The mirror. He is astern, co-heading, slightly high — the picture an
    attacker actually sets up, and one you can only find by checking six."""
    p = _picture(_build("defensive"))
    assert abs(p["range_nm"] - 1.2) <= TOL_NM, p
    assert _close(p["off_nose"], 180, TOL_DEG), f"bandit not astern: {p}"
    assert _close(p["aspect"], 0, TOL_DEG), f"not co-heading: {p}"
    assert p["alt_delta_m"] > 0, "the attacker should start slightly high"


def test_high_aspect_is_nose_to_nose_at_five_miles():
    p = _picture(_build("high_aspect"))
    assert abs(p["range_nm"] - 5.0) <= 0.3, p
    assert _close(p["off_nose"], 0, TOL_DEG), f"bandit not on the nose: {p}"
    assert _close(p["aspect"], 180, TOL_DEG), f"not head-on: {p}"


def test_the_neutral_fight_is_abeam():
    """The legacy card, now measured for the first time — it used to spawn at
    5.9 nm and 149 degrees while briefing '2 nm abeam'."""
    p = _picture(_build("neutral"))
    assert abs(p["range_nm"] - 2.0) <= TOL_NM, p
    assert _close(abs(p["off_nose"]), 90, TOL_DEG), f"not abeam: {p}"


@pytest.mark.parametrize("setup", ["offensive", "defensive", "high_aspect"])
@pytest.mark.parametrize("aircraft,mapk,era", [
    ("F_16C_50", "caucasus", "modern"),
    ("A_10A", "caucasus", "modern"),
    ("F_5E_3", "syria", "coldwar"),
])
def test_the_geometry_holds_across_airframes_maps_and_eras(setup, aircraft, mapk, era):
    """The setups are stated in absolute terms, so they must not drift with the
    airplane, the map's orientation or the era's aircraft pool."""
    spec = bfm.SETUPS[setup]
    p = _picture(_build(setup, aircraft=aircraft, mapk=mapk, era=era))
    assert abs(p["range_nm"] - spec["range_m"] / 1852.0) <= 0.3, (setup, aircraft, mapk, p)
    assert _close(p["off_nose"], spec["bearing_off_nose"], TOL_DEG), (setup, aircraft, mapk, p)
    assert _close(p["aspect"], spec["bandit_heading_off"], TOL_DEG), (setup, aircraft, mapk, p)


@pytest.mark.parametrize("mapk,era,aircraft", [
    ("caucasus", "modern", "F_16C_50"),
    ("syria", "modern", "F_16C_50"),
    ("caucasus", "coldwar", "F_5E_3"),      # period-correct: the era gate is real
])
def test_the_players_stored_heading_is_the_one_the_geometry_used(mapk, era, aircraft):
    """The units bug, pinned.

    pydcs stores unit.heading in DEGREES and converts on save. Writing radians
    produced 5.6 degrees where the geometry had used 318.9 (318.9 deg = 5.566
    rad, written as 5.566 degrees), and every 'off your nose' figure was then
    measured from a nose that did not exist.

    A differential check between two rides does NOT catch this — a constant
    offset cancels, and the first version of this test passed with the fix
    removed. Each theater gives a different absolute heading, so asserting the
    bandit lands on the nose across three of them cannot be satisfied by a
    stuck or mis-scaled value."""
    p = _picture(_build("offensive", aircraft=aircraft, mapk=mapk, era=era))
    assert _close(p["off_nose"], 0, TOL_DEG), (
        f"{mapk}/{era}: bandit {p['off_nose']:.0f} deg off the nose — the "
        f"player's stored heading is not the one the geometry was laid out from")


# ------------------------------------------------------------- the standards card
@pytest.mark.parametrize("setup", ["offensive", "defensive", "high_aspect", "neutral"])
def test_every_ride_briefs_its_own_standards(setup):
    """A generic card on a specific ride is worse than none: the pilot will
    debrief against numbers that did not apply to the sortie they flew."""
    lines = bfm.brief_lines(setup)
    text = "\n".join(lines)
    for section in ("OBJECTIVE", "SETUP", "STANDARDS", "DEBRIEF", "MOVE ON WHEN"):
        assert section in text, f"{setup} card has no {section}"
    assert bfm.SETUPS[setup]["label"] in text
    if setup != "neutral":
        assert "COMMON ERRORS" in text
        assert "CUE:" in text, "an error with no cue is one the pilot cannot notice"


def test_the_cards_differ_from_each_other():
    seen = {s: "\n".join(bfm.brief_lines(s)) for s in
            ("offensive", "defensive", "high_aspect")}
    assert len(set(seen.values())) == 3, "two rides share a standards card"
    assert "six-o'clock" in seen["offensive"] or "six" in seen["offensive"]
    assert "overshoot" in seen["defensive"]
    assert "one-circle" in seen["high_aspect"]


def _briefing_text(setup):
    """DCS stores briefing strings in l10n/DEFAULT/dictionary and references
    them by DictKey — reading descriptionText alone returns the key, not the
    prose, which is exactly how a 'the card is in the brief' test can pass
    while the pilot sees nothing."""
    tpl = load_json("mission_templates")["qf_bfm"]
    rc = dict(tpl.get("recipe", {}))
    rc.update(template="qf_bfm", map="caucasus", era="modern",
              aircraft="F_16C_50", coalition="blue", slots=1, seed=42,
              bfm_setup=setup)
    out = os.path.join(tempfile.mkdtemp(), f"brief_{setup}.miz")
    generate(Recipe.from_dict(rc), out)
    with zipfile.ZipFile(out) as z:
        d = lua.loads(z.read("l10n/DEFAULT/dictionary").decode())["dictionary"]
    return "\n".join(str(v) for v in d.values())


def test_the_card_reaches_the_mission_briefing():
    text = _briefing_text("defensive").upper()
    assert "DEFENSIVE PERCH" in text, "the standards card is not in the briefing"
    assert "OVERSHOOT" in text
    assert "MOVE ON WHEN" in text


def test_the_briefing_matches_the_ride_actually_flown():
    """The failure mode worth guarding: the offensive card printed on a
    defensive sortie. The pilot would fly the wrong exercise and debrief
    against standards that never applied."""
    off = _briefing_text("offensive").upper()
    dfn = _briefing_text("defensive").upper()
    assert "OFFENSIVE PERCH" in off and "DEFENSIVE PERCH" not in off
    assert "DEFENSIVE PERCH" in dfn and "OFFENSIVE PERCH" not in dfn


def test_the_card_does_not_invent_a_corner_speed():
    """Corner velocity is per-type, per-weight, per-fuel. A confidently wrong
    number in a training document is worse than an honest band plus a method,
    and this is the kind of detail that quietly gets 'helpfully' filled in."""
    text = "\n".join(bfm.brief_lines("offensive", aircraft_id="F_16C_50"))
    assert "330 and 400" in text, "the honest band is gone"
    assert "Find it once" in text, "the method for finding your own corner is gone"


# ------------------------------------------------------------------ the recipe
def test_the_rung_is_a_recipe_field_with_a_closed_set():
    """CLOSED, not fixed.

    This asserted set equality against the original four and broke the moment
    six real AETC perches were added — an assertion that fails on correct data
    teaches people to edit assertions. What it actually cares about is that the
    four originals are still selectable (share links) and that an arbitrary
    string is still refused. Both are checked; the size of the set is not."""
    from missiongen.recipe import RECIPE_ENUMS, RecipeError
    assert {"neutral", "offensive", "defensive", "high_aspect"} <= set(
        RECIPE_ENUMS["bfm_setup"]), "an original rung stopped being selectable"
    assert set(RECIPE_ENUMS["bfm_setup"]) <= set(bfm.SETUPS), \
        "the recipe offers a rung the ladder cannot build"
    with pytest.raises(RecipeError):
        Recipe.from_dict(dict(map="caucasus", era="modern", aircraft="F_16C_50",
                              bfm_setup="ace_of_the_base"))


def test_the_default_is_the_plain_fight():
    """Someone who just wants a merge should not have to know the syllabus."""
    r = Recipe.from_dict(dict(map="caucasus", era="modern", aircraft="F_16C_50"))
    assert r.bfm_setup == "neutral"
