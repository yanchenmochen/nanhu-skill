"""算法库只读：列表与详情。"""

from __future__ import annotations

from typing import Any

from nanhu.client import NanhuClient

ALGORITHMS_PATH = "/api/open/dros-ic-platform/open-job/algorithms"


def _bool_query(value: bool | str) -> str:
    """Normalize isPublic for Nanhu query string (expects lowercase true/false)."""
    if isinstance(value, str):
        return value.lower()
    return "true" if value else "false"


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
