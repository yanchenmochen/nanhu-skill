"""Tests for job stop / restart (dry-run default)."""

from __future__ import annotations

from unittest.mock import MagicMock

from nanhu.api.jobs import (
    PATH_RESTART,
    PATH_STOP,
    JobsApi,
    restart_job,
    stop_job,
)
from nanhu.client import NanhuClient


def _client() -> NanhuClient:
    return NanhuClient(
        "http://10.202.32.189:38080",
        user_id="uid-99",
        app_key="k",
        app_secret="s",
    )


def _mock_request(client: NanhuClient) -> MagicMock:
    mock = MagicMock(return_value={"code": "200", "data": {"jobId": "jb-1"}})
    client.request = mock  # type: ignore[method-assign]
    return mock


def test_stop_job_dry_run_by_default() -> None:
    client = _client()
    mock = _mock_request(client)
    out = stop_job(client, "jb-stop-1")
    assert out["dry_run"] is True
    assert out["method"] == "PUT"
    assert out["path"] == PATH_STOP
    assert out["query"] == {
        "userId": "uid-99",
        "bizType": "DROS",
        "jobId": "jb-stop-1",
    }
    assert out["body"] is None
    mock.assert_not_called()


def test_stop_job_submit() -> None:
    client = _client()
    mock = _mock_request(client)
    out = stop_job(client, "jb-stop-2", submit=True)
    assert out["data"]["jobId"] == "jb-1"
    mock.assert_called_once()
    method, path = mock.call_args.args[:2]
    assert method == "PUT"
    assert path == PATH_STOP
    assert mock.call_args.kwargs["query"]["jobId"] == "jb-stop-2"
    assert mock.call_args.kwargs["query"]["userId"] == "uid-99"


def test_restart_job_dry_run_by_default() -> None:
    client = _client()
    mock = _mock_request(client)
    out = restart_job(client, "jb-rst-1")
    assert out["dry_run"] is True
    assert out["method"] == "POST"
    assert out["path"] == PATH_RESTART
    assert out["query"] == {
        "userId": "uid-99",
        "bizType": "DROS",
        "jobId": "jb-rst-1",
    }
    mock.assert_not_called()


def test_restart_job_submit() -> None:
    client = _client()
    mock = _mock_request(client)
    out = JobsApi(client).restart_job("jb-rst-2", submit=True, biz_type="DROS")
    assert "dry_run" not in out
    method, path = mock.call_args.args[:2]
    assert method == "POST"
    assert path == PATH_RESTART
    assert mock.call_args.kwargs["query"]["jobId"] == "jb-rst-2"
