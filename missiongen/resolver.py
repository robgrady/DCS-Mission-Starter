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
    return errors
