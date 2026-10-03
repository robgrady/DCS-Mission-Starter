"""A release label survives broken/offline browser initialization; docs cannot drift."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from fastapi.testclient import TestClient
from missiongen import __version__, Recipe
from missiongen.builder import StarterBuilder
from server.app import app
from server.catalog_owner import replay_target
from ui_source import ROOT
sys.path.insert(0, str(ROOT / 'scripts'))
from manual_review import errors
import artifacts


def test_header_and_scripts_identify_the_server_release_before_javascript_runs():
    with TestClient(app) as client:
        page = client.get('/')
        assert f'id="appver" class="ver">v{__version__}</span>' in page.text
        assert '{{APP_VERSION}}' not in page.text
        assert f'/assets/app.js?v={__version__}' in page.text
        assert page.headers['cache-control'] == 'no-store'
        for path in ['/api/options', '/api/health', '/api/guide']:
            assert client.get(path).headers['cache-control'] == 'no-store'


def test_review_rejects_other_release_and_edits_after_review(tmp_path):
    docs = tmp_path / 'docs'; docs.mkdir()
    manual = docs / 'USER_GUIDE.md'; manual.write_text('Current instructions')
    record = {'version':__version__, 'documentation_required':True,
              'reason':'Controls changed', 'sections_reviewed':['Builder'],
              'source_sha256':hashlib.sha256(manual.read_bytes()).hexdigest(),
              'previous_source_sha256':'old digest'}
    path = docs / 'manual-release-review.json'; path.write_text(json.dumps(record))
    assert errors(__version__, tmp_path) == []
    assert errors('0.0.0', tmp_path)
    manual.write_text('Changed without review')
    assert any('after review' in problem for problem in errors(__version__, tmp_path))


def test_producer_failure_stops_the_ordered_release_registry():
    calls=[]
    def fail(command, **kwargs):
        calls.append(command)
        raise subprocess.CalledProcessError(1, command)
    import pytest
    with pytest.raises(subprocess.CalledProcessError):
        artifacts.run_generators('before-shots', fail)
    assert len(calls) == 1


def test_pack_catalog_has_one_owner_without_routing_private_stores():
    for path in ['/api/options', '/api/pack/test/01.miz', '/admin/packs', '/api/track/wk/all.zip']:
        assert replay_target(path, 'owner', 'other') == 'owner'
        assert replay_target(path, 'owner', 'owner') is None
    for path in ['/api/generate', '/api/contact', '/admin/contact', '/admin/sponsors', '/api/health']:
        assert replay_target(path, 'owner', 'other') is None
    assert replay_target('/api/options', None, None) is None


def test_large_pack_writes_cannot_land_on_a_replica(monkeypatch):
    monkeypatch.setenv('PACKS_OWNER_MACHINE', 'owner')
    monkeypatch.setenv('FLY_MACHINE_ID', 'other')
    with TestClient(app) as client:
        assert client.get('/api/options').headers['fly-replay'] == 'instance=owner'
        response = client.post('/admin/packs', content=b'x' * 1_000_001)
        assert response.status_code == 503
        assert 'fly-replay' not in response.headers
    from server.admin import _pack_upload_script
    script = _pack_upload_script()
    assert 'Fly-Force-Instance-Id' in script and '"owner"' in script


def test_printed_facts_share_the_final_world_clock_route_comms_and_fuel():
    builder = StarterBuilder(Recipe.from_dict({'template':'f14_bombcat_strike','seed':19}))
    mission = builder.build(); facts = builder.document_facts
    assert facts.mission_date == mission.start_time.date()
    assert facts.comms is builder.kb_ctx['comms']
    assert facts.route is builder.kb_ctx['route']
    assert facts.timing is builder.kb_ctx['timing']
    assert facts.fuel_max_kg == builder.kb_ctx['fuel_max_kg']
    assert facts.brief_context['stats'] is builder.stats


def test_historical_roles_do_not_turn_a_display_country_into_a_territorial_claim(monkeypatch):
    from datetime import date
    from missiongen import historical_world as world
    monkeypatch.setattr(world, 'load_json', lambda _: {'map':{'era':{
        'bases':{'Base':'USA'}, 'identities':{'Base':{
            'territorial_host':'UAE', 'military_operator':'USA',
            'valid_from':'2001-01-01', 'valid_to':'2020-12-31', 'sources':['primary source']}}}}})
    historical = world.snapshot('map', 'era', date(2011,6,21), {'blue_airbases':['Base']})
    base = historical.bases[0]
    assert base.display_nation == 'USA' and base.territorial_host == 'UAE'
    assert base.military_operator == 'USA' and base.mission_coalition == 'blue'
    assert world.snapshot('map','era',date(1990,1,1),{}).bases == ()
    from datetime import timedelta
    validity = base.validity
    assert validity.contains(date(2001,1,1)) and validity.contains(date(2020,12,31))
    assert not validity.contains(date(2021,1,1))


def test_pdf_manual_uses_the_reviewed_markdown_instructions_and_release():
    import re
    import pytest
    reader = pytest.importorskip('pypdf').PdfReader(ROOT/'docs/DCS_Mission_Starter_Guide.pdf')
    text = re.sub(r'\s+', ' ', ' '.join(page.extract_text() for page in reader.pages))
    assert 'v'+__version__ in reader.metadata.title
    assert 'Parking, skins and historical fidelity' in text
    assert 'Jester IZLID Strike (F-14B(U), pilot seat)' in text
    assert 'same generator release' in text
    assert 'F-4E training rides are a separate course' in text
