"""Real publication write failures reach authors without losing their draft."""
import errno
import io
import json
from pathlib import Path
import zipfile

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from missiongen import packs
from server import admin


def archive(blob=b'original mission'):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as z:
        z.writestr('pack.json', json.dumps({
            'format': 2, 'id': 'storage_test', 'label': 'Original title',
            'version': '1.0.0',
        }))
        z.writestr('missions/01.miz', blob)
    return output.getvalue()


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(packs, 'DATA_DIR', tmp_path / 'packs')
    monkeypatch.setenv('ADMIN_PASSWORD', 'test-password')
    packs.install(archive(), 'storage_test.sspack')
    app = FastAPI()
    app.include_router(admin.router)
    with TestClient(app) as client:
        client.cookies.set(admin._COOKIE, admin._make_token())
        yield client


@pytest.mark.parametrize('operation', ['upload', 'review'])
@pytest.mark.parametrize('error_number', [errno.ENOSPC, errno.EDQUOT, errno.EACCES])
def test_storage_failure_is_actionable_and_old_pack_survives(
        client, monkeypatch, operation, error_number):
    original_write = Path.write_bytes
    original_file = packs.get_file('storage_test', 'missions/01.miz')
    original_manifest = packs.get_manifest('storage_test')

    def fail_stage(path, blob):
        if any(part.startswith('.stage-') for part in path.parts):
            raise OSError(error_number, 'failure at /private/internal/path')
        return original_write(path, blob)

    monkeypatch.setattr(Path, 'write_bytes', fail_stage)
    if operation == 'upload':
        response = client.post('/admin/packs', files={
            'file': ('storage_test.sspack', archive(b'replacement mission')),
        })
    else:
        response = client.post('/admin/packs/storage_test/edit', data={
            'label': 'Draft title', 'version': '1.0.1',
            'premise': 'Draft <script>alert(1)</script>',
            'label_0': 'Draft mission title', 'premise_0': 'Draft mission premise',
        })
    assert response.status_code == 503
    message = ('Server storage is full' if error_number in (errno.ENOSPC, errno.EDQUOT)
               else 'Server storage is unavailable')
    assert message in response.text
    assert 'site operator' in response.text
    assert '/private/internal/path' not in response.text
    assert 'unreadable upload' not in response.text
    assert packs.get_manifest('storage_test') == original_manifest
    assert packs.get_file('storage_test', 'missions/01.miz') == original_file
    assert original_file.read_bytes() == b'original mission'
    assert not list(packs.DATA_DIR.glob('.stage-*'))
    if operation == 'review':
        assert "value='Draft title'" in response.text
        assert 'Draft mission title' in response.text
        assert 'Draft mission premise' in response.text
        assert 'Draft &lt;script&gt;' in response.text
        assert '<script>alert(1)</script>' not in response.text

    # A subsequent retry publishes successfully once storage accepts writes.
    monkeypatch.setattr(Path, 'write_bytes', original_write)
    response = client.post('/admin/packs/storage_test/edit', data={
        'label': 'Draft title', 'version': '1.0.1',
        'label_0': 'Draft mission title', 'premise_0': 'Draft mission premise',
    })
    assert response.status_code == 200
    assert 'Saved.' in response.text
    assert packs.get_manifest('storage_test')['label'] == 'Draft title'
    assert packs.get_file('storage_test', 'missions/01.miz').read_bytes() == b'original mission'
