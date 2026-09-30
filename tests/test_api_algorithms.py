"""Tests for nanhu.api.algorithms (mocked HTTP)."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pytest

from nanhu.auth import TokenCache
from nanhu.client import NanhuClient
from nanhu.http import ApiError, HttpResponse
from nanhu.api import algorithms


def _client() -> NanhuClient:
    return NanhuClient(
        "http://10.124.120.108:38080",
        user_id="uid-algo",
        app_key="k",
        app_secret="s",
        token_cache=TokenCache(),
    )


def _ok(data: Any, *, code: Any = "200") -> HttpResponse:
    return HttpResponse(
        status=200,
        payload={"code": code, "message": "SUCCESS", "data": data, "traceId": None},
    )


def _fake_http_factory(handler):
    def fake_http(method: str, url: str, **kwargs: Any) -> HttpResponse:
        if url.rstrip("/").endswith("/api/open/credentials"):
            return HttpResponse(
                status=200,
                payload={"code": 0, "data": {"accessToken": "tok-algo"}},
            )
        return handler(method, url, **kwargs)

    return fake_http


def test_list_algorithms_required_query_and_token() -> None:
    calls: list[dict[str, Any]] = []

    def handler(method: str, url: str, **kwargs: Any) -> HttpResponse:
        calls.append({"method": method, "url": url, "headers": kwargs.get("headers")})
        return _ok(
            {
                "page": {"current": 1, "pageSize": 10, "total": 1},
                "result": [{"uuid": "algo-1", "name": "slime"}],
            }
        )

    client = _client()
    with patch("nanhu.auth.http_json", side_effect=_fake_http_factory(handler)), patch(
        "nanhu.http.http_json", side_effect=_fake_http_factory(handler)
    ):
        out = algorithms.list_algorithms(
            client,
            is_public=False,
            current=2,
            page_size=20,
            name="slime",
            supported_cluster_ids="X10000",
            order_by="createDate",
            descend=1,
        )

    assert out["data"]["result"][0]["uuid"] == "algo-1"
    assert calls[0]["method"] == "GET"
    assert calls[0]["headers"]["accessToken"] == "tok-algo"
    parsed = urlparse(calls[0]["url"])
    assert parsed.path == "/api/open/dros-ic-platform/open-job/algorithms"
    qs = parse_qs(parsed.query)
    assert qs["userId"] == ["uid-algo"]
    assert qs["isPublic"] == ["false"]
    assert qs["current"] == ["2"]
    assert qs["pageSize"] == ["20"]
    assert qs["name"] == ["slime"]
    assert qs["supportedClusterIds"] == ["X10000"]
    assert qs["orderBy"] == ["createDate"]
    assert qs["descend"] == ["1"]


def test_get_algorithm_detail_by_uuid() -> None:
    calls: list[dict[str, Any]] = []

    def handler(method: str, url: str, **kwargs: Any) -> HttpResponse:
        calls.append({"url": url})
        return _ok(
            {
                "page": {"current": 1, "pageSize": 10, "total": 1},
                "result": [{"uuid": "f196cb37", "name": "test1125", "algoType": "train"}],
            }
        )

    client = _client()
    with patch("nanhu.auth.http_json", side_effect=_fake_http_factory(handler)), patch(
        "nanhu.http.http_json", side_effect=_fake_http_factory(handler)
    ):
        out = algorithms.get_algorithm(client, "f196cb37", is_public=True)

    assert out["data"]["result"][0]["name"] == "test1125"
    qs = parse_qs(urlparse(calls[0]["url"]).query)
    assert qs["uuid"] == ["f196cb37"]
    assert qs["isPublic"] == ["true"]
    assert qs["userId"] == ["uid-algo"]
    assert "current" not in qs


def test_list_algorithms_accepts_string_is_public() -> None:
    calls: list[dict[str, Any]] = []

    def handler(method: str, url: str, **kwargs: Any) -> HttpResponse:
        calls.append({"url": url})
        return _ok({"page": {"current": 1, "pageSize": 10, "total": 0}, "result": []})

    client = _client()
    with patch("nanhu.auth.http_json", side_effect=_fake_http_factory(handler)), patch(
        "nanhu.http.http_json", side_effect=_fake_http_factory(handler)
    ):
        algorithms.list_algorithms(client, is_public="TRUE")

    qs = parse_qs(urlparse(calls[0]["url"]).query)
    assert qs["isPublic"] == ["true"]


def test_get_algorithm_api_error() -> None:
    def handler(method: str, url: str, **kwargs: Any) -> HttpResponse:
        return HttpResponse(status=200, payload={"code": 403, "message": "denied", "data": None})

    client = _client()
    with patch("nanhu.auth.http_json", side_effect=_fake_http_factory(handler)), patch(
        "nanhu.http.http_json", side_effect=_fake_http_factory(handler)
    ):
        with pytest.raises(ApiError) as exc_info:
            algorithms.get_algorithm(client, "missing", is_public=False)
    assert exc_info.value.code == 403


def test_create_algorithm_dry_run_and_submit() -> None:
    client = _client()
    body = {
        "name": "a1",
        "algoType": "train",
        "srcType": "image",
        "imageUrl": "reg/x:v1",
        "supportedClusterIds": ["X10000"],
    }
    dry = algorithms.create_algorithm(client, body)
    assert dry["dry_run"] is True
    assert dry["method"] == "POST"
    assert dry["path"] == algorithms.ALGORITHMS_PATH
    assert dry["body"]["name"] == "a1"

    calls: list[dict[str, Any]] = []

    def handler(method: str, url: str, **kwargs: Any) -> HttpResponse:
        calls.append({"method": method, "url": url, "body": kwargs.get("body")})
        return _ok("new-uuid")

    with patch("nanhu.auth.http_json", side_effect=_fake_http_factory(handler)), patch(
        "nanhu.http.http_json", side_effect=_fake_http_factory(handler)
    ):
        out = algorithms.create_algorithm(client, body, submit=True)
    assert out["data"] == "new-uuid"
    assert calls[0]["method"] == "POST"
    assert calls[0]["body"]["algoType"] == "train"


def test_update_delete_publish_share_dry_run() -> None:
    client = _client()
    uid = "algo-u1"
    upd = algorithms.update_algorithm(
        client, uid, {"algoType": "train", "srcType": "image", "imageUrl": "x"}
    )
    assert upd["method"] == "PUT"
    assert upd["path"] == f"{algorithms.ALGORITHMS_PATH}/{uid}"

    dele = algorithms.delete_algorithm(client, uid)
    assert dele["method"] == "DELETE"
    assert dele["dry_run"] is True

    pub = algorithms.publish_algorithm(client, uid)
    assert pub["method"] == "PUT"
    assert pub["path"].endswith("/share")

    unpub = algorithms.unpublish_algorithm(client, uid)
    assert unpub["path"].endswith("/stop-share")

    share = algorithms.share_algorithm(client, uid, "000012")
    assert share["method"] == "POST"
    assert share["body"] == {"userName": "000012"}

    unshare = algorithms.unshare_algorithm(client, uid, "000012,000245")
    assert unshare["method"] == "DELETE"
    assert unshare["query"]["shareList"] == ["000012", "000245"]


def test_unshare_algorithm_submit_doseq() -> None:
    calls: list[dict[str, Any]] = []

    def handler(method: str, url: str, **kwargs: Any) -> HttpResponse:
        calls.append({"method": method, "url": url})
        return _ok({})

    client = _client()
    with patch("nanhu.auth.http_json", side_effect=_fake_http_factory(handler)), patch(
        "nanhu.http.http_json", side_effect=_fake_http_factory(handler)
    ):
        algorithms.unshare_algorithm(client, "u1", ["a", "b"], submit=True)

    assert calls[0]["method"] == "DELETE"
    parsed = urlparse(calls[0]["url"])
    assert parsed.path.endswith("/algorithms/u1/share")
    qs = parse_qs(parsed.query)
    assert qs["shareList"] == ["a", "b"]
    assert qs["userId"] == ["uid-algo"]


def test_build_algorithm_payload_friendly() -> None:
    body = algorithms.build_algorithm_payload(
        {
            "name": "n",
            "algo_type": "train",
            "src_type": "oss",
            "image_url": "img",
            "supported_cluster_ids": ["X10000"],
            "oss_path": {"uuid": "o1", "bucket": "b1", "path": "p"},
        }
    )
    assert body["algoType"] == "train"
    assert body["ossPath"]["bucket"] == "b1"
    assert body["supportedClusterIds"] == ["X10000"]
