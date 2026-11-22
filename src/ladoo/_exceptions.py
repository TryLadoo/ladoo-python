from __future__ import annotations

from typing import Any, Optional, cast

import httpx

__all__ = [
    "APIConnectionError",
    "APIError",
    "APIStatusError",
    "APITimeoutError",
    "AuthenticationError",
    "BadRequestError",
    "ConflictError",
    "InternalServerError",
    "LadooError",
    "NotFoundError",
    "PayloadTooLargeError",
    "PaymentRequiredError",
    "PermissionDeniedError",
    "RateLimitError",
    "SignatureVerificationError",
    "UnprocessableEntityError",
]


class LadooError(Exception):
    """Base class for every error this library raises."""


class SignatureVerificationError(LadooError):
    """A webhook, pre-call webhook or custom tool request failed signature checks."""


class APIError(LadooError):
    """A request to the Ladoo API failed."""

    message: str
    request: httpx.Request

    def __init__(self, message: str, *, request: httpx.Request) -> None:
        super().__init__(message)
        self.message = message
        self.request = request


class APIConnectionError(APIError):
    """No response arrived: DNS, TLS, a refused or dropped connection."""

    def __init__(self, *, request: httpx.Request, message: str = "Connection error.") -> None:
        super().__init__(message, request=request)


class APITimeoutError(APIConnectionError):
    """The request timed out."""

    def __init__(self, *, request: httpx.Request) -> None:
        super().__init__(request=request, message="Request timed out.")


class APIStatusError(APIError):
    """The API answered with a 4xx or 5xx status.

    ``code`` is the stable ``error.code`` from the response (match on it, never
    on ``message``), and ``request_id`` is what to quote to support.
    """

    status_code: int
    code: Optional[str]
    details: Any
    request_id: Optional[str]
    response: httpx.Response
    body: Any

    def __init__(
        self,
        message: str,
        *,
        response: httpx.Response,
        body: Any,
        code: Optional[str],
        details: Any,
        request_id: Optional[str],
    ) -> None:
        super().__init__(message, request=response.request)
        self.response = response
        self.status_code = response.status_code
        self.body = body
        self.code = code
        self.details = details
        self.request_id = request_id

    @property
    def headers(self) -> httpx.Headers:
        return self.response.headers

    def __str__(self) -> str:
        parts = [f"{self.status_code}"]
        if self.code:
            parts.append(self.code)
        text = " ".join(parts) + f": {self.message}"
        if self.request_id:
            text += f" (request_id: {self.request_id})"
        return text


class BadRequestError(APIStatusError):
    """400: the request isn't valid. ``details`` may list the problems."""


class AuthenticationError(APIStatusError):
    """401: no key, or a wrong, revoked or expired one."""


class PaymentRequiredError(APIStatusError):
    """402: the plan doesn't include this, or its limit is reached."""


class PermissionDeniedError(APIStatusError):
    """403: the key can't do this, e.g. ``insufficient_scope`` or ``ip_not_allowed``."""


class NotFoundError(APIStatusError):
    """404: no such thing in this workspace."""


class ConflictError(APIStatusError):
    """409: it clashes with the current state, e.g. ``phone_taken``."""


class PayloadTooLargeError(APIStatusError):
    """413: the body or file is over the limit."""


class UnprocessableEntityError(APIStatusError):
    """422: valid JSON that can't be done, e.g. ``idempotency_key_reused``."""


class RateLimitError(APIStatusError):
    """429: over a rate limit. Retried automatically, honoring ``Retry-After``."""


class InternalServerError(APIStatusError):
    """5xx: something failed on Ladoo's side. Retried automatically."""


_BY_STATUS: dict[int, type[APIStatusError]] = {
    400: BadRequestError,
    401: AuthenticationError,
    402: PaymentRequiredError,
    403: PermissionDeniedError,
    404: NotFoundError,
    409: ConflictError,
    413: PayloadTooLargeError,
    422: UnprocessableEntityError,
    429: RateLimitError,
}


def make_status_error(response: httpx.Response, body: object) -> APIStatusError:
    error: object = cast("dict[str, object]", body).get("error") if isinstance(body, dict) else None
    fields = cast("dict[str, object]", error) if isinstance(error, dict) else {}

    def text(key: str) -> Optional[str]:
        value = fields.get(key)
        return value if isinstance(value, str) else None

    code, message, request_id = text("code"), text("message"), text("request_id")
    cls = _BY_STATUS.get(response.status_code)
    if cls is None:
        cls = InternalServerError if response.status_code >= 500 else APIStatusError
    return cls(
        message or response.reason_phrase or "Request failed",
        response=response,
        body=body,
        code=code,
        details=fields.get("details"),
        request_id=request_id,
    )
