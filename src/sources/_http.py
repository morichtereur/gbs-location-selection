"""Cached HTTP. Every pull is written to data/cache so a rerun is reproducible
and does not depend on three public APIs all being up at the same moment."""

from __future__ import annotations

import hashlib
from pathlib import Path

import requests

from src import config as C

TIMEOUT = 180


def fetch(url: str, headers: dict[str, str] | None = None, *, suffix: str = "") -> str:
    """GET `url`, caching the body on disk under a hash of the URL."""
    C.CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(url.encode()).hexdigest()[:20]
    path = C.CACHE / f"{key}{suffix}"
    if path.exists() and path.stat().st_size > 0:
        return path.read_text()
    response = requests.get(url, headers=headers or {}, timeout=TIMEOUT)
    response.raise_for_status()
    path.write_text(response.text)
    return response.text


def cache_path(url: str, suffix: str = "") -> Path:
    key = hashlib.sha256(url.encode()).hexdigest()[:20]
    return C.CACHE / f"{key}{suffix}"
