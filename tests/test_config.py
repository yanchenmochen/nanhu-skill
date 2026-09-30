"""Tests for nanhu.config — clusters + credentials loading."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from nanhu.config import (
    ConfigError,
    get_cluster,
    load_clusters,
    load_credentials,
    load_env_file,
    load_settings,
)


@pytest.fixture()
def clusters_file(tmp_path: Path) -> Path:
    path = tmp_path / "clusters.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "clusters": {
                    "wuxi": {"api_base": "http://10.124.120.108:38080"},
                    "x10000": {"api_base": "http://10.202.32.189:38080/"},
                }
            }
        ),
        encoding="utf-8",
    )
    return path


def test_load_clusters_wuxi_and_x10000(clusters_file: Path) -> None:
    clusters = load_clusters(clusters_file)
    assert set(clusters) == {"wuxi", "x10000"}
    assert clusters["wuxi"].api_base == "http://10.124.120.108:38080"
    # trailing slash stripped
    assert clusters["x10000"].api_base == "http://10.202.32.189:38080"


def test_get_cluster_unknown_raises(clusters_file: Path) -> None:
    with pytest.raises(ConfigError, match="unknown cluster"):
        get_cluster("z1120", clusters_path=clusters_file)


def test_load_env_file_parses_export_and_quotes(tmp_path: Path) -> None:
    path = tmp_path / "creds.env"
    path.write_text(
        'export NANHU_APP_KEY="key1"\n'
        "NANHU_APP_SECRET='sec2'\n"
        "# comment\n"
        "NANHU_USER_ID=uid3\n",
        encoding="utf-8",
    )
    vals = load_env_file(path)
    assert vals["NANHU_APP_KEY"] == "key1"
    assert vals["NANHU_APP_SECRET"] == "sec2"
    assert vals["NANHU_USER_ID"] == "uid3"


def test_load_credentials_from_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("NANHU_APP_KEY", "NANHU_APP_SECRET", "NANHU_USER_ID"):
        monkeypatch.delenv(key, raising=False)
    path = tmp_path / "credentials.env"
    path.write_text(
        "NANHU_APP_KEY=file-key\nNANHU_APP_SECRET=file-secret\nNANHU_USER_ID=file-uid\n",
        encoding="utf-8",
    )
    creds = load_credentials(credentials_path=path)
    assert creds.app_key == "file-key"
    assert creds.app_secret == "file-secret"
    assert creds.user_id == "file-uid"


def test_env_overrides_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "credentials.env"
    path.write_text(
        "NANHU_APP_KEY=file-key\nNANHU_APP_SECRET=file-secret\nNANHU_USER_ID=file-uid\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("NANHU_APP_KEY", "env-key")
    monkeypatch.setenv("NANHU_APP_SECRET", "env-secret")
    monkeypatch.setenv("NANHU_USER_ID", "env-uid")
    creds = load_credentials(credentials_path=path)
    assert creds.app_key == "env-key"
    assert creds.app_secret == "env-secret"
    assert creds.user_id == "env-uid"


def test_missing_credentials_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("NANHU_APP_KEY", "NANHU_APP_SECRET", "NANHU_USER_ID"):
        monkeypatch.delenv(key, raising=False)
    path = tmp_path / "empty.env"
    path.write_text("# empty\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="NANHU_APP_KEY"):
        load_credentials(credentials_path=path)


def test_load_settings_combines(clusters_file: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ("NANHU_APP_KEY", "NANHU_APP_SECRET", "NANHU_USER_ID", "NANHU_API_BASE"):
        monkeypatch.delenv(key, raising=False)
    creds_path = tmp_path / "credentials.env"
    creds_path.write_text(
        "NANHU_APP_KEY=k\nNANHU_APP_SECRET=s\nNANHU_USER_ID=u\n",
        encoding="utf-8",
    )
    settings = load_settings(
        "wuxi",
        clusters_path=clusters_file,
        credentials_path=creds_path,
    )
    assert settings.cluster.name == "wuxi"
    assert settings.api_base == "http://10.124.120.108:38080"
    assert settings.user_id == "u"


def test_api_base_env_override(clusters_file: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NANHU_API_BASE", "http://127.0.0.1:9")
    monkeypatch.setenv("NANHU_APP_KEY", "k")
    monkeypatch.setenv("NANHU_APP_SECRET", "s")
    monkeypatch.setenv("NANHU_USER_ID", "u")
    settings = load_settings(
        "x10000",
        clusters_path=clusters_file,
        credentials_path=tmp_path / "missing.env",
    )
    assert settings.api_base == "http://127.0.0.1:9"


def test_bundled_clusters_yaml_exists() -> None:
    """Repo default clusters.yaml must list only wuxi + x10000."""
    from nanhu.config import DEFAULT_CLUSTERS_PATH, load_clusters

    assert DEFAULT_CLUSTERS_PATH.is_file()
    clusters = load_clusters()
    assert set(clusters) == {"wuxi", "x10000"}
    assert clusters["wuxi"].api_base == "http://10.124.120.108:38080"
    assert clusters["x10000"].api_base == "http://10.202.32.189:38080"
