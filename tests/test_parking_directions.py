"""Exact surveyed direction survives generation, imports, and stand identity."""
import json
import math
from types import SimpleNamespace
import zipfile

import dcs.lua as lua
import pytest

from missiongen import Recipe, generate
from missiongen.dressing import _measured_slot_heading
from missiongen.resolver import load_json, resolve_terrain
from scripts import import_survey
from scripts.build_survey_mission import build


def slot(sid=1, name='02', x=10, y=20):
    return SimpleNamespace(crossroad_idx=sid, slot_name=name,
                           position=SimpleNamespace(x=x, y=y))


def record(heading, name='02', x=10, y=20):
    return {'slot_name': name, 'heading': heading, 'x': x, 'y': y}


def test_duplicate_display_names_keep_independent_directions():
    field = {'slots': {'02': 90}, 'stands': {'1': record(30), '2': record(220, x=40)}}
    assert _measured_slot_heading(field, slot()) == 30
    assert _measured_slot_heading(field, slot(2, x=40)) == 220
    assert _measured_slot_heading({'slots': {'02': 90}}, slot()) == 90


@pytest.mark.parametrize('changed', [record(30, name='03'), record(30, x=10.1)])
def test_export_identity_drift_cannot_apply_a_stale_stand_measurement(changed):
    field = {'slots': {'02': 90}, 'stands': {'1': changed}}
    assert _measured_slot_heading(field, slot()) is None


def test_partial_import_retains_previous_fields_and_measurements():
    terrain = SimpleNamespace(airports={'Test': SimpleNamespace(parking_slots=[slot(1), slot(2, x=40)])})
    old = {'other_map': {'Other': 180}, 'map': {'Test': {'default': 90, 'slots': {'02': 90},
            'stands': {'1': record(30)}}}}
    parsed = import_survey.parse_survey('INFO PSURVEY2_OUT|Test|2|02|220.123|40|20')
    merged = import_survey.merge_survey(old, 'map', parsed, terrain)
    assert old['map']['Test']['stands'] == {'1': record(30)}
    assert merged['other_map'] == old['other_map']
    assert merged['map']['Test']['slots'] == {'02': 90}
    assert merged['map']['Test']['stands']['1'] == record(30)
    assert merged['map']['Test']['stands']['2'] == record(220.123, x=40)
    assert import_survey.parse('INFO PSURVEY_OUT|Test|02|359.5') == {'Test': {'02': 359.5}}


@pytest.mark.parametrize('line', [
    'PSURVEY2_OUT|Test|1|02|nan|10|20',
    'PSURVEY2_OUT|Test|1|02|30|inf|20',
    'PSURVEY2_OUT|Test|bad|02|30|10|20',
    'PSURVEY_OUT|Test|02|nan',
])
def test_invalid_measurements_are_rejected(line):
    with pytest.raises(ValueError):
        import_survey.parse_survey(line)


def test_wrong_map_or_moved_stand_rejected_before_any_data_changes():
    terrain = SimpleNamespace(airports={'Test': SimpleNamespace(parking_slots=[slot()])})
    old = {'map': {'Test': {'slots': {'02': 90}}}}
    for line in ('PSURVEY2_OUT|Other|1|02|30|10|20', 'PSURVEY2_OUT|Test|1|02|30|12|20'):
        with pytest.raises(ValueError):
            import_survey.merge_survey(old, 'map', import_survey.parse_survey(line), terrain)
    assert old == {'map': {'Test': {'slots': {'02': 90}}}}


def test_failed_publish_preserves_the_existing_measurements(tmp_path, monkeypatch):
    path = tmp_path / 'headings.json'
    path.write_text('{"old": true}')
    def fail(*args):
        raise OSError('disk failure')
    monkeypatch.setattr(import_survey.os, 'replace', fail)
    with pytest.raises(OSError):
        import_survey.atomic_write(path, {'new': True})
    assert path.read_text() == '{"old": true}'
    assert list(tmp_path.iterdir()) == [path]


def test_generated_statics_face_the_measured_direction_without_jitter(tmp_path):
    recipe = Recipe.from_dict({'map': 'nevada', 'era': 'modern', 'aircraft': 'FA_18C_hornet',
        'seed': 3, 'bb_ambient': False, 'bb_kneeboard': False})
    path = tmp_path / 'direction.miz'
    generate(recipe, str(path))
    with zipfile.ZipFile(path) as z:
        mission = lua.loads(z.read('mission').decode())['mission']
    terrain = resolve_terrain(load_json('maps')['nevada']['terrain_class'])()
    stands = {f'x{s.crossroad_idx}': s for s in terrain.airports['Nellis'].parking_slots}
    headings = load_json('parking_headings')['nevada']['Nellis']['slots']
    checked = 0
    for country in mission['coalition']['blue']['country'].values():
        for group in country.get('static', {}).get('group', {}).values():
            name = group['name']
            if not name.startswith('ST Nellis '):
                continue
            stand = stands[name.split()[2]]
            expected = headings.get(str(stand.slot_name))
            if expected is None:
                continue
            for unit in group['units'].values():
                assert math.degrees(unit['heading']) % 360 == pytest.approx(expected % 360, abs=1e-6)
                checked += 1
    assert checked >= 10


def test_survey_leaves_all_stands_available_and_exports_unique_ids(tmp_path):
    terrain = resolve_terrain(load_json('maps')['thechannel']['terrain_class'])()
    airport = next(ap for ap in terrain.airport_list() if ap.parking_slots)
    path = tmp_path / 'survey.miz'
    build('thechannel', [airport.name], path)
    with zipfile.ZipFile(path) as z:
        mission = lua.loads(z.read('mission').decode())['mission']
    units = []
    observer = []
    for country in mission['coalition']['blue']['country'].values():
        for kind in ('plane', 'helicopter'):
            for group in country.get(kind, {}).get('group', {}).values():
                for unit in group['units'].values():
                    if unit['name'].startswith('PSURVEY2|'):
                        units.append(unit['name'])
                    if unit.get('skill') == 'Player':
                        observer.append(group)
    eligible = [s for s in airport.parking_slots if s.airplanes or s.helicopter]
    assert len(units) == len(eligible) and len(set(units)) == len(units)
    assert len(observer) == 1 and observer[0]['route']['points'][1]['type'] == 'Turning Point'
    assert 'PSURVEY2_OUT|' in json.dumps(mission)


def test_iraq_capture_covers_every_eligible_stand_and_generated_headings(tmp_path):
    terrain = resolve_terrain(load_json('maps')['iraq']['terrain_class'])()
    fields = load_json('parking_headings')['iraq']
    assert len(fields) == 20
    assert sum(len(f['stands']) for f in fields.values()) == 1397
    for ap in terrain.airport_list():
        expected = {str(s.crossroad_idx) for s in ap.parking_slots if s.airplanes or s.helicopter}
        assert set(fields[ap.name]['stands']) == expected
    path = tmp_path / 'iraq-directions.miz'
    generate(Recipe.from_dict({'map': 'iraq', 'era': 'modern', 'aircraft': 'FA_18C_hornet',
        'home_airbase': 'Al-Asad Airbase', 'dress_overrides': {'Al-Asad Airbase': 50},
        'seed': 3, 'bb_ambient': False, 'bb_kneeboard': False}), str(path))
    with zipfile.ZipFile(path) as z:
        mission = lua.loads(z.read('mission').decode())['mission']
    stands = {f'x{s.crossroad_idx}': s for s in terrain.airports['Al-Asad Airbase'].parking_slots}
    checked = 0
    for coal in mission['coalition'].values():
        for country in coal.get('country', {}).values():
            for group in country.get('static', {}).get('group', {}).values():
                prefix = 'ST Al-Asad Airbase '
                if not group['name'].startswith(prefix):
                    continue
                stand = stands[group['name'][len(prefix):].split()[0]]
                expected = _measured_slot_heading(fields['Al-Asad Airbase'], stand)
                for unit in group['units'].values():
                    assert math.degrees(unit['heading']) % 360 == pytest.approx(expected, abs=1e-6)
                    checked += 1
    assert checked >= 10
