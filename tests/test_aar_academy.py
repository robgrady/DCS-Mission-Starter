"""The AAR Academy: two lane tracks, a trigger-only grader, and printed guides.

WHAT THESE TESTS ARE FOR. Three classes of defect, all of which this codebase
has actually shipped before:

  1. A BRIEF THAT PROMISES WHAT THE MISSION DOES NOT CONTAIN. The grader cannot
     see a refuelling event. Any card whose brief implies a plug was measured
     is the `test_library_promises` failure again, wearing a new hat.
  2. A SYLLABUS THAT MISCOUNTS ITSELF. A printed track whose card says eleven
     rides and whose data holds nine, or two rides numbered 4, is a course
     nobody can follow.
  3. A GUARD THAT PASSES ON DATA OTHER THAN THE DATA UNDER TEST. Every
     assertion here pins an absolute value or a named element; none compares
     two derived values to each other.
"""
import json
import re
import pathlib
import zipfile

import pytest

from missiongen import aar, aar_grade, tracks
from missiongen import aar as aar_mod
from missiongen.recipe import Recipe
from missiongen import generate
from missiongen.templates import effective_recipe
from missiongen.resolver import load_json


# --------------------------------------------------------------------------- #
# 1. The reconciled numbers
# --------------------------------------------------------------------------- #
def test_the_card_prints_both_closure_phases_not_just_the_approach():
    """The defect this fixes: 1-3 kt was printed as THE closure number. One
    knot is 1.688 ft/sec, so that asked a pilot to arrive at the boom two to
    five times faster than the ~1 ft/sec figure the card leant on elsewhere."""
    card = "\n".join(aar.brief_lines("kc135", "F_16C_50"))
    assert "CLOSURE, APPROACH" in card
    assert "CLOSURE, LAST FEW FEET" in card
    assert "1 to 3 knots" in card
    assert "ONE FOOT PER SECOND" in card


def test_the_conversion_between_the_two_closure_numbers_is_stated():
    """A reader given two numbers in two units and no bridge between them is
    given one number and a puzzle."""
    card = "\n".join(aar.brief_lines("kc130", "FA_18C_hornet"))
    assert "1.7 feet per second" in card, "the kt -> ft/sec bridge has gone"


def test_the_15_second_gate_and_the_60_second_standard_are_separated():
    card = "\n".join(aar.brief_lines("kc135", "F_16C_50"))
    assert "PRE-CONTACT, THE GATE" in card and "15" in card
    assert "PRE-CONTACT, THE STANDARD" in card and "60 seconds" in card


def test_the_60_second_standard_admits_it_is_ours():
    """Honest-numbers rule. No document in the library states a duration, so
    the card must not let 60 s borrow ATP-56's authority."""
    card = "\n".join(aar.brief_lines("kc135", "F_16C_50"))
    i = card.index("PRE-CONTACT, THE STANDARD")
    para = card[i:i + 420]
    assert "not quoted from anyone" in para or "OUR proficiency" in para, \
        "the 60 s standard no longer says it is ours"


def test_one_knot_really_is_about_1_7_feet_per_second():
    """The arithmetic the two closure numbers rest on. If this ever fails the
    card's 'factor of three' claim is wrong too."""
    ft_per_sec_per_kt = 1852.0 / 3600.0 / 0.3048
    assert 1.68 < ft_per_sec_per_kt < 1.69
    # and 1-3 kt really is 2-5x the ~1 ft/sec figure, which is why both print
    assert 1.6 < 1 * ft_per_sec_per_kt < 1.8
    assert 5.0 < 3 * ft_per_sec_per_kt < 5.2


# --------------------------------------------------------------------------- #
# 2. The throttle content the plan asked for
# --------------------------------------------------------------------------- #
def test_the_hardware_page_teaches_pulse_and_counter_pulse():
    h = "\n".join(aar.hardware_lines())
    assert "PULSE AND COUNTER-PULSE" in h
    assert "BASELINE" in h
    assert "counter-pulse" in h


def test_the_hardware_page_carries_the_close_stop_aft_stop_drill():
    h = "\n".join(aar.hardware_lines())
    assert "THE DRILL" in h
    assert "20-30" in h, "the drill's distance is gone"
    assert "THREE smooth cycles" in h


def test_the_throttle_advice_starts_linear():
    """ED's own guidance treats linear as the baseline; a card that recommends
    a throttle curve by default contradicts the source it cites."""
    h = "\n".join(aar.hardware_lines())
    assert "start LINEAR" in h


# --------------------------------------------------------------------------- #
# 3. The grader: what it measures, and what it must never claim
# --------------------------------------------------------------------------- #
GRADED_CARDS = [k for k, v in load_json("mission_templates").items()
                if not k.startswith("_") and v.get("aar_grade")]


def test_there_are_graded_cards_at_all():
    """Guards below iterate GRADED_CARDS. If that list empties they all pass
    vacuously — which is exactly the failure mode this file exists to avoid."""
    assert len(GRADED_CARDS) >= 18, GRADED_CARDS


@pytest.mark.parametrize("key", GRADED_CARDS)
def test_every_graded_card_names_a_profile_the_grader_knows(key):
    g = load_json("mission_templates")[key]["aar_grade"]
    assert g in aar_grade.PROFILES, f"{key} asks for unknown profile {g!r}"


def test_the_grading_card_says_contact_is_not_measured():
    """THE most important assertion in this file. Mission Editor triggers
    cannot see S_EVENT_REFUELING. A pass message with no such disclaimer is a
    certificate we did not earn."""
    for profile in aar_grade.PROFILES:
        card = "\n".join(aar_grade.brief_lines(profile))
        assert "NOT MEASURED" in card, profile
        assert "Whether you made contact." in card, profile
        assert "How much fuel you took." in card, profile
        assert "cannot see a refuelling event" in card, profile


def test_the_grading_card_explains_why_the_tolerances_are_wide():
    card = "\n".join(aar_grade.brief_lines("station"))
    assert "WIDE" in card
    assert "calls a correct" in card


def test_coaching_fades():
    card = "\n".join(aar_grade.brief_lines("closure"))
    assert "COACHING FADES" in card
    assert str(aar_grade.MAX_CLOSURE_CALLS) in card or "three times" in card


def test_the_close_envelope_cannot_call_a_correct_pilot_wrong():
    """CLOSE_M has to contain every position a pilot legitimately works from
    and exclude the 1 nm pre-contact air start. Both bounds pinned as absolute
    numbers, not derived from each other."""
    assert aar_grade.CLOSE_M >= 100.0, "too tight — contact sits ~15-50 m out"
    assert aar_grade.CLOSE_M <= 400.0, "so loose it would credit anywhere"
    assert aar_grade.CLOSE_M < 1852.0 * 0.5, \
        "the 1 nm air start must be clearly OUTSIDE the working envelope"


def test_the_warn_envelope_is_wider_than_the_working_one():
    """A closure warning that only fires once you are already close arrives
    after the moment it could have helped."""
    assert aar_grade.WARN_M > aar_grade.CLOSE_M


def test_the_speed_band_is_far_wider_than_a_stable_pilot_needs():
    """A pilot holding contact is inside 1-2 kt. The band must be several
    times that or a correction costs credit."""
    assert aar_grade.STABLE_BAND_KT >= 5.0
    assert aar_grade.UNSAFE_OVERTAKE_KT > aar_grade.STABLE_BAND_KT * 2


def test_scoring_waits_for_the_vr_calibration_window():
    assert aar_grade.CALIBRATE_S >= 15, \
        "too short to recentre and set seat height"


def test_the_grader_never_raises_when_pydcs_shifts():
    """Contract: a signature drift degrades the card to an ungraded one. It
    must not fail the build."""
    warns = []
    ok = aar_grade.attach(None, None, None, "kc135", "station", warnings=warns)
    assert ok is False
    assert warns and "AAR grading not attached" in warns[0]


# --------------------------------------------------------------------------- #
# 4. The tracks: a syllabus that counts itself correctly
# --------------------------------------------------------------------------- #
# AAR LANES ONLY. `tracks` became a general concept the day a second kind of
# syllabus shipped, and every guard in this file asserts something AAR-specific
# — a refuelling lane, a tanker, indicator artwork. Running them over a
# formation-and-low-level track asserts nothing and fails everything.
#
# Scoped by `lane` rather than by an id prefix, so a third refuelling lane is
# picked up automatically and a third NON-refuelling track is not.
ALL_TRACKS = sorted(t for t in tracks.all_tracks()
                    if (tracks.get(t) or {}).get("lane") in ("boom", "probe"))


def test_both_lanes_exist():
    assert ALL_TRACKS == ["aar_boom", "aar_probe"]


def test_the_lane_filter_did_not_empty_this_file():
    """Every guard below iterates ALL_TRACKS. If the filter ever matched
    nothing they would all pass vacuously, which is the failure mode this
    codebase produces most often."""
    assert len(ALL_TRACKS) >= 2, ALL_TRACKS
    assert len(tracks.all_tracks()) > len(ALL_TRACKS), (
        "the filter is not filtering anything — either it is broken or the "
        "non-AAR tracks have gone")


@pytest.mark.parametrize("tid", ALL_TRACKS)
def test_ride_numbers_are_contiguous_from_zero(tid):
    ns = [n for n, _k, _v in tracks.rides(tid)]
    assert ns == list(range(len(ns))), f"{tid} ride numbers: {ns}"


@pytest.mark.parametrize("tid", ALL_TRACKS)
def test_a_track_has_eleven_rides(tid):
    assert len(tracks.rides(tid)) == 11


@pytest.mark.parametrize("tid", ALL_TRACKS)
def test_the_premise_states_the_real_ride_count(tid):
    """The defect: a card advertising eleven rides over a track holding nine.
    Word-form on purpose — the number is written out in the copy."""
    t = tracks.get(tid)
    n = len(tracks.rides(tid))
    words = {9: "Nine", 10: "Ten", 11: "Eleven", 12: "Twelve"}
    assert words[n] in t["premise"], \
        f"{tid} has {n} rides; its premise says otherwise: {t['premise'][:80]}"


@pytest.mark.parametrize("tid", ALL_TRACKS)
def test_the_premise_states_the_real_graded_count(tid):
    graded = sum(1 for _n, _k, v in tracks.rides(tid) if v.get("aar_grade"))
    words = {9: "Nine", 10: "Ten", 11: "Eleven"}
    assert words[graded] in tracks.get(tid)["premise"], \
        f"{tid} grades {graded} rides; the premise disagrees"


def test_duplicate_ride_numbers_are_an_error_not_a_shrug():
    """Prove the guard by breaking it: two rides at the same number must raise
    rather than quietly ordering one of them first."""
    real = load_json("mission_templates")
    import missiongen.tracks as R      # tracks.py binds the name at import,
    orig = R.load_json                 # so patching resolver would do nothing

    def fake(name):
        if name != "mission_templates":
            return orig(name)
        d = dict(real)
        d["aar_boom_0_fit"] = dict(d["aar_boom_0_fit"])
        d["aar_boom_0_fit"]["track"] = {"id": "aar_boom", "n": 5}
        return d

    R.load_json = fake
    try:
        with pytest.raises(ValueError, match="two rides numbered 5"):
            tracks.rides("aar_boom")
    finally:
        R.load_json = orig


@pytest.mark.parametrize("tid", ALL_TRACKS)
def test_the_last_ride_is_the_ungraded_capstone(tid):
    """The plan's ride 9 is the transfer test — a coached repetition with a
    grade attached would be the one thing it must not be."""
    by_n = {n: v for n, _k, v in tracks.rides(tid)}
    assert by_n[9].get("aar_grade") is None, "the capstone must not be graded"
    assert "Operational Transfer" in by_n[9]["label"]


@pytest.mark.parametrize("tid", ALL_TRACKS)
def test_every_ride_states_one_new_demand(tid):
    """A printed syllabus whose rides do not each name their single new demand
    is a pile of missions in an order."""
    for n, k, v in tracks.rides(tid):
        assert any(ln.startswith("NEW DEMAND") for ln in v.get("brief") or []), \
            f"{tid} ride {n} ({k}) states no new demand"


@pytest.mark.parametrize("tid", ALL_TRACKS)
def test_the_lanes_do_not_share_an_airframe(tid):
    """Boom and probe are different tasks. A lane flying the other lane's jet
    would be handing a Viper a basket."""
    from missiongen.resolver import resolve
    t = tracks.get(tid)
    boom_lane = t["lane"] == "boom"
    assert aar.TANKERS[t["tanker"]]["boom"] is boom_lane
    # TWO IDENTIFIER NAMESPACES meet here and they are not the same strings:
    # tracks.json and every recipe use the ROSTER KEY ("F_16C_50"), while
    # aar.BOOM_RECEIVERS holds DCS TYPE IDS ("F-16C_50"). Passing a key where
    # an id is expected returns False for every boom receiver — silently, and
    # in a function whose whole job is to stop a Viper being sent to a basket.
    rid = resolve("planes." + t["aircraft"]).id
    assert aar.compatible(t["tanker"], rid), \
        f"{tid} pairs {t['aircraft']} ({rid}) with an incompatible tanker"


def test_track_rides_are_hidden_from_the_loose_grid_by_carrying_track_metadata():
    """The Library filters on this key. Without it every ride appears twice —
    once in its track and once alphabetically in the grid."""
    tpl = load_json("mission_templates")
    for tid in ALL_TRACKS:
        for _n, k, _v in tracks.rides(tid):
            assert tpl[k].get("track", {}).get("id") == tid


def test_no_academy_ride_is_still_featured():
    """Ten loose cards in the featured row is not a syllabus."""
    tpl = load_json("mission_templates")
    for tid in ALL_TRACKS:
        for _n, k, _v in tracks.rides(tid):
            assert not (tpl[k].get("library") or {}).get("featured"), \
                f"{k} is still competing with its own track for the featured row"


def test_no_shipped_card_still_says_it_is_one_of_four():
    """The five cards that predate the track were written as a set of FOUR and
    said so. Inside an eleven-ride track that is a brief miscounting its own
    course."""
    tpl = load_json("mission_templates")
    for tid in ALL_TRACKS:
        for n, k, _v in tracks.rides(tid):
            text = "\n".join(tpl[k].get("brief") or [])
            assert "of four" not in text, f"{k} still calls itself one of four"
            assert not re.search(r"fly AAR \d", text), \
                f"{k} refers to a ride by its retired number"


@pytest.mark.parametrize("tid", ALL_TRACKS)
def test_ride_titles_say_what_the_ride_teaches(tid):
    """Rob's note: "Fit Check" and "The Flow" are evocative, not descriptive.
    A pilot reading a Library row, a zip listing or a printed contents page
    must be able to tell what a ride teaches WITHOUT the syllabus in hand.

    Two concrete guards: the title spells out the discipline rather than
    abbreviating it, and the descriptive half is a real phrase rather than a
    two-word codename."""
    for n, k, v in tracks.rides(tid):
        label = v["label"]
        assert label.startswith("Air-to-Air Refuelling "), \
            f"{k}: title abbreviates the discipline: {label!r}"
        assert f"Air-to-Air Refuelling {n} " in label, \
            f"{k}: title does not carry its ride number: {label!r}"
        assert "— " in label, f"{k}: no descriptive half: {label!r}"
        desc = label.split("— ", 1)[1]
        assert len(desc.split()) >= 3, \
            f"{k}: {desc!r} is a codename, not a description"


@pytest.mark.parametrize("tid", ALL_TRACKS)
def test_ride_titles_name_their_own_lane(tid):
    """Both tracks number their rides 0-10. Without the lane in the title, two
    files called 'Air-to-Air Refuelling 4' land in the same Missions folder."""
    word = {"boom": "(Boom)", "probe": "(Probe)"}[tracks.get(tid)["lane"]]
    for _n, k, v in tracks.rides(tid):
        assert word in v["label"], f"{k}: title does not say which lane"


def test_no_two_rides_across_the_tracks_share_a_title():
    seen = {}
    for tid in ALL_TRACKS:
        for _n, k, v in tracks.rides(tid):
            assert v["label"] not in seen, \
                f"{k} and {seen.get(v['label'])} share the title {v['label']!r}"
            seen[v["label"]] = k


@pytest.mark.parametrize("tid", ALL_TRACKS)
def test_the_track_itself_is_named_in_full(tid):
    assert tracks.get(tid)["label"].startswith("Air-to-Air Refuelling Academy")


# --------------------------------------------------------------------------- #
# 5. Every ride actually builds, and the graded ones actually carry triggers
# --------------------------------------------------------------------------- #
ALL_RIDES = [(tid, n, k) for tid in ALL_TRACKS for n, k, _v in tracks.rides(tid)]


@pytest.mark.parametrize("tid,n,key", ALL_RIDES)
def test_every_ride_builds(tid, n, key, tmp_path):
    rc = effective_recipe(key, "modern")
    rc["template"] = key
    rc["seed"] = 4400 + n
    r = Recipe.from_dict(rc)
    r.validate()
    res = generate(r, str(tmp_path / f"{key}.miz"))
    assert res["stats"].get("aar"), f"{key} placed no tanker"


@pytest.mark.parametrize("tid,n,key", [x for x in ALL_RIDES
                                       if load_json("mission_templates")[x[2]]
                                       .get("aar_grade")])
def test_a_graded_ride_writes_grading_triggers_into_the_miz(tid, n, key, tmp_path):
    """Not 'the stats dict says graded' — the actual mission file. A stat that
    reports a trigger nobody wrote is the vacuous-test pattern."""
    rc = effective_recipe(key, "modern")
    rc["template"] = key
    rc["seed"] = 4400 + n
    r = Recipe.from_dict(rc)
    r.validate()
    out = tmp_path / f"{key}.miz"
    generate(r, str(out))
    txt = zipfile.ZipFile(out).read("mission").decode("utf-8", "replace")
    comments = set(re.findall(r'\["comment"\]\s*=\s*"(AAR[^"]*)"', txt))
    assert "AAR grade: in tolerance" in comments, comments
    assert "AAR grade: 15 s gate" in comments
    assert "AAR grade: 60 s standard" in comments
    assert any(c.startswith("AAR menu:") for c in comments), \
        "the F10 self-requested hints are missing"


def test_an_ungraded_ride_writes_no_grading_triggers(tmp_path):
    """The other half of the guard: prove the triggers are absent when the
    card did not ask for them, so the test above is testing the flag and not
    the module import."""
    key = "aar_boom_9_transfer"
    rc = effective_recipe(key, "modern")
    rc["template"] = key
    rc["seed"] = 4409
    r = Recipe.from_dict(rc)
    r.validate()
    out = tmp_path / f"{key}.miz"
    generate(r, str(out))
    txt = zipfile.ZipFile(out).read("mission").decode("utf-8", "replace")
    assert '"AAR grade: in tolerance"' not in txt


@pytest.mark.parametrize("tid,n,key", [x for x in ALL_RIDES
                                       if load_json("mission_templates")[x[2]]
                                       .get("aar_grade")])
def test_a_graded_rides_brief_admits_what_is_not_measured(tid, n, key, tmp_path):
    """The say/do guard. A graded card whose briefing never mentions that the
    plug is unmeasured is promising what the mission does not contain."""
    rc = effective_recipe(key, "modern")
    rc["template"] = key
    rc["seed"] = 4400 + n
    r = Recipe.from_dict(rc)
    r.validate()
    out = tmp_path / f"{key}.miz"
    generate(r, str(out))
    # Briefing text lives in the l10n dictionary, not in `mission` — reading
    # the wrong member is how this assertion could have passed vacuously.
    z = zipfile.ZipFile(out)
    txt = z.read("l10n/DEFAULT/dictionary").decode("utf-8", "replace")
    assert "cannot see a refuelling event" in txt, \
        f"{key} grades the pilot without saying what it cannot see"


# --------------------------------------------------------------------------- #
# 6. The printed guides
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("tid", ALL_TRACKS)
def test_each_lane_has_its_own_printed_guide(tid):
    from pathlib import Path
    root = Path(__file__).parent.parent / "docs"
    name = tracks.get(tid)["guide"]
    assert (root / f"{name}.pdf").is_file(), f"{tid}: no printed guide"
    assert (root / f"{name}.md").is_file(), f"{tid}: no markdown guide"


def test_the_two_lane_guides_are_not_the_same_document():
    """Rob's requirement: the Air Force documentation differs from the Navy's.
    A build that quietly wrote one guide twice would pass every other test."""
    from pathlib import Path
    root = Path(__file__).parent.parent / "docs"
    boom = (root / "aar-academy-boom.md").read_text()
    probe = (root / "aar-academy-probe.md").read_text()
    assert boom != probe
    assert "KC-135" in boom and "boom operator" in boom
    assert "basket" in probe
    assert "boom operator flies the boom" not in probe, \
        "the probe guide is describing the boom lane"


@pytest.mark.parametrize("tid", ALL_TRACKS)
def test_the_guide_lists_every_ride_in_the_track(tid):
    """A printed syllabus missing a ride sends the pilot to a gap."""
    from pathlib import Path
    md = (Path(__file__).parent.parent / "docs"
          / f"{tracks.get(tid)['guide']}.md").read_text()
    for n, _k, v in tracks.rides(tid):
        name = v["label"].split("— ", 1)[-1]
        assert name in md, f"{tid}: ride {n} ({name}) is not in the guide"


@pytest.mark.parametrize("tid", ALL_TRACKS)
def test_the_guide_carries_the_honest_numbers_note(tid):
    from pathlib import Path
    md = (Path(__file__).parent.parent / "docs"
          / f"{tracks.get(tid)['guide']}.md").read_text()
    assert "cannot see a refuelling event" in md


# --------------------------------------------------------------------------- #
# 7. The API
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from server.app import app
    return TestClient(app)


def test_options_exposes_both_tracks_with_their_rides(client):
    t = client.get("/api/options").json()["tracks"]
    assert {"aar_boom", "aar_probe"} <= set(t)
    for tid in ALL_TRACKS:
        tr = t[tid]
        assert len(tr["rides"]) == 11
        assert [r["n"] for r in tr["rides"]] == list(range(11))
        assert tr["guide"]
        assert tr["configurable"] is True, (
            f"{tid} is a wizard track and must ship a picker")


def test_options_marks_track_membership_on_the_ride_cards(client):
    """Without this the Library cannot keep rides out of the loose grid."""
    tpl = client.get("/api/options").json()["templates"]
    assert (tpl["aar_boom_0_fit"]["track"] or {}).get("id") == "aar_boom"
    assert tpl["carrier_qual"].get("track") in (None, {})


def test_the_guide_endpoint_serves_a_pdf(client):
    r = client.get("/api/track/aar_boom/guide.pdf")
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"


def test_an_unknown_track_is_a_404_not_a_500(client):
    assert client.get("/api/track/nope/guide.pdf").status_code == 404
    assert client.get("/api/track/nope/all.zip").status_code == 404


def test_the_guide_endpoint_refuses_to_escape_the_docs_directory(client):
    """The track id comes off the URL. A data typo or a probe must not become
    a path traversal."""
    for bad in ("..%2F..%2Fetc%2Fpasswd", "....//....//etc", "%2e%2e%2fetc"):
        assert client.get(f"/api/track/{bad}/guide.pdf").status_code == 404


def test_the_whole_track_download_comes_from_a_pack_and_carries_everything(
        client, tmp_path, monkeypatch):
    """WHAT CHANGED, AND WHY THIS TEST DID.

    This used to build eleven missions inside the request. That is what took
    the Fly machine down, so the builder is deleted rather than cached around:
    a syllabus is either PUBLISHED as a pack or it is flown one ride at a time.

    The contract this now asserts is the same one a pilot cares about — every
    ride, every brief, the printed guide and the read-me arrive in one file —
    but the file is an artifact somebody produced and uploaded, not a
    computation the download waits for.
    """
    import io
    from missiongen import packs as _packs
    src = pathlib.Path(__file__).resolve().parent.parent / "packs"
    art = next(iter(sorted(src.glob("aar_probe*.sspack"))), None)
    if art is None:
        pytest.skip("no produced pack in this tree — scripts/build_pack.py --all")

    monkeypatch.setattr(_packs, "DATA_DIR", tmp_path)
    _packs.install(art.read_bytes(), art.name)

    r = client.get("/api/track/aar_probe/all.zip")
    assert r.status_code == 200, r.status_code
    z = zipfile.ZipFile(io.BytesIO(r.content))
    names = z.namelist()
    mizzes = [n for n in names if n.endswith(".miz")]
    briefs = [n for n in names if n.endswith("_brief.pdf")]
    assert len(mizzes) == 11, mizzes
    assert len(briefs) == 11, briefs
    assert any(n.endswith("aar-academy-probe.pdf") for n in names), \
        "the printed guide is not in the download"
    assert any(n.endswith("READ_ME_FIRST.md") for n in names)
    assert any(n.endswith("pack.json") for n in names), \
        "the download is not self-describing"
    # every ride numbered, in order, so unzipping gives a flyable sequence
    assert sorted(n.split("/")[-1][:2] for n in mizzes) == \
        [f"{i:02d}" for i in range(11)]


def test_an_unpublished_track_offers_the_rides_instead_of_a_broken_button(
        client, tmp_path, monkeypatch):
    """The other half of the same contract. Nothing published means nothing
    built — and a 409 that points the pilot at the per-ride Generate buttons,
    not a machine restarting under his download."""
    from missiongen import packs as _packs
    monkeypatch.setattr(_packs, "DATA_DIR", tmp_path)
    r = client.get("/api/track/aar_probe/all.zip")
    assert r.status_code == 409
    assert "ride" in r.json()["detail"].lower()


# --------------------------------------------------------------------------- #
# The printed guide has to carry EVERYTHING the pilot is shown in the air
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("tid", ALL_TRACKS)
def test_the_guide_carries_every_kneeboard_card(tid):
    """A downloadable syllabus missing one of the four cards is a syllabus you
    cannot revise from. The indicator card was missing entirely until Rob
    asked whether the documentation was current."""
    from pathlib import Path
    md = (Path(__file__).parent.parent / "docs"
          / f"{tracks.get(tid)['guide']}.md").read_text()
    for heading in ("Kneeboard — the procedure",
                    "Kneeboard — what the grader sees",
                    "Kneeboard — the position indicator",
                    "Kneeboard — your hardware"):
        assert heading in md, f"{tid}: {heading} is not in the guide"


@pytest.mark.parametrize("tid", ALL_TRACKS)
def test_the_guide_explains_the_tanker_and_the_ones_not_offered(tid):
    from pathlib import Path
    md = (Path(__file__).parent.parent / "docs"
          / f"{tracks.get(tid)['guide']}.md").read_text()
    assert "Your tanker, and the ones you were not offered" in md
    assert "KIAS at" in md, "the guide does not state the track speed"


@pytest.mark.parametrize("tid", ALL_TRACKS)
def test_the_guide_prints_the_indicator_artwork(tid):
    """Not a redrawn legend — the SAME PNGs the mission carries. A legend drawn
    separately drifts from the artwork within one release and then teaches the
    wrong picture."""
    import re
    from pathlib import Path
    from missiongen import aar_hud
    pdf = (Path(__file__).parent.parent / "docs"
           / f"{tracks.get(tid)['guide']}.pdf").read_bytes()
    # every state ships as an embedded image, so the PDF must carry that many
    n = len(re.findall(rb"/Subtype\s*/Image", pdf))
    assert n >= len(aar_hud.STATES), \
        f"{tid}: {n} images in the guide, expected at least {len(aar_hud.STATES)}"


@pytest.mark.parametrize("tid", ALL_TRACKS)
def test_the_guide_quotes_the_speed_the_mission_actually_flies(tid):
    """The receiver-clamped number, not the tanker's default — a printed chart
    disagreeing with the airplane is the defect v1.73.0 existed to kill."""
    from pathlib import Path
    from missiongen import aar
    t = tracks.get(tid)
    md = (Path(__file__).parent.parent / "docs"
          / f"{t['guide']}.md").read_text()
    from missiongen.aar_guide import _type_id
    ias = aar.track_ias_kt(t["tanker"], _type_id(t["aircraft"]))
    assert f"{ias} KIAS" in md, f"{tid}: guide does not quote {ias} KIAS"


@pytest.mark.parametrize("tid", ALL_TRACKS)
def test_every_wizard_combination_renders_both_guides(tid, tmp_path):
    """THE DEFECT CLASS: `build()` (PDF) and `markdown()` are near-identical
    twins, and an edit meant for one has landed in the other three times. A
    reportlab call inside the markdown builder raises `NameError` and takes the
    whole track download to a 500 — which is how it was found, by the release
    suite, minutes before shipping.

    Renders EVERY combination the wizard offers, not just the default."""
    from missiongen import aar_guide
    t = tracks.get(tid)
    combos = [(e, a, k) for e, acs in tracks.picker(tid).items()
              for a, tks in acs.items() for k in tks]
    assert combos
    for era, ac, tk in combos:
        aar_guide.markdown(tid, t, "test", out_dir=tmp_path,
                           aircraft=ac, tanker=tk, era=era)
    # the PDF path is slower, so one per era is enough to catch a stray call
    for era in tracks.picker(tid):
        ac = sorted(tracks.picker(tid)[era])[0]
        tk = tracks.picker(tid)[era][ac][0]
        aar_guide.build(tid, t, "test", out_dir=tmp_path,
                        aircraft=ac, tanker=tk, era=era)


# --------------------------------------------------------------------------- #
# Does the PRINTED number match the FLOWN number?
# --------------------------------------------------------------------------- #
def _combos(tid):
    return [(e, a, k) for e, acs in tracks.picker(tid).items()
            for a, tks in acs.items() for k in tks]


@pytest.mark.parametrize("tid", ALL_TRACKS)
def test_the_guide_quotes_the_flown_speed_for_every_combination(tid, tmp_path):
    """Reported from the cockpit: "the documentation needs to reflect the
    accurate flight speeds". The guide is generated per combination, so there
    is no excuse for it to disagree — but nothing was checking, and the tanker
    default and the receiver-clamped number are different values."""
    import re
    from pathlib import Path as _P
    from missiongen import aar, aar_guide
    t = tracks.get(tid)
    for era, ac, tk in _combos(tid):
        md = _P(aar_guide.markdown(tid, t, "test", out_dir=tmp_path,
                                     aircraft=ac, tanker=tk,
                                     era=era)).read_text()
        ias = aar.track_ias_kt(tk, aar_guide._type_id(ac))
        assert f"TRACK: {ias} KIAS" in md, \
            f"{tid}/{era}/{ac}/{tk}: guide does not say TRACK: {ias} KIAS"
        # and no OTHER track speed may appear on the card
        for other in set(re.findall(r"TRACK: (\d+) KIAS", md)):
            assert int(other) == ias, \
                f"{tid}/{era}/{ac}/{tk}: guide also quotes {other} KIAS"


@pytest.mark.parametrize("tid,era,ac,tk", [
    ("aar_probe", "coldwar", "F_14B_U", "ka6d"),
    ("aar_boom", "modern", "A_10C_2", "kc135"),
    ("aar_boom", "coldwar", "F_4E_45MC", "kc135"),
])
def test_the_tanker_actually_flies_the_speed_the_card_prints(tid, era, ac, tk,
                                                             tmp_path):
    """THE ONE THAT MATTERS. A card and a guide can agree with each other and
    both disagree with the airplane. This reads the tanker's speed out of the
    generated mission file and compares it to the printed KIAS."""
    import zipfile
    import re
    from missiongen import aar
    from missiongen.aar_guide import _type_id
    n, key, _v = tracks.rides(tid)[0]
    rc = effective_recipe(key, era)
    rc.update({"template": key, "seed": 4400 + n,
               "aircraft": ac, "tanker_type": tk})
    r = Recipe.from_dict(rc)
    r.validate()
    out = tmp_path / "m.miz"
    generate(r, str(out))
    z = zipfile.ZipFile(out)
    card = z.read("l10n/DEFAULT/dictionary").decode("utf-8", "replace")
    printed = int(re.search(r"TRACK: (\d+) KIAS", card).group(1))
    assert printed == aar.track_ias_kt(tk, _type_id(ac))
    # The map matters to the SPEED, not just the altitude: terrain can raise
    # the track, and the same indicated airspeed at a higher altitude is a
    # larger true airspeed. Comparing the file against a sea-level-ish TAS
    # computed at the tanker's book altitude fails a mission that is correct.
    printed_alt = int(re.search(r"TRACK: \d+ KIAS at ([\d,]+) ft",
                                card).group(1).replace(",", ""))
    assert printed_alt == aar.track_alt_ft(tk, rc["map"])

    # The tanker's ROUTE speed, read through pydcs rather than by regexing a
    # window — a window lands on the unit's spawn speed (0 on a warm start) or
    # on a nearby static, and an assertion that reads the wrong field is the
    # vacuous-guard pattern this codebase keeps producing.
    import dcs
    m = dcs.Mission()
    m.load_file(str(out))
    tt = aar.TANKERS[tk]["type"].id
    grp = None
    for c in m.coalition.values():
        for cty in c.countries.values():
            for g in cty.plane_group:
                if str(g.units[0].type) == tt and len(g.points) > 1:
                    grp = g
    assert grp is not None, f"{tt} is not in the mission as a flight"
    flown_ms = grp.points[0].speed
    expect_ms = aar.track_speed_kmh(tk, _type_id(ac), rc["map"]) / 3.6
    assert abs(flown_ms - expect_ms) < 1.0, \
        (f"card says {printed} KIAS but the tanker's route is "
         f"{flown_ms:.1f} m/s, expected {expect_ms:.1f}")


# --------------------------------------------------------------------------- #
# "On launch, the aircraft should be behind the tanker"
# --------------------------------------------------------------------------- #
ASTERN_RIDES = [(t, n, k) for t in ALL_TRACKS for n, k, v in tracks.rides(t)
                if v.get("air_start") == "astern_tanker"][:6]


def test_there_are_astern_rides_to_check():
    assert len(ASTERN_RIDES) >= 4, ASTERN_RIDES


@pytest.mark.parametrize("tid,n,key", ASTERN_RIDES)
def test_the_pre_contact_start_is_actually_behind_the_tanker(tid, n, key,
                                                             tmp_path):
    """Reported from the cockpit and confirmed by measurement: the player was
    spawning DUE SOUTH of a tanker flying 229 degrees — about 49 degrees off
    its right rear quarter, very nearly abeam — and pointing due NORTH, 131
    degrees away from the tanker's direction of flight, at 300 knots.

    Two causes, both silent. The heading came from `unit.heading`, which pydcs
    had not assigned yet, so it read 0.0. And the ORIENTATION comes from `psi`,
    which pydcs only syncs from `heading` when a group has more than one
    waypoint — a pre-contact air start leaves exactly one.

    This measures the built mission: relative bearing from the tanker's ROUTE
    heading, and the player's own heading against it."""
    import math
    import dcs
    rc = effective_recipe(key, "modern")
    rc.update({"template": key, "seed": 4400 + n})
    r = Recipe.from_dict(rc)
    r.validate()
    out = tmp_path / "m.miz"
    res = generate(r, str(out))
    assert res["stats"].get("air_start"), f"{key} is not an astern start"

    m = dcs.Mission()
    m.load_file(str(out))
    tk_id = aar_mod.TANKERS[res["stats"]["aar"]]["type"].id
    tanker = player = None
    for c in m.coalition.values():
        for cty in c.countries.values():
            for g in cty.plane_group:
                if str(g.units[0].type) == tk_id and len(g.points) > 1:
                    tanker = g
                elif any(str(getattr(u, "skill", "")).endswith("Player")
                         for u in g.units):
                    player = g
    assert tanker and player, (tanker, player)

    a, b = tanker.points[0].position, tanker.points[1].position
    route = math.degrees(math.atan2(b.y - a.y, b.x - a.x)) % 360
    tu, pu = tanker.units[0], player.units[0]
    brg = math.degrees(math.atan2(pu.position.y - tu.position.y,
                                  pu.position.x - tu.position.x)) % 360
    rel = (brg - route) % 360
    assert 165 <= rel <= 195, \
        f"{key}: player is {rel:.0f} deg off the tanker's tail (180 = astern)"

    # and pointing the same way he is. `psi` is the field DCS orients on.
    psi_deg = math.degrees(-pu.psi) % 360
    off = abs((psi_deg - route + 180) % 360 - 180)
    assert off <= 10, \
        f"{key}: player faces {psi_deg:.0f}, tanker flies {route:.0f}"

    # below the track, because down is the escape
    assert tu.alt - 400 < pu.alt < tu.alt, (pu.alt, tu.alt)


def test_the_buddy_tanker_reaches_the_mission_WITH_ITS_STORE(tmp_path):
    """THE ARTIFACT, not the declaration. The first version of this guard
    asserted `TANKERS["ka6d"]["store"]` was set and that the pylon existed in
    pydcs — both true while the mission still shipped `["pylons"] = {}`,
    because nothing checked that the fitting code ran. Disabling it left the
    suite green. This reads the generated file."""
    import zipfile
    rc = effective_recipe("aar_boat", "coldwar")
    rc.update({"template": "aar_boat", "seed": 4410})
    r = Recipe.from_dict(rc)
    r.validate()
    out = tmp_path / "m.miz"
    res = generate(r, str(out))
    assert res["stats"].get("aar") == "ka6d"
    txt = zipfile.ZipFile(out).read("mission").decode("utf-8", "replace")
    spec = aar_mod.TANKERS["ka6d"]["store"]
    clsid = getattr(getattr(aar_mod.TANKERS["ka6d"]["type"], spec[0]),
                    spec[1])[1]["clsid"]
    assert clsid in txt, \
        "the KA-6D is on station with no buddy store — it cannot give fuel"
    i = txt.find('"type"]="A6E"')
    seg = txt[max(0, i - 1600):i + 60]
    assert '["pylons"]' in seg and clsid in seg, \
        "the store is somewhere in the file but not on the tanker"


def test_a_tanker_with_a_built_in_system_gets_no_pylon_store(tmp_path):
    """The other half, so the test above is testing the FITTING and not merely
    that the string appears in every mission."""
    import zipfile
    n, key, _v = tracks.rides("aar_boom")[0]
    rc = effective_recipe(key, "modern")
    rc.update({"template": key, "seed": 4400 + n})
    r = Recipe.from_dict(rc)
    r.validate()
    out = tmp_path / "m.miz"
    generate(r, str(out))
    txt = zipfile.ZipFile(out).read("mission").decode("utf-8", "replace")
    assert "HB_A6E_D704" not in txt, \
        "a KC-135 is carrying an A-6 buddy pod"
