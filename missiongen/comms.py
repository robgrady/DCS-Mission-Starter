"""BB-18: predefined standard comm ladder (comms_plan.json) rendered as a comms card.

Every starter uses the same well-known assignments — Flight 305.00, Tactical 254.00,
AWACS 251.00, Tanker 253.00/39Y, Mother 264.00/71X/ICLS 11/Link4 336, CAP 258.00,
AEW 259.00, Guard 243.00 — so users learn one plan across all missions. The
incrementing allocator remains only as a fallback for extras beyond the ladder.
"""
from .resolver import load_json


class CommsPlan:
    def __init__(self):
        self.plan = load_json("comms_plan")
        self.entries = []          # (agency, callsign, freq, tacan, notes)
        self._uhf = 265.0          # fallback allocator, above the ladder
        self._tacan = 40
        self._farp = self.plan["farp_base"]
        self.add("Guard", "-", f"{self.plan['guard']:.2f}", "-", "monitored")

    # --- predefined ladder ------------------------------------------------
    def freq(self, key: str) -> float:
        v = self.plan[key]
        return v["freq"] if isinstance(v, dict) else v

    def cfg(self, key: str) -> dict:
        return self.plan[key]

    def next_farp(self) -> float:
        f = round(self._farp, 2)
        self._farp += 0.25
        return f

    # --- fallback allocator (extras beyond the standard ladder) ------------
    def next_uhf(self) -> float:
        f = round(self._uhf, 2)
        self._uhf += 1.0
        return f

    def next_tacan(self) -> str:
        c = f"{self._tacan}Y"
        self._tacan += 1
        return c

    def add(self, agency, callsign, freq, tacan="-", notes=""):
        self.entries.append((agency, callsign, freq, tacan, notes))

    def card(self) -> str:
        lines = ["COMMS / NAV CARD (standard ladder)", "-" * 46,
                 f"{'AGENCY':<16}{'C/S':<12}{'FREQ':<9}{'TACAN':<7}NOTES"]
        for a, c, f, t, n in self.entries:
            lines.append(f"{a:<16}{c:<12}{f:<9}{t:<7}{n}")
        return "\n".join(lines)
