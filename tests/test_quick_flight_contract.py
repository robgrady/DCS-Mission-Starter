"""Quick Flight must only enable combinations accepted by the aircraft/era domain."""
import json

from fastapi.testclient import TestClient

from missiongen import aar
from missiongen.builder import aircraft_in_era
from missiongen.pending import pending_aircraft
from server.app import app
from test_mission_kit_wiring import run_js


def test_every_quick_flight_combination_respects_aircraft_map_and_template():
    with TestClient(app) as client:
        opt = client.get('/api/options').json()
    script = ('const OPT='+json.dumps(opt)+';const ownedAc=()=>null;\n'
              + "let results=[];for(const type of ['qf_tanker','qf_bfm','qf_guns','qf_sam']){"
              + "for(const map of Object.keys(OPT.maps)){for(const ac of OPT.aircraft){"
              + "results.push({type,map,ac:ac.key,era:qfEra(type,map,ac.key)});}}}"
              + "console.log(JSON.stringify({results,tankers:qfAcList('qf_tanker').list.map(a=>a.key),bfm:qfAcList('qf_bfm').list.map(a=>a.key)}));")
    out = run_js(script, ['qfTplEras', 'qfMapsFor', 'qfEra', 'qfAcList'])
    roster = {a['key']: a for a in opt['aircraft']}
    assert out['results'] and any(r['era'] for r in out['results'])
    for result in out['results']:
        a = roster[result['ac']]
        if result['era']:
            assert result['era'] in opt['templates'][result['type']]['eras']
            assert result['era'] in opt['maps'][result['map']]['presets']
            assert aircraft_in_era(result['ac'], opt['eras'][result['era']])
            assert not a.get('upcoming')
            if result['type'] == 'qf_tanker':
                assert a['can_refuel']
            if result['type'] == 'qf_bfm':
                assert a['kind'] == 'plane'
        elif not a.get('upcoming') and (result['type'] != 'qf_tanker' or a['can_refuel']) and (result['type'] != 'qf_bfm' or a['kind'] == 'plane'):
            template = opt['templates'][result['type']]
            valid = (not template['maps'] or result['map'] in template['maps']) and any(
                era in opt['maps'][result['map']]['presets'] and aircraft_in_era(result['ac'], opt['eras'][era])
                for era in template['eras'])
            assert not valid, result
    assert all(roster[key]['can_refuel'] for key in out['tankers'])
    assert 'F_5E_3' not in out['tankers'] and 'F_14B_U' in out['tankers']
    assert all(roster[key]['kind'] == 'plane' for key in out['bfm'])


def test_refueling_metadata_uses_dcs_ids_including_pending_aircraft():
    with TestClient(app) as client:
        roster = client.get('/api/options').json()['aircraft']
    pending = pending_aircraft()
    for aircraft in roster:
        ident = pending.get(aircraft['key'], {}).get('provisional_id', aircraft['id'])
        assert aircraft['can_refuel'] == aar.can_refuel(ident)
