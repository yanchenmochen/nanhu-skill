"""Jobs OpenAPI: list / detail (Wave1 F4).

``userId`` always comes from ``client.user_id``; ``accessToken`` via ``client.request``.
"""

from __future__ import annotations

from typing import Any

from nanhu.client import NanhuClient

JOB_TYPE_TRAIN = "AI_TRAIN"
JOB_TYPE_DEPLOY = "AI_ONLINE_INFERENCE_SERVICE"
DEFAULT_BIZ_TYPE = "DROS"

PATH_JOB_LIST = "/api/open/dros-ic-platform/open-job/jobList"
PATH_JOB_LIST_ALL = "/api/open/dros-ic-platform/open-job/jobListAll"
PATH_JOB_DETAIL = "/api/open/dros-ic-platform/open-job/getJobDetail"


def _drop_none(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


def _user_query(
    client: NanhuClient,
    *,
    biz_type: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    q: dict[str, Any] = {"userId": client.user_id}
    if biz_type is not None:
        q["bizType"] = biz_type
    q.update(_drop_none(extra))
    return q


class JobsApi:
    """Jobs endpoints bound to a ``NanhuClient``."""

    def __init__(self, client: NanhuClient) -> None:
        self.client = client

    def list_jobs(
        self,
        job_type: str,
        *,
        biz_type: str = DEFAULT_BIZ_TYPE,
        status: str | None = None,
        project_id: str | None = None,
        current: int | None = None,
        page_size: int | None = None,
    ) -> dict[str, Any]:
        """GET train/deploy job list (``jobList``). ``job_type`` required."""
        query = _user_query(
            self.client,
            biz_type=biz_type,
            jobType=job_type,
            status=status,
            projectId=project_id,
            current=current,
            pageSize=page_size,
        )
        return self.client.request("GET", PATH_JOB_LIST, query=query)

    def list_train_jobs(self, **kwargs: Any) -> dict[str, Any]:
        return self.list_jobs(JOB_TYPE_TRAIN, **kwargs)

    def list_deploy_jobs(self, **kwargs: Any) -> dict[str, Any]:
        return self.list_jobs(JOB_TYPE_DEPLOY, **kwargs)

    def get_job_detail(
        self,
        job_id: str,
        *,
        biz_type: str = DEFAULT_BIZ_TYPE,
        job_type: str | None = None,
    ) -> dict[str, Any]:
        """GET job detail (``getJobDetail``)."""
        query = _user_query(
            self.client,
            biz_type=biz_type,
            jobId=job_id,
            jobType=job_type,
        )
        return self.client.request("GET", PATH_JOB_DETAIL, query=query)

    def list_jobs_all(
        self,
        *,
        job_type: str | None = None,
        status: str | None = None,
        project_id: str | None = None,
        current: int | None = None,
        page_size: int | None = None,
    ) -> dict[str, Any]:
        """GET full job list across types (``jobListAll``). No bizType in OpenAPI."""
        query = _user_query(
            self.client,
            biz_type=None,
            jobType=job_type,
            status=status,
            projectId=project_id,
            current=current,
            pageSize=page_size,
        )
        return self.client.request("GET", PATH_JOB_LIST_ALL, query=query)


def list_jobs(client: NanhuClient, job_type: str, **kwargs: Any) -> dict[str, Any]:
    return JobsApi(client).list_jobs(job_type, **kwargs)


def list_train_jobs(client: NanhuClient, **kwargs: Any) -> dict[str, Any]:
    return JobsApi(client).list_train_jobs(**kwargs)


def list_deploy_jobs(client: NanhuClient, **kwargs: Any) -> dict[str, Any]:
    return JobsApi(client).list_deploy_jobs(**kwargs)


def get_job_detail(client: NanhuClient, job_id: str, **kwargs: Any) -> dict[str, Any]:
    return JobsApi(client).get_job_detail(job_id, **kwargs)


def list_jobs_all(client: NanhuClient, **kwargs: Any) -> dict[str, Any]:
    return JobsApi(client).list_jobs_all(**kwargs)
