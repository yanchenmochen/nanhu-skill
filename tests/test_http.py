"""Tests for nanhu.http — proxy bypass and response parsing (mocked)."""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.request
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from nanhu.http import (
    ApiError,
    HttpError,
    HttpResponse,
    http_json,
    is_private_api_host,
    is_success_code,
    parse_api_payload,
    request_json,
)


class _FakeResp:
    def __init__(self, body: bytes, status: int = 200) -> None:
        self._body = body
        self._status = status

    def read(self) -> bytes:
        return self._body

    def getcode(self) -> int:
        return self._status

    def __enter__(self) -> "_FakeResp":
        return self

    def __exit__(self, *args: Any) -> None:
        return None


def test_is_private_api_host() -> None:
    assert is_private_api_host("http://10.124.120.108:38080/api")
    assert is_private_api_host("http://10.202.32.189:38080/")
    assert not is_private_api_host("https://example.com/api")
    assert not is_private_api_host("http://hostname.local/api")


@pytest.mark.parametrize("code", [0, "0", 200, "200"])
def test_is_success_code(code: Any) -> None:
    assert is_success_code(code)


@pytest.mark.parametrize("code", [1, "1", 500, None, ""])
def test_is_success_code_false(code: Any) -> None:
    assert not is_success_code(code)


def test_http_json_private_host_uses_empty_proxy() -> None:
    url = "http://10.124.120.108:38080/api/open/credentials"
    payload = {"code": 0, "data": {"accessToken": "t"}}
    fake = _FakeResp(json.dumps(payload).encode())

    mock_opener = MagicMock()
    mock_opener.open.return_value = fake

    with (
        patch("nanhu.http.urllib.request.build_opener", return_value=mock_opener) as build,
        patch("nanhu.http.urllib.request.urlopen") as urlopen,
    ):
        result = http_json("POST", url, body={"appKey": "k", "appSecret": "s"})

    build.assert_called_once()
    # First arg to build_opener should be ProxyHandler with empty proxies.
    handler = build.call_args[0][0]
    assert isinstance(handler, urllib.request.ProxyHandler)
    assert handler.proxies == {}
    mock_opener.open.assert_called_once()
    urlopen.assert_not_called()
    assert result.status == 200
    assert result.payload["data"]["accessToken"] == "t"

    req = mock_opener.open.call_args[0][0]
    assert req.get_method() == "POST"
    assert req.get_header("Content-type") == "application/json"


def test_http_json_public_host_uses_urlopen() -> None:
    url = "https://example.com/api"
    fake = _FakeResp(b'{"code":0,"data":{}}')

    with (
        patch("nanhu.http.urllib.request.urlopen", return_value=fake) as urlopen,
        patch("nanhu.http.urllib.request.build_opener") as build,
    ):
        result = http_json("GET", url)

    urlopen.assert_called_once()
    build.assert_not_called()
    assert result.payload["code"] == 0


def test_http_json_http_error_returns_body() -> None:
    url = "http://10.1.1.1:1/x"
    err = urllib.error.HTTPError(
        url, 401, "Unauthorized", hdrs=None, fp=io.BytesIO(b'{"code":401,"message":"no"}')
    )
    mock_opener = MagicMock()
    mock_opener.open.side_effect = err

    with patch("nanhu.http.urllib.request.build_opener", return_value=mock_opener):
        result = http_json("GET", url)

    assert result.status == 401
    assert result.payload["code"] == 401


def test_http_json_url_error_raises() -> None:
    url = "http://10.1.1.1:1/x"
    mock_opener = MagicMock()
    mock_opener.open.side_effect = urllib.error.URLError("boom")

    with (
        patch("nanhu.http.urllib.request.build_opener", return_value=mock_opener),
        pytest.raises(HttpError, match="boom"),
    ):
        http_json("GET", url)


def test_parse_api_payload_success() -> None:
    resp = HttpResponse(status=200, payload={"code": "200", "data": {"id": 1}})
    out = parse_api_payload(resp)
    assert out["data"]["id"] == 1


def test_parse_api_payload_failure_raises() -> None:
    resp = HttpResponse(status=200, payload={"code": 1, "message": "bad"})
    with pytest.raises(ApiError, match="bad") as ei:
        parse_api_payload(resp)
    assert ei.value.code == 1


def test_request_json_end_to_end_mock() -> None:
    url = "http://10.202.32.189:38080/api/x"
    fake = _FakeResp(json.dumps({"code": 0, "data": {"ok": True}}).encode())
    mock_opener = MagicMock()
    mock_opener.open.return_value = fake

    with patch("nanhu.http.urllib.request.build_opener", return_value=mock_opener):
        out = request_json("GET", url, headers={"accessToken": "tok"})

    assert out["data"]["ok"] is True
    req = mock_opener.open.call_args[0][0]
    assert req.get_header("Accesstoken") == "tok" or req.headers.get("accessToken") == "tok"
