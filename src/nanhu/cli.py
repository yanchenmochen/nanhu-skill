"""Unified ``nanhu`` CLI: argparse subcommands over Wave1 API modules.

Write operations default to dry-run; pass ``--submit`` to call the API.
Stdout is JSON by default (passwords redacted); ``--format table`` prints a
projected list table when the response looks like a list.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

from nanhu.api import algorithms as algorithms_api
from nanhu.api import devenv as devenv_api
from nanhu.api import images as images_api
from nanhu.api import jobs as jobs_api
from nanhu.api import logs as logs_api
from nanhu.api import pods as pods_api
from nanhu.api import resources as resources_api
from nanhu.api import seahold as seahold_api
from nanhu.client import NanhuClient
from nanhu.config import ConfigError
from nanhu.formatters import (
    format_table,
    project_list_payload,
    redact_secrets,
    should_use_table,
)

CLUSTERS = ("wuxi", "x10000")
DEFAULT_CLUSTER = "wuxi"


def _print_json(payload: Any, *, pretty: bool = False) -> None:
    """Emit JSON for agent/script consumption (UTF-8, no ASCII escape).

    Default is compact (no indent). Pass ``pretty=True`` for indented output.
    """
    if pretty:
        text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    else:
        text = json.dumps(
            payload, ensure_ascii=False, separators=(",", ":"), default=str
        )
    sys.stdout.write(text)
    sys.stdout.write("\n")


def _emit(payload: Any, args: argparse.Namespace) -> None:
    """Print command result honoring ``--format`` (secrets always redacted)."""
    redacted = redact_secrets(payload)
    fmt = getattr(args, "output_format", None) or getattr(args, "format", "json") or "json"
    if should_use_table(redacted, fmt):
        rows = project_list_payload(redacted) or []
        sys.stdout.write(format_table(rows))
        return
    pretty = bool(getattr(args, "pretty", False))
    _print_json(redacted, pretty=pretty)


def _parse_bool(value: str) -> bool:
    v = value.strip().lower()
    if v in {"1", "true", "yes", "y"}:
        return True
    if v in {"0", "false", "no", "n"}:
        return False
    raise argparse.ArgumentTypeError(f"expected true/false, got {value!r}")


def _build_client(args: argparse.Namespace) -> NanhuClient:
    kwargs: dict[str, Any] = {}
    if getattr(args, "credentials", None):
        kwargs["credentials_path"] = Path(args.credentials)
    if getattr(args, "clusters_file", None):
        kwargs["clusters_path"] = Path(args.clusters_file)
    return NanhuClient.from_cluster(args.cluster, **kwargs)


def _add_client_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--credentials",
        type=Path,
        default=None,
        help="credentials.env path (default: config/credentials.<cluster>.env then credentials.env)",
    )
    parser.add_argument(
        "--clusters-file",
        type=Path,
        default=None,
        help="clusters.yaml path override",
    )


def _add_submit_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--submit",
        action="store_true",
        help="actually call the API (default: dry-run, print request JSON)",
    )


# ---------------------------------------------------------------------------
# jobs
# ---------------------------------------------------------------------------


def _cmd_jobs_list(client: NanhuClient, args: argparse.Namespace) -> Any:
    return jobs_api.list_jobs(
        client,
        args.job_type,
        biz_type=args.biz_type,
        status=args.status,
        project_id=args.project_id,
        current=args.current,
        page_size=args.page_size,
    )


def _cmd_jobs_detail(client: NanhuClient, args: argparse.Namespace) -> Any:
    return jobs_api.get_job_detail(
        client,
        args.job_id,
        biz_type=args.biz_type,
        job_type=args.job_type,
    )


def _cmd_jobs_list_all(client: NanhuClient, args: argparse.Namespace) -> Any:
    return jobs_api.list_jobs_all(
        client,
        job_type=args.job_type,
        status=args.status,
        project_id=args.project_id,
        current=args.current,
        page_size=args.page_size,
    )


def _cmd_jobs_running(client: NanhuClient, args: argparse.Namespace) -> Any:
    return jobs_api.list_running_jobs(
        client,
        biz_type=args.biz_type,
        project_id=args.project_id,
        current=args.current,
        page_size=args.page_size,
        status=args.status,
    )


def _cmd_jobs_stop(client: NanhuClient, args: argparse.Namespace) -> Any:
    return jobs_api.stop_job(
        client,
        args.job_id,
        biz_type=args.biz_type,
        submit=args.submit,
    )


def _cmd_jobs_restart(client: NanhuClient, args: argparse.Namespace) -> Any:
    return jobs_api.restart_job(
        client,
        args.job_id,
        biz_type=args.biz_type,
        submit=args.submit,
    )


def _cmd_jobs_create_train(client: NanhuClient, args: argparse.Namespace) -> Any:
    return jobs_api.create_train_from_config(
        client,
        args.config,
        name=args.name,
        worker_num=args.worker_num,
        version=args.version,
        biz_type=args.biz_type,
        submit=args.submit,
    )


def _cmd_jobs_create_deploy(client: NanhuClient, args: argparse.Namespace) -> Any:
    return jobs_api.create_deploy_from_config(
        client,
        args.config,
        name=args.name,
        worker_num=args.worker_num,
        version=args.version,
        biz_type=args.biz_type,
        submit=args.submit,
    )


def _cmd_jobs_restart_deploy(client: NanhuClient, args: argparse.Namespace) -> Any:
    return jobs_api.restart_inference_from_config(
        client,
        args.config,
        uuid=args.uuid,
        name=args.name,
        worker_num=args.worker_num,
        biz_type=args.biz_type,
        submit=args.submit,
    )


def _cmd_jobs_restart_pod(client: NanhuClient, args: argparse.Namespace) -> Any:
    return jobs_api.restart_failed_pods(
        client,
        args.job_id,
        args.pod_names,
        submit=args.submit,
    )


# ---------------------------------------------------------------------------
# devenv
# ---------------------------------------------------------------------------


def _cmd_devenv_list(client: NanhuClient, args: argparse.Namespace) -> Any:
    return devenv_api.list_devenv(
        client,
        status=args.status,
        project_id=args.project_id,
        current=args.current,
        page_size=args.page_size,
        biz_type=args.biz_type,
    )


def _cmd_devenv_detail(client: NanhuClient, args: argparse.Namespace) -> Any:
    return devenv_api.get_devenv(client, args.job_id, biz_type=args.biz_type)


def _cmd_devenv_create(client: NanhuClient, args: argparse.Namespace) -> Any:
    cfg = devenv_api.load_devenv_config(args.config)
    body = devenv_api.build_create_body(cfg)
    return devenv_api.create_devenv(client, body, submit=args.submit)


def _cmd_devenv_restart(client: NanhuClient, args: argparse.Namespace) -> Any:
    cfg = devenv_api.load_devenv_config(args.config)
    body = devenv_api.build_create_body(cfg, uuid=args.uuid)
    return devenv_api.restart_devenv(client, body, submit=args.submit)


def _cmd_devenv_save_image(client: NanhuClient, args: argparse.Namespace) -> Any:
    return devenv_api.save_image(
        client,
        args.job_id,
        repository=args.repository,
        tag=args.tag,
        submit=args.submit,
    )


# ---------------------------------------------------------------------------
# pods
# ---------------------------------------------------------------------------


def _cmd_pods_list(client: NanhuClient, args: argparse.Namespace) -> Any:
    ver = (args.version or "v3").lower().lstrip("v")
    if ver == "2":
        return pods_api.list_pods_v2(
            client,
            args.job_id,
            biz_type=args.biz_type,
        )
    if ver == "3":
        return pods_api.list_pods_v3(
            client,
            args.job_id,
            biz_type=args.biz_type,
            run=args.run,
        )
    raise ValueError(f"unsupported pods API version: {args.version!r} (use v2/v3)")


def _cmd_pods_monitor(client: NanhuClient, args: argparse.Namespace) -> Any:
    if args.pod_names is not None and args.start is not None and args.end is not None:
        return pods_api.get_running_monitor(
            client,
            args.job_id,
            args.pod_names,
            args.start,
            args.end,
            indicator_name=args.indicator_name,
            step=args.step,
        )
    return pods_api.get_job_monitor(
        client,
        args.job_id,
        biz_type=args.biz_type,
        run=args.run,
    )


# ---------------------------------------------------------------------------
# logs
# ---------------------------------------------------------------------------


def _cmd_logs_get(client: NanhuClient, args: argparse.Namespace) -> Any:
    return logs_api.get_log_info(
        client,
        args.job_id,
        args.pod_names,
        zone=args.zone,
        cluster=args.cluster,
        biz_type=args.biz_type,
        start=args.start,
        end=args.end,
        run=args.run,
    )


def _cmd_logs_download(client: NanhuClient, args: argparse.Namespace) -> Any:
    raw = logs_api.download_log(
        client,
        args.job_id,
        args.pod_names,
        dest_path=args.output,
        biz_type=args.biz_type,
        start=args.start,
        end=args.end,
        run=args.run,
    )
    out: dict[str, Any] = {"size": len(raw)}
    if args.output:
        out["written"] = str(args.output)
    else:
        # Avoid dumping binary on stdout; agent should pass --output.
        out["note"] = "bytes not echoed; pass --output to save the log file"
    return out


def _cmd_logs_prefetch(client: NanhuClient, args: argparse.Namespace) -> Any:
    return logs_api.prefetch_log(
        client,
        args.job_id,
        args.pod_names,
        biz_type=args.biz_type,
        start=args.start,
        end=args.end,
        step=args.step,
    )


# ---------------------------------------------------------------------------
# resources / algorithms / images
# ---------------------------------------------------------------------------


def _cmd_resources_specs(client: NanhuClient, args: argparse.Namespace) -> Any:
    return resources_api.list_specs(
        client,
        resource_type=args.resource_type,
        current=args.current,
        page_size=args.page_size,
    )


def _cmd_resources_projects(client: NanhuClient, args: argparse.Namespace) -> Any:
    return resources_api.list_projects(
        client,
        resource_type=args.resource_type,
        current=args.current,
        page_size=args.page_size,
    )


def _cmd_resources_sub_projects(client: NanhuClient, args: argparse.Namespace) -> Any:
    return resources_api.list_sub_projects(client, args.project_id)


def _cmd_resources_promotions(client: NanhuClient, args: argparse.Namespace) -> Any:
    return resources_api.list_promotions(client, args.project_id)


def _cmd_algorithms_list(client: NanhuClient, args: argparse.Namespace) -> Any:
    return algorithms_api.list_algorithms(
        client,
        is_public=args.is_public,
        current=args.current,
        page_size=args.page_size,
        name=args.name,
        uuid=args.uuid,
    )


def _cmd_algorithms_get(client: NanhuClient, args: argparse.Namespace) -> Any:
    return algorithms_api.get_algorithm(
        client,
        args.uuid,
        is_public=args.is_public,
    )


def _cmd_algorithms_create(client: NanhuClient, args: argparse.Namespace) -> Any:
    return algorithms_api.create_algorithm_from_config(
        client, args.config, submit=args.submit
    )


def _cmd_algorithms_update(client: NanhuClient, args: argparse.Namespace) -> Any:
    return algorithms_api.update_algorithm_from_config(
        client, args.config, uuid=args.uuid, submit=args.submit
    )


def _cmd_algorithms_delete(client: NanhuClient, args: argparse.Namespace) -> Any:
    return algorithms_api.delete_algorithm(client, args.uuid, submit=args.submit)


def _cmd_algorithms_publish(client: NanhuClient, args: argparse.Namespace) -> Any:
    return algorithms_api.publish_algorithm(client, args.uuid, submit=args.submit)


def _cmd_algorithms_unpublish(client: NanhuClient, args: argparse.Namespace) -> Any:
    return algorithms_api.unpublish_algorithm(client, args.uuid, submit=args.submit)


def _cmd_algorithms_share(client: NanhuClient, args: argparse.Namespace) -> Any:
    return algorithms_api.share_algorithm(
        client, args.uuid, args.user_name, submit=args.submit
    )


def _cmd_algorithms_unshare(client: NanhuClient, args: argparse.Namespace) -> Any:
    return algorithms_api.unshare_algorithm(
        client, args.uuid, args.user_name, submit=args.submit
    )


def _cmd_images_list(client: NanhuClient, args: argparse.Namespace) -> Any:
    return images_api.list_images(
        client,
        is_public=args.is_public,
        current=args.current,
        page_size=args.page_size,
        name=args.name,
    )


def _cmd_images_tags(client: NanhuClient, args: argparse.Namespace) -> Any:
    return images_api.list_image_tags(
        client,
        repository_name=args.repository_name,
        source=args.source,
        current=args.current,
        page_size=args.page_size,
    )


def _cmd_images_share(client: NanhuClient, args: argparse.Namespace) -> Any:
    return images_api.share_image(
        client,
        uuid=args.uuid,
        source=args.source,
        user_name=args.user_name,
        submit=args.submit,
    )


def _cmd_images_unshare(client: NanhuClient, args: argparse.Namespace) -> Any:
    return images_api.unshare_image(
        client,
        uuid=args.uuid,
        source=args.source,
        user_names=args.user_name,
        submit=args.submit,
    )


# ---------------------------------------------------------------------------
# seahold
# ---------------------------------------------------------------------------


def _cmd_seahold_list(client: NanhuClient, args: argparse.Namespace) -> Any:
    return seahold_api.list_seahold(
        client,
        uuid=args.uuid,
        ak=args.ak,
        status=args.status,
        page=args.page,
        page_size=args.page_size,
    )


def _cmd_seahold_create(client: NanhuClient, args: argparse.Namespace) -> Any:
    return seahold_api.create_seahold_from_config(
        client, args.config, submit=args.submit
    )


def _cmd_seahold_destroy(client: NanhuClient, args: argparse.Namespace) -> Any:
    return seahold_api.destroy_seahold(
        client,
        uuid=args.uuid,
        ak=args.ak,
        sk=args.sk,
        submit=args.submit,
    )


# ---------------------------------------------------------------------------
# parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="nanhu",
        description="Nanhu OpenAPI CLI (clusters: wuxi, x10000). Write ops dry-run unless --submit.",
    )
    parser.add_argument(
        "--cluster",
        choices=CLUSTERS,
        default=DEFAULT_CLUSTER,
        help=f"target cluster (default: {DEFAULT_CLUSTER})",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=("table", "json"),
        default="json",
        help="output format: json (full, default) or table (projected list columns)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="pretty-print JSON with indentation (default: compact)",
    )
    _add_client_flags(parser)

    sub = parser.add_subparsers(dest="group", required=True)

    # --- jobs ---
    jobs_p = sub.add_parser("jobs", help="train/deploy jobs")
    jobs_sub = jobs_p.add_subparsers(dest="action", required=True)

    p = jobs_sub.add_parser("list", help="list train or deploy jobs")
    p.add_argument("--job-type", required=True, help="AI_TRAIN or AI_ONLINE_INFERENCE_SERVICE")
    p.add_argument("--biz-type", default="DROS")
    p.add_argument("--status", default=None)
    p.add_argument("--project-id", default=None)
    p.add_argument("--current", type=int, default=None)
    p.add_argument("--page-size", type=int, default=20)
    p.set_defaults(_handler=_cmd_jobs_list)

    p = jobs_sub.add_parser("detail", help="get job detail")
    p.add_argument("--job-id", required=True)
    p.add_argument("--biz-type", default="DROS")
    p.add_argument("--job-type", default=None)
    p.set_defaults(_handler=_cmd_jobs_detail)

    p = jobs_sub.add_parser("list-all", help="list all jobs (jobListAll)")
    p.add_argument("--job-type", default=None)
    p.add_argument("--status", default=None)
    p.add_argument("--project-id", default=None)
    p.add_argument("--current", type=int, default=None)
    p.add_argument("--page-size", type=int, default=20)
    p.set_defaults(_handler=_cmd_jobs_list_all)

    p = jobs_sub.add_parser(
        "running",
        help="list running train+deploy jobs (aggregated summary)",
    )
    p.add_argument("--biz-type", default="DROS")
    p.add_argument("--status", default="running", help="status filter (case-insensitive, default running)")
    p.add_argument("--project-id", default=None)
    p.add_argument("--current", type=int, default=1)
    p.add_argument("--page-size", type=int, default=20)
    p.set_defaults(_handler=_cmd_jobs_running)

    p = jobs_sub.add_parser("stop", help="stop a job (dry-run unless --submit)")
    p.add_argument("--job-id", required=True)
    p.add_argument("--biz-type", default="DROS")
    _add_submit_flag(p)
    p.set_defaults(_handler=_cmd_jobs_stop)

    p = jobs_sub.add_parser("restart", help="restart a job unchanged (dry-run unless --submit)")
    p.add_argument("--job-id", required=True)
    p.add_argument("--biz-type", default="DROS")
    _add_submit_flag(p)
    p.set_defaults(_handler=_cmd_jobs_restart)

    p = jobs_sub.add_parser("create-train", help="create train job from YAML (dry-run unless --submit)")
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--name", default=None)
    p.add_argument("--worker-num", type=int, default=None)
    p.add_argument("--version", default="v2", choices=("v2", "v3", "2", "3"))
    p.add_argument("--biz-type", default="DROS")
    _add_submit_flag(p)
    p.set_defaults(_handler=_cmd_jobs_create_train)

    p = jobs_sub.add_parser("create-deploy", help="create deploy job from YAML (dry-run unless --submit)")
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--name", default=None)
    p.add_argument("--worker-num", type=int, default=None)
    p.add_argument("--version", default="v2", choices=("v2", "v3", "2", "3"))
    p.add_argument("--biz-type", default="DROS")
    _add_submit_flag(p)
    p.set_defaults(_handler=_cmd_jobs_create_deploy)

    p = jobs_sub.add_parser(
        "restart-deploy",
        help="restart deploy with new params (restartInferenceJob; dry-run unless --submit)",
    )
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--uuid", default=None, help="job uuid override (or set uuid in config)")
    p.add_argument("--name", default=None)
    p.add_argument("--worker-num", type=int, default=None)
    p.add_argument("--biz-type", default="DROS")
    _add_submit_flag(p)
    p.set_defaults(_handler=_cmd_jobs_restart_deploy)

    p = jobs_sub.add_parser(
        "restart-pod",
        help="restart failed deploy POD(s) (podRestart; dry-run unless --submit)",
    )
    p.add_argument("--job-id", required=True)
    p.add_argument("--pod-names", required=True, help="comma-separated failed pod names")
    _add_submit_flag(p)
    p.set_defaults(_handler=_cmd_jobs_restart_pod)

    # --- devenv ---
    devenv_p = sub.add_parser("devenv", help="JUPYTER development environments")
    devenv_sub = devenv_p.add_subparsers(dest="action", required=True)

    p = devenv_sub.add_parser("list", help="list devenv")
    p.add_argument("--status", default=None)
    p.add_argument("--project-id", default=None)
    p.add_argument("--current", type=int, default=1)
    p.add_argument("--page-size", type=int, default=20)
    p.add_argument("--biz-type", default=None)
    p.set_defaults(_handler=_cmd_devenv_list)

    p = devenv_sub.add_parser("detail", help="devenv detail")
    p.add_argument("--job-id", required=True)
    p.add_argument("--biz-type", default=None)
    p.set_defaults(_handler=_cmd_devenv_detail)

    p = devenv_sub.add_parser("create", help="create devenv from YAML (dry-run unless --submit)")
    p.add_argument("--config", type=Path, required=True)
    _add_submit_flag(p)
    p.set_defaults(_handler=_cmd_devenv_create)

    p = devenv_sub.add_parser("restart", help="restart devenv from YAML (dry-run unless --submit)")
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--uuid", default=None, help="override uuid in config")
    _add_submit_flag(p)
    p.set_defaults(_handler=_cmd_devenv_restart)

    p = devenv_sub.add_parser("save-image", help="save devenv image (dry-run unless --submit)")
    p.add_argument("--job-id", required=True)
    p.add_argument("--repository", required=True)
    p.add_argument("--tag", required=True)
    _add_submit_flag(p)
    p.set_defaults(_handler=_cmd_devenv_save_image)

    # --- pods ---
    pods_p = sub.add_parser("pods", help="task POD list and monitor")
    pods_sub = pods_p.add_subparsers(dest="action", required=True)

    p = pods_sub.add_parser("list", help="list pods (v2 getJobMetrics / v3 getJobMonitor)")
    p.add_argument("--job-id", required=True)
    p.add_argument("--version", default="v3", choices=("v2", "v3", "2", "3"))
    p.add_argument("--biz-type", default="DROS")
    p.add_argument("--run", type=int, default=None, help="restart round (v3 only)")
    p.set_defaults(_handler=_cmd_pods_list)

    p = pods_sub.add_parser(
        "monitor",
        help="job monitor snapshot; with --pod-names/--start/--end uses running-monitor",
    )
    p.add_argument("--job-id", required=True)
    p.add_argument("--biz-type", default="DROS")
    p.add_argument("--run", type=int, default=None)
    p.add_argument("--pod-names", default=None, help="comma-separated; enables running-monitor")
    p.add_argument("--start", type=int, default=None, help="unix seconds (running-monitor)")
    p.add_argument("--end", type=int, default=None, help="unix seconds (running-monitor)")
    p.add_argument("--indicator-name", default=None)
    p.add_argument("--step", type=int, default=None)
    p.set_defaults(_handler=_cmd_pods_monitor)

    # --- logs ---
    logs_p = sub.add_parser("logs", help="task logs")
    logs_sub = logs_p.add_subparsers(dest="action", required=True)

    p = logs_sub.add_parser("get", help="query log info (requires zone or known cluster map)")
    p.add_argument("--job-id", required=True)
    p.add_argument("--pod-names", required=True, help="comma-separated pod names")
    p.add_argument("--zone", default=None, help="zone header (e.g. X10000); x10000 cluster maps automatically")
    p.add_argument("--biz-type", default="DROS")
    p.add_argument("--start", type=int, default=None)
    p.add_argument("--end", type=int, default=None)
    p.add_argument("--run", type=int, default=None)
    p.set_defaults(_handler=_cmd_logs_get)

    p = logs_sub.add_parser("download", help="download log bytes; prefer --output")
    p.add_argument("--job-id", required=True)
    p.add_argument("--pod-names", required=True)
    p.add_argument("--output", "-o", type=Path, default=None)
    p.add_argument("--biz-type", default="DROS")
    p.add_argument("--start", type=int, default=None)
    p.add_argument("--end", type=int, default=None)
    p.add_argument("--run", type=int, default=None)
    p.set_defaults(_handler=_cmd_logs_download)

    p = logs_sub.add_parser("prefetch", help="time-window log volume stats (pre_fetch)")
    p.add_argument("--job-id", required=True)
    p.add_argument("--pod-names", required=True, help="comma-separated pod names")
    p.add_argument("--biz-type", default="DROS")
    p.add_argument("--start", type=int, default=None, help="window start ms")
    p.add_argument("--end", type=int, default=None, help="window end ms")
    p.add_argument("--step", default=None, help="window size in minutes (default server 30)")
    p.set_defaults(_handler=_cmd_logs_prefetch)

    # --- resources ---
    res_p = sub.add_parser("resources", help="compute specs / projects")
    res_sub = res_p.add_subparsers(dest="action", required=True)

    p = res_sub.add_parser("specs", help="list compute specs")
    p.add_argument("--resource-type", default=None)
    p.add_argument("--current", type=int, default=None)
    p.add_argument("--page-size", type=int, default=20)
    p.set_defaults(_handler=_cmd_resources_specs)

    p = res_sub.add_parser("projects", help="list projects")
    p.add_argument("--resource-type", default=None)
    p.add_argument("--current", type=int, default=None)
    p.add_argument("--page-size", type=int, default=20)
    p.set_defaults(_handler=_cmd_resources_projects)

    p = res_sub.add_parser("sub-projects", help="list available sub-projects")
    p.add_argument("--project-id", required=True)
    p.set_defaults(_handler=_cmd_resources_sub_projects)

    p = res_sub.add_parser("promotions", help="list project spot/promotion prices")
    p.add_argument("--project-id", required=True)
    p.set_defaults(_handler=_cmd_resources_promotions)

    # --- algorithms ---
    algo_p = sub.add_parser("algorithms", help="algorithm list/detail/CRUD/share")
    algo_sub = algo_p.add_subparsers(dest="action", required=True)

    p = algo_sub.add_parser("list", help="list algorithms")
    p.add_argument("--is-public", type=_parse_bool, required=True, help="true=shared/public; false=mine")
    p.add_argument("--current", type=int, default=1)
    p.add_argument("--page-size", type=int, default=20)
    p.add_argument("--name", default=None)
    p.add_argument("--uuid", default=None)
    p.set_defaults(_handler=_cmd_algorithms_list)

    p = algo_sub.add_parser("get", help="get algorithm by uuid")
    p.add_argument("--uuid", required=True)
    p.add_argument("--is-public", type=_parse_bool, required=True)
    p.set_defaults(_handler=_cmd_algorithms_get)

    p = algo_sub.add_parser("create", help="create algorithm from YAML (dry-run unless --submit)")
    p.add_argument("--config", type=Path, required=True)
    _add_submit_flag(p)
    p.set_defaults(_handler=_cmd_algorithms_create)

    p = algo_sub.add_parser("update", help="update algorithm from YAML (dry-run unless --submit)")
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--uuid", default=None, help="override uuid in config")
    _add_submit_flag(p)
    p.set_defaults(_handler=_cmd_algorithms_update)

    p = algo_sub.add_parser("delete", help="delete algorithm (dry-run unless --submit)")
    p.add_argument("--uuid", required=True)
    _add_submit_flag(p)
    p.set_defaults(_handler=_cmd_algorithms_delete)

    p = algo_sub.add_parser("publish", help="make algorithm public (dry-run unless --submit)")
    p.add_argument("--uuid", required=True)
    _add_submit_flag(p)
    p.set_defaults(_handler=_cmd_algorithms_publish)

    p = algo_sub.add_parser("unpublish", help="cancel public share (dry-run unless --submit)")
    p.add_argument("--uuid", required=True)
    _add_submit_flag(p)
    p.set_defaults(_handler=_cmd_algorithms_unpublish)

    p = algo_sub.add_parser("share", help="add share user (dry-run unless --submit)")
    p.add_argument("--uuid", required=True)
    p.add_argument("--user-name", required=True, help="target username e.g. 001254")
    _add_submit_flag(p)
    p.set_defaults(_handler=_cmd_algorithms_share)

    p = algo_sub.add_parser("unshare", help="remove share user(s) (dry-run unless --submit)")
    p.add_argument("--uuid", required=True)
    p.add_argument("--user-name", required=True, help="comma-separated usernames")
    _add_submit_flag(p)
    p.set_defaults(_handler=_cmd_algorithms_unshare)

    # --- images ---
    img_p = sub.add_parser("images", help="image list/tags/share")
    img_sub = img_p.add_subparsers(dest="action", required=True)

    p = img_sub.add_parser("list", help="list image repositories")
    p.add_argument("--is-public", type=_parse_bool, required=True)
    p.add_argument("--current", type=int, default=1)
    p.add_argument("--page-size", type=int, default=20)
    p.add_argument("--name", default=None)
    p.set_defaults(_handler=_cmd_images_list)

    p = img_sub.add_parser("tags", help="list image tags")
    p.add_argument("--repository-name", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--current", type=int, default=1)
    p.add_argument("--page-size", type=int, default=20)
    p.set_defaults(_handler=_cmd_images_tags)

    p = img_sub.add_parser("share", help="add image share user (dry-run unless --submit)")
    p.add_argument("--uuid", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--user-name", required=True)
    _add_submit_flag(p)
    p.set_defaults(_handler=_cmd_images_share)

    p = img_sub.add_parser("unshare", help="remove image share user(s) (dry-run unless --submit)")
    p.add_argument("--uuid", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--user-name", required=True, help="comma-separated usernames")
    _add_submit_flag(p)
    p.set_defaults(_handler=_cmd_images_unshare)

    # --- seahold ---
    sea_p = sub.add_parser("seahold", help="seahold private dataset PVC (Zero2X)")
    sea_sub = sea_p.add_subparsers(dest="action", required=True)

    p = sea_sub.add_parser("list", help="list seahold PVCs")
    p.add_argument("--uuid", default=None)
    p.add_argument("--ak", default=None)
    p.add_argument("--status", default=None, help="Creating|Created|Failed|Recycling")
    p.add_argument("--page", type=int, default=None)
    p.add_argument("--page-size", type=int, default=20)
    p.set_defaults(_handler=_cmd_seahold_list)

    p = sea_sub.add_parser("create", help="create seahold PVC from YAML (dry-run unless --submit)")
    p.add_argument("--config", type=Path, required=True)
    _add_submit_flag(p)
    p.set_defaults(_handler=_cmd_seahold_create)

    p = sea_sub.add_parser("destroy", help="destroy seahold PVC (dry-run unless --submit)")
    p.add_argument("--uuid", required=True)
    p.add_argument("--ak", required=True)
    p.add_argument("--sk", required=True)
    _add_submit_flag(p)
    p.set_defaults(_handler=_cmd_seahold_destroy)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler: Callable[[NanhuClient, argparse.Namespace], Any] | None = getattr(
        args, "_handler", None
    )
    if handler is None:
        parser.error("missing subcommand handler")
        return 2

    try:
        client = _build_client(args)
        result = handler(client, args)
    except (ConfigError, ValueError, RuntimeError, FileNotFoundError, OSError) as exc:
        _emit({"error": str(exc), "type": type(exc).__name__}, args)
        return 1

    _emit(result, args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
