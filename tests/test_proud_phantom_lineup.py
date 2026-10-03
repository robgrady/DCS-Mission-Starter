"""Who is on which side over Sinai, and where the squadron actually took off.

THE BUG ROB FOUND
-----------------
*"Egypt is listed as a Red Force when it's supposed to be blue."*

He was right, and it went further than the label. Sinai's Cold War preset is
the October 1973 order of battle — Israel blue, Egypt red, Cairo West an
Egyptian field. Every Proud Phantom ride asks for `home_airbase: "Cairo West"`,
which is on the wrong side of that preset, and `builder.py` resolved it with

    home = next((a for a in own_fields if a.name == r.home_airbase),
                own_fields[0])          # <-- silent

...so all eleven rides took off from **Hatzor, in Israel**, with the 70th
Tactical Fighter Squadron — USAF — registered as an Israeli unit, while
Cairo West sat on the red side wearing an SA-6, a SHORAD ring and a row of
parked MiG-23s. `tracks.json` sells the track as "flown from the base they
actually deployed to". Nothing warned; the fallback did exactly what it said.

THE FIX, IN TWO PARTS
---------------------
A **lineup** — a named order of battle layered over the era preset. An era says
WHEN, a lineup says WHO, and Sinai's Cold War honestly has two: October 1973,
and July 1980 with the USAF as Egypt's guest at Cairo West. Israel is on
neither side in 1980; the peace treaty of March 1979 is *why* the exercise
happened. Libya — the standing threat after the 1977 border war — is red, and
because it owns no field on this terrain the notional aggressor holds the three
western fields. That is stated in the map data rather than left to inference.

And the silent fallback is now a hard error. Twenty-two template/map/era
combinations named a home field that was not on the player's side when the
check was added. Twenty-one were this bug. The twenty-second was `Nellis AFB`
on Nevada, where the airfield is called `Nellis` — dead for however long.
"""
import sys
from pathlib import Path

import pytest
from missiongen.wk import RADIO_CALLSIGN as _RADIO  # the name the sim says for REX

ROOT = Path(__file__).resolve().parent.parent
for p in (str(ROOT), str(ROOT / "vendor")):
    if p not in sys.path:
        sys.path.insert(0, p)

from missiongen.recipe import Recipe, RecipeError          # noqa: E402
from missiongen.resolver import load_json                  # noqa: E402
from missiongen.templates import effective_recipe          # noqa: E402

LINEUP = load_json("maps")["sinai"]["lineups"]["proud_phantom"]


# --------------------------------------------------------------------------- #
# the order of battle itself
# --------------------------------------------------------------------------- #
def test_egypt_is_the_host_and_holds_cairo_west():
    """The single fact Rob reported. Cairo West is where the squadron lived."""
    assert "Cairo West" in LINEUP["blue_airbases"]
    assert LINEUP["blue_country"] == "USA", \
        "the 70th TFS is USAF — it does not fly under another flag"


def test_israel_is_on_neither_side_in_1980():
    """Proud Phantom happened BECAUSE of the March 1979 peace treaty. Putting
    Israel on red would assert the opposite of the reason for the exercise; the
    1973 preset next door is where that order of battle belongs."""
    assert LINEUP["red_country"] != "Israel"
    assert not [b for b in LINEUP["red_airbases"] + LINEUP["blue_airbases"]
                if b in load_json("maps")["sinai"]["presets"]["coldwar"]
                ["blue_airbases"]], \
        "an Israeli field is being handed to one of the 1980 sides"


def test_the_nineteen_seventy_three_order_of_battle_is_untouched():
    """A lineup ADDS a reading of the map. It does not rewrite the one that was
    already there — a Yom Kippur scenario is legitimate content."""
    p = load_json("maps")["sinai"]["presets"]["coldwar"]
    assert p["blue_country"] == "Israel" and p["red_country"] == "Egypt"
    assert "Cairo West" in p["red_airbases"]


def test_the_lineup_says_out_loud_what_dcs_forced():
    """Libya owns no airfield on Sinai, so the aggressor sits on real Egyptian
    fields in the west. A pilot who reads the map and concludes Alexandria
    changed hands was told nothing to the contrary."""
    note = LINEUP.get("note", "")
    assert "Libya" in note and "no" in note.lower(), note[:200]
    assert LINEUP["red_airbases"], "a mission needs an enemy that owns fields"


# --------------------------------------------------------------------------- #
# every ride that uses it
# --------------------------------------------------------------------------- #
def test_every_white_knights_ride_on_sinai_asks_for_the_lineup():
    """Derived, not listed. A ride added tomorrow that flies from Cairo West
    and forgets this is the bug coming back."""
    tpl = load_json("mission_templates")
    egyptian = set(LINEUP["blue_airbases"])
    missed = []
    for k, v in tpl.items():
        if not isinstance(v, dict) or k.startswith("_"):
            continue
        for era in v.get("eras") or []:
            try:
                rc = effective_recipe(k, era, "sinai")
            except Exception:
                continue
            if rc.get("home_airbase") in egyptian and rc.get("lineup") != "proud_phantom":
                missed.append((k, era, rc.get("home_airbase")))
    assert not missed, missed


def test_no_card_anywhere_names_a_home_field_it_does_not_hold():
    """THE SWEEP THAT FOUND IT. Twenty-two combinations failed this when it was
    written. It is cheap, it is exhaustive, and it is the only reason the
    Nevada one was ever noticed."""
    maps, tpl = load_json("maps"), load_json("mission_templates")
    bad = []
    for k, v in tpl.items():
        if not isinstance(v, dict) or k.startswith("_"):
            continue
        for mk in (v.get("maps") or list(maps)):
            if mk not in maps:
                continue
            for era in v.get("eras") or []:
                if era not in maps[mk]["presets"]:
                    continue
                try:
                    rc = effective_recipe(k, era, mk)
                except Exception:
                    continue
                ha = rc.get("home_airbase")
                if not ha or ha == "CARRIER":
                    continue
                preset = dict(maps[mk]["presets"][era])
                if rc.get("lineup"):
                    preset.update((maps[mk].get("lineups") or {})[rc["lineup"]])
                own = preset[f"{rc.get('coalition', 'blue')}_airbases"]
                if ha not in own:
                    bad.append((k, mk, era, ha))
    assert not bad, bad


# --------------------------------------------------------------------------- #
# the guard that would have caught it on the first build
# --------------------------------------------------------------------------- #
def _rc(**kw):
    base = dict(map="sinai", era="coldwar", aircraft="F_4E_45MC",
                home_airbase="Cairo West", seed=1)
    base.update(kw)
    return base


def test_a_home_field_on_the_other_side_is_a_hard_error():
    """Not a warning, not a relocation. Without the lineup, Cairo West is an
    Egyptian field and asking to take off from it is a contradiction — which is
    what eleven rides were quietly doing."""
    import tempfile
    from missiongen import generate
    from missiongen.builder import EraViolation
    r = Recipe.from_dict(_rc()).validate()
    with pytest.raises(EraViolation) as e:
        generate(r, tempfile.mktemp(suffix=".miz"))
    msg = str(e.value)
    assert "Cairo West" in msg and "other side" in msg, msg
    assert "Hatzor" in msg, "the error does not say what your side actually holds"


def test_a_home_field_that_is_not_on_the_map_is_a_hard_error():
    """The Nevada case: `Nellis AFB` where DCS calls it `Nellis`."""
    import tempfile
    from missiongen import generate
    from missiongen.builder import EraViolation
    r = Recipe.from_dict(_rc(map="nevada", era="coldwar", aircraft="F_100D",
                             home_airbase="Nellis AFB")).validate()
    with pytest.raises(EraViolation) as e:
        generate(r, tempfile.mktemp(suffix=".miz"))
    assert "not an airfield on this map" in str(e.value), str(e.value)


def test_an_unknown_lineup_is_refused_by_name():
    with pytest.raises(RecipeError) as e:
        Recipe.from_dict(_rc(lineup="yom_kippur")).validate()
    assert "proud_phantom" in str(e.value), str(e.value)


def test_a_lineup_cannot_be_dragged_into_the_wrong_era():
    """Proud Phantom is July 1980. Asking for it in a modern mission is a
    question with no answer; answering it silently is exactly how the 1973
    preset came to serve a 1980 exercise."""
    with pytest.raises(RecipeError) as e:
        Recipe.from_dict(_rc(era="modern", lineup="proud_phantom")).validate()
    assert "coldwar" in str(e.value), str(e.value)


# --------------------------------------------------------------------------- #
# ...and the mission that comes out
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def built(tmp_path_factory):
    from missiongen import generate
    rc = effective_recipe("pp_8_bnai_coach", "coldwar", "sinai")
    rc.update(template="pp_8_bnai_coach", aircraft="F_4E_45MC", seed=4408)
    out = tmp_path_factory.mktemp("pp") / "t.miz"
    generate(Recipe.from_dict(rc).validate(), str(out))
    from dcs.mission import Mission
    m = Mission()
    m.load_file(str(out))
    return m


def _flights(m, side):
    for cn, c in m.coalition[side].countries.items():
        for g in c.plane_group:
            yield cn, g


def test_the_squadron_takes_off_from_cairo_west_as_the_usaf(built):
    """READ OUT OF THE .miz. The card, the brief and the voiceover all say
    Cairo West; before this, all three were true and the mission was not."""
    fields = {a.id: a.name for a in built.terrain.airport_list()}
    rex = [(cn, g) for cn, g in _flights(built, "blue")
           if g.name.startswith(_RADIO)]
    assert rex, "the player's flight is not on the blue side"
    for cn, g in rex:
        assert cn == "USA", f"REX is flying as {cn}"
        pts = getattr(g, "points", [])
        aid = pts[0].airdrome_id if pts else None
        assert fields.get(aid) == "Cairo West", \
            f"{g.name} departs {fields.get(aid)!r}"


def test_israel_flies_and_fights_for_nobody(built):
    """NOT "Israel is absent from the coalition" — pydcs seeds a default
    mission with nineteen countries on blue and twelve on red, Israel among
    them, and a name in that list asserts nothing. What the old bug actually
    produced was Israeli GROUPS: `REX 1` and `REX 2`, the 70th TFS, registered
    under Israel and taking off from Hatzor. Units are the measurable thing."""
    for side in ("blue", "red"):
        c = built.coalition[side].countries.get("Israel")
        if c is None:
            continue
        for attr in ("plane_group", "helicopter_group", "vehicle_group",
                     "ship_group", "static_group"):
            gs = [g.name for g in getattr(c, attr, [])]
            assert not gs, f"Israel has {attr} on {side}: {gs[:5]}"


def test_the_threat_is_libyan_and_it_is_not_over_cairo(built):
    """Egypt's own base must not be defended by the enemy — the shape of the
    old bug was an SA-6 ring around the field you were supposed to live on."""
    red = [g.name for _cn, gs in
           ((cn, getattr(c, "vehicle_group", []))
            for cn, c in built.coalition["red"].countries.items())
           for g in gs]
    assert red, "no red air defense at all"
    assert not [n for n in red if "Cairo West" in n], \
        [n for n in red if "Cairo West" in n]
    assert "Libya" in built.coalition["red"].countries, \
        list(built.coalition["red"].countries)


def test_the_brief_never_puts_the_squadron_in_israel(tmp_path):
    """The say/do check, on the document the pilot actually reads."""
    from missiongen import generate
    rc = effective_recipe("pp_1_drag", "coldwar", "sinai")
    rc.update(template="pp_1_drag", aircraft="F_4E_45MC", seed=4401)
    res = generate(Recipe.from_dict(rc).validate(),
                   str(tmp_path / "t.miz"), brief_dir=str(tmp_path))
    md = Path(res["brief_md"]).read_text()
    assert "Cairo West" in md
    for w in ("Israel", "Hatzor", "Tel Nof", "Hatzerim"):
        assert w not in md, f"the brief still mentions {w}"
