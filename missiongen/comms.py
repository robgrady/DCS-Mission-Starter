"""BB-18: non-conflicting frequency & TACAN plan, rendered as a comms card."""


class CommsPlan:
    def __init__(self):
        self.entries = []          # (agency, callsign, freq, tacan, notes)
        self._uhf = 251.0
        self._tacan = 39

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
        lines = ["COMMS / NAV CARD", "-" * 46,
                 f"{'AGENCY':<16}{'C/S':<12}{'FREQ':<9}{'TACAN':<7}NOTES"]
        for a, c, f, t, n in self.entries:
            lines.append(f"{a:<16}{c:<12}{f:<9}{t:<7}{n}")
        return "\n".join(lines)
