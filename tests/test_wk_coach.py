"""The coached B'NAI.

WHAT CAN GO WRONG HERE, AND THEREFORE WHAT IS ASSERTED

  1. A CUE THAT FIRES SOMEWHERE ELSE. The coaching places trigger zones by
     arithmetic; a wrong sign or a stale leg name puts "PULL UP" eight miles
     from the pull-up point and it still LOOKS like a working mission. Every
     zone is read back out of the built `.miz` and checked against the
     waypoint it is supposed to sit on.
  2. A SEQUENCE THAT WEDGES. One bad pop must not cost the pilot the rest of
     the sortie, because the second run IS the ride. Every phase is checked to
     be reachable from the start of the chain.
  3. A CUE THAT FIRES OUT OF ORDER. "Pickle" arriving on the run-in is the
     worst thing this feature could do.
  4. THE USUAL SAY/DO GAP. The card describes cues, a re-arm and a voice; the
     file must contain the cues and the re-arm, and must not imply the voice
     when there are no WAVs in the build.
  5. A RING IN THE MARGIN. A mistyped card coordinate draws the "you are here"
     ring on white paper, which looks deliberate and teaches the wrong point.
"""
import zipfile

import pytest
from missiongen.wk import RADIO_CALLSIGN as _RADIO  # the name the sim says for REX

from missiongen import wk, wk_coach, wk_route
from missiongen.recipe import Recipe
from missiongen import generate
from missiongen.templates import effective_recipe

RIDE = "pp_8_bnai_coach"
MAP = "sinai"
NM_M = 1852.0
FT_M = 0.3048


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("coach") / "coach.miz"
    rc = effective_recipe(RIDE, "coldwar", MAP)
    rc.update(template=RIDE, seed=7)
    r = Recipe.from_dict(rc)
    r.validate()
    generate(r, str(out))
    return out


def _mission(path):
    import dcs
    m = dcs.Mission()
    m.load_file(str(path))
    return m


def _cues(m):
    return [t for t in m.triggerrules.triggers
            if (t.comment or "").startswith("WK coach: ")
            and t.comment != "WK coach: arm"]


def _zones(m):
    return {z.name: z for z in m.triggers.zones()}


def _card(path):
    return zipfile.ZipFile(path).read(
        "l10n/DEFAULT/dictionary").decode("utf-8", "replace")


# --------------------------------------------------------------------------- #
# 1. The sequence itself
# --------------------------------------------------------------------------- #
def test_there_are_phases_at_all():
    """Every guard below iterates PHASES. If it empties they pass vacuously."""
    assert len(wk_coach.PHASES) >= 10, len(wk_coach.PHASES)
    assert len(set(wk_coach.KEYS)) == len(wk_coach.KEYS), wk_coach.KEYS


def test_every_phase_can_be_reached_from_the_first_one():
    """The wedge check, done on the graph rather than in the airplane.

    Each phase names the phase that must have fired before it. If any of those
    chains does not terminate at a phase with no prerequisite, that phase is
    unreachable and the pilot simply never gets that cue — silently."""
    for key in wk_coach.KEYS:
        seen, cur = [], key
        while cur is not None:
            assert cur not in seen, f"{key}: prerequisite cycle {seen + [cur]}"
            seen.append(cur)
            cur = wk_coach.prereq(cur)
        assert seen[-1] == wk_coach.KEYS[0], (key, seen)


def test_nothing_hangs_off_the_release_because_a_release_can_be_missed():
    """THE REASON `prereq` IS NOT JUST "THE PREVIOUS ENTRY".

    A pop flown shallow does not descend through the release altitude, so the
    release cue never fires. If the pullout — and therefore the egress, and
    therefore the re-arm — hung off it, one bad pass would cost the pilot every
    remaining pass of the sortie. The second run is the whole ride."""
    assert wk_coach.prereq("pullout") == "track"
    assert "release" not in [wk_coach.prereq(k) for k in wk_coach.KEYS]


def test_the_reset_hands_back_the_stages_the_pilot_is_not_asked_to_refly():
    """The re-attack cue says come back round to the IP, so the second pass
    must be armed AT the IP. Resetting to the very beginning would leave the
    pilot flying a coached ride in silence until he re-flew a twenty-mile low
    level he has already flown."""
    assert wk_coach.RESET_TO in wk_coach.KEYS
    i = wk_coach.IDX[wk_coach.RESET_TO]
    assert 0 < i < len(wk_coach.KEYS) - 1, i
    txt = " ".join(p[3] for p in wk_coach.PHASES if p[0] == "reattack")
    assert "IP" in txt, txt


def test_the_pull_up_cue_uses_the_sheet_and_not_the_drawings_4_5_nm():
    """The two numbers on the same page, and the one that governs.

    The B'NAI drawing carries "4.5 NM"; the guide's split-attack section uses
    that same figure for where mutual support ends. Reading it as the pull-up
    distance would fire the cue two and a half miles early."""
    assert wk_coach._pup_ft() == wk.DELIVERIES["lald15"]["pup_ft"]
    assert wk_coach._pup_ft() / 6076.12 < 4.5


# --------------------------------------------------------------------------- #
# 2. The cards
# --------------------------------------------------------------------------- #
def test_every_phase_has_its_own_card_with_its_own_word_on_it():
    """One card per PHASE, not per ring position. Four positions are shared
    between two phases; sharing the CARD would show "TRACK" at the moment the
    pilot is meant to pickle."""
    assert wk_coach.cards_ready(), [k for k in wk_coach.KEYS
                                    if not wk_coach.card_path(k).is_file()]
    paths = {wk_coach.card_path(k) for k in wk_coach.KEYS}
    assert len(paths) == len(wk_coach.KEYS)


@pytest.mark.parametrize("key", wk_coach.KEYS)
def test_the_ring_lands_on_the_drawing_and_not_in_the_margin(key):
    """A mistyped coordinate draws the ring on white paper. That looks
    deliberate, which is what makes it dangerous — it teaches a point that is
    not on the diagram."""
    from PIL import Image
    import importlib.util
    import pathlib
    spec = importlib.util.spec_from_file_location(
        "bwc", pathlib.Path(__file__).resolve().parent.parent
        / "scripts" / "build_wk_coach_cards.py")
    bwc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bwc)

    marker = wk_coach.phase(key)[1]
    (mx, my), _panel = bwc.MARKS[marker]
    with Image.open(bwc.SRC) as im:
        px = im.convert("L").load()
        w, h = im.size
    r = bwc.RING_R
    ink = sum(1 for x in range(max(0, mx - r), min(w, mx + r))
              for y in range(max(0, my - r), min(h, my + r))
              if px[x, y] < 128)
    assert ink >= 25, (key, marker, (mx, my), ink)


def test_the_ring_positions_climb_the_way_the_pop_climbs():
    """INK IS NOT ENOUGH, and this is the guard that says why.

    The page carries a paragraph of body text to the right of the geometry.
    A coordinate typo that lands the ring in that paragraph passes an
    ink-density check with room to spare — the ring is on ink, it is just on
    the wrong ink, sitting over a sentence instead of over the track.

    So the four pop stages are checked as a SHAPE: they run up the page in the
    order the drawing gives them, and they stay in one narrow column, because
    they are four points on one aircraft's track. The target is above all of
    them. A ring that wanders into the prose breaks the column."""
    import importlib.util
    import pathlib
    spec = importlib.util.spec_from_file_location(
        "bwc2", pathlib.Path(__file__).resolve().parent.parent
        / "scripts" / "build_wk_coach_cards.py")
    bwc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bwc)
    xy = {k: v[0] for k, v in bwc.MARKS.items()}

    stages = ["pup", "rollin", "apex", "track"]
    ys = [xy[s][1] for s in stages]
    assert ys == sorted(ys, reverse=True), dict(zip(stages, ys))
    assert xy["pullout"][1] < min(ys), (xy["pullout"], ys)

    xs = [xy[s][0] for s in stages]
    assert max(xs) - min(xs) <= 120, dict(zip(stages, xs))

    # ...and the order being checked is the DRAWING'S order, transcribed off
    # the page, not an order that felt right while placing the rings.
    assert list(wk.ATTACKS["bnai"]["pop_stages"]) == [
        "PUP", "ROLL-IN", "APEX", "TRACK POINT"]


@pytest.mark.parametrize("key", wk_coach.KEYS)
def test_the_directive_is_burned_into_the_card_and_is_legible(key):
    """The card is read in the pop, at a glance, at 30 per cent of window
    width. Assert the band exists and the type in it is actually large — a
    card whose directive silently shrank to fit is a card nobody can read."""
    from PIL import Image
    with Image.open(wk_coach.card_path(key)) as im:
        im = im.convert("L")
        w, h = im.size
        px = im.load()
    band_top = int(h * 0.72)
    # the band is dark, and the type on it is light
    dark = sum(1 for y in range(band_top, h) for x in range(0, w, 3)
               if px[x, y] < 60)
    light = sum(1 for y in range(band_top, h) for x in range(0, w, 3)
                if px[x, y] > 200)
    assert dark > light * 2, (key, dark, light)
    # the tallest run of light pixels in the band is the directive's cap
    # height. Anything under 40 px is not readable at a glance.
    best = 0
    for x in range(0, w, 3):
        run = 0
        for y in range(band_top, h):
            run = run + 1 if px[x, y] > 200 else 0
            best = max(best, run)
    assert best >= 40, (key, best)


# --------------------------------------------------------------------------- #
# 3. Read out of the built mission
# --------------------------------------------------------------------------- #
def test_the_mission_contains_one_trigger_per_condition_set(built):
    m = _mission(built)
    got = sorted(t.comment for t in _cues(m))
    assert len(got) >= len(wk_coach.KEYS), got
    for key in wk_coach.KEYS:
        assert any(c == f"WK coach: {key}" for c in got), (key, got)


def test_every_cue_shows_a_picture_and_prints_its_own_words(built):
    """The say/do gap, at cue scale: a trigger that fires and draws nothing."""
    from dcs import action as A
    m = _mission(built)
    for t in _cues(m):
        key = t.comment.split(": ", 1)[1].split(" (")[0]
        kinds = [type(a).__name__ for a in t.actions]
        assert "PictureToGroup" in kinds, (key, kinds)
        assert "MessageToGroup" in kinds, (key, kinds)
        assert "SetFlag" in kinds, (key, kinds)
    txt = _card(built)
    for key, _mk, directive, call, _after in wk_coach.PHASES:
        assert directive in txt, directive
        assert call[:40] in txt, call[:40]


def test_a_cue_cannot_fire_before_the_one_it_depends_on(built):
    """"Pickle" on the run-in is the worst thing this feature could do. Every
    trigger must test its prerequisite's flag, and its own, so it fires once
    and only after the thing before it."""
    from dcs import condition as C
    m = _mission(built)
    for t in _cues(m):
        key = t.comment.split(": ", 1)[1].split(" (")[0]
        true_flags = {r.flag for r in t.rules if isinstance(r, C.FlagIsTrue)}
        false_flags = {r.flag for r in t.rules if isinstance(r, C.FlagIsFalse)}
        own = wk_coach.F_PHASE + wk_coach.IDX[key]
        assert own in false_flags, (key, false_flags)
        assert wk_coach.F_ARM in true_flags, (key, true_flags)
        pre = wk_coach.prereq(key)
        if pre:
            want = wk_coach.F_PHASE + wk_coach.IDX[pre]
            assert want in true_flags, (key, pre, true_flags)


def test_the_zones_sit_on_the_waypoints_they_are_named_for(built):
    """THE DEFECT A SIGN ERROR PRODUCES. A cue placed by its own copy of the
    offset arithmetic drifts from the flight plan and nothing looks wrong."""
    m = _mission(built)
    z = _zones(m)
    # THE WAYPOINTS THEMSELVES, out of the file — not `leg_positions` called a
    # second time here. Comparing the cue's arithmetic against the same
    # arithmetic proves only that a function is deterministic; what matters is
    # that the zone sits on the point the PILOT will fly to.
    pos = {}
    for co in m.coalition.values():
        for c in co.countries.values():
            for g in c.plane_group:
                if g.name == f"{_RADIO} 1":
                    for p in g.points:
                        if p.name:
                            pos[str(p.name)] = p.position
    assert "IP" in pos, sorted(pos)
    for zone_name, leg in (("WKC LOW LEVEL", "LOW LEVEL"),
                           ("WKC TRAIL", "TRAIL SET"),
                           ("WKC IP", "IP"),
                           ("WKC TARGET AREA", "TARGET"),
                           ("WKC EGRESS", "EGRESS")):
        assert zone_name in z, sorted(z)
        d = z[zone_name].position.distance_to_point(pos[leg])
        assert d < 400, (zone_name, leg, d)


def test_the_pull_up_ring_is_the_sheets_distance_from_the_target(built):
    """Not "near the pull-up waypoint" — the RING, centered on the target at
    the sheet's own pull-up distance, so the cue fires when the RANGE is right
    however the pilot came at it."""
    m = _mission(built)
    z = _zones(m)
    ring = z["WKC PULL-UP RING"]
    want_m = wk_coach._pup_ft() * FT_M
    assert abs(ring.radius - want_m) < 5, (ring.radius, want_m)
    assert ring.position.distance_to_point(z["WKC TARGET AREA"].position) < 5


def test_the_reattack_clears_the_pass_and_rearms_at_the_ip(built):
    """The second run. Without this the ride is a single pass with pictures."""
    from dcs import action as A
    m = _mission(built)
    t = [x for x in _cues(m) if x.comment == "WK coach: reattack"]
    assert len(t) == 1
    cleared = {a.flag for a in t[0].actions if isinstance(a, A.ClearFlag)}
    set_ = {a.flag for a in t[0].actions if isinstance(a, A.SetFlag)}
    every = {wk_coach.F_PHASE + i for i in range(len(wk_coach.KEYS))}
    assert cleared == every, sorted(every - cleared)
    handed_back = {wk_coach.F_PHASE + i
                   for i in range(wk_coach.IDX[wk_coach.RESET_TO])}
    # its OWN flag must be among the cleared and not among the handed back, or
    # `TimeSinceFlag` stays true and the chain free-runs.
    own = wk_coach.F_PHASE + wk_coach.IDX["reattack"]
    assert own in cleared and own not in handed_back
    assert set_ - {own} == handed_back, (sorted(set_), sorted(handed_back))


def test_the_coached_route_approaches_the_ip_from_the_side(built):
    """The guide: "approach the IP at nearly 90 degrees angle off". The check
    ride leaves that to the pilot; a COACHED ride whose flight plan runs
    straight through the IP while a cue says "turn inbound" is a cue arguing
    with the route it fires on."""
    import math
    legs = {n: (along, across)
            for n, along, across, _a, _i in wk_route.legs_for(RIDE, MAP)}
    a_along, a_across = legs["TRAIL SET"]
    b_along, b_across = legs["IP"]
    ang = abs(math.degrees(math.atan2(a_across - b_across,
                                      b_along - a_along)))
    assert 70 <= ang <= 100, ang
    # ...and the un-coached check ride deliberately does NOT do this, or the
    # two rides would not differ in the way the cards say they differ.
    plain = {n: (along, across)
             for n, along, across, _a, _i in wk_route.legs_for("pp_8_bnai",
                                                               MAP)}
    assert plain["IP"][1] == 0 and plain["SPLIT POINT"][1] == 0


def test_the_coaching_did_not_cost_the_ride_its_wingman(built):
    """The coaching must not have cost the ride its second airplane — who
    since v1.85.0 is seat two of the player's own flight, not a second
    group. The trail the card prints is his to be SENT into, so the numbers
    stay asserted at the source table that prints them."""
    m = _mission(built)
    rex = [g for co in m.coalition.values()
           for c in co.countries.values() for g in c.plane_group
           if g.name.startswith(_RADIO)]
    assert len(rex) == 1 and len(rex[0].units) == 2, \
        [(g.name, len(g.units)) for g in rex]
    legs = wk_route.legs_for(RIDE, MAP)
    cp = wk_route.counterpart_legs(RIDE, MAP)
    lo, hi = wk.ATTACKS["bnai"]["trail_nm"]
    trail = legs[1][1] - cp[1][1]
    assert lo <= trail <= hi, trail


# --------------------------------------------------------------------------- #
# 4. What the card says about it
# --------------------------------------------------------------------------- #
def test_the_card_does_not_claim_a_voice_this_build_does_not_have(built):
    """Rob records the lines. Until a WAV lands, the card must say so — a
    ride that implies audio it cannot play is the say/do gap with a
    microphone."""
    txt = _card(built)
    n = sum(1 for k in wk_coach.KEYS if wk_coach.has_audio(k))
    if n == 0:
        assert "VOICE: not in this build" in txt
    elif n < len(wk_coach.KEYS):
        assert f"VOICE: {n} of {len(wk_coach.KEYS)} lines recorded" in txt
    else:
        assert "VOICE" not in txt or "not in this build" not in txt


def test_a_missing_wav_costs_one_line_and_nothing_else(built):
    """The degradation contract. Assert it on the ACTIONS rather than on the
    prose: with no audio present, no cue carries a sound action, and every cue
    still carries its picture."""
    from dcs import action as A
    m = _mission(built)
    for t in _cues(m):
        key = t.comment.split(": ", 1)[1].split(" (")[0]
        has_snd = any(isinstance(a, A.SoundToGroup) for a in t.actions)
        assert has_snd == wk_coach.has_audio(key), key
        assert any(isinstance(a, A.PictureToGroup) for a in t.actions), key


def test_the_card_states_the_limit_of_what_a_trigger_can_see(built):
    """A metronome that implies it is a grader is a training aid the pilot
    will trust at exactly the wrong moment."""
    txt = _card(built)
    for phrase in ("cannot see your dive angle",
                   "position, your altitude and",
                   "not a grader"):
        assert phrase in txt, phrase


def test_the_two_bnai_rides_are_the_same_attack_and_say_so(built):
    """Ride 8 teaches it, ride 9 tests it. If they diverged in geometry the
    second would not be a test of the first."""
    assert wk.RIDES["pp_8_bnai_coach"]["attack"] == "bnai"
    assert wk.RIDES["pp_8_bnai"]["attack"] == "bnai"
    assert wk.RIDES["pp_8_bnai_coach"]["n"] + 1 == wk.RIDES["pp_8_bnai"]["n"]
    assert wk.RIDES["pp_8_bnai_coach"].get("coach") is True
    assert not wk.RIDES["pp_8_bnai"].get("coach")
    txt = _card(built)
    assert "Ride 9 is this same attack with nothing talking to you" in txt


def test_only_the_coached_ride_gets_coached(tmp_path):
    """The blast radius. `attach` keys off the ride's own `coach` flag, so
    every other ride in the product must come out with no cue triggers."""
    for key in ("pp_8_bnai", "pp_9_split", "wk_4_lineabreast"):
        rc = effective_recipe(key, "coldwar", (wk.maps_for(key) or ["sinai"])[0])
        rc.update(template=key, seed=3)
        r = Recipe.from_dict(rc)
        r.validate()
        out = tmp_path / f"{key}.miz"
        generate(r, str(out))
        m = _mission(out)
        assert not _cues(m), (key, [t.comment for t in _cues(m)])
        assert not [z for z in m.triggers.zones()
                    if z.name.startswith("WKC ")], key


# --------------------------------------------------------------------------- #
# 5. The recording sheet
# --------------------------------------------------------------------------- #
def test_the_recording_sheet_asks_for_the_filenames_the_mission_looks_for():
    """A hand-kept sheet is a second list of filenames, and the failure is
    silent: you record thirteen takes, name one the way the sheet says instead
    of the way the code says, and that cue is quiet with nothing to say why."""
    import pathlib
    p = (pathlib.Path(__file__).resolve().parent.parent / "docs"
         / "WK_BNAI_VOICEOVER.md")
    assert p.is_file(), p
    txt = p.read_text(encoding="utf-8")
    for key in wk_coach.KEYS:
        # BACKTICKED, not a bare substring. `audio_path` renaming
        # wk_bnai_lowlevel.wav to lowlevel.wav leaves the new name a SUBSTRING
        # of the old one, so a plain `in` check stays green while the sheet
        # asks for thirteen files the mission no longer looks for. The sheet
        # renders every filename in code ticks, so the ticks are the boundary.
        assert f"`{wk_coach.audio_path(key).name}`" in txt, key


# --------------------------------------------------------------------------- #
# 6. The brief, and the hold
# --------------------------------------------------------------------------- #
def _brief_triggers(m, kind=""):
    return [t for t in m.triggerrules.triggers
            if (t.comment or "").startswith(f"WK brief: {kind}")]


def test_there_are_six_brief_pages_and_they_are_distinct():
    from missiongen import wk_brief
    assert len(wk_brief.PAGES) == 6, len(wk_brief.PAGES)
    assert len(set(wk_brief.KEYS)) == 6, wk_brief.KEYS
    assert wk_brief.pages_ready(), [k for k in wk_brief.KEYS
                                    if not wk_brief.page_path(k).is_file()]


def test_the_brief_restates_no_number_of_its_own():
    """A FOURTH PLACE FOR THE POP NUMBERS TO BE WRONG.

    The brief is prose about figures that already live in `wk`. If it carried
    its own copy, a corrected delivery sheet would fix the kneeboard and the
    cue card and quietly leave the spoken brief saying the old number — and
    the pilot would hear it before he ever read the card. So the page text is
    asserted to CONTAIN the live values, which is only true while it is
    formatting them rather than reciting them."""
    from missiongen import wk_brief
    d = wk.DELIVERIES["lald15"]
    text = " ".join(p[3] for p in wk_brief.pages())
    for n in (d["pup_ft"], d["pdp_ft"], d["apex_ft"], d["release_ft"]):
        assert f"{n:,}" in text, n
    assert wk.COMMANDER in text
    assert wk.ATTACKS["bnai"]["definition"][:40] in text


def test_the_pilot_is_locked_in_before_page_one_and_freed_exactly_once(built):
    """THE HOLD. Locked once, released once, and the release is on the page
    that says it is. Two unlocks would mean a path where he gets the airplane
    back early; zero would mean a mission he can never fly."""
    from dcs import action as A
    m = _mission(built)
    locks, unlocks = [], []
    for t in m.triggerrules.triggers:
        for a in t.actions:
            if isinstance(a, A.StartPlayerSeatLock):
                locks.append(t.comment)
            if isinstance(a, A.StopPlayerSeatLock):
                unlocks.append(t.comment)
    assert locks == ["WK brief: hold and page 1"], locks
    assert unlocks == ["WK brief: next from 6"], unlocks


def test_the_coaching_cannot_arm_until_the_brief_hands_over(built):
    """The ordering defect this pairing creates. `wk_coach` used to arm on a
    ten-second timer; with a brief in front of it that timer expires while the
    pilot is on page two and the first cue fires before he has been told what
    a cue is."""
    from dcs import action as A
    from missiongen import wk_brief, wk_coach
    m = _mission(built)
    assert not [t for t in m.triggerrules.triggers
                if (t.comment or "") == "WK coach: arm"], \
        "the coaching still arms itself on a timer"
    setters = [t.comment for t in m.triggerrules.triggers
               for a in t.actions
               if isinstance(a, A.SetFlag) and a.flag == wk_coach.F_ARM]
    assert setters == ["WK brief: next from 6"], setters
    done = [t.comment for t in m.triggerrules.triggers for a in t.actions
            if isinstance(a, A.SetFlag) and a.flag == wk_brief.F_DONE]
    assert done == ["WK brief: next from 6"], done


def test_every_page_waits_for_the_pilot_rather_than_a_timer(built):
    """"Until they finish reading" is the requirement. A page that advanced on
    a timer would be a slideshow, and the pilot who looked away would be
    holding a locked stick with no idea why."""
    from dcs import action as A
    from missiongen import wk_brief
    m = _mission(built)
    waits = [a for t in m.triggerrules.triggers for a in t.actions
             if isinstance(a, A.StartWaitUserResponse)]
    # one per page shown: the opener, five forward shows, and six back shows
    assert len(waits) == 1 + (len(wk_brief.PAGES) - 1) + len(wk_brief.PAGES)
    pairs = {(a.flag, a.flag_back) for a in waits}
    want = {(wk_brief.F_CONT + i, wk_brief.F_BACK + i)
            for i in range(len(wk_brief.PAGES))}
    assert pairs == want, sorted(pairs ^ want)


def test_every_branch_closes_the_wait_and_clears_both_flag_blocks(built):
    """THE DOCUMENTED FOOTGUN, asserted.

    From the Mission Editor forum thread on this action: taking the BACK
    branch leaves the CONTINUE flag set, so one page later two branches can
    fire at once. Clearing only the flag that fired is exactly the mistake."""
    from dcs import action as A
    from missiongen import wk_brief
    m = _mission(built)
    branches = [t for t in m.triggerrules.triggers
                if (t.comment or "").startswith("WK brief: ")
                and "page 1" not in (t.comment or "")]
    assert len(branches) == 2 * len(wk_brief.PAGES), len(branches)
    every = {wk_brief.F_CONT + i for i in range(len(wk_brief.PAGES))} | \
            {wk_brief.F_BACK + i for i in range(len(wk_brief.PAGES))}
    for t in branches:
        assert isinstance(t.actions[0], A.StopWaitUserResponse), t.comment
        cleared = {a.flag for a in t.actions if isinstance(a, A.ClearFlag)}
        assert cleared == every, (t.comment, sorted(every - cleared))


def test_backspace_on_page_one_reshows_page_one(built):
    """A key that appears to do nothing reads as a broken mission. There is no
    page zero, so the first page's back branch shows the first page again."""
    from dcs import action as A
    from missiongen import wk_brief
    m = _mission(built)
    t = [x for x in m.triggerrules.triggers
         if (x.comment or "") == "WK brief: back from 1"][0]
    waits = [a for a in t.actions if isinstance(a, A.StartWaitUserResponse)]
    assert len(waits) == 1
    assert waits[0].flag == wk_brief.F_CONT + 0, waits[0].flag


def test_the_card_is_honest_about_what_the_hold_actually_holds(built):
    """Rob asked for active pause. A mission cannot press it — it is a client
    keybind and there is no ME action for it. What we CAN do is take the
    controls away, and the difference has to be on the card or the pilot will
    assume the world is frozen and it is not."""
    txt = _card(built)
    assert "YOUR CONTROLS ARE LOCKED" in txt
    assert "CANNOT DO IS PRESS ACTIVE PAUSE" in txt
    assert "LWin+Pause" in txt
    assert "SPACE goes forward" in txt and "BACKSPACE" in txt


def test_no_action_in_the_product_claims_to_pause_the_simulation():
    """The guard against somebody 'fixing' this later with something that does
    not exist. If pydcs ever gains a real pause action this test fails and the
    honest paragraph on the card gets revisited — which is the right outcome
    either way."""
    from dcs import action as A
    names = [n for n in dir(A) if n[0].isupper()]
    assert not [n for n in names
                if "pause" in n.lower() or "activepause" in n.lower()], names


def test_a_missing_brief_wav_costs_one_page_and_nothing_else(built):
    from dcs import action as A
    from missiongen import wk_brief
    m = _mission(built)
    opener = [t for t in m.triggerrules.triggers
              if (t.comment or "") == "WK brief: hold and page 1"][0]
    assert any(isinstance(a, A.PictureToGroup) for a in opener.actions)
    assert any(isinstance(a, A.MessageToGroup) for a in opener.actions)
    has_snd = any(isinstance(a, A.SoundToGroup) for a in opener.actions)
    assert has_snd == wk_brief.has_audio(wk_brief.KEYS[0])


def test_only_the_briefed_ride_gets_a_brief(tmp_path):
    for key in ("pp_8_bnai", "pp_9_split"):
        rc = effective_recipe(key, "coldwar", "sinai")
        rc.update(template=key, seed=3)
        r = Recipe.from_dict(rc)
        r.validate()
        out = tmp_path / f"{key}.miz"
        generate(r, str(out))
        m = _mission(out)
        assert not _brief_triggers(m), key


def test_the_recording_sheet_covers_the_brief_as_well_as_the_cues():
    import pathlib
    from missiongen import wk_brief
    p = (pathlib.Path(__file__).resolve().parent.parent / "docs"
         / "WK_BNAI_VOICEOVER.md")
    txt = p.read_text(encoding="utf-8")
    for key in wk_brief.KEYS:
        assert f"`{wk_brief.audio_path(key).name}`" in txt, key
    assert txt.count("### ") == len(wk_brief.PAGES) + len(wk_coach.PHASES)


def test_the_flag_blocks_do_not_overlap():
    """THE BUG THIS TEST EXISTS BECAUSE OF.

    `F_ARM` was 8890 and the phase block is `F_PHASE + i`. With thirteen
    phases, phase 10 — `twos_pass` — WAS the arm flag. Two silent
    consequences: the cover-two cue re-armed the sequence, and the
    re-attack's clear-everything loop switched the coaching OFF. The second
    run, which is the entire point of the ride, worked once and then died.

    Nothing about that is visible in the code; both flags are just integers.
    So the arithmetic is asserted, with room for phases nobody has written
    yet, and the same check covers the brief's two blocks — which are
    generated the same way and would fail the same way."""
    from missiongen import wk_brief
    assert len(wk_coach.KEYS) <= wk_coach.F_PHASE_MAX, len(wk_coach.KEYS)
    coach_phase = {wk_coach.F_PHASE + i
                   for i in range(wk_coach.F_PHASE_MAX)}
    assert wk_coach.F_ARM not in coach_phase, wk_coach.F_ARM

    brief_cont = {wk_brief.F_CONT + i for i in range(len(wk_brief.PAGES))}
    brief_back = {wk_brief.F_BACK + i for i in range(len(wk_brief.PAGES))}
    assert not (brief_cont & brief_back)
    assert wk_brief.F_DONE not in brief_cont | brief_back
    assert not (coach_phase | {wk_coach.F_ARM}) & (
        brief_cont | brief_back | {wk_brief.F_DONE})


def test_the_second_run_does_not_switch_the_coaching_off(built):
    """The other half of the same bug, asserted where it actually bit: the
    re-attack clears every PHASE flag, and must not clear the ARM flag along
    with them."""
    from dcs import action as A
    m = _mission(built)
    t = [x for x in _cues(m) if x.comment == "WK coach: reattack"][0]
    cleared = {a.flag for a in t.actions if isinstance(a, A.ClearFlag)}
    assert wk_coach.F_ARM not in cleared, "the re-attack disarms the coaching"


def test_the_last_page_hands_the_aeroplane_over_in_words_as_well_as_actions():
    """The final page is where `StopPlayerSeatLock` fires. If the words do not
    say so, the pilot has his controls back and no idea — he is looking at a
    page about coaching, waiting for something else to happen."""
    from missiongen import wk_brief
    last = wk_brief.pages()[-1]
    assert "You have the airplane" in last[3], last[3][-80:]


def test_the_last_page_takes_the_brief_off_the_screen(built):
    """THE BUG ROB FLEW INTO. "The last screen doesn't exit when you press the
    space bar."

    It did exit — the wait ended, the controls came back, the coaching armed.
    What did not happen is the PICTURE going away, because every page is drawn
    for ten minutes and only pages 1-5 are ever replaced by the next one. So
    the pilot pressed SPACE, got his airplane, and flew the whole sortie with
    page six of the brief sitting over the canopy.

    DCS HAS NO ACTION THAT REMOVES A PICTURE. `PictureToGroup` with `clearview`
    is the entire mechanism: the only way to stop showing something is to show
    something else. Hence a blank page for one second.
    """
    from dcs import action as A
    from missiongen import wk_brief
    m = _mission(built)
    last = [t for t in m.triggerrules.triggers
            if (t.comment or "") == f"WK brief: next from {len(wk_brief.PAGES)}"]
    assert len(last) == 1, [t.comment for t in m.triggerrules.triggers]
    pics = [a for a in last[0].actions if isinstance(a, A.PictureToGroup)]
    assert pics, "the last page never replaces itself — the brief stays up"
    assert all(p.clearview for p in pics), "a picture that does not clearview " \
        "stacks on top of the brief instead of replacing it"
    assert max(p.seconds for p in pics) <= 3, \
        f"the replacement lingers for {max(p.seconds for p in pics)}s"
    msgs = [a for a in last[0].actions if isinstance(a, A.MessageToGroup)]
    assert msgs and all(x.clearview for x in msgs), \
        "the brief's text is left on screen with the picture"
    assert max(x.seconds for x in msgs) <= 3


def test_the_pages_before_the_last_are_replaced_by_the_next_one(built):
    """...and must NOT be cleared early. A page has to sit there until the
    pilot presses something — that is the whole point of the hold — so the
    fix for the last page must not become a fix for all of them."""
    from dcs import action as A
    from missiongen import wk_brief
    m = _mission(built)
    for i in range(1, len(wk_brief.PAGES)):
        t = [x for x in m.triggerrules.triggers
             if (x.comment or "") == f"WK brief: next from {i}"][0]
        pics = [a for a in t.actions if isinstance(a, A.PictureToGroup)]
        assert pics, f"page {i} draws no successor"
        assert min(p.seconds for p in pics) > 60, \
            f"page {i + 1} times out instead of waiting for the pilot"


def test_the_blank_page_ships_inside_the_mission(built):
    """A clear that references a file the .miz does not carry clears nothing."""
    import zipfile
    names = zipfile.ZipFile(built).namelist()
    assert any("wk_brief_clear" in n for n in names), \
        [n for n in names if "wk_brief" in n]


# --------------------------------------------------------------------------- #
# The wingman waits for the brief, and the ring comes in green
# --------------------------------------------------------------------------- #
# The wingman is in YOUR flight
# --------------------------------------------------------------------------- #
#
# ROB, across three separate-flight designs: "there is no wingman flying with
# me", then "the other REX flight doesn't fly with me at all." A separate AI
# flight cannot hold position on a human — DCS's one native mechanism that
# flies WITH you is a unit in your own group. v1.85.0 builds every two-ship
# ride that way: one group, the player in seat one, the AI in seat two. The
# hold trigger is gone because nothing needs holding: he waits because you
# wait.

def test_the_wingman_is_seat_two_of_your_own_flight(built):
    m = _mission(built)
    rex = [g for c in m.coalition["blue"].countries.values()
           for g in c.plane_group if g.name.startswith(_RADIO)]
    assert len(rex) == 1, [g.name for g in rex]
    g = rex[0]
    assert len(g.units) == 2, len(g.units)
    skills = [str(u.skill).split(".")[-1] for u in g.units]
    assert skills == ["Player", "Excellent"], skills
    p0 = {k for k, v in (g.units[0].pylons or {}).items() if v}
    p1 = {k for k, v in (g.units[1].pylons or {}).items() if v}
    assert p0 == p1 and p0, (sorted(p0), sorted(p1))


def test_no_machinery_from_the_separate_flight_survives(built):
    """The old design left three kinds of residue, each a bug if it outlives
    the pivot: a second REX group, a late-activation hold, and a release
    trigger watching the brief's flag. All three must be gone."""
    m = _mission(built)
    assert not [g for c in m.coalition["blue"].countries.values()
                for g in c.plane_group if g.name == f"{_RADIO} 2"], \
        "the separate flight is back"
    assert not [t for t in m.triggerrules.triggers
                if "wingman" in (t.comment or "").lower()], \
        "a wingman hold/release trigger survived the pivot"
    for c in m.coalition["blue"].countries.values():
        for g in c.plane_group:
            if g.name.startswith(_RADIO):
                assert not g.late_activation, \
                    "your own flight is late-activated — nobody would spawn"


@pytest.fixture(scope="module")
def built_green(tmp_path_factory):
    out = tmp_path_factory.mktemp("coach_g") / "green.miz"
    rc = effective_recipe("bnai_coach_green", "coldwar", MAP)
    rc.update(template="bnai_coach_green", seed=7)
    r = Recipe.from_dict(rc)
    r.validate()
    generate(r, str(out))
    return out


def test_the_green_variant_ships_green_cards_and_only_green(built_green):
    """ROB: 'a version of the coached B'NAI with green rings.' The variant is
    the SAME ride — same wk_ride key, same route, same cues — differing in
    exactly the palette, so the .miz must carry the green set and none of the
    red one."""
    import zipfile
    names = zipfile.ZipFile(built_green).namelist()
    green = sorted(n.rsplit("/", 1)[-1] for n in names
                   if "wk_coach_green_" in n)
    red = [n for n in names if n.rsplit("/", 1)[-1].startswith("wk_coach_")
           and "green" not in n and n.endswith(".png")]
    from missiongen import wk_coach
    assert len(green) == len(wk_coach.KEYS), green
    assert not red, red


def test_the_green_ring_is_actually_green():
    """A card named green whose ring is red is worse than no variant. Measured
    from the pixels: the green card must contain ring-colored pixels the red
    card does not, at the same position."""
    from PIL import Image
    from missiongen import wk_coach
    for key in ("pup", "release"):
        g = Image.open(wk_coach.card_path(key, "green")).convert("RGB")
        r = Image.open(wk_coach.card_path(key, "red")).convert("RGB")
        assert g.size == r.size
        gp = g.getdata()
        greens = sum(1 for (pr, pg, pb) in gp if pg > 100 and pr < 90 and pb < 90)
        reds_on_green = sum(1 for (pr, pg, pb) in gp
                            if pr > 150 and pg < 80 and pb < 80)
        assert greens > 100, f"{key}: no green ring ink ({greens} px)"
        assert reds_on_green < 20, \
            f"{key}: the 'green' card still carries a red ring"


def test_the_green_variant_is_the_same_ride_with_a_different_ring():
    """The whole point of putting the color in the RECIPE: one ride, two
    palettes. The variant's card must reuse pp_8_bnai_coach and differ from it
    in `coach_ring` — anything else it changes is a second syllabus entry
    wearing a paint job."""
    from missiongen.resolver import load_json
    tpl = load_json("mission_templates")
    g, r = tpl["bnai_coach_green"], tpl["pp_8_bnai_coach"]
    assert g["wk_ride"] == "pp_8_bnai_coach"
    assert "track" not in g, "the green variant crept into the syllabus"
    gr, rr = dict(g["recipe"]), dict(r["recipe"])
    assert gr.pop("coach_ring", None) == "green"
    # ...and the navigation squares, which joined the variant when Rob said
    # what "green" had meant all along. Ring and gates are the WHOLE license;
    # a third difference is a second syllabus entry wearing a paint job.
    assert gr.pop("coach_gates", None) is True
    rr.pop("coach_ring", None); rr.pop("coach_gates", None)
    assert gr == rr, "the variant quietly changes more than the ring and gates"


def test_every_ring_the_recipe_offers_has_a_full_card_set():
    """Derived three ways and they must agree: the recipe's enum, wk_coach's
    palette list, and the files on disk. A color any one of them has that the
    others lack is a FileNotFoundError in somebody's download."""
    from missiongen import wk_coach
    from missiongen.recipe import RECIPE_ENUMS
    assert set(RECIPE_ENUMS["coach_ring"]) == set(wk_coach.RINGS)
    for ring in wk_coach.RINGS:
        gone = [k for k in wk_coach.KEYS
                if not wk_coach.card_path(k, ring).is_file()]
        assert not gone, f"{ring}: {gone}"


# --------------------------------------------------------------------------- #
# The wingman actually flies: units and the climb-out point
# --------------------------------------------------------------------------- #
#
# ROB: "The coached mission AI plane doesn't take off, it just goes slowly
# down the runway." Two defects, both measured out of the built .miz:
#
#   * UNITS. pydcs' `add_waypoint(speed=...)` and `flight_group_inflight`
#     take KM/H (they divide by 3.6). `wk_route` passed meters per second, so
#     every waypoint on every ride was commanded at 112 knots instead of 400 —
#     slow enough that the AI never accelerated to rotation and drove the
#     length of the runway instead. The route READ correctly on the kneeboard
#     the whole time, because the kneeboard prints the briefed IAS, not the
#     waypoint. Say/do, in miles per hour.
#
#   * THE CLIMB-OUT POINT. Every ground-started AI flight pydcs itself builds
#     gets a runway waypoint between parking and the first en-route point.
#     The counterpart did not, so its first instruction after brake release
#     was a turning point twenty miles away at three hundred feet.

def _kt(p):
    return p.speed / 0.514444


def test_the_route_is_commanded_at_the_speed_it_is_briefed(built):
    """Read every en-route waypoint of both flights back out of the mission
    and require the TAS the briefed IAS converts to — not a fixed number, so
    the guard follows the sheet if the sheet ever changes."""
    from missiongen import wk_route
    m = _mission(built)
    checked = 0
    for c in m.coalition["blue"].countries.values():
        for g in c.plane_group:
            if not g.name.startswith(_RADIO):
                continue
            for p in g.points:
                if p.type != "Turning Point" or not p.name:
                    continue
                legs = [l for l in wk_route.legs_for(RIDE, MAP)
                        if l[0] == str(p.name)]
                if not legs:
                    continue
                ias, agl = legs[0][4], legs[0][3]
                want = wk_route.ias_to_tas_kt(ias, wk_route.msl_ft(agl, MAP))
                assert abs(_kt(p) - want) < 5, \
                    f"{g.name} {p.name}: commanded {_kt(p):.0f} kt, " \
                    f"briefed {ias} IAS -> {want:.0f} TAS"
                checked += 1
    assert checked >= 6, f"only {checked} named waypoints checked"


def test_no_waypoint_anywhere_on_the_ride_is_slower_than_flight(built):
    """The blunt version, so a NEW leg added with the old conversion still
    fails: nothing en route may be commanded below 250 knots. The two lawful
    slow points — the parking start and the runway climb-out — are excluded
    by type and by sitting on the field."""
    m = _mission(built)
    home = None
    for c in m.coalition["blue"].countries.values():
        for g in c.plane_group:
            if g.name == f"{_RADIO} 1":
                home = g.points[0].position
    for c in m.coalition["blue"].countries.values():
        for g in c.plane_group:
            if not g.name.startswith(_RADIO):
                continue
            for p in g.points:
                if p.type != "Turning Point":
                    continue
                # 12 km, not tighter: pydcs puts the climb-out 6 km past the
                # threshold, and the parking stand adds a seed-dependent
                # offset (measured: 6.9-8.5 km). The first en-route leg is
                # 34 km out, so the bands cannot touch.
                if home and p.position.distance_to_point(home) < 12000:
                    continue        # the climb-out point sits on the field
                assert _kt(p) > 250, \
                    f"{g.name}: {_kt(p):.0f} kt at {p.name or '(unnamed)'}"


def test_the_two_ship_takes_off_as_one_flight(built):
    """What replaced the climb-out guard: there is no independent route to
    climb out on. Both airplanes sit in one group at the same field, so DCS
    runs the departure — seat two follows you out and forms up."""
    m = _mission(built)
    g = [g for c in m.coalition["blue"].countries.values()
         for g in c.plane_group if g.name.startswith(_RADIO)][0]
    assert g.points[0].type == "TakeOffParkingHot", g.points[0].type
    d = g.units[0].position.distance_to_point(g.units[1].position)
    assert 10 < d < 2000, f"the two airplanes are {d:.0f} m apart on the ramp"



# --------------------------------------------------------------------------- #
# The target is where the route bombs, the route misses Cairo, and the gates
# --------------------------------------------------------------------------- #
#
# ROB: "The coached BNAI mission doesn't have a target to bomb. The mission
# waypoints don't seemed aligned. And the green navigation boxes don't exist."
#
# Three defects. The target packages were anchored to enemy AIRBASES — 60+ NM
# north-west under the 1980 lineup — while the route ran its TARGET leg the
# other way, so the brief listed targets the route never visited and the route
# bombed sand. The sinai axis was 120°, chosen when the rides silently
# launched from Hatzor; from Cairo West that runs the 300-ft low level
# straight across Cairo (Cairo International is 28 NM out on bearing 091).
# And the "green navigation boxes" are DCS's HELPER GATES — a native trigger
# action, no Lua — which nothing ever showed.

def test_the_target_stands_on_the_leg_the_sheet_aims_at(built):
    """Every TGT group in the mission must stand within 3 km of the route's
    own TARGET point — none may be off near the enemy airfields where the old
    placement anchored them."""
    from missiongen import wk_route
    m = _mission(built)
    home = None
    for c in m.coalition["blue"].countries.values():
        for g in c.plane_group:
            if g.name == f"{_RADIO} 1":
                home = g.points[0].position
    tpos = wk_route.leg_positions(home, RIDE, MAP)["TARGET"]
    tgts = [(g.name, g.position.distance_to_point(tpos))
            for c in m.coalition["red"].countries.values()
            for g in list(c.vehicle_group) + list(c.static_group)
            if "TGT" in g.name]
    assert tgts, "there is no target to bomb at all"
    far = [(n, f"{d/1852:.0f} NM") for n, d in tgts if d > 3000]
    assert not far, f"targets standing off the route: {far}"


def test_the_route_stays_out_of_cairo(built):
    """From Cairo West, every en-route waypoint must stay in the Western
    Desert — nothing east of the home field, where the Nile valley and Cairo
    are. The 120° axis put the target leg in the city's southern suburbs."""
    m = _mission(built)
    for c in m.coalition["blue"].countries.values():
        for g in c.plane_group:
            if not g.name.startswith(_RADIO):
                continue
            home_y = g.points[0].position.y
            for p in g.points:
                if p.type != "Turning Point" or not p.name:
                    continue
                assert p.position.y < home_y + 5000, \
                    f"{g.name} {p.name}: {(p.position.y - home_y)/1852:.0f} " \
                    f"NM east of the field — toward Cairo, not the desert"


def test_the_green_variant_shows_the_navigation_squares(built_green):
    """The named ask. `ShowHelperGatesForUnit` — the training missions' green
    fly-through boxes, a NATIVE action — fired by the brief's own done flag at
    the player's unit, so the boxes appear the instant you get the jet."""
    from dcs import action as A, condition as C
    from missiongen import wk_brief
    m = _mission(built_green)
    gates = [t for t in m.triggerrules.triggers
             if (t.comment or "") == "WK gates: navigation squares"]
    assert len(gates) == 1, [t.comment for t in m.triggerrules.triggers]
    acts = [a for a in gates[0].actions
            if isinstance(a, A.ShowHelperGatesForUnit)]
    assert acts, "the trigger shows no gates"
    me = [u for c in m.coalition["blue"].countries.values()
          for g in c.plane_group for u in g.units
          if str(u.skill) == "Skill.Player"]
    assert acts[0].unit == me[0].id, \
        f"the gates follow unit {acts[0].unit}, the player is {me[0].id}"
    flags = [x.flag for x in gates[0].rules if isinstance(x, C.FlagIsTrue)]
    assert flags == [wk_brief.F_DONE], flags


def test_the_coached_ride_shows_the_squares_and_the_check_ride_does_not(built):
    """ROB: "on the coached mission, there should be training-mission gates."
    He is right, and my earlier split was wrong: the no-aids version of this
    attack ALREADY EXISTS — it is ride 9, the B'NAI check. Coached means every
    aid on. So the track's coached ride draws the gates too, and gate-freedom
    is asserted where it belongs: on the check ride and everything else."""
    from dcs import action as A
    m = _mission(built)
    gates = [t for t in m.triggerrules.triggers
             if (t.comment or "") == "WK gates: navigation squares"]
    assert len(gates) == 1, "the coached ride lost its navigation squares"
    # ...and only the two coached templates may ask for them
    from missiongen.resolver import load_json
    gated = sorted(k for k, v in load_json("mission_templates").items()
                   if isinstance(v, dict)
                   and (v.get("recipe") or {}).get("coach_gates"))
    assert gated == ["bnai_coach_green", "pp_8_bnai_coach"], gated


@pytest.fixture(scope="module")
def built_drag(tmp_path_factory):
    """The air-start ride, for the counterpart's spawn speed."""
    out = tmp_path_factory.mktemp("drag") / "drag.miz"
    rc = effective_recipe("pp_1_drag", "coldwar", MAP)
    rc.update(template="pp_1_drag", seed=7)
    generate(Recipe.from_dict(rc).validate(), str(out))
    return out


def test_the_air_start_ride_is_a_two_ship_at_flying_speed(built_drag):
    """The drag ride air-starts: the flight must spawn as a two-ship (seat
    two on the wing, not a separate group) and above 250 kt — m/s-as-km/h
    once put the spawn at 112, below a loaded Phantom's stall."""
    m = _mission(built_drag)
    rex = [g for c in m.coalition["blue"].countries.values()
           for g in c.plane_group if g.name.startswith(_RADIO)]
    assert len(rex) == 1 and len(rex[0].units) == 2, \
        [(g.name, len(g.units)) for g in rex]
    kt = rex[0].points[0].speed / 0.514444
    assert kt > 250, f"the flight spawns at {kt:.0f} kt"


@pytest.fixture(scope="module")
def built_full_ramp(tmp_path_factory):
    """The coached ride with EVERY fitting stand dressed. At the default fill
    the two claimed shelters are usually outside the sample, so a dressing
    that ignored stand claims could pass on seed luck — measured: it did, even
    with both of the main path's unit_id checks removed. At 100% fill there is
    no luck left: a dressing that ignores claims MUST hit the flight's own
    shelters."""
    out = tmp_path_factory.mktemp("coach_full") / "full.miz"
    rc = effective_recipe(RIDE, "coldwar", MAP)
    rc.update(template=RIDE, seed=7, dress_fill=100)
    generate(Recipe.from_dict(rc).validate(), str(out))
    return out


def test_no_static_shares_a_stand_with_either_aeroplane(built_full_ramp):
    """ROB: "there is a static plane in the same hangar as the second plane."
    Measured at the pack's own seed before the fix: a static F-4E at ZERO
    meters from the wingman, his GSE truck at 16. Dressing fills every stand
    whose `unit_id` is unclaimed; both of the flight's stands are claimed at
    group creation, before the ramp is dressed, and this reads the distances
    back out of a FULL ramp — see the fixture for why full."""
    m = _mission(built_full_ramp)
    pos = {}
    for c in m.coalition["blue"].countries.values():
        for g in c.plane_group:
            if g.name.startswith(_RADIO):
                for u in g.units:
                    pos[u.name or f"{g.name}-{len(pos)+1}"] = u.position
    assert len(pos) == 2, sorted(pos)
    clashes = []
    for c in m.coalition["blue"].countries.values():
        for g in c.static_group:
            for name, p in pos.items():
                d = g.position.distance_to_point(p)
                if d < 30:
                    clashes.append((name, g.name, round(d)))
    assert not clashes, clashes
