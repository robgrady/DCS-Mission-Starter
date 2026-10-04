#!/usr/bin/env python3
"""Inject false historical claims from green; require failures and exact restoration."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
CASES = [
    ('missiongen/historical_library.py', "if profile['routing_enabled']:", 'if False:', 'edition_provenance', 'enable an unverified routing profile'),
    ('missiongen/historical_library.py', "if row['valid_from'] or row['valid_to']:\n            raise ValueError('Reference subject dates cannot certify operational validity')", "if False:\n            raise ValueError('Reference subject dates cannot certify operational validity')", 'edition_provenance', 'turn a subject period into operational validity'),
    ('missiongen/historical_library.py', 'abs_tol=1e-10', 'abs_tol=1', 'edition_provenance', 'accept corrupted printed coordinates'),
    ('missiongen/historical_library.py', "row['occupancy_certified'] = False", "row['occupancy_certified'] = True", 'unit_event_precision', 'infer continuous unit occupancy'),
    ('missiongen/historical_library.py', "relation = 'approximate_event_date; exact arrival unknown'", "relation = 'event_on_selected_date'", 'unit_event_precision', 'erase circa arrival precision'),
    ('missiongen/historical_library.py', "(candidate['dcs_type'], candidate['country'], candidate['base']) != (dcs_type, country, base)", "(candidate['dcs_type'], candidate['country']) != (dcs_type, country)", 'exact_livery_assignment', 'apply a squadron skin at another base'),
    ('missiongen/historical_library.py', "return candidate.get('station_verified') is True and candidate.get('variant_verified') is True", 'return True', 'exact_livery_assignment', 'accept an uncertified station or aircraft assignment'),
    ('missiongen/historical_library.py', 'for row in rows[:3]]', 'for row in rows]', 'matching_readings', 'overflow the short mission reading list'),
    ('scripts/audit_historical_content.py', "field='claim_assessment' if old['fingerprint']==row['fingerprint'] else 'previous_claim_assessment'", "field='claim_assessment'", 'content_ledger', 'carry a claim review onto changed evidence'),
]


def run(selector):
    return subprocess.run([sys.executable, '-m', 'pytest', 'tests/test_historical_library.py', '-q', '-x', '-k', selector], cwd=ROOT,
                          env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'), capture_output=True, text=True)


def main():
    evidence = Path(sys.argv[1]); evidence.mkdir(parents=True, exist_ok=True)
    baseline = run('not real_browser'); (evidence/'baseline.log').write_text(baseline.stdout+baseline.stderr)
    if baseline.returncode:
        raise SystemExit('RED baseline\n'+baseline.stdout+baseline.stderr)
    frozen = {p: p.read_bytes() for tree in ('missiongen','tests','scripts') for p in (ROOT/tree).rglob('*') if p.suffix in ('.py','.json')}
    for i, (file, old, new, selector, label) in enumerate(CASES, 1):
        path = ROOT/file; original = path.read_bytes(); source = original.decode()
        assert source.count(old) == 1, (file, source.count(old))
        try:
            path.write_text(source.replace(old, new)); result = run(selector)
            (evidence/f'{i}-{selector}.log').write_text(result.stdout+result.stderr)
            if result.returncode != 1 or 'failed' not in result.stdout:
                raise SystemExit('WEAK: '+label+'\n'+result.stdout+result.stderr)
            print('caught: '+label, flush=True)
        finally:
            path.write_bytes(original)
        assert all(p.read_bytes() == blob for p, blob in frozen.items()), 'Source drift during harness'
    restored = run('not real_browser'); (evidence/'restored.log').write_text(restored.stdout+restored.stderr)
    if restored.returncode:
        raise SystemExit('Restored baseline failed')
    print(f'{len(CASES)} caught; 0 weak; source restored.', flush=True)


if __name__ == '__main__':
    main()
