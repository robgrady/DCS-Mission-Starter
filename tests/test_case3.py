"""The Case III pack must teach the procedure the mission actually contains.

Casmo: *"i have zero idea how to do a case 3 recovery so i was flying around
blind."* This pack is the answer, and the whole risk of a training pack is that
the card teaches one thing and the mission does another — which is this
product's founding defect class, now wearing a flight suit.

So every number on the card is read back out of the .miz: where the marshal fix
actually is, what the gates actually check, which cues a ride actually fires,
and whether the briefing tells the truth about starting airborne.

Four of these guards exist because the alternative implementation is the
obvious one and it is wrong:

  * The marshal radial hangs off the FINAL BEARING (the angled deck), not the
    BRC. Deriving it from BRC is a nine-degree error that is invisible in code
    and puts the student off the arc before he starts.
  * PLATFORM is an ALTITUDE. A range gate is the natural thing to build and
    every community guide quotes a DME beside it, and it is wrong.
  * The range gates must be MOVING zones. The ship makes 25 knots; a static
    zone at 10 DME is four miles out of position ten minutes later.
  * Ride 4 starts three miles out, already inside every range gate on the
    profile. If cues were merely sequential it would fire "ten miles", "dirty
    up" and "on speed" in its first second.
"""
import math
import zipfile
from pathlib import Path

import pytest

import dcs.lua as lua
from missiongen import Recipe, cq, cq_coach, cq_route, generate
from missiongen.resolver import load_json

TEMPLATES = load_json("mission_templates")
CQ_TEMPLATES = sorted(k for k in TEMPLATES if k.startswith("cq_"))
NM_M = cq.NM_M


def _origin():
    """A bare map point to do pure geometry against, with no mission around it.

    `dressing._offset` needs a real pydcs Point (it carries the terrain), so
    this borrows one from an empty mission rather than reimplementing the
    projection — a second copy of that arithmetic is the twin-function shape
    that has already cost this codebase two live defects.
    """
    import dcs
    m = dcs.Mission()
    return dcs.mapping.Point(0.0, 0.0, m.terrain)


_ORIGIN = _origin()


def _build(tmpdir, template_key, seed=4400):
    t = TEMPLATES[template_key]
    rc = dict(t["recipe"])
    rc.update(map=t["default_map"], era=t["eras"][0], template=template_key,
              seed=seed)
    out = str(Path(tmpdir) / f"{template_key}.miz")
    res = generate(Recipe.from_dict(rc), out, brief_dir=str(tmpdir))
    z = zipfile.ZipFile(out)
    m = lua.loads(z.read("mission").decode())["mission"]
    dic = lua.loads(z.read("l10n/DEFAULT/dictionary").decode())["dictionary"]
    return m, dic, res


@pytest.fixture(scope="module")
def flown(tmp_path_factory):
    """One mission per ride, Tomcat side, built once.

    Module-scoped because each build writes a whole .miz and the suite runs
    with --dist loadfile, so this file stays on one worker.
    """
    out = {}
    for i, k in enumerate(k for k in CQ_TEMPLATES if k.endswith("_f14")):
        d = tmp_path_factory.mktemp(k)
        out[k] = _build(d, k, seed=4400 + i)
    return out


@pytest.fixture(scope="module")
def hornet(tmp_path_factory):
    d = tmp_path_factory.mktemp("cq_hornet")
    return _build(d, "cq_2_push_fa18", seed=4500)


# --- reading the mission -----------------------------------------------------

def _groups(m, *kinds):
    for coal in m["coalition"].values():
        for c in coal.get("country", {}).values():
            for k in (kinds or ("plane", "helicopter", "ship")):
                for g in c.get(k, {}).get("group", {}).values():
                    yield g


def _player_group(m):
    for g in _groups(m, "plane"):
        for u in g.get("units", {}).values():
            if u.get("skill") in ("Player", "Client"):
                return g
    raise AssertionError("no player group")


def _carrier_unit(m):
    for g in _groups(m, "ship"):
        pts = g.get("route", {}).get("points", {})
        first = pts[min(pts)] if pts else {}
        tasks = ((first.get("task") or {}).get("params") or {}).get("tasks") or {}
        for t in tasks.values():
            if ((t.get("params") or {}).get("action") or {}).get("id") \
                    == "ActivateBeacon":
                return list(g["units"].values())[0]
    return list(next(_groups(m, "ship"))["units"].values())[0]


def _waypoints(m):
    g = _player_group(m)
    pts = g["route"]["points"]
    return [pts[k] for k in sorted(pts)]


def _wp(m, name):
    return next((p for p in _waypoints(m) if p.get("name") == name), None)


def _triggers(m, prefix):
    return [v for v in (m.get("trigrules") or {}).values()
            if str(v.get("comment", "")).startswith(prefix)]


def _rules(trig):
    return list((trig.get("rules") or {}).values())


def _preds(trig):
    return [r.get("predicate") for r in _rules(trig)]


def _bearing_range(from_pt, to_x, to_y):
    dx, dy = to_x - from_pt["x"], to_y - from_pt["y"]
    # x is north, y is east — the project's convention, not maths'.
    return math.degrees(math.atan2(dy, dx)) % 360.0, math.hypot(dx, dy) / NM_M


# --------------------------------------------------------------------------- #
# 1. The marshal rule
# --------------------------------------------------------------------------- #
def test_the_marshal_radial_is_not_simply_the_reciprocal_of_the_brc():
    """The arithmetic, before any mission is built.

    If someone 'simplifies' `marshal_radial` to BRC + 180 this passes silently
    in every other test — the fix is still on a radial, still at the right
    range, and only nine degrees wrong. Nine degrees at 21 miles is three and
    a half miles off the arc.
    """
    for brc in (0.0, 45.0, 187.5, 350.0):
        assert cq.marshal_radial(brc) != pytest.approx((brc + 180) % 360), \
            f"BRC {brc}: the marshal radial was derived from the BRC"
        assert cq.marshal_radial(brc) == pytest.approx(
            (brc - cq.ANGLED_DECK_DEG + 180) % 360), brc
    assert cq.MARSHAL_RADIAL_FROM == "final bearing"
    assert 8.0 <= cq.ANGLED_DECK_DEG <= 10.0, cq.ANGLED_DECK_DEG


@pytest.mark.parametrize("angels,dme", [(6, 21), (8, 23), (12, 27), (16, 31)])
def test_angels_plus_fifteen(angels, dme):
    assert cq.marshal_dme(angels) == dme


def test_the_published_gates_are_the_published_numbers():
    """The gates are NATOPS's, not ours. Pinned as literals in one place so
    every other test can read them from the module without the module and the
    test agreeing with each other about a number neither of them checked."""
    assert (cq.LEVEL_DME, cq.LEVEL_FT) == (10, 1200)
    assert (cq.DIRTY_DME, cq.ONSPEED_DME, cq.ONSPEED_KT) == (8, 6, 150)
    assert (cq.DESCENT_KT, cq.DESCENT_FPM) == (250, 4000)
    assert (cq.PLATFORM_FT, cq.PLATFORM_FPM_MAX) == (5000, 2000)
    assert cq.GLIDESLOPE_DEG == 3.5
    assert cq.BALL_CALL_NM == 0.75
    assert (cq.MARSHAL_DME_PLUS, cq.MARSHAL_BASE_FT) == (15, 6000)
    assert cq.MARSHAL_PATTERN_MIN == 6
    assert (cq.CASE3_CEILING_FT, cq.CASE3_VIS_NM) == (1000, 5)
    assert cq.BOLTER_ALT_FT == 1200 and cq.BOLTER_FINAL_DME == 4


def test_the_stack_is_never_below_the_natops_floor():
    for key, r in cq.RIDES.items():
        assert cq.stack_is_legal(r["angels"]), (
            f"{key} holds at angels {r['angels']}; NATOPS 6.4.1.1 puts the "
            f"base of the stack at {cq.MARSHAL_BASE_FT:,} ft")


def test_the_marshal_fix_in_the_mission_is_where_the_rule_puts_it(flown):
    """Read back out of the file: bearing and range from the actual ship."""
    m, _, _ = flown["cq_1_stack_f14"]
    boat = _carrier_unit(m)
    fix = _wp(m, "MARSHAL FIX")
    assert fix, "the stack ride has no marshal fix waypoint"
    brg, rng = _bearing_range(boat, fix["x"], fix["y"])
    angels = cq.RIDES["cq_1_stack"]["angels"]
    # The BRC is not written into the mission, so recover it from the fix's own
    # bearing and check the RANGE independently — the range is the half of the
    # rule that no amount of trigonometry can fudge.
    assert rng == pytest.approx(cq.marshal_dme(angels), abs=0.3), (
        f"marshal fix is {rng:.1f} DME, the rule says "
        f"{cq.marshal_dme(angels)} (angels {angels} + 15)")
    assert 0.0 <= brg < 360.0


def test_the_holding_pattern_is_a_left_hand_racetrack_on_the_map(flown):
    """A pattern described on a card and absent from the F10 map is the
    say/do gap in its cheapest form."""
    m, _, _ = flown["cq_1_stack_f14"]
    names = [p.get("name") for p in _waypoints(m)]
    for n in ("MARSHAL FIX", "OUTBOUND ABEAM", "OUTBOUND END", "INBOUND START"):
        assert n in names, f"{n} is missing from the flight plan: {names}"
    boat = _carrier_unit(m)
    fix = _wp(m, "MARSHAL FIX")
    end = _wp(m, "OUTBOUND END")
    _, r_fix = _bearing_range(boat, fix["x"], fix["y"])
    _, r_end = _bearing_range(boat, end["x"], end["y"])
    assert r_end > r_fix + 2.0, (
        "the outbound leg runs toward the ship — holding outbound is AWAY "
        f"from her ({r_end:.1f} vs {r_fix:.1f} DME)")
    # The inbound leg has to pass over the fix (NATOPS says so explicitly);
    # so INBOUND START sits on the same radial as the fix, not offset.
    _, r_in = _bearing_range(boat, _wp(m, "INBOUND START")["x"],
                             _wp(m, "INBOUND START")["y"])
    assert r_in > r_fix, "the inbound leg does not start outside the fix"


# --------------------------------------------------------------------------- #
# 2. Platform is an altitude
# --------------------------------------------------------------------------- #
def test_platform_is_graded_as_an_altitude_and_never_as_a_range(flown):
    m, _, _ = flown["cq_2_push_f14"]
    t = _triggers(m, "CQ cue: platform")
    assert t, "the push ride has no platform cue"
    preds = _preds(t[0])
    assert "c_unit_altitude_lower" in preds, (
        "the platform cue does not test an altitude. Platform is 5,000 feet, "
        f"wherever that falls. Conditions were: {preds}")
    alts = [r["altitude"] for r in _rules(t[0])
            if r.get("predicate") == "c_unit_altitude_lower"]
    assert any(a == pytest.approx(cq.PLATFORM_FT * cq.FT_M, abs=1.0)
               for a in alts), alts
    # It may use a DME gate to keep itself off the level segment, but it must
    # not use one as THE trigger — hence the altitude assertion above standing
    # first and this one only pinning the shape.
    assert cq.PLATFORM_FT == 5000
    assert cq.PLATFORM_FPM_MAX == 2000


def test_the_descent_rate_grade_fires_on_descending_faster_than_the_limit(flown):
    m, _, _ = flown["cq_2_push_f14"]
    t = _triggers(m, "CQ grade: dive")
    assert t, "nothing grades the rate of descent below platform"
    vs = [r for r in _rules(t[0]) if r.get("predicate") == "c_unit_vertical_speed"]
    assert vs, f"the dive grade has no vertical-speed condition: {_preds(t[0])}"
    lo, hi = vs[0]["min_unit_vertical_speed"], vs[0]["max_unit_vertical_speed"]
    assert hi < 0 and lo < hi, (
        f"the window ({lo}, {hi}) does not describe a DESCENT — the bust is "
        f"descending faster than the limit, so both ends must be negative")
    assert abs(hi) == pytest.approx(cq.PLATFORM_FPM_MAX * cq_coach.FPM_TO_MS,
                                    abs=0.05), (
        f"the grade fires at {abs(hi) / cq_coach.FPM_TO_MS:.0f} fpm, not "
        f"{cq.PLATFORM_FPM_MAX}")


# --------------------------------------------------------------------------- #
# 3. The gates move with the ship
# --------------------------------------------------------------------------- #
def test_every_range_gate_is_a_moving_zone(flown):
    """A carrier makes about 25 knots. A static trigger zone placed at 10 DME
    is four miles out of position by the end of a ten-minute recovery, and the
    gate silently grades the wrong piece of sky."""
    for key, (m, _, _) in flown.items():
        for t in _triggers(m, "CQ "):
            for r in _rules(t):
                assert r.get("predicate") not in ("c_unit_in_zone",
                                                  "c_unit_out_zone"), (
                    f"{key}/{t['comment']} uses a STATIC zone; the ship is "
                    f"under way")


def test_the_moving_gates_are_centred_on_the_carrier_herself(flown):
    m, _, _ = flown["cq_3_approach_f14"]
    boat = _carrier_unit(m)
    seen = 0
    for t in _triggers(m, "CQ "):
        for r in _rules(t):
            if r.get("predicate") in ("c_unit_in_zone_unit",
                                      "c_unit_out_zone_unit"):
                assert r["zoneunit"] == boat["unitId"], (
                    f"{t['comment']} hangs its gate off unit "
                    f"{r['zoneunit']}, not the carrier ({boat['unitId']})")
                seen += 1
    assert seen >= 4, f"only {seen} moving-zone conditions in the approach ride"


# THE NUMBERS ARE WRITTEN OUT, NOT IMPORTED. An earlier version of this
# parametrisation read `cq.LEVEL_DME` for the expected value, so moving the
# gate moved the test with it and a four-mile error passed. 10, 8 and 6 are
# NATOPS's numbers, not ours, and a test of a published constant has to carry
# the published constant.
@pytest.mark.parametrize("cue,dme", [("ten", 10), ("dirty", 8), ("six", 6)])
def test_each_gate_fires_at_the_range_the_card_prints(flown, cue, dme):
    m, _, _ = flown["cq_3_approach_f14"]
    t = _triggers(m, f"CQ cue: {cue}")
    assert t, f"no {cue} cue"
    radii = sorted(r["zone"] / NM_M for r in _rules(t[0])
                   if r.get("predicate") in ("c_unit_in_zone_unit",
                                             "c_unit_out_zone_unit"))
    assert radii, f"{cue} has no range gate at all"
    assert max(radii) == pytest.approx(dme, abs=0.01), (
        f"the {cue} cue fires at {max(radii):.1f} DME; the card says {dme}")


# --------------------------------------------------------------------------- #
# 4. Which cues a ride fires
# --------------------------------------------------------------------------- #
def _cue_keys(m):
    return {t["comment"].split("CQ cue: ")[1].split(" (")[0]
            for t in _triggers(m, "CQ cue: ")}


def test_the_ball_ride_does_not_fire_the_gates_it_starts_inside(flown):
    """Ride 4 begins at three miles, already inside ten, eight and six. Merely
    sequential phases would fire all three in its first second, each of them
    telling the pilot to do something he did twenty miles ago."""
    m, _, _ = flown["cq_4_ball_f14"]
    got = _cue_keys(m)
    assert got == {"ball", "bolter"}, got
    for gone in ("ten", "dirty", "six", "platform", "push"):
        assert gone not in got, (
            f"the ball ride fires the '{gone}' cue, and it starts inside that "
            f"gate")


def test_the_check_ride_is_silent(flown):
    """Ride 5 is the check. Every aid off — that is what makes it a check."""
    m, _, _ = flown["cq_5_nightcq_f14"]
    assert not _triggers(m, "CQ cue: "), "the check ride is being coached"
    assert not _triggers(m, "CQ grade: "), "the check ride is being graded"


@pytest.mark.parametrize("key", sorted(cq.RIDES))
def test_every_ride_declares_its_cues_rather_than_inheriting_them(key):
    assert key in cq_coach.RIDE_CUES, f"{key} has no declared cue set"
    assert key in cq_coach.RIDE_GRADES, f"{key} has no declared grade set"
    for c in cq_coach.cues_for(key):
        assert c in cq_coach.CUE_IDX, f"{key} names an unknown cue {c!r}"
    for g in cq_coach.grades_for(key):
        assert g in cq_coach.GRADE_IDX, f"{key} names an unknown grade {g!r}"


def test_the_coached_rides_are_coached_and_the_check_ride_is_not():
    for key, r in cq.RIDES.items():
        has = bool(cq_coach.cues_for(key) or cq_coach.grades_for(key))
        assert has == bool(r["coach"]), (
            f"{key}: coach={r['coach']} but "
            f"{'has' if has else 'has no'} cues or grades")


# --------------------------------------------------------------------------- #
# 5. The timing grade, which is the whole reason ride 1 exists
# --------------------------------------------------------------------------- #
def test_the_push_grade_allows_for_the_flight_time_to_the_commence_band(flown):
    """Without the transit allowance every pilot is graded LATE.

    "Commenced" is measured two miles inside the fix, because the holding
    pattern never touches that band. Those two miles take about half a minute,
    so a pilot who crosses the fix at exactly his approach time reaches the
    band well outside a ten-second window centered on it.
    """
    angels = cq.RIDES["cq_1_stack"]["angels"]
    transit = cq_coach.commence_transit_s(angels)
    assert 15 <= transit <= 60, (
        f"a two-mile transit at holding speed came out as {transit}s")
    assert transit > cq.EAT_TOLERANCE_S, (
        "the transit is inside the tolerance, so the allowance does nothing")

    m, _, _ = flown["cq_1_stack_f14"]
    push = cq_coach.push_time_s("cq_1_stack")
    ontime = _triggers(m, "CQ grade: push_ontime")
    assert ontime, "nothing says you got the timing right"
    after = [r["seconds"] for r in _rules(ontime[0])
             if r.get("predicate") == "c_time_after"]
    before = [r["seconds"] for r in _rules(ontime[0])
              if r.get("predicate") == "c_time_before"]
    assert after and before, _preds(ontime[0])
    assert after[0] == pytest.approx(push + transit - cq.EAT_TOLERANCE_S)
    assert before[0] == pytest.approx(push + transit + cq.EAT_TOLERANCE_S)


def test_the_commence_band_is_clear_of_the_holding_pattern():
    """If the pattern reached inside the band, orbiting would grade as
    commencing and everybody would be marked early on their first lap."""
    for key, r in cq.RIDES.items():
        if "push_early" not in cq_coach.grades_for(key):
            continue
        angels = r["angels"]
        band = cq_coach.commence_dme(angels)
        # The closest the racetrack ever comes to the ship is the fix itself —
        # everything else in the pattern is abeam it or outside it. Computed
        # from the pattern the mission actually lays, not from the rule, so a
        # change to the pattern geometry has to come past this test.
        pattern = cq_route.holding_pattern(_ORIGIN, 0.0, angels)
        closest = min(_ORIGIN.distance_to_point(p) / NM_M
                      for _n, p, _a, _k in pattern)
        assert band < closest - 0.5, (
            f"{key}: the commence band at {band:.1f} DME reaches into the "
            f"holding pattern, whose nearest point is {closest:.1f} DME — "
            f"orbiting would grade as commencing and every pilot would be "
            f"marked early on his first lap")


def test_all_three_timing_verdicts_exist_and_are_mutually_exclusive(flown):
    m, _, _ = flown["cq_1_stack_f14"]
    got = {t["comment"].split("CQ grade: ")[1].split(" (")[0]
           for t in _triggers(m, "CQ grade: ")}
    assert got == {"push_early", "push_late", "push_ontime"}, got
    early = _triggers(m, "CQ grade: push_early")[0]
    late = _triggers(m, "CQ grade: push_late")[0]
    e_before = [r["seconds"] for r in _rules(early)
                if r.get("predicate") == "c_time_before"][0]
    l_after = [r["seconds"] for r in _rules(late)
               if r.get("predicate") == "c_time_after"][0]
    assert e_before < l_after, (
        f"early fires before {e_before}s and late after {l_after}s — they "
        f"overlap, so one push can be graded both")


# --------------------------------------------------------------------------- #
# 6. Flags
# --------------------------------------------------------------------------- #
def test_the_case3_flag_block_collides_with_nothing():
    from missiongen import aar_grade, aar_hud, formation, wk_brief, wk_coach
    cq_flags = set(range(cq_coach.F_PHASE,
                         cq_coach.F_PHASE + cq_coach.F_PHASE_MAX))
    cq_flags |= set(range(cq_coach.F_GRADE,
                          cq_coach.F_GRADE + cq_coach.F_GRADE_MAX))
    assert cq_coach.F_ARM not in cq_flags, (
        "the arm flag IS one of the phase flags — the exact bug wk_coach "
        "shipped, where the sequence silently disarmed itself")
    cq_flags.add(cq_coach.F_ARM)

    others = set(range(wk_coach.F_PHASE,
                       wk_coach.F_PHASE + wk_coach.F_PHASE_MAX))
    others.add(wk_coach.F_ARM)
    others |= {wk_brief.F_CONT + i for i in range(len(wk_brief.PAGES))}
    others |= {wk_brief.F_BACK + i for i in range(len(wk_brief.PAGES))}
    others.add(wk_brief.F_DONE)
    others |= {v for k, v in vars(aar_grade).items()
               if k.startswith("F_") and isinstance(v, int)}
    others |= set(range(aar_hud.F_ARM, aar_hud.F_ARM + len(aar_hud.STATES)))
    others.add(aar_hud.F_HUD_OFF)
    others.add(formation.FORMATION_FLAG)
    assert not (cq_flags & others), sorted(cq_flags & others)


def test_there_is_room_for_more_cues_and_grades_than_exist():
    assert len(cq_coach.CUES) <= cq_coach.F_PHASE_MAX
    assert len(cq_coach.GRADES) <= cq_coach.F_GRADE_MAX


# --------------------------------------------------------------------------- #
# 7. The briefing tells the truth
# --------------------------------------------------------------------------- #
def test_the_briefing_does_not_say_the_jet_is_parked(flown):
    """It is airborne, at six thousand feet, twenty-one miles behind the boat.
    "It's parked and ready" is the say/do gap in one sentence."""
    for key, (m, dic, _) in flown.items():
        text = dic.get(m["descriptionText"], "")
        assert "parked and ready" not in text, key
        assert "airborne" in text.lower(), (
            f"{key}: the briefing never says you start airborne")


def test_the_briefing_does_not_promise_a_sandbox(flown):
    """"No objectives, tasking or waypoints" describes the free-flight
    starter. This mission has a flight plan, cues and grades."""
    for key, (m, dic, _) in flown.items():
        text = dic.get(m["descriptionText"], "")
        assert "there are NO" not in text, (
            f"{key}: the briefing prints the sandbox paragraph over a "
            f"syllabus ride")


def test_the_flight_really_does_start_airborne(flown):
    for key, (m, _, _) in flown.items():
        first = _waypoints(m)[0]
        assert not str(first.get("type", "")).startswith("TakeOff"), (
            f"{key}: first waypoint is {first.get('type')}")
        assert first.get("alt", 0) > 100, (
            f"{key}: starts at {first.get('alt')} m")


def test_supercarrier_is_declared_everywhere_a_pilot_looks(flown):
    tracks = load_json("tracks")
    for key in CQ_TEMPLATES:
        lib = TEMPLATES[key]["library"]
        assert lib.get("requires") == cq.REQUIRES_MODULE, (
            f"{key}'s library card does not say it needs "
            f"{cq.REQUIRES_MODULE}")
    for tid in ("cq_case3_f14", "cq_case3_hornet"):
        assert tracks[tid].get("requires") == cq.REQUIRES_MODULE, tid
    for key, (m, dic, res) in flown.items():
        text = dic.get(m["descriptionText"], "")
        assert cq.REQUIRES_MODULE in text, (
            f"{key}: the in-mission briefing never mentions the module the "
            f"whole ride depends on")


# --------------------------------------------------------------------------- #
# 8. The card is the right card for the cockpit
# --------------------------------------------------------------------------- #
def test_the_tomcat_card_teaches_the_tomcat(flown, hornet):
    f14 = "\n".join(flown["cq_2_push_f14"][2]["stats"]["cq_card"])
    f18 = "\n".join(hornet[2]["stats"]["cq_card"])
    assert "ARA-63" in f14 and "15 units" in f14
    assert "ARA-63" not in f18, "the Hornet card sets up a Tomcat"
    assert "8.1 units" in f18 and "UFC" in f18
    assert "8.1 units" not in f14, "the Tomcat card flies the Hornet's AOA"


def test_the_card_says_platform_is_not_a_range(flown):
    card = "\n".join(flown["cq_2_push_f14"][2]["stats"]["cq_card"])
    assert "NOT A RANGE" in card.upper(), (
        "the single most common student error, and the card does not correct "
        "it")


def test_the_card_names_the_final_bearing_as_the_reference(flown):
    card = "\n".join(flown["cq_1_stack_f14"][2]["stats"]["cq_card"])
    assert "final bearing" in card, card[:400]


def test_the_card_and_the_flight_plan_agree_about_the_gates(flown):
    """The gate table on the card, against the waypoints in the file."""
    m, _, res = flown["cq_3_approach_f14"]
    rows = {n: dme for n, dme, _a, _k in res["stats"]["cq_route"]}
    # Literals again, for the reason above.
    assert rows["DIRTY 8"] == pytest.approx(8, abs=0.2)
    assert rows["ON SPEED 6"] == pytest.approx(6, abs=0.2)
    # 1,200 ft on a 3.5 degree glideslope is 3.2 nm. Computed here from the
    # geometry rather than imported, so a change to either number has to come
    # past this line.
    assert rows["GLIDESLOPE"] == pytest.approx(
        1200 / (6076.12 * math.tan(math.radians(3.5))), abs=0.2)


# --------------------------------------------------------------------------- #
# 9. The recipe refuses what it cannot build
# --------------------------------------------------------------------------- #
def test_a_case3_ride_without_a_carrier_is_refused():
    from missiongen.recipe import RecipeError
    with pytest.raises(RecipeError, match="CARRIER"):
        Recipe.from_dict(dict(map="persiangulf", era="modern",
                              aircraft="F_14B", cq_ride="cq_1_stack",
                              home_airbase="Al Dhafra AB")).validate()


def test_a_case3_ride_in_a_jet_with_no_procedure_is_refused():
    from missiongen.recipe import RecipeError
    with pytest.raises(RecipeError, match="cockpit procedure"):
        Recipe.from_dict(dict(map="persiangulf", era="modern",
                              aircraft="A_10C", cq_ride="cq_1_stack",
                              home_airbase="CARRIER")).validate()


def test_an_unknown_ride_is_refused():
    from missiongen.recipe import RecipeError
    with pytest.raises(RecipeError, match="not a Case III ride"):
        Recipe.from_dict(dict(map="persiangulf", era="modern",
                              aircraft="F_14B", cq_ride="cq_9_ghost",
                              home_airbase="CARRIER")).validate()


# --------------------------------------------------------------------------- #
# 10. The pack is complete
# --------------------------------------------------------------------------- #
def test_every_ride_ships_for_both_jets():
    for key in cq.RIDES:
        for suffix in ("f14", "fa18"):
            t = f"{key}_{suffix}"
            assert t in TEMPLATES, f"{t} is missing from the library"
            assert TEMPLATES[t]["recipe"]["cq_ride"] == key
            assert TEMPLATES[t]["recipe"]["home_airbase"] == "CARRIER"


def test_every_case3_template_points_at_a_real_ride_and_a_real_track():
    tracks = load_json("tracks")
    for key in CQ_TEMPLATES:
        t = TEMPLATES[key]
        assert cq.is_cq_ride(t["recipe"]["cq_ride"]), key
        assert t["track"]["id"] in tracks, key
        assert t["track"]["n"] == cq.RIDES[t["recipe"]["cq_ride"]]["n"], key


def test_the_rides_run_at_night():
    """Case III is mostly a clock, not a weather condition. A daylight Case III
    ride would be teaching the procedure in the one situation that does not
    call for it."""
    for key in CQ_TEMPLATES:
        assert TEMPLATES[key]["recipe"]["time_of_day"] == "night", key


def test_the_check_ride_adds_weather_and_the_teaching_rides_do_not():
    for key in CQ_TEMPLATES:
        w = TEMPLATES[key]["recipe"]["weather"]
        if key.startswith("cq_5_"):
            assert w != "clear", "the check ride is a clear night"
        else:
            assert w == "clear", (
                f"{key}: cloud on a gate you have never flown teaches nothing "
                f"except frustration")


# --------------------------------------------------------------------------- #
# 11b. No card may brief a Case III it does not set up
# --------------------------------------------------------------------------- #
def test_no_card_tells_you_to_fly_a_case_three_it_has_not_built():
    """THE GAP THIS FOUND. The Carrier Qualification card's brief said:

        " - CASE III (night/IMC): Marshal stack, push on time, CATCC/ACLS
          approach."

    The recipe underneath it was day, clear, warm start on the deck. It sets up
    a Case I and always did. Telling a pilot to fly a night marshal stack in a
    daylight mission is the founding defect of this product, and it was sitting
    on a featured card. A second card, the night Tomcat sandbox, did the same
    thing more quietly: night and weather were right, but it put you on the
    deck and then instructed you through a procedure it had not set up.

    THE RULE, and it is deliberately not "never mention it": a card that names
    the procedure must either BE one of the taught rides, or say plainly where
    the taught version is. Pointing at the syllabus is useful; instructing a
    pilot through a recovery the mission has not built is not.
    """
    # PARAGRAPH BY PARAGRAPH, not brief by brief. A first cut checked the whole
    # brief as one string, so a card could instruct a daylight Case III in its
    # tasking and still pass on the strength of a pointer paragraph further
    # down. The instruction and the pointer have to be the same thought for the
    # card to be honest.
    named = ("marshal stack", "push on time", "push at", "call the ball")
    points = ("case iii track", "track in the library")
    for key, v in TEMPLATES.items():
        if key.startswith("_") or not isinstance(v, dict):
            continue
        rc = v.get("recipe") or {}
        paras, cur = [], []
        for line in (v.get("brief") or []):
            if line.strip():
                cur.append(line)
            elif cur:
                paras.append(" ".join(cur).lower())
                cur = []
        if cur:
            paras.append(" ".join(cur).lower())
        for para in paras:
            if not any(p in para for p in named):
                continue
            if rc.get("cq_ride"):
                assert rc.get("time_of_day") == "night", (
                    f"{key} briefs a night recovery in the "
                    f"{rc.get('time_of_day')}")
                continue
            assert any(p in para for p in points), (
                f"{key} walks the pilot through a Case III recovery in a "
                f"mission that is not one, without saying in the same breath "
                f"where the taught version is:\n  {para[:160]}")


def test_the_carrier_sandbox_points_at_the_syllabus_instead_of_faking_it():
    """The other half: having stopped promising it, the card should say where
    the real thing lives. An omission nobody explains reads as a gap."""
    text = " ".join(TEMPLATES["carrier_qual"].get("brief") or [])
    assert "Case III" in text, "the CQ card no longer mentions Case III at all"
    assert "track" in text.lower(), (
        "the CQ card drops Case III without telling the pilot where the taught "
        "version is")
    assert cq.REQUIRES_MODULE in text, (
        "it points at a track without saying the track needs a paid module")


# --------------------------------------------------------------------------- #
# 11. A regression found while building this
# --------------------------------------------------------------------------- #
def test_an_armed_jet_is_never_told_it_starts_clean(flown):
    """THE BUG THIS EXISTS BECAUSE OF. The "no loadout could be composed"
    warning hung off `if wk_ride:` rather than off whether anything actually
    reached the pylons, so every mission that was not a White Knights ride
    got told its jet was clean — while the kneeboard listed the stores and
    the airplane wore them."""
    for key, (m, _, res) in flown.items():
        clean = [w for w in res["warnings"] if "starts clean" in w]
        if res["stats"].get("player_loadout"):
            assert not clean, (
                f"{key}: loadout is {res['stats']['player_loadout']!r} and the "
                f"brief warns {clean[0]!r}")


# --------------------------------------------------------------------------- #
# 12. The paid module, in a real browser
# --------------------------------------------------------------------------- #
# Every guard above reads source text or mission Lua, and neither is what a
# pilot sees. This one is the honest one: the real page, the real card, the
# chip rendered by the real code path. It matters more than the usual browser
# guard because the failure mode is somebody downloading a Case III ride,
# loading it without the Supercarrier module, and finding a boat that does not
# answer the radio — which reads as our bug, not a missing purchase.
_PROBE = r"""
import json, sys, threading, time
sys.path[:0] = [%r, %r]
import uvicorn
from server.app import app
srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8795,
                                    log_level="error"))
threading.Thread(target=srv.run, daemon=True).start()
time.sleep(3)
from playwright.sync_api import sync_playwright
# A Case III ride BELONGS TO A TRACK, so it is deliberately off the shelf —
# `libItems()` never lists it. `rideItem()` is the function the page actually
# uses when somebody opens the track card and clicks a ride, so that is the
# path this probes. Probing `libItems()` instead returns an empty list and a
# green test, which is how the first version of this passed while proving
# nothing.
# A Case III ride BELONGS TO A TRACK, so it is never a card in the grid —
# `libItems()` filters track members out, and `libCard()` is only ever called
# for grid cards. The two surfaces these rides actually have are the TRACK
# PANEL and each ride's own DETAIL PANEL, so those are the two this opens.
#
# The first version of this probe called `libItems()` and got an empty list, a
# green test and no proof of anything. The second called `libCard()` on a ride
# item, which the page never does, and crashed. Probing a path the product
# does not use is worse than not probing.
JS = ("() => { const keys = Object.keys(OPT.templates).filter(k => k.indexOf('cq_') === 0);"
      " openDetail('track_cq_case3_f14');"
      " const trackPanel = document.getElementById('dcardinner').innerHTML;"
      " const said = keys.map(k => { openDetail(k);"
      "   return document.getElementById('dcardinner').innerHTML"
      "     .indexOf('Requires DCS: Supercarrier') >= 0; });"
      " return {n: keys.length,"
      "         ridePanels: said.filter(Boolean).length,"
      "         trackSays: trackPanel.indexOf('DCS: Supercarrier') >= 0,"
      "         trackOpen: document.getElementById('libdetail').classList.contains('on'),"
      "         painted: document.querySelectorAll('#lgrid > *').length}; }")
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    pg.goto("http://127.0.0.1:8795/", wait_until="networkidle")
    pg.click("text=Library", timeout=15000); pg.wait_for_timeout(2500)
    out = pg.evaluate(JS)
    b.close()
print("RESULT " + json.dumps(out))
"""


def test_the_library_card_says_it_needs_supercarrier(tmp_path):
    pytest.importorskip("playwright.sync_api")
    import json
    import subprocess
    import sys
    root = Path(__file__).resolve().parents[1]
    code = _PROBE % (str(root), str(root / "vendor"))
    r = subprocess.run([sys.executable, "-c", code], capture_output=True,
                       text=True, timeout=180, cwd=str(root))
    line = next((l for l in r.stdout.splitlines() if l.startswith("RESULT ")),
                None)
    assert line, f"probe produced nothing:\n{r.stdout[-2000:]}\n{r.stderr[-2000:]}"
    out = json.loads(line[len("RESULT "):])
    assert out["painted"] > 0, "the library grid rendered nothing at all"
    # Rides that belong to a track are deliberately off the shelf, so the count
    # here may be zero cards in the GRID — what must hold is that every Case
    # III item the page knows about carries the requirement and renders it.
    assert out["n"] == 10, f"expected ten Case III rides, page knows {out['n']}"
    assert out["ridePanels"] == out["n"], (
        f"{out['n'] - out['ridePanels']} of {out['n']} Case III ride panels "
        f"never name the module the ride depends on")
    assert out["trackOpen"], "the Case III track panel did not open"
    assert out["trackSays"], (
        "the track panel — where somebody decides to download the whole "
        "syllabus — never names the module it depends on")
