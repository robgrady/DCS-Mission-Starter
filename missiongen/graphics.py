"""BB-23: Mission graphics — F10 map drawing layers (v1.2.0, roadmap 'v1.6' pulled forward).

The map briefs the mission: every element that has geometry gets a drawn zone,
so the F10 map reads like a planned ATO instead of empty terrain.

Layer discipline (MP-safe by construction):
- Coalition-private picture (own support orbits, the threat-ring 'intel'
  overlay) goes on the player's side layer — DCS renders Blue/Red drawing
  layers per coalition.
- Shared references (bullseye; nav points, drawn by navpoints.py) go on Common.

Zones inform, they don't route — no player waypoints, ever.
"""
import math
from dcs import mapping
from dcs.drawing.drawing import Rgba

# one visual language across all zones
FRIENDLY = Rgba(90, 170, 255, 230)     # support orbits — blue
FRIENDLY_FILL = Rgba(90, 170, 255, 20)
CARRIER = Rgba(120, 200, 255, 230)     # CSG ops box
CARRIER_FILL = Rgba(120, 200, 255, 15)
THREAT = Rgba(255, 80, 80, 220)        # SAM WEZ rings — red, minimal fill
THREAT_FILL = Rgba(255, 80, 80, 12)
TARGET = Rgba(255, 170, 60, 230)       # strike packages — amber
TARGET_FILL = Rgba(255, 170, 60, 20)
FARP = Rgba(120, 220, 140, 230)        # FARPs — green
FARP_FILL = Rgba(120, 220, 140, 20)
NEUTRAL = Rgba(230, 230, 230, 230)     # bullseye — white
LABEL_BG = Rgba(0, 0, 0, 90)

# every drawable layer this module owns (nav points live in navpoints.py but
# are part of the same user-facing "Map graphics" checklist)
LAYER_KEYS = ["tanker", "awacs", "cap", "aew", "carrier_box",
              "targets", "farps", "bullseye", "threats"]


def effective_layers(recipe_layers):
    """None = auto (everything with geometry draws); explicit list wins."""
    if recipe_layers is None:
        return set(LAYER_KEYS)
    return {k for k in recipe_layers if k in LAYER_KEYS}


def _offset(pos, meters, bearing_deg):
    b = math.radians(bearing_deg)
    return mapping.Point(pos.x + meters * math.cos(b),
                         pos.y + meters * math.sin(b), pos._terrain)


def _label(layer, pos, text, color, size=13):
    layer.add_text_box(pos, text, color=color, fill=LABEL_BG,
                       font_size=size, border_thickness=0)


def _racetrack(layer, pos, heading, race_dist, label, color, fill,
               radius=7000.0):
    """Orbit stadium: anchor -> race_dist along heading, labeled at the anchor."""
    p2 = _offset(pos, race_dist, heading)
    layer.add_oblong(pos, p2, radius, color=color, fill=fill, line_thickness=3)
    _label(layer, _offset(pos, radius + 2500, (heading + 90) % 360),
           label, color)


def draw_layers(m, gfx, layers, side):
    """Draw everything collected in gfx (see builder) onto the right layers.

    gfx keys (all optional): tanker/awacs = (pos, heading, race, label);
    cap = (st1, st2, label); aew = (pos, heading, race, label);
    carrier = (anchor, brc, name); targets = [(pos, label)];
    farps = [(pos, name)]; bullseye = pos; threats = [(pos, wez_m, label)].
    Returns the list of layer keys actually drawn.
    """
    own = m.drawings.get_layer_by_name("Blue" if side == "blue" else "Red")
    common = m.drawings.get_layer_by_name("Common")
    drawn = []

    if "tanker" in layers and gfx.get("tanker"):
        pos, hdg, race, label = gfx["tanker"]
        _racetrack(own, pos, hdg, race, label, FRIENDLY, FRIENDLY_FILL)
        drawn.append("tanker")

    if "awacs" in layers and gfx.get("awacs"):
        pos, hdg, race, label = gfx["awacs"]
        _racetrack(own, pos, hdg, race, label, FRIENDLY, FRIENDLY_FILL,
                   radius=9000)
        drawn.append("awacs")

    if "cap" in layers and gfx.get("cap"):
        st1, st2, label = gfx["cap"]
        own.add_oblong(st1, st2, 6000, color=FRIENDLY, fill=FRIENDLY_FILL,
                       line_thickness=3)
        _label(own, _offset(st1, 9000, 0), label, FRIENDLY)
        drawn.append("cap")

    if "aew" in layers and gfx.get("aew"):
        pos, hdg, race, label = gfx["aew"]
        _racetrack(own, pos, hdg, race, label, FRIENDLY, FRIENDLY_FILL,
                   radius=8000)
        drawn.append("aew")

    if "carrier_box" in layers and gfx.get("carrier"):
        anchor, brc, name = gfx["carrier"]
        # ops box covers the 40 km steaming leg, oriented on BRC
        p1 = _offset(anchor, -8000, brc)
        p2 = _offset(anchor, 48000, brc)
        own.add_oblong(p1, p2, 14000, color=CARRIER, fill=CARRIER_FILL,
                       line_thickness=3)
        # DCS drawing arrow: its default point set (Arrow.get_default_arrow_points)
        # points along +Y = due EAST (090) at angle 0, and the angle field is in
        # DEGREES measured clockwise. BRC is a compass bearing FROM NORTH, so
        # passing brc directly rendered the arrow 90° off (perpendicular to the
        # track). Convert compass-from-North to the shape's East-zero frame:
        own.add_arrow(anchor, (brc - 90) % 360, 9000, color=CARRIER,
                      fill=CARRIER_FILL, line_thickness=2)
        _label(own, _offset(anchor, 17000, (brc + 90) % 360),
               f"⚓ {name} — BRC {int(brc):03d}", CARRIER)
        drawn.append("carrier_box")

    if "targets" in layers and gfx.get("targets"):
        for pos, label in gfx["targets"]:
            own.add_circle(pos, radius=4000, color=TARGET, fill=TARGET_FILL,
                           line_thickness=3)
            _label(own, _offset(pos, 5500, 45), label, TARGET)
        drawn.append("targets")

    if "farps" in layers and gfx.get("farps"):
        for pos, name in gfx["farps"]:
            own.add_circle(pos, radius=1200, color=FARP, fill=FARP_FILL,
                           line_thickness=2)
            _label(own, _offset(pos, 2200, 45), f"⛽ {name}", FARP, size=12)
        drawn.append("farps")

    if "bullseye" in layers and gfx.get("bullseye"):
        pos = gfx["bullseye"]
        common.add_circle(pos, radius=3000, color=NEUTRAL,
                          fill=Rgba(230, 230, 230, 10), line_thickness=2)
        common.add_circle(pos, radius=700, color=NEUTRAL,
                          fill=Rgba(230, 230, 230, 40), line_thickness=2)
        _label(common, _offset(pos, 4500, 45), "◎ BULLSEYE", NEUTRAL)
        drawn.append("bullseye")

    if "threats" in layers and gfx.get("threats"):
        # the INTEL PICTURE: known enemy area-SAM engagement rings, drawn on
        # the PLAYER's layer only — you brief known threats; red MP players
        # don't get their own SAMs highlighted
        for pos, wez_m, label in gfx["threats"]:
            own.add_circle(pos, radius=wez_m, color=THREAT, fill=THREAT_FILL,
                           line_thickness=3)
            _label(own, _offset(pos, wez_m * 0.75, 315), f"⚠ {label}", THREAT,
                   size=12)
        drawn.append("threats")

    return drawn
