"""The Academy wizard: pick era, aircraft and tanker, get that series.

THE DEFECT CLASS THIS FILE EXISTS FOR is a picker that offers a combination
which then does not build — the worst kind, because the user did exactly what
the interface told them to.

The second is subtler and has already bitten `missiongen/aar.py` twice: the
product carries TWO identifier namespaces for the same airplane. Recipes and
the wizard use the ROSTER KEY (`F_16C_50`); `aar.AAR_RECEIVERS`,
`aar.brief_lines` and every DCS mission file use the TYPE ID (`F-16C_50`).
Mixing them does not raise — it silently returns "cannot refuel" for every
boom receiver, or prints the probe card to a Viper.
"""
import io
import zipfile

import pytest

from missiongen import aar, tracks
from missiongen.recipe import Recipe
from missiongen import generate
from missiongen.templates import effective_recipe
from missiongen.resolver import load_json


# --------------------------------------------------------------------------- #
# 1. Who can actually take fuel — the allow-list that replaced a deny-list
# --------------------------------------------------------------------------- #
def test_the_receiver_list_fails_closed():
    """It used to be a deny-list of type ids that had drifted from the roster,
    so `can_refuel` returned True for a Mustang, a Huey and a Ka-50. Unknown
    must now mean NO."""
    assert aar.can_refuel("Something ED Has Not Made Yet") is False
    assert aar.can_refuel("") is False


@pytest.mark.parametrize("type_id", [
    "P-51D-30-NA", "SpitfireLFMkIXCW", "P-47D-40", "MosquitoFBMkVI", "I-16",
    "La-7",                                    # warbirds: no AAR anywhere
    "UH-1H", "Mi-8MT", "Mi-24P", "Ka-50", "SA342M", "OH58D", "AH-64D_BLK_II",
    "CH-47Fbl1",                               # helicopters: none in DCS
    "F-5E-3", "F-86F_FC", "MiG-15bis_FC", "L-39ZA", "C-101CC", "Hawk",
    "MB-339APAN",                              # trainers/light jets: no probe
])
def test_aircraft_that_cannot_refuel_are_refused(type_id):
    """Each of these returned True under the old deny-list because its exact
    id was never in it. A tanker on station for a Huey is the same class of
    lie as a 9-line with no controller."""
    assert aar.can_refuel(type_id) is False, f"{type_id} would get a tanker"
    assert aar.lane_of(type_id) is None


@pytest.mark.parametrize("type_id,lane", [
    ("F-16C_50", "boom"), ("F-4E-45MC", "boom"), ("A-10C_2", "boom"),
    ("F-15ESE", "boom"),
    ("FA-18C_hornet", "probe"), ("F-14BU", "probe"), ("F-14B", "probe"),
    ("AV8BNA", "probe"), ("Su-33", "probe"),
])
def test_the_aircraft_we_do_support_are_on_the_right_lane(type_id, lane):
    assert aar.lane_of(type_id) == lane


def test_boom_receivers_is_still_derivable_for_old_call_sites():
    assert "F-16C_50" in aar.BOOM_RECEIVERS
    assert "FA-18C_hornet" not in aar.BOOM_RECEIVERS


def test_a_boom_tanker_will_not_fuel_a_probe_receiver():
    assert aar.compatible("kc135", "FA-18C_hornet") is False
    assert aar.compatible("kc130", "F-16C_50") is False
    assert aar.compatible("kc135", "F-4E-45MC") is True
    assert aar.compatible("kc130", "F-14BU") is True


# --------------------------------------------------------------------------- #
# 2. The two identifier namespaces
# --------------------------------------------------------------------------- #
def test_the_roster_mapping_matches_what_the_options_endpoint_publishes():
    """`tracks._flyable_keyed()` reassembles the roster from pydcs plus the
    pending modules. If it drifts from `flyable_aircraft()` the wizard starts
    offering aircraft the Builder does not have, or — as it did on first run —
    silently drops the F-14B(U), which is a pending module and therefore has
    no pydcs class to resolve."""
    from server.app import flyable_aircraft
    published = {a["key"]: a["id"] for a in flyable_aircraft()
                 if not a.get("upcoming")}
    ours = tracks._flyable_keyed()
    missing = {k: v for k, v in published.items() if k not in ours}
    assert not missing, f"the wizard cannot see these flyable aircraft: {missing}"


def test_the_f14bu_is_reachable_even_though_pydcs_has_no_class_for_it():
    """The exact regression: `resolve("planes.F_14B_U")` raises, so a mapping
    built only from the resolver drops it."""
    assert tracks._flyable_keyed().get("F_14B_U") == "F-14BU"


def test_every_pending_module_is_keyed_by_the_id_that_reaches_the_miz():
    """THE THREE-SPELLING TRAP, pinned. The F-14B(U) is `F_14B_U` in a recipe,
    `F-14B(U)` on a Library card, and `F-14BU` in the mission file. Only the
    third ever reaches `can_refuel`, and keying AAR_RECEIVERS on the second
    produced a syllabus the wizard offered and the engine then built with no
    tanker in it."""
    from missiongen.pending import pending_aircraft
    keyed = tracks._flyable_keyed()
    for key, cfg in pending_aircraft().items():
        if not cfg.get("verified"):
            continue
        assert keyed[key] == cfg["provisional_id"], (
            f"{key} is mapped to {keyed[key]!r}; the mission file will say "
            f"{cfg['provisional_id']!r}")
        assert cfg["label"] not in aar.AAR_RECEIVERS, (
            f"AAR_RECEIVERS is keyed on {cfg['label']!r}, the DISPLAY LABEL. "
            f"It must be keyed on {cfg['provisional_id']!r}.")


def test_a_roster_key_is_not_accepted_where_a_type_id_belongs():
    """Not a wish — a guard. If someone "fixes" AAR_RECEIVERS by adding roster
    keys alongside type ids, this fails and says why."""
    assert aar.lane_of("F_16C_50") is None, \
        "AAR_RECEIVERS has grown roster keys; it is keyed by DCS type id"
    assert aar.lane_of("F-16C_50") == "boom"


# --------------------------------------------------------------------------- #
# 3. The picker tree: everything offered must build
# --------------------------------------------------------------------------- #
# AAR lanes only — see the note in tests/test_aar_academy.py. The wizard this
# file tests is the era/aircraft/TANKER picker, and a track with no refuelling
# lane has no tanker to pick.
ALL_TRACKS = sorted(t for t in tracks.all_tracks()
                    if (tracks.get(t) or {}).get("lane") in ("boom", "probe"))
assert len(ALL_TRACKS) >= 2, ALL_TRACKS
COMBOS = [(t, e, a, k)
          for t in ALL_TRACKS
          for e, acs in tracks.picker(t).items()
          for a, tks in acs.items()
          for k in tks]


def test_the_picker_offers_something_at_all():
    assert len(COMBOS) >= 20, COMBOS


@pytest.mark.parametrize("tid", ALL_TRACKS)
def test_the_picker_only_offers_eras_the_tracks_map_can_build(tid):
    """Caucasus is free and has no War-on-Terror preset, and the Academy's
    promise is that the only thing you must own is the receiver. Offering an
    era that forces a paid map — or worse, an EraViolation — breaks both."""
    mp = load_json("maps")[tracks.get(tid)["default_map"]]
    for era in tracks.picker(tid):
        assert era in mp["presets"], \
            f"{tid} offers {era}, which {tracks.get(tid)['default_map']} cannot build"


@pytest.mark.parametrize("tid,era,ac,tk", COMBOS)
def test_every_offered_combination_is_actually_compatible(tid, era, ac, tk):
    keyed = tracks._flyable_keyed()
    lane = tracks.get(tid)["lane"]
    assert aar.lane_of(keyed[ac]) == lane
    assert aar.compatible(tk, keyed[ac])
    assert era in aar.TANKERS[tk]["eras"]


@pytest.mark.parametrize("tid,era,ac,tk", COMBOS)
def test_every_offered_aircraft_was_in_service_in_that_era(tid, era, ac, tk):
    svc = load_json("aircraft_service").get(ac)
    win = load_json("eras")[era].get("window")
    if not svc or not win:
        pytest.skip("no service window recorded")
    frm, to = svc
    assert frm <= win[1] and (to is None or to >= win[0]), \
        f"{ac} ({svc}) is not plausible in {era} ({win})"


def test_the_two_aircraft_rob_asked_for_are_offered():
    """The F-4E in the boom lane and the F-14B(U) in the probe lane, both in
    the Cold War, which is the whole reason this wizard exists."""
    assert "F_4E_45MC" in tracks.picker("aar_boom")["coldwar"]
    assert "F_14B_U" in tracks.picker("aar_probe")["coldwar"]
    assert "F_14B_U" in tracks.picker("aar_probe")["modern"]


def test_an_aircraft_that_did_not_exist_yet_is_not_offered():
    """The F-16C entered service in 1991; the Cold War era window ends 1985.
    If this ever passes, the service gate is not running."""
    assert "F_16C_50" not in tracks.picker("aar_boom")["coldwar"]
    assert "F_16C_50" in tracks.picker("aar_boom")["modern"]


# --------------------------------------------------------------------------- #
# 4. resolve_choice: fills gaps, refuses nonsense, explains itself
# --------------------------------------------------------------------------- #
def test_no_selection_falls_back_to_the_tracks_own_defaults():
    assert tracks.resolve_choice("aar_boom") == ("modern", "F_16C_50", "kc135")
    # kc135mprs, not kc130: the probe lane's default tanker changed when the
    # Hercules turned out to be 15 kt slower than a Tomcat wants.
    assert tracks.resolve_choice("aar_probe") == ("modern", "FA_18C_hornet",
                                                  "kc135mprs")


def test_choosing_only_an_era_picks_a_legal_aircraft_and_tanker():
    era, ac, tk = tracks.resolve_choice("aar_boom", era="coldwar")
    assert era == "coldwar"
    assert ac in tracks.picker("aar_boom")["coldwar"]
    assert tk in tracks.picker("aar_boom")["coldwar"][ac]


def test_choosing_an_aircraft_picks_a_tanker_that_will_fuel_it():
    era, ac, tk = tracks.resolve_choice("aar_probe", "coldwar", "F_14B_U")
    assert (era, ac) == ("coldwar", "F_14B_U")
    assert aar.compatible(tk, "F-14BU")


@pytest.mark.parametrize("args,expect", [
    (("aar_boom", "coldwar", "F_16C_50", None), "not in service"),
    (("aar_boom", "modern", "FA_18C_hornet", None), "refuel"),
    (("aar_probe", "modern", "F_14B_U", "kc135"), "cannot refuel"),
    (("aar_boom", "wwii", None, None), "no aircraft"),
])
def test_an_impossible_selection_is_refused_with_a_reason(args, expect):
    with pytest.raises(ValueError) as e:
        tracks.resolve_choice(*args)
    msg = str(e.value).lower()
    assert any(w in msg for w in expect.lower().split()), msg
    # and the message must tell the pilot what they CAN have
    assert "available" in msg


# --------------------------------------------------------------------------- #
# 5. The cards agree with the picker
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("tid", ALL_TRACKS)
def test_every_ride_advertises_exactly_the_eras_the_picker_offers(tid):
    """`eras` gates the ENGINE, not just the UI. A card advertising Cold War
    while its recipe pins an F-16C hands the builder an EraViolation, which is
    how a card looks broken. Baked into the data by
    scripts/add_aar_academy.py; pinned here so the two cannot drift."""
    offered = set(tracks.picker(tid))
    for n, k, v in tracks.rides(tid):
        assert offered <= set(v["eras"]), \
            f"{k} does not offer {offered - set(v['eras'])}, which the wizard does"


@pytest.mark.parametrize("tid", ALL_TRACKS)
def test_every_rides_per_era_default_is_legal_in_that_era(tid):
    for n, k, v in tracks.rides(tid):
        for era in v["eras"]:
            rc = effective_recipe(k, era)
            ac, tk = rc.get("aircraft"), rc.get("tanker_type")
            assert ac in tracks.picker(tid).get(era, {}), \
                f"{k} defaults to {ac} in {era}, which the wizard will not offer"
            assert tk in tracks.picker(tid)[era][ac], \
                f"{k} defaults to tanker {tk} for {ac} in {era} — incompatible"


def test_the_carrier_organic_card_kept_its_own_tanker():
    """`aar_boat` is the air-wing-tanks-itself card. Widening its eras must not
    replace the S-3B with the lane default — the organic tanker IS the card.
    This exact regression happened once."""
    assert effective_recipe("aar_boat", "modern")["tanker_type"] == "s3b"
    assert effective_recipe("aar_boat", "coldwar")["tanker_type"] == "ka6d"


# --------------------------------------------------------------------------- #
# 6. The API
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from server.app import app
    return TestClient(app)


def test_options_ships_the_picker_tree_and_the_tanker_labels(client):
    o = client.get("/api/options").json()
    for tid in ALL_TRACKS:
        tr = o["tracks"][tid]
        assert tr["picker"], tid
        for era, acs in tr["picker"].items():
            for ac, tks in acs.items():
                for tk in tks:
                    assert tk in o["tankers"], f"{tk} has no label to show"
    assert o["tankers"]["kc135"]["boom"] is True
    assert o["tankers"]["kc130"]["boom"] is False


def test_an_impossible_selection_is_a_400_with_the_reason(client):
    """MOVED, NOT LOST. The selection used to be validated by the whole-track
    zip builder; that builder is gone, because building eleven missions inside
    a request is what took the server down. The wizard still picks a
    combination and the GUIDE is still generated for it, so that is where the
    contract lives now."""
    r = client.get("/api/track/aar_boom/guide.pdf",
                   params={"era": "coldwar", "aircraft": "F_16C_50"})
    assert r.status_code == 400
    assert "F_16C_50" in r.json()["detail"]


def test_the_guide_is_generated_for_the_chosen_aircraft(client):
    """Not the committed default. A guide showing an F-16C sight picture to
    somebody flying the syllabus in a Phantom is the say/do gap."""
    a = client.get("/api/track/aar_boom/guide.pdf",
                   params={"era": "coldwar", "aircraft": "F_4E_45MC"})
    b = client.get("/api/track/aar_boom/guide.pdf")
    assert a.status_code == b.status_code == 200
    assert a.content[:4] == b"%PDF"
    assert a.content != b.content, "the wizard's guide is the default guide"


def test_the_wizard_still_configures_the_rides_it_advertises(client):
    """THE PROMISE THE WIZARD ACTUALLY MAKES, after the whole-track zip stopped
    being built on demand.

    A pilot who picks a Tomcat and a KA-6D must get a Tomcat and a KA-6D. That
    was previously proved through the eleven-mission zip; it is now proved
    through the ride he actually downloads, which is the same generator and one
    mission per request instead of eleven.

    Reads the TYPE ID out of the mission file — "F-14BU", not the roster key
    "F_14B_U" and not the display label. Asserting on the label is what let the
    first version of this pass while the mission contained no tanker at all.
    """
    from missiongen.templates import effective_recipe
    from missiongen import tracks
    # A ride that ACTUALLY HAS A TANKER. Picking one by index is how a guard
    # ends up asserting a tanker against a formation ride that never had one —
    # which looks like a broken feature and is a broken test.
    pick = None
    for n, key, _card in tracks.rides("aar_probe"):
        rc = effective_recipe(key, "coldwar", "")
        if rc.get("bb_tanker"):
            pick = (n, key, rc)
            break
    assert pick, "no probe ride carries a tanker — the guard is vacuous"
    n, key, rc = pick
    rc.update(template=key, aircraft="F_14B_U", tanker_type="ka6d",
              seed=4400 + n)
    r = client.post("/api/generate", json={"recipe": rc})
    assert r.status_code == 200, r.text[:300]
    inner = zipfile.ZipFile(io.BytesIO(r.content))
    txt = inner.read("mission").decode("utf-8", "replace")
    assert "F-14BU" in txt, "the chosen aircraft is not in the mission"
    # ...and the TANKER'S type id, which is "A-6E" — the KA-6D is an A-6E
    # airframe, so neither the roster key "ka6d" nor the label "KA-6D" appears
    # anywhere in the file. Asserting on either of those is the exact mistake
    # this test's own docstring warns about, and it caught me writing it.
    from missiongen import aar as _aar
    tanker_id = _aar.TANKERS["ka6d"]["type"].id
    assert tanker_id not in ("ka6d", "KA-6D"), tanker_id
    assert tanker_id in txt, f"the chosen tanker ({tanker_id}) is not in the mission"


def test_the_whole_track_download_no_longer_builds_anything(client,
                                                            monkeypatch):
    """The three tests that used to live here — a customised zip, a per-
    selection cache key, a filename naming the selection — all described the
    in-request builder. It is deleted, so what replaces them is the assertion
    that it is really gone: with nothing published, the endpoint refuses and
    `generate` is never reached."""
    import server.app as A

    def boom(*a, **k):
        raise AssertionError("a mission was built inside the request")
    monkeypatch.setattr(A, "generate", boom)
    r = client.get("/api/track/aar_probe/all.zip",
                   params={"era": "modern", "aircraft": "AV8BNA",
                           "tanker": "kc130"})
    assert r.status_code == 409, r.status_code


def test_a_track_with_nothing_to_pick_says_so_rather_than_shipping_an_empty_wizard(client):
    """The White Knights syllabus is pinned to the F-4E in one era. There is no
    era/aircraft/tanker choice to make, and an empty picker rendered as a row
    of buttons with nothing in them reads as a broken control rather than an
    absent one."""
    o = client.get("/api/options").json()["tracks"]
    fixed = [t for t, tr in o.items() if not tr["configurable"]]
    assert fixed, "no fixed track in the payload — this guard is vacuous"
    for tid in fixed:
        assert o[tid]["picker"] == {}, tid
        assert o[tid]["rides"], f"{tid} has no rides either — that IS broken"
