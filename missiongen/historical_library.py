"""Source-backed reference content; subject dates never imply clearance or unit occupancy."""
from copy import deepcopy
from datetime import date
from functools import lru_cache
import math
import re

from . import __version__
from .resolver import load_json


def _day(value):
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', str(value)):
        raise ValueError('Date must be YYYY-MM-DD')
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError('Date must be YYYY-MM-DD') from exc


def _refs(value, sources):
    if isinstance(value, dict):
        if any(key in value for key in ('path', 'root')):
            raise ValueError('Private source filesystem paths cannot enter the public catalog')
        if 'source_id' in value:
            if value['source_id'] not in sources:
                raise ValueError('Unknown historical source edition')
            src = sources[value['source_id']]
            if not value['pdf_pages'] or any(not 1 <= p <= src['pdf_pages'] for p in value['pdf_pages']):
                raise ValueError('Historical source page outside the supplied edition')
        for child in value.values():
            _refs(child, sources)
    elif isinstance(value, list):
        for child in value:
            _refs(child, sources)


def validate(register):
    """Reject broken provenance, aliases, inferred validity and corrupted coordinates."""
    maps = load_json('maps')
    seen = set()
    for source in register['sources'].values():
        if not re.fullmatch(r'[0-9a-f]{64}', source['sha256']):
            raise ValueError('Historical source requires an edition SHA-256')
        if source.get('public_url') and not source['public_url'].startswith('https://'):
            raise ValueError('Historical source link must use HTTPS')
    _refs(register, register['sources'])
    for row in register['entries']:
        if row['id'] in seen or row['period'] not in register['periods'] or row['topic'] not in register['topics']:
            raise ValueError('Duplicate or unregistered historical reference')
        seen.add(row['id'])
        if any(m not in maps for m in row['maps']):
            raise ValueError('Historical reference names an unsupported map')
        if _day(row['subject_from']) > _day(row['subject_to']):
            raise ValueError('Historical subject period is reversed')
        if row['valid_from'] or row['valid_to']:
            raise ValueError('Reference subject dates cannot certify operational validity')
    for profile in register['profiles'].values():
        if profile['map'] not in maps:
            raise ValueError('Historical profile names an unsupported map')
        if profile['routing_enabled']:
            raise ValueError('Unverified reference profile cannot drive mission routing')
        ids = set()
        for point in profile['points']:
            if point['id'] in ids:
                raise ValueError('Duplicate historical reference point')
            ids.add(point['id'])
            for key, result, sign in [('north_lat', 'latitude_decimal_degrees', 1),
                                      ('west_lon', 'longitude_decimal_degrees', -1)]:
                degrees, minutes = map(float, point['coordinate_raw'][key].split('-'))
                if not 0 <= minutes < 60 or not math.isclose(point[result], sign * (degrees + minutes / 60), abs_tol=1e-10):
                    raise ValueError('Historical coordinate differs from its printed row')
            if point['datum'] is not None or point['valid_from'] or point['valid_to']:
                raise ValueError('Unverified datum or validity must remain unknown')
    for row in register['unit_records']:
        if row['date_precision'] not in ('day', 'month', 'year', 'circa'):
            raise ValueError('Historical event date precision is required')
        expected = {'day': 10, 'month': 7, 'year': 4, 'circa': 10}[row['date_precision']]
        if len(row['event_date']) != expected:
            raise ValueError('Historical event date disagrees with its precision')
        _day(row['event_date'] + {4: '-01-01', 7: '-01', 10: ''}[expected])
        if row['valid_from'] or row['valid_to']:
            raise ValueError('Historical event does not establish continuous unit occupancy')
    return register


@lru_cache(maxsize=1)
def _data():
    return validate(load_json('historical_library'))


def catalog(map_key=None, period=None, topic=None, on=None):
    data = _data()
    if map_key is not None and map_key not in load_json('maps'):
        raise ValueError('Unknown map')
    if period is not None and period not in data['periods']:
        raise ValueError('Unknown historical reference period')
    if topic is not None and topic not in data['topics']:
        raise ValueError('Unknown historical reference topic')
    day = _day(on) if on is not None else None
    rows = [deepcopy(row) for row in data['entries']
            if (not map_key or not row['maps'] or map_key in row['maps'])
            and (not period or row['period'] == period)
            and (not topic or row['topic'] == topic)
            and (not day or _day(row['subject_from']) <= day <= _day(row['subject_to']))]
    return {'schema_version': data['schema_version'], 'app_version': __version__,
            'reviewed_on': data['reviewed_on'], 'scope': data['scope'],
            'limitations': deepcopy(data['limitations']), 'entries': rows,
            'periods': deepcopy(data['periods']), 'topics': deepcopy(data['topics']),
            'sources': deepcopy(data['sources']), 'profiles': deepcopy(data['profiles']),
            'unit_records': deepcopy(data['unit_records']),
            'source_assessments': deepcopy(data['source_assessments'])}


def profile(profile_id):
    row = _data()['profiles'].get(profile_id)
    if row is None:
        raise ValueError('Unknown historical reference profile')
    return deepcopy(row)


def unit_history(map_key=None, base=None, on=None, variant=None):
    """Describe observations, never infer a continuous roster between milestones."""
    if map_key is not None and map_key not in load_json('maps'):
        raise ValueError('Unknown map')
    day = _day(on) if on is not None else None
    rows = []
    for original in _data()['unit_records']:
        if map_key and original.get('map') != map_key or base and original['base'] != base:
            continue
        row = deepcopy(original)
        row['occupancy_certified'] = False
        row['variant_status'] = ('exact_variant_recorded' if variant in row['aircraft_variants'] else
                                 'variant_not_recorded') if variant else 'not_requested'
        if day:
            if row['date_precision'] == 'circa':
                relation = 'approximate_event_date; exact arrival unknown'
            elif len(row['event_date']) < 10:
                relation = 'month_or_year_resolution; exact event day unknown'
            else:
                event = _day(row['event_date'])
                relation = 'event_on_selected_date' if event == day else 'earlier_event' if event < day else 'later_event'
            row['date_relation'] = relation
        rows.append(row)
    return {'app_version': __version__, 'on': on, 'records': rows,
            'scope': 'Station events, transitions and snapshots do not certify continuous unit occupancy.'}


def livery_matches(candidate, dcs_type, country, base, on):
    """Only fully bounded, exact variant/base/unit skin records can claim history.

    Installed IDs and broad era paint eligibility remain distinct from this
    stronger assertion. No punctuation or aircraft-family alias proves a match.
    """
    required = ('livery_id', 'dcs_type', 'country', 'base', 'unit', 'variant',
                'valid_from', 'valid_to', 'sources')
    if not all(candidate.get(key) for key in required) or not candidate.get('installed_id_verified'):
        return False
    if (candidate['dcs_type'], candidate['country'], candidate['base']) != (dcs_type, country, base):
        return False
    if candidate.get('date_precision') != 'day' or not on:
        return False
    day = _day(on)
    if not _day(candidate['valid_from']) <= day <= _day(candidate['valid_to']):
        return False
    # A source-backed continuous station AND aircraft assignment is necessary;
    # a one-day snapshot, later transition, or group movement cannot certify it.
    return candidate.get('station_verified') is True and candidate.get('variant_verified') is True


def mission_references(map_key, on, aircraft_id):
    """Short reference links matching actual map/date/aircraft, not a new scenario."""
    family = 'F-4' if aircraft_id.replace('_', '-').startswith('F-4') else None
    rows = catalog(map_key=map_key, on=on)['entries']
    rows = [r for r in rows if not r['aircraft_families'] or family in r['aircraft_families']]
    rows.sort(key=lambda r: (not bool(r['maps']), r['priority'], r['id']))
    return [{'id': row['id'], 'title': row['title'], 'period': row['period'],
             'sources': row['sources'], 'url': '/api/historical-library#'+row['id'],
             'reference_only': True} for row in rows[:3]]


def reference_lines(rows):
    if not rows:
        return []
    return ['HISTORICAL READING - reference background; not a claim of unit presence or route clearance.',
            *[f"{r['title']} - Historical Library: {r['url']}" for r in rows]]
