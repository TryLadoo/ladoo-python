from __future__ import annotations

import asyncio
import email.utils
import json as jsonlib
import keyword
import logging
import os
import platform
import random
import time
import uuid
from datetime import datetime, timezone
from types import TracebackType
from typing import Any, Mapping, Optional, Tuple, Union, cast

import httpx

from ._exceptions import APIConnectionError, APIError, APITimeoutError, LadooError, make_status_error
from ._pagination import AsyncCursorPage, AsyncPaginator, SyncCursorPage
from ._types import RequestOptions, Timeout
from ._version import API_VERSION, __version__
from .resources import AsyncNamespaces, SyncNamespaces

__all__ = ["DEFAULT_BASE_URL", "DEFAULT_MAX_RETRIES", "DEFAULT_TIMEOUT", "AsyncLadoo", "Ladoo"]

log = logging.getLogger("ladoo")

DEFAULT_BASE_URL = "https://api.tryladoo.com"
DEFAULT_TIMEOUT = httpx.Timeout(60.0, connect=10.0)
DEFAULT_MAX_RETRIES = 2

MAX_RETRY_AFTER = 60.0
"""Longest ``Retry-After`` the client waits out. A longer one raises instead."""

_USER_AGENT = f"ladoo-python/{__version__} (Python {platform.python_version()})"


class _NotGiven:
    def __repr__(self) -> str:
        return "NOT_GIVEN"


_NOT_GIVEN: Any = _NotGiven()


def _api_name(key: str) -> str:
    """``from_`` in Python is ``from`` on the wire."""
    if key.endswith("_") and keyword.iskeyword(key[:-1]):
        return key[:-1]
    return key


def _query_value(value: object) -> object:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise ValueError(f"{value!r} has no time zone. Pass an aware datetime, e.g. datetime.now(timezone.utc).")
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return value


class _BaseClient:
    api_key: str
    api_version: str
    base_url: str
    max_retries: int
    timeout: Timeout

    def __init__(
        self,
        *,
        api_key: Optional[str],
        api_version: str,
        base_url: Optional[str],
        max_retries: int,
        timeout: Timeout,
        default_headers: Optional[Mapping[str, str]],
    ) -> None:
        api_key = api_key if api_key is not None else os.environ.get("LADOO_API_KEY")
        if not api_key:
            raise LadooError(
                "No API key. Pass api_key=... or set the LADOO_API_KEY environment variable. "
                "Create a key under Settings > Developers in Ladoo."
            )
        if max_retries < 0:
            raise ValueError("max_retries can't be negative")
        self.api_key = api_key
        self.api_version = api_version
        self.base_url = (base_url or os.environ.get("LADOO_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.max_retries = max_retries
        self.timeout = timeout
        self._default_headers = dict(default_headers or {})

    def __repr__(self) -> str:
        return f"{type(self).__name__}(base_url={self.base_url!r}, api_version={self.api_version!r})"

    def _copy_settings(self) -> dict[str, Any]:
        return {
            "api_key": self.api_key,
            "api_version": self.api_version,
            "base_url": self.base_url,
            "max_retries": self.max_retries,
            "timeout": self.timeout,
            "default_headers": self._default_headers,
        }

    def _build_request(
        self,
        http: Union[httpx.Client, httpx.AsyncClient],
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, object]],
        json: object,
        multipart: Optional[Mapping[str, object]],
        file_keys: Tuple[str, ...],
        options: RequestOptions,
        idempotency_key: Optional[str],
    ) -> httpx.Request:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Ladoo-Version": options.get("api_version", self.api_version),
            "Accept": "application/json",
            "User-Agent": _USER_AGENT,
            **self._default_headers,
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        headers.update(options.get("headers", {}))

        query = None
        if params:
            query = {_api_name(k): _query_value(v) for k, v in params.items() if v is not None}

        kwargs: dict[str, Any] = {}
        if multipart is not None:
            kwargs["files"] = {k: v for k, v in multipart.items() if k in file_keys}
            kwargs["data"] = {
                _api_name(k): str(v) for k, v in multipart.items() if k not in file_keys and v is not None
            }
        elif json is not _NOT_GIVEN:
            if isinstance(json, Mapping):
                json = {_api_name(str(k)): v for k, v in cast("Mapping[object, object]", json).items()}
            kwargs["content"] = jsonlib.dumps(json, separators=(",", ":")).encode()
            headers["Content-Type"] = "application/json"

        timeout = options.get("timeout", self.timeout)
        return http.build_request(
            method,
            self.base_url + path,
            params=query,  # type: ignore[arg-type]
            headers=headers,
            timeout=timeout,
            **kwargs,
        )

    def _max_retries(self, options: RequestOptions) -> int:
        return options.get("max_retries", self.max_retries)

    @staticmethod
    def _idempotency_key(method: str, options: RequestOptions) -> Optional[str]:
        if "idempotency_key" in options:
            return options["idempotency_key"]
        return str(uuid.uuid4()) if method == "POST" else None

    @staticmethod
    def _should_retry(response: httpx.Response) -> bool:
        status = response.status_code
        if status in (408, 429) or status >= 500:
            after = _retry_after(response)
            return after is None or after <= MAX_RETRY_AFTER
        if status == 409:
            # The first request with this Idempotency-Key is still running.
            try:
                return bool(response.json()["error"]["code"] == "idempotency_key_in_use")
            except (ValueError, KeyError, TypeError):
                return False
        return False

    @staticmethod
    def _retry_delay(attempt: int, response: Optional[httpx.Response]) -> float:
        if response is not None:
            after = _retry_after(response)
            if after is not None:
                return after
        # 0.5s, 1s, 2s, 4s ... capped at 8s, with up to 25% jitter so clients spread out.
        base = min(0.5 * 2.0**attempt, 8.0)
        return base * (1 - 0.25 * random.random())

    @staticmethod
    def _parse(response: httpx.Response, raw: bool) -> Any:
        if not response.is_success:
            try:
                body: Any = response.json()
            except ValueError:
                body = response.text
            raise make_status_error(response, body)
        if raw:
            return response.content
        if response.status_code == 204 or not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            raise APIError(
                f"Expected JSON from {response.request.url}, got {response.headers.get('content-type')}",
                request=response.request,
            ) from None


def _retry_after(response: httpx.Response) -> Optional[float]:
    value = response.headers.get("retry-after")
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        when = email.utils.parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


async def _asleep(seconds: float) -> None:
    await asyncio.sleep(seconds)


class Ladoo(SyncNamespaces, _BaseClient):
    """A client for the Ladoo API.

    ```python
    from ladoo import Ladoo

    client = Ladoo()  # reads LADOO_API_KEY
    for call in client.calls.list(urgency="high"):
        print(call["started_at"], call["summary"])
    ```

    Args:
        api_key: An API key (``lsk_...``). Defaults to ``LADOO_API_KEY``.
        api_version: The dated version sent as ``Ladoo-Version``. Defaults to the
            version this release's types were generated from.
        base_url: Defaults to ``LADOO_BASE_URL``, then ``https://api.tryladoo.com``.
        max_retries: Retries for network errors, 408, 409 ``idempotency_key_in_use``,
            429 and 5xx. POSTs reuse one ``Idempotency-Key`` across retries.
        timeout: Seconds, or an ``httpx.Timeout``.
        default_headers: Headers to send on every request.
        http_client: Your own ``httpx.Client``, e.g. for proxies or custom TLS.
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        api_version: str = API_VERSION,
        base_url: Optional[str] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        timeout: Timeout = DEFAULT_TIMEOUT,
        default_headers: Optional[Mapping[str, str]] = None,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            api_version=api_version,
            base_url=base_url,
            max_retries=max_retries,
            timeout=timeout,
            default_headers=default_headers,
        )
        self._owns_http = http_client is None
        self._http = http_client or httpx.Client()

    def with_options(
        self,
        *,
        api_key: Optional[str] = None,
        api_version: Optional[str] = None,
        max_retries: Optional[int] = None,
        timeout: Timeout | _NotGiven = _NOT_GIVEN,
        default_headers: Optional[Mapping[str, str]] = None,
    ) -> Ladoo:
        """A copy of this client with some settings changed. It shares the connection pool."""
        settings = self._copy_settings()
        overrides = {
            "api_key": api_key,
            "api_version": api_version,
            "max_retries": max_retries,
            "default_headers": default_headers,
        }
        settings.update({k: v for k, v in overrides.items() if v is not None})
        if not isinstance(timeout, _NotGiven):
            settings["timeout"] = timeout
        copy = Ladoo(**settings, http_client=self._http)
        copy._owns_http = False
        return copy

    def close(self) -> None:
        """Close the connection pool, unless you passed your own ``http_client``."""
        if self._owns_http:
            self._http.close()

    def __enter__(self) -> Ladoo:
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        self.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, object]] = None,
        json: object = _NOT_GIVEN,
        options: Optional[RequestOptions] = None,
    ) -> Any:
        """Call any endpoint, with the client's auth, retries and errors.

        ```python
        client.request("POST", "/v1/billing/portal")
        ```

        Returns the parsed JSON body, or ``None`` for an empty response.
        """
        return self._request(method, path, params=params, json=json, options=options)

    def get(
        self, path: str, *, params: Optional[Mapping[str, object]] = None, options: Optional[RequestOptions] = None
    ) -> Any:
        return self._request("GET", path, params=params, options=options)

    def post(self, path: str, *, json: object = _NOT_GIVEN, options: Optional[RequestOptions] = None) -> Any:
        return self._request("POST", path, json=json, options=options)

    def put(self, path: str, *, json: object = _NOT_GIVEN, options: Optional[RequestOptions] = None) -> Any:
        return self._request("PUT", path, json=json, options=options)

    def patch(self, path: str, *, json: object = _NOT_GIVEN, options: Optional[RequestOptions] = None) -> Any:
        return self._request("PATCH", path, json=json, options=options)

    def delete(self, path: str, *, options: Optional[RequestOptions] = None) -> Any:
        return self._request("DELETE", path, options=options)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, object]] = None,
        json: object = _NOT_GIVEN,
        multipart: Optional[Mapping[str, object]] = None,
        file_keys: Tuple[str, ...] = (),
        options: Optional[RequestOptions] = None,
        raw: bool = False,
    ) -> Any:
        options = options or {}
        idempotency_key = self._idempotency_key(method, options)
        retries = self._max_retries(options)
        attempt = 0
        while True:
            request = self._build_request(
                self._http,
                method,
                path,
                params=params,
                json=json,
                multipart=multipart,
                file_keys=file_keys,
                options=options,
                idempotency_key=idempotency_key,
            )
            try:
                response = self._http.send(request)
            except httpx.TimeoutException as exc:
                if attempt < retries:
                    delay = self._retry_delay(attempt, None)
                    log.info("Request to %s timed out; retrying in %.2fs", request.url.path, delay)
                    _sleep(delay)
                    attempt += 1
                    continue
                raise APITimeoutError(request=request) from exc
            except httpx.TransportError as exc:
                if attempt < retries:
                    delay = self._retry_delay(attempt, None)
                    log.info("Request to %s failed (%s); retrying in %.2fs", request.url.path, exc, delay)
                    _sleep(delay)
                    attempt += 1
                    continue
                raise APIConnectionError(request=request) from exc

            if not response.is_success and attempt < retries and self._should_retry(response):
                delay = self._retry_delay(attempt, response)
                log.info("%s %s answered %s; retrying in %.2fs", method, request.url.path, response.status_code, delay)
                response.close()
                _sleep(delay)
                attempt += 1
                continue
            return self._parse(response, raw)

    def _request_page(
        self,
        path: str,
        *,
        params: Mapping[str, object],
        options: Optional[RequestOptions],
    ) -> SyncCursorPage[Any]:
        def fetch(cursor: Optional[str]) -> SyncCursorPage[Any]:
            query = dict(params)
            if cursor:
                query["cursor"] = cursor
            body = self._request("GET", path, params=query, options=options)
            return SyncCursorPage(body["data"], body.get("next_cursor"), fetch)

        return fetch(None)


class AsyncLadoo(AsyncNamespaces, _BaseClient):
    """An asyncio client for the Ladoo API. Takes the same arguments as :class:`Ladoo`.

    ```python
    from ladoo import AsyncLadoo

    async with AsyncLadoo() as client:
        async for call in client.calls.list(urgency="high"):
            print(call["started_at"], call["summary"])
    ```
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        api_version: str = API_VERSION,
        base_url: Optional[str] = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        timeout: Timeout = DEFAULT_TIMEOUT,
        default_headers: Optional[Mapping[str, str]] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            api_version=api_version,
            base_url=base_url,
            max_retries=max_retries,
            timeout=timeout,
            default_headers=default_headers,
        )
        self._owns_http = http_client is None
        self._http = http_client or httpx.AsyncClient()

    def with_options(
        self,
        *,
        api_key: Optional[str] = None,
        api_version: Optional[str] = None,
        max_retries: Optional[int] = None,
        timeout: Timeout | _NotGiven = _NOT_GIVEN,
        default_headers: Optional[Mapping[str, str]] = None,
    ) -> AsyncLadoo:
        """A copy of this client with some settings changed. It shares the connection pool."""
        settings = self._copy_settings()
        overrides = {
            "api_key": api_key,
            "api_version": api_version,
            "max_retries": max_retries,
            "default_headers": default_headers,
        }
        settings.update({k: v for k, v in overrides.items() if v is not None})
        if not isinstance(timeout, _NotGiven):
            settings["timeout"] = timeout
        copy = AsyncLadoo(**settings, http_client=self._http)
        copy._owns_http = False
        return copy

    async def close(self) -> None:
        """Close the connection pool, unless you passed your own ``http_client``."""
        if self._owns_http:
            await self._http.aclose()

    async def __aenter__(self) -> AsyncLadoo:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        await self.close()

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, object]] = None,
        json: object = _NOT_GIVEN,
        options: Optional[RequestOptions] = None,
    ) -> Any:
        """Call any endpoint, with the client's auth, retries and errors."""
        return await self._request(method, path, params=params, json=json, options=options)

    async def get(
        self, path: str, *, params: Optional[Mapping[str, object]] = None, options: Optional[RequestOptions] = None
    ) -> Any:
        return await self._request("GET", path, params=params, options=options)

    async def post(self, path: str, *, json: object = _NOT_GIVEN, options: Optional[RequestOptions] = None) -> Any:
        return await self._request("POST", path, json=json, options=options)

    async def put(self, path: str, *, json: object = _NOT_GIVEN, options: Optional[RequestOptions] = None) -> Any:
        return await self._request("PUT", path, json=json, options=options)

    async def patch(self, path: str, *, json: object = _NOT_GIVEN, options: Optional[RequestOptions] = None) -> Any:
        return await self._request("PATCH", path, json=json, options=options)

    async def delete(self, path: str, *, options: Optional[RequestOptions] = None) -> Any:
        return await self._request("DELETE", path, options=options)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, object]] = None,
        json: object = _NOT_GIVEN,
        multipart: Optional[Mapping[str, object]] = None,
        file_keys: Tuple[str, ...] = (),
        options: Optional[RequestOptions] = None,
        raw: bool = False,
    ) -> Any:
        options = options or {}
        idempotency_key = self._idempotency_key(method, options)
        retries = self._max_retries(options)
        attempt = 0
        while True:
            request = self._build_request(
                self._http,
                method,
                path,
                params=params,
                json=json,
                multipart=multipart,
                file_keys=file_keys,
                options=options,
                idempotency_key=idempotency_key,
            )
            try:
                response = await self._http.send(request)
            except httpx.TimeoutException as exc:
                if attempt < retries:
                    delay = self._retry_delay(attempt, None)
                    log.info("Request to %s timed out; retrying in %.2fs", request.url.path, delay)
                    await _asleep(delay)
                    attempt += 1
                    continue
                raise APITimeoutError(request=request) from exc
            except httpx.TransportError as exc:
                if attempt < retries:
                    delay = self._retry_delay(attempt, None)
                    log.info("Request to %s failed (%s); retrying in %.2fs", request.url.path, exc, delay)
                    await _asleep(delay)
                    attempt += 1
                    continue
                raise APIConnectionError(request=request) from exc

            if not response.is_success and attempt < retries and self._should_retry(response):
                delay = self._retry_delay(attempt, response)
                log.info("%s %s answered %s; retrying in %.2fs", method, request.url.path, response.status_code, delay)
                await response.aclose()
                await _asleep(delay)
                attempt += 1
                continue
            return self._parse(response, raw)

    def _request_page(
        self,
        path: str,
        *,
        params: Mapping[str, object],
        options: Optional[RequestOptions],
    ) -> AsyncPaginator[Any]:
        async def fetch(cursor: Optional[str]) -> AsyncCursorPage[Any]:
            query = dict(params)
            if cursor:
                query["cursor"] = cursor
            body = await self._request("GET", path, params=query, options=options)
            return AsyncCursorPage(body["data"], body.get("next_cursor"), fetch)

        return AsyncPaginator(lambda: fetch(None))
