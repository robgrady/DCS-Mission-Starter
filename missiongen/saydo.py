"""The say/do check, turned on ourselves.

WHY
---
Every gap in the expert-mission ledger (docs/technique_dossier.html) was a
number a human copied from the world into the paperwork: a frequency in the
brief that no radio held, a departure time two hours off the mission clock,
a callsign the story uses and the file does not. We generate both the world
and the paperwork, so we can recompute the paperwork from the world after
the build and refuse to ship a disagreement — the one advantage a generator
has over the best author in the category, and the whole premise of Bet 1.

WHAT IT CHECKS
--------------
  comms     every frequency on the comms card is held by something in the
            file: a player radio preset, a group's frequency, a carrier's
            frequency, or a field's ATC radio.
  clock     the start time the brief prints is the mission's start time.
  callsign  the name the brief calls the flight is the name DCS will use;
            when it is not (DCS's callsign table is fixed and ours is not),
            the brief must SAY which name ATC and the AI will use.
  timing    every ETA the card prints is the ETA on that waypoint in the
            file, and both agree with the mission clock; the anchor time is
            printed in the brief.

Each finding is one line, prefixed "SAY/DO:", appended to the build
warnings so it reaches the API response and the test suite. Findings are
facts about THIS mission, never inferred from a template.
"""
from __future__ import annotations

import re

PREFIX = "SAY/DO:"


def _mhz(v) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return round(f / 1e6, 3) if f > 1e5 else round(f, 3)


def known_frequencies(m, player_group=None) -> set[float]:
    """Every frequency the FILE can be heard on, in MHz."""
    known = set()
    for coal in m.coalition.values():
        for country in coal.countries.values():
            for g in (list(country.plane_group) + list(country.helicopter_group)
                      + list(country.ship_group) + list(country.vehicle_group)):
                f = _mhz(getattr(g, "frequency", None))
                if f:
                    known.add(f)
                for u in getattr(g, "units", []):
                    for radio in (getattr(u, "radio", None) or {}).values():
                        for v in (radio.get("channels") or {}).values():
                            f = _mhz(v)
                            if f:
                                known.add(f)
    # Airfield ATC radios come from the terrain, not from a group.
    try:
        for ap in m.terrain.airports.values():
            atc = getattr(ap, "atc_radio", None)
            if atc:
                for hz in (atc.uhf_hz, atc.vhf_high_hz, atc.vhf_low_hz):
                    f = _mhz(hz)
                    if f:
                        known.add(f)
    except Exception:
        pass
    return known


NOT_TUNABLE = "not tunable in this aircraft"


def radio_bands(group) -> list[tuple[float, float]]:
    """The bands the player's radios can reach, from their factory channels.

    A radio's default channel list spans its band (the P-51's SCR-522 sits
    100–156, an ARC-164 225–400). A generous margin covers the ends the
    template never used. No radios -> no bands -> nothing is tunable, which
    is the honest answer for an airframe the Editor cannot program.
    """
    bands = []
    if group is None:
        return bands
    for u in getattr(group, "units", []):
        for radio in (getattr(u, "radio", None) or {}).values():
            vals = [float(v) for v in (radio.get("channels") or {}).values()
                    if isinstance(v, (int, float))]
            if vals:
                bands.append((min(vals) - 20.0, max(vals) + 40.0))
    return bands


def type_bands(unit_type) -> list[tuple[float, float]]:
    """Same as radio_bands, from the airframe's factory template (pre-build)."""
    bands = []
    pr = getattr(unit_type, "panel_radio", None) or {}
    for radio in pr.values():
        vals = [float(v) for v in (radio.get("channels") or {}).values()
                if isinstance(v, (int, float))]
        if vals:
            bands.append((min(vals) - 20.0, max(vals) + 40.0))
    return bands


def in_band_flight_freqs(unit_type, flight_mhz: float, tactical_mhz: float):
    """(flight, tactical) this airframe can actually tune, or the inputs.

    A VHF-only Mustang or MiG-21 given our UHF flight frequency has a wingman
    it cannot talk to and a card that lies about it. When the ladder's value
    is outside every band the jet has, fall back to the module's own factory
    channels 1 and 2 — the frequencies its manual expects — and say so.
    """
    bands = type_bands(unit_type)
    if not bands:
        return flight_mhz, tactical_mhz, False
    if any(lo <= flight_mhz <= hi for lo, hi in bands):
        return flight_mhz, tactical_mhz, False
    pr = getattr(unit_type, "panel_radio", None) or {}
    widest = max(pr.values(), key=lambda r: len(r.get("channels") or {}))
    ch = widest.get("channels") or {}
    keys = sorted(ch)
    f1 = float(ch[keys[0]]) if keys else flight_mhz
    f2 = float(ch[keys[1]]) if len(keys) > 1 else f1
    return f1, f2, True


def mark_unreachable(comms, group) -> list[str]:
    """Annotate card entries the player's radios cannot tune. Returns them.

    Found on the first run of this check: a P-51D card listed Guard 243.0
    and a UHF tactical frequency — a VHF-only Mustang. The card is right
    about the world and wrong about the jet; the note makes it right about
    both, and the check below treats the note as the disclosure it is.
    """
    bands = radio_bands(group)
    if not bands or comms is None:
        return []
    marked = []
    for i, (agency, cs_, fq, tacan, note) in enumerate(list(comms.entries)):
        f = _mhz(fq)
        if f is None:
            continue
        if not any(lo <= f <= hi for lo, hi in bands):
            note = (note + " · " if note else "") + NOT_TUNABLE
            comms.entries[i] = (agency, cs_, fq, tacan, note)
            marked.append(f"{agency} {f:.3f}")
    return marked


def check_comms(m, comms, player_group=None) -> list[str]:
    out = []
    if comms is None:
        return out
    known = known_frequencies(m, player_group)
    for agency, cs_, fq, _tacan, note in getattr(comms, "entries", []):
        f = _mhz(fq)
        if f is None:
            continue
        if NOT_TUNABLE in (note or ""):
            continue                      # disclosed on the card itself
        if not any(abs(f - k) < 0.003 for k in known):
            out.append(f"{PREFIX} comms card lists {agency} ({cs_}) on {f:.3f} "
                       f"but nothing in the mission holds that frequency")
    return out


def mission_clock(m) -> str | None:
    """The mission's start time as HH:MM, from whatever pydcs holds."""
    st = getattr(m, "start_time", None)
    if st is None:
        return None
    if hasattr(st, "hour"):
        return f"{st.hour:02d}:{st.minute:02d}"
    try:
        secs = int(st)
        return f"{(secs // 3600) % 24:02d}:{(secs % 3600) // 60:02d}"
    except (TypeError, ValueError):
        return None


def check_clock(m, brief_text: str, said_hhmm: str | None) -> list[str]:
    """The clock the PAPERWORK prints vs the clock the FILE starts.

    `said_hhmm` is what the brief derives its DTG from (brief.HOUR — a twin
    of builder.TIME_PRESETS, which is exactly the kind of pair this check
    exists to keep honest). The in-game text must also print it: a pilot
    reads the clock before he reads the map.
    """
    out = []
    actual = mission_clock(m)
    if not said_hhmm or not actual:
        return out
    if said_hhmm != actual:
        out.append(f"{PREFIX} brief says start {said_hhmm} but the mission "
                   f"clock starts {actual}")
    if brief_text and actual not in brief_text:
        out.append(f"{PREFIX} the in-game brief does not print the start time "
                   f"{actual}")
    return out


def dcs_callsign(player_group) -> str | None:
    """The name DCS's own ATC and AI will use for the player's flight."""
    if player_group is None or not getattr(player_group, "units", None):
        return None
    u = player_group.units[0]
    try:
        western = u.callsign_is_western
        western = western() if callable(western) else western
        if western:
            # pydcs stores the full "Enfield11"; the root is the word.
            name = (u.callsign_dict or {}).get("name") or ""
            return name or None
        return str(u.callsign) if u.callsign is not None else None
    except Exception:
        return None


def voiced_name(flight_name: str | None) -> str:
    """'Gypsy 1' -> 'Gypsy'; a bort number ('231') is the whole name."""
    fn = (flight_name or "").strip()
    if fn.isdigit():
        return fn
    return re.sub(r"\s*\d+$", "", fn).strip()


def check_callsign(player_group, flight_name: str | None, brief_text: str) -> list[str]:
    """Voiced name vs the name in the file — and whether the brief admits it."""
    out = []
    if not flight_name or player_group is None:
        return out
    stock = dcs_callsign(player_group)
    if not stock:
        return out
    voiced = voiced_name(flight_name)
    if not voiced:
        return out
    stock_root = re.sub(r"\d+$", "", stock).strip()
    if voiced.lower() == stock_root.lower():
        return out
    if stock_root.lower() not in (brief_text or "").lower():
        out.append(f"{PREFIX} the brief calls the flight '{voiced}' but DCS ATC "
                   f"and AI will say '{stock_root}' and the brief does not say so")
    return out


def known_issues(player_group, flight_name: str | None, extra: list[str] | None = None,
                 unreachable: list[str] | None = None, aircraft: str = "") -> list[str]:
    """The 'what DCS will get wrong' lines, for the brief. True, per mission."""
    lines = []
    if unreachable:
        lines.append(f"Your {aircraft or 'aircraft'} cannot tune "
                     f"{', '.join(unreachable)} — those card entries are for "
                     f"the rest of the package, not for you.")
    stock = dcs_callsign(player_group)
    voiced = voiced_name(flight_name)
    stock_root = re.sub(r"\d+$", "", stock or "").strip()
    if stock_root and voiced and stock_root.lower() != voiced.lower():
        lines.append(f"DCS ATC and AI wingmen will call you '{stock_root}', "
                     f"not '{voiced}' — the sim's callsign table is fixed. The "
                     f"paperwork uses {voiced}; answer to both.")
    lines += [
        "AI wingmen hold formation loosely, cannot fly an overhead break, and "
        "rejoin slowly after a tanker — give them time before pressing on.",
        "AI tankers hold their track and altitude exactly; your approach is "
        "the variable.",
    ]
    for e in (extra or []):
        if e:
            lines.append(e)
    return lines


def check_timing(m, player_group, timing, brief_text: str) -> list[str]:
    """The card's ETAs vs the file's ETAs vs the mission clock.

    Three numbers that must agree: the ETA the card prints for a point, the
    ETA written on that waypoint in the file, and the clock time the two
    imply against the mission's start. They come from one plan — but a
    renderer edit, a waypoint renamed, or a start time moved after the plan
    was made would silently break the agreement, and this is what catches it.
    """
    out = []
    if not timing or player_group is None:
        return out
    rows = {t["to"]: t for t in timing.get("rows", [])}
    if not rows:
        return out
    st = getattr(m, "start_time", None)
    start_s = (st.hour * 3600 + st.minute * 60 + st.second) if hasattr(st, "hour") else None
    seen = set()
    for p in getattr(player_group, "points", []) or []:
        t = rows.get(getattr(p, "name", None))
        if t is None:
            continue
        seen.add(t["to"])
        if int(getattr(p, "ETA", 0) or 0) != int(t["eta_s"]):
            out.append(f"{PREFIX} the card says {t['to']} at {t['eta']} "
                       f"(+{t['eta_s']} s) but the waypoint in the file carries "
                       f"ETA {int(getattr(p, 'ETA', 0) or 0)} s")
        if getattr(p, "ETA_locked", False):
            out.append(f"{PREFIX} the player's {t['to']} waypoint is ETA-locked; "
                       f"DCS does not fly the player and the lock is a lie")
        if start_s is not None:
            from .timing import hhmmss
            clock = hhmmss(start_s + int(t["eta_s"]))
            if clock != t["eta"]:
                out.append(f"{PREFIX} the card prints {t['to']} at {t['eta']} but "
                           f"the mission clock puts that waypoint at {clock}")
    for name in rows:
        if name not in seen:
            out.append(f"{PREFIX} the card times {name} but no waypoint in the "
                       f"file is named {name}")
    anchor_clock = timing.get("anchor_clock")
    if anchor_clock and timing.get("anchor") != "takeoff" and brief_text \
            and anchor_clock not in brief_text:
        out.append(f"{PREFIX} the anchor {timing.get('anchor')} {anchor_clock} "
                   f"is not printed in the in-game brief")
    return out


def run(m, comms, player_group, flight_name, recipe, timing=None,
        said_hhmm: str | None = None) -> list[str]:
    """All checks. Never raises — a failed check is a finding, not a crash.

    `said_hhmm` overrides the preset clock the paperwork would otherwise
    claim — set when a timing anchor moved the mission start on purpose.
    """
    findings = []
    try:
        text = m.description_text() or ""
    except Exception:
        text = ""
    from .brief import HOUR
    said = said_hhmm or f"{HOUR.get(getattr(recipe, 'time_of_day', None), '12')}:00"
    for fn, args in ((check_comms, (m, comms, player_group)),
                     (check_clock, (m, text, said)),
                     (check_callsign, (player_group, flight_name, text)),
                     (check_timing, (m, player_group, timing, text))):
        try:
            findings += fn(*args)
        except Exception as exc:                          # pragma: no cover
            findings.append(f"{PREFIX} check {fn.__name__} could not run: {exc}")
    return findings
