"""Local corrections to vendored pydcs, applied once at import.

THE BAR FOR ADDING SOMETHING HERE: pydcs writes a .miz that differs from what
the DCS Mission Editor writes for the same setting, and the difference is
reachable from the cockpit. Not "pydcs is awkward" — a missing or wrong field.
Every entry names the editor behavior it is matching and says plainly whether
the effect in DCS is confirmed or only inferred. Delete an entry the moment
pydcs grows the field itself; `tests/test_pydcs_patches.py` fails if a patch
becomes redundant, so this file cannot quietly outlive its reason.

Keeping the corrections here rather than editing `vendor/dcs` is deliberate:
the vendored tree stays byte-identical to upstream, so it can be re-vendored
for a new aircraft without hunting for local edits that a diff would bury.
"""
from dcs.task import Modulation
from dcs.unit import Ship

# ---------------------------------------------------------------------------
# 1. Ships carry no modulation.
#
# Eagle Dynamics' own Supercarrier Operations Guide describes the boat's ATC
# radio as TWO fields: "The ship's ATC radio frequency and modulation are set
# by typing in the desired frequency or selecting the desired modulation
# (AM/FM) from the dropdown menu." pydcs models only the first — `Ship` has a
# `frequency` attribute and `Ship.dict()` emits `frequency` and nothing else.
# There is no modulation key anywhere for ships or ShipGroup in the vendored
# tree.
#
# Modulation is not cosmetic for a carrier. The F-14 pilot's AN/ARC-159 is AM
# ONLY across its entire 225-400 MHz band, so a carrier transmitting FM is
# literally unreachable from the pilot's radio no matter how the presets are
# programmed. Carrier ATC is AM.
#
# HONEST ABOUT THE EVIDENCE: what is confirmed is that the editor writes this
# setting and pydcs does not. What is NOT confirmed is what DCS does with the
# key absent — it may well default to AM, in which case this changes nothing
# observable. This patch is here to make our file match the editor's file, and
# it is not the fix for any reported defect; the radio-preset change in
# presets.py is. If a future test on a real DCS install shows the key is
# ignored entirely, delete this and say so.
_SHIP_DICT = Ship.dict


def _ship_dict_with_modulation(self):
    d = _SHIP_DICT(self)
    d["modulation"] = getattr(self, "modulation", Modulation.AM.value)
    return d


def apply():
    """Idempotent. Called at missiongen import; safe to call again."""
    if getattr(Ship.dict, "_sortie_starter_patch", False):
        return
    _ship_dict_with_modulation._sortie_starter_patch = True
    Ship.dict = _ship_dict_with_modulation


apply()
