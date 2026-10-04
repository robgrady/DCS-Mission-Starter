"""Catalog promises and discoverable limits agree with validation and downloads."""
import io
import json
from pathlib import Path
import zipfile

import anyio
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from mcp import Client
from pypdf import PdfReader
import pytest

from missiongen import Recipe, tracks
from missiongen.recipe import RecipeError
from missiongen.resolver import load_json
from server.app import app
from server.mcp_server import mcp
from server.recipe_contract import recipe_json_schema
from test_library_discovery import library_site, page  # real published-pack browser

ROOT = Path(__file__).resolve().parent.parent
BOUNDS = {
    'slots': (1, 4), 'veteran_wingmen': (0, 3), 'dress_fill': (0, 100),
    'pattern_count': (1, 8), 'threat_intensity': (1, 5), 'timing_hold_min': (0, 15),
}


@pytest.mark.parametrize('name', BOUNDS)
def test_advertised_numeric_bounds_accept_edges_and_refuse_outside(name):
    schema = recipe_json_schema()
    lower, upper = BOUNDS[name]
    assert (schema['properties'][name]['minimum'], schema['properties'][name]['maximum']) == (lower, upper)
    validator = Draft202012Validator(schema)
    for value in (lower, upper):
        data = {'slots': 4, name: value}
        validator.validate(data)
        Recipe.from_dict(data)
    for value in (lower - 1, upper + 1):
        data = {'slots': 4, name: value}
        assert list(validator.iter_errors(data)), (name, value)
        with pytest.raises(RecipeError, match=name):
            Recipe.from_dict(data)


@pytest.mark.parametrize('slots', range(1, 5))
def test_schema_seat_rules_match_engine_for_each_flight_size(slots):
    validator = Draft202012Validator(recipe_json_schema())
    for ai in range(5):
        data = {'slots': slots, 'veteran_wingmen': ai}
        if ai < slots:
            validator.validate(data)
            Recipe.from_dict(data)
        else:
            assert list(validator.iter_errors(data)), data
            with pytest.raises(RecipeError, match='veteran_wingmen'):
                Recipe.from_dict(data)


def test_pattern_bounds_follow_the_owner_without_a_schema_copy(monkeypatch):
    from missiongen import pattern
    monkeypatch.setattr(pattern, 'MAX_COUNT', 6)
    assert recipe_json_schema()['properties']['pattern_count']['maximum'] == 6
    Recipe.from_dict({'pattern_count': 6})
    with pytest.raises(RecipeError, match='pattern_count'):
        Recipe.from_dict({'pattern_count': 7})


@pytest.mark.parametrize('data', [
    {'dress_fill': None, 'dress_mix': None, 'target_packages': None},
    {'template': 'qf_bfm', 'era': 'modern'},
    {'callsign': '   ' + 'R' * 20 + '   '},
    {'dress_overrides': {'Nellis': 0, 'Creech': 100}, 'dress_mix': {'F-4E-45MC': 0}},
    {'target_packages': ['depot', 'convoy', 'c2_site']},
])
def test_schema_preserves_nullable_template_omission_and_normalization(data):
    Draft202012Validator(recipe_json_schema()).validate(data)
    recipe = Recipe.from_dict(data)
    if data.get('template'):
        assert recipe.start == 'air' and recipe.slots == 1
    if data.get('callsign'):
        assert recipe.callsign == 'R' * 20


@pytest.mark.parametrize('data', [
    {'dress_overrides': {'Nellis': 101}}, {'dress_overrides': {'Nellis': -1}},
    {'dress_overrides': {'Nellis': True}}, {'dress_mix': {'F-4E-45MC': -1}},
    {'dress_mix': {'F-4E-45MC': '2'}}, {'target_packages': []},
    {'target_packages': ['depot'] * 4}, {'target_packages': ['not_a_package']},
])
def test_nested_constraints_are_discoverable_and_enforced(data):
    assert list(Draft202012Validator(recipe_json_schema()).iter_errors(data))
    with pytest.raises(RecipeError):
        Recipe.from_dict(data)


def test_http_openapi_mcp_tool_and_resource_publish_the_same_limits():
    schema = recipe_json_schema()
    Draft202012Validator.check_schema(schema)
    with TestClient(app) as client:
        assert client.get('/api/recipe-schema').json() == schema
        request = client.get('/openapi.json').json()['components']['schemas']['GenerateRequest']['properties']['recipe']
        assert request['allOf'] == schema['allOf']
        assert request['properties']['slots']['maximum'] == 4
    async def work():
        async with Client(mcp) as client:
            result = await client.call_tool('sortiestarter_get_recipe_schema')
            assert not result.is_error and result.structured_content == schema
            resource = await client.read_resource('sortiestarter://recipe-schema')
            assert json.loads(resource.contents[0].text) == schema
    anyio.run(work)


def test_catalog_label_matches_unchanged_gwot_window_and_authored_date():
    with TestClient(app) as client:
        options = client.get('/api/options').json()
    era = options['eras']['gwot']
    assert era['window'] == [2003, 2025]
    assert load_json('eras')['gwot']['year'] == 2016
    assert era['label'] == 'War on Terror (2003-2025)'
    from missiongen.historical_world import preview
    assert preview('afghanistan', 'gwot')['date'] == '2011-06-21'


def test_proud_phantom_intro_counts_drag_and_every_tactics_ride():
    from scripts.add_white_knights import TRACKS
    track = tracks.get('wk_proud_phantom')
    rides = tracks.rides('wk_proud_phantom')
    assert len(rides) == 11
    assert track['premise'] == TRACKS['wk_proud_phantom']['premise']
    assert 'Eleven rides: the tanker drag' in track['premise']


def test_published_proud_phantom_manifest_and_printed_guides_agree():
    path = ROOT/'packs/wk_proud_phantom.sspack'
    if not path.is_file():
        pytest.skip('Published archive checks need local release packs.')
    with zipfile.ZipFile(path) as archive:
        man = json.loads(archive.read('pack.json'))
        assert man['version'] == '3.0.7'
        assert len(man['syllabus']) == 11
        assert man['library']['premise'] == tracks.get('wk_proud_phantom')['premise']
        assert 'Eleven rides: the tanker drag' in archive.read(man['docs']['readme']).decode()
        pdf = PdfReader(io.BytesIO(archive.read(man['docs']['guide'])))
        assert 'Eleven rides: the tanker drag' in ' '.join(pdf.pages[0].extract_text().split())


def test_corrected_label_and_collection_intro_reach_the_real_browser(page):
    page.evaluate('showView("builder");showScreen("theater")')
    page.locator('#maps .card[data-k="iraq"]').click()
    era = page.locator('#eras .card[data-k="gwot"]')
    assert era.is_visible() and era.inner_text() == 'War on Terror (2003-2025)'
    era.click()
    assert page.evaluate('recipe().era') == 'gwot'
    page.evaluate('showView("library")')
    page.evaluate("openDetail('pack_wk_proud_phantom')")
    page.get_by_text('About this collection', exact=True).click()
    assert 'Eleven rides: the tanker drag' in page.locator('#dcardinner').inner_text()
    assert page.locator('#dcardinner .evlinks a[aria-label^="Download mission "]').count() == 11
