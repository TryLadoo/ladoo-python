"""Payloads Ladoo sends to your server.

The OpenAPI document doesn't describe webhook payloads yet, so these follow
https://tryladoo.com/docs/developers/webhook-events,
https://tryladoo.com/docs/developers/pre-call-webhook and
https://tryladoo.com/docs/developers/custom-tools.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Union

from typing_extensions import Literal, NotRequired, TypeAlias, TypedDict

from ._generated import CalendarBooking, CallDetail, CallJudgment, KnowledgeSource, PersonDetail, PhoneNumber

__all__ = [
    "BookingEventData",
    "CallAnalyzedEventData",
    "CallEventData",
    "KnowledgeEventData",
    "NumberEventData",
    "PersonEventData",
    "PreCallCaller",
    "PreCallPerson",
    "PreCallRequest",
    "PreCallResponse",
    "WebhookEvent",
    "WebhookEventType",
]

WebhookEventType: TypeAlias = Literal[
    "call.started",
    "call.completed",
    "call.analyzed",
    "call.flagged_urgent",
    "call.transferred",
    "message.taken",
    "booking.created",
    "booking.rescheduled",
    "booking.cancelled",
    "person.created",
    "person.updated",
    "knowledge.source_failed",
    "number.purchased",
    "number.released",
]


class CallEventData(TypedDict):
    """``data`` for ``call.*`` and ``message.taken``."""

    call: CallDetail


class CallAnalyzedEventData(TypedDict):
    """``data`` for ``call.analyzed``. ``judgment`` is null for calls that aren't reviewed."""

    call: CallDetail
    judgment: CallJudgment | None


class BookingEventData(TypedDict):
    """``data`` for ``booking.*``. ``previous_booking_id`` comes with ``booking.rescheduled``."""

    booking: CalendarBooking
    previous_booking_id: NotRequired[str]


class PersonEventData(TypedDict):
    """``data`` for ``person.created`` and ``person.updated``."""

    person: PersonDetail


class KnowledgeEventData(TypedDict):
    """``data`` for ``knowledge.source_failed``."""

    source: KnowledgeSource


class NumberEventData(TypedDict):
    """``data`` for ``number.purchased`` and ``number.released``."""

    phone_number: PhoneNumber


class WebhookEvent(TypedDict):
    """The envelope of every webhook event.

    ``type`` may be one this version of the library doesn't know yet, so
    handle unknown types without failing. ``id`` stays the same across
    retries; use it to skip events you've already handled.
    """

    id: str
    type: Union[WebhookEventType, str]
    created_at: str
    workspace_id: str
    tenant_id: NotRequired[str]
    api_version: str
    data: Dict[str, Any]


class PreCallPerson(TypedDict):
    id: str
    name: str | None
    email: str | None


# "from" is a Python keyword, so this one needs the functional form.
PreCallRequest = TypedDict(
    "PreCallRequest",
    {
        "call_id": str,
        "agent_id": str,
        "kind": Literal["live", "test"],
        "from": Optional[str],
        "to": Optional[str],
        "person": Optional[PreCallPerson],
    },
)
"""What Ladoo POSTs to an agent's pre-call webhook as a call rings.

``from`` is the caller in E.164, or None when caller ID is withheld.
"""


class PreCallCaller(TypedDict, total=False):
    name: str
    first_name: str


class PreCallResponse(TypedDict, total=False):
    """Your answer to a pre-call webhook. Every key is optional; ``{}`` changes nothing.

    ``route`` is ``"default"``, ``"block"`` or ``"transfer:+1555..."``.
    """

    variables: Dict[str, Union[str, float, bool]]
    caller: PreCallCaller
    note_for_agent: str
    route: str
