"""Player flight plan: WP1 -> IP -> TARGET -> home.

WHY THIS MODULE EXISTS, AND WHAT THE NORTH STAR ACTUALLY SAID
-------------------------------------------------------------
The product rule has always been quoted as "never place player waypoints", and
it is written into the user guide, the DTC module, the graphics layer and the
airspace overlay. That shorthand was never the principle. The principle is
"we set the stage, you write the play" — do not TELL the pilot how to fly the
mission he did not ask us to plan.

An unrequested route breaks that. A route the user ticked a box for does not:
he asked. So `bb_route` is **off by default**, every existing share link keeps
generating exactly what it generated before, and nobody receives waypoints they
did not choose.

The rule stands everywhere it stood. What changed is that it is now a default
rather than a prohibition.

WHAT MAKES A ROUTE, AND WHY IT IS NOT A STRAIGHT LINE
-----------------------------------------------------
Three points, because that is the shape of the real thing:

  WP1     a push point roughly half way out, offset to the SIDE. Nobody flies
          the direct radial from home to target — it is the first line an
          enemy controller draws.
  IP      the initial point: a recognisable spot 5-9 nm short of the target,
          offset so the run-in heading differs from the transit heading. The
          IP is where you stop navigating and start attacking.
  TARGET  the aim point, at attack altitude.

then `land_at(home)`. The lateral offset (the "dogleg") is seeded, so the route
is different per mission but identical for the same share link.

Altitudes and speeds are era-plausible rather than optimal: a Mustang does not
transit at 20,000 ft and a Viper does not run in at 250 kt.

SCOPE: TARGETS ONLY
-------------------
A route needs a destination. Strike and CAS have one; a CAP or a sandbox does
not, and inventing a station orbit for them would be exactly the kind of
telling-you-how-to-fly the north star is about. So `route_for()` returns None
when there is no target package, and the checkbox says so.
"""
import math

from dcs import mapping

# (transit alt, IP alt, attack alt) in metres MSL, and transit speed in km/h.
# WWII sits low and slow; the Cold War block is a compromise between a Phantom
# and a MiG-21; modern is a standard medium-altitude transit.
ERA_PROFILE = {
    "wwii":    (2400, 1800, 1500, 400),
    "coldwar": (4500, 3000, 2400, 750),
    # GWOT flies HIGHER than modern, not lower. With no radar SAM to duck and
    # a gun line that tops out around 8-10,000 ft, the whole campaign lived
    # above it. Descending to a modern medium-altitude transit here is the one
    # place this era's profile is actively dangerous.
    "gwot":    (7500, 6000, 4500, 800),
}
DEFAULT_PROFILE = (6000, 4500, 3000, 800)

_M_PER_NM = 1852.0


def _bearing(a, b):
    """Degrees true from a to b. DCS x is NORTH and y is EAST, which is the
    transposition every bearing bug in this codebase has come from."""
    return math.degrees(math.atan2(b.y - a.y, b.x - a.x)) % 360


def _offset(p, dist_m, bearing_deg):
    rad = math.radians(bearing_deg)
    return mapping.Point(p.x + dist_m * math.cos(rad),
                         p.y + dist_m * math.sin(rad), p._terrain)


def route_for(home_pos, target_pos, era, rng, terrain=None):
    """Plan the legs. Returns [{name, point, alt, speed}] or None.

    Pure geometry — builds no groups and touches no mission, so it is testable
    on its own and callable from the brief and the kneeboard without a `.miz`.
    """
    if home_pos is None or target_pos is None:
        return None
    dist = home_pos.distance_to_point(target_pos)
    if dist < 8000:
        # The target is effectively on top of the field. A three-point route
        # here would have the IP behind you at rotation; better to give nothing
        # and let the pilot look out of the window.
        return None
    axis = _bearing(home_pos, target_pos)
    side = 1 if rng.random() < 0.5 else -1
    t_alt, ip_alt, atk_alt, spd = ERA_PROFILE.get(era, DEFAULT_PROFILE)

    half = mapping.Point(home_pos.x + (target_pos.x - home_pos.x) * 0.45,
                         home_pos.y + (target_pos.y - home_pos.y) * 0.45,
                         terrain if terrain is not None else home_pos._terrain)
    wp1 = _offset(half, min(12000, dist * 0.15), (axis + side * 90) % 360)
    ip = _offset(target_pos, min(16000, max(9000, dist * 0.25)),
                 (axis + 180 + side * 30) % 360)
    return [
        {"name": "WP1", "point": wp1, "alt": t_alt, "speed": spd},
        {"name": "IP", "point": ip, "alt": ip_alt, "speed": spd},
        {"name": "TARGET", "point": target_pos, "alt": atk_alt, "speed": spd},
    ]


def add_recovery(group, home_airport=None, home_carrier=None):
    """Use a ship link for carrier recovery; airport IDs belong to airfields."""
    if home_carrier is not None:
        from dcs.point import PointAction
        point = group.add_waypoint(home_carrier.position, altitude=0, speed=250,
                                   name="RECOVER AT CARRIER")
        point.type = "Land"
        point.action = PointAction.Landing
        point.link_unit = point.helipad_id = home_carrier.id
        return True
    if home_airport is not None:
        group.land_at(home_airport)
        return True
    return False


def apply(player_group, legs, home_airport=None, home_carrier=None):
    """Write the legs onto the player's flight and try to land him at home.

    The landing point is best-effort on purpose: `land_at` depends on the
    airport object having a usable runway entry, and a route that ends at the
    target is still a usable route. Losing the whole flight plan because the
    recovery point would not attach is the worse trade.
    """
    for leg in legs:
        player_group.add_waypoint(leg["point"], altitude=leg["alt"],
                                  speed=leg["speed"], name=leg["name"])
    if home_airport is not None or home_carrier is not None:
        try:
            return add_recovery(player_group, home_airport, home_carrier)
        except Exception:
            pass
    return False


def leg_card(home_pos, legs, home_name="HOME"):
    """Leg-by-leg numbers for the kneeboard: heading, distance, altitude, time.

    Computed here rather than in the kneeboard so the same figures can go in
    the briefing text — two renderers deriving the same numbers separately is
    how a chart and a brief end up disagreeing.
    """
    rows, prev, prev_name = [], home_pos, home_name
    for leg in legs:
        d = prev.distance_to_point(leg["point"])
        hdg = _bearing(prev, leg["point"])
        kt = leg["speed"] / _M_PER_NM * 1000.0        # km/h -> kt
        nm = d / _M_PER_NM
        rows.append({
            "from": prev_name,
            "to": leg["name"],
            # The point rides along so the DTC cartridge and the kneeboard work
            # from ONE list. Two consumers re-deriving the same geometry is how
            # a cartridge and a card end up pointing at different places.
            "point": leg["point"],
            # NTTR corridor legs name the published fix they sit on; the
            # generic route has none. Printed on the card and the brief.
            "fix": leg.get("fix"),
            "corridor": leg.get("corridor"),
            "heading": int(round(hdg)) % 360,
            "nm": round(nm, 1),
            "alt_ft": int(round(leg["alt"] / 0.3048 / 100.0) * 100),
            "kt": int(round(kt)),
            "min": round(nm / kt * 60.0, 1) if kt else 0.0,
        })
        prev, prev_name = leg["point"], leg["name"]
    return rows


def summary(legs, target_label, home_name):
    names = " > ".join(l["name"] for l in legs)
    return f"{names} ({target_label}) > {home_name}"


def brief_lines(rows, target_label):
    """The route as briefing text. Plain rows — the pilot reads this on the
    ground and then flies it off the kneeboard."""
    L = ["ROUTE (auto-generated — you asked for it; edit or ignore freely)",
         f"  Target: {target_label}",
         "  Headings are TRUE — apply your theater's magnetic variation.", ""]
    total_nm = total_min = 0.0
    for r in rows:
        L.append(f"  {r['from']:>7s} -> {r['to']:<7s} "
                 f"{r['heading']:03d}deg  {r['nm']:5.1f} nm  "
                 f"{r['alt_ft']:>6,d} ft  {r['kt']:3d} kt  {r['min']:4.1f} min")
        total_nm += r["nm"]
        total_min += r["min"]
    L += ["", f"  Outbound total: {total_nm:.0f} nm, {total_min:.0f} min at "
              f"briefed speeds (no wind, no join-up, no rejoin)."]
    return L
