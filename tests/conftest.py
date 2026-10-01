"""Shared pytest fixtures for nanhu-skill."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _disable_token_file_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep unit tests memory-only unless a test opts into file cache."""
    monkeypatch.setenv("NANHU_TOKEN_CACHE_DISABLE", "1")
