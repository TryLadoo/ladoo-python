"""Check that a request came from Ladoo.

Webhook events and pre-call webhooks carry a ``Ladoo-Signature`` header::

    Ladoo-Signature: t=1763478245,v1=5d41402abc...

``v1`` is the hex HMAC-SHA256 of ``"<t>.<raw body>"`` with the signing secret.
Right after a secret is rotated there are two ``v1`` values, one per secret,
and either may match.

```python
from ladoo import webhooks

event = webhooks.construct_event(
    request.body,                       # raw bytes, before any JSON parsing
    request.headers["Ladoo-Signature"],
    os.environ["LADOO_WEBHOOK_SECRET"],
)
```
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any, Optional, Sequence, Union, cast

from ._exceptions import SignatureVerificationError
from .types.webhooks import PreCallRequest, WebhookEvent

__all__ = [
    "DEFAULT_TOLERANCE",
    "SIGNATURE_HEADER",
    "construct_event",
    "construct_pre_call",
    "sign",
    "verify_signature",
]

SIGNATURE_HEADER = "Ladoo-Signature"
DEFAULT_TOLERANCE = 300
"""Seconds a signature stays valid. Older deliveries are refused to stop replays."""

Payload = Union[bytes, bytearray, memoryview, str]
Secrets = Union[str, Sequence[str]]


def verify_signature(
    payload: Payload,
    header: Optional[str],
    secret: Secrets,
    *,
    tolerance: Optional[int] = DEFAULT_TOLERANCE,
    now: Optional[float] = None,
) -> None:
    """Raise :class:`~ladoo.SignatureVerificationError` unless ``header`` signs ``payload``.

    Args:
        payload: The raw request body. Pass bytes exactly as received: parsing
            and re-encoding JSON changes them, and the signature with them.
        header: The ``Ladoo-Signature`` header value.
        secret: The signing secret (``whsec_...``), or several, e.g. the new
            and old one while you roll a rotation out to your servers.
        tolerance: Maximum age of the signature in seconds. ``None`` skips the
            check, which you should only do in tests.
        now: The current Unix time, for tests.
    """
    if not header:
        raise SignatureVerificationError(f"Missing {SIGNATURE_HEADER} header")
    secrets = [secret] if isinstance(secret, str) else list(secret)
    if not secrets or not all(secrets):
        raise SignatureVerificationError("No signing secret given")

    timestamp: Optional[int] = None
    signatures: list[str] = []
    for part in header.split(","):
        key, sep, value = part.strip().partition("=")
        if not sep:
            continue
        if key == "t":
            try:
                timestamp = int(value)
            except ValueError:
                raise SignatureVerificationError("Malformed timestamp in signature header") from None
        elif key == "v1":
            signatures.append(value.strip())
    if timestamp is None:
        raise SignatureVerificationError("No timestamp in signature header")
    if not signatures:
        raise SignatureVerificationError("No v1 signature in signature header")

    if tolerance is not None:
        current = time.time() if now is None else now
        if abs(current - timestamp) > tolerance:
            raise SignatureVerificationError("Signature timestamp is outside the tolerance window")

    body = _as_bytes(payload)
    for s in secrets:
        expected = _hmac(s, timestamp, body)
        if any(hmac.compare_digest(expected, candidate) for candidate in signatures):
            return
    raise SignatureVerificationError("No signature matches the payload")


def construct_event(
    payload: Payload,
    header: Optional[str],
    secret: Secrets,
    *,
    tolerance: Optional[int] = DEFAULT_TOLERANCE,
) -> WebhookEvent:
    """Verify a webhook event and return it parsed.

    Raises :class:`~ladoo.SignatureVerificationError` if the signature doesn't
    check out or the body isn't a JSON object.
    """
    verify_signature(payload, header, secret, tolerance=tolerance)
    return cast(WebhookEvent, _parse_object(payload))


def construct_pre_call(
    payload: Payload,
    header: Optional[str],
    secret: Secrets,
    *,
    tolerance: Optional[int] = DEFAULT_TOLERANCE,
) -> PreCallRequest:
    """Verify a pre-call webhook request and return it parsed.

    Answer within one second with a :class:`~ladoo.types.PreCallResponse`.
    """
    verify_signature(payload, header, secret, tolerance=tolerance)
    return cast(PreCallRequest, _parse_object(payload))


def sign(payload: Payload, secret: str, *, timestamp: Optional[int] = None) -> str:
    """A ``Ladoo-Signature`` header value for ``payload``. For testing your handlers."""
    t = int(time.time()) if timestamp is None else timestamp
    return f"t={t},v1={_hmac(secret, t, _as_bytes(payload))}"


def _hmac(secret: str, timestamp: int, body: bytes) -> str:
    mac = hmac.new(secret.encode(), f"{timestamp}.".encode(), hashlib.sha256)
    mac.update(body)
    return mac.hexdigest()


def _as_bytes(payload: Payload) -> bytes:
    if isinstance(payload, str):
        return payload.encode()
    return bytes(payload)


def _parse_object(payload: Payload) -> dict[str, Any]:
    try:
        data = json.loads(_as_bytes(payload))
    except ValueError:
        raise SignatureVerificationError("Body is not valid JSON") from None
    if not isinstance(data, dict):
        raise SignatureVerificationError("Body is not a JSON object")
    return cast("dict[str, Any]", data)
