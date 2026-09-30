"""算法库：列表/详情 + 创建/更新/删除/公开/共享（写操作默认 dry-run）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nanhu.client import NanhuClient

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML required: pip install pyyaml") from exc

ALGORITHMS_PATH = "/api/open/dros-ic-platform/open-job/algorithms"

_FRIENDLY_META_KEYS = frozenset({"api_base", "user_id", "biz_type", "name_prefix"})


def _bool_query(value: bool | str) -> str:
    """Normalize isPublic for Nanhu query string (expects lowercase true/false)."""
    if isinstance(value, str):
        return value.lower()
    return "true" if value else "false"


def _dry_run(
    method: str,
    path: str,
    *,
    query: dict[str, Any],
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "dry_run": True,
        "method": method.upper(),
        "path": path,
        "query": query,
        "body": body,
    }


def _user_query(client: NanhuClient, **extra: Any) -> dict[str, Any]:
    q: dict[str, Any] = {"userId": client.user_id}
    for k, v in extra.items():
        if v is not None:
            q[k] = v
    return q


def list_algorithms(
    client: NanhuClient,
    *,
    is_public: bool | str,
    current: int = 1,
    page_size: int = 10,
    user_id: str | None = None,
    order_by: str | None = None,
    descend: int | None = None,
    uuid: str | None = None,
    name: str | None = None,
    supported_cluster_ids: str | None = None,
    creator: str | None = None,
    creator_name: str | None = None,
) -> dict[str, Any]:
    """获取算法列表（GET .../open-job/algorithms）。

    ``is_public=False`` 为我创建的；``True`` 为共享给我的（含公开）。
    """
    query: dict[str, Any] = {
        "userId": user_id or client.user_id,
        "current": current,
        "pageSize": page_size,
        "isPublic": _bool_query(is_public),
    }
    if order_by is not None:
        query["orderBy"] = order_by
    if descend is not None:
        query["descend"] = descend
    if uuid is not None:
        query["uuid"] = uuid
    if name is not None:
        query["name"] = name
    if supported_cluster_ids is not None:
        query["supportedClusterIds"] = supported_cluster_ids
    if creator is not None:
        query["creator"] = creator
    if creator_name is not None:
        query["creatorName"] = creator_name
    return client.request("GET", ALGORITHMS_PATH, query=query)


def get_algorithm(
    client: NanhuClient,
    uuid: str,
    *,
    is_public: bool | str,
    user_id: str | None = None,
) -> dict[str, Any]:
    """获取算法详情（同列表路径，按 uuid + isPublic 查询）。

    查非本人创建的算法时，若 ``is_public`` 不匹配，``data.result`` 可能为空。
    """
    query: dict[str, Any] = {
        "userId": user_id or client.user_id,
        "uuid": uuid,
        "isPublic": _bool_query(is_public),
    }
    return client.request("GET", ALGORITHMS_PATH, query=query)


def load_algorithm_config(path: str | Path) -> dict[str, Any]:
    """Load YAML/JSON algorithm config."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() in {".yaml", ".yml"}:
        data = yaml.safe_load(text) or {}
    else:
        import json

        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"algorithm config must be a mapping, got {type(data).__name__}")
    return data


def build_algorithm_payload(cfg: dict[str, Any]) -> dict[str, Any]:
    """Map friendly or API-shaped config into OpenAPI create/update body."""
    if "algoType" in cfg or "srcType" in cfg or "imageUrl" in cfg:
        return {k: v for k, v in cfg.items() if k not in _FRIENDLY_META_KEYS and k != "uuid"}

    body: dict[str, Any] = {}
    name = cfg.get("name")
    if name is not None:
        body["name"] = name
    if cfg.get("description") is not None:
        body["description"] = cfg["description"]

    algo_type = cfg.get("algo_type") or cfg.get("algoType")
    if algo_type is not None:
        body["algoType"] = algo_type
    src_type = cfg.get("src_type") or cfg.get("srcType")
    if src_type is not None:
        body["srcType"] = src_type
    image_url = cfg.get("image_url") or cfg.get("imageUrl")
    if image_url is not None:
        body["imageUrl"] = image_url

    clusters = cfg.get("supported_cluster_ids") or cfg.get("supportedClusterIds")
    if clusters is not None:
        body["supportedClusterIds"] = list(clusters)

    oss = cfg.get("oss_path") or cfg.get("ossPath")
    if isinstance(oss, dict):
        body["ossPath"] = {
            "uuid": oss["uuid"],
            "bucket": oss["bucket"],
            **({"path": oss["path"]} if oss.get("path") is not None else {}),
        }

    gitlab = cfg.get("gitlab_path") or cfg.get("gitlabPath")
    if isinstance(gitlab, dict):
        gl: dict[str, Any] = {"path": gitlab["path"]}
        if gitlab.get("token") is not None:
            gl["token"] = gitlab["token"]
        if gitlab.get("branch") is not None:
            gl["branch"] = gitlab["branch"]
        body["gitlabPath"] = gl

    return body


def create_algorithm(
    client: NanhuClient,
    body: dict[str, Any],
    *,
    submit: bool = False,
) -> dict[str, Any]:
    """POST 新建算法。Dry-run unless ``submit=True``."""
    query = _user_query(client)
    if not submit:
        return _dry_run("POST", ALGORITHMS_PATH, query=query, body=body)
    return client.request("POST", ALGORITHMS_PATH, query=query, body=body)


def create_algorithm_from_config(
    client: NanhuClient,
    cfg: dict[str, Any] | str | Path,
    *,
    submit: bool = False,
) -> dict[str, Any]:
    if isinstance(cfg, (str, Path)):
        cfg = load_algorithm_config(cfg)
    return create_algorithm(client, build_algorithm_payload(cfg), submit=submit)


def update_algorithm(
    client: NanhuClient,
    uuid: str,
    body: dict[str, Any],
    *,
    submit: bool = False,
) -> dict[str, Any]:
    """PUT 更新算法（``.../algorithms/{uuid}``）。Dry-run unless ``submit=True``."""
    path = f"{ALGORITHMS_PATH}/{uuid}"
    query = _user_query(client)
    if not submit:
        return _dry_run("PUT", path, query=query, body=body)
    return client.request("PUT", path, query=query, body=body)


def update_algorithm_from_config(
    client: NanhuClient,
    cfg: dict[str, Any] | str | Path,
    *,
    uuid: str | None = None,
    submit: bool = False,
) -> dict[str, Any]:
    if isinstance(cfg, (str, Path)):
        cfg = load_algorithm_config(cfg)
    algo_uuid = uuid or cfg.get("uuid")
    if not algo_uuid:
        raise ValueError("update requires uuid= or cfg['uuid']")
    return update_algorithm(
        client, str(algo_uuid), build_algorithm_payload(cfg), submit=submit
    )


def delete_algorithm(
    client: NanhuClient,
    uuid: str,
    *,
    submit: bool = False,
) -> dict[str, Any]:
    """DELETE 删除算法。Dry-run unless ``submit=True``."""
    path = f"{ALGORITHMS_PATH}/{uuid}"
    query = _user_query(client)
    if not submit:
        return _dry_run("DELETE", path, query=query)
    return client.request("DELETE", path, query=query)


def publish_algorithm(
    client: NanhuClient,
    uuid: str,
    *,
    submit: bool = False,
) -> dict[str, Any]:
    """PUT 公开算法（``.../algorithms/{uuid}/share``）。Dry-run unless ``submit=True``."""
    path = f"{ALGORITHMS_PATH}/{uuid}/share"
    query = _user_query(client)
    if not submit:
        return _dry_run("PUT", path, query=query)
    return client.request("PUT", path, query=query)


def unpublish_algorithm(
    client: NanhuClient,
    uuid: str,
    *,
    submit: bool = False,
) -> dict[str, Any]:
    """PUT 取消公开（``.../algorithms/{uuid}/stop-share``）。Dry-run unless ``submit=True``."""
    path = f"{ALGORITHMS_PATH}/{uuid}/stop-share"
    query = _user_query(client)
    if not submit:
        return _dry_run("PUT", path, query=query)
    return client.request("PUT", path, query=query)


def share_algorithm(
    client: NanhuClient,
    uuid: str,
    user_name: str,
    *,
    submit: bool = False,
) -> dict[str, Any]:
    """POST 添加算法共享人。Dry-run unless ``submit=True``."""
    path = f"{ALGORITHMS_PATH}/{uuid}/share"
    query = _user_query(client)
    body = {"userName": user_name}
    if not submit:
        return _dry_run("POST", path, query=query, body=body)
    return client.request("POST", path, query=query, body=body)


def unshare_algorithm(
    client: NanhuClient,
    uuid: str,
    user_names: str | list[str],
    *,
    submit: bool = False,
) -> dict[str, Any]:
    """DELETE 删除算法共享人（query ``shareList``）。Dry-run unless ``submit=True``."""
    if isinstance(user_names, str):
        names = [n.strip() for n in user_names.split(",") if n.strip()]
    else:
        names = [str(n) for n in user_names]
    path = f"{ALGORITHMS_PATH}/{uuid}/share"
    query = _user_query(client, shareList=names)
    if not submit:
        return _dry_run("DELETE", path, query=query)
    return client.request("DELETE", path, query=query)
