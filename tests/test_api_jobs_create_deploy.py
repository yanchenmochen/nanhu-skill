"""Tests for create deploy job (V2/V3, dry-run default)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from nanhu.api.jobs import (
    PATH_CREATE_DEPLOY_V2,
    PATH_CREATE_DEPLOY_V3,
    build_deploy_payload,
    create_deploy,
    create_deploy_from_config,
)
from nanhu.client import NanhuClient

FRIENDLY_DEPLOY = {
    "name": "demo-infer",
    "inference_type": "customized",
    "algorithm": {
        "uuid": "algo-d1",
        "name": "infer-algo",
        "mount_path": "/mnt/algo",
    },
    "start_cmd": "python serve.py",
    "resource": {
        "project_uuid": "pr-d",
        "sub_mission_name": "mission-d",
        "compute_spec_uuid": "spec-d",
        "compute_spec_name": "GPU-1",
        "worker_num": 1,
    },
    "model_dir": {
        "uuid": "oss-m",
        "bucket": "model",
        "path": "Qwen2",
    },
    "env_vars": {"SERVICE_PORT": "8080"},
    "running": True,
    "expire_days": 0,
    "spread": False,
}


def _client() -> NanhuClient:
    return NanhuClient(
        "http://10.202.32.189:38080",
        user_id="uid-deploy",
        app_key="k",
        app_secret="s",
    )


def _mock_request(client: NanhuClient) -> MagicMock:
    mock = MagicMock(return_value={"code": "200", "data": {"jobId": "jb-deploy"}})
    client.request = mock  # type: ignore[method-assign]
    return mock


def test_build_deploy_payload_friendly() -> None:
    body = build_deploy_payload(FRIENDLY_DEPLOY)
    assert body["name"] == "demo-infer"
    assert body["inferenceType"] == "customized"
    assert body["algorithmUuid"] == "algo-d1"
    assert body["algorithmMountPath"] == "/mnt/algo"
    assert body["startCmd"] == "python serve.py"
    assert body["resource"]["projectUuid"] == "pr-d"
    assert body["modelDir"] == {"uuid": "oss-m", "bucket": "model", "path": "Qwen2"}
    assert body["envVars"] == [{"key": "SERVICE_PORT", "value": "8080"}]
    assert body["running"] is True
    assert body["expireDays"] == 0
    assert body["spread"] is False


def test_build_deploy_payload_api_passthrough() -> None:
    api = {
        "name": "x",
        "inferenceType": "customized",
        "algorithmUuid": "a",
        "algorithmName": "n",
        "resource": {
            "projectUuid": "p",
            "subMissionName": "s",
            "computeSpecUuid": "c",
            "computeSpecName": "GPU-1",
            "workerNum": 1,
        },
        "envVars": [{"key": "SERVICE_PORT", "value": "9000"}],
    }
    out = build_deploy_payload(api, worker_num=3, extra_env={"DEMO_PORT": "80"})
    assert out["resource"]["workerNum"] == 3
    assert {e["key"] for e in out["envVars"]} == {"SERVICE_PORT", "DEMO_PORT"}


def test_create_deploy_v2_dry_run() -> None:
    client = _client()
    mock = _mock_request(client)
    body = build_deploy_payload(FRIENDLY_DEPLOY)
    out = create_deploy(client, body, version="v2")
    assert out["dry_run"] is True
    assert out["method"] == "POST"
    assert out["path"] == PATH_CREATE_DEPLOY_V2
    assert out["query"] == {"userId": "uid-deploy", "bizType": "DROS"}
    assert out["body"]["name"] == "demo-infer"
    mock.assert_not_called()


def test_create_deploy_v2_submit() -> None:
    client = _client()
    mock = _mock_request(client)
    body = build_deploy_payload(FRIENDLY_DEPLOY)
    out = create_deploy(client, body, version="v2", submit=True)
    assert out["data"]["jobId"] == "jb-deploy"
    method, path = mock.call_args.args[:2]
    assert method == "POST"
    assert path == PATH_CREATE_DEPLOY_V2
    assert mock.call_args.kwargs["query"]["userId"] == "uid-deploy"
    assert mock.call_args.kwargs["body"]["inferenceType"] == "customized"


def test_create_deploy_v3_path() -> None:
    client = _client()
    mock = _mock_request(client)
    body = {
        "name": "v3-deploy",
        "inferenceType": "customized",
        "algorithmImageUrl": "harbor.example/infer:v1",
        "startCmd": "python app.py",
        "resource": {
            "projectUuid": "p",
            "subMissionName": "s",
            "computeSpecUuid": "c",
            "computeSpecName": "GPU-1",
            "workerNum": 1,
        },
        "envVars": [{"key": "SERVICE_PORT", "value": "8080"}],
    }
    out = create_deploy(client, body, version="v3")
    assert out["path"] == PATH_CREATE_DEPLOY_V3
    assert "bizType" not in out["query"]
    mock.assert_not_called()

    create_deploy(client, body, version="v3", submit=True)
    assert mock.call_args.args[1] == PATH_CREATE_DEPLOY_V3
    assert "bizType" not in mock.call_args.kwargs["query"]


def test_create_deploy_from_config_dict() -> None:
    client = _client()
    mock = _mock_request(client)
    out = create_deploy_from_config(client, FRIENDLY_DEPLOY, name="renamed")
    assert out["dry_run"] is True
    assert out["body"]["name"] == "renamed"
    mock.assert_not_called()


def test_create_deploy_bad_version() -> None:
    client = _client()
    with pytest.raises(ValueError, match="unsupported deploy API version"):
        create_deploy(client, {"name": "x"}, version="v0")
