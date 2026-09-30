"""Tests for nanhu.api.seahold (mocked HTTP)."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pytest

from nanhu.api import seahold
from nanhu.auth import TokenCache
from nanhu.client import NanhuClient
from nanhu.http import HttpResponse


def _client() -> NanhuClient:
    return NanhuClient(
        "http://10.202.32.189:38080",
        user_id="uid-sea",
        app_key="k",
        app_secret="s",
        token_cache=TokenCache(),
    )


def _ok(data: Any, *, code: Any = "200") -> HttpResponse:
    return HttpResponse(
        status=200,
        payload={"code": code, "message": "SUCCESS", "data": data},
    )


def _fake_http_factory(handler):
    def fake_http(method: str, url: str, **kwargs: Any) -> HttpResponse:
        if url.rstrip("/").endswith("/api/open/credentials"):
            return HttpResponse(
                status=200,
                payload={"code": 0, "data": {"accessToken": "tok-sea"}},
            )
        return handler(method, url, **kwargs)

    return fake_http


def test_list_seahold() -> None:
    calls: list[dict[str, Any]] = []

    def handler(method: str, url: str, **kwargs: Any) -> HttpResponse:
        calls.append({"method": method, "url": url, "body": kwargs.get("body")})
        return _ok({"total": 1, "list": [{"uuid": "ds-1", "status": "Created"}]})

    client = _client()
    with patch("nanhu.auth.http_json", side_effect=_fake_http_factory(handler)), patch(
        "nanhu.http.http_json", side_effect=_fake_http_factory(handler)
    ):
        out = seahold.list_seahold(client, status="Created", page=1, page_size=10)

    assert out["data"]["list"][0]["uuid"] == "ds-1"
    assert calls[0]["method"] == "POST"
    assert seahold.PATH_LIST in calls[0]["url"]
    qs = parse_qs(urlparse(calls[0]["url"]).query)
    assert qs["userId"] == ["uid-sea"]
    assert calls[0]["body"]["status"] == "Created"
    assert calls[0]["body"]["pageSize"] == 10


def test_create_seahold_dry_run_and_submit() -> None:
    client = _client()
    body = {
        "seaholdDataSets": [
            {"uuid": "u1", "name": "n1", "ak": "AK", "sk": "SK"},
        ]
    }
    dry = seahold.create_seahold(client, body)
    assert dry["dry_run"] is True
    assert dry["path"] == seahold.PATH_CREATE
    assert dry["body"] == body

    calls: list[dict[str, Any]] = []

    def handler(method: str, url: str, **kwargs: Any) -> HttpResponse:
        calls.append({"method": method, "url": url, "body": kwargs.get("body")})
        return _ok([{"uuid": "u1", "status": "Created"}])

    with patch("nanhu.auth.http_json", side_effect=_fake_http_factory(handler)), patch(
        "nanhu.http.http_json", side_effect=_fake_http_factory(handler)
    ):
        out = seahold.create_seahold(client, body, submit=True)
    assert out["data"][0]["status"] == "Created"
    assert calls[0]["method"] == "POST"
    assert seahold.PATH_CREATE in calls[0]["url"]


def test_create_from_config(tmp_path: Path) -> None:
    cfg = tmp_path / "s.yaml"
    cfg.write_text(
        "\n".join(
            [
                "seahold_data_sets:",
                "  - uuid: u1",
                "    name: n1",
                "    ak: AK",
                "    sk: SK",
            ]
        ),
        encoding="utf-8",
    )
    client = _client()
    out = seahold.create_seahold_from_config(client, cfg)
    assert out["dry_run"] is True
    assert out["body"]["seaholdDataSets"][0]["uuid"] == "u1"


def test_destroy_seahold_dry_run() -> None:
    client = _client()
    out = seahold.destroy_seahold(client, uuid="u1", ak="AK", sk="SK")
    assert out["dry_run"] is True
    assert out["path"] == seahold.PATH_DESTROY
    assert out["body"] == {"uuid": "u1", "ak": "AK", "sk": "SK"}


def test_create_requires_datasets() -> None:
    client = _client()
    with pytest.raises(ValueError, match="seaholdDataSets"):
        seahold.create_seahold(client, {})
