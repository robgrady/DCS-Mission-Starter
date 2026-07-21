"""Resolve dotted data-pack references ("planes.F_16C_50") to pydcs classes.

FR-2: unknown/renamed types fail loudly, never silently produce a broken .miz.
"""
import json
import importlib
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


class UnknownUnitError(Exception):
    pass


def load_json(name: str) -> dict:
    with open(DATA_DIR / f"{name}.json") as f:
        return json.load(f)


def resolve(ref: str):
    """'planes.F_16C_50' -> dcs.planes.F_16C_50; 'vehicles.Unarmed.ATZ_10' -> nested attr."""
    parts = ref.split(".")
    mod = importlib.import_module(f"dcs.{parts[0]}")
    obj = mod
    for attr in parts[1:]:
        obj = getattr(obj, attr, None)
        if obj is None:
            raise UnknownUnitError(f"Data pack references unknown unit '{ref}' "
                                   f"(failed at '{attr}'). Update the data pack or pydcs.")
    return obj


def resolve_terrain(dotted: str):
    module, cls = dotted.rsplit(".", 1)
    return getattr(importlib.import_module(module), cls)


def resolve_country(name: str):
    countries = importlib.import_module("dcs.countries")
    c = getattr(countries, name, None)
    if c is None:
        raise UnknownUnitError(f"Unknown country '{name}'")
    return c


# Anachronism guard: nothing post-1945 may appear in a WWII dressing block.
# This makes "no F/A-18 on a WWII field" a hard invariant instead of a data
# convention — any future edit that sneaks a jet/helo/modern truck into the
# wwii era fails the health check loudly.
_WWII_FORBIDDEN = ("planes.F_", "planes.FA_", "planes.A_10", "planes.MiG",
                   "planes.Su_", "planes.C_130", "planes.IL_76", "planes.An_",
                   "planes.E_2", "planes.S_3", "helicopters.",
                   "HEMTT", "KAMAZ", "Hummer", "GAZ_", "ATZ", "M_818")


def validate_data_packs() -> list:
    """Resolve every unit reference in every data pack. Returns list of errors."""
    errors = []
    eras = load_json("eras")
    for era, sides in eras.items():
        for side in ("blue", "red"):
            cfg = sides[side]
            refs = (cfg["parked_planes"] + cfg["parked_large"] + cfg["parked_helos"]
                    + cfg["utility_trucks"] + cfg["shorad"]
                    + [cfg["fuel_truck"], cfg["fire_truck"]])
            for ref in refs:
                if ref is None:
                    continue
                try:
                    resolve(ref)
                except UnknownUnitError as e:
                    errors.append(f"{era}/{side}: {e}")
                if era == "wwii" and any(tag in ref for tag in _WWII_FORBIDDEN):
                    errors.append(f"ANACHRONISM wwii/{side}: {ref} is not a "
                                  "WWII-era unit - period dressing violated")
    # ramp themes: resolve every ref; wwii themes obey the anachronism guard too
    themes = load_json("ramp_themes")
    for era, sides in themes.items():
        if not isinstance(sides, dict):
            continue                     # _comment
        for side, tset in sides.items():
            for tkey, tcfg in tset.items():
                if tkey == "default":
                    continue
                for pairs in (tcfg["planes"], tcfg["large"], tcfg["helos"]):
                    for ref, _w in pairs:
                        try:
                            resolve(ref)
                        except UnknownUnitError as e:
                            errors.append(f"theme {era}/{side}/{tkey}: {e}")
                        if era == "wwii" and any(t in ref for t in _WWII_FORBIDDEN):
                            errors.append(f"ANACHRONISM theme wwii/{side}/{tkey}: {ref}")

    # nation rosters (Theater Identity P1): every plane ref must resolve, the
    # nation must be a real pydcs country, and wwii rosters obey the anachronism
    # guard. These are 100+ refs the old validator never touched.
    rosters = load_json("nation_rosters")
    for era, nations in rosters.items():
        if not isinstance(nations, dict) or era.startswith("_"):
            continue
        for nation, body in nations.items():
            try:
                resolve_country(nation)
            except UnknownUnitError as e:
                errors.append(f"roster {era}/{nation}: {e}")
            for ref, _w in body.get("planes", []):
                try:
                    resolve(ref)
                except UnknownUnitError as e:
                    errors.append(f"roster {era}/{nation}: {e}")
                if era == "wwii" and any(t in ref for t in _WWII_FORBIDDEN):
                    errors.append(f"ANACHRONISM roster wwii/{nation}: {ref}")

    # theater identity: every base owner must be a real pydcs country, or the
    # builder crashes when it tries to dress that base under a bogus country.
    identity = load_json("theater_identity")
    for mapk, eras_i in identity.items():
        if not isinstance(eras_i, dict) or mapk.startswith("_"):
            continue
        for era, block in eras_i.items():
            for base, nation in (block or {}).get("bases", {}).items():
                try:
                    resolve_country(nation)
                except UnknownUnitError as e:
                    errors.append(f"identity {mapk}/{era}/{base}: {e}")

    # carrier data: hull_class entries must reference a defined deck class
    # (internal consistency). Aircraft keys are NOT strict-resolved here because
    # the roster intentionally lists pre-release modules (e.g. the F-14B(U)).
    carrier = load_json("carrier_capable")
    classes = set(carrier.get("classes", {}))
    for hull, cls in carrier.get("hull_class", {}).items():
        if cls not in classes:
            errors.append(f"carrier hull_class {hull}: unknown deck class '{cls}'")

    # surveyed airframe dimensions: positive numeric length/span/height, else the
    # occupancy registry does maths on garbage and mis-places statics.
    try:
        dims = load_json("airframe_dimensions")
    except Exception as e:
        dims = {}
        errors.append(f"airframe_dimensions: unreadable ({e})")
    for tid, box in dims.items():
        if tid.startswith("_"):
            continue
        if not isinstance(box, dict) or not all(
                isinstance(box.get(k), (int, float)) and box.get(k, 0) > 0
                for k in ("length", "span", "height")):
            errors.append(f"airframe_dimensions/{tid}: needs positive numeric "
                          "length, span, height")

    return errors
