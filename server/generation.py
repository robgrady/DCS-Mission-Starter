"""Bound expensive PyDCS builds within each server process.

Fly currently runs one process on a small machine. More Uvicorn workers create
more independent limits; keep the total process × slot count within the memory
budget. Reject excess requests promptly so a thread-pool queue cannot grow
without bound. CLI/offline pack builds are independent of API admission.
"""
from contextlib import contextmanager
import logging
import os
import threading
import time

from fastapi import HTTPException

log = logging.getLogger('missionstarter.generation')


class GenerationCapacity:
    def __init__(self, limit: int = 1):
        if limit < 1:
            raise ValueError('Generation capacity must be at least one')
        self.limit = limit
        self._slots = threading.BoundedSemaphore(limit)

    @contextmanager
    def slot(self):
        if not self._slots.acquire(blocking=False):
            log.info('generation rejected: capacity=%d', self.limit)
            raise HTTPException(status_code=503,
                                detail='The mission generator is busy. Please try again shortly.',
                                headers={'Retry-After': '3'})
        started = time.monotonic()
        success = False
        try:
            yield
            success = True
        finally:
            self._slots.release()
            log.info('generation completed: seconds=%.3f success=%s',
                     time.monotonic() - started, success)


capacity = GenerationCapacity(int(os.environ.get('GENERATION_CONCURRENCY', '1')))
