#!/usr/bin/env python3
"""Measure coverage/symbol/date guards from green, then restore exact sources."""
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parent.parent
CASES=[
 ('missiongen/historical_coverage.py',"'dated_validity_certified': False","'dated_validity_certified': True",'register_covers','falsely certify all map eras'),
 ('missiongen/historical_coverage.py',"return 'within_recorded_validity' if start and end else 'operational_validity_unknown'","return 'within_recorded_validity'",'reference_date','certify missing validity bounds'),
 ('missiongen/airspace.py',"if ov.get('reference_only') and ov.get('attested_on', '') > m.start_time.date().isoformat():","if False:",'future_snapshots','draw a future boundary in 1991'),
 ('missiongen/airspace.py',"f['radius_nm']*1852.0","f['radius_nm']*1609.34",'dated_references','convert a published nautical radius as statute miles'),
 ('missiongen/historical_symbols.py',"line = LineStyle.Dash","line = LineStyle.Solid",'network_lanes','hide reconstructed geometry confidence'),
 ('missiongen/historical_symbols.py',"_draw_poly(layer, points, color, cs._fill(color,0), 2,","layer.add_circle(point,radius=radius,color=color,fill=cs._fill(color,0),line_thickness=2,line_style=LineStyle.Solid)\n    return\n    _draw_poly(layer, points, color, cs._fill(color,0), 2,",'network_lanes','replace reporting diamonds with zone circles'),
 ('missiongen/corridor_chart.py',"if c[\"role\"] in (\"recovery\", \"departure\"):\n            _arrow(cv, a, b, stroke, 7 * fs)","if c[\"role\"] in (\"recovery\", \"departure\"):\n            _arrow(cv, b, a, stroke, 7 * fs)",'recovery_chart','reverse the homeward direction')]

def run(selector):
 return subprocess.run([sys.executable,'-m','pytest','tests/test_historical_coverage.py','-q','-x','-k',selector],cwd=ROOT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True)

def main():
 evidence=Path(sys.argv[1]);evidence.mkdir(parents=True,exist_ok=True)
 baseline=run('not real_browser');(evidence/'baseline.log').write_text(baseline.stdout+baseline.stderr)
 if baseline.returncode:raise SystemExit('RED baseline\n'+baseline.stdout+baseline.stderr)
 frozen={p:p.read_bytes() for tree in ('missiongen','tests') for p in (ROOT/tree).rglob('*') if p.suffix in ('.py','.json')}
 for n,(file,old,new,selector,label) in enumerate(CASES,1):
  path=ROOT/file;original=path.read_bytes();source=original.decode();assert source.count(old)==1,(file,source.count(old))
  try:
   path.write_text(source.replace(old,new));result=run(selector)
   (evidence/f'{n}-{selector}.log').write_text(result.stdout+result.stderr)
   if result.returncode!=1 or 'failed' not in result.stdout:raise SystemExit('WEAK: '+label+'\n'+result.stdout+result.stderr)
   print('caught: '+label,flush=True)
  finally:path.write_bytes(original)
  assert all(p.read_bytes()==content for p,content in frozen.items()),'Source drift during harness'
 restored=run('not real_browser');(evidence/'restored.log').write_text(restored.stdout+restored.stderr)
 if restored.returncode:raise SystemExit('Restored baseline failed')
 print(f'{len(CASES)} caught; 0 weak; source restored.',flush=True)

if __name__=='__main__':main()
