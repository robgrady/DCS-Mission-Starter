"""Fault-inject authored-route boundaries from a green baseline; restore source."""
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent.parent
CASES=[
 ('missiongen/precision.py',"    if getattr(r, 'waypoints', None) is not None:",'    if False:','historical_reconstruction','claim source-verified history for an authored route'),
 ('frontend/assets/app.js','if(S.map!==k) S.engineSettings=retainAuthoredRoute();','if(S.map!==k) S.engineSettings={};','changing_map','erase authored route on map change'),
 ('missiongen/authored_route.py',"speed=w['speed'] * 3.6, name=w['name']","speed=w['speed'], name=w['name']",'native_order','convert waypoint speed incorrectly'),
 ('missiongen/authored_route.py','for i, w in enumerate(r.waypoints):\n        p = point','for i, w in enumerate(reversed(r.waypoints)):\n        p = point','native_order','reverse authored point order'),
 ('missiongen/authored_route.py',"        check_position(w['position'], r.map, label + '.position')",'        pass','invalid_waypoint_fields','accept out-of-map coordinates at validation'),
 ('server/mission_manifest.py',"'authored_waypoints': stats.get('authored_waypoints')","'authored_waypoints': None",'native_order','drop requested route metadata from the kit'),
 ('frontend/assets/app.js',"RECIPE_ENGINE_FIELDS = ['waypoints','route_recovery'","RECIPE_ENGINE_FIELDS = ['route_recovery'",'exact_imported','lose authored points on recipe restore'),
 ('frontend/assets/route-editor.js',"if(event.target.id==='wp_speed')p.speed=",'if(true)p.speed=','exact_imported','round exact imported speed when renaming'),
]

def run(selector):
 return subprocess.run([sys.executable,'-m','pytest','tests/test_authored_route.py','tests/test_authored_route_browser.py','-q','-x','-k',selector],cwd=ROOT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True)

def main():
 evidence=Path(sys.argv[1]);evidence.mkdir(parents=True,exist_ok=True)
 selector=' or '.join(sorted({c[3] for c in CASES}))
 result=run(selector);(evidence/'baseline.log').write_text(result.stdout+result.stderr)
 if result.returncode:raise SystemExit('RED baseline\n'+result.stdout+result.stderr)
 frozen={p:p.read_bytes() for name in ('missiongen','server','frontend','tests','scripts') for p in (ROOT/name).rglob('*') if p.suffix in ('.py','.json','.js','.html','.css')}
 for i,(file,old,new,test,label) in enumerate(CASES,1):
  path=ROOT/file;original=path.read_bytes();source=original.decode();assert source.count(old)==1,(file,source.count(old))
  try:
   path.write_text(source.replace(old,new));result=run(test);(evidence/f'{i}.log').write_text(result.stdout+result.stderr)
   if result.returncode!=1 or 'failed' not in result.stdout:raise SystemExit('WEAK '+label+'\n'+result.stdout+result.stderr)
   print('caught: '+label,flush=True)
  finally:path.write_bytes(original)
  assert all(p.read_bytes()==value for p,value in frozen.items()),'Source drift'
 result=run(selector);(evidence/'restored.log').write_text(result.stdout+result.stderr)
 if result.returncode:raise SystemExit('Restored baseline failed')
 print(f'{len(CASES)} caught; 0 weak; source restored.',flush=True)

if __name__=='__main__':main()
