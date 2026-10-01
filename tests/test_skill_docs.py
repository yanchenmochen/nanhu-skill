"""Lightweight checks that Skill / reference docs keep critical agent guidance."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_skill_has_high_freq_recipes_and_reply_templates() -> None:
    text = _read("SKILL.md")
    assert "jobs running" in text
    assert "--format table" in text
    assert "对人回复模板" in text
    assert "OUTPUT_DIR/run.log" in text or "OUTPUT_DIR" in text and "run.log" in text
    assert "references/workflows.md" in text
    assert "references/pitfalls.md" in text


def test_workflows_has_run_log_fallback() -> None:
    text = _read("references/workflows.md")
    assert "run.log" in text
    assert "OUTPUT_DIR" in text
    assert "--status running" in text or "status running" in text


def test_pitfalls_mentions_hint_and_token_cache() -> None:
    text = _read("references/pitfalls.md")
    assert "hint" in text
    assert "token.json" in text or "NANHU_TOKEN_CACHE" in text
    assert "run.log" in text
