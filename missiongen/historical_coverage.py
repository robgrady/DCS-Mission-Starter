"""Audited corridor/airspace inventory. Availability never certifies history."""
from copy import deepcopy
from datetime import date

from . import __version__
from .resolver import load_json


EVIDENCE = {
    'documented_structure': 'Documented structure',
    'reported_track': 'Reported operational track',
    'training_design': 'Training design',
}


def element(element_id):
    """Return independent metadata; callers cannot mutate the cached register."""
    return deepcopy(load_json('historical_coverage')['elements'][element_id])


def temporal_status(entry, on):
    """A source/reference date is never substituted for operational validity."""
    day = date.fromisoformat(str(on)[:10])
    start, end = entry['valid_from'], entry['valid_to']
    if (start and day < date.fromisoformat(start)) or (end and day > date.fromisoformat(end)):
        return 'outside_recorded_validity'
    return 'within_recorded_validity' if start and end else 'operational_validity_unknown'


def report(map_key=None, era=None):
    maps, eras = load_json('maps'), load_json('eras')
    if map_key is not None and map_key not in maps:
        raise ValueError('Unknown map')
    if era is not None and era not in eras:
        raise ValueError('Unknown era')
    if map_key and era and era not in maps[map_key]['presets']:
        raise ValueError('This map does not offer that era')
    register = load_json('historical_coverage')
    rows = []
    for cell in register['map_eras']:
        if map_key and cell['map'] != map_key or era and cell['era'] != era:
            continue
        entries = [deepcopy(v) for v in register['elements'].values()
                   if v['map'] == cell['map'] and cell['era'] in v['eras']]
        network = sum(e['dataset'] == 'network' for e in entries)
        tactical = sum(e['dataset'] == 'tactical' for e in entries)
        overlay = sum(e['dataset'] == 'overlay' for e in entries)
        status = ('partial_network' if network else 'tactical_only' if tactical
                  else 'overlay_only' if overlay else 'no_drawn_geometry')
        findings = [deepcopy(f) for f in register['research_findings']
                    if f['id'] in cell['research_findings']]
        rows.append({**deepcopy(cell), 'map_label': maps[cell['map']]['label'],
                     'era_label': eras[cell['era']]['label'], 'status': status,
                     'counts': {'route_segments': network, 'tactical_axes': tactical,
                                'overlay_features': overlay},
                     'dated_validity_certified': False, 'elements': entries,
                     'research': findings})
    return {'schema_version': register['schema_version'], 'app_version': __version__,
            'reviewed_on': register['reviewed_on'], 'scope': register['scope'],
            'limitations': register['limitations'], 'map_eras': rows}


def visual_tag(entry):
    return {'documented_structure': 'DOC', 'reported_track': 'REPORTED',
            'training_design': 'TRAINING'}[entry['evidence']]


def brief_line(entry):
    return (f"{EVIDENCE[entry['evidence']]}; {entry['geometry_accuracy'].replace('_', ' ')}. "
            'Operational validity unknown; drawn for exercise reference, not crossing permission.')
