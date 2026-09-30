"""Tests for nanhu.api.devenv (mocked NanhuClient.request)."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from nanhu.api import devenv
from nanhu.auth import TokenCache
from nanhu.client import NanhuClient
from nanhu.http import HttpResponse


def _client() -> NanhuClient:
    return NanhuClient(
        "http://10.202.32.189:38080",
        user_id="uid-1",
        app_key="k",
        app_secret="s",
        token_cache=TokenCache(),
    )


def _sample_body(*, with_uuid: bool = False) -> dict[str, Any]:
    body: dict[str, Any] = {
        "name": "dev-env-test",
        "imageUrl": "registry.example.com/dev:latest",
        "sshPwd": "Passw0rd@",
        "vscodePassword": "Passw0rd@",
        "resource": {
            "projectUuid": "pr-123",
            "subMissionName": "my-project",
            "computeSpecUuid": "spec-456",
            "computeSpecName": "cpu_test",
            "workerNum": 1,
        },
        "mountedStorages": [
            {
                "uuid": "oss-789",
                "ossName": "my-oss",
                "bucket": "default",
                "path": "",
                "outputPath": "/mnt/storage",
            }
        ],
    }
    if with_uuid:
        body["uuid"] = "jb-jupyter-001"
    return body


def test_list_devenv_query(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client()
    calls: list[dict[str, Any]] = []

    def fake_request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        calls.append({"method": method, "path": path, **kwargs})
        return {"code": "200", "data": {"page": {"current": 1, "pageSize": 10, "total": 0}, "result": []}}

    monkeypatch.setattr(client, "request", fake_request)
    out = devenv.list_devenv(client, status="running", project_id="pr-1", current=2, page_size=10)
    assert out["data"]["result"] == []
    assert calls[0]["method"] == "GET"
    assert calls[0]["path"] == devenv.PATH_LIST
    q = calls[0]["query"]
    assert q["userId"] == "uid-1"
    assert q["jobType"] == "JUPYTER"
    assert q["status"] == "running"
    assert q["projectId"] == "pr-1"
    assert q["current"] == 2
    assert q["pageSize"] == 10


def test_get_devenv_query(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client()
    calls: list[dict[str, Any]] = []

    def fake_request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        calls.append({"method": method, "path": path, **kwargs})
        return {"code": "200", "data": {"uuid": "jb-1", "name": "t1"}}

    monkeypatch.setattr(client, "request", fake_request)
    out = devenv.get_devenv(client, "jb-1", biz_type="DROS")
    assert out["data"]["uuid"] == "jb-1"
    assert calls[0]["path"] == devenv.PATH_DETAIL
    q = calls[0]["query"]
    assert q == {
        "userId": "uid-1",
        "jobId": "jb-1",
        "jobType": "JUPYTER",
        "bizType": "DROS",
    }


def test_create_devenv_dry_run_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client()
    request = MagicMock()
    monkeypatch.setattr(client, "request", request)
    body = _sample_body()
    out = devenv.create_devenv(client, body)
    assert out["dry_run"] is True
    assert out["method"] == "POST"
    assert out["path"] == devenv.PATH_CREATE
    assert out["query"]["userId"] == "uid-1"
    assert out["body"]["name"] == "dev-env-test"
    request.assert_not_called()


def test_create_devenv_submit(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client()
    calls: list[dict[str, Any]] = []

    def fake_request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        calls.append({"method": method, "path": path, **kwargs})
        return {"code": "200", "data": {"jobId": "jb-new"}}

    monkeypatch.setattr(client, "request", fake_request)
    body = _sample_body()
    out = devenv.create_devenv(client, body, submit=True)
    assert out["data"]["jobId"] == "jb-new"
    assert calls[0]["method"] == "POST"
    assert calls[0]["path"] == devenv.PATH_CREATE
    assert calls[0]["body"]["imageUrl"] == body["imageUrl"]
    assert calls[0]["query"]["userId"] == "uid-1"


def test_restart_devenv_requires_uuid() -> None:
    client = _client()
    with pytest.raises(ValueError, match="uuid"):
        devenv.restart_devenv(client, _sample_body())


def test_restart_devenv_dry_run_and_submit(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client()
    request = MagicMock()
    monkeypatch.setattr(client, "request", request)
    body = _sample_body(with_uuid=True)
    dry = devenv.restart_devenv(client, body)
    assert dry["dry_run"] is True
    assert dry["path"] == devenv.PATH_RESTART
    assert dry["body"]["uuid"] == "jb-jupyter-001"
    request.assert_not_called()

    calls: list[dict[str, Any]] = []

    def fake_request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        calls.append({"method": method, "path": path, **kwargs})
        return {"code": "200", "data": {"jobId": "jb-jupyter-001"}}

    monkeypatch.setattr(client, "request", fake_request)
    out = devenv.restart_devenv(client, body, submit=True)
    assert out["data"]["jobId"] == "jb-jupyter-001"
    assert calls[0]["path"] == devenv.PATH_RESTART
    assert calls[0]["body"]["uuid"] == "jb-jupyter-001"


def test_save_image_dry_run_and_submit(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client()
    request = MagicMock()
    monkeypatch.setattr(client, "request", request)
    dry = devenv.save_image(client, "jb-1", repository="dev-env", tag="v1")
    assert dry["dry_run"] is True
    assert dry["path"] == devenv.PATH_SAVE_IMAGE
    assert dry["query"]["jobId"] == "jb-1"
    assert dry["body"] == {"repository": "dev-env", "tag": "v1"}
    request.assert_not_called()

    calls: list[dict[str, Any]] = []

    def fake_request(method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        calls.append({"method": method, "path": path, **kwargs})
        return {"code": "200", "data": {}}

    monkeypatch.setattr(client, "request", fake_request)
    out = devenv.save_image(client, "jb-1", repository="dev-env", tag="v1", submit=True)
    assert out["code"] == "200"
    assert calls[0]["method"] == "POST"
    assert calls[0]["path"] == devenv.PATH_SAVE_IMAGE
    assert calls[0]["query"]["userId"] == "uid-1"
    assert calls[0]["query"]["jobId"] == "jb-1"
    assert calls[0]["body"] == {"repository": "dev-env", "tag": "v1"}


def test_create_validates_required_fields() -> None:
    client = _client()
    with pytest.raises(ValueError, match="missing required"):
        devenv.create_devenv(client, {"name": "x"})


def test_build_create_body_from_snake_yaml(tmp_path: Path) -> None:
    path = tmp_path / "devenv.yaml"
    path.write_text(
        """
name: my-dev
image_url: registry.example.com/dev:v1
ssh_pwd: Passw0rd@
vscode_password: Passw0rd@
resource:
  project_uuid: pr-1
  sub_mission_name: demo
  compute_spec_uuid: spec-1
  compute_spec_name: cpu_test
  worker_num: 1
mounted_storages:
  - uuid: oss-1
    oss_name: store
    bucket: default
    output_path: /mnt/data
env_vars:
  FOO: bar
customize_ports:
  - 8881
""",
        encoding="utf-8",
    )
    cfg = devenv.load_devenv_config(path)
    body = devenv.build_create_body(cfg)
    assert body["imageUrl"] == "registry.example.com/dev:v1"
    assert body["resource"]["projectUuid"] == "pr-1"
    assert body["mountedStorages"][0]["ossName"] == "store"
    assert body["envVars"] == [{"key": "FOO", "value": "bar"}]
    assert body["customizePorts"] == [8881]
    restart = devenv.build_create_body(cfg, uuid="jb-9")
    assert restart["uuid"] == "jb-9"


def test_client_request_attaches_token_for_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """Integration-ish: list goes through NanhuClient.request → http layer."""
    client = _client()
    seen: list[dict[str, Any]] = []

    def fake_http(method: str, url: str, **kwargs: Any) -> HttpResponse:
        seen.append({"method": method, "url": url, "headers": kwargs.get("headers"), "body": kwargs.get("body")})
        if url.endswith("/api/open/credentials"):
            return HttpResponse(status=200, payload={"code": 0, "data": {"accessToken": "tok-list"}})
        return HttpResponse(
            status=200,
            payload={"code": "200", "data": {"page": {"current": 1, "pageSize": 100, "total": 0}, "result": []}},
        )

    monkeypatch.setattr("nanhu.auth.http_json", fake_http)
    monkeypatch.setattr("nanhu.http.http_json", fake_http)
    out = devenv.list_devenv(client)
    assert out["data"]["result"] == []
    list_calls = [c for c in seen if "dev-env/list" in c["url"]]
    assert len(list_calls) == 1
    assert list_calls[0]["method"] == "GET"
    assert "userId=uid-1" in list_calls[0]["url"]
    assert "jobType=JUPYTER" in list_calls[0]["url"]
    assert list_calls[0]["headers"]["accessToken"] == "tok-list"
