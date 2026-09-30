"""Tests for restartInferenceJob (变配) and podRestart."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from nanhu.api.jobs import (
    PATH_POD_RESTART,
    PATH_RESTART_INFERENCE,
    JobsApi,
    restart_failed_pods,
    restart_inference_from_config,
    restart_inference_job,
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
    mock = MagicMock(return_value={"code": "200", "data": {}})
    client.request = mock  # type: ignore[method-assign]
    return mock


def _deploy_body(uuid: str = "job-uuid-1") -> dict:
    return {
        "uuid": uuid,
        "name": "deploy-a",
        "inferenceType": "customized",
        "resource": {
            "projectUuid": "p1",
            "subMissionName": "sm",
            "computeSpecUuid": "cs1",
            "computeSpecName": "spec",
            "workerNum": 1,
        },
        "envVars": [],
    }


def test_restart_inference_dry_run() -> None:
    client = _client()
    mock = _mock_request(client)
    body = _deploy_body()
    out = restart_inference_job(client, body)
    assert out["dry_run"] is True
    assert out["method"] == "POST"
    assert out["path"] == PATH_RESTART_INFERENCE
    assert out["query"]["userId"] == "uid-99"
    assert out["query"]["bizType"] == "DROS"
    assert out["body"]["uuid"] == "job-uuid-1"
    mock.assert_not_called()


def test_restart_inference_submit() -> None:
    client = _client()
    mock = _mock_request(client)
    body = _deploy_body("jb-2")
    out = JobsApi(client).restart_inference_job(body, submit=True)
    assert "dry_run" not in out
    method, path = mock.call_args.args[:2]
    assert method == "POST"
    assert path == PATH_RESTART_INFERENCE
    assert mock.call_args.kwargs["body"]["uuid"] == "jb-2"


def test_restart_inference_requires_uuid() -> None:
    client = _client()
    with pytest.raises(ValueError, match="uuid"):
        restart_inference_job(client, {"name": "x"})


def test_restart_inference_from_config(tmp_path: Path) -> None:
    cfg = tmp_path / "d.yaml"
    cfg.write_text(
        "\n".join(
            [
                "uuid: cfg-uuid",
                "name: d1",
                "inference_type: customized",
                "resource:",
                "  project_uuid: p1",
                "  sub_mission_name: sm",
                "  compute_spec_uuid: cs",
                "  compute_spec_name: sn",
                "  worker_num: 2",
            ]
        ),
        encoding="utf-8",
    )
    client = _client()
    mock = _mock_request(client)
    out = restart_inference_from_config(client, cfg)
    assert out["dry_run"] is True
    assert out["body"]["uuid"] == "cfg-uuid"
    assert out["body"]["resource"]["workerNum"] == 2
    mock.assert_not_called()


def test_restart_failed_pods_dry_run() -> None:
    client = _client()
    mock = _mock_request(client)
    out = restart_failed_pods(client, "jb-1", "pod-a,pod-b")
    assert out["dry_run"] is True
    assert out["path"] == PATH_POD_RESTART
    assert out["body"] == {
        "userId": "uid-99",
        "jobId": "jb-1",
        "jobPodNames": "pod-a,pod-b",
    }
    mock.assert_not_called()


def test_restart_failed_pods_submit_list() -> None:
    client = _client()
    mock = _mock_request(client)
    out = restart_failed_pods(client, "jb-2", ["p0", "p1"], submit=True)
    assert "dry_run" not in out
    method, path = mock.call_args.args[:2]
    assert method == "POST"
    assert path == PATH_POD_RESTART
    assert mock.call_args.kwargs["body"]["jobPodNames"] == "p0,p1"
