"""Storage mount ``path`` normalization for train / deploy payloads.

Regression test for the platform UI bug where ``mountedStorages[].path = "/"``
caused the console to render the storage row as ``ossName/bucket//`` and the
mount-path column as ``挂载路径: /`` instead of the configured
``outputPath`` (e.g. ``/mnt/zj-data/data``).

The OpenAPI spec marks ``path`` as optional; omitting it means "mount the
whole bucket". The builder therefore strips trailing slashes / whitespace and
drops the field entirely when the resulting path is empty so the platform UI
shows the desired mount path.
"""

from __future__ import annotations

import copy

from nanhu.api.jobs import (
    _normalize_bucket_path,
    build_deploy_payload,
    build_train_payload,
)


_BASE_CFG: dict = {
    "biz_type": "DROS",
    "job_type": "AI_TRAIN",
    "algorithm": {
        "uuid": "algo-uuid",
        "name": "algo-name",
        "mount_path": "/mnt/algo",
    },
    "start_cmd": "python train.py",
    "resource": {
        "project_uuid": "pr-1",
        "sub_mission_name": "mission-a",
        "compute_spec_uuid": "spec-1",
        "compute_spec_name": "GPU-8",
        "worker_num": 1,
    },
    "env_vars": {"OUTPUT_DIR": "/mnt/data/out"},
}


def _cfg_with_storage(storage: dict, output_dir: dict | None = None) -> dict:
    cfg = copy.deepcopy(_BASE_CFG)
    cfg["mounted_storages"] = [storage]
    if output_dir is not None:
        cfg["output_dir"] = output_dir
    else:
        cfg["output_dir"] = {
            "uuid": storage["uuid"],
            "bucket": storage["bucket"],
            "path": "out/run",
            "output_path": "/mnt/data/out/run",
        }
    return cfg


# ---------------------------------------------------------------------------
# Pure helper
# ---------------------------------------------------------------------------


def test_normalize_bucket_path_root_variants() -> None:
    """`/`, ``""``, ``None``, whitespace-only → ``None`` (drop the field)."""
    for value in ("/", "//", "///", "", "   ", None):
        assert _normalize_bucket_path(value) is None, value


def test_normalize_bucket_path_real_subdirs() -> None:
    """Non-root paths keep their content but lose trailing slashes."""
    assert _normalize_bucket_path("/foo") == "/foo"
    assert _normalize_bucket_path("/foo/") == "/foo"
    assert _normalize_bucket_path("/foo/bar/") == "/foo/bar"
    assert _normalize_bucket_path("  /foo  ") == "/foo"
    # Non-strings like bool should not leak through as "True".
    assert _normalize_bucket_path(True) is None
    assert _normalize_bucket_path(False) is None


# ---------------------------------------------------------------------------
# Train payload
# ---------------------------------------------------------------------------


def test_train_payload_drops_root_path_in_storage() -> None:
    cfg = _cfg_with_storage(
        {
            "uuid": "oss-1",
            "oss_name": "zj-data",
            "bucket": "data",
            "path": "/",
            "output_path": "/mnt/zj-data/data",
        }
    )
    body = build_train_payload(cfg, name="job-root")
    item = body["mountedStorages"][0]
    assert item["ossName"] == "zj-data"
    assert item["bucket"] == "data"
    assert item["outputPath"] == "/mnt/zj-data/data"
    # ``path`` must NOT be present when the user meant "mount the whole bucket".
    assert "path" not in item, item


def test_train_payload_keeps_real_subpath() -> None:
    cfg = _cfg_with_storage(
        {
            "uuid": "oss-1",
            "oss_name": "zj-data",
            "bucket": "models",
            "path": "/llm/qwen",
            "output_path": "/mnt/zj-data/models/llm/qwen",
        }
    )
    body = build_train_payload(cfg, name="job-sub")
    item = body["mountedStorages"][0]
    assert item["path"] == "/llm/qwen"
    assert item["outputPath"] == "/mnt/zj-data/models/llm/qwen"


def test_train_payload_strips_trailing_slash_on_subpath() -> None:
    cfg = _cfg_with_storage(
        {
            "uuid": "oss-1",
            "oss_name": "zj-data",
            "bucket": "models",
            "path": "/llm/qwen/",
            "output_path": "/mnt/zj-data/models/llm/qwen",
        }
    )
    body = build_train_payload(cfg, name="job-sub-trailing")
    assert body["mountedStorages"][0]["path"] == "/llm/qwen"


def test_train_payload_output_dir_normalizes_root() -> None:
    cfg = _cfg_with_storage(
        {
            "uuid": "oss-1",
            "oss_name": "zj-data",
            "bucket": "data",
            "output_path": "/mnt/zj-data/data",
        },
        output_dir={
            "uuid": "oss-1",
            "bucket": "data",
            "path": "/",
            "output_path": "/mnt/zj-data/data",
        },
    )
    body = build_train_payload(cfg, name="job-out-root")
    # ``/`` is "mount the whole bucket" so we don't send it again.
    assert "path" not in body["outputDir"]


def test_train_payload_output_dir_keeps_subpath() -> None:
    cfg = _cfg_with_storage(
        {
            "uuid": "oss-1",
            "oss_name": "zj-data",
            "bucket": "data",
            "output_path": "/mnt/zj-data/data",
        },
        output_dir={
            "uuid": "oss-1",
            "bucket": "data",
            "path": "songquanheng/output/slime/run",
            "output_path": "/mnt/zj-data/data/songquanheng/output/slime/run",
        },
    )
    body = build_train_payload(cfg, name="job-out-sub")
    assert body["outputDir"]["path"] == "songquanheng/output/slime/run"


# ---------------------------------------------------------------------------
# Deploy payload
# ---------------------------------------------------------------------------


def test_deploy_payload_drops_root_storage_path() -> None:
    cfg = copy.deepcopy(_BASE_CFG)
    cfg["mounted_storages"] = [
        {
            "uuid": "oss-1",
            "oss_name": "zj-data",
            "bucket": "data",
            "path": "/",
            "output_path": "/mnt/zj-data/data",
        }
    ]
    cfg["model_dir"] = {"uuid": "oss-1", "bucket": "data", "path": "/"}
    body = build_deploy_payload(cfg, name="deploy-root")
    assert "path" not in body["mountedStorages"][0]
    assert "path" not in body["modelDir"]
