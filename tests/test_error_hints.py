"""Tests for actionable error hints on known wuxi capability gaps."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from nanhu import cli
from nanhu.http import ApiError, hint_for_error


@pytest.fixture
def fake_client() -> MagicMock:
    client = MagicMock(name="NanhuClient")
    client.user_id = "u-test"
    client.api_base = "http://10.0.0.1:38080"
    return client


def test_hint_for_wuxi_images_path() -> None:
    exc = ApiError(
        "Not Found",
        http_status=404,
        url="http://10.1.1.1/api/open/dros-ic-platform/open-job/images",
    )
    hint = hint_for_error(exc, cluster="wuxi")
    assert hint is not None
    assert "镜像" in hint
    assert "x10000" in hint


def test_hint_for_wuxi_devenv_list() -> None:
    exc = ApiError(
        "Not Found",
        http_status=404,
        url="http://10.1.1.1/api/open/dros-ic-platform/dev-env/list",
    )
    hint = hint_for_error(exc, cluster="wuxi")
    assert hint is not None
    assert "开发环境" in hint


def test_hint_for_wuxi_job_list_all() -> None:
    exc = ApiError(
        "Not Found",
        http_status=404,
        url="http://10.1.1.1/api/open/dros-ic-platform/open-job/jobListAll",
    )
    hint = hint_for_error(exc, cluster="wuxi")
    assert hint is not None
    assert "jobListAll" in hint or "jobs list" in hint


def test_hint_generic_404_on_wuxi() -> None:
    exc = ApiError("Not Found", http_status=404, url="http://10.1.1.1/api/open/unknown")
    hint = hint_for_error(exc, cluster="wuxi")
    assert hint is not None
    assert "404" in hint


def test_hint_not_applied_on_x10000_known_path() -> None:
    exc = ApiError(
        "Not Found",
        http_status=404,
        url="http://10.1.1.1/api/open/dros-ic-platform/open-job/images",
    )
    assert hint_for_error(exc, cluster="x10000") is None


def test_cli_emits_hint_on_api_error(
    fake_client: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    exc = ApiError(
        "Not Found",
        http_status=404,
        url="http://10.1.1.1/api/open/dros-ic-platform/open-job/images",
    )
    with (
        patch.object(cli, "_build_client", return_value=fake_client),
        patch.object(cli.images_api, "list_images", side_effect=exc),
    ):
        code = cli.main(
            ["--cluster", "wuxi", "images", "list", "--is-public", "false"]
        )
    assert code == 1
    data = json.loads(capsys.readouterr().out)
    assert data["type"] == "ApiError"
    assert "hint" in data
    assert "镜像" in data["hint"]
