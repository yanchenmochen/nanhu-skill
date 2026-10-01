"""Tests for nanhu.auth and NanhuClient facade (mocked HTTP)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from nanhu.auth import (
    DEFAULT_TOKEN_CACHE_PATH,
    TokenCache,
    TokenInfo,
    fetch_access_token,
    get_access_token,
    resolve_token_cache_path,
)
from nanhu.client import NanhuClient
from nanhu.config import ClusterConfig, Credentials, NanhuSettings
from nanhu.http import HttpResponse


def _token_response(token: str = "tok-abc", code: Any = 0) -> HttpResponse:
    return HttpResponse(
        status=200,
        payload={"code": code, "data": {"accessToken": token}},
    )


def test_fetch_access_token_posts_credentials() -> None:
    calls: list[dict[str, Any]] = []

    def fake_http(method: str, url: str, **kwargs: Any) -> HttpResponse:
        calls.append({"method": method, "url": url, **kwargs})
        return _token_response("live-token")

    token = fetch_access_token(
        "http://10.124.120.108:38080",
        "key",
        "secret",
        http_json_fn=fake_http,
    )
    assert token == "live-token"
    assert calls[0]["method"] == "POST"
    assert calls[0]["url"] == "http://10.124.120.108:38080/api/open/credentials"
    assert calls[0]["body"] == {"appKey": "key", "appSecret": "secret"}


def test_token_cache_memory_hit(tmp_path: Path) -> None:
    cache = TokenCache(ttl_seconds=7200)
    calls = {"n": 0}

    def fake_http(method: str, url: str, **kwargs: Any) -> HttpResponse:
        calls["n"] += 1
        return _token_response(f"t{calls['n']}")

    t1 = get_access_token("http://10.1.1.1", "k", "s", cache=cache, http_json_fn=fake_http)
    t2 = get_access_token("http://10.1.1.1", "k", "s", cache=cache, http_json_fn=fake_http)
    assert t1 == t2 == "t1"
    assert calls["n"] == 1


def test_token_cache_force_refresh() -> None:
    cache = TokenCache()
    calls = {"n": 0}

    def fake_http(method: str, url: str, **kwargs: Any) -> HttpResponse:
        calls["n"] += 1
        return _token_response(f"t{calls['n']}")

    get_access_token("http://10.1.1.1", "k", "s", cache=cache, http_json_fn=fake_http)
    t2 = get_access_token(
        "http://10.1.1.1", "k", "s", cache=cache, force_refresh=True, http_json_fn=fake_http
    )
    assert t2 == "t2"
    assert calls["n"] == 2


def test_token_cache_expired_refetches() -> None:
    cache = TokenCache(skew_seconds=0)
    cache.put("http://10.1.1.1", "k", "old", expires_at=time.time() - 1)
    calls = {"n": 0}

    def fake_http(method: str, url: str, **kwargs: Any) -> HttpResponse:
        calls["n"] += 1
        return _token_response("new")

    token = get_access_token("http://10.1.1.1", "k", "s", cache=cache, http_json_fn=fake_http)
    assert token == "new"
    assert calls["n"] == 1


def test_token_cache_file_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "token.json"
    cache1 = TokenCache(cache_path=path, ttl_seconds=7200)
    cache1.put("http://10.1.1.1", "k", "file-tok")
    assert path.is_file()

    cache2 = TokenCache(cache_path=path)
    hit = cache2.get("http://10.1.1.1", "k")
    assert hit is not None
    assert hit.access_token == "file-tok"


def test_token_info_skew() -> None:
    info = TokenInfo(access_token="x", expires_at=time.time() + 60)
    assert not info.is_valid(skew_seconds=120)
    assert info.is_valid(skew_seconds=0)


def test_client_auth_headers_and_request() -> None:
    client = NanhuClient(
        "http://10.202.32.189:38080",
        user_id="uid-1",
        app_key="k",
        app_secret="s",
        token_cache=TokenCache(),
    )

    def fake_http(method: str, url: str, **kwargs: Any) -> HttpResponse:
        if url.endswith("/api/open/credentials"):
            return _token_response("client-tok")
        return HttpResponse(status=200, payload={"code": 0, "data": {"jobs": []}})

    with patch("nanhu.auth.http_json", side_effect=fake_http), patch(
        "nanhu.http.http_json", side_effect=fake_http
    ):
        headers = client.auth_headers()
        assert headers["accessToken"] == "client-tok"
        assert client.access_token == "client-tok"

        out = client.request("GET", "/api/open/job/list", query={"userId": client.user_id})
        assert out["data"]["jobs"] == []


def test_client_from_settings() -> None:
    settings = NanhuSettings(
        cluster=ClusterConfig(name="wuxi", api_base="http://10.124.120.108:38080"),
        credentials=Credentials(app_key="k", app_secret="s", user_id="u"),
    )
    client = NanhuClient.from_settings(settings)
    assert client.api_base == "http://10.124.120.108:38080"
    assert client.user_id == "u"


def test_client_build_url() -> None:
    client = NanhuClient("http://10.1.1.1:38080/", user_id="u", app_key="k", app_secret="s")
    assert client.build_url("/api/x") == "http://10.1.1.1:38080/api/x"
    assert "userId=u" in client.build_url("api/x", query={"userId": "u", "skip": None})


def test_resolve_token_cache_path_default() -> None:
    assert resolve_token_cache_path(env={}) == DEFAULT_TOKEN_CACHE_PATH


def test_resolve_token_cache_path_disable_env() -> None:
    assert resolve_token_cache_path(env={"NANHU_TOKEN_CACHE": "0"}) is None
    assert resolve_token_cache_path(env={"NANHU_TOKEN_CACHE": "false"}) is None
    assert resolve_token_cache_path(env={"NANHU_TOKEN_CACHE_DISABLE": "1"}) is None


def test_resolve_token_cache_path_custom(tmp_path: Path) -> None:
    custom = tmp_path / "tok.json"
    assert resolve_token_cache_path(env={"NANHU_TOKEN_CACHE": str(custom)}) == custom
    assert (
        resolve_token_cache_path(env={"NANHU_TOKEN_CACHE_PATH": str(custom)}) == custom
    )


def test_token_cache_defaults_to_resolved_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("NANHU_TOKEN_CACHE_DISABLE", raising=False)
    path = tmp_path / "token.json"
    monkeypatch.setenv("NANHU_TOKEN_CACHE", str(path))
    cache = TokenCache()
    assert cache.cache_path == path
    cache.put("http://10.1.1.1", "k", "env-tok")
    assert path.is_file()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert any(v.get("access_token") == "env-tok" for v in data.values())


def test_token_cache_explicit_none_is_memory_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("NANHU_TOKEN_CACHE_DISABLE", raising=False)
    monkeypatch.setenv("NANHU_TOKEN_CACHE", str(tmp_path / "should-not-write.json"))
    cache = TokenCache(cache_path=None)
    cache.put("http://10.1.1.1", "k", "mem-only")
    assert not (tmp_path / "should-not-write.json").exists()


def test_client_from_settings_uses_default_file_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("NANHU_TOKEN_CACHE_DISABLE", raising=False)
    path = tmp_path / "cli-token.json"
    monkeypatch.setenv("NANHU_TOKEN_CACHE", str(path))
    settings = NanhuSettings(
        cluster=ClusterConfig(name="wuxi", api_base="http://10.124.120.108:38080"),
        credentials=Credentials(app_key="k", app_secret="s", user_id="u"),
    )
    client = NanhuClient.from_settings(settings)
    assert client.token_cache.cache_path == path
