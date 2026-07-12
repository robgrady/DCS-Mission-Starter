"""Carrier deck configuration (BB-9 extension): real-world deck layouts with
aircraft and equipment statics LINKED to the ship so they ride the deck.

DCS mechanism: static group with linkOffset=true and the unit carrying
linkUnit=<ship unit id> + offsets{x, y, angle}. pydcs doesn't serialize
linkUnit/offsets, so DeckStatic extends Static.dict() with them.
"""
import math
from dcs import mapping
from dcs.unit import Static
from dcs.point import StaticPoint

from .resolver import load_json, resolve


class LinkedStaticPoint(StaticPoint):
    """Static group route point carrying linkUnit — this is where the ME puts it
    (mist.lua: group_data.route.points[1].linkUnit) and what DCS reads for deck
    statics. Without it, linked statics silently fail to ride the ship."""
    def __init__(self, position, link_unit_id):
        super().__init__(position)
        self.link_unit_id = link_unit_id

    def dict(self):
        d = super().dict()
        d["linkUnit"] = self.link_unit_id
        return d


class DeckStatic(Static):
    """A static linked to a ship unit (rides the deck)."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.link_unit_id = None
        self.link_dx = 0.0     # forward (+) meters
        self.link_dy = 0.0     # starboard (+) meters
        self.link_angle = 0.0  # radians relative to ship heading

    def dict(self):
        d = super().dict()
        if self.link_unit_id is not None:
            d["linkUnit"] = self.link_unit_id
            d["offsets"] = {"x": self.link_dx, "y": self.link_dy,
                            "angle": round(self.link_angle, 13)}
        return d


def _load_hull(hull_key: str) -> dict:
    data = load_json("carrier_decks")
    hull = dict(data["hulls"][hull_key])
    parent_key = hull.get("inherit_spots")
    if parent_key:
        parent = data["hulls"][parent_key]
        hull.setdefault("spots", parent["spots"])
        hull.setdefault("equipment", parent["equipment"])
        hull.setdefault("deck_aircraft", parent["deck_aircraft"])
    return hull


def hulls_for_options() -> dict:
    """Hull metadata for /api/options (wizard hull picker)."""
    data = load_json("carrier_decks")
    out = {}
    for key in data["hulls"]:
        h = _load_hull(key)
        out[key] = {"label": h["label"], "eras": h["eras"], "module": h["module"],
                    "deck_aircraft": h["deck_aircraft"]}
    out["_layouts"] = {k: v["label"] for k, v in data["layouts"].items()}
    return out


def _place_linked(m, country, name, unit_type, ship_unit, brc_deg, dx, dy, hdg_rel_deg):
    """Create one deck-linked static at ship-relative (dx fwd, dy stbd)."""
    brc = math.radians(brc_deg)
    # world position: rotate ship-relative offsets by BRC (x north, y east in DCS)
    wx = ship_unit.position.x + dx * math.cos(brc) - dy * math.sin(brc)
    wy = ship_unit.position.y + dx * math.sin(brc) + dy * math.cos(brc)

    from dcs import unitgroup
    sg = unitgroup.StaticGroup(m.next_group_id(), name)
    s = DeckStatic(m.next_unit_id(), name + " unit", unit_type, m.terrain)
    s.position = mapping.Point(wx, wy, m.terrain)
    s.heading = (brc_deg + hdg_rel_deg) % 360
    s.link_unit_id = ship_unit.id
    s.link_dx = dx
    s.link_dy = dy
    s.link_angle = math.radians(hdg_rel_deg)
    sg.add_unit(s)
    # linkUnit must ALSO be on the route point — that's the field DCS actually
    # reads for deck statics (verified against mist.lua's mission parser)
    sg.add_point(LinkedStaticPoint(s.position, ship_unit.id))
    sg.link_offset = True
    country.add_static_group(sg)
    return sg


def _place_linked_raw(m, country, name, type_str, ship_unit, brc_deg,
                      dx, dy, hdg_rel_deg, category=None, livery=None):
    """Deck-linked static from a raw DCS type string (SC gear, personnel, liveried jets)."""
    import math as _math
    brc = _math.radians(brc_deg)
    wx = ship_unit.position.x + dx * _math.cos(brc) - dy * _math.sin(brc)
    wy = ship_unit.position.y + dx * _math.sin(brc) + dy * _math.cos(brc)
    from dcs import unitgroup
    from dcs.point import StaticPoint
    sg = unitgroup.StaticGroup(m.next_group_id(), name)
    s = DeckStatic(m.next_unit_id(), name + " unit", type_str, m.terrain)
    if category:
        s.category = category
    if livery:
        s.livery_id = livery
    s.position = mapping.Point(wx, wy, m.terrain)
    s.heading = (brc_deg + hdg_rel_deg) % 360
    s.link_unit_id = ship_unit.id
    s.link_dx = dx
    s.link_dy = dy
    s.link_angle = _math.radians(hdg_rel_deg)
    sg.add_unit(s)
    sg.add_point(LinkedStaticPoint(s.position, ship_unit.id))
    sg.link_offset = True
    country.add_static_group(sg)
    return sg


def configure_deck_formation(m, country, csg_group, brc_deg, hull_key, layout_key,
                             aircraft_keys, want_equipment, rng, warnings):
    """Supercarrier hulls: editor-MEASURED formation templates (Redkite data).
    Rows are real ops-phase packs; one aircraft type per row (squadron spotting);
    template liveries carried when the type matches."""
    fm = load_json("deck_formations")
    formation = fm["formations"].get(layout_key) or fm["formations"]["underway"]
    hull = _load_hull(hull_key)
    ship_unit = csg_group.units[0]
    placed = 0

    valid = [r for r in hull["deck_aircraft"] if r.split(".")[-1] in aircraft_keys]
    jets = [r for r in valid if not r.startswith("helicopters.")
            and not r.split(".")[-1].startswith("E_2")]
    i = 0
    for ri, row in enumerate(formation["rows"]):
        if not jets:
            break
        ref = jets[ri % len(jets)]          # homogeneous type per row
        actype = resolve(ref)
        for spot in row["slots"]:
            i += 1
            livery = spot.get("livery") if actype.id == spot.get("template_type") else None
            _place_linked_raw(m, country, f"DECK {hull_key} {i} {actype.id}",
                              actype.id, ship_unit, brc_deg,
                              spot["x"], spot["y"], spot["hdg"],
                              category="Planes", livery=livery)
            placed += 1

    # typed specials (E-2 by the island, SH-60 on the port quarter) — only if selected
    sel = set(aircraft_keys)
    for sp in formation.get("special", []):
        want = (sp["type"] == "E-2C" and "E_2C" in sel) or \
               (sp["type"] == "SH-60B" and "SH_60B" in sel)
        if not want:
            continue
        i += 1
        cat = "Helicopters" if sp["type"] == "SH-60B" else "Planes"
        _place_linked_raw(m, country, f"DECK {hull_key} {i} {sp['type']}",
                          sp["type"], ship_unit, brc_deg,
                          sp["x"], sp["y"], sp["hdg"], category=cat,
                          livery=sp.get("livery"))
        placed += 1

    if want_equipment:
        for j, eq in enumerate(fm["equipment"]):
            _place_linked_raw(m, country, f"DECKEQ {hull_key} {j+1}",
                              eq["type"], ship_unit, brc_deg,
                              eq["x"], eq["y"], eq["hdg"],
                              category=eq.get("category"),
                              livery=eq.get("livery"))
            placed += 1
    return placed


def configure_deck(m, country, csg_group, brc_deg, hull_key, layout_key,
                   aircraft_keys, want_equipment, rng, warnings):
    """Fill the selected layout with the chosen aircraft + default gear.
    Supercarrier hulls use measured formation templates; other hulls use zones."""
    fm = load_json("deck_formations")
    if hull_key in fm["applies_to_hulls"]:
        return configure_deck_formation(m, country, csg_group, brc_deg, hull_key,
                                        layout_key, aircraft_keys, want_equipment,
                                        rng, warnings)
    data = load_json("carrier_decks")
    hull = _load_hull(hull_key)
    layout = data["layouts"].get(layout_key) or data["layouts"]["recovery"]
    ship_unit = csg_group.units[0]
    placed = 0

    # user-selected aircraft, kept to this hull's deckable list
    valid = [r for r in hull["deck_aircraft"]
             if r.split(".")[-1] in aircraft_keys] or []
    if aircraft_keys and not valid:
        warnings.append(f"none of the selected deck aircraft are deckable on "
                        f"{hull['label']} - deck left empty")

    # squadron spotting: ONE type per zone (whole rows of the same airframe at a
    # uniform heading, like a real handler's spot), helos to the corral, E-2s to
    # their pref spots. Zones fill in doctrine order — nothing is shuffled.
    helos = [r for r in valid if r.startswith("helicopters.")]
    e2s = [r for r in valid if r.split(".")[-1].startswith("E_2")]
    jets = [r for r in valid if r not in helos and r not in e2s]

    zi = 0   # cycles jet types across zones, keeping each row homogeneous
    i = 0
    for zone in layout["fill_zones"]:
        zone_spots = hull["spots"].get(zone, [])
        if not zone_spots:
            continue
        # pick this zone's type once
        pref = zone_spots[0].get("pref")
        if pref == "helo":
            zone_ref = helos[0] if helos else None      # corral stays open otherwise
        elif pref == "e2":
            zone_ref = e2s[0] if e2s else (jets[zi % len(jets)] if jets else None)
        elif jets:
            zone_ref = jets[zi % len(jets)]
            zi += 1
        else:
            zone_ref = valid[0] if valid else None
        if zone_ref is None:
            continue
        actype = resolve(zone_ref)
        for spot in zone_spots:
            i += 1
            _place_linked(m, country, f"DECK {hull_key} {i} {actype.id}", actype,
                          ship_unit, brc_deg, spot["x"], spot["y"], spot["hdg"])
            placed += 1

    if want_equipment:
        for j, eq in enumerate(hull["equipment"]):
            _place_linked(m, country, f"DECKEQ {hull_key} {j+1}", resolve(eq["ref"]),
                          ship_unit, brc_deg, eq["x"], eq["y"], eq["hdg"])
            placed += 1
    return placed
