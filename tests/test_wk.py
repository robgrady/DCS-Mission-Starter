"""The White Knights: two tracks built from a 1980 squadron's own paperwork.

WHAT THESE TESTS ARE FOR. The defect classes this content can produce are not
the usual ones, because almost every number here is transcribed rather than
computed:

  1. A TRANSCRIPTION ERROR. A digit wrong in a delivery planning sheet is
     invisible — it looks exactly like a correct number. So the sheets are
     checked against the document's OWN pop-up formulae, which they satisfy to
     the foot. A typo breaks the arithmetic.
  2. A CARD THAT TRAVELS BADLY. The same ride in two theatres tells two
     different truths about the low-level floor. Asserted out of the BUILT
     MISSION on both maps, not off the function that writes it.
  3. THE USUAL SAY/DO GAP. No card may claim a grade the triggers cannot see.
"""
import zipfile

import pytest

from missiongen import wk
from missiongen.recipe import Recipe
from missiongen import generate
from missiongen.templates import effective_recipe, maps_for, templates

ALL_RIDES = [k for k in wk.RIDES]
CHECKOUT = [k for _n, k, _v in wk.rides_in("wk_checkout")]
PROUD = [k for _n, k, _v in wk.rides_in("wk_proud_phantom")]


def _build(key, map_key, tmp_path, seed=31):
    rc = effective_recipe(key, "coldwar", map_key)
    rc.update(template=key, seed=seed)
    r = Recipe.from_dict(rc)
    r.validate()
    out = tmp_path / f"{key}-{map_key}.miz"
    generate(r, str(out))
    return out


def _card(path):
    """The briefing text, which lives in the dictionary and NOT in `mission`.

    Reading the wrong member here is how an assertion passes vacuously; it has
    already happened once in this codebase."""
    return zipfile.ZipFile(path).read(
        "l10n/DEFAULT/dictionary").decode("utf-8", "replace")


# --------------------------------------------------------------------------- #
# 1. The transcribed sheets check out against the document's own formulae
# --------------------------------------------------------------------------- #
def test_there_are_five_delivery_sheets():
    """Guards below iterate DELIVERIES. If it empties they pass vacuously."""
    assert len(wk.DELIVERIES) == 5, sorted(wk.DELIVERIES)


@pytest.mark.parametrize("key", sorted(wk.DELIVERIES))
def test_the_pull_up_point_is_the_apex_over_the_climb_angle(key):
    """PUP = (APEX / climb angle) x 60, from the sheet's own POP UP DATA block.

    This is the check a transcription error cannot survive: change any one of
    the three numbers and the identity breaks."""
    d = wk.DELIVERIES[key]
    want = d["apex_ft"] / d["climb_deg"] * 60
    assert abs(d["pup_ft"] - want) <= 1.5, (key, d["pup_ft"], want)


@pytest.mark.parametrize("key", sorted(wk.DELIVERIES))
def test_the_pull_down_point_is_the_apex_less_fifty_per_degree(key):
    """PDP = APEX - (climb angle x 50). Also the sheet's own formula."""
    d = wk.DELIVERIES[key]
    assert d["pdp_ft"] == d["apex_ft"] - d["climb_deg"] * 50, key


@pytest.mark.parametrize("key", ["dt35", "dt20", "hidrag10"])
def test_the_apex_formula_holds_for_the_primary_profiles(key):
    """APEX = (2 x dive angle x 100) + release altitude / 2."""
    d = wk.DELIVERIES[key]
    want = 2 * d["angle"] * 100 + d["release_ft"] / 2
    assert d["apex_ft"] == want, (key, d["apex_ft"], want)


@pytest.mark.parametrize("direct,dt", [("dive30", "dt35"), ("lald15", "dt20")])
def test_a_direct_delivery_carries_its_DIVE_TOSS_partners_pop_block(direct, dt):
    """The finding that explains why the apex formula does NOT close on the two
    direct sheets — and it is not an error in the document.

    You fly the DIVE TOSS pop-up and revert. Section I: "At PUP, pull to the
    climb angle calculated for the DT delivery you planned to use... if you have
    to revert to your back up direct delivery, at the AOD, check IPP and
    continue to the direct delivery release altitude." So the direct sheet
    prints the DT's apex, PUP, climb angle and PDP, because that is the profile
    you are flying until the moment you revert.
    """
    a, b = wk.DELIVERIES[direct], wk.DELIVERIES[dt]
    for f in ("apex_ft", "pup_ft", "climb_deg", "pdp_ft"):
        assert a[f] == b[f], (direct, dt, f, a[f], b[f])
    assert wk.DELIVERIES[dt]["backup"] == direct
    # ...and it is genuinely NOT its own dive angle's apex, or this test would
    # be asserting a coincidence.
    assert a["apex_ft"] != 2 * a["angle"] * 100 + a["release_ft"] / 2


def test_the_squadrons_turn_performance_assumptions_are_self_consistent():
    """Section I gives airspeed, turn radius, rate and G for ingress and
    delivery. Four numbers describing one turn: they must agree."""
    import math
    g = 32.174
    v = wk.INGRESS["tas_kt"] * 1.68781
    radial = v * v / (g * wk.INGRESS["turn_radius_ft"])
    rate = math.degrees(v / wk.INGRESS["turn_radius_ft"])
    assert abs(radial - wk.INGRESS["g"]) < 0.5, radial
    assert abs(rate - wk.INGRESS["deg_per_sec"]) < 0.5, rate
    v = wk.DELIVERY_TURN["tas_kt"] * 1.68781
    radial = v * v / (g * wk.DELIVERY_TURN["turn_radius_ft"])
    lo, hi = wk.DELIVERY_TURN["radial_g"]
    assert lo - 0.2 <= radial <= hi, radial


# --------------------------------------------------------------------------- #
# 2. The floor: two numbers, and the card says which governs
# --------------------------------------------------------------------------- #
def test_germany_raises_the_floor_above_what_the_squadron_trained_to():
    """The collision the Germany track exists for. Pinned as absolute values,
    not derived from each other."""
    assert wk.FORMATION_MIN_FT == 300
    assert wk.floor_ft("germany") == 500
    assert wk.floor_basis("germany") == "host_nation"
    assert wk.floor_conflicts("germany") is True


def test_egypt_does_not_and_the_squadrons_own_number_stands():
    assert wk.floor_ft("sinai") == wk.FORMATION_MIN_FT
    assert wk.floor_basis("sinai") == "squadron"
    assert wk.floor_conflicts("sinai") is False


def test_an_unlisted_theatre_fails_closed_to_the_most_restrictive_floor():
    """For a MINIMUM altitude, failing closed means the HIGHER number. A floor
    we cannot source is not permission."""
    assert wk.floor_ft("a-map-ed-has-not-built") == max(
        v[0] for v in wk.LOW_LEVEL_FLOOR_FT.values())
    assert wk.floor_ft("a-map-ed-has-not-built") > wk.FORMATION_MIN_FT


@pytest.mark.parametrize("key", ["wk_4_lineabreast", "wk_5_commout",
                                 "wk_6_ridge", "wk_7_threats"])
def test_the_built_mission_briefs_the_floor_that_governs_there(key, tmp_path):
    """Read out of the .miz on BOTH maps. This is the guard that would have
    caught a card hard-coding one theater's number."""
    de = _card(_build(key, "germany", tmp_path))
    eg = _card(_build(key, "sinai", tmp_path))
    assert "500' AGL" in de or "500 FEET GOVERNS" in de, de[:400]
    assert "300' AGL" in eg, eg[:400]
    assert "FEET GOVERNS" not in eg, \
        "Egypt has no host-nation floor and must not claim one"


def test_the_germany_card_does_not_quietly_replace_the_squadrons_number(tmp_path):
    """It must print BOTH. Substituting somebody else's floor for the 70th's
    own would be putting words in a dead man's mouth."""
    c = _card(_build("wk_4_lineabreast", "germany", tmp_path))
    assert "YOUR SQUADRON:" in c, "the squadron's own paragraph has gone"
    assert "FORMATIONS TO 300'" in c, "the squadron's own number has gone"
    assert "Single ship to 100'" in c, "the single-ship number has gone"
    assert "THIS THEATRE:" in c, "the host-nation paragraph has gone"
    assert "500 FEET GOVERNS" in c, "the rule that actually applies has gone"


# --------------------------------------------------------------------------- #
# 3. Route Abort does not travel, and says why
# --------------------------------------------------------------------------- #
def test_the_route_abort_ride_is_germany_only():
    """Inadvertent IMC is the lesson and the weather that teaches it does not
    occur over the Western Desert."""
    assert wk.maps_for("wk_8_abort") == ["germany"]
    assert maps_for("wk_8_abort") == ["germany"]
    assert "sinai" not in maps_for("wk_8_abort")


def test_every_other_checkout_ride_does_travel():
    """Or the 'two maps' promise is a promise about one ride."""
    travel = [k for k in CHECKOUT if "sinai" in maps_for(k)]
    assert len(travel) == len(CHECKOUT) - 1, travel


def test_the_abort_card_explains_the_omission_rather_than_just_omitting(tmp_path):
    c = _card(_build("wk_8_abort", "germany", tmp_path))
    assert "GERMANY ONLY" in c
    assert "2,500' MSL" in c, "the squadron's own worked example has gone"


# --------------------------------------------------------------------------- #
# 4. Every ride builds, everywhere it is advertised
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("key,map_key",
                         [(k, m) for k in ALL_RIDES for m in maps_for(k)])
def test_every_advertised_combination_actually_builds(key, map_key, tmp_path):
    p = _build(key, map_key, tmp_path)
    assert p.exists() and p.stat().st_size > 1000


@pytest.mark.parametrize("key", ALL_RIDES)
def test_every_ride_puts_its_own_card_in_the_mission(key, tmp_path):
    """Not a generic brief — the ride's own. Pinned on the ride title, which is
    unique per card."""
    c = _card(_build(key, maps_for(key)[0], tmp_path))
    assert wk.RIDES[key]["title"].upper()[:18] in c.upper(), key


# --------------------------------------------------------------------------- #
# 5. Say/do — the rule this whole product exists for
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("key", ALL_RIDES)
def test_no_card_claims_a_grade_the_triggers_cannot_see(key):
    c = "\n".join(wk.brief_lines(key, maps_for(key)[0]))
    assert "WHAT THIS RIDE DOES NOT MEASURE" in c, key
    assert "cannot see your dive angle" in c, key


def test_the_tanker_ride_admits_the_plug_is_not_measured():
    """Same constraint the AAR Academy already lives under: ME triggers cannot
    see S_EVENT_REFUELING or read fuel."""
    c = "\n".join(wk.brief_lines("pp_1_drag", "sinai"))
    assert "cannot see a refuelling event" in c


@pytest.mark.parametrize("key", ["pp_4_hidrag", "pp_7_double90"])
def test_a_frag_claim_is_labelled_as_the_proxy_it_is(key):
    """DCS cannot model a frag pattern. A card that implied it could would be
    the say/do gap in its purest form.

    Asserting the word "proxy" alone is not enough and a mutation proved it:
    deleting the disclaimer while leaving the heading "A FRAG PROXY" in place
    left this guard green. The DISCLAIMER is what has to be there."""
    c = "\n".join(wk.brief_lines(key, "sinai"))
    assert "cannot model a frag" in c, key
    assert "approximation" in c or "proxy, not a frag model" in c, key


# The two rides flown alone. The tactical overhead is NOT one of them: the
# break interval it teaches is measured against another airplane, so ride 2
# gets a counterpart like every other flying ride. It was in this list while
# no ride had a counterpart at all, which made the list look right.
SOLO_RIDES = ("wk_1_stepstart", "wk_3_cqt")


@pytest.mark.parametrize("key", [k for k in ALL_RIDES if k not in SOLO_RIDES])
def test_every_flying_ride_explains_what_the_wingman_is_and_costs(key):
    """v1.85.0 inverted the design: after three separate-flight attempts that
    could not hold position on a human, the wingman is seat two of YOUR
    flight. The card must say so — and must still say plainly what that
    costs: he will not fly the two-ship geometry by himself."""
    c = "\n".join(wk.brief_lines(key, maps_for(key)[0]))
    assert "IN YOUR FLIGHT, on your wing" in c, key
    assert "he will not fly the two-ship geometry by" in c.lower() or \
        "will not fly the two-ship geometry" in c, key
    assert "SEPARATE FLIGHT flying a scripted route" not in c, \
        "the old promise is back on the card"


def test_the_solo_rides_do_not_carry_a_wingman_note_they_do_not_need():
    for key in SOLO_RIDES:
        c = "\n".join(wk.brief_lines(key, "germany"))
        assert "IN YOUR FLIGHT, on your wing" not in c, key


@pytest.mark.parametrize("key", ALL_RIDES)
def test_every_card_names_the_document_it_came_out_of(key):
    c = "\n".join(wk.brief_lines(key, maps_for(key)[0]))
    name, date = wk.DOCS[wk.RIDES[key]["doc"]]
    assert name in c and date in c, key
    assert wk.COMMANDER in c, key


@pytest.mark.parametrize("key", ALL_RIDES)
def test_every_card_says_where_it_is_actually_staged(key):
    """Moody AFB is not in DCS. A card that flew this syllabus somewhere else
    without saying so would let a pilot assume the ground under him was the
    ground the document was written about."""
    c = "\n".join(wk.brief_lines(key, maps_for(key)[0]))
    assert "STAGING:" in c, key


def test_the_germany_cards_do_not_claim_a_deployment_that_never_happened():
    """The 347th was drafted into NATO contingency plans and never flew to
    Europe in the Phantom. The card says the first part and denies the second."""
    c = "\n".join(wk.brief_lines("wk_4_lineabreast", "germany"))
    assert "never deployed to Europe" in c
    assert "not a deployment that happened" in c


def test_the_egypt_cards_DO_claim_the_deployment_that_did_happen():
    c = "\n".join(wk.brief_lines("pp_8_bnai", "sinai"))
    assert "PROUD PHANTOM" in c
    assert "3 October 1980" in c


# --------------------------------------------------------------------------- #
# 6. The content is the squadron's, and it is all there
# --------------------------------------------------------------------------- #
def test_the_comm_card_is_the_squadrons_own_with_its_code_names():
    c = "\n".join(wk.brief_lines("wk_1_stepstart", "germany"))
    for code in ("RAYMOND", "DIRT", "DONNA", "GOOD BYE", "BOBBY"):
        assert code in c, code
    assert "381.300" in c and "289.600" in c
    assert wk.CALLSIGN in c


def test_the_bfm_card_carries_all_sixteen_calls_with_their_parameters():
    assert len(wk.BFM_CALLS) == 16, len(wk.BFM_CALLS)
    c = "\n".join(wk.brief_lines("wk_11_bfm", "germany"))
    for call, _m in wk.BFM_CALLS:
        assert call in c, call
    assert "in ten to thirty seconds you'll be dead" in c


def test_the_bnai_card_names_the_reason_the_attack_exists():
    c = "\n".join(wk.brief_lines("pp_8_bnai", "sinai"))
    assert "1973" in c and "SA-6" in c
    assert "Israelis" in c
    # And the disadvantage the pilot is about to live through.
    assert "DEFENSES ARE ALERTED FOR THE NUMBER TWO" in c.upper()


def test_the_four_attacks_print_the_squadrons_own_disadvantage_lists():
    """The guide is blunt about what each attack costs you, and a card that
    printed only the advantages would be selling rather than briefing."""
    for key in ("echelon", "double90", "bnai", "split_lowlow"):
        c = "\n".join(wk.attack_brief(key))
        assert "DISADVANTAGES" in c, key
        assert len(wk.ATTACKS[key]["con"]) >= 3, key


def test_the_delivery_cards_print_the_sheet_not_a_summary():
    c = "\n".join(wk.brief_lines("pp_2_lald", "sinai"))
    for field in ("PICKLE SLANT RANGE", "AIM OFF DISTANCE", "PULL UP POINT",
                  "INTERVALOMETER", "PATTERN LENGTH"):
        assert field in c, field
    assert "5,551'" in c and "121 (+0.8)" in c


# --------------------------------------------------------------------------- #
# 7. Track shape
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("tid", ["wk_checkout", "wk_proud_phantom"])
def test_a_track_is_numbered_one_to_n_with_no_gaps(tid):
    ns = [n for n, _k, _v in wk.rides_in(tid)]
    assert ns == list(range(1, len(ns) + 1)), (tid, ns)


def test_the_two_tracks_are_the_sizes_the_syllabus_promises():
    assert len(CHECKOUT) == 11
    # 11, not 10: the B'NAI is taught twice — ride 8 coached, ride 9 with the
    # calls switched off — because a syllabus that only ever tests is not a
    # syllabus.
    assert len(PROUD) == 11


def test_every_attack_in_the_guide_has_a_ride():
    """THE GUARD THAT WAS MISSING, and Rob found the gap by reading rather than
    by a test failing.

    Section II of Conventional Tactics describes the split attack in TWO forms
    — low/high against one aimpoint, and low/low against separate aimpoints —
    and v1.76.0 shipped only the low/low. The geometry for the low/high was
    sitting in `ATTACKS` with nothing flying it, which is a syllabus quietly
    teaching four fifths of a document.

    Coverage of the source is now asserted, not assumed."""
    flown = {v["attack"] for v in wk.RIDES.values() if v.get("attack")}
    assert flown == set(wk.ATTACKS), (
        f"attacks with no ride: {sorted(set(wk.ATTACKS) - flown)}")
    assert len(wk.ATTACKS) == 5


def test_every_delivery_sheet_has_a_ride():
    """Same guard, other half of the document. Five planning sheets, five
    rides that fly them — the dive-toss ride covers both DT sheets."""
    covered = set()
    for v in wk.RIDES.values():
        if v.get("delivery"):
            covered.add(v["delivery"])
        covered.update(v.get("deliveries") or ())
    # A dive-toss ride also flies its DIRECT back-up, by the drill in Section I.
    for k in list(covered):
        b = wk.DELIVERIES[k].get("backup")
        if b:
            covered.add(b)
    assert covered == set(wk.DELIVERIES), (
        f"sheets with no ride: {sorted(set(wk.DELIVERIES) - covered)}")


def test_both_halves_of_the_split_are_taught_and_in_the_right_order():
    """Low/high before low/low. The low/low adds separate aimpoints, 10,000 ft
    of target separation and a near head-on egress on top of everything the
    low/high already demanded."""
    order = {v["attack"]: v["n"] for v in wk.RIDES.values() if v.get("attack")}
    assert order["split_lowhigh"] < order["split_lowlow"]
    # ...and both come after the three attacks that keep mutual support.
    for easier in ("echelon", "double90", "bnai"):
        assert order[easier] < order["split_lowhigh"], easier


def test_a_ride_key_may_disagree_with_its_position_and_that_is_deliberate():
    """`pp_9_split` sits at position 10. It shipped in v1.76.0 as ride 9, so
    the key is in share links; renaming it to match would be tidier and would
    break them. The number a pilot sees comes from `n`."""
    assert wk.RIDES["pp_9_split"]["n"] == 11
    assert wk.RIDES["pp_9_splithigh"]["n"] == 10
    # ...and the drift got one wider when the coached B'NAI was inserted at 8,
    # which is exactly the pressure this test exists to absorb: positions move
    # when the syllabus changes, keys do not move ever.
    assert wk.RIDES["pp_8_bnai"]["n"] == 9


def test_every_ride_has_a_card_body_and_a_library_template():
    tpl = templates()
    for key in ALL_RIDES:
        assert key in wk._BODY, f"{key} has no brief body"
        assert key in tpl, f"{key} has no Library card"
        assert tpl[key].get("wk_ride") == key
        assert tpl[key]["recipe"]["aircraft"] == "F_4E_45MC"


def test_proud_phantom_is_pinned_to_sinai_and_cannot_be_flown_elsewhere():
    """Its entire value is being specific. Offer it on Germany and the
    deployment, the base and the B'NAI's birthplace all become false."""
    for key in PROUD:
        assert maps_for(key) == ["sinai"], key
        assert templates()[key]["recipe"]["home_airbase"] == "Cairo West"


def test_the_checkout_starts_from_ramstein_on_germany_and_beni_suef_on_sinai():
    """by_map doing its job. Ramstein is where the 1980 CONUS F-4E rotation
    actually went; Beni Suef carries the parallel 18R the squadron's own CQT
    diagram is drawn against."""
    assert effective_recipe("wk_1_stepstart", "coldwar",
                            "germany")["home_airbase"] == "Ramstein"
    assert effective_recipe("wk_1_stepstart", "coldwar",
                            "sinai")["home_airbase"] == "Beni Suef"


def test_a_by_map_block_cannot_teleport_the_mission_to_another_map(monkeypatch):
    """Honouring `{"by_map": {"sinai": {"map": "germany"}}}` would make the
    override a teleport and hand the caller a theater they did not ask for.

    THE HOSTILE CASE IS CONSTRUCTED HERE, not hoped for in shipped data. No
    card we ship attempts this, so a guard that only read the real templates
    would pass whether or not the protection existed — which a mutation
    demonstrated."""
    import missiongen.templates as T
    real = T.templates()
    evil = dict(real)
    evil["wk_4_lineabreast"] = dict(
        real["wk_4_lineabreast"],
        by_map={"sinai": {"map": "germany", "home_airbase": "Beni Suef"}})
    monkeypatch.setattr(T, "templates", lambda: evil)
    rc = T.effective_recipe("wk_4_lineabreast", "coldwar", "sinai")
    assert rc["map"] == "sinai", "a by_map block moved the mission to Germany"
    assert rc["home_airbase"] == "Beni Suef", (
        "the rest of the override must still apply — this is a guard against "
        "teleporting, not against by_map")


def test_the_tracks_are_bound_as_a_series_without_gating():
    """A returning Phantom pilot should be able to fly Proud Phantom cold. A
    card that refuses to open is a card people complain about."""
    from missiongen.resolver import load_json
    t = load_json("tracks")
    assert t["wk_checkout"]["series"] == t["wk_proud_phantom"]["series"]
    assert t["wk_proud_phantom"]["follows"] == "wk_checkout"
    assert "requires" not in t["wk_proud_phantom"]


# --------------------------------------------------------------------------- #
# 8. The printed syllabus
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from server.app import app
    return TestClient(app)


@pytest.mark.parametrize("tid", ["wk_checkout", "wk_proud_phantom"])
def test_a_track_that_advertises_a_guide_can_actually_produce_one(tid, client):
    """These tracks have no tanker and no wizard. Routed through the AAR guide
    path they would 404 on a committed default that does not exist and 400 on a
    tanker they never had — a track advertising a guide it cannot produce is
    the say/do gap with a filename on it."""
    from missiongen.resolver import load_json
    assert load_json("tracks")[tid].get("guide")
    r = client.get(f"/api/track/{tid}/guide.pdf")
    assert r.status_code == 200, r.text[:300]
    assert r.content[:4] == b"%PDF"
    assert len(r.content) > 20000


@pytest.mark.parametrize("tid", ["wk_checkout", "wk_proud_phantom"])
def test_the_guide_carries_every_ride_and_every_card(tid, tmp_path):
    from missiongen import wk_guide
    from missiongen.resolver import load_json
    t = load_json("tracks")[tid]
    md = wk_guide.markdown(tid, t, "9.9.9", tmp_path).read_text()
    for n, key, ride in wk.rides_in(tid):
        assert f"## {n}. {ride['title']}" in md, key
        # ...and the CARD, not a paraphrase of it. Pinned on a line that only
        # appears in the generated brief.
        assert wk.DOCS[ride["doc"]][1] in md, key
    assert "WHAT THIS RIDE DOES NOT MEASURE" in md


def test_the_guide_says_what_it_could_not_source(tmp_path):
    """The January 1980 range is not in any source reached. A syllabus that
    quietly picked one would be inventing history to fill a table."""
    from missiongen import wk_guide
    from missiongen.resolver import load_json
    md = wk_guide.markdown("wk_checkout", load_json("tracks")["wk_checkout"],
                           "9.9.9", tmp_path).read_text()
    assert "Moody AFB" in md
    assert wk.COMMANDER in md


def test_the_checkout_guide_flags_the_ride_that_does_not_travel(tmp_path):
    from missiongen import wk_guide
    from missiongen.resolver import load_json
    md = wk_guide.markdown("wk_checkout", load_json("tracks")["wk_checkout"],
                           "9.9.9", tmp_path).read_text()
    assert "Route Abort" in md
    assert "Cold War Germany only" in md, \
        "the one ride that cannot be flown on both maps must say so"


def test_the_pdf_and_the_markdown_describe_the_same_syllabus(tmp_path):
    """The twin-builder defect has shipped twice in this codebase. Both walk
    wk.brief_lines(); neither restates a card. This pins that they agree on the
    ride list, which is the part written twice."""
    from missiongen import wk_guide
    from missiongen.resolver import load_json
    from pypdf import PdfReader
    t = load_json("tracks")["wk_proud_phantom"]
    md = wk_guide.markdown("wk_proud_phantom", t, "9.9.9", tmp_path).read_text()
    pdf = wk_guide.build("wk_proud_phantom", t, "9.9.9", tmp_path)
    txt = "".join(p.extract_text() for p in PdfReader(pdf).pages)
    txt = " ".join(txt.split())
    for _n, _k, ride in wk.rides_in("wk_proud_phantom"):
        assert ride["title"] in md, ride["title"]
        assert ride["title"] in txt, f"{ride['title']} is in the md, not the pdf"


# --------------------------------------------------------------------------- #
# 9. Livery, waypoints, kneeboard — the three things a card promised and the
#    mission did not contain
# --------------------------------------------------------------------------- #
def _player_group(path):
    import dcs
    m = dcs.Mission()
    m.load_file(str(path))
    for co in m.coalition.values():
        for c in co.countries.values():
            for g in c.plane_group:
                if any(str(getattr(u, "skill", "")) == "Skill.Player"
                       for u in g.units):
                    return g
    return None


def test_the_flight_is_called_REX_on_paper_and_by_its_dcs_name_on_the_radio(tmp_path):
    """Standards Section II: "REX 1, loud and clear". The card said REX and the
    mission called the flight Oyster. Since v1.92.0 the mission calls it the
    DCS name REX maps to (the sim cannot say REX), and the card says both."""
    g = _player_group(_build("wk_4_lineabreast", "germany", tmp_path))
    assert g is not None and g.name.startswith(wk.RADIO_CALLSIGN), g.name if g else None
    assert wk.CALLSIGN == "REX"
    from missiongen import callsign as _cs
    assert wk.RADIO_CALLSIGN in _cs.pool()
    c = "\n".join(wk.brief_lines("wk_4_lineabreast", "germany"))
    assert "REX" in c and wk.RADIO_CALLSIGN in c


@pytest.mark.parametrize("key", [k for k in ALL_RIDES if k != "wk_3_cqt"])
def test_every_flying_ride_has_a_real_flight_plan(key, tmp_path):
    """Every ride shipped with ONE waypoint — the parking spot — while its card
    described an IP, a pop and an egress."""
    g = _player_group(_build(key, maps_for(key)[0], tmp_path))
    assert g is not None, key
    assert len(g.points) >= 3, (key, len(g.points))


def test_the_quick_turn_ride_has_no_flight_plan_and_says_why(tmp_path):
    """It is a ramp, a taxiway and a stopwatch. Waypoints on the F10 map for a
    sortie that never leaves the chocks would be decoration."""
    from missiongen import wk_route
    g = _player_group(_build("wk_3_cqt", "germany", tmp_path))
    assert len(g.points) == 1, len(g.points)
    assert wk_route.legs_for("wk_3_cqt", "germany") == []
    c = "\n".join(wk_route.brief_lines("wk_3_cqt", "germany", []))
    assert "never leaves the chocks" in c


def test_the_low_level_route_is_flown_at_the_theatre_floor():
    """The route must obey the same number the card prints. A flight plan at
    2,000 ft under a card that says 500 would be the say/do gap with waypoints
    on it."""
    from missiongen import wk_route
    for mk in ("germany", "sinai"):
        legs = wk_route.legs_for("wk_4_lineabreast", mk)
        cruise = [l for l in legs if l[0].startswith(("ROUTE", "TP"))]
        assert cruise, mk
        for name, _a, _x, agl, ias in cruise:
            assert agl == wk.floor_ft(mk), (mk, name, agl)
            assert ias >= wk.MIN_IAS_KT, (mk, name, ias)


def test_germany_and_egypt_get_different_route_altitudes():
    """The whole point of by_map, expressed in the flight plan rather than only
    in the prose."""
    from missiongen import wk_route
    de = wk_route.legs_for("wk_4_lineabreast", "germany")[1][3]
    eg = wk_route.legs_for("wk_4_lineabreast", "sinai")[1][3]
    assert de == 500 and eg == 300, (de, eg)


def test_the_delivery_ride_puts_its_IP_at_the_sheets_own_pull_up_point():
    """Not a generic strike IP — the number off the squadron's planning sheet."""
    from missiongen import wk_route
    for ride, dk in (("pp_2_lald", "lald15"), ("pp_3_dive30", "dive30")):
        legs = dict((l[0], l) for l in wk_route.legs_for(ride, "sinai"))
        pup = legs["PULL UP POINT"][1]
        ip = legs["IP"][1]
        want_nm = wk.DELIVERIES[dk]["pup_ft"] / 6076.12
        assert abs((32 - pup) - want_nm) < 0.2, (ride, pup, want_nm)
        assert pup > ip, (ride, "the pull-up must come after the IP")


def test_the_attack_rides_split_at_the_range_the_guide_names():
    from missiongen import wk_route
    for ride, key in (("pp_6_echelon", "echelon"), ("pp_7_double90", "double90"),
                      ("pp_9_split", "split_lowlow")):
        legs = dict((l[0], l) for l in wk_route.legs_for(ride, "sinai"))
        want = wk.ATTACKS[key].get("support_nm") or 4.0
        assert abs((36 - legs["SPLIT POINT"][1]) - want) < 0.05, ride


def test_the_route_ground_reference_is_labelled_as_ours_not_measured():
    """pydcs exposes no terrain elevation. The AGL-to-MSL conversion is our
    estimate and the card has to say so, or a pilot reads a planning altitude
    as a survey."""
    from missiongen import wk_route
    rows = [("ROUTE ENTRY", 500, 400)]
    c = "\n".join(wk_route.brief_lines("wk_4_lineabreast", "germany", rows))
    assert "OUR estimate" in c and "not a survey" in c
    assert "ALTITUDES ABOVE ARE AGL" in c
    assert "SPEEDS ARE INDICATED" in c


@pytest.mark.parametrize("key", ["wk_4_lineabreast", "pp_8_bnai"])
def test_the_ride_card_is_on_the_kneeboard_not_only_in_the_briefing(key, tmp_path):
    """In a Phantom at three hundred feet you have a kneeboard and nothing
    else. A card that only lives in the mission briefing is a card the pilot
    cannot read at the moment it matters."""
    import zipfile as _z
    p = _build(key, maps_for(key)[0], tmp_path)
    pages = [n for n in _z.ZipFile(p).namelist() if n.startswith("KNEEBOARD/")]
    assert len(pages) > 4, (key, len(pages))


def test_a_non_white_knights_card_still_gets_exactly_the_old_four_pages(tmp_path):
    """The card pages APPEND. A pilot who knows the theater page is 03 must not
    find something else there because a different mission was built."""
    import zipfile as _z
    rc = effective_recipe("f100_fulda_cas", "coldwar", "germany")
    rc.update(template="f100_fulda_cas", seed=9)
    r = Recipe.from_dict(rc)
    r.validate()
    out = tmp_path / "f100.miz"
    generate(r, str(out))
    pages = [n for n in _z.ZipFile(out).namelist() if n.startswith("KNEEBOARD/")]
    assert len(pages) == 4, len(pages)


def test_no_kneeboard_page_runs_text_off_the_right_edge(tmp_path):
    """A clipped line on a kneeboard means the pilot reads half a rule and
    believes it. Measured in pixels, out of the rendered page."""
    import zipfile as _z
    import numpy as np
    from PIL import Image
    import io as _io
    p = _build("wk_4_lineabreast", "germany", tmp_path)
    z = _z.ZipFile(p)
    names = sorted(n for n in z.namelist() if n.startswith("KNEEBOARD/"))
    assert len(names) > 4
    for n in names[4:]:
        a = np.array(Image.open(_io.BytesIO(z.read(n))).convert("L"))
        H, W = a.shape
        margin = a[148:H - 84, W - 30:W]
        assert not (margin < 120).any(), f"{n}: text in the right margin"


@pytest.mark.parametrize("key", ALL_RIDES)
def test_every_card_says_what_the_aeroplane_should_look_like(key):
    c = "\n".join(wk.brief_lines(key, maps_for(key)[0]))
    assert "== YOUR AIRCRAFT ==" in c, key
    for fs in ("FS 34079", "FS 34102", "FS 30219", "FS 36622"):
        assert fs in c, (key, fs)
    assert "checkered tail stripe" in c, key


def test_the_livery_card_admits_the_skin_does_not_exist():
    """We describe a checkered tail and the jet wears somebody else's paint.
    Saying so is the only honest option — it is the say/do gap in the one place
    the pilot can actually SEE it."""
    c = "\n".join(wk.brief_lines("pp_8_bnai", "sinai"))
    assert "DCS SHIPS NO 70 TFS LIVERY" in c
    assert "blank airplane" in c


def test_the_livery_block_separates_what_is_known_from_what_is_not():
    c = "\n".join(wk.livery_lines())
    assert "NOT ESTABLISHED, AND NOT INVENTED HERE:" in c
    assert len(wk.LIVERY["unverified"]) >= 3
    # the two airframes actually photographed in 1980
    assert "68-0429" in c and "68-0369" in c


# --------------------------------------------------------------------------- #
# 10. The squadron's own diagrams
# --------------------------------------------------------------------------- #
def test_every_attack_has_the_squadrons_diagram_on_disk():
    """A pilot in the pop needs a picture. Redrawing them would have meant
    re-deriving every angle by eye from a scan — a second source of truth for
    geometry nobody can check — so these are the squadron's own pages."""
    assert len(wk.DIAGRAMS) == len(wk.ATTACKS) == 5
    for k in wk.ATTACKS:
        p = wk.diagram_path(k)
        assert p is not None and p.is_file(), k
        assert p.stat().st_size > 10_000, (k, p.stat().st_size)


def test_a_missing_diagram_degrades_to_no_page_and_never_raises(monkeypatch):
    """An absent asset must cost you a picture, not a mission."""
    monkeypatch.setattr(wk, "DIAGRAMS", dict(wk.DIAGRAMS, bnai="not_here.png"))
    assert wk.diagram_path("bnai") is None
    assert wk.diagram_path("nonesuch") is None


def test_the_diagrams_are_clean_line_art_not_a_grey_scan():
    """Thresholded to paper and ink. A gray halo reads as smudge on a kneeboard
    that renders on a paper background."""
    import numpy as np
    from PIL import Image
    for k in wk.ATTACKS:
        a = np.array(Image.open(wk.diagram_path(k)).convert("L"))
        mid = ((a > 60) & (a < 200)).mean()
        assert mid < 0.06, (k, mid)     # antialiasing from the resize only
        assert (a < 60).mean() > 0.005, (k, "no ink at all")


def test_the_punch_holes_are_gone_but_the_type_is_not():
    """The first cleanup pass used fill ratio alone and ate the lettering —
    "DOUBLE 90" came out "OU LE O". Pinned on the words that were lost."""
    import numpy as np
    from PIL import Image
    from scipy import ndimage
    for k in wk.ATTACKS:
        a = np.array(Image.open(wk.diagram_path(k)).convert("L"))
        H, W = a.shape
        lab, _n = ndimage.label(a < 60)
        for i, sl in enumerate(ndimage.find_objects(lab), start=1):
            h = sl[0].stop - sl[0].start
            w = sl[1].stop - sl[1].start
            if w < 25 or h < 30:
                continue
            fill = (lab[sl] == i).sum() / float(w * h)
            assert fill < 0.6, (k, "a solid disc survived", w, h, fill)


def _kb_pages(path):
    import zipfile as _z
    return sorted(n for n in _z.ZipFile(path).namelist()
                  if n.startswith("KNEEBOARD/"))


def _expected_pages(key, map_key):
    """4 reference pages + however many the card needs + 1 if there is a
    diagram. Counted, not eyeballed: the first version of this guard checked
    ink density on the last page, and text pages and line art are both mostly
    white — so a mutation that removed the diagram entirely went unnoticed."""
    from missiongen import kneeboard, wk_route
    card = wk.brief_lines(key, map_key)
    fp = wk_route.brief_lines(key, map_key,
                              wk_route.legs_for(key, map_key) and [
                                  (n, a, i) for n, _x, _y, a, i
                                  in wk_route.legs_for(key, map_key)])
    if fp:
        card = card + [""] + fp
    n = 4 + len(kneeboard.pages_text("T", "S", card))
    if (wk.RIDES[key].get("attack")
            and wk.diagram_path(wk.RIDES[key]["attack"])):
        n += 1
    return n


@pytest.mark.parametrize("key", [k for k, v in wk.RIDES.items()
                                 if v.get("attack")])
def test_an_attack_ride_carries_its_diagram_as_a_kneeboard_page(key, tmp_path):
    assert len(_kb_pages(_build(key, "sinai", tmp_path))) == \
        _expected_pages(key, "sinai"), key


def test_a_ride_with_no_attack_gets_no_diagram_page(tmp_path):
    """Only the five attacks have one. A delivery ride ends on its card."""
    key = "pp_4_hidrag"
    assert not wk.RIDES[key].get("attack")
    assert len(_kb_pages(_build(key, "sinai", tmp_path))) == \
        _expected_pages(key, "sinai")


def test_the_diagram_page_never_enlarges_the_scan(tmp_path):
    """An 850 px scan blown up to fill a 1024 px page turns line art into
    fuzz, and a fuzzy diagram at three hundred feet is worse than a small
    sharp one. Asserted on the RENDERED page, by finding the artwork.

    Tested against `page_image` directly rather than through a built mission:
    at mission level a text page and a diagram page are both mostly white, and
    that similarity is what made the first version of this guard useless."""
    import numpy as np
    from PIL import Image
    from missiongen import kneeboard

    # A SMALL synthetic source, not one of the real diagrams. The shipped
    # scans are ~1120 px tall and the page body is ~1090, so height already
    # constrains them and the no-enlarge rule never fires — a guard using one
    # would pass whether or not the rule existed, which is exactly what a
    # mutation demonstrated.
    sw, sh = 300, 200
    small = Image.new("L", (sw, sh), 255)
    small.paste(0, (10, 10, sw - 10, sh - 10))          # a solid black block
    small.paste(255, (30, 30, sw - 30, sh - 30))        # hollowed to a frame
    src = tmp_path / "small.png"
    small.save(src)
    assert sw < kneeboard.W - 96 and sh < 900, "the source must FIT, or the " \
        "no-enlarge rule is never exercised"

    page = kneeboard.page_image("TEST", "SINAI", str(src), ["a caption"])
    a = np.array(page.convert("L"))
    ink = a < 60
    cols = np.where(ink[200:1150].any(axis=0))[0]
    rows = np.where(ink[200:1150].any(axis=1))[0]
    assert len(cols) and len(rows), "nothing was drawn"
    assert cols[-1] - cols[0] <= sw + 2, (cols[-1] - cols[0], sw)
    assert rows[-1] - rows[0] <= sh + 2, (rows[-1] - rows[0], sh)


def test_the_diagram_says_where_it_came_from():
    """A diagram with no provenance is just a drawing."""
    for k in wk.ATTACKS:
        note = " ".join(wk.diagram_note(k))
        assert "70 TFS Conventional Tactics" in note, k
        assert "27 Jan 1980" in note, k
        assert "not redrawn" in note, k
        assert wk.ATTACKS[k]["section"] in note, k


@pytest.mark.parametrize("tid", ["wk_proud_phantom"])
def test_the_printed_guide_carries_every_diagram(tid, tmp_path):
    from missiongen import wk_guide
    from missiongen.resolver import load_json
    from pypdf import PdfReader
    t = load_json("tracks")[tid]
    md = wk_guide.markdown(tid, t, "9.9.9", tmp_path).read_text()
    for k in wk.ATTACKS:
        assert wk.DIAGRAMS[k] in md, k
    pdf = wk_guide.build(tid, t, "9.9.9", tmp_path)
    txt = " ".join("".join(p.extract_text()
                           for p in PdfReader(pdf).pages).split())
    # ONE DIAGRAM PAGE PER RIDE THAT FLIES AN ATTACK — not per attack. The
    # B'NAI is flown twice in Proud Phantom (coached, then not), and both cards
    # need the drawing in front of them; asserting len(ATTACKS) here would make
    # teaching an attack twice look like a bug.
    want = sum(1 for _n, _k, r in wk.rides_in(tid) if r.get("attack"))
    assert txt.count("the squadron's diagram") == want, txt.count(
        "the squadron's diagram")


# --------------------------------------------------------------------------- #
# 11. The counterpart, and what the jet carries
# --------------------------------------------------------------------------- #
def _groups(path, prefix=None):
    prefix = prefix or wk.RADIO_CALLSIGN
    import dcs
    m = dcs.Mission()
    m.load_file(str(path))
    out = []
    for co in m.coalition.values():
        for c in co.countries.values():
            for g in c.plane_group:
                if g.name.startswith(prefix):
                    out.append(g)
    return sorted(out, key=lambda g: g.name)


@pytest.mark.parametrize("key", [k for k in ALL_RIDES
                                 if k not in SOLO_RIDES])
def test_the_wingman_the_card_promises_is_actually_in_the_mission(key,
                                                                  tmp_path):
    """THE DEFECT ROB FOUND BY FLYING IT — twice, in two designs. First the
    cards promised a separate flight and the missions carried one airplane;
    then the separate flight existed and "doesn't fly with me at all",
    because DCS gives an independent flight no way to hold position on a
    human. Seat two of the player's own group is the one native mechanism
    that does. So: ONE flight, TWO airplanes, and the second one is AI."""
    gs = _groups(_build(key, maps_for(key)[0], tmp_path))
    assert len(gs) == 1, (key, [g.name for g in gs])
    assert len(gs[0].units) == 2, (key, len(gs[0].units))
    skills = [str(u.skill).split(".")[-1] for u in gs[0].units]
    assert skills[0] == "Player" and skills[1] == "Excellent", skills
    # ...armed the same: a wingman flying the attack with empty pylons is a
    # different airplane
    p0 = {k for k, v in (gs[0].units[0].pylons or {}).items() if v}
    p1 = {k for k, v in (gs[0].units[1].pylons or {}).items() if v}
    assert p0 == p1 and p0, (key, sorted(p0), sorted(p1))


def test_the_promise_and_the_aeroplane_come_from_one_function():
    """A hand-kept list of ride keys is how the card and the file drifted
    apart in the first place.

    THE ASSERTION IS DELIBERATELY NOT `promised == wk.has_counterpart(...)`.
    `brief_lines` calls `has_counterpart` to decide whether to print the note,
    so that comparison is self-referential: replace the predicate with a
    hand-kept list and BOTH sides move together and the test stays green. It
    was weak exactly the way the thing it guards against is weak.

    So the card is compared to the ROUTE MODULE, whose counterpart-legs
    table is still the single predicate deciding which rides are two-ships —
    it now sizes the player's own group instead of building a second one.
    Three independent things still have to agree: the printed promise, the
    predicate, and the group size the builder derives.
    """
    from missiongen import wk_route
    for key in ALL_RIDES:
        mk = maps_for(key)[0]
        card = "\n".join(wk.brief_lines(key, mk))
        promised = "IN YOUR FLIGHT, on your wing" in card
        flown = bool(wk_route.counterpart_legs(key, mk))
        assert promised == flown, (key, promised, flown)


@pytest.mark.parametrize("key", SOLO_RIDES)
def test_the_solo_rides_have_no_wingman_and_do_not_claim_one(key, tmp_path):
    assert not wk.has_counterpart(key, "germany")
    card = "\n".join(wk.brief_lines(key, "germany"))
    assert "IN YOUR FLIGHT, on your wing" not in card
    gs = _groups(_build(key, "germany", tmp_path))
    assert len(gs) == 1 and len(gs[0].units) == 1, \
        (key, len(gs), len(gs[0].units))


def test_the_two_ship_predicate_still_reads_the_squadron_geometry():
    """`counterpart_legs` no longer builds a flight — v1.85.0 moved the
    wingman into the player's group — but it remains THE predicate for which
    rides are two-ships, so its tables must stay the squadron's numbers, not
    a hand list. Spot-checked at both ends of the syllabus."""
    from missiongen import wk_route
    assert wk_route.counterpart_legs("wk_4_lineabreast", "germany")
    assert wk_route.counterpart_legs("pp_8_bnai", "sinai")
    assert not wk_route.counterpart_legs("wk_1_stepstart", "germany")


@pytest.mark.parametrize("key", [k for k, v in wk.RIDES.items()
                                 if v.get("delivery") or v.get("attack")])
def test_a_ride_that_drops_something_carries_something_to_drop(key, tmp_path):
    """The sheet said 6 x MK-82LD and the jet carried four Sparrows and three
    Sidewinders. `mission_kind` was never set, so every ride composed the
    air-to-air fit."""
    gs = _groups(_build(key, "sinai", tmp_path))
    for g in gs:
        st = {int(k): (v or {}).get("CLSID", "")
              for k, v in (g.units[0].pylons or {}).items()}
        assert any("MK-82" in v for v in st.values()), (key, g.name, st)


@pytest.mark.parametrize("key", [k for k, v in wk.RIDES.items()
                                 if v.get("delivery") or v.get("attack")])
def test_the_stores_on_the_card_are_the_stores_on_the_pylons(key, tmp_path):
    """Read back out of the .miz. The composed CAP fit used to run first and
    leave a tank and two AIM-9P5s hanging beside the MER, so the card listed
    one thing and the jet wore another."""
    want = wk.loadout_for(key)
    assert want, key
    g = _groups(_build(key, "sinai", tmp_path))[0]
    got = {int(k): (v or {}).get("CLSID", "")
           for k, v in (g.units[0].pylons or {}).items()}
    assert got == want, (key, sorted(got.items()), sorted(want.items()))


def test_the_high_drag_sheet_gets_snakeyes_and_the_rest_get_low_drag():
    """4 x MK-82HD on the double 90 and its own delivery ride; 6 x MK-82LD
    everywhere else. Both counts are the sheet's."""
    hd = wk.loadout_for("pp_4_hidrag")
    assert hd.get(3) == hd.get(11) == wk.MK82_HD_TER and 7 not in hd
    assert wk.loadout_for("pp_7_double90") == hd, \
        "the Double 90 is FOR high drag"
    for k in ("pp_2_lald", "pp_3_dive30", "pp_5_divetoss", "pp_8_bnai"):
        assert wk.loadout_for(k).get(7) == wk.MK82_LD_MER, k


def test_the_stores_block_counts_what_the_sheet_counts():
    c = "\n".join(wk.loadout_lines("pp_2_lald"))
    assert "6 x Mk-82 total" in c
    c = "\n".join(wk.loadout_lines("pp_4_hidrag"))
    assert "4 x Mk-82 total" in c
    assert not wk.loadout_lines("wk_4_lineabreast"), \
        "a ride that drops nothing must not print a stores block"


def test_the_air_to_air_fit_is_period_correct():
    """AIM-9P5 entered service in the 1980s; this is January 1980. The sheet
    fit carries the AIM-9J and the AIM-7E-2."""
    fit = wk.loadout_for("pp_2_lald")
    assert wk.AIM9J in fit.values() and wk.AIM7E2 in fit.values()
    assert not any("9P5" in v for v in fit.values())
