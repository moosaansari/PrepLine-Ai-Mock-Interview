import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict


class InMemoryRateLimiter:
    """Small process-local limiter for demo deployments.

    It is intentionally dependency-free. A multi-worker production deployment
    should use a shared store instead.
    """

    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= cutoff:
                hits.popleft()

            if len(hits) >= self.limit:
                return False

            hits.append(now)
            return True


interview_creation_limiter = InMemoryRateLimiter(limit=10, window_seconds=60)
live_connection_limiter = InMemoryRateLimiter(limit=6, window_seconds=60)
