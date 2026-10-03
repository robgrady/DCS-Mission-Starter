"""Failed replacements preserve published content; simultaneous bundles stay valid."""
from concurrent.futures import ThreadPoolExecutor
import io
from pathlib import Path
import zipfile

import pytest

from missiongen import packs


def archive(blob=b'old mission'):
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w') as z:
        z.writestr('01.miz', blob)
    return out.getvalue()


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(packs, 'DATA_DIR', tmp_path / 'packs')
    packs.install(archive(), 'test.zip', pack_id='test')
    return packs.DATA_DIR


def test_write_failure_preserves_old_pack(store, monkeypatch):
    write = Path.write_bytes

    def fail_stage(path, blob):
        if any(part.startswith('.stage-') for part in path.parts):
            raise OSError('disk full')
        return write(path, blob)

    monkeypatch.setattr(Path, 'write_bytes', fail_stage)
    with pytest.raises(OSError, match='disk full'):
        packs.install(archive(b'new mission'), 'test.zip', pack_id='test')
    assert packs.get_file('test', '01.miz').read_bytes() == b'old mission'
    assert [p.name for p in store.iterdir()] == ['test']


def test_publication_failure_rolls_back(store, monkeypatch):
    replace = packs.os.replace

    def fail_publish(source, target):
        if Path(source).name.startswith('.stage-') and Path(target).name == 'test':
            raise OSError('publish failed')
        return replace(source, target)

    monkeypatch.setattr(packs.os, 'replace', fail_publish)
    with pytest.raises(OSError, match='publish failed'):
        packs.install(archive(b'new mission'), 'test.zip', pack_id='test')
    assert packs.get_file('test', '01.miz').read_bytes() == b'old mission'
    assert [p.name for p in store.iterdir()] == ['test']


def test_concurrent_bundle_creation_returns_complete_archives(store):
    with ThreadPoolExecutor(max_workers=6) as pool:
        outputs = list(pool.map(lambda _: packs.all_zip('test'), range(12)))
    assert len(set(outputs)) == 1
    for path in outputs:
        with zipfile.ZipFile(path) as z:
            assert z.testzip() is None
            assert z.read('test/01.miz') == b'old mission'
    assert not list(outputs[0].parent.glob(outputs[0].name + '.part-*'))
    packs.install(archive(b'new mission'), 'test.zip', pack_id='test')
    with zipfile.ZipFile(packs.all_zip('test')) as z:
        assert z.read('test/01.miz') == b'new mission'
