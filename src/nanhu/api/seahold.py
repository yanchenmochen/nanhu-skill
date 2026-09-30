"""海纳私有数据集 PVC：list / create / destroy（写操作默认 dry-run）。

仅限 Zero2X 等支持该接口的平台；部分集群可能 404。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from nanhu.client import NanhuClient

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML required: pip install pyyaml") from exc

PATH_LIST = "/api/open/dros-ic-platform/open-job/seahold-dataset/list"
PATH_CREATE = "/api/open/dros-ic-platform/open-job/seahold-dataset/create"
PATH_DESTROY = "/api/open/dros-ic-platform/open-job/seahold-dataset/destroy"


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


def _user_query(client: NanhuClient) -> dict[str, Any]:
    return {"userId": client.user_id}


def list_seahold(
    client: NanhuClient,
    *,
    uuid: str | None = None,
    ak: str | None = None,
    status: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
) -> dict[str, Any]:
    """查询已创建海纳私有数据集列表（POST .../seahold-dataset/list）。"""
    body: dict[str, Any] = {}
    if uuid is not None:
        body["uuid"] = uuid
    if ak is not None:
        body["ak"] = ak
    if status is not None:
        body["status"] = status
    if page is not None:
        body["page"] = page
    if page_size is not None:
        body["pageSize"] = page_size
    return client.request("POST", PATH_LIST, query=_user_query(client), body=body or None)


def create_seahold(
    client: NanhuClient,
    body: dict[str, Any],
    *,
    submit: bool = False,
) -> dict[str, Any]:
    """POST 创建海纳私有数据集 PVC。Dry-run unless ``submit=True``.

    Body must include ``seaholdDataSets`` (1–5 items with uuid/name/ak/sk).
    """
    if "seaholdDataSets" not in body:
        raise ValueError("create body requires seaholdDataSets")
    query = _user_query(client)
    if not submit:
        return _dry_run("POST", PATH_CREATE, query=query, body=body)
    return client.request("POST", PATH_CREATE, query=query, body=body)


def destroy_seahold(
    client: NanhuClient,
    *,
    uuid: str,
    ak: str,
    sk: str,
    submit: bool = False,
) -> dict[str, Any]:
    """POST 销毁海纳私有数据集 PVC。Dry-run unless ``submit=True``."""
    query = _user_query(client)
    body = {"uuid": uuid, "ak": ak, "sk": sk}
    if not submit:
        return _dry_run("POST", PATH_DESTROY, query=query, body=body)
    return client.request("POST", PATH_DESTROY, query=query, body=body)


def load_seahold_config(path: str | Path) -> dict[str, Any]:
    """Load YAML/JSON for create payload."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() in {".yaml", ".yml"}:
        data = yaml.safe_load(text) or {}
    else:
        import json

        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"seahold config must be a mapping, got {type(data).__name__}")
    return data


def build_create_body(cfg: dict[str, Any]) -> dict[str, Any]:
    """Normalize config into OpenAPI create body."""
    if "seaholdDataSets" in cfg:
        return {"seaholdDataSets": list(cfg["seaholdDataSets"])}

    items = cfg.get("seahold_data_sets") or cfg.get("datasets")
    if items is None and all(k in cfg for k in ("uuid", "name", "ak", "sk")):
        items = [cfg]

    if not items:
        raise ValueError("config requires seaholdDataSets or seahold_data_sets / single dataset fields")

    out: list[dict[str, Any]] = []
    for item in items:
        out.append(
            {
                "uuid": item["uuid"],
                "name": item["name"],
                "ak": item["ak"],
                "sk": item["sk"],
            }
        )
    return {"seaholdDataSets": out}


def create_seahold_from_config(
    client: NanhuClient,
    cfg: dict[str, Any] | str | Path,
    *,
    submit: bool = False,
) -> dict[str, Any]:
    if isinstance(cfg, (str, Path)):
        cfg = load_seahold_config(cfg)
    return create_seahold(client, build_create_body(cfg), submit=submit)
