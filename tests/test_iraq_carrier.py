"""Iraq Gulf support: geography, saved ship links and assembled Builder controls.

The geographic mask is a schematic shoreline, not a DCS land-mask query.
These checks do not certify simulator flight, historical naval deployment or
the latest terrain's beacon database.
"""
import zipfile

import pytest
from dcs import lua, mapping
from dcs.mission import Mission
from missiongen import Recipe, StarterBuilder
from missiongen.comms import CommsPlan
from missiongen.naval import add_carrier_group
from missiongen.resolver import load_json
from missiongen.terrains.iraq import Iraq
from test_theater_chart import _is_water
from test_refactor_browser import site


def test_iraq_carrier_screen_and_entire_wind_window_stay_offshore():
    cfg = load_json('maps')['iraq']
    assert cfg.get('carrier'), 'Iraq must offer a carrier anchor'
    terrain = Iraq()
    # Exercise the actual naval constructor, including every available Iraq
    # hull, all wind bearings and intermediate route/screen positions.
    for key, hull in load_json('carrier_decks')['hulls'].items():
        if key.startswith('_') or not isinstance(hull, dict) or 'eras' not in hull:
            continue
        eras = set(hull['eras']) & set(cfg['presets'])
        if not eras:
            continue
        for wind in range(0, 360, 15):
            mission = Mission(terrain)
            mission.weather.wind_at_ground.direction = wind
            mission.weather.wind_at_ground.speed = 8
            group, brc = add_carrier_group(mission, mission.country('USA'),
                sorted(eras)[0], 'blue', cfg, mission.weather,
                CommsPlan(), [], hull_key=key)
            assert group
            start, end = group.points[0].position, group.points[-1].position
            assert start.distance_to_point(end) == pytest.approx(40000)
            assert abs((brc-cfg['carrier']['heading']+180) % 360-180) <= 60
            for unit in group.units:
                for step in range(21):
                    fraction = step/20
                    point = mapping.Point(unit.position.x + (end.x-start.x)*fraction,
                                          unit.position.y + (end.y-start.y)*fraction, terrain)
                    ll = point.latlng()
                    assert terrain.bounds.point_in_rect(point), (key, wind, step)
                    assert _is_water('persiangulf', ll.lat, ll.lng), (key, wind, step, ll)


@pytest.mark.parametrize('map_key,era,aircraft', [('iraq','coldwar','F_14A_135_GR'),
    ('iraq','modern','FA_18C_hornet'), ('iraq','gwot','FA_18C_hornet'),
    ('caucasus','coldwar','F_14A_135_GR'), ('caucasus','modern','FA_18C_hornet')])
def test_saved_iraq_mission_links_launch_and_recovery_to_the_carrier(tmp_path,map_key,era,aircraft):
    recipe = Recipe.from_dict(dict(map=map_key, era=era, aircraft=aircraft,
        home_airbase='CARRIER', bb_carrier=True, start='warm',
        bb_ambient=False, bb_dressing=False, bb_sams=False, bb_kneeboard=False,
        bb_targets=True, bb_route=True, timing_package=True))
    builder = StarterBuilder(recipe)
    mission = builder.build()
    path = tmp_path/'iraq.miz'
    mission.save(str(path))
    with zipfile.ZipFile(path) as archive:
        native = lua.loads(archive.read('mission').decode())['mission']
        dictionary = archive.read('l10n/DEFAULT/dictionary').decode()
    countries = list(native['coalition']['blue']['country'].values())
    ships = [g for country in countries for g in country.get('ship', {}).get('group', {}).values()]
    planes = [g for country in countries for g in country.get('plane', {}).get('group', {}).values()]
    carrier = ships[0]['units'][1]['unitId']
    player = next(g for g in planes if any(u.get('skill') in ('Player','Client') for u in g['units'].values()))
    route = list(player['route']['points'].values())
    assert route[0]['linkUnit'] == carrier
    assert route[-1]['linkUnit'] == carrier and route[-1]['type'] == 'Land'
    assert builder.stats['route_legs'][0]['from'] == 'CARRIER'
    first_leg = builder.stats['route_legs'][0]
    carrier_pos = mapping.Point(ships[0]['units'][1]['x'], ships[0]['units'][1]['y'], mission.terrain)
    waypoint = mapping.Point(route[1]['x'], route[1]['y'], mission.terrain)
    assert first_leg['nm'] == round(carrier_pos.distance_to_point(waypoint)/1852, 1)
    target = mapping.Point(route[-2]['x'], route[-2]['y'], mission.terrain)
    assert carrier_pos.distance_to_point(waypoint) < .6 * carrier_pos.distance_to_point(target), \
        'WP1 must be on the outbound transit from the carrier, not beyond it near a land base'
    assert builder.stats['route'].endswith('> CARRIER')
    package = next(g for g in planes if g['name'] == 'Package')
    package_recovery = list(package['route']['points'].values())[-1]
    assert package_recovery['linkUnit'] == carrier and package_recovery['type'] == 'Land'
    if map_key == 'iraq':
        assert 'authored training force' in dictionary
    assert not any('no carrier anchor' in warning for warning in builder.warnings)


@pytest.mark.parametrize('width',[1280,390])
def test_iraq_carrier_is_selectable_in_the_real_builder(site,width):
    pw = pytest.importorskip('playwright.sync_api')
    with pw.sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={'width':width,'height':900})
        errors = []
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(site)
        page.wait_for_function('OPT !== null && NAV_READY')
        assert page.evaluate('OPT.maps.iraq.has_carrier')
        page.evaluate('''applyRecipe({map:"iraq",era:"modern",aircraft:"FA_18C_hornet",
          bb_carrier:true,home_airbase:"CARRIER",carrier_hull:"stennis"});
          showView("builder");showScreen("flight");''')
        assert page.locator('#carrierstep').is_visible()
        restored = page.evaluate('decodeRecipe(encodeRecipe(recipe()))')
        assert restored['map'] == 'iraq' and restored['home_airbase'] == 'CARRIER'
        assert restored['bb_carrier'] and restored['carrier_hull'] == 'stennis'
        assert not errors
        browser.close()
