"""Jobs OpenAPI: list / detail / lifecycle / create train & deploy (Wave1 F4–F7).

Write paths default to dry-run unless ``submit=True``.
``userId`` always comes from ``client.user_id``; ``accessToken`` via ``client.request``.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from nanhu.client import NanhuClient

try:
    import yaml
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PyYAML required: pip install pyyaml") from exc

JOB_TYPE_TRAIN = "AI_TRAIN"
JOB_TYPE_DEPLOY = "AI_ONLINE_INFERENCE_SERVICE"
DEFAULT_BIZ_TYPE = "DROS"

PATH_JOB_LIST = "/api/open/dros-ic-platform/open-job/jobList"
PATH_JOB_LIST_ALL = "/api/open/dros-ic-platform/open-job/jobListAll"
PATH_JOB_DETAIL = "/api/open/dros-ic-platform/open-job/getJobDetail"
PATH_STOP = "/api/open/dros-ic-platform/open-job/stop"
PATH_RESTART = "/api/open/dros-ic-platform/open-job/restart"
PATH_RESTART_INFERENCE = "/api/open/dros-ic-platform/open-job/restartInferenceJob"
PATH_POD_RESTART = "/api/open/dros-ic-platform/open-job/podRestart"
PATH_CREATE_TRAIN_V2 = "/api/open/dros-ic-platform/open-job/create"
PATH_CREATE_TRAIN_V3 = "/api/open/dros-ic-platform/open-job/v3/create"
PATH_CREATE_DEPLOY_V2 = "/api/open/dros-ic-platform/open-job/createInferenceJob"
PATH_CREATE_DEPLOY_V3 = "/api/open/dros-ic-platform/open-job/v3/createInferenceJob"

_FRIENDLY_META_KEYS = frozenset({"api_base", "user_id", "biz_type", "name_prefix"})


def normalize_status(status: str | None) -> str | None:
    """Normalize job status filter to lowercase; ``None``/blank stay ``None``."""
    if status is None:
        return None
    text = str(status).strip()
    if not text:
        return None
    return text.lower()


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


def _is_api_shaped_body(cfg: dict[str, Any]) -> bool:
    """True when ``cfg`` already looks like an OpenAPI JSON body (camelCase)."""
    if "algorithmUuid" in cfg or "algorithmImageUrl" in cfg:
        return True
    resource = cfg.get("resource")
    if isinstance(resource, dict) and "projectUuid" in resource:
        return True
    return False


def load_job_config(path: str | Path) -> dict[str, Any]:
    """Load a YAML/JSON job config file into a dict."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if p.suffix.lower() in {".yaml", ".yml"}:
        data = yaml.safe_load(text) or {}
    else:
        import json

        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"job config must be a mapping, got {type(data).__name__}")
    return data


def build_train_payload(
    cfg: dict[str, Any],
    *,
    name: str | None = None,
    worker_num: int | None = None,
    extra_env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build create-train request body from friendly YAML or an API-shaped dict.

    Friendly keys follow ``submit_nanhu_job`` conventions (``algorithm.uuid``,
    ``resource.project_uuid``, ``env_vars`` map, etc.). API-shaped bodies
    (``algorithmUuid`` / ``algorithmImageUrl`` / ``resource.projectUuid``) are
    copied with optional ``name`` / ``worker_num`` / env overrides.
    """
    if _is_api_shaped_body(cfg):
        body = {k: v for k, v in cfg.items() if k not in _FRIENDLY_META_KEYS}
        body = dict(body)
        if name is not None:
            body["name"] = name
        if worker_num is not None:
            resource = dict(body.get("resource") or {})
            resource["workerNum"] = int(worker_num)
            body["resource"] = resource
        if extra_env:
            env_vars = list(body.get("envVars") or [])
            for k, v in extra_env.items():
                env_vars = [e for e in env_vars if e.get("key") != k]
                env_vars.append({"key": k, "value": str(v)})
            body["envVars"] = env_vars
        return body

    algo = cfg.get("algorithm") or {}
    resource_cfg = dict(cfg.get("resource") or {})
    wn = int(worker_num if worker_num is not None else resource_cfg.get("worker_num", 1))

    env_src = cfg.get("env_vars") or {}
    if isinstance(env_src, dict):
        env_vars = [{"key": str(k), "value": str(v)} for k, v in env_src.items()]
    else:
        env_vars = list(env_src)
    for k, v in (extra_env or {}).items():
        env_vars = [e for e in env_vars if e.get("key") != k]
        env_vars.append({"key": k, "value": str(v)})

    mounted: list[dict[str, Any]] = []
    for m in cfg.get("mounted_storages") or []:
        item: dict[str, Any] = {
            "uuid": m["uuid"],
            "ossName": m.get("oss_name") or m.get("ossName"),
            "bucket": m["bucket"],
        }
        if m.get("path") is not None:
            item["path"] = m["path"]
        out_path = m.get("output_path", m.get("outputPath"))
        if out_path is not None:
            item["outputPath"] = out_path
        mounted.append(item)

    out = cfg.get("output_dir") or cfg.get("outputDir") or {}
    output_dir: dict[str, Any] | None = None
    if out:
        output_dir = {"uuid": out["uuid"], "bucket": out["bucket"]}
        if out.get("path") is not None:
            output_dir["path"] = out["path"]
        op = out.get("output_path", out.get("outputPath"))
        if op is not None:
            output_dir["outputPath"] = op

    job_name = name or cfg.get("name")
    if not job_name:
        raise ValueError("train payload requires name= or cfg['name']")

    body: dict[str, Any] = {
        "name": job_name,
        "jobType": cfg.get("job_type") or cfg.get("jobType") or JOB_TYPE_TRAIN,
        "startCmd": str(cfg.get("start_cmd") or cfg.get("startCmd") or "").strip(),
        "resource": {
            "projectUuid": resource_cfg.get("project_uuid") or resource_cfg["projectUuid"],
            "subMissionName": resource_cfg.get("sub_mission_name")
            or resource_cfg["subMissionName"],
            "computeSpecUuid": resource_cfg.get("compute_spec_uuid")
            or resource_cfg["computeSpecUuid"],
            "computeSpecName": resource_cfg.get("compute_spec_name")
            or resource_cfg["computeSpecName"],
            "workerNum": wn,
        },
        "envVars": env_vars,
    }

    if algo.get("uuid") or cfg.get("algorithm_uuid"):
        body["algorithmUuid"] = algo.get("uuid") or cfg["algorithm_uuid"]
        body["algorithmName"] = algo.get("name") or cfg.get("algorithm_name") or ""
    if cfg.get("algorithm_image_url") or cfg.get("algorithmImageUrl"):
        body["algorithmImageUrl"] = cfg.get("algorithm_image_url") or cfg["algorithmImageUrl"]

    mount_path = (algo.get("mount_path") or cfg.get("algorithm_mount_path") or "").strip()
    if mount_path:
        body["algorithmMountPath"] = mount_path

    run_type = (cfg.get("run_type") or cfg.get("runType") or "").strip()
    if run_type:
        body["runType"] = run_type

    sq_id = resource_cfg.get("sub_quota_id") or resource_cfg.get("subQuotaId")
    sq_name = resource_cfg.get("sub_quota_name") or resource_cfg.get("subQuotaName")
    if sq_id:
        body["resource"]["subQuotaId"] = sq_id
    if sq_name:
        body["resource"]["subQuotaName"] = sq_name

    if mounted:
        body["mountedStorages"] = mounted
    if output_dir is not None:
        body["outputDir"] = output_dir

    if "use_tensorboard" in cfg or "useTensorBoard" in cfg:
        body["useTensorBoard"] = bool(cfg.get("use_tensorboard", cfg.get("useTensorBoard")))
    if "auto_restart" in cfg or "autoRestart" in cfg:
        body["autoRestart"] = bool(cfg.get("auto_restart", cfg.get("autoRestart")))

    for src_key, dst_key in (
        ("dataSets", "dataSets"),
        ("data_sets", "dataSets"),
        ("subJobs", "subJobs"),
        ("sub_jobs", "subJobs"),
        ("algoOssVolume", "algoOssVolume"),
        ("algo_oss_volume", "algoOssVolume"),
        ("gitRepoInfo", "gitRepoInfo"),
        ("git_repo_info", "gitRepoInfo"),
        ("resumeable", "resumeable"),
        ("enableSpotRestart", "enableSpotRestart"),
        ("enable_spot_restart", "enableSpotRestart"),
        ("fallBack", "fallBack"),
        ("fall_back", "fallBack"),
        ("maxRestarts", "maxRestarts"),
        ("max_restarts", "maxRestarts"),
        ("promotionDetail", "promotionDetail"),
        ("promotion_detail", "promotionDetail"),
    ):
        if src_key in cfg and cfg[src_key] is not None:
            body[dst_key] = cfg[src_key]

    return body


def build_deploy_payload(
    cfg: dict[str, Any],
    *,
    name: str | None = None,
    worker_num: int | None = None,
    extra_env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build create-deploy request body from friendly YAML or an API-shaped dict."""
    resource = cfg.get("resource")
    api_shaped = (
        "inferenceType" in cfg
        or _is_api_shaped_body(cfg)
        or (isinstance(resource, dict) and "projectUuid" in resource)
    )
    if api_shaped and ("inferenceType" in cfg or "algorithmUuid" in cfg or "algorithmImageUrl" in cfg or "projectUuid" in (resource or {})):
        body = {k: v for k, v in cfg.items() if k not in _FRIENDLY_META_KEYS}
        body = dict(body)
        if "inference_type" in body and "inferenceType" not in body:
            body["inferenceType"] = body.pop("inference_type")
        if name is not None:
            body["name"] = name
        if worker_num is not None:
            res = dict(body.get("resource") or {})
            res["workerNum"] = int(worker_num)
            body["resource"] = res
        if extra_env:
            env_vars = list(body.get("envVars") or [])
            for k, v in extra_env.items():
                env_vars = [e for e in env_vars if e.get("key") != k]
                env_vars.append({"key": k, "value": str(v)})
            body["envVars"] = env_vars
        return body

    algo = cfg.get("algorithm") or {}
    resource_cfg = dict(cfg.get("resource") or {})
    wn = int(worker_num if worker_num is not None else resource_cfg.get("worker_num", 1))

    env_src = cfg.get("env_vars") or {}
    if isinstance(env_src, dict):
        env_vars = [{"key": str(k), "value": str(v)} for k, v in env_src.items()]
    else:
        env_vars = list(env_src)
    for k, v in (extra_env or {}).items():
        env_vars = [e for e in env_vars if e.get("key") != k]
        env_vars.append({"key": k, "value": str(v)})

    mounted: list[dict[str, Any]] = []
    for m in cfg.get("mounted_storages") or []:
        item: dict[str, Any] = {
            "uuid": m["uuid"],
            "ossName": m.get("oss_name") or m.get("ossName"),
            "bucket": m["bucket"],
        }
        if m.get("path") is not None:
            item["path"] = m["path"]
        out_path = m.get("output_path", m.get("outputPath"))
        if out_path is not None:
            item["outputPath"] = out_path
        mounted.append(item)

    job_name = name or cfg.get("name")
    if not job_name:
        raise ValueError("deploy payload requires name= or cfg['name']")

    body: dict[str, Any] = {
        "name": job_name,
        "inferenceType": cfg.get("inference_type") or cfg.get("inferenceType") or "customized",
        "resource": {
            "projectUuid": resource_cfg.get("project_uuid") or resource_cfg["projectUuid"],
            "subMissionName": resource_cfg.get("sub_mission_name")
            or resource_cfg["subMissionName"],
            "computeSpecUuid": resource_cfg.get("compute_spec_uuid")
            or resource_cfg["computeSpecUuid"],
            "computeSpecName": resource_cfg.get("compute_spec_name")
            or resource_cfg["computeSpecName"],
            "workerNum": wn,
        },
        "envVars": env_vars,
    }

    if cfg.get("description") is not None:
        body["description"] = cfg["description"]

    if algo.get("uuid") or cfg.get("algorithm_uuid"):
        body["algorithmUuid"] = algo.get("uuid") or cfg["algorithm_uuid"]
        body["algorithmName"] = algo.get("name") or cfg.get("algorithm_name") or ""
    if cfg.get("algorithm_image_url") or cfg.get("algorithmImageUrl"):
        body["algorithmImageUrl"] = cfg.get("algorithm_image_url") or cfg["algorithmImageUrl"]

    mount_path = (algo.get("mount_path") or cfg.get("algorithm_mount_path") or "").strip()
    if mount_path:
        body["algorithmMountPath"] = mount_path

    start_cmd = cfg.get("start_cmd") or cfg.get("startCmd")
    if start_cmd is not None:
        body["startCmd"] = str(start_cmd).strip()

    frame = cfg.get("inference_frame_type") or cfg.get("inferenceFrameType")
    if frame:
        body["inferenceFrameType"] = frame

    for src, dst in (
        ("per_worker_node_num", "perWorkerNodeNum"),
        ("perWorkerNodeNum", "perWorkerNodeNum"),
        ("pd_count", "pdCount"),
        ("pdCount", "pdCount"),
    ):
        if src in resource_cfg and resource_cfg[src] is not None:
            body["resource"][dst] = resource_cfg[src]

    sq_id = resource_cfg.get("sub_quota_id") or resource_cfg.get("subQuotaId")
    sq_name = resource_cfg.get("sub_quota_name") or resource_cfg.get("subQuotaName")
    if sq_id:
        body["resource"]["subQuotaId"] = sq_id
    if sq_name:
        body["resource"]["subQuotaName"] = sq_name

    model = cfg.get("model_dir") or cfg.get("modelDir")
    if model:
        body["modelDir"] = {
            "uuid": model["uuid"],
            "bucket": model["bucket"],
            "path": model["path"],
        }

    if mounted:
        body["mountedStorages"] = mounted

    for src_key, dst_key in (
        ("spread", "spread"),
        ("running", "running"),
        ("expire_days", "expireDays"),
        ("expireDays", "expireDays"),
        ("auto_restart", "autoRestart"),
        ("autoRestart", "autoRestart"),
        ("max_restarts", "maxRestarts"),
        ("maxRestarts", "maxRestarts"),
        ("sub_jobs", "subJobs"),
        ("subJobs", "subJobs"),
        ("router", "router"),
        ("fall_back", "fallBack"),
        ("fallBack", "fallBack"),
        ("promotion_detail", "promotionDetail"),
        ("promotionDetail", "promotionDetail"),
        ("algo_oss_volume", "algoOssVolume"),
        ("algoOssVolume", "algoOssVolume"),
        ("git_repo_info", "gitRepoInfo"),
        ("gitRepoInfo", "gitRepoInfo"),
    ):
        if src_key in cfg and cfg[src_key] is not None:
            body[dst_key] = cfg[src_key]

    return body


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
            status=normalize_status(status),
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
            status=normalize_status(status),
            projectId=project_id,
            current=current,
            pageSize=page_size,
        )
        return self.client.request("GET", PATH_JOB_LIST_ALL, query=query)

    def list_running_jobs(
        self,
        *,
        biz_type: str = DEFAULT_BIZ_TYPE,
        project_id: str | None = None,
        current: int | None = 1,
        page_size: int | None = 20,
        status: str = "running",
    ) -> dict[str, Any]:
        """Aggregate train + deploy lists filtered by ``status`` (default running).

        Returns a synthetic envelope::

            {
              "code": 0,
              "data": {
                "result": [...],  # each row tagged with jobType
                "train": {...},   # raw train list payload data/page
                "deploy": {...},
              }
            }
        """
        status_norm = normalize_status(status) or "running"
        train = self.list_train_jobs(
            biz_type=biz_type,
            status=status_norm,
            project_id=project_id,
            current=current,
            page_size=page_size,
        )
        deploy = self.list_deploy_jobs(
            biz_type=biz_type,
            status=status_norm,
            project_id=project_id,
            current=current,
            page_size=page_size,
        )

        def _rows(payload: dict[str, Any], job_type: str) -> list[dict[str, Any]]:
            data = payload.get("data") if isinstance(payload, dict) else None
            rows: list[Any]
            if isinstance(data, dict):
                rows = data.get("result") or []
            elif isinstance(data, list):
                rows = data
            else:
                rows = []
            out: list[dict[str, Any]] = []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                item = dict(row)
                item.setdefault("jobType", job_type)
                out.append(item)
            return out

        merged = _rows(train, JOB_TYPE_TRAIN) + _rows(deploy, JOB_TYPE_DEPLOY)
        return {
            "code": 0,
            "data": {
                "result": merged,
                "status": status_norm,
                "train": train.get("data") if isinstance(train, dict) else train,
                "deploy": deploy.get("data") if isinstance(deploy, dict) else deploy,
            },
        }

    def stop_job(
        self,
        job_id: str,
        *,
        biz_type: str = DEFAULT_BIZ_TYPE,
        submit: bool = False,
    ) -> dict[str, Any]:
        """PUT stop job. Dry-run unless ``submit=True``."""
        query = _user_query(self.client, biz_type=biz_type, jobId=job_id)
        if not submit:
            return _dry_run("PUT", PATH_STOP, query=query)
        return self.client.request("PUT", PATH_STOP, query=query)

    def restart_job(
        self,
        job_id: str,
        *,
        biz_type: str = DEFAULT_BIZ_TYPE,
        submit: bool = False,
    ) -> dict[str, Any]:
        """POST restart job (不变配). Dry-run unless ``submit=True``."""
        query = _user_query(self.client, biz_type=biz_type, jobId=job_id)
        if not submit:
            return _dry_run("POST", PATH_RESTART, query=query)
        return self.client.request("POST", PATH_RESTART, query=query)

    def restart_inference_job(
        self,
        body: dict[str, Any],
        *,
        biz_type: str | None = DEFAULT_BIZ_TYPE,
        user_extra_info: str | None = None,
        submit: bool = False,
    ) -> dict[str, Any]:
        """POST 变配重启部署作业（``restartInferenceJob``），保持 jobId 不变。

        Body 需含 ``uuid``（待重启作业 id）及与创建部署类似的字段。
        Dry-run unless ``submit=True``.
        """
        if not body.get("uuid"):
            raise ValueError("restartInferenceJob body requires uuid")
        query = _user_query(
            self.client,
            biz_type=biz_type if biz_type is not None else DEFAULT_BIZ_TYPE,
            userExtraInfo=user_extra_info,
        )
        if not submit:
            return _dry_run("POST", PATH_RESTART_INFERENCE, query=query, body=body)
        return self.client.request("POST", PATH_RESTART_INFERENCE, query=query, body=body)

    def restart_inference_from_config(
        self,
        cfg: dict[str, Any] | str | Path,
        *,
        uuid: str | None = None,
        name: str | None = None,
        worker_num: int | None = None,
        extra_env: dict[str, str] | None = None,
        biz_type: str | None = DEFAULT_BIZ_TYPE,
        submit: bool = False,
    ) -> dict[str, Any]:
        """Load/build deploy-like payload then ``restart_inference_job`` (dry-run by default)."""
        if isinstance(cfg, (str, Path)):
            cfg = load_job_config(cfg)
        body = build_deploy_payload(cfg, name=name, worker_num=worker_num, extra_env=extra_env)
        job_uuid = uuid or cfg.get("uuid") or body.get("uuid")
        if not job_uuid:
            raise ValueError("restart-deploy requires uuid= or cfg['uuid']")
        body["uuid"] = str(job_uuid)
        resolved_biz = biz_type
        if biz_type is DEFAULT_BIZ_TYPE and cfg.get("biz_type"):
            resolved_biz = str(cfg["biz_type"])
        return self.restart_inference_job(body, biz_type=resolved_biz, submit=submit)

    def restart_failed_pods(
        self,
        job_id: str,
        job_pod_names: str | list[str],
        *,
        submit: bool = False,
    ) -> dict[str, Any]:
        """POST 重启失败 POD（``podRestart``）。Dry-run unless ``submit=True``.

        Body carries ``userId`` / ``jobId`` / ``jobPodNames`` (comma-separated).
        """
        if isinstance(job_pod_names, (list, tuple)):
            pods = ",".join(str(n) for n in job_pod_names)
        else:
            pods = str(job_pod_names)
        body: dict[str, Any] = {
            "userId": self.client.user_id,
            "jobId": job_id,
            "jobPodNames": pods,
        }
        if not submit:
            return _dry_run("POST", PATH_POD_RESTART, query={}, body=body)
        return self.client.request("POST", PATH_POD_RESTART, body=body)

    def create_train(
        self,
        body: dict[str, Any],
        *,
        version: str = "v2",
        biz_type: str | None = DEFAULT_BIZ_TYPE,
        user_extra_info: str | None = None,
        submit: bool = False,
    ) -> dict[str, Any]:
        """POST create train job (V2 ``/create`` or V3 ``/v3/create``).

        Dry-run unless ``submit=True``. V3 OpenAPI omits ``bizType`` by default.
        """
        ver = version.lower().lstrip("v")
        if ver == "2":
            path = PATH_CREATE_TRAIN_V2
            query = _user_query(
                self.client,
                biz_type=biz_type if biz_type is not None else DEFAULT_BIZ_TYPE,
                userExtraInfo=user_extra_info,
            )
        elif ver == "3":
            path = PATH_CREATE_TRAIN_V3
            query = _user_query(
                self.client,
                biz_type=None,
                userExtraInfo=user_extra_info,
            )
            if biz_type is not None and biz_type != DEFAULT_BIZ_TYPE:
                query["bizType"] = biz_type
        else:
            raise ValueError(f"unsupported train API version: {version!r} (use v2/v3)")

        if not submit:
            return _dry_run("POST", path, query=query, body=body)
        return self.client.request("POST", path, query=query, body=body)

    def create_train_from_config(
        self,
        cfg: dict[str, Any] | str | Path,
        *,
        name: str | None = None,
        worker_num: int | None = None,
        extra_env: dict[str, str] | None = None,
        version: str = "v2",
        biz_type: str | None = DEFAULT_BIZ_TYPE,
        submit: bool = False,
    ) -> dict[str, Any]:
        """Load/build train payload then ``create_train`` (dry-run by default)."""
        if isinstance(cfg, (str, Path)):
            cfg = load_job_config(cfg)
        resolved_name = name
        if resolved_name is None and not cfg.get("name"):
            prefix = cfg.get("name_prefix") or "nanhu-job"
            resolved_name = f"{prefix}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        body = build_train_payload(
            cfg, name=resolved_name, worker_num=worker_num, extra_env=extra_env
        )
        resolved_biz = biz_type
        if biz_type is DEFAULT_BIZ_TYPE and cfg.get("biz_type"):
            resolved_biz = str(cfg["biz_type"])
        return self.create_train(body, version=version, biz_type=resolved_biz, submit=submit)

    def create_deploy(
        self,
        body: dict[str, Any],
        *,
        version: str = "v2",
        biz_type: str | None = DEFAULT_BIZ_TYPE,
        user_extra_info: str | None = None,
        submit: bool = False,
    ) -> dict[str, Any]:
        """POST create deploy job (V2 ``createInferenceJob`` / V3 ``v3/createInferenceJob``).

        Dry-run unless ``submit=True``.
        """
        ver = version.lower().lstrip("v")
        if ver == "2":
            path = PATH_CREATE_DEPLOY_V2
            query = _user_query(
                self.client,
                biz_type=biz_type if biz_type is not None else DEFAULT_BIZ_TYPE,
                userExtraInfo=user_extra_info,
            )
        elif ver == "3":
            path = PATH_CREATE_DEPLOY_V3
            query = _user_query(
                self.client,
                biz_type=None,
                userExtraInfo=user_extra_info,
            )
            if biz_type is not None and biz_type != DEFAULT_BIZ_TYPE:
                query["bizType"] = biz_type
        else:
            raise ValueError(f"unsupported deploy API version: {version!r} (use v2/v3)")

        if not submit:
            return _dry_run("POST", path, query=query, body=body)
        return self.client.request("POST", path, query=query, body=body)

    def create_deploy_from_config(
        self,
        cfg: dict[str, Any] | str | Path,
        *,
        name: str | None = None,
        worker_num: int | None = None,
        extra_env: dict[str, str] | None = None,
        version: str = "v2",
        biz_type: str | None = DEFAULT_BIZ_TYPE,
        submit: bool = False,
    ) -> dict[str, Any]:
        """Load/build deploy payload then ``create_deploy`` (dry-run by default)."""
        if isinstance(cfg, (str, Path)):
            cfg = load_job_config(cfg)
        body = build_deploy_payload(cfg, name=name, worker_num=worker_num, extra_env=extra_env)
        resolved_biz = biz_type
        if biz_type is DEFAULT_BIZ_TYPE and cfg.get("biz_type"):
            resolved_biz = str(cfg["biz_type"])
        return self.create_deploy(body, version=version, biz_type=resolved_biz, submit=submit)


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


def list_running_jobs(client: NanhuClient, **kwargs: Any) -> dict[str, Any]:
    return JobsApi(client).list_running_jobs(**kwargs)


def stop_job(client: NanhuClient, job_id: str, **kwargs: Any) -> dict[str, Any]:
    return JobsApi(client).stop_job(job_id, **kwargs)


def restart_job(client: NanhuClient, job_id: str, **kwargs: Any) -> dict[str, Any]:
    return JobsApi(client).restart_job(job_id, **kwargs)


def restart_inference_job(
    client: NanhuClient, body: dict[str, Any], **kwargs: Any
) -> dict[str, Any]:
    return JobsApi(client).restart_inference_job(body, **kwargs)


def restart_inference_from_config(
    client: NanhuClient, cfg: dict[str, Any] | str | Path, **kwargs: Any
) -> dict[str, Any]:
    return JobsApi(client).restart_inference_from_config(cfg, **kwargs)


def restart_failed_pods(
    client: NanhuClient, job_id: str, job_pod_names: str | list[str], **kwargs: Any
) -> dict[str, Any]:
    return JobsApi(client).restart_failed_pods(job_id, job_pod_names, **kwargs)


def create_train(client: NanhuClient, body: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    return JobsApi(client).create_train(body, **kwargs)


def create_train_from_config(
    client: NanhuClient, cfg: dict[str, Any] | str | Path, **kwargs: Any
) -> dict[str, Any]:
    return JobsApi(client).create_train_from_config(cfg, **kwargs)


def create_deploy(client: NanhuClient, body: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    return JobsApi(client).create_deploy(body, **kwargs)


def create_deploy_from_config(
    client: NanhuClient, cfg: dict[str, Any] | str | Path, **kwargs: Any
) -> dict[str, Any]:
    return JobsApi(client).create_deploy_from_config(cfg, **kwargs)
