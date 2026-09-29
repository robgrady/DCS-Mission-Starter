"""The comm plan as a TABLE the pilot can overwrite.

Every starter ships the same standard ladder (comms_plan.json) so a pilot
learns ONE plan. Squadrons already have one of their own, and a card that
argues with the squadron SOP loses. So the ladder is now a table with a
default column and a "this mission" column: leave it alone and nothing
changes, byte for byte; overwrite a row and the whole pipeline follows —
the tanker's radio, the AWACS's radio, the boat's radio (in hertz), the
player's cockpit presets, the card, the kneeboard and the DTC page. There is
one entry point for a frequency (CommsPlan.freq / .cfg) and the override
lives there, so nothing downstream can print a number the world does not
hold.

THREE KINDS OF ROW, and the table says which is which:

  generated   an agency this mission builds — editable
  engine      a row the engine owns: Guard is 243.000 by regulation and is
              never editable; Flight is editable but its CHANNEL is not,
              because DCS loads the group frequency on CH 1 whatever we do
  absent      an agency this mission does not build (no tanker, no boat) —
              shown so the plan is complete, but an override there is a
              no-op and the table says so instead of pretending

WHAT IS REFUSED, and why each rule exists:
  - Guard                 fixed by regulation; a plan that moves it is wrong
  - off the 25 kHz raster a real radio cannot tune 253.630; the pilot would
                          dial the nearest channel and the card would be a lie
  - out of band           our ladder is UHF 225-400. A frequency the jet's
                          radios cannot reach is refused up front (the
                          airframe's own bands widen this: a Mustang's VHF
                          flight frequency is fine for a Mustang)
  - an unknown row        typo'd keys vanish silently otherwise (the same
                          fail-loud rule Recipe.from_dict applies)
  - two rows, one freq    WARNED, not refused: co-channel is legal, sometimes
                          intended (tanker and AWACS on one net), often a slip

Channels are not editable. They are the ladder's shape (presets.CHANNEL_ORDER)
and the reason the plan is learnable; a squadron that wants Texaco on CH 2 is
asking for a different ladder, not a different tanker frequency, and that is
a bigger change than a table cell. Frequencies are what SOPs actually differ
on.
"""
from __future__ import annotations

import math

from .comms import snap
from .presets import CHANNEL_ORDER, UHF_HI, UHF_LO, _uhf_radio_ids
from .resolver import load_json

_CH = dict(CHANNEL_ORDER)

# key in comms_plan.json, agency label on the card, the recipe flag that makes
# the agency exist in a mission (None = every mission has it), one line of
# what it is. Order is card order.
LADDER = [
    ("flight_common", "Flight", None,
     "Your flight's working frequency. DCS loads it on CH 1 of the main radio."),
    ("carrier", "Carrier", "bb_carrier",
     "Mother — the boat's tower and approach."),
    ("awacs", "AWACS", "bb_awacs",
     "Overlord — the picture."),
    ("tanker", "Tanker", "bb_tanker",
     "Texaco — the gas."),
    ("angel", "Plane guard", "bb_carrier",
     "Angel — the plane-guard helo, carrier flight ops."),
    ("cap", "CAP", "carrier_cap",
     "The air wing's CAP common."),
    ("tactical", "Tactical", None,
     "Inter-flight coordination; no station answers here."),
    ("aew", "AEW", "carrier_aew",
     "The E-2's net. Takes CH 3 when there is no AWACS."),
    ("guard", "Guard", None,
     "243.000, the UHF emergency channel. Fixed by regulation."),
]

LOCKED = {"guard"}            # never editable
ENGINE = {"guard", "flight_common"}   # rows the engine owns (see module doc)
KEYS = [k for k, *_ in LADDER]
AGENCY_OF = {k: a for k, a, *_ in LADDER}
KEY_OF = {a: k for k, a, *_ in LADDER}


def _plan():
    return load_json("comms_plan")


def default_mhz(key: str) -> float:
    v = _plan()[key]
    return snap(v["freq"] if isinstance(v, dict) else v)


def channel_for(key: str, has_awacs: bool = True):
    """The preset channel this row rides, or None (Guard = last channel)."""
    if key == "guard":
        return "last"
    if key == "aew" and not has_awacs:
        return 3
    return _CH.get(AGENCY_OF[key])


def unit_type_for(aircraft: str | None):
    """The pydcs airframe class for a recipe aircraft key, or None. Unknown
    keys are None here — Recipe/builder report those properly; this module
    only needs the radios."""
    if not aircraft:
        return None
    from .resolver import resolve, UnknownUnitError
    for mod in ("planes", "helicopters"):
        try:
            return resolve(f"{mod}.{aircraft}")
        except UnknownUnitError:
            continue
    try:
        from .pending import get_pending
        return get_pending(aircraft)[0]
    except Exception:
        return None


def _bands(unit_type) -> list[tuple[float, float]]:
    if unit_type is None:
        return []
    from .saydo import type_bands
    return type_bands(unit_type)


def radios_for(unit_type) -> list[dict]:
    """The UHF sets presets.apply() will program on this airframe."""
    pr = getattr(unit_type, "panel_radio", None) or {}
    out = []
    for rid in _uhf_radio_ids(pr):
        chans = pr[rid].get("channels") or {}
        out.append({"id": rid, "channels": len(chans), "last": max(chans) if chans else None})
    return out


def holds(radios: list[dict], channel) -> bool:
    """Can some programmed radio hold this channel? (Guard rides `last`.)"""
    if not radios:
        return False
    if channel == "last" or channel is None:
        return channel == "last"
    return any(r["channels"] >= channel and channel != r["last"] for r in radios)


def rows(unit_type=None, present: dict | None = None) -> list[dict]:
    """The table. `present` is the recipe's flag values ({flag: bool}); with
    none given every agency is treated as present."""
    present = present or {}
    radios = radios_for(unit_type)
    has_awacs = bool(present.get("bb_awacs", True))
    out = []
    for key, agency, flag, blurb in LADDER:
        exists = True if flag is None else bool(present.get(flag, True))
        ch = channel_for(key, has_awacs)
        if key in LOCKED:
            kind = "engine"
        elif not exists:
            kind = "absent"
        elif key in ENGINE:
            kind = "engine"
        else:
            kind = "generated"
        out.append({
            "key": key, "agency": agency, "channel": ch, "default": default_mhz(key),
            "kind": kind, "editable": key not in LOCKED, "needs": flag, "blurb": blurb,
            "held": holds(radios, ch) if exists else False,
        })
    return out


def _fmt(v: float) -> str:
    return f"{v:.3f}"


def validate(overrides, unit_type=None) -> dict:
    """Check a {key: MHz} override map. Returns
    {"ok": bool, "clean": {key: mhz}, "errors": [{key, msg}], "warnings": [...]}.

    `clean` holds only real changes (an override equal to the default is a
    no-op and is dropped, so a share link never carries dead weight)."""
    errors, warnings, clean = [], [], {}
    if overrides is None:
        return {"ok": True, "clean": {}, "errors": [], "warnings": []}
    if not isinstance(overrides, dict):
        return {"ok": False, "clean": {}, "warnings": [],
                "errors": [{"key": None, "msg": "comms must be a table of {row: MHz}."}]}
    bands = _bands(unit_type)
    guard = default_mhz("guard")

    for key, raw in overrides.items():
        if key not in KEYS:
            errors.append({"key": key, "msg": f"{key!r} is not a row of the comm plan. "
                                              f"Rows: {', '.join(KEYS)}."})
            continue
        if key in LOCKED:
            errors.append({"key": key, "msg": f"{AGENCY_OF[key]} {_fmt(guard)} is fixed by "
                                              f"regulation and cannot be moved."})
            continue
        if raw is None or raw == "":
            continue                       # an emptied cell = back to default
        try:
            v = float(raw)
        except (TypeError, ValueError):
            errors.append({"key": key, "msg": f"{AGENCY_OF[key]}: {raw!r} is not a frequency."})
            continue
        if isinstance(raw, bool) or not math.isfinite(v):
            errors.append({"key": key, "msg": f"{AGENCY_OF[key]}: {raw!r} is not a frequency."})
            continue
        s = snap(v)
        if abs(s - v) > 1e-6:
            errors.append({"key": key, "msg": f"{AGENCY_OF[key]}: {v:.3f} is off the 25 kHz "
                                              f"raster — a radio cannot tune it. Nearest: {_fmt(s)}."})
            continue
        in_uhf = UHF_LO <= s < UHF_HI
        in_own = any(lo <= s <= hi for lo, hi in bands)
        if not (in_uhf or in_own):
            errors.append({"key": key, "msg": f"{AGENCY_OF[key]}: {_fmt(s)} is outside UHF "
                                              f"{UHF_LO:.0f}-{UHF_HI:.0f}"
                                              + (" and outside this aircraft's radios." if bands else ".")})
            continue
        if abs(s - guard) < 1e-6:
            errors.append({"key": key, "msg": f"{AGENCY_OF[key]}: {_fmt(guard)} is Guard."})
            continue
        if abs(s - default_mhz(key)) < 1e-6:
            continue                       # no change: not an override
        clean[key] = s

    # Co-channel across the EFFECTIVE ladder (overrides + defaults for the rest).
    eff = {k: clean.get(k, default_mhz(k)) for k in KEYS if k not in LOCKED}
    seen: dict[float, str] = {}
    for k in KEYS:
        if k not in eff:
            continue
        f = eff[k]
        if f in seen and (k in clean or seen[f] in clean):
            a, b = AGENCY_OF[seen[f]], AGENCY_OF[k]
            warnings.append({"key": k, "msg": f"{a} and {b} share {_fmt(f)} — co-channel. "
                                              f"Legal, but check it is what you meant."})
        else:
            seen.setdefault(f, k)
    return {"ok": not errors, "clean": clean, "errors": errors, "warnings": warnings}


def describe(clean: dict) -> list[str]:
    """One line per override, for the build stats and the API response."""
    return [f"{AGENCY_OF[k]} {_fmt(v)} (default {_fmt(default_mhz(k))})"
            for k, v in clean.items() if k in AGENCY_OF]
