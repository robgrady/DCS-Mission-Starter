#!/usr/bin/env python3
"""Prove historical date/equipment/disclosure guards; restore local work exactly."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parent.parent
CASES=[
 ('missiongen/data/maps.json','"scenario_date": "1980-07-10"','"scenario_date": "1978-06-21"','authored_dates'),
 ('missiongen/loadouts.py','(win[0] or 0) <= year <= (win[1] or 9999)','True','known_future_stores'),
 ('missiongen/data/historical_airspace.json','"source_effective_date": "1995-07-20"','"source_effective_date": "1978-06-21"','overlay_geometry'),
 ('missiongen/data/historical_airspace.json','"geometry_accuracy": "illustrative"','"geometry_accuracy": "exact"','overlay_geometry'),
 ('missiongen/data/theater_identity.json','"military_operator": "USSR"','"military_operator": "GDR"','base_roles'),
 ('missiongen/brief.py','when.day:02d','21:02d','context_is_in_pdf'),
 ('missiongen/brief.py','if d.textlength(w, font=font) > width_px:','if False:','long_source_urls'),
 ('missiongen/kneeboard.py','if d.textlength(w, font=font) > width_px:','if False:','long_source_urls'),
]

def check(selector=None):
 args=[sys.executable,'-m','pytest','tests/test_historical_content.py','-q']
 if selector: args+=['-x','-k',selector]
 return subprocess.run(args,cwd=ROOT,env=dict(os.environ,PYTHONPATH='.:vendor',PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True)

def main():
 baseline=check()
 if baseline.returncode:
  print(baseline.stdout,baseline.stderr);raise SystemExit('Baseline is not green')
 evidence=Path(sys.argv[1]) if len(sys.argv)>1 else Path(tempfile.mkdtemp(prefix='historical-mutations-'))
 evidence.mkdir(parents=True,exist_ok=True)
 (evidence/'baseline.log').write_text(baseline.stdout+baseline.stderr)
 frozen={p:p.read_bytes() for tree in ('missiongen','tests') for p in (ROOT/tree).rglob('*') if p.suffix in ('.py','.json')}
 for n,(fn,old,new,selector) in enumerate(CASES,1):
  path=ROOT/fn;original=path.read_bytes();source=original.decode()
  assert source.count(old)==1,(fn,source.count(old))
  try:
   path.write_text(source.replace(old,new))
   result=check(selector)
   (evidence/f'{n}-{selector}.log').write_text(result.stdout+result.stderr)
   assert result.returncode==1 and 'failed' in result.stdout,(selector,result.returncode,result.stdout)
   print('caught:',selector,flush=True)
  finally:path.write_bytes(original)
  assert all(p.read_bytes()==data for p,data in frozen.items()),'Source changed during mutation run'
 print(f'{len(CASES)} mutations caught; source restored; evidence {evidence}')

if __name__=='__main__':main()
