"""Capacity must be shared by all API build paths and released after failure."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import threading

from fastapi import HTTPException
from fastapi.testclient import TestClient
import pytest

from server.generation import GenerationCapacity


def test_capacity_rejects_then_recovers_after_a_failure():
    capacity = GenerationCapacity(1)
    with pytest.raises(ValueError):
        GenerationCapacity(0)
    with pytest.raises(RuntimeError):
        with capacity.slot():
            with pytest.raises(HTTPException) as busy:
                with capacity.slot():
                    pytest.fail('capacity exceeded')
            assert busy.value.status_code == 503
            assert busy.value.headers['Retry-After'] == '3'
            raise RuntimeError('generation failed')
    with capacity.slot():
        pass


def test_api_build_paths_share_one_limit_and_return_retryable_busy_errors(monkeypatch):
    from server import app as api
    entered, release = threading.Event(), threading.Event()
    monkeypatch.setattr(api, 'generation_capacity', GenerationCapacity(1))

    def build(recipe, out_path, brief_dir=None):
        entered.set()
        assert release.wait(10)
        Path(out_path).write_bytes(b'PK test mission')
        return {'stats': {}, 'warnings': []}

    monkeypatch.setattr(api, '_engine_generate', build)
    request = {'recipe': {'map': 'caucasus', 'era': 'modern', 'aircraft': 'FA_18C_hornet'}}
    with TestClient(api.app) as client, ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(client.post, '/api/generate', json=request)
        assert entered.wait(10)
        try:
            for endpoint in ['/api/generate', '/api/brief', '/api/kneeboard']:
                response = client.post(endpoint, json=request)
                assert response.status_code == 503, response.text
                assert response.headers['Retry-After'] == '3'
                assert 'busy' in response.json()['detail']
        finally:
            release.set()
        assert pending.result(timeout=10).status_code == 200
        assert client.post('/api/generate', json=request).status_code == 200
