"""BB-18: predefined standard comm ladder (comms_plan.json) rendered as a comms card.

Every starter uses the same well-known assignments — Flight 305.725, Tactical 254.325,
AWACS 251.475, Tanker 253.625/39Y, Mother 264.425/71X/ICLS 11/Link4 336, CAP 258.175,
AEW 259.925, Guard 243.000 — so users learn one plan across all missions.

All agency frequencies sit on the real-world 25 kHz channel raster (multiples of
0.025 MHz), so a card reads like an assigned SPINS ladder instead of round
placeholders (251.0, 252.0…). Guard 243.000 is the fixed UHF emergency channel.
The incrementing allocator (extras beyond the ladder) also steps on the raster.
"""
from .resolver import load_json

RASTER_MHZ = 0.025   # UHF/VHF-AM aviation channel spacing (25 kHz)


def snap(mhz: float) -> float:
    """Round a frequency onto the 25 kHz channel raster."""
    return round(round(mhz / RASTER_MHZ) * RASTER_MHZ, 3)


class CommsPlan:
    def __init__(self):
        self.plan = load_json("comms_plan")
        self.entries = []          # (agency, callsign, freq, tacan, notes)
        self._uhf = 265.225        # fallback allocator base, above the ladder (on raster)
        self._uhf_step = 0.825     # 33 x 25 kHz — realistic separation, stays off round values
        self._tacan = 40
        self._farp = snap(self.plan["farp_base"])
        self.add("Guard", "-", f"{snap(self.plan['guard']):.3f}", "-", "monitored")

    # --- predefined ladder ------------------------------------------------
    def freq(self, key: str) -> float:
        v = self.plan[key]
        return snap(v["freq"] if isinstance(v, dict) else v)

    def cfg(self, key: str) -> dict:
        d = dict(self.plan[key])
        if "freq" in d:
            d["freq"] = snap(d["freq"])
        return d

    def next_farp(self) -> float:
        f = snap(self._farp)
        self._farp += 0.25          # 0.25 MHz = 10 x 25 kHz, stays on raster
        return f

    # --- fallback allocator (extras beyond the standard ladder) ------------
    def next_uhf(self) -> float:
        f = snap(self._uhf)
        self._uhf += self._uhf_step
        return f

    def next_tacan(self) -> str:
        c = f"{self._tacan}Y"
        self._tacan += 1
        return c

    def add(self, agency, callsign, freq, tacan="-", notes=""):
        self.entries.append((agency, callsign, freq, tacan, notes))

    def card(self) -> str:
        lines = ["COMMS / NAV CARD (standard ladder)", "-" * 48,
                 f"{'AGENCY':<16}{'C/S':<14}{'FREQ':<9}{'TACAN':<7}NOTES"]
        for a, c, f, t, n in self.entries:
            lines.append(f"{a:<16}{c:<14}{f:<9}{t:<7}{n}")
        return "\n".join(lines)
