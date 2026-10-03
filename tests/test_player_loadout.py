"""Your own jet has to take off with weapons on it.

Until this release it did not. Every mission, every mission kind, every
airframe: empty pylons. It had even been written up as a feature — "your
loadout is yours to set in the Mission Editor" — but it was never a decision.
It is the same missing data that left the bandits clean until v1.44.0: pydcs's
`load_task_default_loadout()` reads payload `.lua` files out of a DCS
*installation*, a server has no install, and the call is a silent no-op.

The fix cannot be a hand-authored table. The player flies 75 airframes across 7
mission kinds, 3 eras and 3 weights, and hand-authoring that matrix is thousands
of entries and thousands of chances to hang a store on a station DCS refuses.
So the fit is COMPOSED from pydcs's own per-airframe `PylonN` legal-store lists
— the same source `tests/test_loadouts.py` checks the AI table against.

That makes the interesting risk different from the AI table's. A derived fit
cannot be illegal, because it can only choose from what the aircraft is allowed
to carry. What it CAN be is stupid: a SEAD jet with no anti-radiation missile, a
strike jet that spent every station on AMRAAMs, a Tomcat with no Phoenix
because its type id isn't in pydcs. All three of those happened while this was
being built, and all three are pinned below.
"""
from ui_source import ui_source, server_source
import collections
import zipfile

import pytest

import dcs.lua as lua
from dcs import planes
from missiongen import Recipe, generate
from missiongen import loadouts as LO
from missiongen.recipe import RECIPE_ENUMS
from missiongen.resolver import load_json
from missiongen.threats import resolve_plane

ERAS = load_json("eras")
SERVICE = load_json("aircraft_service")


def _flyable():
    """(recipe key, pydcs type id) for everything the Builder offers."""
    from server.app import flyable_aircraft
    out = []
    for a in flyable_aircraft():
        key = a["key"]
        try:
            out.append((key, resolve_plane(key).id))
        except Exception:
            try:
                from missiongen.pending import get_pending
                out.append((key, get_pending(key)[0].id))
            except Exception:
                pytest.fail(f"{key} is offered but resolves to no aircraft type")
    return sorted(out)


FLYABLE = _flyable()
KINDS = list(LO.KIND_ROLE)

# Airframes pydcs gives no pylon stores for at all — trainers, aerobatic types,
# and the Gazelle variants whose armament is part of the airframe rather than a
# station. An empty fit is the correct answer for these, and listing them by
# name means a NEW empty airframe fails the sweep instead of joining a silent
# allowlist.
UNARMED = {"C-101EB", "Christen Eagle II", "MosquitoFBMkVI", "SA342M",
           "SA342Minigun", "SA342Mistral", "TF-51D", "Yak-52"}


def _eras_for(key):
    win = SERVICE.get(key)
    for era, cfg in ERAS.items():
        if win:
            lo, hi = (win[0] or 0), (win[1] or 9999)
            if lo > cfg["window"][1] or hi < cfg["window"][0]:
                continue
        yield era


# --- the sweep --------------------------------------------------------------

def test_the_roster_parsed():
    assert len(FLYABLE) >= 60, f"only {len(FLYABLE)} flyable aircraft found"
    assert len(KINDS) == len(RECIPE_ENUMS["mission_kind"])


@pytest.mark.parametrize("key,type_id", FLYABLE, ids=[k for k, _t in FLYABLE])
def test_every_flyable_airframe_gets_armed(key, type_id):
    """The headline sweep. An armed aircraft must produce a fit for every
    mission kind in every era it can fly, and an unarmed one must be on the
    list of aircraft that genuinely carry nothing."""
    for era in _eras_for(key):
        for kind in KINDS:
            fit = LO.player_loadout(type_id, kind, era)
            if type_id in UNARMED:
                continue
            assert fit["pylons"], (
                f"{type_id} ({kind}/{era}) spawns CLEAN. If this airframe "
                f"really carries nothing, add it to UNARMED and say why.")
            assert fit["label"], f"{type_id} ({kind}/{era}) has a fit and no label"


@pytest.mark.parametrize("type_id", sorted(UNARMED))
def test_the_unarmed_list_is_honest(type_id):
    """The other half: an aircraft is only allowed on the UNARMED list if pydcs
    genuinely offers it no stores. Without this the list becomes a place to
    hide airframes whose fits are merely broken."""
    t = LO._plane_type(type_id)
    if t is None:
        return
    stores = {}
    for p in getattr(t, "pylons", ()) or ():
        stores.update(LO._pylon_stores(t, p))
    weapons = [c for c in (LO.store_class(c) for c in stores)
               if c not in ("tank", "pod", "ecm", "other", "practice")]
    assert not weapons, (
        f"{type_id} is on the UNARMED list but pydcs offers it {set(weapons)} "
        f"— it should be getting a fit")


# --- legality: the same guarantee the AI table gets -------------------------

def _sample():
    """A representative slice: every kind, on the airframes people actually
    fly, in each era they fly in. The full cross-product is ~760 builds."""
    picks = ["FA-18C_hornet", "F-16C_50", "F-15ESE", "F-14B", "F-14A-135-GR",
             "A-10C_2", "AV8BNA", "M-2000C", "JF-17", "MiG-21Bis", "F-5E-3",
             "Su-25T", "AH-64D_BLK_II", "Ka-50", "P-51D", "F-4E-45MC"]
    by_id = {t: k for k, t in FLYABLE}
    for t in picks:
        if t not in by_id:
            continue
        # Only eras the aircraft can actually be flown in. `aircraft_in_era()`
        # gates the Builder, so an F-16C in WWII is not a combination anyone can
        # produce — and asserting on it just measures the authored table's "*"
        # era key, which is not what this test is about.
        for era in _eras_for(by_id[t]):
            for kind in KINDS:
                yield t, kind, era


SAMPLE = list(_sample())


@pytest.mark.parametrize("type_id,kind,era", SAMPLE,
                         ids=[f"{t}/{k}/{e}" for t, k, e in SAMPLE])
def test_every_store_is_legal_on_the_station_it_lands_on(type_id, kind, era):
    """DCS silently drops an illegal store — the jet spawns without it and
    nothing says so. A derived fit should be incapable of this by construction;
    this proves the construction."""
    t = LO._plane_type(type_id)
    if t is None:
        pytest.skip(f"{type_id} has no pydcs class")
    for station, clsid in LO.player_loadout(type_id, kind, era)["pylons"].items():
        legal = LO._pylon_stores(t, int(station))
        assert clsid in legal, (
            f"{type_id} ({kind}/{era}) pylon {station} will not take "
            f"{LO._store_names().get(clsid, clsid)}")


@pytest.mark.parametrize("type_id,kind,era", SAMPLE,
                         ids=[f"{t}/{k}/{e}" for t, k, e in SAMPLE])
def test_nothing_predates_the_era_it_is_flown_in(type_id, kind, era):
    """An AMRAAM on a 1975 mission is not a bug DCS will catch. It is a bug the
    person flying a Cold War mission will catch."""
    windows = LO.service_windows()
    e_lo, e_hi = ERAS[era]["window"]
    for station, clsid in LO.player_loadout(type_id, kind, era)["pylons"].items():
        win = windows.get(clsid)
        if not win:
            continue
        w_lo, w_hi = (win[0] or 0), (win[1] or 9999)
        assert not (w_lo > e_hi or w_hi < e_lo), (
            f"{type_id} ({kind}/{era}) carries "
            f"{LO._store_names().get(clsid, clsid)} on pylon {station}, "
            f"in service {w_lo}-{w_hi}, era is {e_lo}-{e_hi}")


# --- the fit has to suit the job -------------------------------------------

@pytest.mark.parametrize("kind,wanted,type_id,era", [
    ("sead", "arm", "FA-18C_hornet", "modern"),
    ("sead", "arm", "F-16C_50", "modern"),
    ("strike", ("jdam", "lgb", "bomb", "cbu", "agm"), "FA-18C_hornet", "modern"),
    ("strike", ("jdam", "lgb", "bomb", "cbu", "agm"), "F-15ESE", "modern"),
    ("cas", ("agm", "rocket", "cbu", "bomb", "lgb", "gunpod"), "A-10C_2", "modern"),
    ("cas", ("agm", "rocket", "cbu", "bomb", "lgb", "gunpod"), "Ka-50", "modern"),
    ("a2a", ("arh", "sarh", "hobs", "ir"), "F-14B", "modern"),
    ("a2a", ("arh", "sarh", "hobs", "ir"), "MiG-21Bis", "coldwar"),
])
def test_picking_a_mission_type_changes_what_you_carry(kind, wanted, type_id, era):
    """The whole point. Early on this silently failed for the sixteen airframes
    that happen to be in the AI table, because `loadout_for` falls back to the
    `cap` entry — so an F-16C flew every SEAD, CAS and strike mission carrying
    the authored air-to-air fit."""
    want = (wanted,) if isinstance(wanted, str) else wanted
    fit = LO.player_loadout(type_id, kind, era)
    classes = {LO.store_class(c) for c in fit["pylons"].values()}
    assert classes & set(want), (
        f"{type_id} on a {kind} mission carries {sorted(classes)}, "
        f"none of which is {sorted(want)}: {fit['label']}")


def test_a_strike_jet_does_not_spend_the_aeroplane_on_air_to_air():
    """Without a cap, filling every AAM-capable station first gave a 'strike'
    F-15E eight AMRAAMs and two bombs — a jet that has not been sent to do the
    job the user picked."""
    for type_id in ("F-15ESE", "FA-18C_hornet", "F-16C_50"):
        fit = LO.player_loadout(type_id, "strike", "modern")
        classes = [LO.store_class(c) for c in fit["pylons"].values()]
        aam = sum(1 for c in classes if c in ("arh", "sarh", "ir", "hobs"))
        a2g = sum(1 for c in classes if c in ("jdam", "lgb", "bomb", "cbu", "agm"))
        assert a2g >= aam, \
            f"{type_id} strike fit is {aam} AAMs to {a2g} ground stores: {fit['label']}"


def test_nobody_goes_to_war_with_empty_rails():
    """Every fit keeps a pair of air-to-air missiles where the airframe has
    stations that can carry nothing else."""
    for kind in ("strike", "cas", "sead"):
        fit = LO.player_loadout("FA-18C_hornet", kind, "modern")
        classes = {LO.store_class(c) for c in fit["pylons"].values()}
        assert classes & {"ir", "hobs", "arh", "sarh"}, \
            f"Hornet {kind} fit has no self-defense missile: {fit['label']}"


def test_the_tomcat_carries_the_phoenix():
    """Named on its own because it was silently broken: the F-14B(U) is
    registered at runtime as a subclass of the F-14B, so it never appeared in
    the pylon index under its own id and derived an EMPTY fit. On a Tomcat that
    means no Phoenix, which is most of the reason to fly one."""
    for type_id in ("F-14B", "F-14A-135-GR", "F-14BU"):
        fit = LO.player_loadout(type_id, "a2a", "modern")
        assert fit["pylons"], f"{type_id} derived nothing at all"
        names = " ".join(LO._store_names().get(c, "")
                         for c in fit["pylons"].values())
        assert "AIM-54" in names, f"{type_id} has no Phoenix: {fit['label']}"


def test_the_weight_dial_changes_the_load():
    loads = [len(LO.player_loadout("F-14B", "a2a", "modern", w)["pylons"])
             for w in LO.WEIGHTS]
    assert loads[0] < loads[-1], f"light/standard/heavy gave {loads}"
    for type_id in ("FA-18C_hornet", "A-10C_2"):
        a = LO.player_loadout(type_id, "cas", "modern", "light")["label"]
        b = LO.player_loadout(type_id, "cas", "modern", "heavy")["label"]
        assert a != b, f"{type_id}: the weight dial does nothing"


def test_an_authored_entry_still_wins():
    """The hand-curated AI table is the override for anything the derivation
    gets wrong, so it has to actually take precedence."""
    fit = LO.player_loadout("MiG-21Bis", "a2a", "coldwar")
    authored = LO.loadout_for("MiG-21Bis", LO.ROLE_CAP, "coldwar")
    assert fit["pylons"] == authored["pylons"]


def test_a_jet_asked_for_a_job_it_cannot_do_still_flies_armed():
    """A Mustang has no anti-radiation anything. It should fly its ground-attack
    fit rather than come back clean."""
    fit = LO.player_loadout("P-51D", "sead", "wwii")
    assert fit["pylons"], "the P-51 came back clean from a SEAD tasking"


def test_derivation_is_deterministic():
    """A share link is a byte-for-byte contract, so no rng may touch this."""
    for _ in range(3):
        assert (LO.player_loadout("FA-18C_hornet", "cas", "modern")
                == LO.player_loadout("FA-18C_hornet", "cas", "modern"))


# --- the classifier ---------------------------------------------------------

@pytest.mark.parametrize("needle,want", [
    ("AIM-54A-Mk60", "arh"), ("AIM-7M", "sarh"), ("LAU-7 AIM-9M", "ir"),
    ("K-13A", "ir"), ("PL-12 AAM", "arh"), ("Mk-20", "cbu"),
    ("GIAT M621 (240x HE)", "gunpod"), ("Lantirn Target Pod", "pod"),
    ("MXU-648 Travel Pod", "other"),
    ("TGM-65H - Trg Round for Mav H (CCD)", "practice"),
    ("AGM-88C HARM - High Speed Anti-Radiation Missile", "arm"),
])
def test_stores_are_classified_from_dcs_own_words(needle, want):
    """A baggage pod is not a targeting pod, and a training round is not a
    Maverick. Both were mounted on real fits before these patterns existed."""
    names = LO._store_names()
    clsid = next((k for k, v in names.items() if v == needle), None)
    assert clsid, f"{needle!r} is no longer a store pydcs knows about"
    assert LO.store_class(clsid) == want


def test_no_fit_ever_selects_a_store_we_cannot_name():
    """The meaningful version of "is the classifier good enough": not a
    percentage, but whether anything unclassified actually reaches a jet. An
    'other' store can only be chosen as a tank or a pod, never as a weapon, so
    a fit containing one means the taxonomy has a hole where a weapon should be.
    """
    bad = []
    for type_id, kind, era in SAMPLE:
        for station, clsid in LO.player_loadout(type_id, kind, era)["pylons"].items():
            if LO.store_class(clsid) == "other":
                bad.append(f"{type_id}/{kind}/{era} p{station}: "
                           f"{LO._store_names().get(clsid, clsid)}")
    assert not bad, "fits contain unclassified stores:\n  " + "\n  ".join(bad[:12])


@pytest.mark.parametrize("needle", [
    "AIM-54", "AIM-120", "AIM-9", "AIM-7", "AGM-88", "AGM-65", "GBU-12",
    "GBU-31", "R-73", "R-27", "R-60", "Kh-25", "Vikhr", "Mk-82",
])
def test_the_weapons_that_matter_are_all_classified(needle):
    """A named list, because the failure mode is silent: an unclassified store
    is simply never selected, and when this taxonomy had 336 unknowns the
    AIM-54 Phoenix was one of them — so the Tomcat flew without its missile and
    nothing anywhere said so."""
    names = LO._store_names()
    hits = [k for k, v in names.items() if needle.lower() in v.lower()]
    assert hits, f"{needle} is no longer a store pydcs knows about"
    unknown = [names[k] for k in hits if LO.store_class(k) == "other"]
    assert not unknown, f"{needle}: unclassified variants {unknown[:4]}"


def test_the_unclassified_tail_stays_small():
    """A loose canary on the rest. These should be smoke, decoys, empty racks
    and camera pods — things with no business on a combat fit."""
    names = LO._store_names()
    unknown = [n for k, n in names.items() if LO.store_class(k) == "other"]
    assert len(unknown) < 0.10 * len(names), (
        f"{len(unknown)} of {len(names)} stores are unclassified: "
        f"{sorted(set(unknown))[:8]}")


def test_the_later_mark_is_preferred():
    """Sorting on the name picks the AIM-120B over the C because B sorts first,
    and the AIM-9P over the AIM-9M even though the P is older. The service year
    is the actual answer."""
    fit = LO.player_loadout("FA-18C_hornet", "a2a", "modern")
    names = " ".join(LO._store_names().get(c, "") for c in fit["pylons"].values())
    assert "AIM-120C" in names, f"Hornet CAP fit took an older AMRAAM: {names}"


# --- end to end -------------------------------------------------------------

def _player_units(path):
    m = lua.loads(zipfile.ZipFile(path).read("mission").decode())["mission"]
    for coal in m["coalition"].values():
        if not isinstance(coal, dict):
            continue
        for c in coal.get("country", {}).values():
            for kind in ("plane", "helicopter"):
                for g in c.get(kind, {}).get("group", {}).values():
                    for u in g.get("units", {}).values():
                        if u.get("skill") in ("Player", "Client"):
                            yield u


@pytest.mark.parametrize("ac,kind", [
    ("FA_18C_hornet", "a2a"), ("FA_18C_hornet", "strike"),
    ("F_16C_50", "sead"), ("A_10C_2", "cas"), ("F_14B_U", "a2a"),
    ("F_5E_3", "training"),
])
def test_the_players_jet_is_armed_in_a_real_mission(ac, kind, tmp_path):
    """Everything above can be right and the jet still spawn clean if `arm()`
    is never called on the path that builds it — which is exactly what used to
    happen."""
    out = str(tmp_path / "p.miz")
    res = generate(Recipe.from_dict(dict(
        map="caucasus", era="modern", aircraft=ac, mission_kind=kind,
        bb_ambient=False, seed=1)), out)
    units = list(_player_units(out))
    assert units, f"{ac}: no player unit in the mission"
    for u in units:
        pylons = (u.get("payload") or {}).get("pylons") or {}
        assert pylons, f"{ac} ({kind}) spawned with empty pylons"
    assert res["stats"].get("player_loadout"), \
        f"{ac} ({kind}): armed but the brief has nothing to say about it"


def test_turning_it_off_gives_you_a_clean_jet(tmp_path):
    out = str(tmp_path / "c.miz")
    generate(Recipe.from_dict(dict(
        map="caucasus", era="modern", aircraft="FA_18C_hornet",
        mission_kind="a2a", player_arm=False, bb_ambient=False, seed=1)), out)
    for u in _player_units(out):
        assert not ((u.get("payload") or {}).get("pylons") or {}), \
            "player_arm=False still armed the jet"


def test_the_brief_says_what_you_are_carrying(tmp_path):
    """The user never sees a pylon picker, so the brief is where they find out
    what they took off with."""
    out = str(tmp_path / "b.miz")
    res = generate(Recipe.from_dict(dict(
        map="caucasus", era="modern", aircraft="FA_18C_hornet",
        mission_kind="sead", bb_ambient=False, seed=2)),
        out, brief_dir=str(tmp_path))
    md = open(res["brief_md"]).read()
    assert "## Your loadout" in md, "the brief never mentions your loadout"
    assert res["stats"]["player_loadout"] in md


def test_the_setting_survives_a_share_link():
    from missiongen.share import decode_recipe, encode_recipe
    rc = Recipe.from_dict(dict(map="caucasus", era="modern",
                               aircraft="FA_18C_hornet", player_arm=False,
                               player_load="heavy"))
    back = decode_recipe(encode_recipe(rc))
    assert back.player_arm is False and back.player_load == "heavy"


def test_an_older_link_gets_the_default():
    import base64
    import json
    from missiongen.share import decode_recipe
    payload = {"v": 1, "r": {"map": "caucasus", "era": "modern",
                             "aircraft": "FA_18C_hornet"}}
    code = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    rc = decode_recipe(code)
    assert rc.player_arm is True and rc.player_load == "standard"


def test_the_controls_are_in_the_builder():
    import re
    from pathlib import Path
    html = ui_source()
    assert 'id="player_arm"' in html, "no arm toggle in the Builder"
    m = re.search(r'<select[^>]*id="player_load"[^>]*>(.*?)</select>', html, re.S)
    assert m, "no weight dial in the Builder"
    offered = set(re.findall(r'value="([^"]+)"', m.group(1)))
    assert offered == set(LO.WEIGHTS), f"UI offers {sorted(offered)}"


# --- the F-14B(U) livery ----------------------------------------------------

def test_nothing_is_written_while_the_livery_pack_is_unverified():
    """A livery id is a folder name on someone's disk and cannot be checked from
    a server. v1.46.4 is what happens when you guess anyway."""
    from missiongen.dressing import livery_pack_verified, player_livery
    if livery_pack_verified():
        pytest.skip("pack verified against a real install")
    assert player_livery("F-14BU", "modern", "USA") is None


def test_the_red_rippers_are_the_f14b_default_once_verified(monkeypatch):
    """What Rob asked for, proven against a simulated verified pack so it is
    known to work the moment `dump_liveries.py` runs."""
    import json as _json

    from missiongen import dressing as D
    raw = _json.loads(_json.dumps(load_json("liveries")))
    raw["_verified"] = True
    monkeypatch.setattr(D, "_LIVERY_RAW", raw)
    for type_id in ("F-14BU", "F-14B"):
        assert D.player_livery(type_id, "modern", "USA") == "VF-11 Red Rippers", \
            f"{type_id} does not default to the Red Rippers"


def test_the_red_rippers_do_not_fly_a_cold_war_mission(monkeypatch):
    """VF-11 flew the F-14B from 1996 to 2005. The F-14B(U) is Cold War-capable
    since v1.46.2, and Red Rippers markings on a 1975 mission are an
    anachronism — so the marking is era-keyed, not a single default."""
    import json as _json

    from missiongen import dressing as D
    raw = _json.loads(_json.dumps(load_json("liveries")))
    raw["_verified"] = True
    monkeypatch.setattr(D, "_LIVERY_RAW", raw)
    cw = D.player_livery("F-14BU", "coldwar", "USA")
    assert cw and cw != "VF-11 Red Rippers", \
        f"Cold War F-14B(U) wears {cw!r}"


def test_the_pack_no_longer_claims_unknown_ids_are_harmless():
    """The note said DCS falls back to the stock skin for a name it doesn't
    know. It does not — that belief is what shipped v1.46.4."""
    note = " ".join(load_json("liveries").get("_note", "").lower().split())
    assert "are harmless" not in note and "is harmless" not in note, \
        "liveries.json still tells the next maintainer that a wrong id is safe"
    assert "not harmless" in note or "wrong or blank" in note, \
        "the note no longer warns that an unverified id gives a wrong aircraft"
