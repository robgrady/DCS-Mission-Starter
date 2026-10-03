"""The comms card must describe the mission, not a plan the mission ignores.

Rob asked whether the printed frequencies are the ones the mission actually
uses. Three of them were not, for two separate reasons:

  1. pydcs's `refuel_flight()` / `awacs_flight()` attach a SetFrequency TASK at
     waypoint 2 but leave the group's own radio on their 251.0 default. The
     tanker and the AWACS therefore spawned co-channel on 251.0, off the briefed
     frequency, and the Mission Editor showed 251 beside a card saying 253.625.
  2. `ShipGroup.set_frequency()` takes HERTZ (pydcs default 127500000) while
     `FlyingGroup.set_frequency()` takes MHz. Passing MHz put the entire carrier
     battle group on 264.425 Hz — the carrier was never on the briefed
     frequency at all.

A card that says one thing while the mission does another is worse than no card,
so this walks the printed ladder and checks each row against the .miz.
"""
import zipfile
from pathlib import Path

import pytest

import dcs.lua as lua
from missiongen import Recipe, generate

# Agencies with no group of their own by design: Guard is a monitored emergency
# channel and Tactical is a flight-internal working frequency. Neither is a
# station you call, so there is nothing in the mission to compare them against.
NO_GROUP = {"Guard", "Tactical"}


def _mission(path):
    return lua.loads(zipfile.ZipFile(path).read("mission").decode())["mission"]


def _groups(m, *kinds):
    for coal in m["coalition"].values():
        for c in coal.get("country", {}).values():
            for k in (kinds or ("plane", "helicopter", "ship")):
                for g in c.get(k, {}).get("group", {}).values():
                    yield g


def _card_rows(md_path):
    rows, on = [], False
    for line in Path(md_path).read_text().splitlines():
        if line.startswith("| Agency"):
            on = True
            continue
        if on:
            if not line.startswith("|"):
                break
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 5 and not set(cells[0]) <= set("-"):
                rows.append(cells)
    return rows


def _build(tmp_path, **rc):
    out = str(tmp_path / "m.miz")
    res = generate(Recipe.from_dict({**rc, "bb_ambient": False}), out,
                   brief_dir=str(tmp_path))
    return _mission(out), _card_rows(res["brief_md"])


def _named(m, needle, *kinds):
    return next((g for g in _groups(m, *kinds)
                 if needle.lower() in (g.get("name") or "").lower()), None)


# --- the two defects, pinned individually -----------------------------------

def test_tanker_and_awacs_own_their_radio(tmp_path):
    """Not just a SetFrequency task at waypoint 2 — the group must BE on the
    briefed frequency when it spawns."""
    m, rows = _build(tmp_path, map="caucasus", era="modern",
                     aircraft="FA_18C_hornet", bb_tanker=True, bb_awacs=True,
                     seed=4)
    card = {r[0]: float(r[2]) for r in rows if r[2].replace(".", "").isdigit()}
    for agency, needle in (("Tanker", "texaco"), ("AWACS", "overlord")):
        g = _named(m, needle, "plane")
        assert g is not None, f"no {agency} group in the mission"
        assert g.get("frequency") == pytest.approx(card[agency]), (
            f"{agency}: card says {card[agency]}, group radio is "
            f"{g.get('frequency')} (pydcs's default is 251.0)")

    # and they must not share a channel
    assert (_named(m, "texaco", "plane")["frequency"]
            != _named(m, "overlord", "plane")["frequency"]), \
        "the tanker and the AWACS are co-channel"


def test_carrier_frequency_is_in_hertz(tmp_path):
    """ShipGroup.set_frequency takes hertz while FlyingGroup takes MHz — the
    trap that put the battle group on 264.425 Hz."""
    m, rows = _build(tmp_path, map="caucasus", era="coldwar",
                     aircraft="F_14A_135_GR", bb_carrier=True,
                     home_airbase="CARRIER", seed=6)
    want = next(float(r[2]) for r in rows if r[0] == "Carrier")
    ships = [u for g in _groups(m, "ship") for u in g.get("units", {}).values()]
    assert ships, "no carrier group generated"
    for u in ships:
        f = u.get("frequency")
        assert f and f > 1e6, \
            f"{u.get('name')}: frequency {f} looks like MHz in a hertz field"
        assert round(f / 1e6, 3) == pytest.approx(want), \
            f"{u.get('name')}: card says {want} MHz, ship is on {f/1e6:.3f} MHz"


# --- the general contract ---------------------------------------------------

@pytest.mark.parametrize("label,rc", [
    ("land", dict(map="caucasus", era="modern", aircraft="FA_18C_hornet",
                  bb_tanker=True, bb_awacs=True, seed=4)),
    ("carrier", dict(map="caucasus", era="coldwar", aircraft="F_14A_135_GR",
                     bb_carrier=True, home_airbase="CARRIER", bb_tanker=True,
                     bb_awacs=True, carrier_cap=True, carrier_aew=True, seed=6)),
])
def test_every_airborne_agency_is_on_its_printed_frequency(label, rc, tmp_path):
    m, rows = _build(tmp_path, **rc)
    needles = {"Tanker": "texaco", "AWACS": "overlord", "AEW": "aew",
               "CAP": "cap", "Plane guard": "angel"}
    checked = 0
    for agency, cs_, freq, chan, tacan, *_notes in rows:
        if agency in NO_GROUP or agency not in needles:
            continue
        try:
            want = float(freq)
        except ValueError:
            continue
        g = _named(m, needles[agency], "plane", "helicopter")
        if g is None:
            continue
        checked += 1
        assert g.get("frequency") == pytest.approx(want), (
            f"{label}/{agency}: card {want}, group '{g['name']}' "
            f"{g.get('frequency')}")
    assert checked, f"{label}: no airborne agency was actually checked"


def test_player_presets_match_the_card(tmp_path):
    """The CHAN column promises a cockpit preset. Verify the radio really holds
    that frequency on that channel."""
    m, rows = _build(tmp_path, map="caucasus", era="modern",
                     aircraft="FA_18C_hornet", bb_tanker=True, bb_awacs=True,
                     seed=4)
    unit = next(u for g in _groups(m, "plane")
                for u in g.get("units", {}).values()
                if u.get("skill") in ("Player", "Client"))
    radios = {int(rid): {int(c): float(v) for c, v in (r.get("channels") or {}).items()}
              for rid, r in enumerate((unit.get("Radio") or {}).values(), 1)}
    checked = 0
    for agency, cs_, freq, chan, tacan, *_notes in rows:
        if not chan.startswith("CH"):
            continue
        ch, want = int(chan[2:]), float(freq)
        assert any(r.get(ch) == pytest.approx(want) for r in radios.values()), (
            f"{agency}: card says CH{ch} = {want}, cockpit has "
            f"{ {rid: r.get(ch) for rid, r in radios.items()} }")
        checked += 1
    assert checked >= 4, "the card stopped advertising cockpit presets"


def test_farp_pads_carry_their_printed_frequency(tmp_path):
    """FARPs store theirs on the pad as heliport_frequency, in MHz — a third
    unit convention in the same library, so it is worth pinning."""
    m, rows = _build(tmp_path, map="caucasus", era="modern",
                     aircraft="AH_64D_BLK_II", bb_farps=True, bb_tanker=False,
                     bb_awacs=False, seed=8)
    want = sorted(float(r[2]) for r in rows if r[0] == "FARP")
    pads = sorted(u["heliport_frequency"]
                  for coal in m["coalition"].values()
                  for c in coal.get("country", {}).values()
                  for g in c.get("static", {}).get("group", {}).values()
                  for u in g.get("units", {}).values()
                  if u.get("type") == "FARP")
    assert want and pads == pytest.approx(want), \
        f"card lists FARPs on {want}, pads are on {pads}"


# --- liveries: never write a guess into someone's mission -------------------

def test_no_livery_id_is_written_while_the_pack_is_unverified(tmp_path):
    """The pack's ids are hand-authored GUESSES at DCS livery folder names and
    nothing server-side can check them — pydcs's liveries package is a scanner
    over a DCS install, not bundled data. The data has always said
    "_verified": false; the engine simply never read it, so ~390 guessed strings
    went into a single busy mission. DCS does not reliably fall back to the
    stock skin for a name it does not know, which is why parked aircraft stopped
    looking default."""
    from missiongen.dressing import livery_pack_verified
    from missiongen.resolver import load_json

    pack = load_json("liveries")
    if livery_pack_verified():
        pytest.skip("pack has been verified against a real install")
    assert pack.get("_verified") is False, "the pack lost its honesty flag"

    out = str(tmp_path / "s.miz")
    generate(Recipe.from_dict(dict(map="caucasus", era="modern",
                                   aircraft="FA_18C_hornet", dress_fill=100,
                                   bb_ambient=False, seed=2)), out)
    m = _mission(out)
    from missiongen.dressing import _verified_static_liveries
    guessed = [u for coal in m["coalition"].values()
               for c in coal.get("country", {}).values()
               for g in c.get("static", {}).get("group", {}).values()
               for u in g.get("units", {}).values()
               if u.get("livery_id") and u["livery_id"] not in
               _verified_static_liveries(u["type"], c["name"], "modern")]
    assert not guessed, (
        f"{len(guessed)} static aircraft carry a guessed livery_id, e.g. "
        f"{[u.get('livery_id') for u in guessed[:3]]}")


def test_the_user_is_told_why_statics_are_stock(tmp_path):
    """Silent is worse than plain: a mission whose skins are deliberately stock
    should say so, and say what turns them on."""
    out = str(tmp_path / "w.miz")
    res = generate(Recipe.from_dict(dict(map="caucasus", era="modern",
                                         aircraft="FA_18C_hornet",
                                         dress_fill=60, bb_ambient=False,
                                         seed=2)), out)
    from missiongen.dressing import livery_pack_verified
    if livery_pack_verified():
        pytest.skip("pack verified — no warning expected")
    assert any("dump_liveries" in w for w in res["warnings"]), \
        "no warning explains why parked statics wear stock skins"
