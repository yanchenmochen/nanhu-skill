"""CLI output helpers: secret redaction, list projection, table formatting."""

from __future__ import annotations

from datetime import datetime
from typing import Any

# Fixed projection for ``--format table`` list views.
LIST_TABLE_FIELDS: tuple[str, ...] = (
    "name",
    "uuid",
    "status",
    "jobDuration",
    "createDate",
    "computeSpecName",
    "workerNum",
)

# Password-like keys redacted in all output formats.
_SECRET_KEYS = frozenset(
    {
        "sshPwd",
        "ssh_pwd",
        "jupyterPwd",
        "jupyter_pwd",
        "password",
        "passwd",
        "pwd",
    }
)
_REDACTED = "***"


def format_create_date(value: Any) -> str:
    """Convert ms/s epoch (or leave strings) to ``YYYY-MM-DD HH:MM``."""
    if value is None or value == "":
        return "-"
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        ts = float(value)
        # Heuristic: values > 1e12 are milliseconds.
        if ts > 1e12:
            ts = ts / 1000.0
        try:
            return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
        except (OverflowError, OSError, ValueError):
            return str(value)
    return str(value)


def redact_secrets(obj: Any) -> Any:
    """Deep-copy-like walk that replaces known password fields with ``***``."""
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for key, value in obj.items():
            if key in _SECRET_KEYS and value is not None and value != "":
                out[key] = _REDACTED
            else:
                out[key] = redact_secrets(value)
        return out
    if isinstance(obj, list):
        return [redact_secrets(item) for item in obj]
    return obj


def _dig(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row and row[key] is not None:
            return row[key]
    resource = row.get("resource")
    if isinstance(resource, dict):
        for key in keys:
            if key in resource and resource[key] is not None:
                return resource[key]
    return None


def extract_list_rows(payload: Any) -> list[dict[str, Any]] | None:
    """Pull list rows from common Nanhu list envelopes; None if not list-shaped."""
    if isinstance(payload, list):
        return [r for r in payload if isinstance(r, dict)]
    if not isinstance(payload, dict):
        return None
    # Dry-run / error / detail-shaped payloads are not list views.
    if payload.get("dry_run") is True or "error" in payload:
        return None
    data = payload.get("data", payload)
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict):
        for key in ("result", "records", "list", "jobs", "items"):
            rows = data.get(key)
            if isinstance(rows, list):
                return [r for r in rows if isinstance(r, dict)]
        # Single resource object (detail) — not a list.
        if any(k in data for k in ("uuid", "jobId", "name", "status")):
            return None
    return None


def project_list_row(row: dict[str, Any]) -> dict[str, Any]:
    """Project one job/devenv-like row to the fixed table columns."""
    uuid = _dig(row, "uuid", "jobId", "id")
    create_raw = _dig(row, "createDate", "createTime", "createdAt")
    return {
        "name": _dig(row, "name") or "-",
        "uuid": uuid if uuid is not None else "-",
        "status": _dig(row, "status") or "-",
        "jobDuration": _dig(row, "jobDuration", "duration") or "-",
        "createDate": format_create_date(create_raw),
        "computeSpecName": _dig(row, "computeSpecName", "specName") or "-",
        "workerNum": _dig(row, "workerNum", "worker_num"),
    }


def project_list_payload(payload: Any) -> list[dict[str, Any]] | None:
    rows = extract_list_rows(payload)
    if rows is None:
        return None
    return [project_list_row(r) for r in rows]


def format_table(rows: list[dict[str, Any]], *, fields: tuple[str, ...] = LIST_TABLE_FIELDS) -> str:
    """Render projected rows as an aligned plain-text table."""
    headers = list(fields)
    if not rows:
        header_line = "  ".join(headers)
        return f"{header_line}\n(no rows)\n"

    str_rows: list[list[str]] = []
    for row in rows:
        str_rows.append([("-" if row.get(f) is None else str(row.get(f))) for f in fields])

    widths = [len(h) for h in headers]
    for row in str_rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def fmt_line(cells: list[str]) -> str:
        return "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(cells))

    lines = [fmt_line(headers), fmt_line(["-" * w for w in widths])]
    lines.extend(fmt_line(r) for r in str_rows)
    return "\n".join(lines) + "\n"


def should_use_table(payload: Any, fmt: str) -> bool:
    """True when ``fmt`` is table and ``payload`` looks like a list response."""
    return (fmt or "json").strip().lower() == "table" and project_list_payload(payload) is not None
