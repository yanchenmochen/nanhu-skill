"""任务 POD 列表与资源监控。

- F9: V2 ``getJobMetrics`` / V3 ``getJobMonitor``（POD 列表）
- F10: ``getJobMonitor`` 快照 + ``running-monitor`` 时序指标
"""

from __future__ import annotations

from typing import Any, Sequence

from nanhu.client import NanhuClient

DEFAULT_BIZ_TYPE = "DROS"

PATH_JOB_METRICS = "/api/open/dros-ic-platform/open-job/getJobMetrics"
PATH_JOB_MONITOR = "/api/open/dros-ic-platform/open-job/getJobMonitor"
PATH_RUNNING_MONITOR = "/api/open/dros-ic-platform/open-job/running-monitor"


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


def get_job_monitor(
    client: NanhuClient,
    job_id: str,
    *,
    user_id: str | None = None,
    biz_type: str = DEFAULT_BIZ_TYPE,
    run: int | None = None,
) -> dict[str, Any]:
    """查询任务资源/POD 监控快照（GET .../getJobMonitor）。

    与 slime ``monitor_slime_job`` 路径一致。可选 ``run`` 指定重启轮次；
    响应常见结构：``data.jobInstancePodMonitorInfoVOList[].podInfos``。
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


def list_pods_v3(
    client: NanhuClient,
    job_id: str,
    *,
    user_id: str | None = None,
    biz_type: str = DEFAULT_BIZ_TYPE,
    run: int | None = None,
) -> dict[str, Any]:
    """V3 查询任务 POD 列表（同 ``get_job_monitor``）。"""
    return get_job_monitor(
        client,
        job_id,
        user_id=user_id,
        biz_type=biz_type,
        run=run,
    )


def get_running_monitor(
    client: NanhuClient,
    job_id: str,
    pod_names: str | Sequence[str],
    start: int,
    end: int,
    *,
    indicator_name: str | None = None,
    step: int | None = None,
) -> dict[str, Any]:
    """V2 查询任务资源时序监控（GET .../running-monitor）。

    ``pod_names`` 可为逗号分隔字符串或名称序列；``start``/``end`` 为秒级时间戳。
    ``job_id`` 对应上游 query 参数 ``uuid``。
    """
    if isinstance(pod_names, str):
        names = pod_names
    else:
        names = ",".join(str(n) for n in pod_names)
    query: dict[str, Any] = {
        "uuid": job_id,
        "podNames": names,
        "start": start,
        "end": end,
    }
    if indicator_name is not None:
        query["indicatorName"] = indicator_name
    if step is not None:
        query["step"] = step
    return client.request("GET", PATH_RUNNING_MONITOR, query=query)
