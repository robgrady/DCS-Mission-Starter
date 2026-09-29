"""Air refuelling: the speed has to be one the receiver can actually fly.

THE BUG THIS FILE EXISTS TO PIN.

Every tanker this product ever generated flew at `speed=550` (pydcs takes km/h)
at 6,096 m. Measured out of a built mission that is **152.8 m/s — 297 kt TAS,
about 217 KIAS at 20,000 ft**, for every tanker, every receiver, every era.

Boom AAR for fighters lives in the high 200s to low 300s KIAS. At 217 an F-16
behind a KC-135 is on the back of the drag curve fighting the airplane instead
of flying the position, which is indistinguishable — to the pilot — from being
bad at refuelling. Nothing errored. The mission built. It was simply not a
refuelling track.

So the assertions here are in **KIAS, computed from the mission file** — the
unit the pilot flies and the unit the brief prints, not the true airspeed the
file happens to store. That conversion is the entire fix, so it is the thing
under test.
"""
import math
import re
import tempfile
import zipfile

import pytest

import dcs.lua as lua

from missiongen import Recipe, aar, generate
from missiongen.resolver import load_json
from missiongen.templates import effective_recipe

TEMPLATES = load_json("mission_templates")
AAR_CARDS = sorted(k for k in TEMPLATES
                   if k.startswith("aar_") or k == "qf_tanker")


def _build(rc, tmp_path, name="m.miz"):
    path = str(tmp_path / name)
    generate(Recipe.from_dict(rc), path)
    with zipfile.ZipFile(path) as z:
        return lua.loads(z.read("mission").decode("utf-8"))["mission"]


def _tanker_and_player(mission):
    tk = tk_group = player = None
    for co in mission["coalition"]["blue"].get("country", {}).values():
        for g in co.get("plane", {}).get("group", {}).values():
            units = list(g["units"].values())
            if "Texaco" in (g.get("name") or ""):
                tk, tk_group = units[0], g
            if any(u.get("skill") in ("Player", "Client") for u in units):
                player = units[0]
    return tk, tk_group, player


def _track_kias(tk_group):
    """What the tanker is ACTUALLY doing, in the unit a pilot reads."""
    pt = list(tk_group["route"]["points"].values())[0]
    alt_m = pt.get("alt") or 0
    tas_kt = (pt.get("speed") or 0) * 1.94384
    sigma = (1.0 - 2.25577e-5 * alt_m) ** 4.2559
    return tas_kt * math.sqrt(sigma), alt_m * 3.28084


@pytest.mark.parametrize("key", sorted(aar.TANKERS))
def test_the_track_speed_is_flyable_not_217_knots(key, tmp_path):
    """The regression, stated as a band rather than a value.

    A tanker below 180 KIAS is unflyable for a fast jet and above 330 is
    unflyable for a Hercules. The old 217 sat inside neither aircraft's comfort
    and was applied to both."""
    t = aar.TANKERS[key]
    ias = t["ias_kt"]
    assert 180 <= ias <= 330, f"{key} briefs {ias} KIAS, which nobody can fly"
    # And the km/h the mission file gets must round-trip back to that IAS.
    back = aar.ias_to_tas_kt(ias, t["alt_ft"]) * 1.852
    assert abs(back - aar.track_speed_kmh(key)) < 0.5


def test_the_conversion_is_a_conversion_and_not_the_identity():
    """The whole bug in one assertion: IAS and TAS are not the same number, and
    treating them as one is what produced 217 KIAS from a 297 kt table."""
    assert aar.ias_to_tas_kt(300, 0) == pytest.approx(300, abs=1)
    tas_20k = aar.ias_to_tas_kt(300, 20000)
    assert tas_20k > 380, (
        f"300 KIAS at 20,000 ft should be well over 380 kt true; got {tas_20k:.0f}")


@pytest.mark.parametrize("key", AAR_CARDS)
def test_an_aar_card_puts_the_tanker_where_it_says(key, tmp_path):
    """Read back out of the file, in KIAS, against the card's own tanker
    table — the number the procedure card prints for the pilot to fly."""
    v = TEMPLATES[key]
    for era in v["eras"]:
        rc = effective_recipe(key, era)
        rc.setdefault("map", v.get("default_map", "caucasus"))
        rc.update(era=era, template=key, seed=7)
        m = _build(rc, tmp_path, f"{key}-{era}.miz")
        tk, tk_group, _p = _tanker_and_player(m)
        assert tk is not None, f"{key}/{era}: an AAR card with no tanker"
        ias, alt_ft = _track_kias(tk_group)
        tk_key, want = next((k, t) for k, t in aar.TANKERS.items()
                            if t["type"].id == tk["type"])
        assert abs(ias - want["ias_kt"]) <= 5, (
            f"{key}/{era}: {tk['type']} is flying {ias:.0f} KIAS, the card "
            f"briefs {want['ias_kt']}")
        # NOT `want["alt_ft"]` — that is the tanker's own preferred block, and
        # terrain can push the track above it. The card prints the raised
        # number, so the file must contain the raised number.
        want_alt = aar.track_alt_ft(tk_key, rc["map"])
        assert abs(alt_ft - want_alt) <= 100, (
            f"{key}/{era}: {tk['type']} is at {alt_ft:.0f} ft, the card "
            f"briefs {want_alt}")


@pytest.mark.parametrize("key", [k for k in AAR_CARDS
                                 if TEMPLATES[k].get("air_start") == "astern_tanker"])
def test_the_sortie_starts_at_the_boom(key, tmp_path):
    """The point of the whole set. A pilot practising refuelling wants
    repetitions of the last thirty seconds; the old card spent fifteen minutes
    getting there. Pre-contact is 1 nm astern and 1,000 ft below — BELOW,
    because the escape from a bad approach is down and the tanker is the one
    thing up there you must not climb into."""
    v = TEMPLATES[key]
    for era in v["eras"]:
        rc = effective_recipe(key, era)
        rc.setdefault("map", v.get("default_map", "caucasus"))
        rc.update(era=era, template=key, seed=7)
        m = _build(rc, tmp_path, f"{key}-{era}-astern.miz")
        tk, _g, player = _tanker_and_player(m)
        assert tk and player
        nm = math.hypot(player["x"] - tk["x"], player["y"] - tk["y"]) / 1852.0
        assert nm == pytest.approx(1.0, abs=0.15), (
            f"{key}/{era}: player starts {nm:.2f} nm from the tanker, not at "
            f"pre-contact")
        assert (tk.get("alt") or 0) - (player.get("alt") or 0) > 150, (
            f"{key}/{era}: the player is not below the tanker")


@pytest.mark.parametrize("receiver,era,carrier,expect_boom", [
    ("F-16C_50", "modern", False, True),
    ("F-4E-45MC", "coldwar", False, True),      # Jester's jet takes the boom
    ("A-10C_2", "gwot", False, True),
    ("FA-18C_hornet", "modern", False, False),
    ("FA-18C_hornet", "modern", True, False),
    ("AV8BNA", "modern", False, False),
])
def test_the_receiver_gets_a_tanker_it_can_actually_use(receiver, era, carrier,
                                                        expect_boom):
    """Boom to a probe jet is worse than no tanker: the mission builds, the
    tanker flies the track, the pilot joins, and nothing happens. That reads as
    'the tool is broken', not 'wrong tanker'."""
    key = aar.choose(receiver, era, carrier=carrier)
    assert key, f"{receiver} in {era} got no tanker at all"
    assert aar.TANKERS[key]["boom"] is expect_boom


def test_the_boat_gets_the_air_wings_own_tanker():
    """A Hornet off the carrier should meet a Viking, and a Cold War Tomcat an
    Intruder with a buddy pack — not a land-based Hercules. An altitude
    tie-break used to hand both of them the Hercules."""
    assert aar.choose("FA-18C_hornet", "modern", carrier=True) == "s3b"
    assert aar.choose("F-14A-135-GR", "coldwar", carrier=True) == "ka6d"


def test_an_aircraft_that_cannot_refuel_gets_no_tanker(tmp_path):
    """And no brief mentioning one. The first version of this warned 'no tanker
    placed' and then placed one through the legacy fallback — a warning saying
    the opposite of the file."""
    m = _build(dict(map="caucasus", era="modern", aircraft="Su_25T",
                    coalition="blue", slots=1, seed=7, bb_tanker=True),
               tmp_path, "noaar.miz")
    tk, _g, _p = _tanker_and_player(m)
    assert tk is None, "a tanker was placed for an aircraft that cannot refuel"


def test_an_incompatible_explicit_pick_warns_rather_than_silently_swapping(tmp_path):
    """A pilot who asks for a KC-130 and gets a KC-135 without being told has
    been lied to quietly, which is worse than being refused."""
    path = str(tmp_path / "mismatch.miz")
    res = generate(Recipe.from_dict(
        dict(map="caucasus", era="modern", aircraft="F_16C_50", coalition="blue",
             slots=1, seed=7, bb_tanker=True, tanker_type="kc130")), path)
    assert any("cannot refuel" in w for w in res.get("warnings", [])), \
        f"no warning for an incompatible tanker pick: {res.get('warnings')}"


@pytest.mark.parametrize("key", sorted(aar.TANKERS))
def test_every_tanker_says_where_its_numbers_came_from(key):
    """These operating points are TUNED, not quoted — no document in our source
    library states AAR airspeed bands. `basis` carries that admission next to
    the number, the same way the roadmap's magnetic-variation note does."""
    assert aar.TANKERS[key].get("basis"), f"{key} has no stated basis"


def test_the_procedure_card_is_specific_to_the_tanker():
    """A generic card on a specific tanker is the failure mode the BFM
    standards cards were built to avoid: the pilot debriefs against numbers
    that did not apply to the ride they flew."""
    boom = "\n".join(aar.brief_lines("kc135", "F-16C_50"))
    drogue = "\n".join(aar.brief_lines("kc130", "FA-18C_hornet"))
    assert "300 KIAS at 20,000 ft" in boom
    assert "230 KIAS at 15,000 ft" in drogue
    assert "boom operator flies the boom" in boom
    assert "probe into the basket" in drogue
    assert "fly the probe to the basket" in drogue.lower()
    # Scoped to the CONTACT instructions, not the whole card. The shared
    # PIO section legitimately names both — "look at the tanker, not the boom
    # or basket" is the same lesson for either — and an over-broad search here
    # failed on correct content, which is the third time that pattern has bitten
    # in this codebase.
    boom_contact = boom.split("4. CONTACT.")[1].split("BEFORE YOU FLY")[0]
    assert "basket" not in boom_contact.lower(), \
        "the boom card's contact instructions are written in basket terms"
    assert "operator will" in boom_contact, \
        "the boom card stopped saying who flies the boom"


# ---------------------------------------------------------------------------
# The instructional content, which is the actual product here. The tanker
# being at the right speed is necessary and not sufficient — a pilot who
# cannot refuel usually has a control-curve problem and a gain problem, and
# neither is fixed by putting the tanker at 300 knots.
# ---------------------------------------------------------------------------

def test_the_card_sends_them_to_their_controller_settings_first():
    """The single most-reported fix in the community is an axis curve, and it
    lives outside the mission entirely. A refuelling card that never mentions
    it has skipped the step that actually unblocks people."""
    card = "\n".join(aar.brief_lines("kc135", "F-16C_50"))
    assert "CHECK YOUR STICK" in card
    for principle in ("gimbal", "longer stick", "Deadzone", "curve the throttle"):
        assert principle in card, f"the setup section lost '{principle}'"


def test_the_card_refuses_to_give_a_universal_curve_number():
    """Honest-numbers rule, applied to advice rather than geometry. The right
    curve is a function of gimbal quality and stick length — published
    recommendations range from 0 to 30 for the same task on different hardware.
    A single number here would be confidently wrong for most readers, which is
    the failure mode this codebase keeps writing tests about."""
    card = "\n".join(aar.brief_lines("kc135", "F-16C_50"))
    assert "NO right number" in card
    assert not re.search(r"(?:set|use|try)\s+(?:a\s+)?curve\s+(?:of\s+)?\d+",
                         card, re.I), "the card prescribes a specific curve value"


def test_the_card_explains_the_oscillation_instead_of_scolding():
    """PIO is a control-theory problem with four named levers, not a character
    defect. Naming it is what turns 'I am bad at this' into something a pilot
    can act on — and 'look at the tanker' stops being a comfort tip and starts
    being the removal of a second oscillator from the loop."""
    card = "\n".join(aar.brief_lines("kc135", "F-16C_50"))
    assert "pilot-" in card and "oscillation" in card
    assert "180 degrees" in card, "the phase explanation is gone"
    assert "LESS GAIN" in card
    assert "noise source" in card


def test_the_card_states_measurable_pass_criteria():
    """Otherwise 'practice refuelling' has no finish line and the pilot cannot
    tell improvement from luck."""
    card = "\n".join(aar.brief_lines("kc135", "F-16C_50"))
    # v1.74.0 split this into a 15 s GATE and a 60 s STANDARD, because
    # one number was doing two jobs. Both must survive.
    assert "PRE-CONTACT, THE GATE" in card
    assert "PRE-CONTACT, THE STANDARD" in card
    assert "60 seconds" in card
    assert "1 to 3 knots" in card
    assert "three-foot box" in card


def test_the_card_sets_an_honest_expectation_of_how_long_it_takes():
    """Thirty minutes a day for a fortnight. Telling someone that is kinder
    and more useful than implying it should click today — and it is the figure
    the community converges on."""
    card = "\n".join(aar.brief_lines("kc130", "FA-18C_hornet"))
    assert "thirty minutes a day" in card and "two" in card
    assert "not the exception" in card


@pytest.mark.parametrize("key", sorted(aar.TANKERS))
def test_the_pass_criteria_quote_this_tankers_own_speed(key):
    """A closure criterion is meaningless without the speed it is relative to,
    and a generic card on a specific tanker is the failure the BFM standards
    cards were built to avoid."""
    card = "\n".join(aar.brief_lines(key, "F-16C_50"))
    # The number the PAIRING flies, not the tanker's default. Those differ
    # whenever the receiver's band clamps it, and a card quoting the default
    # while the mission flew something else is a chart disagreeing with the
    # airplane — which is the whole reason v1.73.0 existed.
    assert f"{aar.track_ias_kt(key, 'F-16C_50')} KIAS" in card
    assert "TRACK: " in card


# ---------------------------------------------------------------------------
# The hardware page. Two of its claims are CORRECTIONS, and both are the kind
# of thing that quietly reverts: the negative finding on force feedback, and
# the fact that this card's own curve advice is wrong for FFB users.
# ---------------------------------------------------------------------------

def test_the_hardware_page_reports_the_negative_ffb_finding():
    """We went looking for evidence that force feedback helps refuelling and
    found none — not weak evidence, none. Saying so is the honest output, and
    it is the claim most likely to get quietly upgraded to 'FFB helps' by
    someone editing for tone."""
    h = "\n".join(aar.hardware_lines())
    assert "NO EVIDENCE" in h
    assert "not a supported reason" in h, \
        "the page no longer discourages buying FFB to fix refuelling"


def test_the_hardware_page_corrects_this_cards_own_curve_advice_for_ffb():
    """The procedure card says 'add curve until small corrections stop
    overshooting'. VPforce's documentation says curves and saturation are
    incompatible with FFB and must be disabled — because on FFB, DCS also
    WRITES stick position to represent trim, and a curve desynchronises that.

    A product that gives one piece of advice in one place and contradicts it in
    another without saying so is worse than either piece alone."""
    h = "\n".join(aar.hardware_lines())
    assert "ONE THING ON THIS CARD IS WRONG FOR YOU" in h
    assert "SPRING GRADIENT" in h and "DAMPING" in h
    assert "NOT friction" in h and "NOT inertia" in h


def test_the_hardware_page_says_where_the_ffb_settings_advice_came_from():
    """Nobody has published AAR-specific FFB settings. Ours is reasoning from
    the effect definitions, and it says so — same discipline as `basis` on the
    tanker table."""
    h = "\n".join(aar.hardware_lines())
    assert "not a" in h and "quoted source" in h


def test_the_vr_claim_is_bounded_by_range_not_left_as_vr_is_better():
    """'VR helps with refuelling' is true and useless. The mechanism is stereo
    depth, which falls off as the SQUARE of range — so it does real work inside
    ~100 ft and none at all at a mile astern. A pilot who believes VR helps
    them find the tanker has learned the wrong thing."""
    h = "\n".join(aar.hardware_lines())
    assert "5 and 100 ft" in h, "the bounded range claim is gone"
    assert "NOTHING" in h and "1 nm astern" in h
    assert "does not help you find the tanker" in h


def test_the_vr_section_carries_the_real_world_corroboration():
    """The KC-46 Remote Vision System is the strongest evidence in the whole
    research pass — real boom operators failing at depth judgment from camera
    displays for a decade — and it is what raises this above sim folklore."""
    h = "\n".join(aar.hardware_lines())
    assert "KC-46" in h and "hyper-stereo" in h


def test_the_known_dcs_defect_is_named_so_pilots_stop_blaming_themselves():
    """The KC-135's director lights are a pre-rendered texture, not lights.
    Confirmed by an ED beta tester, reported since 2021, still open. A pilot
    squinting at them in VR should know it is not their headset."""
    h = "\n".join(aar.hardware_lines())
    assert "ARE NOT LIGHTS" in h
    assert "texture" in h


def test_the_hardware_page_rides_only_on_the_refuelling_cards(tmp_path):
    """It is read once, on the ground. Stapling two pages of settings advice to
    every mission that happens to have a tanker buries the procedure."""
    m = _build(dict(map="caucasus", era="modern", aircraft="F_16C_50",
                    coalition="blue", slots=1, seed=7, bb_tanker=True),
               tmp_path, "plain.miz")
    import zipfile as _z
    # rebuild to read the dictionary rather than the parsed mission
    path = str(tmp_path / "plain2.miz")
    generate(Recipe.from_dict(dict(map="caucasus", era="modern",
                                   aircraft="F_16C_50", coalition="blue",
                                   slots=1, seed=7, bb_tanker=True)), path)
    with _z.ZipFile(path) as z:
        txt = z.read("l10n/DEFAULT/dictionary").decode("utf-8")
    assert "AIR REFUELLING" in txt, "the procedure card should still be there"
    assert "YOUR HARDWARE" not in txt, \
        "the hardware page leaked onto an ordinary mission with a tanker"


def test_the_ffb_finding_names_the_gap_in_its_own_search():
    """"No evidence" is only as strong as the corpus searched, and ours had a
    hole: Reddit was unreachable from the research environment, so r/hoggit —
    one of the largest DCS venues — was never read.

    The claim is therefore "no evidence in everything we could search", not
    "no evidence anywhere". Stating the boundary is the same discipline as
    `basis` on the tanker table and the magnetic-variation note on the roadmap:
    when the limit is in the method rather than the data, say so, because a
    reader cannot see the method."""
    h = "\n".join(aar.hardware_lines())
    assert "REDDIT" in h, "the unsearched-corpus caveat has gone"
    assert "not 'no evidence anywhere'" in h


# --------------------------------------------------------------------------- #
# Receiver-aware track speed — "the tankers are way too slow for the jets"
# --------------------------------------------------------------------------- #
def test_a_fast_jet_gets_a_faster_track_than_the_tanker_default():
    """The reported bug. Speed used to be a property of the TANKER alone, so a
    Hercules flew 210 KIAS whether a Harrier or a Tomcat was joining."""
    assert aar.TANKERS["kc135mprs"]["ias_kt"] >= 275, \
        "the MPRS is back to a speed a fast jet cannot comfortably fly"
    assert aar.TANKERS["kc130"]["ias_kt"] >= 225


def test_a_slow_aeroplane_slows_the_tanker_down():
    """The other direction, and it is the one people forget: 300 KIAS is a fine
    boom track for a Viper and impossible for a Hog. The real tanker slows."""
    hog = aar.track_ias_kt("kc135", "A-10C_2")
    viper = aar.track_ias_kt("kc135", "F-16C_50")
    assert hog <= 225, hog
    assert viper >= 290, viper


def test_the_track_never_exceeds_what_the_tanker_can_hold():
    """A receiver's floor may raise the track, but not past the airframe. A
    Hercules asked for 300 KIAS is a Hercules that is not there."""
    for k, t in aar.TANKERS.items():
        for r in ("F-4E-45MC", "F-14BU", "FA-18C_hornet", "F-16C_50"):
            assert aar.track_ias_kt(k, r) <= t["max_ias_kt"], (k, r)


def test_a_pairing_that_cannot_reach_the_receivers_speed_says_so():
    """A Tomcat behind a Hercules is 15 kt slow and there is no fixing it. The
    card must say that, or the pilot blames their hands for the airplane."""
    assert aar.shortfall_kt("kc130", "F-14BU") >= aar.SHORTFALL_WARN_KT
    card = "\n".join(aar.brief_lines("kc130", "F-14BU"))
    assert "CANNOT FLY YOUR SPEED" in card
    assert "That is the airplane, not you." in card


def test_an_ordinary_pairing_does_not_cry_wolf():
    """A Hornet off a Hercules is the most ordinary tanking in the Navy. If it
    warns, the warning is noise and the real one gets ignored."""
    assert aar.shortfall_kt("kc130", "FA-18C_hornet") == 0
    card = "\n".join(aar.brief_lines("kc130", "FA-18C_hornet"))
    assert "CANNOT FLY YOUR SPEED" not in card


def test_choose_prefers_a_tanker_that_can_fly_the_receivers_speed():
    """The fix for the report: the probe lane used to hand a Tomcat the
    Hercules because it sorted on altitude."""
    assert aar.shortfall_kt(aar.choose("F-14BU", "modern"), "F-14BU") == 0


def test_ashore_you_do_not_get_the_boats_tanker():
    """An S-3B or a KA-6D belongs to a carrier. Sorting purely on altitude gave
    a land-based Hornet a Viking, because the Viking flies lowest."""
    assert not aar.TANKERS[aar.choose("FA-18C_hornet", "modern")].get("organic")
    assert aar.TANKERS[aar.choose("FA-18C_hornet", "modern",
                                  carrier=True)].get("organic")


# --------------------------------------------------------------------------- #
# Era availability: a RULE, not a hand-applied judgment
# --------------------------------------------------------------------------- #
def test_every_tanker_has_a_service_window():
    """Without one, era availability is somebody's opinion. It was: the S-3B
    (retired 2009) was offered in the modern era and the KA-6D (retired 1997)
    was not, and nothing in the data explained the difference."""
    for k, t in aar.TANKERS.items():
        svc = t.get("service")
        assert svc and len(svc) == 2, f"{k} has no service window"
        assert 1940 < svc[0] < 2030, (k, svc)
        assert svc[1] is None or svc[1] >= svc[0], (k, svc)


def test_the_two_retired_carrier_tankers_are_treated_the_same_way():
    """THE INCONSISTENCY THIS FILE EXISTS TO PIN. Both left service part-way
    through or before the modern era. Either both are offered with a label or
    neither is; what must not happen is one of each with no stated reason."""
    from missiongen.resolver import load_json
    win = load_json("eras")["modern"]["window"]
    for k in ("s3b", "ka6d"):
        assert "modern" in aar.TANKERS[k]["eras"], \
            f"{k} is hidden from modern while the other is offered"
        assert aar.period_note(k, "modern"), \
            f"{k} is offered in modern without saying it left service in " \
            f"{aar.TANKERS[k]['service'][1]}, before {win[1]}"


def test_the_a6e_buddy_tanker_is_available_to_the_navy_in_both_eras():
    """Rob's report. The AI A-6E carries a buddy store and tanks perfectly
    well; it was hidden from the modern era by a bucket boundary."""
    for era in ("coldwar", "modern"):
        assert "ka6d" in aar.tankers_for("F-14BU", era), era
        assert "ka6d" in aar.tankers_for("FA-18C_hornet", era), era


def test_a_tanker_that_covers_a_whole_era_carries_no_period_note():
    """Otherwise every option wears a caveat and the caveats stop meaning
    anything."""
    assert aar.period_note("kc135", "modern") == ""
    assert aar.period_note("kc130", "modern") == ""


def test_an_absence_is_explained_from_the_service_window():
    """A reason written by hand can disagree with the rule beside it. This one
    is derived, so it cannot."""
    why = dict(aar.tankers_excluded_by_era("F-14BU", "gwot"))
    assert "ka6d" in why
    assert "1997" in why["ka6d"] and "2003" in why["ka6d"], why["ka6d"]


# --------------------------------------------------------------------------- #
# The store, the speed and the air start — all three reported from the cockpit
# --------------------------------------------------------------------------- #
def test_the_only_tanker_needing_a_store_declares_one():
    """The A-6E carries a D-704 pod on a pylon; every other tanker in the table
    has a built-in refuelling system. `refuel_flight` fits nothing, so the
    KA-6D shipped with empty pylons — on a track, on frequency, with a TACAN
    and a briefing, and unable to give anybody fuel."""
    assert aar.TANKERS["ka6d"].get("store") == ("Pylon3", "D_704_Refuelling_Pod")
    for k, t in aar.TANKERS.items():
        if k == "ka6d":
            continue
        assert not t.get("store"), f"{k} claims a store it does not need"


def test_the_declared_store_exists_on_the_airframe():
    """Pinned against pydcs, so a pylon rename fails here rather than shipping
    an empty pylon block again."""
    spec = aar.TANKERS["ka6d"]["store"]
    pylon = getattr(aar.TANKERS["ka6d"]["type"], spec[0])
    weapon = getattr(pylon, spec[1])
    assert weapon[0] == 3
    assert "D704" in weapon[1]["clsid"]


def test_the_buddy_tanker_is_fast_enough_for_a_tomcat():
    """Reported twice: at 270 KIAS the KA-6D was "still slow for the F-14 to
    line up with it"."""
    assert aar.shortfall_kt("ka6d", "F-14BU") == 0
    assert aar.track_ias_kt("ka6d", "F-14BU") >= 285


def test_the_tomcats_floor_is_high_enough_to_catch_a_slow_tanker():
    """A floor set below where the airplane is comfortable makes the shortfall
    warning silent exactly when it should be speaking. At a 250 floor the
    Hercules looked acceptable for a Tomcat; it is not."""
    assert aar.RECEIVER_IAS["F-14BU"][0] >= 265
    assert aar.shortfall_kt("kc130", "F-14BU") >= aar.SHORTFALL_WARN_KT


# --------------------------------------------------------------------------- #
# Terrain: a refuelling track you can fly into a mountain is not a training aid
# --------------------------------------------------------------------------- #
def test_the_track_clears_the_maps_highest_ground():
    """Reported from the cockpit: "the altitude seems too low for the terrain".
    It was. Mount Elbrus is 18,510 ft and sits on the FREE Caucasus map; the
    KC-130 and KA-6D flew 15,000 and the S-3B 12,000, with the receiver a
    further 1,000 ft below that."""
    for m in aar.TERRAIN_MAX_FT:
        hi = aar.TERRAIN_MAX_FT[m][0]
        for k in aar.TANKERS:
            if not aar.clears_terrain(k, m):
                continue
            alt = aar.track_alt_ft(k, m)
            assert alt >= hi + aar.TERRAIN_CLEARANCE_FT - 999, (m, k, alt, hi)


def test_the_RECEIVER_clears_it_too_not_just_the_tanker():
    """The pre-contact air start is 1,000 ft BELOW the track. Clearing terrain
    with the tanker and not the pilot is the wrong half of the problem."""
    from missiongen.builder import StarterBuilder
    step = StarterBuilder.ASTERN_TANKER_BELOW_M / 0.3048
    for m in aar.TERRAIN_MAX_FT:
        hi = aar.TERRAIN_MAX_FT[m][0]
        for k in aar.TANKERS:
            if not aar.clears_terrain(k, m):
                continue
            assert aar.track_alt_ft(k, m) - step > hi, (m, k)


def test_caucasus_is_the_case_that_prompted_this():
    """Pinned by name, because it is the FREE map and therefore the one most
    people fly the Academy on."""
    assert aar.TERRAIN_MAX_FT["caucasus"][0] == 18510   # Elbrus, 5,642 m
    for k in aar.TANKERS:
        assert aar.track_alt_ft(k, "caucasus") >= 22000, k


def test_a_tanker_that_cannot_climb_that_high_is_not_offered():
    """A KC-130 asked for a 28,000 ft track over the Hindu Kush is a Hercules
    at an altitude it cannot hold. Not offered, rather than offered broken."""
    assert aar.clears_terrain("kc130", "afghanistan") is False
    assert aar.clears_terrain("kc135", "afghanistan") is True
    assert "kc130" not in aar.tankers_for("FA-18C_hornet", "modern",
                                          map_key="afghanistan")
    assert aar.choose("FA-18C_hornet", "modern", map_key="afghanistan") != "kc130"


def test_every_tanker_declares_a_ceiling():
    for k, t in aar.TANKERS.items():
        assert t.get("max_alt_ft", 0) >= t["alt_ft"], k


def test_an_unknown_map_assumes_the_worst():
    """Failing closed gives an unlisted map an unrealistically high track.
    Failing open gives it one inside a mountain. Those are not comparable."""
    assert aar.terrain_floor_ft("some-map-ed-has-not-made") >= \
        aar.terrain_floor_ft("afghanistan")


def test_the_card_explains_a_raised_track():
    """A pilot briefed 22,000 ft on a card that used to say 15,000 deserves the
    reason, or the number looks arbitrary."""
    card = "\n".join(aar.brief_lines("kc130", "FA-18C_hornet",
                                     map_key="caucasus"))
    assert "TRACK: 230 KIAS at 22,000 ft" in card
    assert "WHY THE TRACK IS HIGH" in card
    assert "18,510 ft" in card


def test_a_low_map_does_not_raise_anything():
    """Otherwise every track everywhere climbs and the rule is just a tax."""
    card = "\n".join(aar.brief_lines("kc130", "FA-18C_hornet",
                                     map_key="marianas"))
    assert "TRACK: 230 KIAS at 15,000 ft" in card
    assert "WHY THE TRACK IS HIGH" not in card


def test_the_printed_guide_prints_the_altitude_the_mission_flies():
    """Both guide builders, both formats, on a map where terrain raises the
    track. The PDF and the markdown are near-identical twins written twice, and
    a number corrected in one and left stale in the other is the exact defect
    class this product exists to eliminate: a brief promising what the mission
    does not contain."""
    import tempfile
    from pathlib import Path
    from pypdf import PdfReader
    from missiongen import aar_guide, tracks

    d = tempfile.mkdtemp()
    t = tracks.get("aar_boom")
    flown = aar.track_alt_ft("kc135", t.get("default_map") or "caucasus")
    assert flown > aar.TANKERS["kc135"]["alt_ft"], (
        "pick a map where terrain actually raises the track, or this proves "
        "nothing")
    want = f"{flown:,} ft"
    stale = f"{aar.TANKERS['kc135']['alt_ft']:,} ft"

    md = Path(aar_guide.markdown("aar_boom", t, "9.9.9", d,
                                 aircraft="F_16C_50", tanker="kc135",
                                 era="modern")).read_text()
    assert f"**300 KIAS at {want}**" in md, md[:400]

    pdf = aar_guide.build("aar_boom", t, "9.9.9", d, aircraft="F_16C_50",
                          tanker="kc135", era="modern")
    txt = "".join(p.extract_text() for p in PdfReader(pdf).pages)
    txt = txt.replace("\n", " ")
    assert want in txt, f"the PDF never prints the flown altitude {want}"
    # The book figure may appear ONCE, in the paragraph that explains why the
    # track is higher than it. It may not appear as the track itself.
    assert f"KIAS, {stale}" not in txt and f"KIAS at {stale}" not in txt, (
        f"the PDF briefs the tanker's book altitude {stale}, not the "
        f"{want} the mission actually flies")


def test_a_tanker_the_terrain_removed_says_so():
    """The KA-6D taught this lesson once already: a tanker that simply vanishes
    reads as a missing feature, and somebody has to ask. Terrain removes
    tankers too, and owes the same sentence."""
    gone = dict(aar.tankers_excluded_by_era("FA-18C_hornet", "modern",
                                            map_key="afghanistan"))
    assert "kc130" in gone, "the Hercules cannot hold that track and vanished"
    why = gone["kc130"]
    assert "24,000" in why and "28,000" in why, why
    assert "kc130" not in dict(
        aar.tankers_excluded_by_era("FA-18C_hornet", "modern",
                                    map_key="caucasus")), \
        "it clears Caucasus, so it must not be listed as removed there"
