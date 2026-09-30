"""任务 POD 列表（V2 getJobMetrics / V3 getJobMonitor）。"""

from __future__ import annotations

from typing import Any

from nanhu.client import NanhuClient

DEFAULT_BIZ_TYPE = "DROS"

PATH_JOB_METRICS = "/api/open/dros-ic-platform/open-job/getJobMetrics"
PATH_JOB_MONITOR = "/api/open/dros-ic-platform/open-job/getJobMonitor"


def _job_query(
    client: NanhuClient,
    job_id: str,
    *,
    user_id: str | None = None,
    biz_type: str = DEFAULT_BIZ_TYPE,
    run: int | None = None,
    include_run: bool = False,
) -> dict[str, Any]:
    query: dict[str, Any] = {
        "jobId": job_id,
        "userId": user_id or client.user_id,
        "bizType": biz_type,
    }
    if include_run and run is not None:
        query["run"] = run
    return query


def list_pods_v2(
    client: NanhuClient,
    job_id: str,
    *,
    user_id: str | None = None,
    biz_type: str = DEFAULT_BIZ_TYPE,
) -> dict[str, Any]:
    """V2 查询任务 POD 列表（GET .../getJobMetrics）。

    响应常见结构：``data.zoneType.nodes[].pods``。
    """
    return client.request(
        "GET",
        PATH_JOB_METRICS,
        query=_job_query(client, job_id, user_id=user_id, biz_type=biz_type),
    )


def list_pods_v3(
    client: NanhuClient,
    job_id: str,
    *,
    user_id: str | None = None,
    biz_type: str = DEFAULT_BIZ_TYPE,
    run: int | None = None,
) -> dict[str, Any]:
    """V3 查询任务 POD 列表（GET .../getJobMonitor）。

    可选 ``run`` 指定重启轮次；响应常见结构：
    ``data.jobInstancePodMonitorInfoVOList[].podInfos``。
    """
    return client.request(
        "GET",
        PATH_JOB_MONITOR,
        query=_job_query(
            client,
            job_id,
            user_id=user_id,
            biz_type=biz_type,
            run=run,
            include_run=True,
        ),
    )
