"""Small in-memory limiter for failed logins (per process; use a shared store if you run several workers)."""
import time

from fastapi import HTTPException

from .config import LOGIN_MAX_FAILURES, LOGIN_WINDOW_SECONDS

_failures: dict[str, list[float]] = {}


def _recent(key: str) -> list[float]:
    cutoff = time.time() - LOGIN_WINDOW_SECONDS
    _failures[key] = [t for t in _failures.get(key, []) if t > cutoff]
    return _failures[key]


def check(key: str):
    if len(_recent(key)) >= LOGIN_MAX_FAILURES:
        raise HTTPException(429, "Too many failed sign-in attempts. Try again later.")


def record_failure(key: str):
    _recent(key).append(time.time())


def clear(key: str):
    _failures.pop(key, None)


def reset_all():
    _failures.clear()
