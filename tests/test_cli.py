"""CLI wiring tests: jobs / devenv / pods / logs / resources / algorithms / images."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nanhu import cli


@pytest.fixture
def fake_client() -> MagicMock:
    client = MagicMock(name="NanhuClient")
    client.user_id = "u-test"
    client.api_base = "http://10.0.0.1:38080"
    return client


def _run(argv: list[str], fake_client: MagicMock, monkeypatch: pytest.MonkeyPatch) -> tuple[int, dict]:
    captured: dict = {}

    def fake_print(payload):  # type: ignore[no-untyped-def]
        captured["payload"] = payload

    monkeypatch.setattr(cli, "_print_json", fake_print)
    with patch.object(cli, "_build_client", return_value=fake_client):
        code = cli.main(argv)
    return code, captured["payload"]


# ---- jobs ----


def test_jobs_list(fake_client: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    with patch.object(cli.jobs_api, "list_jobs", return_value={"code": 0, "data": []}) as m:
        code, out = _run(
            ["--cluster", "wuxi", "jobs", "list", "--job-type", "AI_TRAIN"],
            fake_client,
            monkeypatch,
        )
    assert code == 0
    assert out == {"code": 0, "data": []}
    m.assert_called_once()
    assert m.call_args.args[0] is fake_client
    assert m.call_args.args[1] == "AI_TRAIN"


def test_jobs_detail(fake_client: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    with patch.object(cli.jobs_api, "get_job_detail", return_value={"data": {"uuid": "j1"}}) as m:
        code, out = _run(
            ["--cluster", "x10000", "jobs", "detail", "--job-id", "j1"],
            fake_client,
            monkeypatch,
        )
    assert code == 0
    assert out["data"]["uuid"] == "j1"
    m.assert_called_once_with(fake_client, "j1", biz_type="DROS", job_type=None)


def test_jobs_list_all(fake_client: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    with patch.object(cli.jobs_api, "list_jobs_all", return_value={"data": {}}) as m:
        code, _ = _run(["jobs", "list-all", "--status", "Running"], fake_client, monkeypatch)
    assert code == 0
    assert m.call_args.kwargs["status"] == "Running"


def test_jobs_stop_dry_run_default(fake_client: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    dry = {"dry_run": True, "method": "PUT", "path": "/stop", "query": {}}
    with patch.object(cli.jobs_api, "stop_job", return_value=dry) as m:
        code, out = _run(["jobs", "stop", "--job-id", "j1"], fake_client, monkeypatch)
    assert code == 0
    assert out["dry_run"] is True
    assert m.call_args.kwargs["submit"] is False


def test_jobs_stop_submit(fake_client: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    with patch.object(cli.jobs_api, "stop_job", return_value={"code": 0}) as m:
        code, _ = _run(
            ["jobs", "stop", "--job-id", "j1", "--submit"],
            fake_client,
            monkeypatch,
        )
    assert code == 0
    assert m.call_args.kwargs["submit"] is True


def test_jobs_restart_submit(fake_client: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    with patch.object(cli.jobs_api, "restart_job", return_value={"code": 0}) as m:
        code, _ = _run(
            ["jobs", "restart", "--job-id", "j1", "--submit"],
            fake_client,
            monkeypatch,
        )
    assert code == 0
    assert m.call_args.kwargs["submit"] is True


def test_jobs_restart_deploy_dry_run(
    fake_client: MagicMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = tmp_path / "d.yaml"
    cfg.write_text("uuid: u1\nname: d\n", encoding="utf-8")
    dry = {"dry_run": True, "path": "/restartInferenceJob"}
    with patch.object(cli.jobs_api, "restart_inference_from_config", return_value=dry) as m:
        code, out = _run(
            ["jobs", "restart-deploy", "--config", str(cfg)],
            fake_client,
            monkeypatch,
        )
    assert code == 0
    assert out["dry_run"] is True
    assert m.call_args.kwargs["submit"] is False
    assert m.call_args.kwargs["uuid"] is None


def test_jobs_restart_pod_submit(fake_client: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    with patch.object(cli.jobs_api, "restart_failed_pods", return_value={"code": 0}) as m:
        code, _ = _run(
            ["jobs", "restart-pod", "--job-id", "j1", "--pod-names", "a,b", "--submit"],
            fake_client,
            monkeypatch,
        )
    assert code == 0
    assert m.call_args.kwargs["submit"] is True
    assert m.call_args.args[1] == "j1"
    assert m.call_args.args[2] == "a,b"


def test_jobs_create_train_dry_run(
    fake_client: MagicMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = tmp_path / "train.yaml"
    cfg.write_text("name: demo\n", encoding="utf-8")
    dry = {"dry_run": True, "body": {"name": "demo"}}
    with patch.object(cli.jobs_api, "create_train_from_config", return_value=dry) as m:
        code, out = _run(
            ["jobs", "create-train", "--config", str(cfg)],
            fake_client,
            monkeypatch,
        )
    assert code == 0
    assert out["dry_run"] is True
    assert m.call_args.kwargs["submit"] is False
    assert m.call_args.args[1] == cfg


def test_jobs_create_deploy_submit(
    fake_client: MagicMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = tmp_path / "deploy.yaml"
    cfg.write_text("name: svc\n", encoding="utf-8")
    with patch.object(cli.jobs_api, "create_deploy_from_config", return_value={"code": 0}) as m:
        code, _ = _run(
            ["jobs", "create-deploy", "--config", str(cfg), "--version", "v3", "--submit"],
            fake_client,
            monkeypatch,
        )
    assert code == 0
    assert m.call_args.kwargs["submit"] is True
    assert m.call_args.kwargs["version"] == "v3"


# ---- devenv ----


def test_devenv_list(fake_client: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    with patch.object(cli.devenv_api, "list_devenv", return_value={"data": []}) as m:
        code, _ = _run(["devenv", "list"], fake_client, monkeypatch)
    assert code == 0
    m.assert_called_once()


def test_devenv_detail(fake_client: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    with patch.object(cli.devenv_api, "get_devenv", return_value={"data": {}}) as m:
        code, _ = _run(["devenv", "detail", "--job-id", "jb-1"], fake_client, monkeypatch)
    assert code == 0
    m.assert_called_once_with(fake_client, "jb-1", biz_type=None)


def test_devenv_create_dry_run(
    fake_client: MagicMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = tmp_path / "devenv.yaml"
    cfg.write_text("name: env1\n", encoding="utf-8")
    body = {"name": "env1"}
    dry = {"dry_run": True, "body": body}
    with (
        patch.object(cli.devenv_api, "load_devenv_config", return_value={"name": "env1"}) as load_m,
        patch.object(cli.devenv_api, "build_create_body", return_value=body) as build_m,
        patch.object(cli.devenv_api, "create_devenv", return_value=dry) as create_m,
    ):
        code, out = _run(["devenv", "create", "--config", str(cfg)], fake_client, monkeypatch)
    assert code == 0
    assert out["dry_run"] is True
    load_m.assert_called_once()
    build_m.assert_called_once()
    assert create_m.call_args.kwargs["submit"] is False


def test_devenv_restart_and_save_image(
    fake_client: MagicMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cfg = tmp_path / "devenv.yaml"
    cfg.write_text("name: env1\nuuid: u1\n", encoding="utf-8")
    with (
        patch.object(cli.devenv_api, "load_devenv_config", return_value={"name": "env1", "uuid": "u1"}),
        patch.object(cli.devenv_api, "build_create_body", return_value={"uuid": "u1", "name": "env1"}),
        patch.object(cli.devenv_api, "restart_devenv", return_value={"dry_run": True}) as restart_m,
    ):
        code, _ = _run(["devenv", "restart", "--config", str(cfg)], fake_client, monkeypatch)
    assert code == 0
    assert restart_m.call_args.kwargs["submit"] is False

    with patch.object(cli.devenv_api, "save_image", return_value={"code": 0}) as save_m:
        code, _ = _run(
            [
                "devenv",
                "save-image",
                "--job-id",
                "jb-1",
                "--repository",
                "repo/a",
                "--tag",
                "v1",
                "--submit",
            ],
            fake_client,
            monkeypatch,
        )
    assert code == 0
    assert save_m.call_args.kwargs["submit"] is True


# ---- pods / logs ----


def test_pods_list_v2_v3(fake_client: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    with patch.object(cli.pods_api, "list_pods_v2", return_value={"v": 2}) as v2:
        code, out = _run(
            ["pods", "list", "--job-id", "j1", "--version", "v2"],
            fake_client,
            monkeypatch,
        )
    assert code == 0
    assert out["v"] == 2
    v2.assert_called_once()

    with patch.object(cli.pods_api, "list_pods_v3", return_value={"v": 3}) as v3:
        code, out = _run(
            ["pods", "list", "--job-id", "j1", "--version", "v3", "--run", "2"],
            fake_client,
            monkeypatch,
        )
    assert code == 0
    assert out["v"] == 3
    assert v3.call_args.kwargs["run"] == 2


def test_pods_monitor_snapshot_and_running(
    fake_client: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    with patch.object(cli.pods_api, "get_job_monitor", return_value={"snap": 1}) as snap:
        code, out = _run(["pods", "monitor", "--job-id", "j1"], fake_client, monkeypatch)
    assert code == 0
    assert out["snap"] == 1
    snap.assert_called_once()

    with patch.object(cli.pods_api, "get_running_monitor", return_value={"ts": 1}) as run_m:
        code, out = _run(
            [
                "pods",
                "monitor",
                "--job-id",
                "j1",
                "--pod-names",
                "p0,p1",
                "--start",
                "1",
                "--end",
                "2",
            ],
            fake_client,
            monkeypatch,
        )
    assert code == 0
    assert out["ts"] == 1
    run_m.assert_called_once()


def test_logs_get_and_download(
    fake_client: MagicMock, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    with patch.object(cli.logs_api, "get_log_info", return_value={"logs": []}) as get_m:
        code, _ = _run(
            [
                "--cluster",
                "x10000",
                "logs",
                "get",
                "--job-id",
                "j1",
                "--pod-names",
                "pod-0",
            ],
            fake_client,
            monkeypatch,
        )
    assert code == 0
    assert get_m.call_args.kwargs["cluster"] == "x10000"

    out_path = tmp_path / "a.log"
    with patch.object(cli.logs_api, "download_log", return_value=b"abc") as dl:
        code, out = _run(
            [
                "logs",
                "download",
                "--job-id",
                "j1",
                "--pod-names",
                "pod-0",
                "--output",
                str(out_path),
            ],
            fake_client,
            monkeypatch,
        )
    assert code == 0
    assert out["size"] == 3
    assert out["written"] == str(out_path)
    assert dl.call_args.kwargs["dest_path"] == out_path


# ---- resources / algorithms / images ----


def test_resources_commands(fake_client: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    with patch.object(cli.resources_api, "list_specs", return_value={"specs": 1}) as m:
        code, out = _run(["resources", "specs"], fake_client, monkeypatch)
    assert code == 0 and out["specs"] == 1
    m.assert_called_once()

    with patch.object(cli.resources_api, "list_projects", return_value={"projects": 1}) as m:
        code, _ = _run(["resources", "projects"], fake_client, monkeypatch)
    assert code == 0
    m.assert_called_once()

    with patch.object(cli.resources_api, "list_sub_projects", return_value={"sub": 1}) as m:
        code, _ = _run(
            ["resources", "sub-projects", "--project-id", "pr-1"],
            fake_client,
            monkeypatch,
        )
    assert code == 0
    m.assert_called_once_with(fake_client, "pr-1")


def test_algorithms_and_images(fake_client: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
    with patch.object(cli.algorithms_api, "list_algorithms", return_value={"a": 1}) as m:
        code, _ = _run(
            ["algorithms", "list", "--is-public", "false"],
            fake_client,
            monkeypatch,
        )
    assert code == 0
    assert m.call_args.kwargs["is_public"] is False

    with patch.object(cli.algorithms_api, "get_algorithm", return_value={"a": 2}) as m:
        code, _ = _run(
            ["algorithms", "get", "--uuid", "u1", "--is-public", "true"],
            fake_client,
            monkeypatch,
        )
    assert code == 0
    assert m.call_args.kwargs["is_public"] is True

    with patch.object(cli.images_api, "list_images", return_value={"i": 1}) as m:
        code, _ = _run(["images", "list", "--is-public", "false"], fake_client, monkeypatch)
    assert code == 0
    assert m.call_args.kwargs["is_public"] is False

    with patch.object(cli.images_api, "list_image_tags", return_value={"t": 1}) as m:
        code, _ = _run(
            [
                "images",
                "tags",
                "--repository-name",
                "repo/a",
                "--source",
                "private",
            ],
            fake_client,
            monkeypatch,
        )
    assert code == 0
    assert m.call_args.kwargs["repository_name"] == "repo/a"
    assert m.call_args.kwargs["source"] == "private"


def test_config_error_returns_json(monkeypatch: pytest.MonkeyPatch) -> None:
    from nanhu.config import ConfigError

    captured: dict = {}
    monkeypatch.setattr(cli, "_print_json", lambda payload: captured.update(payload=payload))
    with patch.object(cli, "_build_client", side_effect=ConfigError("missing NANHU_APP_KEY")):
        code = cli.main(["jobs", "list", "--job-type", "AI_TRAIN"])
    assert code == 1
    assert captured["payload"]["type"] == "ConfigError"
    assert "NANHU_APP_KEY" in captured["payload"]["error"]


def test_build_parser_help() -> None:
    parser = cli.build_parser()
    help_text = parser.format_help()
    assert "jobs" in help_text
    assert "devenv" in help_text


def test_main_prints_real_json(capsys: pytest.CaptureFixture[str], fake_client: MagicMock) -> None:
    with (
        patch.object(cli, "_build_client", return_value=fake_client),
        patch.object(cli.jobs_api, "list_jobs_all", return_value={"ok": True}),
    ):
        code = cli.main(["jobs", "list-all"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data == {"ok": True}
