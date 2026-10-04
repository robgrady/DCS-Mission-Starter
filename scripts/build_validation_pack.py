"""Produce four native flight-check missions and one DKS import fixture."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import zipfile
from missiongen import Recipe, __version__
from server.mission_kit import build_kit
from scripts.audit_library import inspect_archive

CASES = [
 ('convoy', {'template':'af_convoy_overwatch','seed':7},
  'Observe all four friendly convoy trucks move along their road route. Approach the ambush zone; confirm the hostile group activates once, then engage and recover. Record movement, activation, attack and recovery separately.'),
 ('jtac', {'template':'af_tic_cas','seed':7},
  'Tune 30.000 MHz FM. Request tasking from Pointer. Confirm a hostile target is designated with the briefing laser code and a usable native JTAC response; deliver the carried guided weapon without hitting the friendly patrol, then recover.'),
 ('a6', {'template':'cv_alpha_strike_escort','seed':7},
  'Observe the A-6 STRIKE group proceed to its assigned depot, release bombs, then return and land on the linked carrier. Record attack and landing separately; surviving or reaching a waypoint alone is not a pass.'),
 ('tarps', {'template':'f14_tarps_recon','seed':7},
  'Confirm the TARPS pod is fitted on station 6 in the F-14B(U). Follow the mission brief and Heatblur manual to operate it, fly the reconnaissance pass and inspect the recorded imagery. Pod presence alone is not a recording pass; recover after the pass.'),
 ('dks', {'map':'caucasus','era':'modern','aircraft':'F_14B_U','seed':11203,
          'slots':4,'veteran_wingmen':3,'bb_route':True,'bb_targets':True,
          'bb_dressing':False,'bb_ambient':False,'comms':{'flight_common':307.725,'tanker':271.5}},
  'Import mission.miz into a new unpublished DKS kneeboard. Select the human flight. Compare native route, aircraft, human/AI roles, payload, radio presets, tanker/AWACS and drawings. Compare sidecars manually; ZIP support and automatic ATO posting are not assumed.')]


def build(output):
    output.mkdir(parents=True, exist_ok=True)
    entries=[]
    for name, inputs, steps in CASES:
        directory=output/name; directory.mkdir(exist_ok=True)
        result=build_kit(Recipe.from_dict(inputs),directory)
        evidence=inspect_archive(result['miz'])
        record={'id':name, 'app_version':__version__, 'recipe':result['manifest']['recipe'],
                'mission_sha256':hashlib.sha256(result['miz'].read_bytes()).hexdigest(),
                'generated_file':'generated_and_read_back', 'dcs_flight':'not_run',
                'dks_import':'not_run', 'checkpoints':steps, 'native':evidence}
        (directory/'expected.json').write_text(json.dumps(record,indent=2,ensure_ascii=False,default=str)+'\n')
        (directory/'CHECKLIST.md').write_text(f'# {name.upper()} flight/import check — v{__version__}\n\n{steps}\n\nMission checksum: `{record["mission_sha256"]}`.\n\nRecord DCS build, module versions, tester, result for each checkpoint and log/track/imagery paths in results.csv. Do not mark unobserved behavior passed.\n')
        entries.append({k:v for k,v in record.items() if k!='native'})
    (output/'manifest.json').write_text(json.dumps({'app_version':__version__,'cases':entries},indent=2)+'\n')
    with (output/'results.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['case','mission_sha256','dcs_build','module_versions','tester','checkpoint','result','evidence_path','notes'])
        for e in entries:w.writerow([e['id'],e['mission_sha256'],'','','','all','NOT RUN','',''])
    (output/'README.md').write_text(f'# Sortie Starter validation pack v{__version__}\n\nUnzip each mission_kit.zip. Put mission.miz in Saved Games/DCS/Missions; keep its folder name to distinguish cases. Start with brief.md and CHECKLIST.md. expected.json records the emitted actors, tasks, stores and routes for comparison. These are deterministic catalog sorties, not shortened test simulations. Required modules and warnings appear in each kit manifest readiness report. All flight/import results start NOT RUN.\n\nUse dcs.log and debrief.log plus a track or screenshot for disputed results. For TARPS retain imagery. For DKS retain the imported unpublished design and compare against the native facts. Do not publish or post the test board to the ATO.\n')
    archive=output.parent/f'sortie-validation-{__version__}.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(output.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(output))
    print(archive,flush=True)
    return archive

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path)
    build(p.parse_args().output)
