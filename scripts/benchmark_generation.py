#!/usr/bin/env python3
"""Measure production-compatible generation latency and process peak RSS.

Run one case per process; results are observations, not load-test guarantees.
No recipe, visitor or private store data is collected from users.
"""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import time
ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT/'vendor')]
from missiongen import Recipe, generate, __version__

CASES = {
    'carrier': {'template':'cv_alpha_strike_escort'},
    'training': {'template':'wk_9_intercepts'},
    'large_ramp': {'map':'nevada','era':'modern','density':'busy','dress_fill':100},
}

def peak_rss_mb():
    try:
        import resource
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return round(peak / (1024**2 if sys.platform == 'darwin' else 1024), 2)
    except ImportError:
        return None

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('case',choices=CASES)
    args = parser.parse_args()
    start = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix='sortie-measure-') as temporary:
        path = Path(temporary)/'m.miz'
        result = generate(Recipe.from_dict({**CASES[args.case], 'seed':19}), str(path))
        print(json.dumps({'version':__version__, 'case':args.case,
                          'seconds':round(time.perf_counter()-start,3),
                          'process_peak_rss_mb':peak_rss_mb(), 'miz_bytes':path.stat().st_size,
                          'warnings':result['warnings']}))
