"""Tests for nanhu.api.logs (F11, mocked HTTP)."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pytest

from nanhu.api import logs
from nanhu.auth import TokenCache
from nanhu.client import NanhuClient
from nanhu.http import HttpResponse


API_BASE = "http://10.202.32.189:38080"
JOB_ID = "jb-aitrain-789"
PODS = "ji-aitrain-789-master-0,ji-aitrain-789-worker-0"


def _client() -> NanhuClient:
    return NanhuClient(
        API_BASE,
        user_id="uid-l",
        app_key="k",
        app_secret="s",
        token_cache=TokenCache(),
    )


def _token_ok() -> HttpResponse:
    return HttpResponse(
        status=200,
        payload={"code": 0, "data": {"accessToken": "tok-log"}},
    )


def _ok(data: dict[str, Any]) -> HttpResponse:
    return HttpResponse(status=200, payload={"code": "200", "message": "SUCCESS", "data": data})


def test_resolve_zone() -> None:
    assert logs.resolve_zone("X10000") == "X10000"
    assert logs.resolve_zone(cluster="x10000") == "X10000"
    with pytest.raises(ValueError, match="zone is required"):
        logs.resolve_zone(cluster="wuxi")


def test_get_log_info_requires_zone_header() -> None:
    client = _client()
    calls: list[dict[str, Any]] = []

    def fake_http(method: str, url: str, **kwargs: Any) -> HttpResponse:
        if url.endswith("/api/open/credentials"):
            return _token_ok()
        calls.append({"method": method, "url": url, "headers": kwargs.get("headers")})
        return _ok({"logContent": "ts node hello"})

    with patch("nanhu.auth.http_json", side_effect=fake_http), patch(
        "nanhu.http.http_json", side_effect=fake_http
    ):
        out = logs.get_log_info(
            client,
            JOB_ID,
            ["ji-aitrain-789-master-0", "ji-aitrain-789-worker-0"],
            zone="X10000",
            start=1753068196000,
            end=1753068425000,
            run=0,
        )

    assert out["data"]["logContent"] == "ts node hello"
    assert calls[0]["method"] == "GET"
    assert logs.PATH_LOG_INFO in calls[0]["url"]
    assert calls[0]["headers"]["accessToken"] == "tok-log"
    assert calls[0]["headers"]["zone"] == "X10000"
    qs = parse_qs(urlparse(calls[0]["url"]).query)
    assert qs["jobId"] == [JOB_ID]
    assert qs["jobPodNames"] == [PODS]
    assert qs["bizType"] == ["DROS"]
    assert qs["start"] == ["1753068196000"]
    assert qs["end"] == ["1753068425000"]
    assert qs["run"] == ["0"]


def test_get_log_info_cluster_maps_zone() -> None:
    client = _client()
    calls: list[dict[str, Any]] = []

    def fake_http(method: str, url: str, **kwargs: Any) -> HttpResponse:
        if url.endswith("/api/open/credentials"):
            return _token_ok()
        calls.append({"headers": kwargs.get("headers")})
        return _ok({"logContent": ""})

    with patch("nanhu.auth.http_json", side_effect=fake_http), patch(
        "nanhu.http.http_json", side_effect=fake_http
    ):
        logs.get_log_info(client, JOB_ID, "pod-a", cluster="x10000")

    assert calls[0]["headers"]["zone"] == "X10000"


def test_get_log_info_missing_zone_raises() -> None:
    client = _client()
    with pytest.raises(ValueError, match="zone is required"):
        logs.get_log_info(client, JOB_ID, "pod-a")


def test_download_log_writes_bytes(tmp_path: Path) -> None:
    client = _client()
    dest = tmp_path / "job.log"
    captured: list[dict[str, Any]] = []

    def fake_token(*_a: Any, **_k: Any) -> str:
        return "tok-dl"

    def fake_bytes(method: str, url: str, **kwargs: Any) -> tuple[int, bytes]:
        captured.append({"method": method, "url": url, "headers": kwargs.get("headers")})
        return 200, b"log-bytes-here"

    with patch.object(client, "ensure_token", side_effect=fake_token), patch(
        "nanhu.api.logs._http_bytes", side_effect=fake_bytes
    ):
        raw = logs.download_log(client, JOB_ID, "pod-a", dest_path=dest, run=2)

    assert raw == b"log-bytes-here"
    assert dest.read_bytes() == b"log-bytes-here"
    assert captured[0]["method"] == "GET"
    assert logs.PATH_LOG_DOWNLOAD in captured[0]["url"]
    assert captured[0]["headers"]["accessToken"] == "tok-dl"
    qs = parse_qs(urlparse(captured[0]["url"]).query)
    assert qs["jobId"] == [JOB_ID]
    assert qs["jobPodNames"] == ["pod-a"]
    assert qs["run"] == ["2"]


def test_download_log_http_error() -> None:
    client = _client()

    with patch.object(client, "ensure_token", return_value="tok"), patch(
        "nanhu.api.logs._http_bytes", return_value=(500, b"boom")
    ):
        with pytest.raises(RuntimeError, match="download log HTTP 500"):
            logs.download_log(client, JOB_ID, "pod-a")
