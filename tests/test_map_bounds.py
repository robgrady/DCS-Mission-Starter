"""Validation and native generation must agree for every published map."""
import anyio
from mcp import Client
import pytest

from missiongen import Recipe
from missiongen.map_bounds import catalog_bounds, check_position, contains, normalized_bounds
from missiongen.recipe import RecipeError
from missiongen.resolver import load_json, resolve_terrain
from server.catalog_routes import options
from server.mcp_server import mcp

MAPS = load_json('maps')


@pytest.mark.parametrize('key', MAPS)
def test_all_maps_accept_their_center_airfields_and_carrier_anchor(key):
    terrain = resolve_terrain(MAPS[key]['terrain_class'])()
    b = catalog_bounds(key)
    limits = tuple(b[k] for k in ('x_min', 'x_max', 'y_min', 'y_max'))
    check_position({'x':(b['x_min']+b['x_max'])/2, 'y':(b['y_min']+b['y_max'])/2}, key, 'center')
    for airport in terrain.airports.values():
        p = airport.position
        assert contains(limits, p.x, p.y), airport.name
        ll = p.latlng()
        check_position({'lat':ll.lat,'lon':ll.lng}, key, airport.name)
    if 'carrier' in MAPS[key]:
        check_position(MAPS[key]['carrier']['anchor'], key, 'carrier')
    for xy in ({'x':b['x_min']-1,'y':b['y_min']},
               {'x':b['x_max']+1,'y':b['y_max']},
               {'x':b['x_min'],'y':b['y_min']-1},
               {'x':b['x_max'],'y':b['y_max']+1}):
        with pytest.raises(RecipeError, match='outside.*map bounds'):
            check_position(xy, key, 'start_position')
    assert b['units'] == 'metres' and b['axes'] == {'x':'north','y':'east'}


def test_reversed_vendor_rectangles_are_normalized_without_vendor_mutation():
    for key in ('syria','sinai','normandy','persiangulf'):
        t = resolve_terrain(MAPS[key]['terrain_class'])()
        raw = (t.bounds.bottom,t.bounds.top,t.bounds.left,t.bounds.right)
        assert raw[0] > raw[1]  # the regression: native point_in_rect always false
        x0,x1,y0,y1 = normalized_bounds(t)
        assert x0 < x1 and y0 < y1
        check_position({'x':(x0+x1)/2,'y':(y0+y1)/2}, key, 'start_position')
        assert raw == (t.bounds.bottom,t.bounds.top,t.bounds.left,t.bounds.right)


@pytest.mark.parametrize('field', ['start_position','map_view'])
def test_outside_coordinates_fail_recipe_validation_before_build(field):
    position = {'x':1e12,'y':1e12}
    value = position if field == 'start_position' else {'center':position}
    with pytest.raises(RecipeError, match=field):
        Recipe.from_dict({'map':'syria','start':'air',field:value})


def test_syria_exact_start_and_view_survive_native_save(tmp_path):
    from test_precision_recipe import BASE, save, human_group, values
    # Near Abu al-Duhur: a real in-map location rejected by 1.120.1.
    pos = {'lat':35.732306452623504,'lon':37.10412796442225}
    r = Recipe.from_dict({**BASE, 'map':'syria','start_position':pos,
        'start_altitude':4000,'player_slot':'player',
        'map_view':{'center':pos,'zoom':150000}})
    _, m, n = save(r, tmp_path/'syria.miz')
    u = next(iter(values(human_group(n)['units'])))
    assert u['x'] == pytest.approx(76048.957031)
    assert u['y'] == pytest.approx(111344.925781)
    assert n['map']['centerX'] == pytest.approx(u['x'])
    assert n['map']['centerY'] == pytest.approx(u['y'])
    assert m.map.position.latlng().lat == pytest.approx(pos['lat'])


def test_mcp_map_catalog_publishes_same_bounds_and_rejects_before_generation():
    async def run():
        async with Client(mcp) as client:
            item = await client.call_tool('sortiestarter_get_catalog_item',
                {'params':{'kind':'maps','key':'syria'}})
            assert not item.is_error
            # Public HTTP and MCP share the exact same map metadata.
            assert item.structured_content['item']['bounds'] == options()['maps']['syria']['bounds']
            for name in ('start_position','map_view'):
                pos = {'x':1e12,'y':1e12}
                result = await client.call_tool('sortiestarter_validate_recipe',
                    {'params':{'recipe':{'map':'syria','start':'air',
                     name:pos if name == 'start_position' else {'center':pos}}}})
                assert result.is_error and 'outside the selected map bounds' in result.content[0].text
    anyio.run(run)
