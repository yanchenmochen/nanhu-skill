"""Tests for nanhu.api.resources (mocked HTTP)."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pytest

from nanhu.auth import TokenCache
from nanhu.client import NanhuClient
from nanhu.http import ApiError, HttpResponse
from nanhu.api import resources


def _client() -> NanhuClient:
    return NanhuClient(
        "http://10.202.32.189:38080",
        user_id="uid-42",
        app_key="k",
        app_secret="s",
        token_cache=TokenCache(),
    )


def _ok(data: Any, *, code: Any = 0) -> HttpResponse:
    return HttpResponse(status=200, payload={"code": code, "msg": "SUCCESS", "data": data})


def _fake_http_factory(handler):
    def fake_http(method: str, url: str, **kwargs: Any) -> HttpResponse:
        if url.rstrip("/").endswith("/api/open/credentials"):
            return HttpResponse(
                status=200,
                payload={"code": 0, "data": {"accessToken": "tok-res"}},
            )
        return handler(method, url, **kwargs)

    return fake_http


def test_list_specs_injects_user_id_and_token() -> None:
    calls: list[dict[str, Any]] = []

    def handler(method: str, url: str, **kwargs: Any) -> HttpResponse:
        calls.append({"method": method, "url": url, "headers": kwargs.get("headers")})
        return _ok([{"uuid": "spec-1", "name": "GPU-8", "gpuNum": 8}])

    client = _client()
    with patch("nanhu.auth.http_json", side_effect=_fake_http_factory(handler)), patch(
        "nanhu.http.http_json", side_effect=_fake_http_factory(handler)
    ):
        out = resources.list_specs(client, resource_type="MTU_X10000_80GB", current=1, page_size=50)

    assert out["data"][0]["uuid"] == "spec-1"
    assert len(calls) == 1
    assert calls[0]["method"] == "GET"
    parsed = urlparse(calls[0]["url"])
    assert parsed.path == "/api/open/dros-ic-platform/open-job/specs"
    qs = parse_qs(parsed.query)
    assert qs["userId"] == ["uid-42"]
    assert qs["resourceType"] == ["MTU_X10000_80GB"]
    assert qs["current"] == ["1"]
    assert qs["pageSize"] == ["50"]
    assert calls[0]["headers"]["accessToken"] == "tok-res"


def test_list_projects_path_and_optional_resource_type() -> None:
    calls: list[dict[str, Any]] = []

    def handler(method: str, url: str, **kwargs: Any) -> HttpResponse:
        calls.append({"method": method, "url": url})
        return _ok(
            [{"projectId": "pr-1", "projectName": "demo", "hasAvailableSubQuotas": True}],
            code=200,
        )

    client = _client()
    with patch("nanhu.auth.http_json", side_effect=_fake_http_factory(handler)), patch(
        "nanhu.http.http_json", side_effect=_fake_http_factory(handler)
    ):
        out = resources.list_projects(client)

    assert out["code"] == 200
    assert out["data"][0]["projectId"] == "pr-1"
    parsed = urlparse(calls[0]["url"])
    assert parsed.path == "/api/open/resource-proxy/subMission/open-job/projects"
    qs = parse_qs(parsed.query)
    assert qs["userId"] == ["uid-42"]
    assert "resourceType" not in qs


def test_list_sub_projects_requires_project_id() -> None:
    calls: list[dict[str, Any]] = []

    def handler(method: str, url: str, **kwargs: Any) -> HttpResponse:
        calls.append({"method": method, "url": url, "headers": kwargs.get("headers")})
        return _ok(
            [{"subQuotaId": "sq-1", "subQuotaName": "默认", "remainCardNum": 8}],
            code=200,
        )

    client = _client()
    with patch("nanhu.auth.http_json", side_effect=_fake_http_factory(handler)), patch(
        "nanhu.http.http_json", side_effect=_fake_http_factory(handler)
    ):
        out = resources.list_sub_projects(client, "pr-1226", user_id="other-uid")

    assert out["data"][0]["subQuotaId"] == "sq-1"
    parsed = urlparse(calls[0]["url"])
    assert parsed.path == "/api/open/resource-proxy/subMission/open-job/subProjects"
    qs = parse_qs(parsed.query)
    assert qs["userId"] == ["other-uid"]
    assert qs["projectId"] == ["pr-1226"]
    assert calls[0]["headers"]["accessToken"] == "tok-res"


def test_list_promotions() -> None:
    calls: list[dict[str, Any]] = []

    def handler(method: str, url: str, **kwargs: Any) -> HttpResponse:
        calls.append({"method": method, "url": url})
        return _ok(
            [
                {
                    "promotionDetailId": "pd-1",
                    "promotionType": "fixedPrice",
                    "promotionValue": 0.01,
                    "promotionUnit": "元 / 卡 * 小时",
                }
            ],
            code=200,
        )

    client = _client()
    with patch("nanhu.auth.http_json", side_effect=_fake_http_factory(handler)), patch(
        "nanhu.http.http_json", side_effect=_fake_http_factory(handler)
    ):
        out = resources.list_promotions(client, "pr-1226")

    assert out["data"][0]["promotionDetailId"] == "pd-1"
    parsed = urlparse(calls[0]["url"])
    assert parsed.path == "/api/open/resource-proxy/subMission/open-job/promotion/list"
    qs = parse_qs(parsed.query)
    assert qs["userId"] == ["uid-42"]
    assert qs["projectId"] == ["pr-1226"]


def test_list_specs_api_error() -> None:
    def handler(method: str, url: str, **kwargs: Any) -> HttpResponse:
        return HttpResponse(status=200, payload={"code": 500, "msg": "boom", "data": None})

    client = _client()
    with patch("nanhu.auth.http_json", side_effect=_fake_http_factory(handler)), patch(
        "nanhu.http.http_json", side_effect=_fake_http_factory(handler)
    ):
        with pytest.raises(ApiError) as exc_info:
            resources.list_specs(client)
    assert exc_info.value.code == 500
