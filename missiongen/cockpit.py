"""Cockpit facts we have VERIFIED, by airframe, with where each one came from.

WHY THIS FILE IS SO SHORT
-------------------------
The Mission Editor can test a cockpit — "is COMM1 on 251.9?", "is the gear
handle down?" — through `c_cockpit_param_*` and `c_argument_in_range`. Both
take names and numbers that differ per module and are documented nowhere
official. Get one wrong and the mission waits forever for a switch that is
never read, which is a say/do gap of the worst kind: the brief promises a
check the file cannot perform.

So the rule here is provenance or nothing. An entry exists only when a
shipping mission or a first-hand source showed the exact name working. The
expert missions we dissected are the source for most of it:

  * F-4E: Fulda 1979 M1–M6 gate every handoff on `COMM_FREQ` / `AUX_FREQ`
    and read the gear handle, engines and IFF drums by argument. Read from
    the trigger tables, 13 gates a mission.
  * F-16C: ED forum thread 273747 shows `COMM1_FREQ` / `COMM2_FREQ` working,
    with the author's warning to keep values to one decimal.

Everything else — F-14, F/A-18C included — is UNVERIFIED and deliberately
absent. `radio_param()` returns None and the caller must say so in the brief
rather than install a gate that will never fire. When someone runs
`return list_cockpit_params()` in the Lua console on the module and sends
the names back, they go here with the source recorded.
"""
from __future__ import annotations

RADIO_PARAMS = {
    "F-4E-45MC": {
        "comm1": "COMM_FREQ", "comm2": "AUX_FREQ",
        "source": "Fulda 1979 MSN01–06 trigger tables (Heatblur F-4E), "
                  "c_cockpit_param_equal_to on COMM_FREQ / AUX_FREQ",
    },
    "F-16C_50": {
        "comm1": "COMM1_FREQ", "comm2": "COMM2_FREQ",
        "source": "ED forum topic 273747 (F-16C radio-frequency trigger demo)",
    },
}

# c_argument_in_range facts, same rule. Ranges are inclusive [lo, hi].
ARGUMENTS = {
    "F-4E-45MC": {
        "gear_up":   {"argument": 5, "range": (0.0, 0.3)},
        "gear_down": {"argument": 5, "range": (0.7, 1.0)},
        "source": "Fulda 1979 MSN02 'AIRBORNE' gate (argument 5 in 0–0.3 = "
                  "gear handle up); down range is the mirror and UNTESTED",
    },
}

# Frequency text the Editor compares against. The F-16 thread says values
# with more than one decimal misbehave; Fulda's gates are all one decimal.
# We do not truncate a 25 kHz frequency to make it fit — we use the RANGE
# condition instead (see gates.py), and this helper only formats for people.
def freq_text(mhz: float) -> str:
    s = f"{mhz:.3f}".rstrip("0").rstrip(".")
    return s if "." in s else s + ".0"


def radio_param(aircraft: str, radio: str = "comm1") -> str | None:
    """The cockpit parameter that holds this radio's tuned frequency, or None."""
    return (RADIO_PARAMS.get(aircraft) or {}).get(radio)


def supports_readback(aircraft: str) -> bool:
    return radio_param(aircraft) is not None


def argument(aircraft: str, key: str) -> dict | None:
    return (ARGUMENTS.get(aircraft) or {}).get(key)


def provenance(aircraft: str) -> str:
    return (RADIO_PARAMS.get(aircraft) or {}).get("source", "")
