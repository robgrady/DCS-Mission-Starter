"""BB-16/17: strike target sets and practice ranges — pre-composed packages
placed near the enemy rear (targets) or friendly rear (ranges)."""
import math
import random
from dcs import mapping
import dcs.statics as st

from .resolver import resolve

TARGET_PACKAGES = {
    "depot": {
        "label": "Vehicle depot",
        "statics": [("Fortification.Fuel_tank", 0, 0), ("Fortification.Fuel_tank", 25, 90),
                    ("Fortification.Barracks_2", 60, 45), ("Fortification.Tent01", 90, 60)],
        "vehicles": {"coldwar": ["vehicles.Armor.BMP_1", "vehicles.Unarmed.ATZ_10"],
                     "modern": ["vehicles.Armor.BMP_2", "vehicles.Unarmed.ATZ_10"],
                     "wwii": ["vehicles.Armor.Pz_IV_H", "vehicles.Unarmed.Blitz_36_6700A"]},
        "count": 6,
    },
    "convoy": {
        "label": "Road convoy",
        "statics": [],
        "vehicles": {"coldwar": ["vehicles.Armor.BMP_1", "vehicles.Unarmed.KAMAZ_Truck"],
                     "modern": ["vehicles.Armor.BTR_80", "vehicles.Unarmed.KAMAZ_Truck"],
                     "wwii": ["vehicles.Armor.Sd_Kfz_251", "vehicles.Unarmed.Blitz_36_6700A"]},
        "count": 8,
    },
    "c2_site": {
        "label": "Command & control site",
        "statics": [("Fortification.Comms_tower_M", 0, 0), ("Fortification.Barracks_2", 40, 30),
                    ("Fortification.Tent03", 70, 90), ("Fortification.Fuel_tank", 55, 200)],
        "vehicles": {"coldwar": ["vehicles.Unarmed.GAZ_66"],
                     "modern": ["vehicles.Unarmed.KAMAZ_Truck"],
                     "wwii": ["vehicles.Unarmed.Kubelwagen_82"]},
        "count": 3,
    },
}


def _offset(pos, meters, bearing_deg):
    b = math.radians(bearing_deg)
    return mapping.Point(pos.x + meters * math.cos(b),
                         pos.y + meters * math.sin(b), pos._terrain)


def add_target_package(m, enemy_country, era, package_key, center,
                       rng: random.Random, name):
    pkg = TARGET_PACKAGES[package_key]
    for i, (ref, dist, brg) in enumerate(pkg["statics"]):
        cat, attr = ref.split(".")
        obj = getattr(getattr(st, cat), attr)
        m.static_group(enemy_country, f"{name} s{i}", _type=obj,
                       position=_offset(center, dist, brg),
                       heading=rng.uniform(0, 360))
    refs = pkg["vehicles"].get(era) or []
    for i in range(pkg["count"]):
        ref = refs[i % len(refs)] if refs else None
        if not ref:
            break
        pos = _offset(center, rng.uniform(20, 120), rng.uniform(0, 360))
        m.vehicle_group(enemy_country, f"{name} v{i}", resolve(ref), pos,
                        heading=rng.uniform(0, 360))
    zone = m.triggers.add_triggerzone(center, radius=1500, name=f"TGT {name}")
    return pkg["label"]


def add_practice_range(m, own_country, center, rng: random.Random, name):
    """Simple bombing/strafe range in the friendly rear: ring of targets + pit."""
    # bombing circle: 6 fuel tanks in a ring, aim point at center
    for i in range(6):
        m.static_group(own_country, f"{name} ring {i}",
                       _type=st.Fortification.Fuel_tank,
                       position=_offset(center, 80, i * 60), heading=0)
    # strafe pit: 3 old trucks in a line 500m away
    for i in range(3):
        m.static_group(own_country, f"{name} strafe {i}",
                       _type=st.Fortification.Tent01,
                       position=_offset(_offset(center, 500, 90), i * 30, 0),
                       heading=270)
    m.triggers.add_triggerzone(center, radius=2000, name=f"RANGE {name}")
    return name
