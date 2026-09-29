"""The boat card must be true in the cockpit, on every hull and both jets.

Casmo flew a Case III off the boat and reported two things:

    "i have zero idea how to do a case 3 recovery so i was flying around blind.
     The radios didn't turn right tho. It says carrier on channel 2 but I had
     to manually tune it to the freq."

Both were real, and neither could fail a test, because nothing here had ever
been checked:

  1. `presets.py` programmed ONE radio. The F-14 has two full UHF sets — the
     pilot's ARC-159 and the RIO's ARC-182 — and the RIO's is the one crews
     normally use for boat comms. It kept pydcs's factory table, where channel
     2 is 258.000. The card said CH2 = Mother and was true about a radio he
     was not keyed to. `test_comms_truth.py` did check presets, but only on a
     LAND Hornet mission, so the carrier row's CH2 had never been read back out
     of a cockpit at all.

  2. ICLS, Link 4, ACLS and the BRC existed ONLY as small gray text on a
     kneeboard PNG inside the .miz. The brief he read before starting had a
     five-column comms table with the notes discarded. You cannot dial an ICLS
     channel you were never given.

So this file reads the whole boat card back out of the mission: the frequency,
the modulation, the TACAN (including whether it is a surface beacon a pilot can
actually receive in T/R), the ICLS channel, the Link 4 frequency, ACLS, and the
cockpit presets on every radio that can hold them — in both directions, so the
card can neither under-promise nor over-promise.
"""
import re
import zipfile
from pathlib import Path

import pytest

import dcs.lua as lua
from missiongen import Recipe, generate

# Map, hull, aircraft and era together — a hull is only offered in the eras its
# ship existed, an aircraft only in the years it flew, and a map only in the
# eras it has a preset for (Caucasus has no 1944, so the Essex sails Marianas).
CASES = [
    ("forrestal/F-14A", dict(map="caucasus", era="coldwar",
                             aircraft="F_14A_135_GR",
                             carrier_hull="forrestal", seed=6)),
    ("cvn73/Hornet",    dict(map="persiangulf", era="modern",
                             aircraft="FA_18C_hornet",
                             carrier_hull="cvn_73", seed=11)),
    ("stennis/F-14B",   dict(map="caucasus", era="modern", aircraft="F_14B",
                             carrier_hull="stennis", seed=23)),
    ("invincible/AV-8B", dict(map="falklands", era="coldwar",
                              aircraft="AV8BNA",
                              carrier_hull="invincible", seed=31)),
    ("essex/F4U",       dict(map="marianas", era="wwii", aircraft="F4U_1D",
                             carrier_hull="essex", seed=44)),
]

UHF_LO, UHF_HI = 225.0, 400.0


# --- reading the mission back ------------------------------------------------

def _build(tmpdir, **rc):
    out = str(Path(tmpdir) / "m.miz")
    rc.setdefault("map", "caucasus")
    rc.setdefault("bb_carrier", True)
    rc.setdefault("home_airbase", "CARRIER")
    res = generate(Recipe.from_dict(dict(bb_ambient=False, **rc)),
                   out, brief_dir=str(tmpdir))
    m = lua.loads(zipfile.ZipFile(out).read("mission").decode())["mission"]
    return m, Path(res["brief_md"]).read_text()


@pytest.fixture(scope="module")
def boats(tmp_path_factory):
    """Every case built once. Module-scoped on purpose: each build writes a
    whole .miz, and the suite runs with --dist loadfile so this file stays on
    one worker and builds them once, not once per worker."""
    out = {}
    for label, rc in CASES:
        d = tmp_path_factory.mktemp(label.replace("/", "_"))
        out[label] = _build(d, **rc)
    return out


def _groups(m, *kinds):
    for coal in m["coalition"].values():
        for c in coal.get("country", {}).values():
            for k in (kinds or ("plane", "helicopter", "ship")):
                for g in c.get(k, {}).get("group", {}).values():
                    yield g


def _csg(m):
    """The carrier battle group — the ship group carrying the beacon tasks, or
    failing that the only ship group with a frequency."""
    ships = list(_groups(m, "ship"))
    assert ships, "no ship group in a carrier mission"
    for g in ships:
        if _actions(g):
            return g
    return ships[0]


def _actions(grp):
    """{ActionId: params} for every WrappedAction on the group's first point."""
    pts = grp.get("route", {}).get("points", {})
    if not pts:
        return {}
    first = pts[min(pts)] if isinstance(pts, dict) else pts[0]
    tasks = ((first.get("task") or {}).get("params") or {}).get("tasks") or {}
    found = {}
    for t in tasks.values():
        act = ((t.get("params") or {}).get("action") or {})
        if act.get("id"):
            found[act["id"]] = act.get("params") or {}
    return found


def _card_row(brief_md, agency):
    """The comms-table row for one agency, as a list of cells."""
    for line in brief_md.splitlines():
        if line.startswith(f"| {agency} |"):
            return [c.strip() for c in line.strip("|").split("|")]
    return None


def _player(m):
    for g in _groups(m, "plane", "helicopter"):
        for u in g.get("units", {}).values():
            if u.get("skill") in ("Player", "Client"):
                return u
    raise AssertionError("no player unit")


def _radios(unit):
    """{radio index (1-based): {channel: MHz}} as DCS will read it."""
    return {rid: {int(c): float(v)
                  for c, v in (r.get("channels") or {}).items()}
            for rid, r in enumerate((unit.get("Radio") or {}).values(), 1)}


# --- the frequency itself ----------------------------------------------------

@pytest.mark.parametrize("label", [c[0] for c in CASES])
def test_every_ship_in_the_group_is_on_the_frequency_the_card_prints(label, boats):
    m, brief = boats[label]
    want = float(_card_row(brief, "Carrier")[2])
    ships = [u for g in _groups(m, "ship") for u in g.get("units", {}).values()]
    assert ships, "no ships"
    for u in ships:
        f = u.get("frequency")
        assert f and f > 1e6, \
            f"{label}/{u.get('name')}: frequency {f} looks like MHz in a hertz field"
        assert round(f / 1e6, 3) == pytest.approx(want), (
            f"{label}/{u.get('name')}: card says {want} MHz, ship is on "
            f"{f / 1e6:.3f} MHz")


@pytest.mark.parametrize("label", [c[0] for c in CASES])
def test_every_ship_transmits_am(label, boats):
    """The F-14 pilot's ARC-159 is AM ONLY across its whole 225-400 MHz band.
    A carrier on FM is unreachable from that radio no matter how the presets
    are programmed, and pydcs does not write the field at all — see
    missiongen/pydcs_patches.py."""
    m, _ = boats[label]
    ships = [u for g in _groups(m, "ship") for u in g.get("units", {}).values()]
    for u in ships:
        assert u.get("modulation") == 0, (
            f"{label}/{u.get('name')}: modulation {u.get('modulation')!r} "
            f"(0 = AM, 1 = FM, missing = pydcs never wrote it)")


# --- TACAN -------------------------------------------------------------------

def _tacan_hz(channel, band, aa):
    """DCS's own channel->frequency arithmetic, restated here deliberately.

    This is the ONE place this file duplicates pydcs, and it is worth it: the
    bug it catches is `aa=True` on a ship, which leaves the channel number on
    the card looking perfectly right while moving the transmitter to the
    air-to-air band, where an aircraft in T/R hears nothing. The channel field
    alone cannot tell you that; only the frequency can.
    """
    if not aa and band == "X":
        f = (962 + channel - 1) if channel < 64 else (1151 + channel - 64)
    else:
        f = (1088 + channel - 1) if channel < 64 else (1025 + channel - 64)
    return f * 1_000_000


@pytest.mark.parametrize("label", [c[0] for c in CASES])
def test_the_carrier_tacan_is_a_surface_beacon_a_pilot_can_receive(label, boats):
    m, brief = boats[label]
    tac = _card_row(brief, "Carrier")[4]
    act = _actions(_csg(m)).get("ActivateBeacon")
    if tac == "-":
        assert act is None, f"{label}: card prints no TACAN but one is activated"
        return
    assert act, f"{label}: card advertises TACAN {tac} and nothing activates it"
    # system 3 = surface TACAN (receivable in T/R), 4 = air-to-air.
    assert act.get("system") == 3, (
        f"{label}: carrier beacon system {act.get('system')} — 4 is air-to-air, "
        "which a pilot in T/R cannot receive. Ships are surface beacons.")
    assert act.get("bearing") is True, \
        f"{label}: beacon has no bearing, so the pilot gets DME and no radial"
    ch, band, ident = int(act["channel"]), act["modeChannel"], act["callsign"]
    assert act.get("frequency") == _tacan_hz(ch, band, aa=False), (
        f"{label}: beacon frequency {act.get('frequency')} does not match "
        f"channel {ch}{band} on the surface band")


@pytest.mark.parametrize("label", [c[0] for c in CASES])
def test_the_tacan_on_the_card_is_the_tacan_in_the_mission(label, boats):
    m, brief = boats[label]
    tac = _card_row(brief, "Carrier")[4]
    if tac == "-":
        return
    mt = re.fullmatch(r"(\d+)([XY])\s+(\S+)", tac)
    assert mt, f"{label}: TACAN cell {tac!r} is not '<channel><band> <ident>'"
    ch, band, ident = int(mt.group(1)), mt.group(2), mt.group(3)
    act = _actions(_csg(m))["ActivateBeacon"]
    assert (int(act["channel"]), act["modeChannel"], act["callsign"]) \
        == (ch, band, ident), (
            f"{label}: card says {tac}, mission has "
            f"{act['channel']}{act['modeChannel']} {act['callsign']}")
    assert 1 <= ch <= 126, f"{label}: TACAN channel {ch} is outside 1-126"


# --- ICLS / Link 4 / ACLS, in both directions --------------------------------

@pytest.mark.parametrize("label", [c[0] for c in CASES])
def test_the_icls_channel_on_the_card_is_the_one_in_the_mission(label, boats):
    m, brief = boats[label]
    note = _card_row(brief, "Carrier")[5]
    act = _actions(_csg(m)).get("ActivateICLS")
    claimed = re.search(r"ICLS (\d+)", note)
    if claimed is None:
        assert act is None, (
            f"{label}: ICLS channel {act.get('channel')} is active and the card "
            "never mentions it — the pilot has no way to know what to dial")
        return
    assert act, f"{label}: card advertises ICLS {claimed.group(1)}, mission has none"
    assert int(act["channel"]) == int(claimed.group(1)), (
        f"{label}: card says ICLS {claimed.group(1)}, mission activates "
        f"ICLS {act['channel']}")
    assert 1 <= int(act["channel"]) <= 20, (
        f"{label}: ICLS channel {act['channel']} is outside the 1-20 DCS "
        "accepts, so no aircraft can tune it")


@pytest.mark.parametrize("label", [c[0] for c in CASES])
def test_the_link4_frequency_on_the_card_is_the_one_in_the_mission(label, boats):
    m, brief = boats[label]
    note = _card_row(brief, "Carrier")[5]
    act = _actions(_csg(m)).get("ActivateLink4")
    claimed = re.search(r"Link4 (\d+(?:\.\d+)?)", note)
    if claimed is None:
        assert act is None, f"{label}: Link 4 is active and uncarded"
        return
    assert act, f"{label}: card advertises Link4 {claimed.group(1)}, mission has none"
    assert act["frequency"] / 1e6 == pytest.approx(float(claimed.group(1))), (
        f"{label}: card says Link4 {claimed.group(1)}, mission activates "
        f"{act['frequency'] / 1e6}")


@pytest.mark.parametrize("label", [c[0] for c in CASES])
def test_acls_is_claimed_exactly_where_it_is_activated(label, boats):
    m, brief = boats[label]
    note = _card_row(brief, "Carrier")[5]
    act = _actions(_csg(m)).get("ActivateACLS")
    assert bool(act) == ("ACLS" in note), (
        f"{label}: card {'claims' if 'ACLS' in note else 'omits'} ACLS, mission "
        f"{'activates' if act else 'does not activate'} it")


def test_a_hull_with_no_boat_systems_says_so_and_activates_nothing(boats):
    """The 1944 Essex has no TACAN, no ICLS and no landing aids. Blanket
    activation used to advertise all four on her."""
    m, brief = boats["essex/F4U"]
    row = _card_row(brief, "Carrier")
    assert row[4] == "-", f"Essex is carded with TACAN {row[4]}"
    assert "visual recovery" in row[5], \
        f"Essex's note does not say she is a visual-recovery deck: {row[5]!r}"
    acts = _actions(_csg(m))
    for aid in ("ActivateBeacon", "ActivateICLS", "ActivateLink4", "ActivateACLS"):
        assert aid not in acts, f"Essex activates {aid} in 1944"


# --- THE COCKPIT: Casmo's bug ------------------------------------------------

def _advertised(brief):
    """[(channel, MHz, agency)] for every row the card claims a preset for."""
    out = []
    for line in brief.splitlines():
        if not line.startswith("| ") or line.startswith("| Agency"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 6 and cells[3].startswith("CH"):
            out.append((int(cells[3][2:]), float(cells[2]), cells[0]))
    return out


def _programmed(radios, brief):
    """Which radios this mission actually loaded, decided FROM THE FILE.

    The anchor is channel 1 holding the flight frequency. That value is on the
    25 kHz raster (305.725) and no factory table in pydcs carries it — the
    Hornet's untouched COMM2 channel 1 is a round 305, the Tomcat's ARC-182 is
    225. So this identifies a loaded radio without asking presets.py which
    radios it chose, which is the whole point: a test that re-derives the
    module's own rule proves only that the module agrees with itself, and this
    codebase has already paid for that shape twice.
    """
    flight = next((mhz for ch, mhz, ag in _advertised(brief)
                   if ag == "Flight" and ch == 1), None)
    if flight is None:
        return {}
    return {rid: chans for rid, chans in radios.items()
            if chans.get(1) == pytest.approx(flight)}


def _pure_uhf(radios):
    """Radios whose every factory channel sits in 225-400 — a real UHF set."""
    return {rid for rid, chans in radios.items()
            if chans and all(UHF_LO <= v <= UHF_HI for v in chans.values())}


@pytest.mark.parametrize("label", [c[0] for c in CASES])
def test_a_second_uhf_set_is_never_left_on_the_factory_table(label, boats):
    """CASMO'S BUG, STATED DIRECTLY.

    If the jet has two full UHF radios, both must be loaded, because the card
    says "CH2" without saying which radio — and on the Tomcat the second one is
    the RIO's ARC-182, which is the set most crews actually use for boat comms.
    Leaving it factory means channel 2 reads 258.000 and the card is true only
    about a radio the pilot is not keyed to.
    """
    m, brief = boats[label]
    radios = _radios(_player(m))
    prog = _programmed(radios, brief)
    pure = _pure_uhf(radios)
    if not _advertised(brief):
        return                          # airframe has no programmable radio
    assert prog, f"{label}: the card advertises channels and no radio was loaded"
    missing = sorted(pure - set(prog))
    assert not missing, (
        f"{label}: radio(s) {missing} are full UHF sets and were left on the "
        f"factory table while the card advertises presets. Radio "
        f"{missing[0]} channel 2 holds {radios[missing[0]].get(2)}.")


@pytest.mark.parametrize("label", [c[0] for c in CASES])
def test_every_loaded_radio_holds_the_whole_card(label, boats):
    """Not just Mother — every row the card claims, on every radio it loaded."""
    m, brief = boats[label]
    radios = _radios(_player(m))
    prog = _programmed(radios, brief)
    rows = _advertised(brief)
    if not rows:
        return
    assert prog, f"{label}: nothing was loaded"
    for ch, want, agency in rows:
        for rid, chans in prog.items():
            assert chans.get(ch) == pytest.approx(want), (
                f"{label}/{agency}: card says CH{ch} = {want}, radio {rid} "
                f"holds {chans.get(ch)}")
    assert len(rows) >= 3, f"{label}: the card stopped advertising presets"


@pytest.mark.parametrize("label", [c[0] for c in CASES])
def test_the_carrier_is_on_channel_two_of_every_loaded_radio(label, boats):
    """The specific promise, pinned separately from the general one so a
    reordered CHANNEL_ORDER cannot quietly move Mother off CH2 — the number
    the kneeboard, the guide and the pilot all say out loud."""
    m, brief = boats[label]
    row = _card_row(brief, "Carrier")
    if not row[3].startswith("CH"):
        return
    assert row[3] == "CH2", f"{label}: Mother moved to {row[3]}"
    want = float(row[2])
    for rid, chans in _programmed(_radios(_player(m)), brief).items():
        assert chans.get(2) == pytest.approx(want), (
            f"{label}: radio {rid} channel 2 holds {chans.get(2)}, not Mother "
            f"on {want}")


@pytest.mark.parametrize("label", [c[0] for c in CASES])
def test_guard_rides_the_last_channel_of_every_loaded_radio(label, boats):
    m, brief = boats[label]
    guard = float(_card_row(brief, "Guard")[2])
    for rid, chans in _programmed(_radios(_player(m)), brief).items():
        last = max(chans)
        assert chans[last] == pytest.approx(guard), (
            f"{label}: radio {rid} last channel {last} holds {chans[last]}, "
            f"not Guard {guard}")


def test_a_vhf_radio_is_never_given_a_uhf_agency(tmp_path):
    """The reason this module programmed one radio for so long. The A-10C's
    radio 1 is the VHF AM/FM ARC-186 and its radio 3 is VHF FM; only radio 2
    is the UHF ARC-164. Writing 264.425 into a set that cannot tune it would
    be a card that is false in a new way."""
    m, _ = _build(tmp_path, era="modern", aircraft="A_10C", seed=8,
                  bb_carrier=False, home_airbase=None, bb_tanker=True,
                  bb_awacs=True)
    radios = _radios(_player(m))
    for rid, chans in radios.items():
        if not chans:
            continue
        if all(UHF_LO <= v <= UHF_HI for v in chans.values()):
            continue                       # a UHF set — programming it is correct
        assert not any(UHF_LO <= v <= UHF_HI for v in chans.values()), (
            f"A-10C radio {rid} is a VHF set and holds UHF values: "
            f"{ {c: v for c, v in chans.items() if UHF_LO <= v <= UHF_HI} }")


# --- the brief, not just the kneeboard ---------------------------------------

@pytest.mark.parametrize("label", [c[0] for c in CASES])
def test_the_comms_table_header_matches_its_rows(label, boats):
    """A markdown table whose header is narrower than its rows silently drops
    the extra cells when rendered — the notes would be written and invisible,
    which is the original defect wearing a different hat."""
    _, brief = boats[label]
    lines = brief.splitlines()
    i = next(i for i, l in enumerate(lines) if l.startswith("| Agency |"))
    width = len([c for c in lines[i].strip("|").split("|")])
    assert len(lines[i + 1].strip("|").split("|")) == width, \
        f"{label}: the separator row does not match the header width"
    for l in lines[i + 2:]:
        if not l.startswith("| "):
            break
        assert len(l.strip("|").split("|")) == width, (
            f"{label}: header has {width} columns, row has "
            f"{len(l.strip('|').split('|'))}: {l}")


@pytest.mark.parametrize("label", [c[0] for c in CASES])
def test_the_brief_carries_the_boat_card_and_not_only_the_kneeboard(label, boats):
    """Casmo's other sentence. ICLS, Link 4, ACLS and the BRC used to live only
    as gray text on a kneeboard image inside the .miz — nothing the pilot could
    read while planning. The comms table in the brief must carry the notes."""
    m, brief = boats[label]
    row = _card_row(brief, "Carrier")
    assert row is not None and len(row) >= 6, (
        f"{label}: the brief's comms table has no notes column — the boat card "
        f"is invisible until you are strapped in. Row: {row}")
    assert re.search(r"BRC \d{3}", row[5]), (
        f"{label}: the brief never states the BRC, which is the number the "
        f"whole recovery geometry hangs off. Note: {row[5]!r}")
    acts = _actions(_csg(m))
    if "ActivateICLS" in acts:
        assert "ICLS" in row[5], \
            f"{label}: the mission has ICLS and the brief does not say so"
