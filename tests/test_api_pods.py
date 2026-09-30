"""Tests for nanhu.api.pods (F9 POD list, mocked HTTP)."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest

from nanhu.api import pods
from nanhu.auth import TokenCache
from nanhu.client import NanhuClient
from nanhu.http import HttpResponse


API_BASE = "http://10.124.120.108:38080"
JOB_ID = "jb-aitrain-123"


def _client() -> NanhuClient:
    return NanhuClient(
        API_BASE,
        user_id="uid-1",
        app_key="k",
        app_secret="s",
        token_cache=TokenCache(),
    )


def _ok(data: dict[str, Any]) -> HttpResponse:
    return HttpResponse(status=200, payload={"code": "200", "message": "SUCCESS", "data": data})


def _token_ok() -> HttpResponse:
    return HttpResponse(
        status=200,
        payload={"code": 0, "data": {"accessToken": "tok-pods"}},
    )


def test_list_pods_v2_get_job_metrics() -> None:
    client = _client()
    calls: list[dict[str, Any]] = []

    def fake_http(method: str, url: str, **kwargs: Any) -> HttpResponse:
        if url.endswith("/api/open/credentials"):
            return _token_ok()
        calls.append({"method": method, "url": url, "headers": kwargs.get("headers")})
        return _ok(
            {
                "zoneType": {
                    "zoneType": "AI_GPU",
                    "nodes": [{"pods": [{"podName": "ji-x-master-0", "status": "RUNNING"}]}],
                }
            }
        )

    with patch("nanhu.auth.http_json", side_effect=fake_http), patch(
        "nanhu.http.http_json", side_effect=fake_http
    ):
        out = pods.list_pods_v2(client, JOB_ID)

    assert out["data"]["zoneType"]["nodes"][0]["pods"][0]["podName"] == "ji-x-master-0"
    assert len(calls) == 1
    assert calls[0]["method"] == "GET"
    assert pods.PATH_JOB_METRICS in calls[0]["url"]
    assert f"jobId={JOB_ID}" in calls[0]["url"]
    assert "userId=uid-1" in calls[0]["url"]
    assert "bizType=DROS" in calls[0]["url"]
    assert calls[0]["headers"]["accessToken"] == "tok-pods"


def test_list_pods_v3_get_job_monitor() -> None:
    client = _client()
    calls: list[dict[str, Any]] = []

    def fake_http(method: str, url: str, **kwargs: Any) -> HttpResponse:
        if url.endswith("/api/open/credentials"):
            return _token_ok()
        calls.append({"method": method, "url": url, "headers": kwargs.get("headers")})
        return _ok(
            {
                "jobInstancePodMonitorInfoVOList": [
                    {
                        "runCounts": 0,
                        "podInfos": [
                            {
                                "podName": "ji-x-master-0",
                                "status": "FAILED",
                                "nodeName": "node-a",
                            }
                        ],
                    }
                ]
            }
        )

    with patch("nanhu.auth.http_json", side_effect=fake_http), patch(
        "nanhu.http.http_json", side_effect=fake_http
    ):
        out = pods.list_pods_v3(client, JOB_ID, run=0)

    pods_info = out["data"]["jobInstancePodMonitorInfoVOList"][0]["podInfos"]
    assert pods_info[0]["podName"] == "ji-x-master-0"
    assert pods.PATH_JOB_MONITOR in calls[0]["url"]
    assert f"jobId={JOB_ID}" in calls[0]["url"]
    assert "run=0" in calls[0]["url"]
    assert calls[0]["headers"]["accessToken"] == "tok-pods"


def test_list_pods_v2_custom_user_and_biz() -> None:
    client = _client()
    calls: list[dict[str, Any]] = []

    def fake_http(method: str, url: str, **kwargs: Any) -> HttpResponse:
        if url.endswith("/api/open/credentials"):
            return _token_ok()
        calls.append({"url": url})
        return _ok({})

    with patch("nanhu.auth.http_json", side_effect=fake_http), patch(
        "nanhu.http.http_json", side_effect=fake_http
    ):
        pods.list_pods_v2(client, JOB_ID, user_id="other", biz_type="OTHER")

    assert "userId=other" in calls[0]["url"]
    assert "bizType=OTHER" in calls[0]["url"]
