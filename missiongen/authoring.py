"""Strict complete station fits: authored inputs never silently lose a store."""
from collections import Counter

from . import loadouts
from .recipe import RecipeError


def aircraft_type(key):
    from .commplan import unit_type_for
    aircraft = unit_type_for(key)
    if aircraft is None or not getattr(aircraft, 'flyable', False):
        raise RecipeError(f'Unknown flyable aircraft {key!r}; use the aircraft catalog key.')
    return aircraft


def setting_year(r):
    from .resolver import load_json
    from .historical_world import resolve_setting, scenario_date
    if r.mission_date:
        return int(r.mission_date[:4])
    maps = load_json('maps')
    preset = maps[r.map]['presets'].get(r.era)
    if preset is None:
        raise RecipeError(f'{r.map} has no {r.era} preset for player_stores date resolution.')
    preset = dict(preset)
    if r.lineup:
        preset.update(maps[r.map].get('lineups', {}).get(r.lineup, {}))
    return scenario_date(resolve_setting(r.map, r.era, preset, r.template), load_json('eras')[r.era]).year


def explicit_fit(r, *, year=None):
    aircraft = aircraft_type(r.aircraft)
    pylons = r.player_stores
    if not isinstance(pylons, dict) or len(pylons) > 64:
        raise RecipeError('player_stores must be a complete station-to-CLSID object with at most 64 stations.')
    year = setting_year(r) if year is None else year
    warnings = []
    for station, clsid in pylons.items():
        if (not isinstance(station, str) or len(station) > 3 or not station.isascii() or not station.isdecimal()
                or station != str(int(station)) or int(station) not in aircraft.pylons):
            raise RecipeError(f'player_stores station {station!r} is not a station on {r.aircraft}.')
        legal = loadouts._pylon_stores(aircraft, int(station))
        if not isinstance(clsid, str) or clsid not in legal:
            raise RecipeError(f'player_stores station {station}: CLSID {clsid!r} is not listed for {r.aircraft}; use the stores catalog.')
        window = loadouts.window_for(clsid)
        if window and not ((window[0] or 0) <= year and (window[1] is None or year <= window[1])):
            msg = f'Station {station}: {legal[clsid]} is outside its recorded service window {window} for {year}.'
            if not r.allow_anachronistic_stores:
                raise RecipeError(msg + ' Set allow_anachronistic_stores=true only for an intentional fictional fit.')
            warnings.append('Fictional equipment override: ' + msg)
        elif not window:
            warnings.append(f'Station {station}: service dates for {legal[clsid]} are unknown; historical suitability is unverified.')
    counts = Counter(loadouts._pylon_stores(aircraft, int(p))[c] for p, c in pylons.items())
    label = ', '.join(f'{count}x {name}' for name, count in sorted(counts.items())) or 'Clean — no external stores'
    return {'pylons': dict(pylons), 'label': 'Exact author fit: ' + label, 'warnings': warnings}


def validate_authoring(r):
    if r.allow_anachronistic_stores and r.player_stores is None:
        raise RecipeError('allow_anachronistic_stores requires an explicit player_stores fit.')
    if r.player_stores is None:
        return
    from .build_context import CREW_OPS_TEMPLATES, _scenario_templates
    tpl = _scenario_templates().get(r.template, {})
    if (not r.player_arm or r.player_fit != 'auto' or r.cq_ride or r.formation
            or r.template in CREW_OPS_TEMPLATES or tpl.get('wk_ride') or tpl.get('formation')):
        raise RecipeError('player_stores requires player_arm=true, player_fit=auto and a normal player flight; fixed training fits own their stores.')
    explicit_fit(r)


def apply_explicit(group, fit):
    """Clear all old stores, write exactly the requested fit, then verify it."""
    for unit in group.units:
        unit.pylons = {}
    for station, clsid in sorted(fit['pylons'].items(), key=lambda row: int(row[0])):
        group.load_pylon((int(station), {'clsid': clsid}), int(station))
    for unit in group.units:
        actual = {str(p): store['CLSID'] for p, store in unit.pylons.items()}
        if actual != fit['pylons']:
            raise RecipeError('The aircraft did not retain the complete player_stores fit; no mission was returned.')
