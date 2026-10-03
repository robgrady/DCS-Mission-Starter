"""Immutable public pack revisions with an atomic, durable catalog pointer.

Readers resolve the pointer once; replacing/deleting a pack does not remove
bytes a download already owns. Retained revisions are also rollback points.
"""
import json
try:
    import fcntl
except ImportError:
    fcntl = None
    import msvcrt
import os
from pathlib import Path
import shutil
import tempfile
import threading
import uuid

class CatalogLock:
    """Reentrant within a thread and exclusive across local writer processes."""
    def __init__(self, root):
        self.root = root
        self.thread_lock = threading.RLock()
        self.local = threading.local()

    def __enter__(self):
        self.thread_lock.acquire()
        try:
            if not getattr(self.local, 'depth', 0):
                root = self.root(); root.mkdir(parents=True, exist_ok=True)
                self.local.fd = open(root / '.catalog.lock', 'a+b')
                if fcntl is not None:
                    fcntl.flock(self.local.fd, fcntl.LOCK_EX)
                else:
                    if self.local.fd.tell() == 0:
                        self.local.fd.write(b'0'); self.local.fd.flush()
                    self.local.fd.seek(0)
                    msvcrt.locking(self.local.fd.fileno(), msvcrt.LK_LOCK, 1)
            self.local.depth = getattr(self.local, 'depth', 0) + 1
        except BaseException:
            try:
                fd = getattr(self.local, 'fd', None)
                if fd is not None:
                    fd.close()
            finally:
                self.thread_lock.release()
            raise
        return self

    def __exit__(self, *unused):
        self.local.depth -= 1
        try:
            if not self.local.depth:
                try:
                    if fcntl is not None:
                        fcntl.flock(self.local.fd, fcntl.LOCK_UN)
                    else:
                        self.local.fd.seek(0)
                        msvcrt.locking(self.local.fd.fileno(), msvcrt.LK_UNLCK, 1)
                finally:
                    self.local.fd.close()
        finally:
            self.thread_lock.release()


def sync_directory(path):
    if os.name == 'nt':  # Windows cannot open a directory with os.open.
        return
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def resolve_pack(root, pid):
    pointer = root / '.catalog' / (pid + '.json')
    if not pointer.exists():
        return root / pid  # existing installations remain readable
    record = json.loads(pointer.read_text())
    relative = record.get('revision')
    if relative is None:
        return root / '.deleted' / pid
    path = (root / relative).resolve()
    revisions = (root / '.revisions' / pid).resolve()
    if path.parent != revisions:
        raise ValueError('Invalid pack revision pointer')
    return path


def point_catalog(root, pid, revision):
    catalog = root / '.catalog'; catalog.mkdir(parents=True, exist_ok=True)
    pointer = catalog / ('.publish-' + uuid.uuid4().hex)
    try:
        data = json.dumps({'revision':str(revision.relative_to(root)) if revision else None}).encode()
        pointer.write_bytes(data)
        with pointer.open('rb') as handle:
            os.fsync(handle.fileno())
        os.replace(pointer, catalog / (pid + '.json'))
        sync_directory(catalog)
        sync_directory(root)
    finally:
        pointer.unlink(missing_ok=True)


def publish(root, pid, files):
    root.mkdir(parents=True, exist_ok=True)
    revisions = root / '.revisions' / pid
    revisions.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.stage-', dir=root))
    revision = revisions / uuid.uuid4().hex
    try:
        for rel, blob in files.items():
            path = stage / rel; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(blob)
            with path.open('rb') as handle:
                os.fsync(handle.fileno())
        for directory in sorted((p for p in stage.rglob('*') if p.is_dir()), reverse=True):
            sync_directory(directory)
        sync_directory(stage)
        os.replace(stage, revision)
        sync_directory(revisions)
        # Persist the newly created per-pack directory before publishing a
        # pointer into it; syncing only its own entries leaves its parent link
        # vulnerable to a crash on the first publication.
        sync_directory(revisions.parent)
        point_catalog(root, pid, revision)
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    return revision
