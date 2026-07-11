"""Carrier deck configuration (BB-9 extension): real-world deck layouts with
aircraft and equipment statics LINKED to the ship so they ride the deck.

DCS mechanism: static group with linkOffset=true and the unit carrying
linkUnit=<ship unit id> + offsets{x, y, angle}. pydcs doesn't serialize
linkUnit/offsets, so DeckStatic extends Static.dict() with them.
"""
import math
from dcs import mapping
from dcs.unit import Static

from .resolver import load_json, resolve


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
    from dcs.point import StaticPoint
    sp = StaticPoint(s.position)
    sg.add_point(sp)
    sg.link_offset = True
    country.add_static_group(sg)
    return sg


def configure_deck(m, country, csg_group, brc_deg, hull_key, layout_key,
                   aircraft_keys, want_equipment, rng, warnings):
    """Fill the selected layout's zones with the chosen aircraft + default gear."""
    data = load_json("carrier_decks")
    hull = _load_hull(hull_key)
    layout = data["layouts"][layout_key]
    ship_unit = csg_group.units[0]
    placed = 0

    # user-selected aircraft, kept to this hull's deckable list
    valid = [r for r in hull["deck_aircraft"]
             if r.split(".")[-1] in aircraft_keys] or []
    if aircraft_keys and not valid:
        warnings.append(f"none of the selected deck aircraft are deckable on "
                        f"{hull['label']} - deck left empty")

    spots = [s for z in layout["fill_zones"] for s in hull["spots"].get(z, [])]
    rng.shuffle(spots)
    for i, spot in enumerate(spots):
        if not valid:
            break
        ref = valid[i % len(valid)]
        actype = resolve(ref)
        _place_linked(m, country, f"DECK {hull_key} {i+1} {actype.id}", actype,
                      ship_unit, brc_deg, spot["x"], spot["y"], spot["hdg"])
        placed += 1

    if want_equipment:
        for j, eq in enumerate(hull["equipment"]):
            _place_linked(m, country, f"DECKEQ {hull_key} {j+1}", resolve(eq["ref"]),
                          ship_unit, brc_deg, eq["x"], eq["y"], eq["hdg"])
            placed += 1
    return placed
