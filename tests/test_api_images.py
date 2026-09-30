"""Tests for nanhu.api.images (mocked HTTP)."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pytest

from nanhu.auth import TokenCache
from nanhu.client import NanhuClient
from nanhu.http import ApiError, HttpResponse
from nanhu.api import images


def _client() -> NanhuClient:
    return NanhuClient(
        "http://10.202.32.189:38080",
        user_id="uid-img",
        app_key="k",
        app_secret="s",
        token_cache=TokenCache(),
    )


def _ok(data: Any, *, code: Any = "200") -> HttpResponse:
    return HttpResponse(
        status=200,
        payload={"code": code, "msg": "SUCCESS", "data": data, "traceId": "t1"},
    )


def _fake_http_factory(handler):
    def fake_http(method: str, url: str, **kwargs: Any) -> HttpResponse:
        if url.rstrip("/").endswith("/api/open/credentials"):
            return HttpResponse(
                status=200,
                payload={"code": 0, "data": {"accessToken": "tok-img"}},
            )
        return handler(method, url, **kwargs)

    return fake_http


def test_list_images_injects_query_and_token() -> None:
    calls: list[dict[str, Any]] = []

    def handler(method: str, url: str, **kwargs: Any) -> HttpResponse:
        calls.append({"method": method, "url": url, "headers": kwargs.get("headers")})
        return _ok(
            {
                "page": {"total": 1, "current": 1, "pageSize": 10},
                "result": [
                    {
                        "uuid": "img-1",
                        "name": "002929/add-model-api",
                        "source": "x10000",
                        "imageCount": 3,
                    }
                ],
            }
        )

    client = _client()
    with patch("nanhu.auth.http_json", side_effect=_fake_http_factory(handler)), patch(
        "nanhu.http.http_json", side_effect=_fake_http_factory(handler)
    ):
        out = images.list_images(client, is_public=False, name="add-model", current=1, page_size=10)

    assert out["data"]["result"][0]["uuid"] == "img-1"
    assert calls[0]["method"] == "GET"
    assert calls[0]["headers"]["accessToken"] == "tok-img"
    parsed = urlparse(calls[0]["url"])
    assert parsed.path == "/api/open/dros-ic-platform/open-job/images"
    qs = parse_qs(parsed.query)
    assert qs["userId"] == ["uid-img"]
    assert qs["isPublic"] == ["false"]
    assert qs["name"] == ["add-model"]
    assert qs["current"] == ["1"]
    assert qs["pageSize"] == ["10"]


def test_list_image_tags_requires_repo_and_source() -> None:
    calls: list[dict[str, Any]] = []

    def handler(method: str, url: str, **kwargs: Any) -> HttpResponse:
        calls.append({"url": url, "headers": kwargs.get("headers")})
        return _ok(
            {
                "page": {"total": 1, "current": 1, "pageSize": 100},
                "result": [
                    {
                        "uuid": "tag-1",
                        "repositoryName": "002929/add-model-api",
                        "tag": "v1",
                        "size": 1024,
                        "pullUrl": "10.0.0.1/002929/add-model-api:v1",
                    }
                ],
            }
        )

    client = _client()
    with patch("nanhu.auth.http_json", side_effect=_fake_http_factory(handler)), patch(
        "nanhu.http.http_json", side_effect=_fake_http_factory(handler)
    ):
        out = images.list_image_tags(
            client,
            repository_name="002929/add-model-api",
            source="x10000",
            page_size=50,
        )

    assert out["data"]["result"][0]["tag"] == "v1"
    parsed = urlparse(calls[0]["url"])
    assert parsed.path == "/api/open/dros-ic-platform/open-job/images/tags"
    qs = parse_qs(parsed.query)
    assert qs["userId"] == ["uid-img"]
    assert qs["repositoryName"] == ["002929/add-model-api"]
    assert qs["source"] == ["x10000"]
    assert qs["pageSize"] == ["50"]
    assert calls[0]["headers"]["accessToken"] == "tok-img"


def test_list_images_public_true() -> None:
    calls: list[dict[str, Any]] = []

    def handler(method: str, url: str, **kwargs: Any) -> HttpResponse:
        calls.append({"url": url})
        return _ok({"page": {"total": 0, "current": 1, "pageSize": 10}, "result": []})

    client = _client()
    with patch("nanhu.auth.http_json", side_effect=_fake_http_factory(handler)), patch(
        "nanhu.http.http_json", side_effect=_fake_http_factory(handler)
    ):
        images.list_images(client, is_public=True)

    qs = parse_qs(urlparse(calls[0]["url"]).query)
    assert qs["isPublic"] == ["true"]


def test_list_image_tags_api_error() -> None:
    def handler(method: str, url: str, **kwargs: Any) -> HttpResponse:
        return HttpResponse(status=200, payload={"code": 404, "msg": "not found", "data": None})

    client = _client()
    with patch("nanhu.auth.http_json", side_effect=_fake_http_factory(handler)), patch(
        "nanhu.http.http_json", side_effect=_fake_http_factory(handler)
    ):
        with pytest.raises(ApiError) as exc_info:
            images.list_image_tags(client, repository_name="x/y", source="z1120")
    assert exc_info.value.code == 404


def test_share_image_dry_run_and_submit() -> None:
    client = _client()
    dry = images.share_image(client, uuid="714", source="z1120", user_name="002916")
    assert dry["dry_run"] is True
    assert dry["method"] == "POST"
    assert dry["path"] == images.IMAGE_SHARE_PATH
    assert dry["body"] == {"uuid": "714", "source": "z1120", "userName": "002916"}

    calls: list[dict[str, Any]] = []

    def handler(method: str, url: str, **kwargs: Any) -> HttpResponse:
        calls.append({"method": method, "url": url, "body": kwargs.get("body")})
        return _ok(None)

    with patch("nanhu.auth.http_json", side_effect=_fake_http_factory(handler)), patch(
        "nanhu.http.http_json", side_effect=_fake_http_factory(handler)
    ):
        images.share_image(
            client, uuid="714", source="z1120", user_name="002916", submit=True
        )

    assert calls[0]["method"] == "POST"
    assert images.IMAGE_SHARE_PATH in calls[0]["url"]
    assert calls[0]["body"]["userName"] == "002916"


def test_unshare_image_dry_run_and_submit() -> None:
    client = _client()
    dry = images.unshare_image(client, uuid="714", source="z1120", user_names="a,b")
    assert dry["dry_run"] is True
    assert dry["method"] == "DELETE"
    assert dry["body"]["userNameList"] == ["a", "b"]

    calls: list[dict[str, Any]] = []

    def handler(method: str, url: str, **kwargs: Any) -> HttpResponse:
        calls.append({"method": method, "body": kwargs.get("body")})
        return _ok(True)

    with patch("nanhu.auth.http_json", side_effect=_fake_http_factory(handler)), patch(
        "nanhu.http.http_json", side_effect=_fake_http_factory(handler)
    ):
        images.unshare_image(
            client, uuid="714", source="z1120", user_names=["a", "b"], submit=True
        )

    assert calls[0]["method"] == "DELETE"
    assert calls[0]["body"]["userNameList"] == ["a", "b"]
