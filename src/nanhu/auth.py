"""Nanhu OpenAPI token exchange and cache (appKey → accessToken, ~2h)."""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from nanhu.http import HttpError, http_json, parse_api_payload

# Platform tokens are typically valid for about two hours; refresh a bit early.
DEFAULT_TTL_SECONDS = 2 * 60 * 60
DEFAULT_SKEW_SECONDS = 5 * 60
DEFAULT_TOKEN_CACHE_PATH = Path.home() / ".cache" / "nanhu" / "token.json"

# Env overrides:
# - NANHU_TOKEN_CACHE / NANHU_TOKEN_CACHE_PATH: custom file path
# - NANHU_TOKEN_CACHE=0|false|off|disable|disabled|none|"" (empty with explicit disable
#   via NANHU_TOKEN_CACHE_DISABLE=1 also works): disable file persistence
_DISABLE_VALUES = frozenset({"0", "false", "off", "no", "disable", "disabled", "none", ""})

HttpJsonFn = Callable[..., Any]


def resolve_token_cache_path(
    *,
    explicit: Path | None = None,
    env: dict[str, str] | None = None,
) -> Path | None:
    """Resolve default token cache path with env overrides.

    Returns ``None`` when file cache is disabled.
    Priority: ``explicit`` → ``NANHU_TOKEN_CACHE`` / ``NANHU_TOKEN_CACHE_PATH``
    → default ``~/.cache/nanhu/token.json``.
    """
    if explicit is not None:
        return explicit
    environ = env if env is not None else os.environ
    if str(environ.get("NANHU_TOKEN_CACHE_DISABLE", "")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }:
        return None
    raw = environ.get("NANHU_TOKEN_CACHE")
    if raw is None:
        raw = environ.get("NANHU_TOKEN_CACHE_PATH")
    if raw is not None:
        value = str(raw).strip()
        if value.lower() in _DISABLE_VALUES:
            return None
        return Path(value).expanduser()
    return DEFAULT_TOKEN_CACHE_PATH



@dataclass
class TokenInfo:
    """Cached access token with absolute expiry timestamp (epoch seconds)."""

    access_token: str
    expires_at: float

    def is_valid(self, *, now: float | None = None, skew_seconds: float = DEFAULT_SKEW_SECONDS) -> bool:
        ts = time.time() if now is None else now
        return bool(self.access_token) and ts < (self.expires_at - skew_seconds)


class TokenCache:
    """In-memory token cache with optional JSON file persistence.

    When ``cache_path`` is omitted, resolves via ``resolve_token_cache_path()``
    (default ``~/.cache/nanhu/token.json`` unless disabled by env).
    """

    def __init__(
        self,
        *,
        cache_path: Path | None | object = ...,
        ttl_seconds: float = DEFAULT_TTL_SECONDS,
        skew_seconds: float = DEFAULT_SKEW_SECONDS,
    ) -> None:
        if cache_path is ...:
            resolved: Path | None = resolve_token_cache_path()
        else:
            resolved = cache_path  # type: ignore[assignment]
        self.cache_path = resolved
        self.ttl_seconds = ttl_seconds
        self.skew_seconds = skew_seconds
        self._lock = threading.Lock()
        self._mem: dict[str, TokenInfo] = {}
        if self.cache_path is not None:
            self._load_file()

    def _key(self, api_base: str, app_key: str) -> str:
        return f"{api_base.rstrip('/')}|{app_key}"

    def get(self, api_base: str, app_key: str) -> TokenInfo | None:
        key = self._key(api_base, app_key)
        with self._lock:
            info = self._mem.get(key)
            if info and info.is_valid(skew_seconds=self.skew_seconds):
                return info
            if info:
                self._mem.pop(key, None)
            return None

    def put(self, api_base: str, app_key: str, access_token: str, *, expires_at: float | None = None) -> TokenInfo:
        info = TokenInfo(
            access_token=access_token,
            expires_at=expires_at if expires_at is not None else time.time() + self.ttl_seconds,
        )
        key = self._key(api_base, app_key)
        with self._lock:
            self._mem[key] = info
            self._save_file_unlocked()
        return info

    def clear(self, api_base: str | None = None, app_key: str | None = None) -> None:
        with self._lock:
            if api_base is None and app_key is None:
                self._mem.clear()
            elif api_base is not None and app_key is not None:
                self._mem.pop(self._key(api_base, app_key), None)
            else:
                prefix = f"{(api_base or '').rstrip('/')}|" if api_base else None
                drop = [
                    k
                    for k in self._mem
                    if (prefix and k.startswith(prefix)) or (app_key and k.endswith(f"|{app_key}"))
                ]
                for k in drop:
                    self._mem.pop(k, None)
            self._save_file_unlocked()

    def _load_file(self) -> None:
        path = self.cache_path
        if path is None or not path.is_file():
            return
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(raw, dict):
            return
        now = time.time()
        for key, meta in raw.items():
            if not isinstance(meta, dict):
                continue
            token = str(meta.get("access_token") or "")
            expires_at = float(meta.get("expires_at") or 0)
            info = TokenInfo(access_token=token, expires_at=expires_at)
            if info.is_valid(now=now, skew_seconds=self.skew_seconds):
                self._mem[str(key)] = info

    def _save_file_unlocked(self) -> None:
        path = self.cache_path
        if path is None:
            return
        payload = {
            key: {"access_token": info.access_token, "expires_at": info.expires_at}
            for key, info in self._mem.items()
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def fetch_access_token(
    api_base: str,
    app_key: str,
    app_secret: str,
    *,
    http_json_fn: HttpJsonFn | None = None,
    timeout: float = 60.0,
) -> str:
    """POST ``/api/open/credentials`` with appKey/appSecret; return accessToken."""
    do_http = http_json_fn or http_json
    url = f"{api_base.rstrip('/')}/api/open/credentials"
    response = do_http(
        "POST",
        url,
        body={"appKey": app_key, "appSecret": app_secret},
        timeout=timeout,
    )
    # http_json returns HttpResponse; allow plain (status, dict) for tests.
    if hasattr(response, "payload"):
        payload = parse_api_payload(response, require_success=True)
        http_status = response.status
    else:
        http_status, payload = response  # type: ignore[misc]
        from nanhu.http import HttpResponse as _HR

        payload = parse_api_payload(_HR(status=int(http_status), payload=payload), require_success=True)

    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    token = data.get("accessToken") if isinstance(data, dict) else None
    if not token:
        raise HttpError(
            f"failed to get accessToken (http={http_status}): {payload}",
            status=http_status,
            body=payload,
        )
    return str(token)


def get_access_token(
    api_base: str,
    app_key: str,
    app_secret: str,
    *,
    cache: TokenCache | None = None,
    force_refresh: bool = False,
    http_json_fn: HttpJsonFn | None = None,
    timeout: float = 60.0,
) -> str:
    """Return a valid accessToken, using ``cache`` when available."""
    store = cache or TokenCache()
    if not force_refresh:
        cached = store.get(api_base, app_key)
        if cached is not None:
            return cached.access_token
    token = fetch_access_token(
        api_base,
        app_key,
        app_secret,
        http_json_fn=http_json_fn,
        timeout=timeout,
    )
    store.put(api_base, app_key, token)
    return token
