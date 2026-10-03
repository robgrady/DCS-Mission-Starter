"""Reviewed native contracts pin seeded parking, stores, triggers and documents.

v1.108.3 intentionally corrects dated content and base nationality. The
pre-refactor v1.108.2 facts and field-level review are retained in release
evidence; these hashes now pin the reviewed historical-content release.
"""
import hashlib
import json
from pathlib import Path
import pytest
from missiongen import __version__, Recipe, generate
from scripts.audit_library import inspect_archive

BASELINES=json.loads((Path(__file__).parent/'fixtures/placement-contracts.json').read_text())

@pytest.mark.parametrize('baseline',BASELINES,ids=lambda b:b['recipe'].get('template') or b['recipe']['map'])
def test_seeded_native_content_matches_the_reviewed_release_contract(baseline,tmp_path):
    recipe=Recipe.from_dict(baseline['recipe']); path=tmp_path/'m.miz'
    result=generate(recipe,str(path))
    facts=json.loads(json.dumps({'stats':result['stats'],'warnings':result['warnings'],
                                 'mission':inspect_archive(path)},default=str))
    text=json.dumps(facts,sort_keys=True).replace(__version__,'<release>')
    assert hashlib.sha256(text.encode()).hexdigest() == baseline['sha256'], (
        'Native mission facts changed; investigate before updating the reviewed release baseline')
