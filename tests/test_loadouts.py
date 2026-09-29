"""AI armament: the bandits must be armed, legally, and for the right decade.

Until v1.44.0 every enemy CAP flight and every BFM adversary spawned CLEAN.
pydcs can set a "default loadout" per task, but it reads payload `.lua` files
out of a DCS *installation*; a server has no install, so `load_payloads()`
returns `{}` and `load_task_default_loadout()` is a silent no-op. Nothing threw.
The mission built, the intercept flew, and the bandit arrived at the merge with
empty pylons.

That class of defect is invisible from the outside, which is what these tests
are for. The table in `data/loadouts.json` is hand-authored, so the risk is not
that it crashes — it is that it quietly contains a store DCS will reject on that
station, or a 1985 missile hung on a 1972 mission. Both are checkable:

  * pydcs DOES ship the per-airframe, per-pylon legal-store lists that DCS
    itself generates (`MiG_21Bis.Pylon1` and friends). Every CLSID we author is
    checked against them, so a fit DCS would refuse cannot reach a cockpit.
  * `data/weapon_service.json` carries a service window per store, checked
    against the era window in `data/eras.json`.

And then the end-to-end check that matters more than either: build missions and
read the pylons back out of the finished .miz.
"""
import zipfile

import pytest

import dcs.lua as lua
from missiongen import Recipe, generate
from missiongen import loadouts as LO
from missiongen import threats as TH
from missiongen.resolver import load_json

ERAS = load_json("eras")

# Roles the engine actually asks for. A role in this list must resolve for
# every airframe the threat pools can spawn.
ROLES = (LO.ROLE_CAP, LO.ROLE_BFM)


def _pool_entries():
    """(era, python name, pydcs id) for every airframe a threat pool can spawn.

    The pools carry python attribute names ('MiG_21Bis'); the loadout table is
    keyed by the DCS id ('MiG-21Bis'), because the id is what the engine has in
    hand at spawn time. Translate through pydcs rather than assuming the
    hyphen/underscore mapping — several airframes break that rule.

    Carrying the era matters: a MiG-23MLD has no business resolving a *WWII*
    fit, and demanding one would only push junk entries into the table.
    """
    seen = set()
    for era, sides in TH.TIER_CAP.items():
        for _side, tiers in sides.items():
            for _tier, pool in tiers.items():
                for n in pool:
                    seen.add((era, n, TH.resolve_plane(n).id))
    return sorted(seen, key=lambda t: (t[0], t[2]))


POOL = _pool_entries()
POOL_IDS = sorted({tid for _e, _n, tid in POOL})

# Guns are the whole armament on a WWII fighter, so an empty `pylons` dict is
# the correct answer there and a lie anywhere else.
GUNFIGHTER_ERAS = {"wwii"}


# --- the table is complete --------------------------------------------------

@pytest.mark.parametrize("era,name,type_id", POOL,
                         ids=[f"{e}/{t}" for e, _n, t in POOL])
def test_every_threat_airframe_has_a_fit_in_the_era_it_flies(era, name, type_id):
    """A jet the engine can spawn but the table has never heard of flies clean
    — exactly the v1.44.0 defect, one airframe at a time."""
    assert type_id in LO.table(), (
        f"{name} is in the {era} threat pool but absent from loadouts.json "
        f"(the table is keyed by pydcs id, so the key is '{type_id}')")
    for role in ROLES:
        fit = LO.loadout_for(type_id, role, era)
        assert fit is not None, f"{type_id}: no {role} fit resolves for {era}"
        if era not in GUNFIGHTER_ERAS:
            assert fit["pylons"], (
                f"{type_id} ({role}, {era}) resolves to an EMPTY fit — that is "
                f"the clean airframe defect wearing a label")


# --- every store is legal on the station it is hung from --------------------

def _authored():
    """(type_id, role, era_key, pylon, clsid) for every store in the table."""
    for type_id, roles in LO.table().items():
        for role, eras in roles.items():
            for era_key, entry in eras.items():
                variants = [entry]
                if isinstance(entry.get("light"), dict):
                    variants.append(entry["light"])
                for v in variants:
                    for pylon, clsid in (v.get("pylons") or {}).items():
                        yield type_id, role, era_key, int(pylon), clsid


AUTHORED = list(_authored())


def test_the_table_is_not_empty():
    """A guard on the guards: every check below is a parametrize over this
    list, and an empty list makes all of them vacuously pass."""
    assert len(AUTHORED) > 40, f"only {len(AUTHORED)} authored stores — did the table load?"


@pytest.mark.parametrize("type_id,role,era_key,pylon,clsid", AUTHORED,
                         ids=[f"{t}/{r}/{e}/p{p}" for t, r, e, p, _c in AUTHORED])
def test_every_store_is_legal_on_its_pylon(type_id, role, era_key, pylon, clsid):
    """DCS silently drops an illegal store — the jet spawns without it and
    nothing anywhere says so. pydcs ships the same legal-store lists DCS
    generates, so this is checkable before anyone flies it."""
    t = LO._plane_type(type_id)
    assert t is not None, f"{type_id} is not a pydcs airframe"
    legal = LO._pylon_stores(t, pylon)
    assert legal, f"{type_id} has no pylon {pylon}"
    assert clsid in legal, (
        f"{type_id} pylon {pylon} will not take {clsid} "
        f"({LO._store_names().get(clsid, 'unknown store')}). "
        f"Legal there: {sorted(legal.values())[:6]}")


@pytest.mark.parametrize("clsid", sorted({c for *_x, c in AUTHORED}))
def test_every_store_is_a_store_we_can_name(clsid):
    """`weapon_class()` reads the guidance type out of the store's display
    name. A CLSID with no name silently classifies as 'other', which means the
    brief tells the pilot nothing — the failure is a blank line, not an error."""
    assert LO._store_names().get(clsid), f"{clsid} has no display name"


# --- era discipline ---------------------------------------------------------

def test_no_store_predates_the_era_it_is_authored_for():
    """An R-77 on a 1978 MiG is not a bug DCS will catch. It is a bug the
    person flying a Cold War mission will catch, and it costs the mission its
    credibility."""
    windows = LO.service_windows()
    bad = []
    for type_id, role, era_key, pylon, clsid in AUTHORED:
        if era_key == "*" or era_key not in ERAS:
            continue
        win = windows.get(clsid)
        if not win:
            continue
        e_lo, e_hi = ERAS[era_key]["window"]
        # An open-ended window (`null` upper bound) means "still in service".
        w_lo, w_hi = (win[0] or 0), (win[1] or 9999)
        if w_lo > e_hi or w_hi < e_lo:
            bad.append(f"{type_id}/{era_key} p{pylon}: "
                       f"{LO._store_names().get(clsid, clsid)} served "
                       f"{w_lo}-{w_hi}, era is {e_lo}-{e_hi}")
    assert not bad, "stores outside their service window:\n  " + "\n  ".join(bad)


def test_every_missile_in_the_table_has_a_service_window():
    """Coverage guard on the test above: a store with no window is skipped, so
    an unlisted store would sail through the era check unexamined."""
    windows = LO.service_windows()
    missing = sorted({
        f"{LO._store_names().get(c, c)} [{c}]"
        for *_x, c in AUTHORED
        if c not in windows and LO.weapon_class(c) not in ("tank", "other")})
    assert not missing, "missiles with no service window:\n  " + "\n  ".join(missing)


# --- the merge is a knife fight ---------------------------------------------

@pytest.mark.parametrize("era,name,type_id", POOL,
                         ids=[f"{e}/{t}" for e, _n, t in POOL])
def test_the_bfm_adversary_never_carries_radar_missiles(era, name, type_id):
    """The point of BFM is the fight. A bandit that kills you at twenty miles
    has not given you the training you asked for."""
    fit = LO.loadout_for(type_id, LO.ROLE_BFM, era) or {}
    classes = {LO.weapon_class(c) for c in fit.get("pylons", {}).values()}
    assert not (classes & {"arh", "sarh"}), (
        f"{type_id} BFM fit in {era} carries radar missiles "
        f"({fit.get('label')})")


def test_the_threat_dial_changes_the_fit_not_just_the_head_count():
    """Intensity 1-2 takes the 'light' variant where one is authored. If the
    dial only ever changed the number of jets, a training mission at Minimal
    would still be a full-up modern fight."""
    lighter = []
    for type_id, roles in LO.table().items():
        for role, eras in roles.items():
            for era_key, entry in eras.items():
                if not isinstance(entry.get("light"), dict):
                    continue
                low = LO.loadout_for(type_id, role, era_key, intensity=1)
                high = LO.loadout_for(type_id, role, era_key, intensity=4)
                assert low != high, \
                    f"{type_id}/{role}/{era_key} authored a light variant that " \
                    f"resolve ignores"
                lighter.append(type_id)
    assert lighter, "no airframe has a light variant — the dial is cosmetic"


# --- the brief tells the truth ----------------------------------------------

def test_the_implication_reports_the_worst_thing_carried():
    """Two R-60s under an R-27ER do not make the fight a knife fight."""
    arh = "{B4C01D60-A8A3-4237-BD72-CA7655BC0FE9}"   # R-77 (AA-12) Active Rdr
    sarh = "{9B25D316-0434-4954-868F-D51DB1A38DF0}"  # R-27R Semi-Act Rdr
    ir = "{FBC29BFE-3D24-4C64-B81D-941239D12249}"    # R-73 (also HOBS)
    assert LO.weapon_class(arh) == "arh"
    assert LO.weapon_class(sarh) == "sarh"
    assert LO.weapon_class(ir) == "hobs"

    line = LO.implication([arh, ir])
    assert "Active radar" in line, f"R-77 + R-73 read as: {line}"
    assert "high-off-boresight" in line, \
        "a radar shooter that also carries HOBS IR must say so — surviving " \
        "the BVR phase is not the same as surviving"
    assert "Semi-active" in LO.implication([sarh])
    assert "Guns only" in LO.implication([])


def test_the_same_implication_is_never_printed_twice():
    """A CAP MiG-21 and a merge MiG-21 threaten you the same way. Printing the
    identical sentence twice turns intel back into boilerplate, which is how
    people learn to skip the block."""
    recs = [LO.describe("MiG-21Bis", LO.ROLE_CAP, "coldwar", count=2),
            LO.describe("MiG-21Bis", LO.ROLE_BFM, "coldwar", count=1)]
    imps = [imp for _who, _fit, imp in LO.brief_lines(recs) if imp]
    assert len(imps) == len(set(imps)), f"duplicated implication: {imps}"


def test_summarize_collapses_flights_but_keeps_the_count():
    recs = [LO.describe("MiG-29S", LO.ROLE_CAP, "modern", count=2)] * 3
    rows = LO.summarize(recs)
    assert len(rows) == 1 and rows[0]["count"] == 6


def test_a_missing_entry_degrades_instead_of_exploding():
    """A new airframe added to a threat pool must not be able to break
    generation — it flies clean and says so."""
    warnings = []
    assert LO.loadout_for("Not-A-Jet", LO.ROLE_CAP, "modern") is None

    class _Grp:
        def load_pylon(self, *a, **k):
            raise AssertionError("nothing should be loaded")

    assert LO.arm(_Grp(), "Not-A-Jet", LO.ROLE_CAP, "modern",
                  warnings=warnings) is None
    assert any("Not-A-Jet" in w for w in warnings)


# --- and finally: read the pylons back out of a finished mission ------------

def _mission(path):
    return lua.loads(zipfile.ZipFile(path).read("mission").decode())["mission"]


def _enemy_flights(m, own_country_hint="USA"):
    """Plane groups on the coalition the player is not on."""
    for coal_name, coal in m["coalition"].items():
        if coal_name not in ("red", "blue"):
            continue
        for c in coal.get("country", {}).values():
            for g in c.get("plane", {}).get("group", {}).values():
                yield coal_name, g


@pytest.mark.parametrize("label,rc", [
    ("coldwar-cap", dict(map="caucasus", era="coldwar", aircraft="F_5E_3",
                         threat_intensity=5, bb_sams=True, seed=11)),
    ("modern-cap", dict(map="caucasus", era="modern", aircraft="FA_18C_hornet",
                        threat_intensity=5, bb_sams=True, seed=12)),
    ("bfm", dict(map="caucasus", era="modern", aircraft="FA_18C_hornet",
                 bb_bfm=True, threat_intensity=3, seed=13)),
    ("wwii", dict(map="normandy", era="wwii", aircraft="P_51D",
                  threat_intensity=4, bb_sams=True, seed=14)),
])
def test_enemy_flights_in_a_real_mission_are_armed(label, rc, tmp_path):
    """The end-to-end version of all of the above. Everything upstream can be
    right and the jets still spawn clean if `arm()` is never called on the path
    that actually builds them — which is precisely what used to happen.

    WWII is checked too, and is the interesting case: those fighters carry no
    stores at all, so the only honest assertion is that they resolved a fit and
    got briefed. Skipping the era entirely would leave the guns-only path with
    no coverage.
    """
    era = rc["era"]
    out = str(tmp_path / "m.miz")
    res = generate(Recipe.from_dict({**rc, "bb_ambient": False}), out)
    m = _mission(out)

    player = {u.get("type") for _c, g in _enemy_flights(m)
              for u in g.get("units", {}).values()
              if u.get("skill") in ("Player", "Client")}

    fighters = armed = clean = 0
    for _coal, g in _enemy_flights(m):
        for u in g.get("units", {}).values():
            if u.get("skill") in ("Player", "Client"):
                continue            # the player's jet is theirs to load
            if u.get("type") in player:
                continue            # wingmen in the player's flight
            if u.get("type") not in LO.table():
                continue            # transports, tankers, AWACS — not fighters
            fighters += 1
            if (u.get("payload") or {}).get("pylons"):
                armed += 1
            else:
                clean += 1
    assert fighters, f"{label}: the mission fielded no enemy fighters at all"

    if era in GUNFIGHTER_ERAS:
        assert not armed, \
            f"{label}: a WWII fighter is carrying stores it has no pylons for"
    else:
        assert armed, f"{label}: no enemy fighter carried a single store"
        assert not clean, f"{label}: {clean} enemy fighters spawned clean"

    # and the brief must have something to say about them
    assert res["stats"].get("enemy_air"), \
        f"{label}: {fighters} enemy fighters are airborne and none are briefed"


def test_the_briefing_pack_prints_the_enemy_fit(tmp_path):
    """The fit being right is half of it. The user never picks the enemy's
    loadout, so being TOLD what it is, is the whole feature."""
    out = str(tmp_path / "b.miz")
    res = generate(Recipe.from_dict(dict(
        map="caucasus", era="coldwar", aircraft="F_5E_3", threat_intensity=4,
        bb_sams=True, bb_ambient=False, seed=15)), out, brief_dir=str(tmp_path))
    md = open(res["brief_md"]).read()
    assert "## Enemy air" in md, "the brief has no Enemy air section"
    assert res["stats"]["enemy_air"], "nothing to brief — pick a busier seed"
    for rec in res["stats"]["enemy_air"]:
        assert rec["type"] in md, f"{rec['type']} is armed but not briefed"
        assert rec["fit"] in md, f"{rec['type']}: fit '{rec['fit']}' not printed"
        assert rec["implication"] in md, \
            f"{rec['type']}: the tactical implication is missing — that IS the feature"


def test_the_kneeboard_carries_the_enemy_fit_into_the_cockpit(tmp_path):
    """A brief you read on a second monitor before takeoff is not the same as
    a page you can pull up at the merge. The kneeboard is the one that counts."""
    out = str(tmp_path / "k.miz")
    res = generate(Recipe.from_dict(dict(
        map="caucasus", era="modern", aircraft="FA_18C_hornet",
        threat_intensity=4, bb_sams=True, bb_kneeboard=True,
        bb_ambient=False, seed=16)), out)
    assert res["stats"].get("enemy_air"), "no bandits to put on the page"
    pages = [n for n in zipfile.ZipFile(out).namelist()
             if "KNEEBOARD" in n.upper() and n.lower().endswith(".png")]
    assert pages, "no kneeboard pages rode along in the .miz"
    assert res["stats"].get("kneeboard_pages"), "kneeboard page count is zero"
