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
    assert [p['id'] for p in packs.list_packs()] == ['test']


def test_publication_failure_rolls_back(store, monkeypatch):
    replace = packs.os.replace

    def fail_publish(source, target):
        if Path(source).name.startswith('.publish-') and Path(target).name == 'test.json':
            raise OSError('publish failed')
        return replace(source, target)

    monkeypatch.setattr(packs.os, 'replace', fail_publish)
    with pytest.raises(OSError, match='publish failed'):
        packs.install(archive(b'new mission'), 'test.zip', pack_id='test')
    assert packs.get_file('test', '01.miz').read_bytes() == b'old mission'
    assert [p['id'] for p in packs.list_packs()] == ['test']


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


def test_inflight_file_and_bundle_keep_their_revision_after_replace_and_delete(store):
    old_file = packs.get_file('test', '01.miz')
    old_bundle = packs.all_zip('test')
    assert '.revisions' in old_file.parts
    packs.install(archive(b'new mission'), 'test.zip', pack_id='test')
    assert packs.get_file('test', '01.miz').read_bytes() == b'new mission'
    assert old_file.read_bytes() == b'old mission'
    packs.delete('test')
    assert packs.get_file('test', '01.miz') is None
    assert old_file.read_bytes() == b'old mission'
    with zipfile.ZipFile(old_bundle) as z:
        assert z.read('test/01.miz') == b'old mission'


def test_first_revision_parent_is_durable_before_the_catalog_pointer(tmp_path, monkeypatch):
    from missiongen import pack_revisions as revisions
    synced = []
    monkeypatch.setattr(revisions, 'sync_directory', lambda path: synced.append(path))
    revision = revisions.publish(tmp_path, 'first', {'01.miz': b'mission'})
    assert synced.index(revision.parent.parent) < synced.index(tmp_path / '.catalog')


def test_unlock_failure_releases_the_thread_and_file_lock(tmp_path, monkeypatch):
    from missiongen import pack_revisions as revisions
    if revisions.fcntl is None:
        pytest.skip('Unix file-lock failure injection')
    lock = revisions.CatalogLock(lambda: tmp_path)
    flock = revisions.fcntl.flock
    def fail_unlock(fd, operation):
        if operation == revisions.fcntl.LOCK_UN:
            raise OSError('unlock failed')
        return flock(fd, operation)
    monkeypatch.setattr(revisions.fcntl, 'flock', fail_unlock)
    with pytest.raises(OSError, match='unlock failed'):
        with lock:
            pass
    assert lock.local.fd.closed
    monkeypatch.setattr(revisions.fcntl, 'flock', flock)
    def acquire_again():
        if not lock.thread_lock.acquire(timeout=1):
            return False
        try:
            with lock:
                return True
        finally:
            lock.thread_lock.release()
    with ThreadPoolExecutor(max_workers=1) as pool:
        assert pool.submit(acquire_again).result(timeout=2)
