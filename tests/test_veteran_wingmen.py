"""Read native missions back: AI wingmen must be in the human's own group."""
import pytest
from missiongen import Recipe, generate
from missiongen.recipe import RecipeError
from missiongen.share import encode_recipe, decode_recipe
from scripts.audit_library import inspect_archive


def build_flight(tmp_path, **settings):
    recipe = Recipe.from_dict({**dict(era='modern', slots=4, veteran_wingmen=3,
        bb_dressing=False, bb_ambient=False, bb_sams=False, bb_tanker=False,
        bb_awacs=False, bb_briefing=True, bb_kneeboard=False, bb_branding=False),
        **settings})
    path = tmp_path / 'wingmen.miz'
    result = generate(recipe, str(path))
    mission = inspect_archive(path)
    groups = [g for g in mission['groups']
              if any(u['skill'] in ('Player', 'Client') for u in g['units'])]
    assert len(groups) == 1
    return recipe, groups[0], mission, result


@pytest.mark.parametrize('start', ['cold', 'warm', 'runway', 'air'])
def test_four_ship_has_one_player_and_three_veterans_in_the_same_group(tmp_path, start):
    recipe, group, mission, result = build_flight(tmp_path, start=start)
    assert [u['skill'] for u in group['units']] == ['Player', 'High', 'High', 'High']
    assert len({u['type'] for u in group['units']}) == 1
    assert len({str(u.get('payload')) for u in group['units']}) == 1
    assert '3 veteran AI wingmen (High skill)' in result['stats']['flight_composition']
    assert any('3 veteran AI wingmen (High skill)' in text
               for text in mission['embedded_text'].values())


def test_human_clients_and_veterans_can_share_the_same_flight(tmp_path):
    _, group, _, result = build_flight(tmp_path, veteran_wingmen=2)
    assert [u['skill'] for u in group['units']] == ['Client', 'Client', 'High', 'High']
    assert '2 multiplayer client aircraft' in result['stats']['flight_composition']


def test_old_four_ship_still_has_four_client_seats(tmp_path):
    _, group, _, result = build_flight(tmp_path, veteran_wingmen=0)
    assert [u['skill'] for u in group['units']] == ['Client'] * 4
    assert 'flight_composition' not in result['stats']


def test_veterans_launch_from_the_carrier_in_the_player_group(tmp_path):
    _, group, _, _ = build_flight(tmp_path, era='coldwar', aircraft='F_14A_135_GR',
        home_airbase='CARRIER', bb_carrier=True, carrier_hull='forrestal', start='warm')
    assert [u['skill'] for u in group['units']] == ['Player', 'High', 'High', 'High']
    assert group['route'][0].get('linkUnit')


def test_formation_keeps_its_instructor_and_adds_veterans_to_dash_two(tmp_path):
    _, group, mission, _ = build_flight(tmp_path, formation='route', start='air')
    assert group['name'] == 'Dash 2'
    assert [u['skill'] for u in group['units']] == ['Player', 'High', 'High', 'High']
    lead = next(g for g in mission['groups'] if g['name'] == 'Formation Lead')
    assert [u['skill'] for u in lead['units']] == ['Excellent']


@pytest.mark.parametrize('value', [-1, 4, '3', True, 1.5])
def test_invalid_veteran_counts_are_field_errors(value):
    with pytest.raises(RecipeError, match='veteran_wingmen'):
        Recipe.from_dict({'slots':4, 'veteran_wingmen':value})


@pytest.mark.parametrize('settings', [
    {'template':'backseat_izlid'},
    {'cq_ride':'cq1', 'home_airbase':'CARRIER', 'aircraft':'FA_18C_hornet'},
])
def test_fixed_procedural_flights_do_not_silently_ignore_wingmen(settings):
    # Validate the count against the fixed-flight restriction before generation.
    if 'cq_ride' in settings:
        from missiongen.cq import RIDE_ORDER
        settings = {**settings, 'cq_ride':RIDE_ORDER[0]}
    with pytest.raises(RecipeError, match='veteran_wingmen'):
        Recipe.from_dict({'slots':4, 'veteran_wingmen':3, **settings})


def test_share_links_keep_the_veteran_count():
    recipe = Recipe(slots=4, veteran_wingmen=3)
    restored = decode_recipe(encode_recipe(recipe))
    assert (restored.slots, restored.veteran_wingmen) == (4, 3)


def test_veterans_are_explained_in_the_generated_brief(tmp_path):
    recipe = Recipe(era='modern', slots=4, veteran_wingmen=3,
                    bb_dressing=False, bb_kneeboard=False, bb_branding=False)
    result = generate(recipe, str(tmp_path/'flight.miz'), brief_dir=str(tmp_path))
    from pathlib import Path
    assert '1 player aircraft + 3 veteran AI wingmen (High skill)' in Path(result['brief_md']).read_text()
    assert Path(result['brief_pdf']).is_file()


def test_pdf_execution_describes_the_actual_veterans():
    from missiongen.builder import StarterBuilder
    from missiongen.brief import _smea
    builder = StarterBuilder(Recipe(era='modern', slots=4, veteran_wingmen=3,
        bb_dressing=False, bb_kneeboard=False, bb_branding=False))
    builder.build()
    assert '1 player aircraft + 3 veteran AI wingmen (High skill)' in _smea(builder.brief_ctx)[2]
