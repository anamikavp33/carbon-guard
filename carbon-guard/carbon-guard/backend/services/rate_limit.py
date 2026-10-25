"""A very small per-IP rate limit for login and registration (protects against password guessing).

Prototype limitation: the counters live in this server process's memory, so they reset on
restart and are not shared between several server processes.
"""
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request
from config import settings

_lock = threading.Lock()
_hits = defaultdict(deque)


def reset():
    with _lock:
        _hits.clear()


def auth_rate_limit(request: Request):
    """FastAPI dependency: allows AUTH_RATE_LIMIT_PER_MINUTE requests per client IP per route."""
    ip = request.client.host if request.client else "unknown"
    key = (ip, request.url.path)
    t = time.monotonic()
    with _lock:
        q = _hits[key]
        while q and t - q[0] > 60:
            q.popleft()
        if len(q) >= settings.AUTH_RATE_LIMIT_PER_MINUTE:
            raise HTTPException(status_code=429, detail="Too many attempts. Please wait a minute and try again.")
        q.append(t)
