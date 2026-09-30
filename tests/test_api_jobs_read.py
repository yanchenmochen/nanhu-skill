"""Tests for jobs read APIs (list / detail / full list)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from nanhu.api.jobs import (
    JOB_TYPE_DEPLOY,
    JOB_TYPE_TRAIN,
    PATH_JOB_DETAIL,
    PATH_JOB_LIST,
    PATH_JOB_LIST_ALL,
    JobsApi,
    get_job_detail,
    list_deploy_jobs,
    list_jobs,
    list_jobs_all,
    list_train_jobs,
)
from nanhu.client import NanhuClient


def _client() -> NanhuClient:
    return NanhuClient(
        "http://10.124.120.108:38080",
        user_id="uid-42",
        app_key="k",
        app_secret="s",
    )


def _mock_request(client: NanhuClient) -> MagicMock:
    mock = MagicMock(return_value={"code": 0, "data": {"result": []}})
    client.request = mock  # type: ignore[method-assign]
    return mock


def test_list_train_jobs_query() -> None:
    client = _client()
    mock = _mock_request(client)
    out = list_train_jobs(client, status="running", current=1, page_size=20)
    assert out["code"] == 0
    mock.assert_called_once()
    method, path = mock.call_args.args[:2]
    kwargs = mock.call_args.kwargs
    assert method == "GET"
    assert path == PATH_JOB_LIST
    assert kwargs["query"] == {
        "userId": "uid-42",
        "bizType": "DROS",
        "jobType": JOB_TYPE_TRAIN,
        "status": "running",
        "current": 1,
        "pageSize": 20,
    }


def test_list_deploy_jobs_via_api_class() -> None:
    client = _client()
    mock = _mock_request(client)
    JobsApi(client).list_deploy_jobs(project_id="pr-1")
    kwargs = mock.call_args.kwargs
    assert kwargs["query"]["jobType"] == JOB_TYPE_DEPLOY
    assert kwargs["query"]["projectId"] == "pr-1"
    assert kwargs["query"]["userId"] == "uid-42"


def test_list_jobs_custom_type() -> None:
    client = _client()
    mock = _mock_request(client)
    list_jobs(client, "AI_TRAIN", biz_type="DROS")
    assert mock.call_args.kwargs["query"]["jobType"] == "AI_TRAIN"


def test_get_job_detail_query() -> None:
    client = _client()
    mock = _mock_request(client)
    mock.return_value = {"code": 0, "data": {"uuid": "jb-1", "status": "running"}}
    out = get_job_detail(client, "jb-1", job_type=JOB_TYPE_TRAIN)
    assert out["data"]["uuid"] == "jb-1"
    method, path = mock.call_args.args[:2]
    assert method == "GET"
    assert path == PATH_JOB_DETAIL
    assert mock.call_args.kwargs["query"] == {
        "userId": "uid-42",
        "bizType": "DROS",
        "jobId": "jb-1",
        "jobType": JOB_TYPE_TRAIN,
    }


def test_list_jobs_all_omits_biz_type() -> None:
    client = _client()
    mock = _mock_request(client)
    list_jobs_all(client, job_type=JOB_TYPE_TRAIN, status="error", page_size=50)
    method, path = mock.call_args.args[:2]
    assert method == "GET"
    assert path == PATH_JOB_LIST_ALL
    q: dict[str, Any] = mock.call_args.kwargs["query"]
    assert "bizType" not in q
    assert q == {
        "userId": "uid-42",
        "jobType": JOB_TYPE_TRAIN,
        "status": "error",
        "pageSize": 50,
    }


def test_optional_filters_omitted_when_none() -> None:
    client = _client()
    mock = _mock_request(client)
    get_job_detail(client, "jb-x")
    q = mock.call_args.kwargs["query"]
    assert q == {"userId": "uid-42", "bizType": "DROS", "jobId": "jb-x"}
    assert "jobType" not in q
