"""The position indicator: a graphic instead of text in a corner nobody reads.

THE DEFECT CLASS: a cue the mission cannot actually measure. The indicator has
two honest axes and one it must never draw, and the difference between "we did
not build lateral yet" and "we drew lateral from a sphere" is the difference
between a training aid and a liar.

THE SECOND: saying the same thing twice. If the graphic and the top-right text
both fire on the same condition, the distraction the graphic exists to remove
is still there, now with a picture next to it.
"""
import re
import zipfile

import pytest

from missiongen import aar_grade, aar_hud, tracks
from missiongen.recipe import Recipe
from missiongen import generate
from missiongen.templates import effective_recipe
from missiongen.resolver import load_json


# --------------------------------------------------------------------------- #
# 1. The art
# --------------------------------------------------------------------------- #
def test_there_is_a_picture_for_every_state():
    assert len(aar_hud.STATES) == 11, aar_hud.STATES
    for s in aar_hud.STATES:
        assert aar_hud.asset(s).is_file(), f"missing art for {s}"


def test_the_art_is_small_enough_to_ride_inside_every_mission():
    """Eleven PNGs go into each graded .miz and eleven missions into each
    track zip. Flat color at 8-bit; if this ever blows up, someone has saved
    them as full-color."""
    total = sum(aar_hud.asset(s).stat().st_size for s in aar_hud.STATES)
    assert total < 250_000, f"{total} bytes of indicator art per mission"


def test_the_nine_position_cells_cover_every_combination():
    cells = set(aar_hud.CELLS)
    assert cells == {(f, v) for f in (-1, 0, 1) for v in (-1, 0, 1)}


# --------------------------------------------------------------------------- #
# 2. The two axes, and the one it refuses
# --------------------------------------------------------------------------- #
def test_the_card_states_which_two_axes_it_shows():
    card = "\n".join(aar_hud.brief_lines())
    assert "FORE/AFT" in card
    assert "your HEIGHT" in card, "the vertical axis is no longer explained"


def test_it_sits_left_at_eye_level_not_under_the_nose():
    """From the cockpit: bottom-center is where the nose is, and a panel under
    your gaze competes with the sight picture. Left-center is where a naval
    aviator's eye already goes for the ball."""
    assert aar_hud.HORZ == "Left"
    assert aar_hud.VERT == "Center"


def test_it_is_about_half_the_size_it_shipped_at():
    """22% was roughly double what it needed to be. Bounds, not a magic number:
    small enough to sit beside the sight picture, large enough to read."""
    assert 6 <= aar_hud.SIZE_PCT <= 12, aar_hud.SIZE_PCT


def test_the_art_is_tall_and_narrow_for_an_edge_placement():
    """A wide card on the left edge eats the canopy. Portrait or it does not
    belong there."""
    from PIL import Image
    for s in aar_hud.STATES:
        w, h = Image.open(aar_hud.asset(s)).size
        assert h > w * 1.4, f"{s} is {w}x{h} — too wide for the left edge"


def test_the_redraw_is_rate_limited():
    """From the cockpit: "it currently flashes too often". Firing only on a
    state change is not the same as firing rarely — a pilot sitting on a band
    boundary crosses it several times a second."""
    assert 3 <= aar_hud.MIN_REDRAW_S <= 6, aar_hud.MIN_REDRAW_S


def test_the_card_says_there_is_no_lateral_cue_and_why():
    """The single most important assertion here. A pilot who assumes the
    graphic would tell them about a lateral error will sit there being wrong
    and trusting it."""
    card = "\n".join(aar_hud.brief_lines())
    assert "DOES NOT SHOW LEFT/RIGHT" in card
    assert "sphere" in card, "the card no longer explains WHY there is no lateral cue"


def test_colour_is_never_the_only_cue():
    """The plan is explicit: pair color with position, label and shape. A
    red/green-only indicator is unreadable for a chunk of the audience and
    invisible on a washed-out VR panel."""
    card = "\n".join(aar_hud.brief_lines())
    assert "Color is never the only cue" in card


def test_the_indicator_bands_are_tighter_than_the_graders():
    """Guidance may lead; a verdict may not. If the indicator's bands were
    wider than the grader's it would say "on speed" while the grade was
    breaking, which is the worst of both."""
    assert aar_hud.FORE_BAND_KT < aar_grade.STABLE_BAND_KT


def test_the_safety_threshold_matches_the_graders_exactly():
    """The picture and the retained spoken warning must never disagree about
    what counts as unsafe."""
    assert aar_hud.UNSAFE_OVERTAKE_KT == aar_grade.UNSAFE_OVERTAKE_KT


def test_the_flag_blocks_do_not_overlap():
    grade_flags = {v for k, v in vars(aar_grade).items()
                   if k.startswith("F_") and isinstance(v, int)}
    hud_flags = set(range(aar_hud.F_ARM, aar_hud.F_ARM + len(aar_hud.STATES)))
    hud_flags.add(aar_hud.F_HUD_OFF)
    assert not (grade_flags & hud_flags), grade_flags & hud_flags
    # and neither may collide with formation.py's
    from missiongen import formation
    assert formation.FORMATION_FLAG not in (grade_flags | hud_flags)


# --------------------------------------------------------------------------- #
# 3. Fading: the qualification ride is silent
# --------------------------------------------------------------------------- #
def test_the_quiet_profile_gets_no_indicator():
    assert "quiet" not in aar_hud.profiles_with_hud()
    assert aar_hud.profiles_with_hud() <= set(aar_grade.PROFILES)


def test_the_indicator_never_raises_when_pydcs_shifts():
    warns = []
    assert aar_hud.attach(None, None, None, "kc135", "station",
                          warnings=warns) is False
    assert warns and "indicator not attached" in warns[0]


def test_a_quiet_ride_returns_false_without_warning():
    """Not attaching because the ride is silent is a DESIGN decision, not a
    failure — it must not produce a warning that reads like a bug."""
    warns = []
    assert aar_hud.attach(None, None, None, "kc135", "quiet",
                          warnings=warns) is False
    assert not warns


# --------------------------------------------------------------------------- #
# 4. What actually lands in the mission
# --------------------------------------------------------------------------- #
def _build(key, era, tmp_path, seed=4400):
    rc = effective_recipe(key, era)
    rc["template"] = key
    rc["seed"] = seed
    r = Recipe.from_dict(rc)
    r.validate()
    out = tmp_path / f"{key}.miz"
    res = generate(r, str(out))
    return out, res


_TPL = {k: v for k, v in load_json("mission_templates").items()
        if not k.startswith("_")}
HUD_RIDES = sorted(k for k, v in _TPL.items()
                   if v.get("aar_grade") in aar_hud.profiles_with_hud())


def test_there_are_rides_with_an_indicator_at_all():
    assert len(HUD_RIDES) >= 14, HUD_RIDES


@pytest.mark.parametrize("key", HUD_RIDES[:4])
def test_a_coached_ride_carries_the_art_and_the_picture_actions(key, tmp_path):
    out, res = _build(key, "modern", tmp_path)
    assert res["stats"].get("aar_hud") is True
    z = zipfile.ZipFile(out)
    pics = [n for n in z.namelist() if "aar_hud_" in n and n.endswith(".png")]
    assert len(pics) == 11, pics
    txt = z.read("mission").decode("utf-8", "replace")
    comments = set(re.findall(r'\["comment"\]\s*=\s*"(AAR HUD[^"]*)"', txt))
    assert "AAR HUD: f0_v0" in comments, comments
    assert "AAR HUD: breakoff" in comments
    assert "AAR HUD: out" in comments
    assert len([c for c in comments if c.startswith("AAR HUD: f")]) == 9


def test_the_qualification_ride_carries_no_indicator(tmp_path):
    """The other half of the guard — proves the test above is testing the
    profile gate and not merely that the module imports."""
    out, res = _build("aar_boom_8_qual", "modern", tmp_path)
    assert res["stats"].get("aar_hud") is False
    z = zipfile.ZipFile(out)
    assert not [n for n in z.namelist() if "aar_hud_" in n]
    assert "AAR HUD" not in z.read("mission").decode("utf-8", "replace")


def test_a_coached_ride_does_not_also_nag_in_the_corner(tmp_path):
    """The whole point. If the graphic is up, the two CONTINUOUS text cues —
    fell-out and overtake — must be gone, or the distraction is still there
    with a picture beside it."""
    out, _ = _build("aar_boom_0_fit", "modern", tmp_path)
    txt = zipfile.ZipFile(out).read("mission").decode("utf-8", "replace")
    assert "AAR grade: unsafe overtake" not in txt, \
        "the closure text still fires alongside the picture"
    # the fell-out trigger stays (it counts excursions) but must carry no message
    i = txt.find('"AAR grade: fell out"')
    assert i > 0
    block = txt[i:i + 2000]
    assert "a_out_text_g" not in block, \
        "the fell-out call still puts text in the corner"


def test_the_discrete_calls_survive(tmp_path):
    """Fading the nagging must not delete the two announcements worth reading.
    A gate you pass and nobody tells you about is not a gate."""
    out, _ = _build("aar_boom_0_fit", "modern", tmp_path)
    txt = zipfile.ZipFile(out).read("mission").decode("utf-8", "replace")
    for c in ("AAR grade: 15 s gate", "AAR grade: 60 s standard",
              "AAR grade: what this ride measures"):
        assert c in txt, c


def test_every_state_trigger_carries_the_redraw_lockout(tmp_path):
    """The rate limit has to be on EVERY state, not just most. One state
    without it is a state that can strobe."""
    out, _ = _build("aar_boom_0_fit", "modern", tmp_path)
    txt = zipfile.ZipFile(out).read("mission").decode("utf-8", "replace")
    # The Lua writes `["comment"]="AAR HUD: ..."` — bracketed, and the split
    # has to match that exactly or this test passes on an empty list, which is
    # the vacuous-guard pattern this codebase keeps producing.
    blocks = txt.split('["comment"]=')
    # Match the STATE triggers by name rather than by prefix — "arm" and
    # "menu toggle" are also AAR HUD triggers and neither draws a picture.
    hud = [b for st in aar_hud.STATES
           for b in blocks if b.startswith(f'"AAR HUD: {st}"')]
    assert len(hud) == len(aar_hud.STATES), len(hud)
    for b in hud:
        assert "c_time_since_flag" in b, "a state can redraw without waiting"
        assert str(aar_hud.F_DRAWN) in b, "the lockout uses the wrong flag"


def test_drawing_restarts_the_lockout_clock(tmp_path):
    """Clear-then-set is what restarts `TimeSinceFlag`. Setting an already-set
    flag does nothing, so an implementation that only sets would lock the
    indicator out after its first draw and never show anything again."""
    out, _ = _build("aar_boom_0_fit", "modern", tmp_path)
    txt = zipfile.ZipFile(out).read("mission").decode("utf-8", "replace")
    i = txt.index("a_out_picture_g")
    block = txt[i:i + 900]
    ci = block.index(f"a_clear_flag({aar_hud.F_DRAWN})")
    si = block.index(f"a_set_flag({aar_hud.F_DRAWN})")
    assert ci < si, "the clock is set before it is cleared — it never restarts"


def test_the_indicator_can_be_switched_off_from_the_cockpit(tmp_path):
    out, _ = _build("aar_boom_0_fit", "modern", tmp_path)
    txt = zipfile.ZipFile(out).read("mission").decode("utf-8", "replace")
    assert "position indicator OFF" in zipfile.ZipFile(out).read(
        "l10n/DEFAULT/dictionary").decode("utf-8", "replace")
    assert str(aar_hud.F_HUD_OFF) in txt


def test_the_brief_explains_the_indicator_on_rides_that_have_one(tmp_path):
    out, _ = _build("aar_probe_2_closure", "modern", tmp_path)
    d = zipfile.ZipFile(out).read("l10n/DEFAULT/dictionary").decode(
        "utf-8", "replace")
    assert "DOES NOT SHOW LEFT/RIGHT" in d


# --------------------------------------------------------------------------- #
# 5. Helper gates — one ride, and only one
# --------------------------------------------------------------------------- #
GATE_RIDES = sorted(k for k, v in _TPL.items() if v.get("aar_gates"))


def test_gates_are_on_the_rendezvous_rides_and_nowhere_else():
    """A path in space is right for the navigation ride and wrong for every
    formation ride — a pilot chasing a floating ring has swapped one thing to
    stare at for another."""
    assert sorted(GATE_RIDES) == ["aar_boom_7_rv", "aar_probe_7_rv"]


@pytest.mark.parametrize("key", GATE_RIDES)
def test_the_rendezvous_ride_actually_places_gates(key, tmp_path):
    out, res = _build(key, "modern", tmp_path, seed=4407)
    assert res["stats"].get("aar_gates") is True
    txt = zipfile.ZipFile(out).read("mission").decode("utf-8", "replace")
    assert txt.count("a_show_helper_gate") >= aar_hud.GATE_COUNT


def test_the_gate_card_says_why_they_are_only_here():
    card = "\n".join(aar_hud.gate_brief_lines())
    assert "THIS RIDE AND NO OTHER" in card
    assert "fly the tanker" in card


@pytest.mark.parametrize("key", ["aar_boom_0_fit", "aar_boom_8_qual"])
def test_a_close_in_ride_places_no_gates(key, tmp_path):
    out, res = _build(key, "modern", tmp_path)
    assert not res["stats"].get("aar_gates")
    txt = zipfile.ZipFile(out).read("mission").decode("utf-8", "replace")
    assert "a_show_helper_gate" not in txt


def test_a_mission_with_an_indicator_can_be_READ_BACK(tmp_path):
    """THE ONE THAT MATTERS MOST, and it nearly shipped broken.

    pydcs stores whatever it is handed straight into the Lua table. Passing an
    Enum member rather than its `.value` wrote `HorzAlignment.Center` — an
    undefined variable — into the mission. The build succeeded, every stat was
    correct, the art was in the zip, and DCS would have refused to open it.

    Generating a file proves nothing about whether it loads. Parsing it back
    does."""
    import dcs
    out, _ = _build("aar_boom_0_fit", "modern", tmp_path)
    m = dcs.Mission()
    m.load_file(str(out))          # raises SyntaxError on undefined variables
    txt = zipfile.ZipFile(out).read("mission").decode("utf-8", "replace")
    assert "HorzAlignment" not in txt, \
        "an enum member was serialized instead of its value"
    assert "VertAlignment" not in txt
    assert "SizeUnits" not in txt


def test_the_rendezvous_ride_can_be_read_back_too(tmp_path):
    """Helper gates are the other unverified serialisation on this ride."""
    import dcs
    out, _ = _build("aar_boom_7_rv", "modern", tmp_path, seed=4407)
    dcs.Mission().load_file(str(out))
