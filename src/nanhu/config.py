"""Cluster and credential loading for Nanhu OpenAPI clients."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

# Repo layout: <repo>/src/nanhu/config.py → parents[2] == <repo>
_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CLUSTERS_PATH = _REPO_ROOT / "config" / "clusters.yaml"
DEFAULT_CREDENTIALS_PATH = _REPO_ROOT / "config" / "credentials.env"

ENV_APP_KEY = "NANHU_APP_KEY"
ENV_APP_SECRET = "NANHU_APP_SECRET"
ENV_USER_ID = "NANHU_USER_ID"
ENV_API_BASE = "NANHU_API_BASE"


@dataclass(frozen=True)
class ClusterConfig:
    """Named Nanhu control-plane endpoint."""

    name: str
    api_base: str


@dataclass(frozen=True)
class Credentials:
    """OpenAPI app credentials (env overrides file values)."""

    app_key: str
    app_secret: str
    user_id: str


@dataclass(frozen=True)
class NanhuSettings:
    """Resolved settings for one cluster + credentials."""

    cluster: ClusterConfig
    credentials: Credentials

    @property
    def api_base(self) -> str:
        return self.cluster.api_base

    @property
    def user_id(self) -> str:
        return self.credentials.user_id


class ConfigError(ValueError):
    """Invalid or incomplete Nanhu configuration."""


def load_env_file(path: Path) -> dict[str, str]:
    """Parse a simple KEY=VALUE env file (supports optional ``export`` prefix)."""
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        key, _, val = line.partition("=")
        out[key.strip()] = val.strip().strip("\"'")
    return out


def load_clusters(path: Path | None = None) -> dict[str, ClusterConfig]:
    """Load ``clusters.yaml``; return mapping of cluster name → config."""
    clusters_path = path or DEFAULT_CLUSTERS_PATH
    if not clusters_path.is_file():
        raise ConfigError(f"clusters file not found: {clusters_path}")
    raw = yaml.safe_load(clusters_path.read_text(encoding="utf-8")) or {}
    section = raw.get("clusters") if isinstance(raw, dict) else None
    if not isinstance(section, dict) or not section:
        raise ConfigError(f"no clusters defined in {clusters_path}")

    result: dict[str, ClusterConfig] = {}
    for name, meta in section.items():
        if not isinstance(meta, dict):
            raise ConfigError(f"cluster {name!r} must be a mapping")
        api_base = str(meta.get("api_base") or "").strip().rstrip("/")
        if not api_base:
            raise ConfigError(f"cluster {name!r} missing api_base")
        result[str(name)] = ClusterConfig(name=str(name), api_base=api_base)
    return result


def get_cluster(name: str, *, clusters_path: Path | None = None) -> ClusterConfig:
    """Return one cluster by name."""
    clusters = load_clusters(clusters_path)
    if name not in clusters:
        known = ", ".join(sorted(clusters))
        raise ConfigError(f"unknown cluster {name!r}; known: {known}")
    return clusters[name]


def _credentials_candidates(
    cluster: str | None,
    credentials_path: Path | None,
) -> list[Path]:
    """Ordered credential file candidates (most specific first)."""
    if credentials_path is not None:
        return [credentials_path]
    base = DEFAULT_CREDENTIALS_PATH
    candidates: list[Path] = []
    if cluster:
        # config/credentials.<cluster>.env then config/credentials.env
        candidates.append(base.with_name(f"credentials.{cluster}.env"))
    candidates.append(base)
    return candidates


def load_credentials(
    *,
    cluster: str | None = None,
    credentials_path: Path | None = None,
    require: bool = True,
) -> Credentials:
    """Load credentials from file + env overrides.

    Precedence (highest last / wins): file → process environment
    (``NANHU_APP_KEY`` / ``NANHU_APP_SECRET`` / ``NANHU_USER_ID``).
    """
    file_vals: dict[str, str] = {}
    used_path: Path | None = None
    for candidate in _credentials_candidates(cluster, credentials_path):
        if candidate.is_file():
            file_vals = load_env_file(candidate)
            used_path = candidate
            break

    app_key = (os.environ.get(ENV_APP_KEY) or file_vals.get(ENV_APP_KEY) or "").strip()
    app_secret = (os.environ.get(ENV_APP_SECRET) or file_vals.get(ENV_APP_SECRET) or "").strip()
    user_id = (os.environ.get(ENV_USER_ID) or file_vals.get(ENV_USER_ID) or "").strip()

    if require:
        missing: list[str] = []
        if not app_key:
            missing.append(ENV_APP_KEY)
        if not app_secret:
            missing.append(ENV_APP_SECRET)
        if not user_id:
            missing.append(ENV_USER_ID)
        if missing:
            hint = str(used_path) if used_path else str(DEFAULT_CREDENTIALS_PATH)
            raise ConfigError(
                f"missing {', '.join(missing)} — set in {hint} or the environment"
            )

    return Credentials(app_key=app_key, app_secret=app_secret, user_id=user_id)


def load_settings(
    cluster: str,
    *,
    clusters_path: Path | None = None,
    credentials_path: Path | None = None,
) -> NanhuSettings:
    """Resolve cluster endpoint + credentials for CLI / client factory."""
    cluster_cfg = get_cluster(cluster, clusters_path=clusters_path)
    # Optional NANHU_API_BASE override (useful for staging / tunnels).
    api_override = (os.environ.get(ENV_API_BASE) or "").strip().rstrip("/")
    if api_override:
        cluster_cfg = ClusterConfig(name=cluster_cfg.name, api_base=api_override)
    creds = load_credentials(cluster=cluster, credentials_path=credentials_path)
    return NanhuSettings(cluster=cluster_cfg, credentials=creds)


def as_dict(settings: NanhuSettings) -> dict[str, Any]:
    """Serialize settings for dry-run / debug (never includes secrets in full)."""
    return {
        "cluster": settings.cluster.name,
        "api_base": settings.api_base,
        "user_id": settings.user_id,
        "app_key_set": bool(settings.credentials.app_key),
        "app_secret_set": bool(settings.credentials.app_secret),
    }
