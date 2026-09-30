"""镜像：列表/版本 + 共享人增删（写操作默认 dry-run）。"""

from __future__ import annotations

from typing import Any

from nanhu.client import NanhuClient

IMAGES_PATH = "/api/open/dros-ic-platform/open-job/images"
IMAGE_TAGS_PATH = "/api/open/dros-ic-platform/open-job/images/tags"
IMAGE_SHARE_PATH = "/api/open/dros-ic-platform/open-job/images/share"


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


def share_image(
    client: NanhuClient,
    *,
    uuid: str,
    source: str,
    user_name: str,
    submit: bool = False,
) -> dict[str, Any]:
    """POST 添加镜像共享人（``.../images/share``）。Dry-run unless ``submit=True``."""
    query = {"userId": client.user_id}
    body = {"uuid": uuid, "source": source, "userName": user_name}
    if not submit:
        return _dry_run("POST", IMAGE_SHARE_PATH, query=query, body=body)
    return client.request("POST", IMAGE_SHARE_PATH, query=query, body=body)


def unshare_image(
    client: NanhuClient,
    *,
    uuid: str,
    source: str,
    user_names: str | list[str],
    submit: bool = False,
) -> dict[str, Any]:
    """DELETE 删除镜像共享人。Dry-run unless ``submit=True``.

    Body uses ``userNameList`` (array); CLI may pass comma-separated names.
    """
    if isinstance(user_names, str):
        names = [n.strip() for n in user_names.split(",") if n.strip()]
    else:
        names = [str(n) for n in user_names]
    query = {"userId": client.user_id}
    body = {"uuid": uuid, "source": source, "userNameList": names}
    if not submit:
        return _dry_run("DELETE", IMAGE_SHARE_PATH, query=query, body=body)
    return client.request("DELETE", IMAGE_SHARE_PATH, query=query, body=body)
