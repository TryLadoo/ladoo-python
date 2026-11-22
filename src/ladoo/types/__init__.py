"""Types for everything the API sends and accepts.

Responses are plain dicts. These ``TypedDict`` classes describe them for your
editor and type checker. They're generated from the API's OpenAPI document,
except the webhook payloads in :mod:`ladoo.types.webhooks`, which follow the
webhook docs.
"""

from ._generated import *  # noqa: F403
from .webhooks import *  # noqa: F403
