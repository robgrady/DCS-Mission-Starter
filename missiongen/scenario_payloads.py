"""Explicit scenario fits; generic role selection remains the default."""
from . import loadouts
from .recipe import RecipeError
from .resolver import load_json


def resolve_fit(recipe, aircraft_id, *, year=None):
    profile = recipe.player_fit
    if profile == "auto":
        return loadouts.player_loadout(aircraft_id, recipe.mission_kind,
                                      recipe.era, recipe.player_load, year=year)
    if profile in ("clean", "guns"):
        return {"label": "Clean carrier qualification fit" if profile == "clean"
                else "Guns only — no external weapons or tanks", "pylons": {}}
    if profile == "recon":
        stores = load_json("scenario_stores").get(aircraft_id)
        if not stores:
            raise RecipeError(f"No verified reconnaissance fit for {aircraft_id}.")
        return {"label": "TARPS reconnaissance pod — no external weapons",
                "pylons": {p: v["clsid"] for p, v in stores.items()}}
    aircraft = loadouts._plane_type(aircraft_id)
    if aircraft is None:
        raise RecipeError(f"No store data for {aircraft_id}.")
    if profile == "unguided":
        # Pair the same bomb on legal mirrored stations. Never silently fall
        # back to guided weapons when the lesson requires an unguided delivery.
        stations = sorted(aircraft.pylons)
        candidates = {p: {c: n for c, n in loadouts._pylon_stores(aircraft, p).items()
                          if ("mk-82" in n.lower() or "mk82" in n.lower())
                          and loadouts._era_ok(c, recipe.era, year)} for p in stations}
        pylons = {}
        for a, b in loadouts._mirror_pairs([p for p in stations if candidates[p]], stations):
            if a == b:
                continue
            common = set(candidates[a]) & set(candidates[b])
            if common:
                store = min(common, key=lambda c: (len(candidates[a][c]), c))
                pylons[str(a)] = pylons[str(b)] = store
                if len(pylons) >= 4:
                    break
        if not pylons:
            raise RecipeError(f"No paired unguided Mk-82 fit for {aircraft_id}.")
        return {"label": "Unguided Mk-82 training/attack fit", "pylons": pylons}
    fit = loadouts.player_loadout(aircraft_id, "strike", recipe.era, recipe.player_load, year=year)
    # A precision/talk-on scenario needs a visual designator even when the
    # composed bombs are dual-mode GPS weapons rather than pure laser weapons.
    fit = {**fit, "pylons": dict(fit["pylons"])}
    for p in sorted(aircraft.pylons):
        for clsid, name in loadouts._pylon_stores(aircraft, p).items():
            if "litening" in name.lower() or "lantirn targeting" in name.lower():
                fit["pylons"][str(p)] = clsid
                return {**fit, "label": fit["label"] + " — targeting pod fitted"}
    raise RecipeError(f"No verified targeting pod for {aircraft_id}.")
