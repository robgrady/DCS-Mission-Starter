"""Waypoint timing: the clock on the card, the anchor, the file, the coach,
and the four F-4E rides that teach it.

WHAT THIS FILE HOLDS THE PRODUCT TO
-----------------------------------
  1. the arithmetic — anchored, not accumulated: a TOT anchor moves the
     mission clock so the target is crossed at the time asked; a hold adds
     to the push leg; the first leg is timed on a climb schedule; wind is
     symmetric.
  2. the file — the player's waypoints carry the card's ETAs unlocked, the
     package's carry them LOCKED and two minutes ahead, and the mission's
     start time is the moved one.
  3. the paperwork — the in-game brief, the PDF/MD brief and the kneeboard
     all print the same clock; the say/do check CATCHES a planted
     disagreement and the shipped rides have none.
  4. the coach — grades at four points inside flag block 8860–8879, a
     scorecard, and nothing attached when the recipe did not ask.
  5. the library — four rides in track `timing_f4e`, numbered 1–4, whose
     hand-written briefs quote only clock times the plan actually produces.

Published constants (ground 8/3/1/0 min, ±30 s TOT, ±60 s push, package
lead 120 s, base 50) are literals here on purpose.
"""
from __future__ import annotations

import json
from datetime import datetime

import pytest

from missiongen import Recipe, generate
from missiongen import saydo, timing, timing_coach, tracks
from missiongen.builder import StarterBuilder
from missiongen.recipe import RecipeError
from missiongen.resolver import load_json
from missiongen.templates import effective_recipe

TEMPLATES = load_json("mission_templates")


def _recipe(key, seed=311, **over):
    v = TEMPLATES[key]
    era = (v.get("eras") or ["modern"])[0]
    rc = effective_recipe(key, era)
    rc.setdefault("map", v.get("default_map", "caucasus"))
    rc.update(era=era, template=key, seed=seed)
    rc.update(over)
    return Recipe.from_dict(rc)


def _rows():
    """A three-leg card like routing.leg_card makes: 60 + 60 + 9 nm at 400 kt."""
    return [
        {"from": "HOME", "to": "WP1", "heading": 90, "nm": 60.0, "alt_ft": 15000, "kt": 400, "min": 9.0},
        {"from": "WP1", "to": "IP", "heading": 90, "nm": 60.0, "alt_ft": 10000, "kt": 400, "min": 9.0},
        {"from": "IP", "to": "TARGET", "heading": 90, "nm": 9.0, "alt_ft": 8000, "kt": 400, "min": 1.35},
    ]


# --------------------------------------------------------------------------- #
# 1. arithmetic
# --------------------------------------------------------------------------- #
def test_takeoff_anchor_counts_from_the_ground_block():
    tl = timing.plan(_rows(), start="cold", era="coldwar",
                     mission_start=datetime(1978, 6, 21, 12, 0))
    assert tl["anchor"] == "takeoff" and tl["ground_s"] == 480
    assert tl["takeoff_clock"] == "12:08:00" and tl["shift_s"] == 0
    r = tl["rows"]
    assert [x["to"] for x in r] == ["WP1", "IP", "TARGET"]
    assert r[0]["eta_s"] == 480 + r[0]["cum_s"]
    assert r[2]["cum_s"] == r[0]["leg_s"] + r[1]["leg_s"] + r[2]["leg_s"]
    assert r[2]["eta"] == timing.hhmmss(12 * 3600 + r[2]["eta_s"])


@pytest.mark.parametrize("start,ground", [("cold", 480), ("warm", 180), ("runway", 60), ("air", 0)])
def test_the_ground_block_by_start_type(start, ground):
    tl = timing.plan(_rows(), start=start, mission_start=datetime(1978, 6, 21, 12, 0))
    assert tl["takeoff_s"] == ground


def test_the_first_leg_is_timed_on_a_climb_schedule():
    """60 nm at 400 kt is 540 s. Climbing to 15,000 ft at 350 kt makes it longer."""
    tl = timing.plan(_rows(), start="air", era="coldwar",
                     mission_start=datetime(1978, 6, 21, 12, 0))
    first, second = tl["rows"][0], tl["rows"][1]
    assert second["leg_s"] == 540
    assert first["leg_s"] > 540 and first["gs_kt"] < 400


def test_a_tot_anchor_moves_the_mission_clock_backwards():
    tl = timing.plan(_rows(), start="warm", era="coldwar", anchor="tot",
                     anchor_hhmm="06:42", mission_start=datetime(1978, 6, 21, 5, 0))
    assert tl["anchor_wp"] == "TARGET" and tl["anchor_clock"] == "06:42:00"
    assert tl["rows"][-1]["eta"] == "06:42:00"
    assert tl["tolerance_s"] == 30
    # start = 06:42 - time to target - 3 min: later than 05:00, so a positive shift
    assert tl["shift_s"] > 0
    assert tl["mission_start"] == datetime(1978, 6, 21, 5, 0) + __import__("datetime").timedelta(seconds=tl["shift_s"])
    assert tl["start_clock"] == timing.hhmmss(5 * 3600 + tl["shift_s"])
    assert tl["takeoff_clock"] == timing.hhmmss(5 * 3600 + tl["shift_s"] + 180)


def test_a_push_anchor_fixes_wp1_with_the_wider_window():
    tl = timing.plan(_rows(), start="warm", anchor="push", anchor_hhmm="12:35:00",
                     mission_start=datetime(1978, 6, 21, 12, 0))
    assert tl["anchor_wp"] == "WP1" and tl["rows"][0]["eta"] == "12:35:00"
    assert tl["tolerance_s"] == 60
    lo, hi = timing.windows(tl)["WP1"]
    assert hi - lo == 120
    lo, hi = timing.windows(tl)["TARGET"]
    assert hi - lo == 120        # not the anchor: the wider of the two


def test_a_tot_window_is_thirty_seconds_and_wp1_sixty():
    tl = timing.plan(_rows(), anchor="tot", anchor_hhmm="06:00",
                     mission_start=datetime(1978, 6, 21, 5, 0))
    w = timing.windows(tl)
    assert w["TARGET"][1] - w["TARGET"][0] == 60
    assert w["WP1"][1] - w["WP1"][0] == 120


def test_a_hold_adds_to_the_push_leg_and_nothing_else():
    plain = timing.plan(_rows(), mission_start=datetime(1978, 6, 21, 12, 0))
    held = timing.plan(_rows(), mission_start=datetime(1978, 6, 21, 12, 0), hold_s=180)
    assert held["rows"][0]["hold_s"] == 180 and held["rows"][1]["hold_s"] == 0
    assert held["rows"][0]["cum_s"] == plain["rows"][0]["cum_s"] + 180
    assert held["rows"][2]["cum_s"] == plain["rows"][2]["cum_s"] + 180
    assert held["rows"][0]["leg_s"] == plain["rows"][0]["leg_s"]


def test_wind_is_symmetric_and_absent_by_default():
    rows = _rows()
    tail = timing.plan(rows, start="air", mission_start=datetime(1978, 6, 21, 12, 0),
                       winds=[(2000, 20.0, 90), (8000, 20.0, 90)])      # blowing east, track east
    head = timing.plan(rows, start="air", mission_start=datetime(1978, 6, 21, 12, 0),
                       winds=[(2000, 20.0, 270), (8000, 20.0, 270)])
    calm = timing.plan(rows, start="air", mission_start=datetime(1978, 6, 21, 12, 0))
    assert tail["wind"] and head["wind"] and not calm["wind"]
    assert tail["rows"][1]["gs_kt"] > calm["rows"][1]["gs_kt"] > head["rows"][1]["gs_kt"]
    assert abs((tail["rows"][1]["gs_kt"] - 400) + (head["rows"][1]["gs_kt"] - 400)) <= 1


def test_the_anchor_time_parser_refuses_what_is_not_a_clock():
    assert timing.parse_hhmm("06:42") == 6 * 3600 + 42 * 60
    assert timing.parse_hhmm("06:42:30") == 6 * 3600 + 42 * 60 + 30
    for bad in ("6", "25:00", "06:60", "noon", "", None, "1:2:3:4"):
        assert timing.parse_hhmm(bad) is None, bad


def test_no_rows_no_plan():
    assert timing.plan([], mission_start=datetime(1978, 6, 21, 12, 0)) is None
    assert timing.plan(None) is None


# --------------------------------------------------------------------------- #
# recipe validation
# --------------------------------------------------------------------------- #
def test_timing_at_needs_an_anchor_that_can_use_it():
    with pytest.raises(RecipeError, match="timing_at needs"):
        Recipe.from_dict({"timing_at": "06:42"})
    with pytest.raises(RecipeError, match="not a clock time"):
        Recipe.from_dict({"timing_anchor": "tot", "timing_at": "quarter past"})
    with pytest.raises(RecipeError, match="timing_anchor"):
        Recipe.from_dict({"timing_anchor": "sunrise"})
    with pytest.raises(RecipeError, match="timing_hold_min"):
        Recipe.from_dict({"timing_hold_min": 45})
    r = Recipe.from_dict({"timing_anchor": "tot", "timing_at": "06:42", "timing_hold_min": 3})
    assert r.timing_anchor == "tot"


# --------------------------------------------------------------------------- #
# 2 + 3 + 4. one full build: file, paperwork, coach, say/do
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def strike():
    r = _recipe("gun_belt_strike", seed=7, start="warm", timing_anchor="tot",
                timing_at="06:42", timing_coach=True, timing_package=True,
                timing_hold_min=3)
    b = StarterBuilder(r)
    m = b.build()
    return b, m


def test_the_mission_clock_is_the_moved_one(strike):
    b, m = strike
    tl = b.stats["timing"]
    assert tl["anchor_clock"] == "06:42:00"
    assert saydo.mission_clock(m) == tl["start_clock"][:5]
    assert b.stats["start_clock"] == tl["start_clock"][:5]
    assert m.start_time != datetime(m.start_time.year, 6, 21, 5, 0), "the dawn preset was not moved"


def test_the_players_waypoints_carry_the_cards_etas_unlocked(strike):
    b, m = strike
    by = {p.name: p for p in b._player_group.points if p.name}
    for row in b.stats["timing"]["rows"]:
        assert by[row["to"]].ETA == row["eta_s"]
        assert by[row["to"]].ETA_locked is False
        assert by[row["to"]].speed_locked is True, "the player's card keeps its speeds"


def test_the_package_flies_the_same_card_locked_two_minutes_ahead(strike):
    b, m = strike
    pkg = [g for c in m.coalition["blue"].countries.values() for g in c.plane_group
           if str(g.name).startswith("Package")]
    assert len(pkg) == 1
    g = pkg[0]
    assert g.late_activation is True
    by = {p.name: p for p in g.points if p.name}
    for row in b.stats["timing"]["rows"]:
        assert by[row["to"]].ETA == row["eta_s"] - 120
        assert by[row["to"]].ETA_locked is True
        # Rob's screenshot (v1.99.1): the Mission Editor refuses to save a
        # mission whose waypoint has locked speed between locked times. A
        # time-locked point flies whatever speed meets the time.
        assert by[row["to"]].speed_locked is False, \
            "locked time AND locked speed: DCS will not save the mission"
    assert b.stats["timing"]["package_lead_s"] == 120
    launch = [t for t in m.triggerrules.triggers if t.comment == "Timing: launch the package"]
    assert len(launch) == 1
    assert any("package" in s for s in b.stats["support"])


def test_the_in_game_brief_prints_the_timeline_and_the_anchor(strike):
    b, m = strike
    text = m.description_text()
    tl = b.stats["timing"]
    assert "TIMING" in text and "Anchor: TOT 06:42:00 at TARGET" in text
    for row in tl["rows"]:
        assert row["eta"] in text, row
    assert "HOLD 3 min at WP1" in text
    assert "moved" in text and "so that time can be met" in text
    assert "TIMING COACH" in text
    assert "Mission clock: " + tl["start_clock"][:5] in text
    assert any("advisory" in k for k in b.stats["known_issues"])
    assert any("LOCKED ETAs" in k for k in b.stats["known_issues"])


def test_the_coach_is_wired_inside_its_flag_block(strike):
    b, m = strike
    ts = [t for t in m.triggerrules.triggers if t.comment.startswith("Timing")]
    assert b.stats["timing_coach_triggers"] == len(ts) - 1      # minus the launch
    names = {t.comment for t in ts}
    for pt in ("TAKEOFF", "WP1", "IP", "TARGET"):
        for k in ("early", "ontime", "late"):
            assert f"Timing grade: {pt} {k}" in names
            assert f"Timing debrief: {pt} {k}" in names
    for pt in ("WP1", "IP", "TARGET"):
        assert f"Timing grade: {pt} missed" in names
    assert "Timing debrief: open the card" in names
    assert "Timing: package at the IP" in names
    assert "Timing: hold reminder" in names
    # every flag the coach touches lives in 8860-8879
    flags = set()
    for t in ts:
        for a in t.actions:
            v = a.dict().get("flag") if hasattr(a, "dict") else None
            if isinstance(v, int):
                flags.add(v)
        for c in t.rules:
            v = c.dict().get("flag") if hasattr(c, "dict") else None
            if isinstance(v, int):
                flags.add(v)
    assert flags and all(8860 <= f <= 8879 for f in flags), sorted(flags)
    assert timing_coach.F_ARM == 8879 and timing_coach.F_DEBRIEF == 8878


def _said(m, trigger):
    """The text of a trigger's message action."""
    return " ".join(str(a.text) for a in trigger.actions if hasattr(a, "text"))


def test_the_debrief_scores_the_anchor_double(strike):
    b, m = strike
    by = {t.comment: t for t in m.triggerrules.triggers}
    assert _said(m, by["Timing debrief: TARGET ontime"]).startswith("+20  TARGET on time")
    assert _said(m, by["Timing debrief: TARGET late"]).startswith("-20  TARGET late")
    assert _said(m, by["Timing debrief: WP1 ontime"]).startswith("+10  WP1 on time")
    assert _said(m, by["Timing debrief: WP1 early"]).startswith("-5  WP1 early")
    assert "Base score 50" in _said(m, by["Timing debrief: open the card"])
    # the grade calls name the window the pilot was held to
    assert "06:42:00 +/-30 s" in _said(m, by["Timing grade: TARGET ontime"])
    assert "+/-60 s" in _said(m, by["Timing grade: WP1 ontime"])


def test_the_say_do_check_passes_the_shipped_build(strike):
    b, m = strike
    assert not [w for w in b.warnings if w.startswith("SAY/DO:")], b.warnings


def test_stats_timing_is_api_safe(strike):
    b, m = strike
    json.dumps(b.stats["timing"])


def test_the_full_documents_print_the_same_clock(tmp_path):
    r = _recipe("gun_belt_strike", seed=7, start="warm", timing_anchor="tot",
                timing_at="06:42", timing_coach=True)
    res = generate(r, str(tmp_path / "t.miz"), brief_dir=str(tmp_path))
    assert not [w for w in res["warnings"] if "rendering failed" in w or "SAY/DO" in w]
    md = (tmp_path / "Mission_Brief.md").read_text()
    tl = res["stats"]["timing"]
    assert "## Timing" in md and "TOT 06:42:00" in md
    for row in tl["rows"]:
        assert row["eta"] in md
    assert res["stats"]["kneeboard_pages"] >= 5


def test_the_dtg_follows_the_moved_clock():
    from missiongen import brief
    b = StarterBuilder(_recipe("gun_belt_strike", seed=7, start="warm",
                               timing_anchor="tot", timing_at="06:42"))
    b.build()
    tl = b.stats["timing"]
    dtg = brief._dtg(b.brief_ctx)
    assert dtg.startswith(f"21{tl['start_clock'][:5].replace(':', '')}L"), dtg
    assert not dtg.startswith("210500L")
    plain = StarterBuilder(_recipe("gun_belt_strike", seed=7))
    plain.build()
    assert brief._dtg(plain.brief_ctx).startswith("210500L")


def test_no_timing_without_a_route():
    b = StarterBuilder(_recipe("cap_alert5", seed=3))
    b.build()
    assert "timing" not in b.stats and b._timing is None
    assert not any(t.comment.startswith("Timing") for t in b._mission.triggerrules.triggers)


def test_no_coach_and_no_package_unless_asked():
    b = StarterBuilder(_recipe("gun_belt_strike", seed=7))
    m = b.build()
    assert b.stats["timing"]["anchor"] == "takeoff"
    assert not any(t.comment.startswith("Timing") for t in m.triggerrules.triggers)
    assert "timing_coach_triggers" not in b.stats
    assert not [g for c in m.coalition["blue"].countries.values() for g in c.plane_group
                if str(g.name).startswith("Package")]


# --------------------------------------------------------------------------- #
# the say/do check catches what it is for
# --------------------------------------------------------------------------- #
def _tl_and_group(strike):
    b, m = strike
    tl = json.loads(json.dumps(b.stats["timing"]))
    return b, m, tl


def test_say_do_catches_a_waypoint_whose_eta_drifted(strike):
    b, m, tl = _tl_and_group(strike)
    tl["rows"][1]["eta_s"] += 15
    found = saydo.check_timing(m, b._player_group, tl, m.description_text())
    assert any("IP" in f and "carries ETA" in f for f in found), found


def test_say_do_catches_a_locked_player_point(strike):
    b, m, tl = _tl_and_group(strike)
    p = next(p for p in b._player_group.points if p.name == "IP")
    p.ETA_locked = True
    try:
        found = saydo.check_timing(m, b._player_group, tl, m.description_text())
    finally:
        p.ETA_locked = False
    assert any("ETA-locked" in f for f in found), found


def test_say_do_catches_a_renamed_waypoint(strike):
    b, m, tl = _tl_and_group(strike)
    p = next(p for p in b._player_group.points if p.name == "WP1")
    p.name = "WP01"
    try:
        found = saydo.check_timing(m, b._player_group, tl, m.description_text())
    finally:
        p.name = "WP1"
    assert any("no waypoint in the file is named WP1" in f for f in found), found


def test_say_do_catches_a_clock_that_moved_after_the_plan(strike):
    b, m, tl = _tl_and_group(strike)
    from datetime import timedelta
    m.start_time = m.start_time + timedelta(minutes=1)
    try:
        found = saydo.check_timing(m, b._player_group, tl, m.description_text())
    finally:
        m.start_time = m.start_time - timedelta(minutes=1)
    assert any("mission clock puts that waypoint" in f for f in found), found


def test_say_do_catches_an_anchor_missing_from_the_brief(strike):
    b, m, tl = _tl_and_group(strike)
    found = saydo.check_timing(m, b._player_group, tl, "a brief with no clock in it")
    assert any("anchor tot 06:42:00 is not printed" in f for f in found), found


# --------------------------------------------------------------------------- #
# 5. the library: four F-4E rides
# --------------------------------------------------------------------------- #
RIDES = tracks.rides("timing_f4e")


def test_the_track_has_four_rides_then_a_check():
    assert [n for n, _k, _v in RIDES] == [1, 2, 3, 4, 5]
    assert RIDES[-1][1] == "timing_5_check" and RIDES[-1][2]["recipe"]["check_ride"] is True
    t = tracks.get("timing_f4e")
    assert t["aircraft"] == "F_4E_45MC" and t["default_map"] == "germany"
    for _n, key, v in RIDES:
        assert v["route"] == "strike" and v["recipe"]["aircraft"] == "F_4E_45MC"
        assert v["recipe"]["timing_coach"] is True
        assert v["library"]["module"] == "F-4E"


@pytest.fixture(scope="module")
def built_rides():
    out = {}
    for n, key, _v in RIDES:
        b = StarterBuilder(_recipe(key, seed=1))
        m = b.build()
        out[key] = (b, m)
    return out


def test_every_ride_builds_clean_with_a_timed_card(built_rides):
    for key, (b, m) in built_rides.items():
        bad = [w for w in b.warnings if "livery" not in w]
        assert not bad, (key, bad)
        assert b.stats.get("timing"), key
        assert b.stats.get("timing_coach_triggers", 0) >= 30, key


def test_each_ride_fixes_the_anchor_it_teaches(built_rides):
    tl = {k: b.stats["timing"] for k, (b, _m) in built_rides.items()}
    assert tl["timing_1_flythecard"]["anchor"] == "takeoff"
    assert tl["timing_2_hitthetot"]["anchor_clock"] == "05:45:00"
    assert tl["timing_3_thepackage"]["anchor"] == "push" and tl["timing_3_thepackage"]["anchor_clock"] == "12:35:00"
    assert tl["timing_3_thepackage"].get("package_lead_s") == 120
    assert tl["timing_4_absorbtheearly"]["anchor_clock"] == "05:50:00"
    assert tl["timing_4_absorbtheearly"]["hold_s"] == 180
    # short enough to fly twice in an evening
    for k, t in tl.items():
        assert t["rows"][-1]["cum_s"] < 25 * 60, (k, t["rows"][-1]["cum_s"])


def test_the_hand_written_briefs_quote_only_clocks_the_plan_produces(built_rides):
    """The one say/do gap a template can still open: a time typed into the
    brief. Every HH:MM:SS in a ride's brief must be a clock the plan prints."""
    import re
    for _n, key, v in RIDES:
        b, _m = built_rides[key]
        tl = b.stats["timing"]
        clocks = {t["eta"] for t in tl["rows"]} | {tl["anchor_clock"], tl["takeoff_clock"]}
        for line in v["brief"]:
            for said in re.findall(r"\b\d{2}:\d{2}:\d{2}\b", line):
                assert said in clocks, (key, said, sorted(c for c in clocks if c))
        # and the ride's own anchor is in the in-game text
        text = _m.description_text()
        if tl["anchor"] != "takeoff":
            assert tl["anchor_clock"] in text


def test_ride_three_has_the_package_and_the_others_do_not(built_rides):
    for key, (b, m) in built_rides.items():
        pkg = [g for c in m.coalition["blue"].countries.values() for g in c.plane_group
               if str(g.name).startswith("Package")]
        assert (len(pkg) == 1) == (key == "timing_3_thepackage"), key


def test_a_planted_drift_reaches_the_build_warnings(monkeypatch):
    """The wiring, not the check: a waypoint written 15 s off the card must
    surface as a SAY/DO warning on the BUILD, through saydo.run."""
    real = timing.apply_to_group

    def drifted(group, tl, locked=False, offset_s=0):
        n = real(group, tl, locked=locked, offset_s=offset_s)
        if not locked:
            for p in group.points:
                if p.name == "IP":
                    p.ETA += 15
        return n

    monkeypatch.setattr(timing, "apply_to_group", drifted)
    b = StarterBuilder(_recipe("gun_belt_strike", seed=7))
    b.build()
    assert any(w.startswith("SAY/DO:") and "IP" in w and "carries ETA" in w
               for w in b.warnings), b.warnings


def test_the_builder_ui_carries_the_timing_controls():
    from ui_source import ui_source
    src = ui_source()
    for el in ('id="timing_anchor"', 'id="timing_at"', 'id="timing_hold_min"',
               'id="timing_coach"', 'id="timing_package"', 'id="timing_opts"'):
        assert el in src, el
    # share links carry the defaults; the reader sends them only with a route
    assert 'timing_anchor:"takeoff",timing_at:null,timing_hold_min:0,timing_coach:false,timing_package:false' in src
    assert "if (r.bb_route){" in src and "r.timing_at = (r.timing_anchor !== 'takeoff' && at) ? at : null;" in src


def test_the_timing_flag_block_overlaps_no_other():
    """Every coach claims a block; collisions ship silently. 8860-8879 sits
    between aar_hud (8840-8859) and wk_coach (8880-8899)."""
    from missiongen import aar_grade, aar_hud, wk_coach, wk_brief, cq_coach, gates, formation
    mine = set(range(8860, 8880))
    used = {timing_coach.arrive_flag(n) for n in timing_coach.POINTS}
    used |= {timing_coach.grade_flag(n, k) for n in timing_coach.POINTS
             for k in ("early", "ontime", "late")}
    used |= {timing_coach.F_DEBRIEF, timing_coach.F_ARM}
    assert used <= mine and len(used) == 4 + 12 + 2
    others = set(range(aar_hud.F_ARM, aar_hud.F_ARM + 20))
    others |= {v for k, v in vars(aar_grade).items() if k.startswith("F_") and isinstance(v, int)}
    others |= set(range(wk_coach.F_PHASE, wk_coach.F_PHASE + wk_coach.F_PHASE_MAX)) | {wk_coach.F_ARM}
    others |= set(range(wk_brief.F_CONT, wk_brief.F_DONE + 1))
    others |= set(range(8940, 8980)) | {gates.F_START, gates.F_DONE, gates.F_REMIND}
    others |= {formation.FORMATION_FLAG}
    assert not (mine & others), sorted(mine & others)
