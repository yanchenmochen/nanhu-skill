"""Thin Nanhu client facade: api_base / userId / accessToken attachment."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from nanhu.auth import TokenCache, get_access_token
from nanhu.config import Credentials, NanhuSettings, load_settings
from nanhu.http import request_json


class NanhuClient:
    """Stable entry point for Wave1 API modules.

    Holds ``api_base`` and ``user_id``, obtains / caches ``accessToken``, and
    exposes ``request(...)`` that injects the token header.
    """

    def __init__(
        self,
        api_base: str,
        *,
        user_id: str,
        app_key: str,
        app_secret: str,
        token_cache: TokenCache | None = None,
        default_headers: dict[str, str] | None = None,
    ) -> None:
        self.api_base = api_base.rstrip("/")
        self.user_id = str(user_id)
        self.app_key = app_key
        self.app_secret = app_secret
        self.token_cache = token_cache or TokenCache()
        self.default_headers = dict(default_headers or {})
        self._access_token: str | None = None

    @classmethod
    def from_settings(
        cls,
        settings: NanhuSettings,
        *,
        token_cache: TokenCache | None = None,
        cache_path: Path | None = None,
    ) -> "NanhuClient":
        cache = token_cache or TokenCache(cache_path=cache_path)
        return cls(
            settings.api_base,
            user_id=settings.user_id,
            app_key=settings.credentials.app_key,
            app_secret=settings.credentials.app_secret,
            token_cache=cache,
        )

    @classmethod
    def from_cluster(
        cls,
        cluster: str,
        *,
        clusters_path: Path | None = None,
        credentials_path: Path | None = None,
        token_cache: TokenCache | None = None,
        cache_path: Path | None = None,
    ) -> "NanhuClient":
        settings = load_settings(
            cluster,
            clusters_path=clusters_path,
            credentials_path=credentials_path,
        )
        return cls.from_settings(settings, token_cache=token_cache, cache_path=cache_path)

    @property
    def access_token(self) -> str | None:
        return self._access_token

    def ensure_token(self, *, force_refresh: bool = False) -> str:
        """Fetch or reuse accessToken and store on the client."""
        token = get_access_token(
            self.api_base,
            self.app_key,
            self.app_secret,
            cache=self.token_cache,
            force_refresh=force_refresh,
        )
        self._access_token = token
        return token

    def auth_headers(self, *, force_refresh: bool = False) -> dict[str, str]:
        """Headers including ``accessToken`` (and optional defaults)."""
        token = self.ensure_token(force_refresh=force_refresh)
        headers = dict(self.default_headers)
        headers["accessToken"] = token
        return headers

    def build_url(self, path: str, *, query: dict[str, Any] | None = None) -> str:
        """Join ``api_base`` with path; optional query string."""
        base = self.api_base
        if not path.startswith("/"):
            path = "/" + path
        url = f"{base}{path}"
        if query:
            # Drop None values; stringify the rest.
            items = {k: v for k, v in query.items() if v is not None}
            if items:
                url = f"{url}?{urlencode(items)}"
        return url

    def request(
        self,
        method: str,
        path: str,
        *,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float = 60.0,
        require_success: bool = True,
        attach_token: bool = True,
        force_refresh_token: bool = False,
    ) -> dict[str, Any]:
        """JSON request against this client's ``api_base``.

        When ``attach_token`` is True (default), injects ``accessToken``.
        Wave1 modules should prefer this method over raw ``http.request_json``.
        """
        url = self.build_url(path, query=query)
        merged = dict(self.default_headers)
        if attach_token:
            merged.update(self.auth_headers(force_refresh=force_refresh_token))
        if headers:
            merged.update(headers)
        return request_json(
            method,
            url,
            headers=merged,
            body=body,
            timeout=timeout,
            require_success=require_success,
        )
