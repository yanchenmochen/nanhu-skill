"""Tests for create train job (V2/V3, YAML payload, dry-run default)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from nanhu.api.jobs import (
    PATH_CREATE_TRAIN_V2,
    PATH_CREATE_TRAIN_V3,
    build_train_payload,
    create_train,
    create_train_from_config,
    load_job_config,
)
from nanhu.client import NanhuClient

FRIENDLY_CFG = {
    "biz_type": "DROS",
    "job_type": "AI_TRAIN",
    "name_prefix": "demo-train",
    "algorithm": {
        "uuid": "algo-uuid-1",
        "name": "algo-name-1",
        "mount_path": "/mnt/algo",
    },
    "start_cmd": "python train.py",
    "resource": {
        "project_uuid": "pr-1",
        "sub_mission_name": "mission-a",
        "compute_spec_uuid": "spec-1",
        "compute_spec_name": "GPU-8",
        "worker_num": 2,
    },
    "mounted_storages": [
        {
            "uuid": "oss-1",
            "oss_name": "zj-data",
            "bucket": "data",
            "path": "/",
            "output_path": "/mnt/data",
        }
    ],
    "output_dir": {
        "uuid": "oss-1",
        "bucket": "data",
        "path": "/out",
        "output_path": "/mnt/out",
    },
    "env_vars": {"OUTPUT_DIR": "/mnt/out", "FOO": "1"},
    "use_tensorboard": False,
    "auto_restart": True,
}


def _client() -> NanhuClient:
    return NanhuClient(
        "http://10.124.120.108:38080",
        user_id="uid-train",
        app_key="k",
        app_secret="s",
    )


def _mock_request(client: NanhuClient) -> MagicMock:
    mock = MagicMock(return_value={"code": "200", "data": {"jobId": "jb-new"}})
    client.request = mock  # type: ignore[method-assign]
    return mock


def test_build_train_payload_from_friendly_yaml() -> None:
    body = build_train_payload(FRIENDLY_CFG, name="my-job")
    assert body["name"] == "my-job"
    assert body["jobType"] == "AI_TRAIN"
    assert body["algorithmUuid"] == "algo-uuid-1"
    assert body["algorithmName"] == "algo-name-1"
    assert body["algorithmMountPath"] == "/mnt/algo"
    assert body["startCmd"] == "python train.py"
    assert body["resource"] == {
        "projectUuid": "pr-1",
        "subMissionName": "mission-a",
        "computeSpecUuid": "spec-1",
        "computeSpecName": "GPU-8",
        "workerNum": 2,
    }
    assert body["mountedStorages"][0]["ossName"] == "zj-data"
    assert body["mountedStorages"][0]["outputPath"] == "/mnt/data"
    assert body["outputDir"]["outputPath"] == "/mnt/out"
    assert {"key": "OUTPUT_DIR", "value": "/mnt/out"} in body["envVars"]
    assert body["autoRestart"] is True
    assert body["useTensorBoard"] is False


def test_build_train_payload_api_shaped_passthrough() -> None:
    api_body = {
        "name": "x",
        "jobType": "AI_TRAIN",
        "algorithmUuid": "a",
        "algorithmName": "n",
        "startCmd": "echo",
        "resource": {
            "projectUuid": "p",
            "subMissionName": "s",
            "computeSpecUuid": "c",
            "computeSpecName": "GPU-1",
            "workerNum": 1,
        },
        "envVars": [{"key": "A", "value": "1"}],
    }
    out = build_train_payload(api_body, worker_num=4, extra_env={"B": "2"})
    assert out["resource"]["workerNum"] == 4
    keys = {e["key"] for e in out["envVars"]}
    assert keys == {"A", "B"}


def test_create_train_v2_dry_run() -> None:
    client = _client()
    mock = _mock_request(client)
    body = build_train_payload(FRIENDLY_CFG, name="dry-job")
    out = create_train(client, body, version="v2")
    assert out["dry_run"] is True
    assert out["method"] == "POST"
    assert out["path"] == PATH_CREATE_TRAIN_V2
    assert out["query"] == {"userId": "uid-train", "bizType": "DROS"}
    assert out["body"]["name"] == "dry-job"
    mock.assert_not_called()


def test_create_train_v2_submit() -> None:
    client = _client()
    mock = _mock_request(client)
    body = build_train_payload(FRIENDLY_CFG, name="live-job")
    out = create_train(client, body, version="v2", submit=True)
    assert out["data"]["jobId"] == "jb-new"
    method, path = mock.call_args.args[:2]
    assert method == "POST"
    assert path == PATH_CREATE_TRAIN_V2
    assert mock.call_args.kwargs["query"]["userId"] == "uid-train"
    assert mock.call_args.kwargs["body"]["name"] == "live-job"


def test_create_train_v3_path_and_query() -> None:
    client = _client()
    mock = _mock_request(client)
    body = {
        "name": "v3-job",
        "jobType": "AI_TRAIN",
        "algorithmImageUrl": "harbor.example/img:v1",
        "startCmd": "bash run.sh",
        "resource": {
            "projectUuid": "p",
            "subMissionName": "s",
            "computeSpecUuid": "c",
            "computeSpecName": "GPU-8",
            "workerNum": 1,
        },
        "envVars": [{"key": "OUTPUT_DIR", "value": "/out"}],
    }
    out = create_train(client, body, version="v3")
    assert out["path"] == PATH_CREATE_TRAIN_V3
    assert "bizType" not in out["query"]
    assert out["query"]["userId"] == "uid-train"
    mock.assert_not_called()

    create_train(client, body, version="v3", submit=True)
    assert mock.call_args.args[1] == PATH_CREATE_TRAIN_V3
    assert "bizType" not in mock.call_args.kwargs["query"]


def test_create_train_from_config_yaml_file(tmp_path: Path) -> None:
    yaml_path = tmp_path / "train.yaml"
    yaml_path.write_text(
        """
name: from-yaml
job_type: AI_TRAIN
algorithm:
  uuid: u1
  name: n1
start_cmd: python main.py
resource:
  project_uuid: pr
  sub_mission_name: sm
  compute_spec_uuid: cs
  compute_spec_name: GPU-8
  worker_num: 1
env_vars:
  OUTPUT_DIR: /tmp
""",
        encoding="utf-8",
    )
    client = _client()
    mock = _mock_request(client)
    out = create_train_from_config(client, yaml_path)
    assert out["dry_run"] is True
    assert out["body"]["name"] == "from-yaml"
    assert out["body"]["algorithmUuid"] == "u1"
    assert load_job_config(yaml_path)["name"] == "from-yaml"
    mock.assert_not_called()


def test_create_train_bad_version() -> None:
    client = _client()
    with pytest.raises(ValueError, match="unsupported train API version"):
        create_train(client, {"name": "x"}, version="v9")
