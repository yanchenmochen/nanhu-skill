"""任务日志查询与下载。

- 查询：``GET /api/open/job-service/log/info``（必填 ``zone`` header）
- 下载：``GET /api/open/job-service/log/download``（薄封装，返回原始字节）
"""

from __future__ import annotations

import ipaddress
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Sequence

from nanhu.client import NanhuClient

DEFAULT_BIZ_TYPE = "DROS"

PATH_LOG_INFO = "/api/open/job-service/log/info"
PATH_LOG_DOWNLOAD = "/api/open/job-service/log/download"
PATH_LOG_PREFETCH = "/api/open/job-service/log/pre_fetch"

# Apifox enum for log/info ``zone`` header.
KNOWN_ZONES = frozenset({"Z2120", "Z1120", "V5000", "X10000"})

# Best-effort map from nanhu-skill cluster name → zone header.
CLUSTER_ZONE_MAP = {
    "x10000": "X10000",
}


def resolve_zone(zone: str | None = None, *, cluster: str | None = None) -> str:
    """Resolve zone header value; raise if neither ``zone`` nor known ``cluster``."""
    if zone is not None and str(zone).strip():
        return str(zone).strip()
    if cluster is not None:
        mapped = CLUSTER_ZONE_MAP.get(str(cluster).strip().lower())
        if mapped:
            return mapped
    raise ValueError(
        "zone is required for log/info "
        f"(known: {sorted(KNOWN_ZONES)}; cluster map: {sorted(CLUSTER_ZONE_MAP)})"
    )


def _pod_names_param(job_pod_names: str | Sequence[str]) -> str:
    if isinstance(job_pod_names, str):
        return job_pod_names
    return ",".join(str(n) for n in job_pod_names)


def _log_query(
    job_id: str,
    job_pod_names: str | Sequence[str],
    *,
    biz_type: str = DEFAULT_BIZ_TYPE,
    start: int | None = None,
    end: int | None = None,
    run: int | None = None,
) -> dict[str, Any]:
    query: dict[str, Any] = {
        "jobId": job_id,
        "jobPodNames": _pod_names_param(job_pod_names),
        "bizType": biz_type,
    }
    if start is not None:
        query["start"] = start
    if end is not None:
        query["end"] = end
    if run is not None:
        query["run"] = run
    return query


def get_log_info(
    client: NanhuClient,
    job_id: str,
    job_pod_names: str | Sequence[str],
    *,
    zone: str | None = None,
    cluster: str | None = None,
    biz_type: str = DEFAULT_BIZ_TYPE,
    start: int | None = None,
    end: int | None = None,
    run: int | None = None,
) -> dict[str, Any]:
    """查询任务日志（GET .../log/info）。

    必须提供 ``zone``，或可通过 ``cluster``（如 ``x10000``）映射到 zone。
    """
    zone_value = resolve_zone(zone, cluster=cluster)
    return client.request(
        "GET",
        PATH_LOG_INFO,
        query=_log_query(
            job_id,
            job_pod_names,
            biz_type=biz_type,
            start=start,
            end=end,
            run=run,
        ),
        headers={"zone": zone_value},
    )


def prefetch_log(
    client: NanhuClient,
    job_id: str,
    job_pod_names: str | Sequence[str],
    *,
    biz_type: str = DEFAULT_BIZ_TYPE,
    start: int | None = None,
    end: int | None = None,
    step: int | str | None = None,
    user_id: str | None = None,
) -> dict[str, Any]:
    """查询时间窗口日志量统计（GET .../log/pre_fetch）。

    ``step`` 为窗口跨度（分钟，最小 1；不传则服务端默认 30）。
    不要求 ``zone`` header（与 Apifox 一致）。
    """
    query = _log_query(
        job_id,
        job_pod_names,
        biz_type=biz_type,
        start=start,
        end=end,
    )
    query["userId"] = user_id or client.user_id
    if step is not None:
        query["step"] = step
    return client.request("GET", PATH_LOG_PREFETCH, query=query)


def _is_private_host(url: str) -> bool:
    host = urllib.parse.urlparse(url).hostname
    try:
        return bool(host and ipaddress.ip_address(host).is_private)
    except ValueError:
        return False


def _http_bytes(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 120.0,
) -> tuple[int, bytes]:
    """GET/POST raw bytes with private-host proxy bypass (download is not JSON)."""
    req = urllib.request.Request(url, method=method.upper())
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    private = _is_private_host(url)
    try:
        if private:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            resp_ctx = opener.open(req, timeout=timeout)
        else:
            resp_ctx = urllib.request.urlopen(req, timeout=timeout)
        with resp_ctx as resp:
            return int(resp.getcode()), resp.read()
    except urllib.error.HTTPError as exc:
        raw = exc.read() if exc.fp else b""
        return int(exc.code), raw


def download_log(
    client: NanhuClient,
    job_id: str,
    job_pod_names: str | Sequence[str],
    *,
    dest_path: str | Path | None = None,
    biz_type: str = DEFAULT_BIZ_TYPE,
    start: int | None = None,
    end: int | None = None,
    run: int | None = None,
    timeout: float = 120.0,
) -> bytes:
    """下载任务日志（GET .../log/download）。

    返回原始响应字节；若提供 ``dest_path`` 则同时写入文件。
    不强制 ``zone`` header（与 Apifox 下载接口一致）。
    """
    url = client.build_url(
        PATH_LOG_DOWNLOAD,
        query=_log_query(
            job_id,
            job_pod_names,
            biz_type=biz_type,
            start=start,
            end=end,
            run=run,
        ),
    )
    headers = client.auth_headers()
    status, raw = _http_bytes("GET", url, headers=headers, timeout=timeout)
    if status >= 400:
        raise RuntimeError(f"download log HTTP {status}: {raw[:200]!r}")
    if dest_path is not None:
        path = Path(dest_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return raw
