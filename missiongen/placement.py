"""Airfield placement discipline: runways and movement areas stay CLEAR.

The rule every real airfield lives by — nothing parks on the runway or the
taxi routes. pydcs terrain data gives us runway *headings* but not geometry,
so we model each runway as a keep-out corridor through the airport reference
point (which DCS puts on/near the runway): generous half-length to cover the
longest strips, wide half-width to absorb runway + shoulders + the parallel
taxiway + magnetic-variation error in the published heading.

Placement strategy (defense in depth):
1. PREFER positions derived from known-safe geometry (parking stands are
   surveyed apron locations; anything within a stand's own footprint is off
   the movement area).
2. PUSH free-placed clusters to the side of the ramp AWAY from the runway
   axis, never at a random bearing.
3. VALIDATE every free-placed object against the corridors and occupied
   stands; reject and retry (or drop) violators.
"""
import math
from dcs import mapping

RUNWAY_HALF_LEN = 1900.0    # covers 12,000 ft runways + overrun
RUNWAY_HALF_WIDTH = 150.0   # runway + shoulders + parallel taxiway + magvar slack
STAND_CLEARANCE = 40.0      # don't drop free objects onto a parking stand


class AirfieldKeepOut:
    """Keep-out geometry for one airfield: runway corridors + parking stands."""

    def __init__(self, airport):
        self.airport = airport
        self.corridors = []          # ((ax, ay), (bx, by)) per runway
        p = airport.position
        for rw in airport.runways:
            for hdg_deg in (rw.main.heading,):   # main+opposite share one axis
                h = math.radians(hdg_deg)
                dx, dy = math.cos(h), math.sin(h)
                self.corridors.append((
                    (p.x - dx * RUNWAY_HALF_LEN, p.y - dy * RUNWAY_HALF_LEN),
                    (p.x + dx * RUNWAY_HALF_LEN, p.y + dy * RUNWAY_HALF_LEN)))
        if not self.corridors:       # data gap: treat the reference point as hot
            self.corridors.append(((p.x, p.y), (p.x, p.y)))
        self._stands = [(s.position.x, s.position.y) for s in airport.parking_slots]

    @staticmethod
    def _seg_dist(px, py, a, b):
        ax, ay = a; bx, by = b
        vx, vy = bx - ax, by - ay
        wx, wy = px - ax, py - ay
        seg2 = vx * vx + vy * vy
        t = 0.0 if seg2 == 0 else max(0.0, min(1.0, (wx * vx + wy * vy) / seg2))
        cx, cy = ax + t * vx, ay + t * vy
        return math.hypot(px - cx, py - cy)

    def dist_to_runway(self, pos) -> float:
        return min(self._seg_dist(pos.x, pos.y, a, b) for a, b in self.corridors)

    def runway_axis_heading(self) -> float:
        """Heading (deg) of the primary runway axis."""
        return self.airport.runways[0].main.heading if self.airport.runways else 0.0

    def on_stand(self, pos, clearance=STAND_CLEARANCE) -> bool:
        return any(math.hypot(pos.x - sx, pos.y - sy) < clearance
                   for sx, sy in self._stands)

    def clear(self, pos, margin=0.0, avoid_stands=True) -> bool:
        """True if pos is safely off the movement area (and off stands)."""
        if self.dist_to_runway(pos) < RUNWAY_HALF_WIDTH + margin:
            return False
        if avoid_stands and self.on_stand(pos):
            return False
        return True

    def away_side_bearing(self, from_pos) -> float:
        """Bearing (deg) perpendicular to the runway axis, pointing from the
        runway line toward from_pos — i.e. deeper into the safe side."""
        axis = math.radians(self.runway_axis_heading())
        p = self.airport.position
        # cross product sign tells which side of the axis from_pos sits on
        vx, vy = math.cos(axis), math.sin(axis)
        wx, wy = from_pos.x - p.x, from_pos.y - p.y
        side = 1.0 if (vx * wy - vy * wx) >= 0 else -1.0
        return (self.runway_axis_heading() + side * 90.0) % 360.0

    def find_clear(self, anchor, radius_lo, radius_hi, rng, margin=0.0,
                   avoid_stands=True, tries=24, prefer_bearing=None):
        """Sample positions around anchor until one clears the keep-outs.
        Returns a mapping.Point or None. prefer_bearing biases the first
        attempts toward a known-good direction (e.g. the away side)."""
        terrain = anchor._terrain
        for i in range(tries):
            if prefer_bearing is not None and i < tries // 2:
                brg = (prefer_bearing + rng.uniform(-55, 55)) % 360
            else:
                brg = rng.uniform(0, 360)
            r = rng.uniform(radius_lo, radius_hi)
            b = math.radians(brg)
            pos = mapping.Point(anchor.x + r * math.cos(b),
                                anchor.y + r * math.sin(b), terrain)
            if self.clear(pos, margin=margin, avoid_stands=avoid_stands):
                return pos
        return None
