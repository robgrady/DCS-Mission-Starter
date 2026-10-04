#!/usr/bin/env python3
"""Require the Iraq carrier guards to catch misplaced ships and broken recovery."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
CASES = [
    ('missiongen/data/maps.json', '"x": -485340.63496921165', '"x": 80000', 'screen_and_entire', 'move the carrier inland'),
    ('missiongen/phases/routes.py', 'routing.route_for(route_home.position, tgt_pos', 'routing.route_for(home.position, tgt_pos', 'saved_iraq', 'plan the carrier flight from a land base'),
    ('missiongen/routing.py', 'point.link_unit = point.helipad_id = home_carrier.id', 'point.link_unit = point.helipad_id = 999999', 'saved_iraq', 'link recovery to a nonexistent ship'),
    ('missiongen/phases/flight_operations.py', 'home_carrier=carrier_home)', 'home_carrier=None)', 'saved_iraq', 'drop the timed package carrier recovery'),
]


def run(selector):
    return subprocess.run([sys.executable, '-m', 'pytest', 'tests/test_iraq_carrier.py', '-q', '-x', '-k', selector],
        cwd=ROOT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'), capture_output=True, text=True)


def main():
    evidence = Path(sys.argv[1]); evidence.mkdir(parents=True, exist_ok=True)
    baseline = run('not real_builder'); (evidence/'baseline.log').write_text(baseline.stdout+baseline.stderr)
    if baseline.returncode:
        raise SystemExit('RED baseline\n'+baseline.stdout+baseline.stderr)
    frozen = {p:p.read_bytes() for tree in ('missiongen','tests','scripts') for p in (ROOT/tree).rglob('*') if p.suffix in ('.py','.json')}
    for i,(file,old,new,selector,label) in enumerate(CASES,1):
        path=ROOT/file; original=path.read_bytes(); source=original.decode()
        assert source.count(old)==1,(file,source.count(old))
        try:
            path.write_text(source.replace(old,new)); result=run(selector)
            (evidence/f'{i}.log').write_text(result.stdout+result.stderr)
            if result.returncode!=1 or 'failed' not in result.stdout:
                raise SystemExit('WEAK: '+label+'\n'+result.stdout+result.stderr)
            print('caught: '+label,flush=True)
        finally:
            path.write_bytes(original)
        assert all(p.read_bytes()==blob for p,blob in frozen.items()),'Source drift during harness'
    restored=run('not real_builder'); (evidence/'restored.log').write_text(restored.stdout+restored.stderr)
    if restored.returncode:raise SystemExit('Restored baseline failed')
    print(f'{len(CASES)} caught; 0 weak; source restored.',flush=True)


if __name__=='__main__':main()
