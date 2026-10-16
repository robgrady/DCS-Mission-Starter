"""Prove exact authoring/startup guards from green, then restore every source."""
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent.parent
CASES=[
    ('missiongen/authoring.py', 'if not r.allow_anachronistic_stores:', 'if False:',
     'invalid_authoring', 'silently bypass recorded weapon service windows'),
    ('missiongen/authoring.py', '        unit.pylons = {}', '        pass',
     'explicit_fit_replaces', 'retain preset stores beside the exact fit'),
    ('missiongen/precision.py', '            u.speed = r.start_speed', '            u.speed = r.start_speed / 3.6',
     'six_phoenix', 'convert native m/s twice'),
    ('missiongen/build_context.py', '    if r.start_time is not None:', '    if False:',
     'six_phoenix', 'ignore the exact start clock'),
    ('missiongen/precision.py', "preset = {**preset, 'historical_classification': 'fictional_exercise',",
     "preset = {**preset, 'historical_classification': 'reconstruction',",
     'six_phoenix', 'claim reconstruction for fictional equipment'),
    ('missiongen/historical_world.py', "preview(mk, era, key, cfg.get('lineup'), data=data)",
     "preview(mk, era, key, cfg.get('lineup'))",
     'options_bounds', 'reload historical JSON for every preview'),
    ('frontend/assets/app.js', '  if(!NAV_READY){', '  if(false){',
     'navigation_during', 'run Library navigation before options are available'),
    ('frontend/assets/library-controller.js', 'if(libraryCatalogSignature===signature&&libraryCatalogCache)', 'if(false)',
     'library_catalog_reuses', 'recompute unchanged Library projections'),
]


def run(selector):
    return subprocess.run([sys.executable,'-m','pytest','tests/test_exact_authoring.py',
        'tests/test_catalog_performance.py','tests/test_refactor_browser.py','-q','-x','-k',selector],
        cwd=ROOT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True)


def main():
    evidence=Path(sys.argv[1]); evidence.mkdir(parents=True,exist_ok=True)
    selector=' or '.join(sorted({case[3] for case in CASES}))
    baseline=run(selector); (evidence/'baseline.log').write_text(baseline.stdout+baseline.stderr)
    if baseline.returncode:
        raise SystemExit('RED baseline\n'+baseline.stdout+baseline.stderr)
    frozen={p:p.read_bytes() for tree in ('missiongen','server','frontend','tests','scripts')
            for p in (ROOT/tree).rglob('*') if p.suffix in ('.py','.json','.js','.html')}
    for i,(file,old,new,test,label) in enumerate(CASES,1):
        path=ROOT/file; original=path.read_bytes(); source=original.decode()
        assert source.count(old)==1,(file,source.count(old))
        try:
            path.write_text(source.replace(old,new)); result=run(test)
            (evidence/f'{i}.log').write_text(result.stdout+result.stderr)
            if result.returncode!=1 or 'failed' not in result.stdout:
                raise SystemExit('WEAK: '+label+'\n'+result.stdout+result.stderr)
            print('caught: '+label,flush=True)
        finally:
            path.write_bytes(original)
        assert all(p.read_bytes()==data for p,data in frozen.items()),'Source drift during harness'
    restored=run(selector); (evidence/'restored.log').write_text(restored.stdout+restored.stderr)
    if restored.returncode:
        raise SystemExit('Restored baseline failed\n'+restored.stdout+restored.stderr)
    print(f'{len(CASES)} caught; 0 weak; source restored.',flush=True)


if __name__=='__main__':
    main()
