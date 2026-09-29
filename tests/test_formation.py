"""Formation training: there has to be somebody to fly formation ON.

The v1.50 version of this module built ONE group and put the AI lead in slot 0
of the player's own flight. Rob's report was blunt — "no planes that are
generated to fly in formation with." The tests below all passed at the time,
because they inspected a single group named "Formation" and asserted its two
units had the right skills. They never asked the question that mattered: is the
thing you fly on an INDEPENDENT aircraft, flying its own route?

So the shape of this file changed with the fix. It now asserts across two
groups, and the properties it guards are:

  * a separate AI lead group exists, at Excellent, with its own scripted route
  * you are a Player/Client and you are NOT in lead's group
  * lead's cruise is scaled to the airframe (the mechanism by which this was
    an "F-16 tool" was 300 kt hard-coded, not the card list)
  * the in-mission coaching is one call per excursion, not one per second
  * the syllabus is five stages (each adding one variable), then a pre-check and a check
"""
import zipfile

import pytest

import dcs.lua as lua
from missiongen import Recipe, formation, generate
from missiongen.recipe import RECIPE_ENUMS
from missiongen.templates import advertised_combinations, effective_recipe

CARDS = [c for c in advertised_combinations() if c[0].startswith("form_")]
AIRFRAMES = ["F_16C_50", "FA_18C_hornet", "F_14B_U", "F_4E_45MC"]

LEAD_NAME = "Formation Lead"
DASH_NAME = "Dash 2"


def _mission(path):
    return lua.loads(zipfile.ZipFile(path).read("mission").decode())["mission"]


def _groups(path):
    """Every plane group in the mission, by name."""
    out = {}
    for coal in _mission(path)["coalition"].values():
        if not isinstance(coal, dict):
            continue
        for c in coal.get("country", {}).values():
            for g in c.get("plane", {}).get("group", {}).values():
                out[g.get("name", "")] = g
    return out


def _units(g):
    return [g["units"][i] for i in sorted(g["units"])]


def _build(tmp_path, **rc):
    base = dict(map="caucasus", era="modern", aircraft="F_16C_50",
                formation="route", mission_kind="training",
                bb_ambient=False, bb_sams=False, player_arm=False, seed=1)
    base.update(rc)
    out = str(tmp_path / "f.miz")
    return generate(Recipe.from_dict(base), out), out


# --------------------------------------------------------------- the syllabus
def test_the_syllabus_is_five_stages_then_a_precheck_and_a_check():
    stages = sorted(p["stage"] for p in formation.PROFILES.values())
    assert stages == [1, 2, 3, 4, 5, 6, 7], f"syllabus stages are {stages}"
    assert set(formation.PROFILES) <= set(RECIPE_ENUMS["formation"])
    taught = [k for k, p in formation.PROFILES.items() if not p.get("check")]
    assert len(taught) == 5
    assert formation.PROFILES["precheck"]["stage"] == 6
    assert formation.PROFILES["check"]["stage"] == 7


def test_route_comes_before_close_formation():
    """The instructional inversion the rebuild fixed. Pilots fly route almost
    all the time and fingertip almost never, so teaching fingertip first starts
    a learner at the highest-workload position they will hardly ever use."""
    assert formation.PROFILES["route"]["stage"] == 1
    assert formation.PROFILES["close"]["stage"] == 2
    assert formation.PROFILES["route"]["start"] == "route"
    assert formation.PROFILES["close"]["start"] == "fingertip"
    r = formation.START_OFFSETS["route"]
    c = formation.START_OFFSETS["fingertip"]
    assert r[0] > c[0] * 3, f"route {r} is no wider than fingertip {c}"


def test_each_stage_adds_exactly_one_variable():
    """The instructional spine. Route is straight and level; close adds
    heading; energy adds altitude and speed. If stage 1 starts turning, the
    foundation sortie stops being a foundation."""
    st = formation.PROFILES["route"]["legs"]
    assert all(dft == 0 and dkt == 0 for _d, _m, dft, dkt in st), \
        f"the route profile changes energy: {st}"
    tn = formation.PROFILES["close"]["legs"]
    assert any(dh for dh, *_r in tn), "the close profile never turns"
    assert all(dft == 0 and dkt == 0 for _d, _m, dft, dkt in tn), \
        "the close profile also changes energy — that is stage 3's job"
    en = formation.PROFILES["energy"]["legs"]
    assert any(dft for _d, _m, dft, _k in en) and any(dkt for *_r, dkt in en)


def test_the_rejoin_starts_you_out_of_position():
    """You cannot practice a rejoin from fingertip."""
    close = formation.START_OFFSETS["fingertip"]
    spread = formation.START_OFFSETS["spread"]
    assert spread[0] > close[0] * 10, f"spread {spread} is not a rejoin start"
    assert formation.PROFILES["rejoin"]["start"] == "spread"


def test_only_the_capstone_starts_on_the_ground():
    ground = {k for k, p in formation.PROFILES.items() if p.get("ground")}
    assert ground == {"takeoff"}, f"ground-start stages are {ground}"


# ------------------------------------------------------- there IS a lead now
@pytest.mark.parametrize("stage", sorted(formation.PROFILES))
def test_there_is_a_separate_ai_lead_to_fly_on(stage, tmp_path):
    """THE regression. Rob flew a formation sortie and found nothing to fly
    formation with, because the 'lead' was slot 0 of his own flight."""
    _res, out = _build(tmp_path, formation=stage)
    gs = _groups(out)
    assert LEAD_NAME in gs, f"{stage}: no separate lead group; groups={list(gs)}"
    assert DASH_NAME in gs, f"{stage}: no player group; groups={list(gs)}"
    assert gs[LEAD_NAME] is not gs[DASH_NAME]

    lead = _units(gs[LEAD_NAME])
    assert len(lead) == 1, f"{stage}: lead is a flight of {len(lead)}"
    assert lead[0].get("skill") == "Excellent", \
        f"{stage}: lead is {lead[0].get('skill')} — a sloppy lead is unflyable"

    me = _units(gs[DASH_NAME])
    assert me[0].get("skill") in ("Player", "Client"), \
        f"{stage}: you are {me[0].get('skill')}, not in the airplane"
    assert all(u.get("skill") != "Excellent" for u in lead[1:])


def test_the_lead_is_not_your_wingman(tmp_path):
    """Same-group is the bug, not a detail. Aircraft in YOUR group sit under
    your F-key command structure — you could order the man you are supposed to
    be learning from to go home."""
    _res, out = _build(tmp_path)
    gs = _groups(out)
    assert all(u.get("skill") not in ("Player", "Client")
               for u in _units(gs[LEAD_NAME])), "the player is inside lead's group"
    assert all(u.get("skill") != "Excellent"
               for u in _units(gs[DASH_NAME])), "lead is inside the player's group"


def test_the_lead_flies_a_scripted_profile(tmp_path):
    """The AI lead has to be predictable, and it has to have somewhere to go."""
    _res, out = _build(tmp_path, formation="close")
    pts = _groups(out)[LEAD_NAME].get("route", {}).get("points", {})
    assert len(pts) >= 5, f"the lead flies only {len(pts)} waypoints"


def test_you_get_a_flight_plan_too(tmp_path):
    """Both start types. A player left on one orphan waypoint has nothing on
    the F10 map to navigate by when he loses lead — which he will."""
    for stage in ("route", "takeoff"):
        _res, out = _build(tmp_path, formation=stage)
        pts = _groups(out)[DASH_NAME].get("route", {}).get("points", {})
        assert len(pts) >= 2, f"{stage}: your flight plan is {len(pts)} points"


def test_the_capstone_starts_both_of_you_on_the_ramp(tmp_path):
    res, out = _build(tmp_path, formation="takeoff")
    assert res["stats"].get("formation_ground_start") is True
    gs = _groups(out)
    for name in (LEAD_NAME, DASH_NAME):
        p0 = gs[name]["route"]["points"][1]
        assert p0.get("type") == "TakeOffParking" or "airdrome" in str(p0).lower() \
            or p0.get("airdromeId"), f"{name} is not on an airfield: {p0.get('type')}"
    for stage in ("route", "close", "energy", "rejoin"):
        res, _o = _build(tmp_path, formation=stage)
        assert res["stats"].get("formation_ground_start") is False, \
            f"{stage} should be an air start"


# ------------------------------------------------- not an F-16 tool any more
def test_lead_cruises_at_a_speed_your_aeroplane_can_actually_fly():
    """The real mechanism behind 'it shouldn't just be an F-16 tool'. A fixed
    300 kt lead is unflyable in a Yak-52, which tops out around 145."""
    import dcs.planes as P
    fast = formation.cruise_for(P.F_16C_50)
    slow = formation.cruise_for(P.Yak_52)
    prop = formation.cruise_for(P.P_51D)
    assert fast[1] > prop[1] > slow[1], f"{fast} {prop} {slow} are not ordered"
    assert slow[1] <= 145, f"a Yak-52 cannot hold {slow[1]} kt"
    assert 250 <= fast[1] <= 350, f"{fast[1]} kt is not a fast-jet cruise"
    assert slow[0] < fast[0], "a piston trainer is briefed to a jet's block"


def test_cruise_survives_an_airframe_with_no_speed_data():
    class Mystery:
        pass
    alt, kt = formation.cruise_for(Mystery)
    assert 120 <= kt <= 320 and alt > 0


def test_the_slow_end_is_not_sped_up_by_a_leg_floor(tmp_path):
    """The energy sortie asks lead to slow down. An absolute floor would have
    silently pushed a piston trainer back ABOVE its own briefed cruise."""
    import dcs.planes as P
    _alt, kt = formation.cruise_for(P.Yak_52)
    res, _out = _build(tmp_path, aircraft="Yak_52", formation="energy")
    assert res["stats"]["lead_speed_kt"] == kt


@pytest.mark.parametrize("ac,era", [
    ("P_51D", "wwii"), ("SpitfireLFMkIX", "wwii"),
    ("F_86F_Sabre", "coldwar"), ("MiG_21Bis", "coldwar"),
    ("L_39C", "modern"), ("A_10C_2", "modern"), ("M_2000C", "modern"),
])
def test_the_syllabus_builds_in_anything_it_advertises(ac, era, tmp_path):
    mp = "normandy" if era == "wwii" else "caucasus"
    for stage in ("route", "takeoff"):
        res, out = _build(tmp_path, aircraft=ac, era=era, map=mp,
                          formation=stage)
        gs = _groups(out)
        assert LEAD_NAME in gs and DASH_NAME in gs, \
            f"{ac}/{era}/{stage}: {list(gs)}"
        # The BUILD has to use the scaled cruise, not just expose a function
        # that computes it. Testing cruise_for() alone would let a hard-coded
        # 300 kt back into build() unnoticed.
        import dcs.planes as P
        want = formation.cruise_for(getattr(P, ac))
        assert (res["stats"]["lead_alt_ft"],
                res["stats"]["lead_speed_kt"]) == want, \
            f"{ac}: lead briefed {res['stats']['lead_speed_kt']} kt, want {want}"


@pytest.mark.parametrize("era", ["coldwar", "modern"])
@pytest.mark.parametrize("stage", sorted(formation.PROFILES))
def test_the_tomcat_upgrade_flies_the_syllabus(stage, era, tmp_path):
    """The F-14B(U) is the one airframe on the offer list that pydcs has no
    native class for — it is registered at runtime from `pending_aircraft.json`,
    inheriting F-14B flight data. Anything that reaches for `dcs.planes.<key>`
    silently loses it, which is exactly how it derived an empty loadout back in
    v1.48.0. Rob asked for it here by name, so it gets its own guard rather
    than riding along on the generic card test."""
    res, out = _build(tmp_path, aircraft="F_14B_U", era=era, formation=stage)
    gs = _groups(out)
    assert LEAD_NAME in gs, f"F-14B(U)/{era}/{stage}: nothing to fly on"
    from missiongen.pending import get_pending
    cls = get_pending("F_14B_U")[0]
    for name in (LEAD_NAME, DASH_NAME):
        types = {u.get("type") for u in _units(gs[name])}
        assert types == {cls.id}, f"{name} is a {types}, not a {cls.id}"
    # Pinned to the F-14B it inherits from, NOT to cruise_for(cls) — comparing
    # the build against the same function it calls is a tautology that passes
    # even when the function has lost the runtime class and fallen back to its
    # default. It must land on Tomcat numbers, not on "some number".
    import dcs.planes as P
    assert (res["stats"]["lead_alt_ft"], res["stats"]["lead_speed_kt"]) \
        == formation.cruise_for(P.F_14B), \
        "the runtime class lost its inherited speed data"


def test_the_tomcat_upgrade_is_on_the_offer_list():
    from missiongen.resolver import load_json
    for key, tpl in load_json("mission_templates").items():
        if not key.startswith("form_"):
            continue
        ch = tpl["aircraft_choices"]
        for era in ("coldwar", "modern"):
            assert "F_14B_U" in ch[era], f"{key}/{era} does not offer the F-14B(U)"
        assert "F_14B_U" not in ch["wwii"], "a Tomcat in 1944"


def test_every_offered_aircraft_is_real_and_era_legal():
    """The card list is DATA, so a typo is invisible until somebody clicks it."""
    import json
    import dcs.planes as planes
    from missiongen.resolver import load_json
    tpls = load_json("mission_templates")
    svc = load_json("aircraft_service")
    # Read the windows rather than restate them. This dict used to be a
    # verbatim copy of eras.json and would have failed the moment a fourth era
    # landed — a test that breaks on correct data is a test that gets deleted.
    windows = {k: tuple(v["window"]) for k, v in load_json("eras").items()}
    from missiongen.pending import pending_aircraft
    pend = pending_aircraft()
    seen = 0
    for key, tpl in tpls.items():
        if not isinstance(tpl, dict):      # "_comment" is a string
            continue
        for era, keys in (tpl.get("aircraft_choices") or {}).items():
            assert era in windows, f"{key}: unknown era {era!r}"
            lo, hi = windows[era]
            for ac in keys:
                seen += 1
                assert hasattr(planes, ac) or ac in pend, \
                    f"{key}/{era}: {ac} is not an aircraft"
                s = svc.get(ac)
                assert s, f"{key}/{era}: {ac} has no service window"
                assert s[0] <= hi and (s[1] or 2100) >= lo, \
                    f"{key}/{era}: {ac} served {s}, outside {lo}-{hi}"
    assert seen > 20, f"only {seen} offered airframes — the data did not load"


def test_the_offer_is_not_one_airframe_wide():
    """Rob's actual complaint, as an assertion."""
    from missiongen.resolver import load_json
    for key, tpl in load_json("mission_templates").items():
        if not key.startswith("form_"):
            continue
        ch = tpl.get("aircraft_choices") or {}
        # Every era the card ADVERTISES must offer a real choice — checked
        # against the card's own `eras`, not against a hard-coded list of all
        # the eras that exist. Formation training is deliberately not offered
        # in every era; the guard is "no card advertises an era it can't fly".
        assert set(ch) == set(tpl.get("eras") or []), f"{key}: eras {set(ch)}"
        for era, keys in ch.items():
            assert len(keys) >= 5, f"{key}/{era}: only {len(keys)} aircraft"
        allkeys = {a for v in ch.values() for a in v}
        assert len(allkeys) >= 15, f"{key}: {len(allkeys)} distinct airframes"


# -------------------------------------------------------------- the coaching
def _trigrules(path):
    return _mission(path).get("trigrules", {}) or {}


def test_lead_calls_you_when_you_drift_out(tmp_path):
    """A PDF is not an instructor. A learner alone has no way to know whether
    he is ten feet out or forty."""
    _res, out = _build(tmp_path)
    rules = list(_trigrules(out).values())
    preds = {r["rules"][i]["predicate"]
             for r in rules for i in sorted(r.get("rules", {}))}
    assert "c_unit_out_zone_unit" in preds, "nothing watches your position"
    assert "c_unit_in_zone_unit" in preds, "nothing tells you when you fix it"
    msgs = [a for r in rules for a in r.get("actions", {}).values()
            if a.get("predicate", "").startswith("a_out_text")]
    assert len(msgs) >= 3, f"only {len(msgs)} radio calls in the whole sortie"


def test_the_zone_is_locked_to_lead_not_to_the_ground(tmp_path):
    """A static zone would grade you on where you are over the map. The whole
    question is where you are relative to LEAD, who is moving."""
    _res, out = _build(tmp_path)
    gs = _groups(out)
    lead_uid = _units(gs[LEAD_NAME])[0]["unitId"]
    me_uid = _units(gs[DASH_NAME])[0]["unitId"]
    zoned = [r for rr in _trigrules(out).values()
             for r in rr.get("rules", {}).values()
             if r.get("predicate", "").startswith("c_unit_")
             and "zone_unit" in r.get("predicate", "")]
    assert zoned, "no moving-zone conditions at all"
    for r in zoned:
        assert r["zoneunit"] == lead_uid, "the zone is not centered on lead"
        assert r["unit"] == me_uid, "the zone is not watching YOU"


def test_the_instructor_does_not_nag(tmp_path):
    """A continuous trigger fires every second its condition holds. Without a
    flag guard, drifting out of position means being shouted at once a second
    for as long as you are out — which is exactly how you teach somebody to
    ignore the instructor. The flag makes it one call per excursion."""
    _res, out = _build(tmp_path)
    rules = list(_trigrules(out).values())
    coached = [r for r in rules
               if any("zone_unit" in c.get("predicate", "")
                      for c in r.get("rules", {}).values())]
    assert coached, "no coaching triggers"
    for r in coached:
        preds = [c["predicate"] for c in r["rules"].values()]
        assert any(p in ("c_flag_is_true", "c_flag_is_false") for p in preds), \
            f"{r.get('comment')} has no flag guard — it will fire every second"
        acts = [a["predicate"] for a in r["actions"].values()]
        assert any(a in ("a_set_flag", "a_clear_flag") for a in acts), \
            f"{r.get('comment')} never flips the flag, so it fires forever"


def test_the_two_calls_use_opposite_flag_states(tmp_path):
    """Set-and-never-clear is the silent failure: you would be told once, ever,
    and then coached at for the rest of your flying life by nothing at all."""
    _res, out = _build(tmp_path)
    states = {}
    for r in _trigrules(out).values():
        cond = {c["predicate"] for c in r.get("rules", {}).values()}
        acts = {a["predicate"] for a in r.get("actions", {}).values()}
        if "c_unit_out_zone_unit" in cond:
            states["out"] = ("c_flag_is_false" in cond, "a_set_flag" in acts)
        if "c_unit_in_zone_unit" in cond:
            states["in"] = ("c_flag_is_true" in cond, "a_clear_flag" in acts)
    assert states.get("out") == (True, True), f"drift call: {states.get('out')}"
    assert states.get("in") == (True, True), f"recovery call: {states.get('in')}"


def test_the_recovery_zone_is_tighter_than_the_drift_zone(tmp_path):
    """Deadband, generalized for the position ladder (v1.104.0).

    The old form — one drift call, one recovery call, recovery radius tighter
    than drift — is gone with the drift calls (v1.104.1). What replaced it is a
    ladder of nested bands: every rung that both enters and leaves a zone is a
    BAND (out-radius strictly inside in-radius), and the rung radii nest
    strictly, so a wingman is in exactly one band and a boundary is never a
    place two rungs argue over.

    The patient lead's hold uses one radius for settling and for losing it,
    and that is fine: those two transitions only set and clear a flag that a
    15-second timer consumes. Nothing is SAID on that boundary, so there is
    nothing to ping-pong."""
    _res, out = _build(tmp_path)
    bands, radii, hold_pairs = {}, set(), {}
    for r in _trigrules(out).values():
        cm = r.get("comment", "")
        for c in r.get("rules", {}).values():
            p = c.get("predicate", "")
            if p not in ("c_unit_in_zone_unit", "c_unit_out_zone_unit"):
                continue
            key = "in" if p == "c_unit_in_zone_unit" else "out"
            if cm.startswith("Formation ladder"):
                bands.setdefault(cm, {})[key] = c["zone"]
                radii.add(round(c["zone"]))
            elif cm.startswith("Formation hold"):
                hold_pairs.setdefault(cm.rsplit(":", 1)[0], {})[key] = c["zone"]
    assert bands, "the ladder draws no zones at all"
    for cm, z in bands.items():
        if "in" in z and "out" in z:
            assert z["out"] < z["in"], f"{cm}: not a band {z}"
    assert len(radii) >= 3 and sorted(radii) == sorted(set(radii)), radii
    # the hold: equal radii, and the only actions on that boundary are a flag
    # set and a flag clear — no message, no picture
    for cm, z in hold_pairs.items():
        assert z.get("in") == z.get("out"), (cm, z)
    for r in _trigrules(out).values():
        cm = r.get("comment", "")
        if cm.startswith("Formation hold") and (cm.endswith("settling") or cm.endswith("lost it")):
            kinds = {a.get("predicate") for a in r.get("actions", {}).values()}
            assert kinds <= {"a_set_flag", "a_clear_flag"}, (cm, kinds)


def test_coaching_failure_never_fails_the_build(tmp_path, monkeypatch):
    """pydcs is vendored and moves. A trigger API change must cost the coaching
    calls, not the mission."""
    def boom(*a, **k):
        raise RuntimeError("pydcs moved")
    monkeypatch.setattr("dcs.triggers.TriggerOnce", boom)
    res, out = _build(tmp_path)
    assert LEAD_NAME in _groups(out), "losing the coaching lost the lead"
    assert any("coaching" in w for w in res["warnings"]), \
        "the coaching vanished silently"


# ------------------------------------------------------------------- cards
def test_the_cards_are_advertised():
    assert len(CARDS) == 21, f"expected 7 cards x 3 eras, got {len(CARDS)}"


@pytest.mark.parametrize("key,era", CARDS, ids=[f"{k}/{e}" for k, e in CARDS])
def test_every_card_builds_and_seats_you_as_dash_two(key, era, tmp_path):
    rc = effective_recipe(key, era)
    rc.update(seed=1, bb_ambient=False)
    out = str(tmp_path / f"{key}_{era}.miz")
    generate(Recipe.from_dict(rc), out)
    gs = _groups(out)
    assert LEAD_NAME in gs, f"{key}/{era}: nothing to fly formation with"
    assert _units(gs[LEAD_NAME])[0].get("skill") == "Excellent"
    assert _units(gs[DASH_NAME])[0].get("skill") in ("Player", "Client"), \
        f"{key}/{era}: YOU are not in the airplane"


def test_a_formation_sortie_is_not_a_combat_mission():
    """No threats, no tasking, and a clean jet. A learner holding position does
    not need a SAM ring, and being shot at while task-saturated teaches
    nothing."""
    for key, era in CARDS:
        rc = effective_recipe(key, era)
        assert rc.get("bb_sams") is False, f"{key}: air defenses are on"
        assert rc.get("threat_intensity") == 1, f"{key}: threat dial is up"
        assert rc.get("player_arm") is False, f"{key}: the jet is armed"
        assert rc.get("bb_bfm") is False, f"{key}: a BFM bandit is on the card"


def test_the_card_default_is_legal_for_its_era():
    """by_era exists because a card that spans eras cannot pin one jet."""
    for key, era in CARDS:
        rc = effective_recipe(key, era)
        choices = ((__import__("missiongen.resolver", fromlist=["load_json"])
                    .load_json("mission_templates")[key]
                    .get("aircraft_choices") or {}).get(era) or [])
        assert rc["aircraft"] in choices, \
            f"{key}/{era}: default {rc['aircraft']} is not on its own offer list"


# ------------------------------------------------------------------- briefs
@pytest.mark.parametrize("ac", AIRFRAMES)
def test_the_sight_picture_follows_the_aircraft(ac, tmp_path):
    """A Phantom wingman and a Viper wingman look at completely different
    things, so a generic instruction sheet would be nearly useless."""
    era = "coldwar" if ac == "F_4E_45MC" else "modern"
    res, _out = _build(tmp_path, aircraft=ac, era=era)
    from missiongen.threats import resolve_plane
    try:
        tid = resolve_plane(ac).id
    except Exception:
        from missiongen.pending import get_pending
        tid = get_pending(ac)[0].id
    sp = formation.sight_picture(tid)
    assert sp and "No airframe-specific" not in (sp.get("note") or ""), \
        f"{ac} ({tid}) has no authored sight picture"
    for axis in ("bearing", "lateral", "vertical"):
        assert len(sp.get(axis, "")) > 40, f"{ac}: {axis} reference is a stub"


def test_an_unlisted_airframe_still_gets_usable_instruction():
    """Degrade, never blank. Someone will fly this in a Spitfire."""
    sp = formation.sight_picture("SpitfireLFMkIX")
    assert sp and sp.get("bearing"), "no fallback sight picture at all"
    assert "No airframe-specific" in sp["note"], \
        "the fallback pretends to be airframe-specific"


@pytest.mark.parametrize("stage", sorted(formation.PROFILES))
def test_the_brief_teaches_something_specific_per_stage(stage):
    lines = formation.brief_lines(stage, "F-16C_50")
    text = "\n".join(lines)
    assert formation.PROFILES[stage]["label"].upper() in text
    assert "THROTTLE" in text, "the brief never says what controls fore/aft"
    assert "STANDARD" in text, "no performance standard to self-assess against"
    assert "IF IT IS GOING WRONG" in text, "no error diagnostics"
    teaches = formation.PROFILES[stage]["teaches"]
    assert teaches in text, f"stage {stage} never states what it teaches"


def test_the_setting_survives_a_share_link():
    from missiongen.share import decode_recipe, encode_recipe
    rc = Recipe.from_dict(dict(map="caucasus", era="modern",
                               aircraft="F_16C_50", formation="rejoin"))
    assert decode_recipe(encode_recipe(rc)).formation == "rejoin"


def test_a_bad_stage_name_is_a_clean_error_not_a_crash():
    """RECIPE_ENUMS['formation'] contains None, and the rejection path joins
    the tuple into a message. That crashed with a TypeError — a 500 where the
    user should have got 'that is not a stage'."""
    from missiongen.recipe import RecipeError
    with pytest.raises(RecipeError) as e:
        Recipe.from_dict(dict(map="caucasus", era="modern",
                              aircraft="F_16C_50", formation="banana"))
    assert "formation" in str(e.value)


def test_an_ordinary_mission_still_makes_you_lead(tmp_path):
    """The other direction: this must not leak into every other mission."""
    out = str(tmp_path / "n.miz")
    generate(Recipe.from_dict(dict(
        map="caucasus", era="modern", aircraft="F_16C_50",
        bb_ambient=False, seed=1)), out)
    gs = _groups(out)
    assert LEAD_NAME not in gs, "a normal mission grew a formation lead"
    for g in gs.values():
        units = _units(g)
        if any(u.get("skill") in ("Player", "Client") for u in units):
            assert units[0].get("skill") in ("Player", "Client"), \
                "a normal mission seated the player as a wingman"
            return
    pytest.fail("no player flight found")
