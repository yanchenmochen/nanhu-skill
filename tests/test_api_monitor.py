"""Tests for job monitor APIs in nanhu.api.pods (F10, mocked HTTP)."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from nanhu.api import pods
from nanhu.auth import TokenCache
from nanhu.client import NanhuClient
from nanhu.http import HttpResponse


API_BASE = "http://10.202.32.189:38080"
JOB_ID = "jb-aitrain-456"
POD = "ji-aitrain-456-master-0"


def _client() -> NanhuClient:
    return NanhuClient(
        API_BASE,
        user_id="uid-m",
        app_key="k",
        app_secret="s",
        token_cache=TokenCache(),
    )


def _ok(data: dict[str, Any]) -> HttpResponse:
    return HttpResponse(status=200, payload={"code": "200", "message": "SUCCESS", "data": data})


def _token_ok() -> HttpResponse:
    return HttpResponse(
        status=200,
        payload={"code": 0, "data": {"accessToken": "tok-mon"}},
    )


def test_get_job_monitor_path_and_query() -> None:
    client = _client()
    calls: list[dict[str, Any]] = []

    def fake_http(method: str, url: str, **kwargs: Any) -> HttpResponse:
        if url.endswith("/api/open/credentials"):
            return _token_ok()
        calls.append({"method": method, "url": url, "headers": kwargs.get("headers")})
        return _ok(
            {
                "jobInstancePodMonitorInfoVOList": [
                    {"runCounts": 1, "podInfos": [{"podName": POD, "status": "RUNNING"}]}
                ]
            }
        )

    with patch("nanhu.auth.http_json", side_effect=fake_http), patch(
        "nanhu.http.http_json", side_effect=fake_http
    ):
        out = pods.get_job_monitor(client, JOB_ID, run=1)

    assert out["data"]["jobInstancePodMonitorInfoVOList"][0]["podInfos"][0]["podName"] == POD
    assert calls[0]["method"] == "GET"
    assert pods.PATH_JOB_MONITOR in calls[0]["url"]
    qs = parse_qs(urlparse(calls[0]["url"]).query)
    assert qs["jobId"] == [JOB_ID]
    assert qs["userId"] == ["uid-m"]
    assert qs["bizType"] == ["DROS"]
    assert qs["run"] == ["1"]
    assert calls[0]["headers"]["accessToken"] == "tok-mon"


def test_get_running_monitor_query() -> None:
    client = _client()
    calls: list[dict[str, Any]] = []

    def fake_http(method: str, url: str, **kwargs: Any) -> HttpResponse:
        if url.endswith("/api/open/credentials"):
            return _token_ok()
        calls.append({"method": method, "url": url, "headers": kwargs.get("headers")})
        return _ok({"podCPUUtilisation": [{"key": POD, "values": [["1", "2"]]}]})

    with patch("nanhu.auth.http_json", side_effect=fake_http), patch(
        "nanhu.http.http_json", side_effect=fake_http
    ):
        out = pods.get_running_monitor(
            client,
            JOB_ID,
            [POD, "ji-aitrain-456-worker-0"],
            start=1752732162,
            end=1752732462,
            indicator_name="podCPUUtilisation",
            step=1000,
        )

    assert "podCPUUtilisation" in out["data"]
    assert pods.PATH_RUNNING_MONITOR in calls[0]["url"]
    qs = parse_qs(urlparse(calls[0]["url"]).query)
    assert qs["uuid"] == [JOB_ID]
    assert qs["podNames"] == [f"{POD},ji-aitrain-456-worker-0"]
    assert qs["start"] == ["1752732162"]
    assert qs["end"] == ["1752732462"]
    assert qs["indicatorName"] == ["podCPUUtilisation"]
    assert qs["step"] == ["1000"]
    assert calls[0]["headers"]["accessToken"] == "tok-mon"


def test_list_pods_v3_delegates_to_get_job_monitor() -> None:
    client = _client()
    calls: list[str] = []

    def fake_http(method: str, url: str, **kwargs: Any) -> HttpResponse:
        if url.endswith("/api/open/credentials"):
            return _token_ok()
        calls.append(url)
        return _ok({})

    with patch("nanhu.auth.http_json", side_effect=fake_http), patch(
        "nanhu.http.http_json", side_effect=fake_http
    ):
        pods.list_pods_v3(client, JOB_ID)
        pods.get_job_monitor(client, JOB_ID)

    assert all(pods.PATH_JOB_MONITOR in u for u in calls)
    assert len(calls) == 2
