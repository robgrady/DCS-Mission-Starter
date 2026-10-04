"""Prove readiness/import guards with faults; green baseline and exact restoration."""
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
CASES=[
 ('missiongen/readiness.py',"'dcs_flight':'unverified'","'dcs_flight':'passed'",'selection_humans','claim unflown missions passed'),
 ('missiongen/readiness.py',"if data.get('module') and 'carrier' in ctx.map_cfg:","if False:",'selection_humans','omit ship dependency'),
 ('missiongen/readiness.py',"'human_aircraft':humans, 'ai_aircraft':ai","'human_aircraft':humans+ai, 'ai_aircraft':0",'generated_counts','count AI as human seats'),
 ('server/mission_manifest.py',"'route':plain(stats.get('route_legs')","'route':(stats.get('route_legs')",'generated_counts','leak Point objects into JSON'),
 ('server/mission_manifest.py',"'x','y','alt','alt_type','speed'","'x','y','alt','alt_type','omitted_speed'",'generated_counts','lose native speed'),
 ('frontend/assets/readiness.js',"pending.get(box)!==token || !box.isConnected","!box.isConnected",'stale_readiness','stale request replaces new selection'),
 ('frontend/assets/mission-results.js',"kit.flight?.human_aircraft ?? ((rc.slots || 1) - (rc.veteran_wingmen || 0))","rc.slots || 1",'single_player_install','mislabel solo veteran flight as multiplayer'),
 ('frontend/assets/readiness.js',"pending.delete(box); box.textContent=''","box.textContent=''",'cleared_readiness','old response restores cleared selection'),
 ('frontend/assets/readiness.js',"if(r.ownership?.aircraft)","if(false)",'owned_carrier','ignore owned carrier aircraft family'),
 ('scripts/build_validation_pack.py',"'dcs_flight':'not_run'","'dcs_flight':'passed'",'validation_pack','stamp test pack flown')]
def run(selector):
 return subprocess.run([sys.executable,'-m','pytest','tests/test_readiness.py','-q','-x','-k',selector],cwd=ROOT,capture_output=True,text=True)
def main():
 baseline=run('not real_browser')
 if baseline.returncode:raise SystemExit(baseline.stdout+baseline.stderr)
 originals={p:(ROOT/p).read_text() for p,*_ in CASES}
 try:
  for p,anchor,replacement,guard,label in CASES:
   source=originals[p];assert source.count(anchor)==1,(p,anchor)
   (ROOT/p).write_text(source.replace(anchor,replacement))
   try:
    r=run(guard)
    if r.returncode!=1:raise SystemExit('WEAK '+label+'\n'+r.stdout+r.stderr)
    print('caught: '+label,flush=True)
   finally:(ROOT/p).write_text(source)
 finally:
  for p,s in originals.items():(ROOT/p).write_text(s)
 restored=run('not real_browser')
 if restored.returncode:raise SystemExit(restored.stdout+restored.stderr)
 print(f'{len(CASES)} caught; 0 weak; restored baseline passed.',flush=True)
if __name__=='__main__':main()
