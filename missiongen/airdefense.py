"""BB-5..6: era-correct, functionally complete SAM sites and SHORAD."""
import random
from dcs import mapping
from dcs.unit import Skill

from .kits import kit_positions, SAM_KITS
from .resolver import resolve
from .dressing import _offset


def place_sam_site(m, country, kit_key, center, rng: random.Random, name):
    """One complete SAM site as a single group (radars + launchers stay linked)."""
    base_heading = rng.uniform(0, 360)
    vg = None
    for ref, pos, heading in kit_positions(kit_key, center, base_heading):
        utype = resolve(ref)
        if vg is None:
            vg = m.vehicle_group(country, name, utype, pos, heading=heading)
            vg.units[0].skill = Skill.High
        else:
            u = m.vehicle(f"{name} {len(vg.units)+1}", utype)
            u.position = pos
            u.heading = heading
            u.skill = Skill.High
            vg.add_unit(u)
    return vg


def defend_airbase(m, country, airport, side_cfg, rng: random.Random, era_key):
    """Stand up one SAM site 2.5-4km off the field plus SHORAD point defense."""
    created = []
    kits = side_cfg["sam_kits"]
    if kits:
        kit = rng.choice(kits)
        center = _offset(airport.position, rng.uniform(2500, 4000), rng.uniform(0, 360))
        name = f"{SAM_KITS[kit]['label']} - {airport.name}"
        place_sam_site(m, country, kit, center, rng, name)
        created.append(name)

    # SHORAD pair on the field perimeter
    for i, ref in enumerate(rng.sample(side_cfg["shorad"], k=min(2, len(side_cfg["shorad"])))):
        pos = _offset(airport.position, rng.uniform(900, 1400), rng.uniform(0, 360))
        g = m.vehicle_group(country, f"SHORAD {airport.name} {i+1}", resolve(ref),
                            pos, heading=rng.uniform(0, 360))
        g.units[0].skill = Skill.High
        created.append(g.name)
    return created
