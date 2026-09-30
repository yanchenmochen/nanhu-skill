"""V2 开发环境（JUPYTER）OpenAPI：创建 / 列表 / 详情 / 变配重启 / 保存镜像。

写操作（create / restart / save_image）默认 dry-run；``submit=True`` 才真正请求。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from nanhu.client import NanhuClient

JOB_TYPE_JUPYTER = "JUPYTER"

PATH_CREATE = "/api/open/dros-ic-platform/open-job/dev-env/create"
PATH_LIST = "/api/open/dros-ic-platform/open-job/dev-env/list"
PATH_DETAIL = "/api/open/dros-ic-platform/open-job/dev-env/detail"
PATH_RESTART = "/api/open/dros-ic-platform/open-job/dev-env/restart"
PATH_SAVE_IMAGE = "/api/open/dros-ic-platform/open-job/dev-env/saveImage"

_CREATE_REQUIRED = (
    "name",
    "imageUrl",
    "sshPwd",
    "vscodePassword",
    "resource",
    "mountedStorages",
)
_RESOURCE_REQUIRED = (
    "projectUuid",
    "subMissionName",
    "computeSpecUuid",
    "computeSpecName",
    "workerNum",
)


def _dry_run_result(
    method: str,
    path: str,
    *,
    query: dict[str, Any],
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "dry_run": True,
        "method": method.upper(),
        "path": path,
        "query": dict(query),
    }
    if body is not None:
        out["body"] = body
    return out


def _user_query(
    client: NanhuClient,
    *,
    extra: dict[str, Any] | None = None,
    user_extra_info: str | None = None,
) -> dict[str, Any]:
    query: dict[str, Any] = {"userId": client.user_id}
    if user_extra_info is not None:
        query["userExtraInfo"] = user_extra_info
    if extra:
        for key, value in extra.items():
            if value is not None:
                query[key] = value
    return query


def list_devenv(
    client: NanhuClient,
    *,
    status: str | None = None,
    project_id: str | None = None,
    current: int | None = 1,
    page_size: int | None = 100,
    biz_type: str | None = None,
) -> dict[str, Any]:
    """GET 开发环境列表（jobType 固定为 JUPYTER）。"""
    query = _user_query(
        client,
        extra={
            "jobType": JOB_TYPE_JUPYTER,
            "status": status,
            "projectId": project_id,
            "current": current,
            "pageSize": page_size,
            "bizType": biz_type,
        },
    )
    return client.request("GET", PATH_LIST, query=query)


def get_devenv(
    client: NanhuClient,
    job_id: str,
    *,
    biz_type: str | None = None,
) -> dict[str, Any]:
    """GET 开发环境详情。"""
    if not job_id:
        raise ValueError("job_id is required")
    query = _user_query(
        client,
        extra={
            "jobId": job_id,
            "jobType": JOB_TYPE_JUPYTER,
            "bizType": biz_type,
        },
    )
    return client.request("GET", PATH_DETAIL, query=query)


def create_devenv(
    client: NanhuClient,
    body: dict[str, Any],
    *,
    submit: bool = False,
    user_extra_info: str | None = None,
) -> dict[str, Any]:
    """POST 创建开发环境；默认 dry-run。"""
    payload = dict(body)
    _validate_create_body(payload)
    query = _user_query(client, user_extra_info=user_extra_info)
    if not submit:
        return _dry_run_result("POST", PATH_CREATE, query=query, body=payload)
    return client.request("POST", PATH_CREATE, query=query, body=payload)


def restart_devenv(
    client: NanhuClient,
    body: dict[str, Any],
    *,
    submit: bool = False,
    user_extra_info: str | None = None,
) -> dict[str, Any]:
    """POST 变配重启开发环境；默认 dry-run。

    ``body`` 与创建参数相同，且必须包含 ``uuid``（待重启开发环境 UUID）。
    """
    payload = dict(body)
    if not payload.get("uuid"):
        raise ValueError("restart body requires uuid")
    _validate_create_body(payload, require_uuid=False)
    query = _user_query(client, user_extra_info=user_extra_info)
    if not submit:
        return _dry_run_result("POST", PATH_RESTART, query=query, body=payload)
    return client.request("POST", PATH_RESTART, query=query, body=payload)


def save_image(
    client: NanhuClient,
    job_id: str,
    *,
    repository: str,
    tag: str,
    submit: bool = False,
) -> dict[str, Any]:
    """POST 开发环境保存镜像；默认 dry-run。"""
    if not job_id:
        raise ValueError("job_id is required")
    if not repository or not tag:
        raise ValueError("repository and tag are required")
    query = _user_query(client, extra={"jobId": job_id})
    body = {"repository": repository, "tag": tag}
    if not submit:
        return _dry_run_result("POST", PATH_SAVE_IMAGE, query=query, body=body)
    return client.request("POST", PATH_SAVE_IMAGE, query=query, body=body)


def load_devenv_config(path: str | Path) -> dict[str, Any]:
    """Load a YAML config file for create / restart payloads."""
    text = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"devenv config must be a mapping: {path}")
    return data


def build_create_body(config: dict[str, Any], *, uuid: str | None = None) -> dict[str, Any]:
    """Map snake_case / camelCase YAML into OpenAPI create/restart body.

    When ``uuid`` is set (or present in ``config``), it is included for restart.
    """
    cfg = dict(config)
    body: dict[str, Any] = {
        "name": _pick(cfg, "name"),
        "imageUrl": _pick(cfg, "imageUrl", "image_url"),
        "sshPwd": _pick(cfg, "sshPwd", "ssh_pwd"),
        "vscodePassword": _pick(cfg, "vscodePassword", "vscode_password"),
        "resource": _map_resource(_pick(cfg, "resource") or {}),
        "mountedStorages": [
            _map_storage(item) for item in (_pick(cfg, "mountedStorages", "mounted_storages") or [])
        ],
    }
    data_sets = _pick(cfg, "dataSets", "data_sets")
    if data_sets is not None:
        body["dataSets"] = [_map_dataset(item) for item in data_sets]
    seahold = _pick(cfg, "seaholdDataSets", "seahold_data_sets")
    if seahold is not None:
        body["seaholdDataSets"] = [_map_seahold(item) for item in seahold]
    ports = _pick(cfg, "customizePorts", "customize_ports")
    if ports is not None:
        body["customizePorts"] = list(ports)
    start_cmd = _pick(cfg, "startCmd", "start_cmd")
    if start_cmd is not None:
        body["startCmd"] = start_cmd
    env_vars = _pick(cfg, "envVars", "env_vars")
    if env_vars is not None:
        body["envVars"] = _map_env_vars(env_vars)

    env_uuid = uuid if uuid is not None else _pick(cfg, "uuid")
    if env_uuid:
        body["uuid"] = env_uuid
    # Drop keys that were never set (None from missing required fields stays
    # so validation can report them).
    return {k: v for k, v in body.items() if v is not None or k in _CREATE_REQUIRED}


def _validate_create_body(body: dict[str, Any], *, require_uuid: bool = False) -> None:
    missing = [k for k in _CREATE_REQUIRED if body.get(k) in (None, "", [])]
    if require_uuid and not body.get("uuid"):
        missing.append("uuid")
    if missing:
        raise ValueError(f"missing required devenv fields: {', '.join(missing)}")
    resource = body.get("resource")
    if not isinstance(resource, dict):
        raise ValueError("resource must be an object")
    res_missing = [k for k in _RESOURCE_REQUIRED if resource.get(k) in (None, "")]
    if res_missing:
        raise ValueError(f"missing required resource fields: {', '.join(res_missing)}")


def _pick(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return None


def _map_resource(raw: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "projectUuid": _pick(raw, "projectUuid", "project_uuid"),
        "subMissionName": _pick(raw, "subMissionName", "sub_mission_name"),
        "computeSpecUuid": _pick(raw, "computeSpecUuid", "compute_spec_uuid"),
        "computeSpecName": _pick(raw, "computeSpecName", "compute_spec_name"),
        "workerNum": _pick(raw, "workerNum", "worker_num"),
    }
    sub_id = _pick(raw, "subQuotaId", "sub_quota_id")
    if sub_id is not None:
        out["subQuotaId"] = sub_id
    sub_name = _pick(raw, "subQuotaName", "sub_quota_name")
    if sub_name is not None:
        out["subQuotaName"] = sub_name
    return out


def _map_storage(raw: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "uuid": _pick(raw, "uuid"),
        "ossName": _pick(raw, "ossName", "oss_name"),
        "bucket": _pick(raw, "bucket"),
    }
    path = _pick(raw, "path")
    if path is not None:
        out["path"] = path
    output_path = _pick(raw, "outputPath", "output_path")
    if output_path is not None:
        out["outputPath"] = output_path
    return out


def _map_dataset(raw: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "name": _pick(raw, "name"),
        "uuid": _pick(raw, "uuid"),
        "path": _pick(raw, "path"),
        "isPublic": _pick(raw, "isPublic", "is_public"),
    }
    version = _pick(raw, "version")
    if version is not None:
        out["version"] = version
    return out


def _map_seahold(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "uuid": _pick(raw, "uuid"),
        "name": _pick(raw, "name"),
        "ak": _pick(raw, "ak"),
        "sk": _pick(raw, "sk"),
        "path": _pick(raw, "path"),
    }


def _map_env_vars(raw: Any) -> list[dict[str, str]]:
    if isinstance(raw, dict):
        return [{"key": str(k), "value": str(v)} for k, v in raw.items()]
    if isinstance(raw, list):
        out: list[dict[str, str]] = []
        for item in raw:
            if not isinstance(item, dict):
                raise ValueError("envVars list items must be objects with key/value")
            key = _pick(item, "key")
            value = _pick(item, "value")
            if key is None or value is None:
                raise ValueError("envVars items require key and value")
            out.append({"key": str(key), "value": str(value)})
        return out
    raise ValueError("envVars must be a dict or list of {key, value}")
