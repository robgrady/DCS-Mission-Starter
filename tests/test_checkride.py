"""Check rides: the instructor's framework, abbreviated for a game.

WHAT THIS FILE HOLDS THE PRODUCT TO
-----------------------------------
  1. the arithmetic — a ratio with no division: paired counters (in x10 vs
     total x9 is 90 %) compared with FlagIsLessThanFlag, in flag block
     8700–8749 and nowhere else;
  2. the framework — items read off LEAD's own state (level / turning /
     climbing), a timed rejoin after the pitchout, three critical items,
     U / F / G / E per item and Q / Q- / U overall, and SILENCE on the
     check (no coach) versus coach-on for the pre-check;
  3. the profile — pre-check and check fly the same legs, and the pitchout
     is called when the legs are done;
  4. the timing check — the timing coach goes silent, adds the E window,
     prints letters, and treats a late anchor as critical;
  5. the course — the Formation and Timing phases end in a check, the AAR
     phase's check is the qualification ride, the kit speaks U/F/G/E.
"""
from __future__ import annotations

import pytest
import dcs.action as A
from pathlib import Path

from missiongen import Recipe, checkride, formation, timing_coach
from missiongen.builder import StarterBuilder
from missiongen.resolver import load_json
from missiongen.templates import effective_recipe

TEMPLATES = load_json("mission_templates")


def _recipe(key, seed=5, **over):
    v = TEMPLATES[key]
    era = "coldwar" if "coldwar" in (v.get("eras") or []) else (v.get("eras") or ["modern"])[0]
    rc = effective_recipe(key, era)
    rc.setdefault("map", v.get("default_map", "caucasus"))
    rc.update(era=era, template=key, seed=seed)
    rc.update(over)
    return Recipe.from_dict(rc)


def _build(key, **over):
    b = StarterBuilder(_recipe(key, **over))
    m = b.build()
    return b, m


def _by(m, prefix):
    return {t.comment: t for t in m.triggerrules.triggers if t.comment.startswith(prefix)}


def _said(t):
    return " ".join(str(a.text) for a in t.actions if hasattr(a, "text"))


def _shown(m, t):
    """The art file a trigger draws, by stem (v1.104.0: cards are pictures).

    Resolved through the mission's resource map, the way DCS resolves it, so a
    trigger that names a key the map does not hold fails here instead of in
    the cockpit."""
    files = m.map_resource.files.get("DEFAULT", {})
    stems = []
    for a in t.actions:
        if isinstance(a, A.PictureToGroup):
            path = files.get(a.file_res_key.key, "")
            stems.append(Path(path).stem)
    return stems


def _flags(t):
    out = set()
    for a in t.actions:
        v = a.dict().get("flag")
        if isinstance(v, int):
            out.add(v)
    for c in t.rules:
        d = c.dict()
        for k in ("flag", "flag2"):
            if isinstance(d.get(k), int):
                out.add(d[k])
    return out


@pytest.fixture(scope="module")
def check():
    return _build("form_check", aircraft="F_4E_45MC")


@pytest.fixture(scope="module")
def precheck():
    return _build("form_precheck", aircraft="F_4E_45MC")


# --------------------------------------------------------------------------- #
# 1. arithmetic and flags
# --------------------------------------------------------------------------- #
def test_the_ladder_is_ninety_seventy_five_fifty():
    assert checkride.LADDER == (("E", 10, 9), ("G", 4, 3), ("F", 2, 1))
    for _g, a, b in checkride.LADDER:
        assert a > b


def test_the_counters_grow_by_the_ladder_and_compare_flag_to_flag(check):
    b, m = check
    by = _by(m, "Check")
    tot = by["Check: level total (0)"]
    inn = by["Check: level in band (0)"]
    f = checkride.item_flags("level")
    incs = {a.dict()["flag"]: a.dict()["value"] for a in tot.actions}
    assert incs == {f["e_tot"]: 9, f["g_tot"]: 3, f["f_tot"]: 1}
    incs = {a.dict()["flag"]: a.dict()["value"] for a in inn.actions}
    assert incs == {f["e_in"]: 10, f["g_in"]: 4, f["f_in"]: 2}
    # in-band adds the band condition to the same lead-state conditions
    assert len(inn.rules) == len(tot.rules) + 1
    e = by["Check card: level E"]
    d = [c.dict() for c in e.rules if c.dict().get("predicate") == "c_flag_less_flag"]
    assert d and d[0]["flag"] == f["e_tot"] and d[0]["flag2"] == f["e_in"]


def test_every_flag_lives_in_the_check_block_and_no_other(check):
    b, m = check
    flags = set()
    for t in m.triggerrules.triggers:
        if t.comment.startswith("Check"):
            flags |= _flags(t)
    assert flags and min(flags) >= 8700 and max(flags) <= 8749, sorted(flags)
    assert max(flags) == checkride.F_LAST
    # ...and the formation coach's flag is not touched by the check
    assert formation.FORMATION_FLAG not in flags


# --------------------------------------------------------------------------- #
# 2. the framework
# --------------------------------------------------------------------------- #
def test_items_are_read_off_lead_not_the_student(check):
    b, m = check
    lead = next(g for c in m.coalition["blue"].countries.values() for g in c.plane_group
                if str(g.name) == "Formation Lead").units[0]
    me = b._player_group.units[0]
    by = _by(m, "Check")
    for name in ("level", "turns", "vertical"):
        t = by[f"Check: {name} total (0)"]
        units = {c.dict().get("unit") for c in t.rules if "unit" in c.dict()}
        assert units == {lead.id}, (name, units)
    inn = by["Check: level in band (0)"]
    z = [c.dict() for c in inn.rules if c.dict().get("predicate") == "c_unit_in_zone_unit"]
    assert z and z[0]["unit"] == me.id and z[0]["zoneunit"] == lead.id
    assert z[0]["zone"] == checkride.POSITION_M


def test_turns_count_both_ways_and_vertical_both_ways(check):
    b, m = check
    by = _by(m, "Check")
    l = by["Check: turns total (0)"].rules[-1].dict()
    r = by["Check: turns total (1)"].rules[-1].dict()
    assert l["max_unit_bank"] == -checkride.TURN_BANK and r["min_unit_bank"] == checkride.TURN_BANK
    up = by["Check: vertical total (0)"].rules[-1].dict()
    dn = by["Check: vertical total (1)"].rules[-1].dict()
    assert up["min_unit_vertical_speed"] == checkride.LEVEL_VS
    assert dn["max_unit_vertical_speed"] == -checkride.LEVEL_VS


def test_three_critical_items_each_make_the_check_a_u(check):
    b, m = check
    by = _by(m, "Check")
    coll = by["Check: CRITICAL collision band"]
    assert any(c.dict().get("zone") == checkride.COLLISION_M for c in coll.rules)
    lost = by["Check: CRITICAL lost"]
    assert any(c.dict().get("seconds") == checkride.LOST_S for c in lost.rules)
    never = by["Check: CRITICAL never rejoined"]
    assert any(c.dict().get("seconds") == checkride.REJOIN_MAX_S for c in never.rules)
    for t in (coll, lost, never):
        # SET by the action, not merely tested in the rules
        assert any(a.dict().get("predicate") == "a_set_flag" and a.dict().get("flag") == checkride.F_CRIT
                   for a in t.actions), t.comment
    u = by["Check card: overall U"]
    assert any(c.dict().get("flag") == checkride.F_CRIT for c in u.rules)
    # the overall is the one card that keeps a text line: it is what the pilot
    # writes on the gradesheet, and it should survive in the log
    assert "re-fly" in _said(u) and _shown(m, u) == ["checkride_overall_uc"]
    for k in (1, 2, 3):
        assert _shown(m, by[f"Check card: critical {k}"]) == [f"checkride_crit_{k}"]
        assert _said(by[f"Check card: critical {k}"]) == "", "picture OR text, never both"


def test_the_card_speaks_the_instructors_letters(check):
    b, m = check
    by = _by(m, "Check")
    # v1.104.0: one picture at a time, center screen, replacing the last —
    # the letter is drawn on the card, so the test checks WHICH card is drawn
    for item in ("level", "turns", "vertical"):
        for g in "EGFU":
            assert _shown(m, by[f"Check card: {item} {g}"]) == [f"checkride_{item}_{g}"]
    assert _shown(m, by["Check card: rejoin E"]) == ["checkride_rejoin_E"]
    assert _shown(m, by["Check card: overall Q-"]) == ["checkride_overall_qm"]
    assert _shown(m, by["Check card: overall Q"]) == ["checkride_overall_q"]
    # every card replaces the previous one: clearview on, never a stack
    for t in by.values():
        for a in t.actions:
            if isinstance(a, A.PictureToGroup):
                assert a.params[3] is True, (t.comment, "clearview")
    # an F sets ANY_F, a U sets ANY_U, and the overall reads them in that order
    assert checkride.F_ANY_F in _flags(by["Check card: level F"])
    assert checkride.F_ANY_U in _flags(by["Check card: level U"])
    qm = by["Check card: overall Q-"]
    assert checkride.F_ANY_F in _flags(qm) and checkride.F_ANY_U in _flags(qm)


def test_the_rejoin_is_graded_on_the_clock(check):
    b, m = check
    by = _by(m, "Check")
    clk = by["Check: rejoin clock"]
    assert any(a.dict().get("flag") == checkride.F_REJOIN_T for a in clk.actions)
    e = by["Check card: rejoin E"].rules[-1].dict()
    assert e["value"] == checkride.REJOIN_E_S + 1
    u = by["Check card: rejoin U"].rules[-1].dict()
    assert u["value"] == checkride.REJOIN_F_S
    # a rejoin needs a departure first
    assert checkride.F_WENT_OUT in _flags(by["Check: rejoined"])


def test_the_check_is_silent_and_the_precheck_is_not(check, precheck):
    _b, m = check
    # the check is graded, not coached: no ladder, no drift calls
    assert not any(t.comment.startswith("Formation ladder") for t in m.triggerrules.triggers)
    assert not any(t.comment.startswith("Formation: out of position") for t in m.triggerrules.triggers)
    said = [_said(t) for t in m.triggerrules.triggers if t.comment.startswith("Check")]
    # before the card, the check says: the brief, "joined", the pitchout, "rejoined"
    assert any("CHECK RIDE" in s for s in said), [x for x in said if x][:5]
    assert not any("PRE-CHECK" in s for s in said)
    _b2, m2 = precheck
    # the pre-check is coached by the position ladder (v1.104.0); the two
    # continuous drift calls it replaced are gone (v1.104.1)
    assert any(t.comment.startswith("Formation ladder") for t in m2.triggerrules.triggers)
    assert not any(t.comment.startswith("Formation: out of position") for t in m2.triggerrules.triggers)
    assert any("PRE-CHECK (practice)" in _said(t) for t in m2.triggerrules.triggers)


# --------------------------------------------------------------------------- #
# 3. the profile
# --------------------------------------------------------------------------- #
def test_precheck_and_check_fly_the_same_legs_and_pitch_out_when_done(check):
    assert formation.PROFILES["precheck"]["legs"] == formation.PROFILES["check"]["legs"]
    assert formation.PROFILES["check"]["check"] == "check"
    assert formation.PROFILES["precheck"]["check"] == "practice"
    secs = formation.profile_seconds("check")
    assert secs == 18 * 60
    _b, m = check
    pitch = _by(m, "Check")["Check: pitchout"]
    assert any(c.dict().get("seconds") == secs for c in pitch.rules)
    # the profile makes lead do every item: a turn each way, a climb, a descent, speed both ways
    legs = formation.PROFILES["check"]["legs"]
    assert any(dh < 0 for dh, *_ in legs) and any(dh > 0 for dh, *_ in legs)
    assert any(dft > 0 for _h, _m, dft, _k in legs) and any(dft < 0 for _h, _m, dft, _k in legs)
    assert any(dkt > 0 for *_, dkt in legs) and any(dkt < 0 for *_, dkt in legs)


def test_the_brief_says_what_is_graded_and_what_is_not(check, precheck):
    _b, m = check
    text = m.description_text()
    assert "CHECK RIDE: FINGERTIP" in text
    assert "cannot see the wingline" in text and "CRITICAL" in text
    assert "Silent." in text
    _b2, m2 = precheck
    assert "PRE-CHECK: FINGERTIP" in m2.description_text()
    assert "coach stays on" in m2.description_text()


# --------------------------------------------------------------------------- #
# 4. the timing check
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def tcheck():
    return _build("timing_5_check", seed=1)


def test_the_timing_check_is_silent_prints_letters_and_has_a_critical(tcheck):
    b, m = tcheck
    grades = [t for t in m.triggerrules.triggers if t.comment.startswith("Timing grade")]
    assert grades and all(not _said(t) for t in grades), "a check ride grade must not talk"
    by = _by(m, "Timing check")
    assert _said(by["Timing check: TARGET E"]).startswith("E  TARGET")
    assert _said(by["Timing check: TARGET U"]).startswith("U  TARGET")
    assert "CRITICAL ITEM" in _said(by["Timing check: critical"])
    assert _said(by["Timing check: overall Q"]).startswith("OVERALL: Q —")
    tight = [t for t in m.triggerrules.triggers if t.comment == "Timing grade: TARGET tight"]
    assert len(tight) == 1
    secs = sorted(c.dict()["seconds"] for c in tight[0].rules if "seconds" in c.dict())
    eta = next(r["eta_s"] for r in b.stats["timing"]["rows"] if r["to"] == "TARGET")
    assert secs == [eta - 10, eta + 10], "the E window is +/-10 s, a literal on purpose"
    assert not any(t.comment == "Timing debrief: open the card" for t in m.triggerrules.triggers)
    assert b.stats["timing"]["anchor_clock"] == "06:00:00"
    assert "06:00:00" in m.description_text()


def test_a_coached_timing_ride_still_talks():
    b, m = _build("timing_2_hitthetot", seed=1)
    grades = [t for t in m.triggerrules.triggers if t.comment.startswith("Timing grade")]
    assert any(_said(t) for t in grades)
    assert any(t.comment == "Timing debrief: open the card" for t in m.triggerrules.triggers)


# --------------------------------------------------------------------------- #
# 5. the course
# --------------------------------------------------------------------------- #
def test_every_upt_phase_with_rides_ends_in_a_check():
    from missiongen import courses
    c = courses.resolve("f4e_pipeline")
    upt = c["schools"][0]
    for p in upt["phases"]:
        rides = [u for u in p["units"] if u["kind"] in ("card", "track")]
        if not rides:
            continue
        checks = [u for u in rides if u.get("check")]
        assert len(checks) == 1, (p["id"], [u["id"] for u in rides])
        # the check comes after every graded ride except the post-check ops rides
        idx = rides.index(checks[0])
        assert idx >= 1


def test_the_gradesheet_flags_every_check_and_speaks_the_letters():
    from missiongen import courses, course_kit
    c = courses.resolve("f4e_pipeline")
    rows = courses.gradesheet_rows(c)
    checks = [r for r in rows if r["check"]]
    assert {r["ride"] for r in checks} == {"form_check", "timing_5_check", "aar_boom_8_qual", "pp_8_bnai"}
    csv_text = course_kit.gradesheet_csv(c)
    assert "sim_grade_UFGE" in csv_text and "check_result_Q_Qminus_U" in csv_text
