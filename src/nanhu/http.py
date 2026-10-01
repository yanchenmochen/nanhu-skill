"""HTTP helpers for Nanhu OpenAPI (private 10.x hosts bypass system proxy)."""

from __future__ import annotations

import ipaddress
import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


SUCCESS_CODES = frozenset({"0", "200"})


class HttpError(RuntimeError):
    """Transport or non-JSON HTTP failure."""

    def __init__(self, message: str, *, status: int | None = None, body: Any = None) -> None:
        super().__init__(message)
        self.status = status
        self.body = body


class ApiError(RuntimeError):
    """Nanhu business response with unsuccessful ``code``."""

    def __init__(
        self,
        message: str,
        *,
        code: Any = None,
        payload: dict[str, Any] | None = None,
        http_status: int | None = None,
        url: str | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.payload = payload or {}
        self.http_status = http_status
        self.url = url


@dataclass(frozen=True)
class HttpResponse:
    """Raw HTTP result before business-code interpretation."""

    status: int
    payload: dict[str, Any]


def is_private_api_host(url: str) -> bool:
    """True when URL hostname is a private IP (e.g. 10.x Nanhu control planes)."""
    host = urllib.parse.urlparse(url).hostname
    try:
        return bool(host and ipaddress.ip_address(host).is_private)
    except ValueError:
        return False


def _open_url(req: urllib.request.Request, *, timeout: float, private_host: bool):
    # urllib's proxy matcher does not consistently honor CIDR NO_PROXY entries
    # such as 10.0.0.0/8; inherited workstation proxies can turn a valid POST
    # into a gateway 405. Bypass proxies for private API hosts.
    if private_host:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        return opener.open(req, timeout=timeout)
    return urllib.request.urlopen(req, timeout=timeout)


def http_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout: float = 60.0,
) -> HttpResponse:
    """Send a JSON request and return ``(http_status, payload_dict)``.

    Always sets ``Content-Type: application/json``. Private IP hosts use an
    empty ProxyHandler so system HTTP(S)_PROXY is ignored.
    """
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method.upper())
    req.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        req.add_header(key, value)

    private_host = is_private_api_host(url)
    try:
        with _open_url(req, timeout=timeout, private_host=private_host) as resp:
            raw = resp.read().decode()
            status = resp.getcode()
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode() if exc.fp else ""
        status = int(exc.code)
    except urllib.error.URLError as exc:
        raise HttpError(f"HTTP {method.upper()} {url} failed: {exc}") from exc

    try:
        parsed: Any = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        parsed = {"raw": raw}
    if not isinstance(parsed, dict):
        parsed = {"data": parsed}
    return HttpResponse(status=status, payload=parsed)


def is_success_code(code: Any) -> bool:
    """Nanhu variants: code 0 / \"0\" / 200 / \"200\"."""
    return str(code) in SUCCESS_CODES


def parse_api_payload(
    response: HttpResponse,
    *,
    require_success: bool = True,
    url: str | None = None,
) -> dict[str, Any]:
    """Interpret Nanhu envelope ``{code, data, message?, msg?}``.

    When ``require_success`` is True, raises ``ApiError`` unless ``code`` is
    success (0/200). Returns the full payload dict on success (or always when
    ``require_success`` is False).
    """
    payload = response.payload
    code = payload.get("code")
    if require_success and not is_success_code(code):
        msg = (
            payload.get("message")
            or payload.get("msg")
            or payload.get("error")
            or f"Nanhu API error code={code!r}"
        )
        raise ApiError(
            str(msg),
            code=code,
            payload=payload,
            http_status=response.status,
            url=url,
        )
    return payload


# Path fragments that are known-missing / flaky on wuxi (often HTTP 404).
_WUXI_CAPABILITY_HINTS: tuple[tuple[str, str], ...] = (
    (
        "/dev-env/list",
        "wuxi 常不支持开发环境列表 (dev-env/list)；请改用平台 UI，或切换 --cluster x10000",
    ),
    (
        "/dev-env/",
        "wuxi 上部分开发环境接口可能不可用；可改用平台 UI 或 --cluster x10000",
    ),
    (
        "/open-job/images",
        "wuxi 常不支持镜像列表/标签接口；请改用平台 UI，或切换 --cluster x10000",
    ),
    (
        "jobListAll",
        "wuxi 上 jobListAll 可能 404；请改用 jobs list --job-type AI_TRAIN|AI_ONLINE_INFERENCE_SERVICE",
    ),
    (
        "/log/",
        "wuxi 查日志常缺 zone 或接口失败；可显式传 --zone，或从 jobs detail 取 OUTPUT_DIR 读本地 run.log",
    ),
)


def hint_for_error(
    exc: BaseException,
    *,
    cluster: str | None = None,
) -> str | None:
    """Return an actionable hint for known cluster capability gaps, else None."""
    cluster_norm = (cluster or "").strip().lower()
    url = getattr(exc, "url", None) or ""
    text = f"{url} {exc}"
    http_status = getattr(exc, "http_status", None)
    # Also inspect HttpError.status
    if http_status is None:
        http_status = getattr(exc, "status", None)

    if cluster_norm == "wuxi":
        for fragment, hint in _WUXI_CAPABILITY_HINTS:
            if fragment in text or fragment in url:
                return hint
        if http_status == 404:
            return (
                "该接口在 wuxi 上可能不可用 (HTTP 404)；"
                "请对照 references/pitfalls.md，或改用 --cluster x10000 / 平台 UI"
            )
    return None


def request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout: float = 60.0,
    require_success: bool = True,
) -> dict[str, Any]:
    """Convenience: ``http_json`` + ``parse_api_payload``."""
    resp = http_json(method, url, headers=headers, body=body, timeout=timeout)
    return parse_api_payload(resp, require_success=require_success, url=url)
