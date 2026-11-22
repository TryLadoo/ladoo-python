"""The official Python library for the Ladoo API.

https://tryladoo.com/docs/developers
"""

from . import types, webhooks
from ._client import DEFAULT_BASE_URL, DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT, AsyncLadoo, Ladoo
from ._exceptions import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    InternalServerError,
    LadooError,
    NotFoundError,
    PayloadTooLargeError,
    PaymentRequiredError,
    PermissionDeniedError,
    RateLimitError,
    SignatureVerificationError,
    UnprocessableEntityError,
)
from ._pagination import AsyncCursorPage, AsyncPaginator, SyncCursorPage
from ._types import RequestOptions
from ._version import API_VERSION, __version__

__all__ = [
    "API_VERSION",
    "DEFAULT_BASE_URL",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_TIMEOUT",
    "APIConnectionError",
    "APIError",
    "APIStatusError",
    "APITimeoutError",
    "AsyncCursorPage",
    "AsyncLadoo",
    "AsyncPaginator",
    "AuthenticationError",
    "BadRequestError",
    "ConflictError",
    "InternalServerError",
    "Ladoo",
    "LadooError",
    "NotFoundError",
    "PayloadTooLargeError",
    "PaymentRequiredError",
    "PermissionDeniedError",
    "RateLimitError",
    "RequestOptions",
    "SignatureVerificationError",
    "SyncCursorPage",
    "UnprocessableEntityError",
    "__version__",
    "types",
    "webhooks",
]
