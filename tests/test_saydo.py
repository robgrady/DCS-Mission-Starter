"""The say/do check turned on ourselves, the readback gate, the scorecard, and
the "what DCS will get wrong" lines.

WHAT THIS FILE HOLDS THE PRODUCT TO
-----------------------------------
Every finding in the expert-mission ledger was a number copied by hand from
the world into the paperwork. We generate both, so after every build we
recompute the paperwork from the world and refuse a disagreement. The tests
below prove three things:

  1. the checks CATCH the classes of gap the experts shipped (a card
     frequency nothing holds, a brief clock that is not the mission clock, a
     voiced callsign the file does not use) — by planting each one;
  2. the shipped library has ZERO findings;
  3. the two techniques lifted from Fulda and Rampagers — the frequency gate
     and the shutdown scorecard — are wired the way the dossier describes,
     and the gate REFUSES to install on an airframe whose cockpit parameter
     we have not verified.

Published constants (base score 50, card at 60 s, reminders at 30/90 s,
window ±6 kHz, flags 8975–8978) are literals here on purpose: a test that
imports the constant it checks proves only that Python can copy a variable.
"""
from __future__ import annotations

import json
import tempfile
import zipfile
from pathlib import Path

import pytest
from dcs import lua

from missiongen import Recipe, generate
from missiongen import cockpit, cq_coach, gates, saydo
from missiongen.builder import StarterBuilder
from missiongen.resolver import load_json
from missiongen.templates import effective_recipe

TEMPLATES = load_json("mission_templates")
CARDS = {k: v for k, v in TEMPLATES.items() if isinstance(v, dict) and "recipe" in v}


def _recipe(key, seed=311):
    v = CARDS[key]
    era = (v.get("eras") or ["modern"])[0]
    rc = effective_recipe(key, era)
    rc.setdefault("map", v.get("default_map", "caucasus"))
    rc.update(era=era, template=key, seed=seed)
    return Recipe.from_dict(rc)


def _build(key, seed=311):
    b = StarterBuilder(_recipe(key, seed))
    m = b.build()
    return b, m


def _triggers(m):
    return [(t.comment, t) for t in m.triggerrules.triggers]


# --------------------------------------------------------------------------- #
# 1. the checks catch what the experts shipped
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def corridor():
    return _build("berlin_corridor_transit")


def test_a_card_frequency_nothing_holds_is_a_finding(corridor):
    b, m = corridor
    class FakeComms:
        entries = [("Ghost", "GHOST", "301.775", "-", "")]
    found = saydo.check_comms(m, FakeComms(), b._player_group)
    assert len(found) == 1
    assert found[0].startswith("SAY/DO:") and "301.775" in found[0] and "Ghost" in found[0]


def test_the_real_card_has_no_frequency_nothing_holds(corridor):
    b, m = corridor
    assert saydo.check_comms(m, b._comms, b._player_group) == []


def test_a_brief_clock_off_the_mission_clock_is_a_finding(corridor):
    b, m = corridor
    text = m.description_text()
    hhmm = saydo.mission_clock(m)
    assert hhmm == f"{m.start_time.hour:02d}:00"
    assert saydo.check_clock(m, text, hhmm) == []
    wrong = f"{(m.start_time.hour + 2) % 24:02d}:00"
    found = saydo.check_clock(m, text, wrong)
    assert any("mission clock starts" in f for f in found)


def test_the_in_game_brief_prints_the_clock_it_really_starts_on(corridor):
    b, m = corridor
    hhmm = saydo.mission_clock(m)
    assert f"Mission clock: {hhmm} local" in m.description_text()
    found = saydo.check_clock(m, "no clock in this brief", hhmm)
    assert any("does not print the start time" in f for f in found)


def test_the_pdf_dtg_hour_is_the_mission_hour():
    # brief.HOUR is a twin of builder.TIME_PRESETS. The twin is allowed to
    # exist only while this holds.
    from missiongen import brief
    from missiongen.builder import TIME_PRESETS
    assert {k: int(v) for k, v in brief.HOUR.items()} == TIME_PRESETS


def test_a_voiced_callsign_the_file_does_not_use_must_be_admitted(corridor):
    b, m = corridor
    stock = saydo.dcs_callsign(b._player_group)
    assert stock and stock[0].isalpha(), "the player flies a western callsign"
    root = stock.rstrip("0123456789")
    # The brief that says nothing about it is a finding...
    found = saydo.check_callsign(b._player_group, "Oyster 1", "a brief that never mentions it")
    assert len(found) == 1 and root in found[0]
    # ...and the real brief admits it, so the real check is clean.
    assert saydo.check_callsign(b._player_group, b._flight_name, m.description_text()) == []


def test_known_issues_name_the_ai_limits_and_the_brief_carries_them(corridor):
    b, m = corridor
    lines = b.stats["known_issues"]
    assert any("overhead break" in ln for ln in lines)
    assert any("tankers hold their track" in ln for ln in lines)
    assert "WHAT DCS WILL GET WRONG" in m.description_text()
    # Since v1.92.0 the flight flies under a DCS name, so the callsign line
    # is not a Known Issue any more — it must NOT be here.
    assert not any("callsign table is fixed" in ln for ln in lines)


def test_the_stock_callsign_line_returns_if_the_file_and_paper_ever_disagree(corridor):
    b, m = corridor
    lines = saydo.known_issues(b._player_group, "Oyster 1")
    assert any("callsign table is fixed" in ln and "Oyster" in ln for ln in lines)


def test_a_card_entry_the_jet_cannot_tune_is_disclosed_not_hidden():
    # Found on the first run of the check: a VHF-only Mustang with Guard
    # 243.0 and a UHF tactical on its card.
    b, m = _build("form_route")
    assert b._player_group.units[0].type == "P-51D"
    marked = b.stats["comms_unreachable"]
    assert marked == ["Guard 243.000"]
    notes = {ag: note for ag, _cs, _fq, _t, note in b._comms.entries}
    assert saydo.NOT_TUNABLE in notes["Guard"]
    assert any("cannot tune" in ln for ln in b.stats["known_issues"])
    assert [w for w in b.warnings if w.startswith("SAY/DO:")] == []


def test_a_vhf_only_jet_gets_a_flight_frequency_it_can_tune():
    from dcs import planes
    f, t, swapped = saydo.in_band_flight_freqs(planes.P_51D, 305.725, 254.325)
    assert swapped and f == 105.0 and t == 124.0
    f, t, swapped = saydo.in_band_flight_freqs(planes.F_14B, 305.725, 254.325)
    assert not swapped and (f, t) == (305.725, 254.325)
    b, m = _build("form_route")
    assert b._player_group.frequency == 105.0
    flight = next(e for e in b._comms.entries if e[0] == "Flight")
    assert flight[2] == "105.000" and "this aircraft's band" in flight[4]
    assert b.stats["comms_unreachable"] == ["Guard 243.000"]


def test_the_markdown_brief_carries_the_known_issues():
    d = tempfile.mkdtemp()
    out = str(Path(d) / "x.miz")
    res = generate(_recipe("berlin_corridor_transit"), out, brief_dir=d)
    md = Path(res["brief_md"]).read_text()
    assert "## What DCS will get wrong" in md
    assert "overhead break" in md
    assert "**Callsign " in md and "own callsign is" in md
    # A new stats key must never break a renderer that unpacks kb_ctx as
    # kwargs — the first cut of this release did exactly that.
    assert not [w for w in res["warnings"] if "rendering failed" in w], res["warnings"]


def test_findings_reach_the_build_warnings(monkeypatch):
    # The library is clean, so the wiring can only be proven with a planted
    # finding: a check that returns one must surface in the build warnings.
    monkeypatch.setattr(saydo, "check_comms",
                        lambda m, comms, pg=None: ["SAY/DO: planted"])
    b, m = _build("berlin_corridor_transit")
    assert "SAY/DO: planted" in b.warnings


# --------------------------------------------------------------------------- #
# 2. the shipped library has zero findings
# --------------------------------------------------------------------------- #
SAMPLE = sorted(CARDS)[::7] + ["cq_1_stack_f14", "cq_3_approach_fa18"]


@pytest.mark.parametrize("key", sorted(set(SAMPLE)))
def test_the_library_ships_with_no_say_do_findings(key):
    b, m = _build(key)
    findings = [w for w in b.warnings if w.startswith("SAY/DO:")]
    assert findings == [], findings


# --------------------------------------------------------------------------- #
# 3a. the readback gate
# --------------------------------------------------------------------------- #
def test_the_gate_refuses_an_unverified_airframe():
    assert cockpit.radio_param("F-14B") is None
    assert cockpit.radio_param("FA-18C_hornet") is None
    b, m = _build("cq_1_stack_f14")
    names = [c for c, _t in _triggers(m)]
    assert not any(c.startswith("Readback:") for c in names)
    line = b.stats["cq_readback"]
    assert "not available" in line and "unverified" in line
    assert "264." in line or "26" in line          # Mother's frequency is still told
    assert line in "\n".join(b.stats["cq_card"])
    assert line in m.description_text()


def test_the_gate_knows_where_its_facts_came_from():
    assert cockpit.radio_param("F-4E-45MC") == "COMM_FREQ"
    assert cockpit.radio_param("F-4E-45MC", "comm2") == "AUX_FREQ"
    assert "Fulda" in cockpit.provenance("F-4E-45MC")
    assert cockpit.radio_param("F-16C_50") == "COMM1_FREQ"
    for ac, e in cockpit.RADIO_PARAMS.items():
        assert e.get("source"), f"{ac}: a cockpit fact without a source is a guess"


def test_the_gate_installs_the_triplet_on_a_verified_airframe(monkeypatch):
    monkeypatch.setitem(cockpit.RADIO_PARAMS, "F-14B",
                        {"comm1": "TEST_COMM", "source": "test double"})
    b, m = _build("cq_1_stack_f14")
    tr = dict(_triggers(m))
    assert "Readback: MOTHER set" in tr
    assert "Readback: MOTHER NOT set" in tr
    assert "Readback: MOTHER still NOT set" in tr
    mother = float(next(fq for ag, _cs, fq, *_ in b._comms.entries if ag == "Carrier"))
    st = tr["Readback: MOTHER set"]
    rng = next(c for c in st.rules if c.predicate == "c_cockpit_param_in_range")
    assert rng.cockpit_param == "TEST_COMM"
    assert rng._min2 == pytest.approx(mother - 0.006) and rng._max2 == pytest.approx(mother + 0.006)
    assert any(getattr(a, "flag", None) == 8977 for a in st.actions)
    r1 = tr["Readback: MOTHER NOT set"]
    tsf = next(c for c in r1.rules if c.predicate == "c_time_since_flag")
    assert tsf.flag == 8976 and tsf.seconds == 30
    r2 = tr["Readback: MOTHER still NOT set"]
    tsf2 = next(c for c in r2.rules if c.predicate == "c_time_since_flag")
    assert tsf2.seconds == 90
    assert "confirms COMM1" in b.stats["cq_readback"]


def test_the_checkin_cue_opens_the_gate():
    b, m = _build("cq_1_stack_f14")
    tr = dict(_triggers(m))
    checkin = tr["CQ cue: checkin"]
    assert any(getattr(a, "flag", None) == 8976 for a in checkin.actions)


def test_gate_flags_sit_inside_the_coach_registry():
    assert (gates.F_START, gates.F_DONE, gates.F_REMIND) == (8976, 8977, 8978)
    assert cq_coach.F_DEBRIEF == 8975 and cq_coach.F_ARM == 8979
    # slot 15 of the grade block is the debrief flag; no ride may have 16 grades
    assert cq_coach.F_DEBRIEF == cq_coach.F_GRADE + 15
    assert all(len(v) < 15 for v in cq_coach.RIDE_GRADES.values())


# --------------------------------------------------------------------------- #
# 3b. the scorecard
# --------------------------------------------------------------------------- #
def test_every_grade_has_a_score_line():
    for key, _text in cq_coach.GRADES:
        assert key in cq_coach.SCORE, key
        pts, short = cq_coach.SCORE[key]
        assert short and isinstance(pts, int) and pts != 0
    assert cq_coach.BASE_SCORE == 50 and cq_coach.DEBRIEF_AFTER_S == 60
    assert cq_coach.score_line("push_ontime").startswith("+10")
    assert cq_coach.score_line("dive").startswith("-10")


@pytest.mark.parametrize("key", ["cq_1_stack_f14", "cq_2_push_fa18", "cq_3_approach_f14"])
def test_a_graded_ride_prints_its_card_a_minute_after_the_last_cue(key):
    b, m = _build(key)
    tr = dict(_triggers(m))
    ride = TEMPLATES[key]["recipe"]["cq_ride"]
    cues, grades = cq_coach.cues_for(ride), cq_coach.grades_for(ride)
    card = tr["CQ debrief: open the card"]
    tsf = next(c for c in card.rules if c.predicate == "c_time_since_flag")
    assert tsf.flag == cq_coach.F_PHASE + cq_coach.CUE_IDX[cues[-1]]
    assert tsf.seconds == 60
    assert any(getattr(a, "flag", None) == 8975 for a in card.actions)
    for g in grades:
        t = tr[f"CQ debrief: {g}"]
        assert any(c.predicate == "c_flag_is_true" and c.flag == cq_coach.F_GRADE + cq_coach.GRADE_IDX[g]
                   for c in t.rules)
    busts = [g for g in grades if cq_coach.SCORE[g][0] < 0]
    if busts:
        clean = tr["CQ debrief: clean"]
        falses = {c.flag for c in clean.rules if c.predicate == "c_flag_is_false"}
        assert falses == {cq_coach.F_GRADE + cq_coach.GRADE_IDX[g] for g in busts}
    assert "Scorecard" in "\n".join(b.stats["cq_card"])


@pytest.mark.parametrize("key", ["cq_4_ball_f14", "cq_5_nightcq_fa18"])
def test_an_ungraded_ride_prints_no_card(key):
    b, m = _build(key)
    names = [c for c, _t in _triggers(m)]
    assert not any(c.startswith("CQ debrief") for c in names)
    assert "Scorecard" not in "\n".join(b.stats["cq_card"])


def test_the_card_lines_reach_the_dictionary():
    d = tempfile.mkdtemp()
    out = str(Path(d) / "x.miz")
    generate(_recipe("cq_2_push_fa18"), out)
    z = zipfile.ZipFile(out)
    dic = lua.loads(z.read("l10n/DEFAULT/dictionary").decode())["dictionary"]
    texts = "\n".join(str(v) for v in dic.values())
    assert "RIDE DEBRIEF" in texts and "Base score 50" in texts
    assert "+10  Level 1,200 at ten miles" in texts
    assert "No busts recorded on this ride." in texts


# --------------------------------------------------------------------------- #
# 4. the flight flies under a callsign DCS can say (v1.92.0)
# --------------------------------------------------------------------------- #
from missiongen import callsign as _callsign


def test_the_pool_is_the_eight_names_dcs_speaks():
    assert _callsign.pool() == ["Enfield", "Springfield", "Uzi", "Colt",
                                "Dodge", "Ford", "Chevy", "Pontiac"]


def test_a_pool_name_is_used_as_typed_and_others_map_stably():
    assert _callsign.dcs_name("colt") == "Colt"
    assert _callsign.dcs_name("Gypsy") == _callsign.dcs_name("gypsy")
    assert _callsign.dcs_name("Gypsy") in _callsign.pool()
    assert _callsign.dcs_name("Gypsy") == _callsign.dcs_name("Gypsy")   # stable
    assert _callsign.heritage_line("Gypsy", "Colt", "VF-32") .startswith("VF-32's own callsign is Gypsy")
    assert _callsign.heritage_line("Colt", "Colt") is None


def test_the_file_carries_the_index_dcs_reads_not_only_the_name():
    b, m = _build("carrier_qual")
    u = b._player_group.units[0]
    used = b._callsign_used
    assert b.stats["callsign"] == f"{used} 1"
    assert u.callsign is None
    assert u.callsign_dict["name"] == f"{used}11"
    assert u.callsign_dict[1] == _callsign.pool().index(used) + 1
    assert u.callsign_dict[2] == 1 and u.callsign_dict[3] == 1
    # and the paperwork agrees, so the Known Issues line is gone
    assert not any("callsign table is fixed" in ln for ln in b.stats["known_issues"])
    assert f"Callsign: {used} 1." in m.description_text()
    assert "own callsign is" in b.stats["callsign_heritage"]


def test_a_typed_pool_name_is_honoured_exactly():
    r = _recipe("carrier_qual")
    r.callsign = "Dodge"
    b = StarterBuilder(r); m = b.build()
    assert b.stats["callsign"] == "Dodge 1"
    assert b._player_group.units[0].callsign_dict == {1: 5, 2: 1, 3: 1, "name": "Dodge11"}
    assert "callsign_heritage" not in b.stats


def test_a_numeric_nation_flies_the_bort_number():
    b, m = _build("mig_gun_belt_strike")
    u = b._player_group.units[0]
    assert b.stats["callsign"] == "231" and u.callsign == 231
    assert saydo.dcs_callsign(b._player_group) == "231"
    assert not any("callsign table is fixed" in ln for ln in b.stats["known_issues"])


def test_wingmen_take_the_next_position():
    b, m = _build("form_route")
    g = b._player_group
    for i, u in enumerate(g.units, start=1):
        assert u.callsign_dict[3] == i and u.callsign_dict["name"].endswith(f"1{i}")


def test_a_named_callsign_on_a_numeric_nation_becomes_a_number():
    r = _recipe("mig_gun_belt_strike")
    r.callsign = "Gypsy"
    b = StarterBuilder(r); m = b.build()
    assert b.stats["callsign"].isdigit()
    assert b._player_group.units[0].callsign == int(b.stats["callsign"])
    assert "Gypsy" in b.stats["callsign_heritage"]
