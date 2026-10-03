"""Pre-extraction native contracts preserve RNG, parking, stores and documents."""
import hashlib
import json
from pathlib import Path
import pytest
from missiongen import __version__, Recipe, generate
from scripts.audit_library import inspect_archive

BASELINES=json.loads((Path(__file__).parent/'fixtures/placement-contracts.json').read_text())

@pytest.mark.parametrize('baseline',BASELINES,ids=lambda b:b['recipe'].get('template') or b['recipe']['map'])
def test_seeded_native_content_matches_the_pre_refactor_contract(baseline,tmp_path):
    recipe=Recipe.from_dict(baseline['recipe']); path=tmp_path/'m.miz'
    result=generate(recipe,str(path))
    facts=json.loads(json.dumps({'stats':result['stats'],'warnings':result['warnings'],
                                 'mission':inspect_archive(path)},default=str))
    text=json.dumps(facts,sort_keys=True).replace(__version__,'<release>')
    assert hashlib.sha256(text.encode()).hexdigest() == baseline['sha256'], (
        'Native mission facts changed; investigate before updating the pre-refactor baseline')
