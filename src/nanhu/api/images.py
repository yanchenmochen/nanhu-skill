"""镜像只读：镜像列表与版本列表。"""

from __future__ import annotations

from typing import Any

from nanhu.client import NanhuClient

IMAGES_PATH = "/api/open/dros-ic-platform/open-job/images"
IMAGE_TAGS_PATH = "/api/open/dros-ic-platform/open-job/images/tags"


def _bool_query(value: bool | str) -> str:
    """Normalize isPublic for Nanhu query string (expects lowercase true/false)."""
    if isinstance(value, str):
        return value.lower()
    return "true" if value else "false"


def list_images(
    client: NanhuClient,
    *,
    is_public: bool | str,
    current: int = 1,
    page_size: int = 10,
    user_id: str | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    """获取镜像列表（GET .../open-job/images）。

    ``is_public=False`` 为我创建的仓库；``True`` 为共享给我的（含公开）。
    """
    query: dict[str, Any] = {
        "userId": user_id or client.user_id,
        "isPublic": _bool_query(is_public),
        "current": current,
        "pageSize": page_size,
    }
    if name is not None:
        query["name"] = name
    return client.request("GET", IMAGES_PATH, query=query)


def list_image_tags(
    client: NanhuClient,
    *,
    repository_name: str,
    source: str,
    current: int = 1,
    page_size: int = 100,
    user_id: str | None = None,
) -> dict[str, Any]:
    """获取镜像版本列表（GET .../open-job/images/tags）。

    ``repository_name`` / ``source`` 来自 ``list_images`` 返回的 ``name`` / ``source``。
    """
    query: dict[str, Any] = {
        "userId": user_id or client.user_id,
        "repositoryName": repository_name,
        "source": source,
        "current": current,
        "pageSize": page_size,
    }
    return client.request("GET", IMAGE_TAGS_PATH, query=query)
