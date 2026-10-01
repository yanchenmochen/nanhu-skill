"""Tests for nanhu.formatters (projection, table, secret redaction)."""

from __future__ import annotations

from nanhu.formatters import (
    LIST_TABLE_FIELDS,
    extract_list_rows,
    format_create_date,
    format_table,
    project_list_payload,
    project_list_row,
    redact_secrets,
    should_use_table,
)


def test_format_create_date_ms_epoch() -> None:
    # 2024-01-15 00:00:00 UTC+8 roughly — just check shape
    text = format_create_date(1_705_248_000_000)
    assert len(text) == 16
    assert text[4] == "-" and text[10] == " "


def test_format_create_date_passthrough_str() -> None:
    assert format_create_date("already") == "already"
    assert format_create_date(None) == "-"


def test_redact_secrets_nested_login_info() -> None:
    payload = {
        "code": 0,
        "data": {
            "result": [
                {
                    "name": "job-a",
                    "loginInfo": {"sshPwd": "Secret123!", "user": "root"},
                    "jupyterPwd": "jpwd",
                }
            ]
        },
    }
    out = redact_secrets(payload)
    row = out["data"]["result"][0]
    assert row["loginInfo"]["sshPwd"] == "***"
    assert row["loginInfo"]["user"] == "root"
    assert row["jupyterPwd"] == "***"
    # original untouched
    assert payload["data"]["result"][0]["loginInfo"]["sshPwd"] == "Secret123!"


def test_extract_and_project_list() -> None:
    payload = {
        "code": 0,
        "data": {
            "page": {"total": 1},
            "result": [
                {
                    "name": "demo",
                    "uuid": "jb-1",
                    "status": "running",
                    "jobDuration": "1h",
                    "createDate": 1_705_248_000_000,
                    "resource": {"computeSpecName": "A100", "workerNum": 2},
                    "startCmd": "long...",
                    "loginInfo": {"sshPwd": "x"},
                }
            ],
        },
    }
    rows = extract_list_rows(payload)
    assert rows is not None and len(rows) == 1
    projected = project_list_row(rows[0])
    assert set(projected) == set(LIST_TABLE_FIELDS)
    assert projected["name"] == "demo"
    assert projected["uuid"] == "jb-1"
    assert projected["computeSpecName"] == "A100"
    assert projected["workerNum"] == 2
    assert projected["createDate"] != str(1_705_248_000_000)
    assert "startCmd" not in projected


def test_project_list_payload_none_for_detail() -> None:
    assert project_list_payload({"code": 0, "data": {"uuid": "jb-1", "status": "running"}}) is None
    assert project_list_payload({"dry_run": True, "path": "/x"}) is None
    assert project_list_payload({"error": "boom", "type": "ApiError"}) is None


def test_format_table_empty() -> None:
    text = format_table([])
    assert "name" in text
    assert "(no rows)" in text


def test_format_table_rows() -> None:
    rows = [
        {
            "name": "a",
            "uuid": "u1",
            "status": "running",
            "jobDuration": "1h",
            "createDate": "2024-01-01 00:00",
            "computeSpecName": "spec",
            "workerNum": 1,
        }
    ]
    text = format_table(rows)
    assert "running" in text
    assert "u1" in text
    assert text.startswith("name")


def test_should_use_table() -> None:
    list_payload = {"data": {"result": [{"name": "x", "uuid": "1"}]}}
    assert should_use_table(list_payload, "table") is True
    assert should_use_table(list_payload, "json") is False
    assert should_use_table({"data": {"uuid": "1"}}, "table") is False
