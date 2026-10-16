"""Bounded, aircraft-scoped authoring data, shared by HTTP and MCP.

PyDCS station membership is evidence of a listed store, not certification of
every combined fit, client installation or simulator behavior.
"""
from datetime import date

from . import Recipe, __version__, loadouts
from .authoring import aircraft_type
from .recipe import RecipeError
from .resolver import load_json

KINDS = ('stores', 'loadouts', 'liveries')


def entries(kind, aircraft_key, era=None, on=None):
    aircraft = aircraft_type(aircraft_key)
    if era is not None and era not in load_json('eras'):
        raise RecipeError('Unknown era; use an eras catalog key.')
    year = None
    if on is not None:
        try:
            when = date.fromisoformat(on)
            if when.isoformat() != on:
                raise ValueError()
            year = when.year
        except (ValueError, TypeError):
            raise RecipeError('on must be a valid YYYY-MM-DD date.') from None
        if era:
            window = load_json('eras')[era]['window']
            if not window[0] <= year <= window[1]:
                raise RecipeError('on must fall within the selected era.')
    provenance = {'source': 'vendored PyDCS aircraft station lists',
                  'aircraft': aircraft_key, 'dcs_type': aircraft.id,
                  'installation_verified': False,
                  'combined_fit_certified': False}
    if kind == 'stores':
        stores = {}
        for station in sorted(aircraft.pylons):
            for clsid, name in sorted(loadouts._pylon_stores(aircraft, station).items()):
                row = stores.setdefault(clsid, {'key': clsid, 'label': name, 'clsid': clsid,
                    'stations': [], 'service_window': loadouts.window_for(clsid), **provenance})
                row['stations'].append(station)
        for row in stores.values():
            window = row['service_window']
            row['historical_status'] = ('unknown' if not window else 'not_filtered')
            if window and (era or year is not None):
                lower, upper = ([year, year] if year is not None else load_json('eras')[era]['window'])
                row['historical_status'] = ('within_recorded_window' if (window[0] or 0) <= upper
                    and (window[1] is None or window[1] >= lower) else 'outside_recorded_window')
        return sorted(stores.values(), key=lambda row: (row['label'].casefold(), row['key']))
    if kind == 'loadouts':
        if era is None:
            raise RecipeError('The loadouts catalog requires an era, and optionally on=YYYY-MM-DD.')
        year = year if year is not None else load_json('eras')[era]['year']
        out = []
        for mission_kind in loadouts.KIND_ROLE:
            for weight in loadouts.WEIGHTS:
                fit = loadouts.player_loadout(aircraft.id, mission_kind, era, weight, year=year)
                out.append({'key': f'{mission_kind}:{weight}', 'label': fit['label'] or 'Clean',
                    'recipe': {'aircraft': aircraft_key, 'era': era, 'mission_kind': mission_kind,
                               'player_load': weight, 'player_fit': 'auto', 'player_arm': True,
                               **({'mission_date': on, 'timing_anchor': 'takeoff'} if on else {})},
                    'player_stores': fit['pylons'], 'year': year,
                    'date_basis': 'requested date' if on else 'era default year; mission presets may differ',
                    **provenance})
        return out
    if kind == 'liveries':
        entry = load_json('static_liveries').get('types', {}).get(aircraft.id, {})
        out = []
        for period, countries in entry.get('eras', {}).items():
            if era and period != era:
                continue
            for country, ids in countries.items():
                for ident in ids:
                    out.append({'key': ident, 'label': ident, 'livery_id': ident,
                        'aircraft': aircraft_key, 'dcs_type': aircraft.id,
                        'era': period, 'country': country, 'name_evidence': 'source-backed exact model ID',
                        'sources': entry.get('sources', []),
                        'installation_verified': False, 'historical_identity_verified': False,
                        'selection': 'Mission Editor; no explicit recipe livery selector'})
        # Do not expose the hand-authored, _verified:false pack as real choices.
        # Empty is the honest result when no exact-model IDs have evidence.
        return sorted(out, key=lambda row: (row['key'], row['era'], row['country']))
    raise RecipeError('Unknown authoring catalog kind.')


def catalog(kind, aircraft, era=None, on=None, query='', limit=20, offset=0):
    if kind not in KINDS or not aircraft:
        raise RecipeError('Authoring catalogs require kind=stores/loadouts/liveries and an aircraft catalog key.')
    rows = entries(kind, aircraft, era, on)
    q = query.casefold()
    rows = [row for row in rows if not q or q in str(row).casefold()]
    page = rows[offset:offset + limit]
    next_offset = offset + len(page)
    return {'app_version': __version__, 'items': page, 'total': len(rows), 'offset': offset,
            'has_more': next_offset < len(rows), 'next_offset': next_offset if next_offset < len(rows) else None,
            'limitations': 'Individual station membership only; multi-station interference, aircraft weight '
                'and performance limits and installed modules/skins require separate verification. '
                'Livery coverage is partial; unverified guessed IDs are excluded. Known service windows '
                'do not establish operator-specific availability.'}
