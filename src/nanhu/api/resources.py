"""计算资源查询：规格 / 项目 / 可用子项目。"""

from __future__ import annotations

from typing import Any

from nanhu.client import NanhuClient

SPECS_PATH = "/api/open/dros-ic-platform/open-job/specs"
PROJECTS_PATH = "/api/open/resource-proxy/subMission/open-job/projects"
SUB_PROJECTS_PATH = "/api/open/resource-proxy/subMission/open-job/subProjects"
PROMOTIONS_PATH = "/api/open/resource-proxy/subMission/open-job/promotion/list"


def list_specs(
    client: NanhuClient,
    *,
    user_id: str | None = None,
    resource_type: str | None = None,
    current: int | None = None,
    page_size: int | None = None,
) -> dict[str, Any]:
    """查询计算规格（GET .../open-job/specs）。

    ``resource_type`` 可选；未传时由服务端按当前集群 URL 返回可见规格。
    """
    query: dict[str, Any] = {"userId": user_id or client.user_id}
    if resource_type is not None:
        query["resourceType"] = resource_type
    if current is not None:
        query["current"] = current
    if page_size is not None:
        query["pageSize"] = page_size
    return client.request("GET", SPECS_PATH, query=query)


def list_projects(
    client: NanhuClient,
    *,
    user_id: str | None = None,
    resource_type: str | None = None,
    current: int | None = None,
    page_size: int | None = None,
) -> dict[str, Any]:
    """查询项目（GET .../open-job/projects）。

    ``resource_type`` 可选；未传时返回当前集群下未过期且卡时>0 的可用项目。
    """
    query: dict[str, Any] = {"userId": user_id or client.user_id}
    if resource_type is not None:
        query["resourceType"] = resource_type
    if current is not None:
        query["current"] = current
    if page_size is not None:
        query["pageSize"] = page_size
    return client.request("GET", PROJECTS_PATH, query=query)


def list_sub_projects(
    client: NanhuClient,
    project_id: str,
    *,
    user_id: str | None = None,
) -> dict[str, Any]:
    """查询可用子项目（GET .../open-job/subProjects）。

    通常在 ``list_projects`` 返回项 ``hasAvailableSubQuotas=true`` 时调用。
    """
    query: dict[str, Any] = {
        "userId": user_id or client.user_id,
        "projectId": project_id,
    }
    return client.request("GET", SUB_PROJECTS_PATH, query=query)


def list_promotions(
    client: NanhuClient,
    project_id: str,
    *,
    user_id: str | None = None,
) -> dict[str, Any]:
    """查询项目弹性填充价格（GET .../open-job/promotion/list）。"""
    query: dict[str, Any] = {
        "userId": user_id or client.user_id,
        "projectId": project_id,
    }
    return client.request("GET", PROMOTIONS_PATH, query=query)
