from __future__ import annotations

from typing import Mapping, Union

import httpx
from typing_extensions import TypedDict

__all__ = ["RequestOptions", "Timeout"]

Timeout = Union[float, httpx.Timeout, None]


class RequestOptions(TypedDict, total=False):
    """Per-request settings. Every key is optional.

    ```python
    client.people.create(
        name="Jordan Rivera",
        phone="+15555550100",
        request_options={"idempotency_key": "person-jordan-rivera", "timeout": 10},
    )
    ```
    """

    idempotency_key: str
    """Sent as ``Idempotency-Key``. POSTs get a random one by default, reused on retries."""

    timeout: Timeout
    """Seconds, or an ``httpx.Timeout``. Overrides the client's timeout."""

    max_retries: int
    """Overrides the client's ``max_retries``."""

    api_version: str
    """Sent as ``Ladoo-Version``. Overrides the client's ``api_version``."""

    headers: Mapping[str, str]
    """Extra headers to send."""
