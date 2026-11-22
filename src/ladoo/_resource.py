from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import quote

if TYPE_CHECKING:
    from ._client import AsyncLadoo, Ladoo

__all__ = ["AsyncAPIResource", "SyncAPIResource", "path_param"]


class SyncAPIResource:
    def __init__(self, client: Ladoo) -> None:
        self._client = client


class AsyncAPIResource:
    def __init__(self, client: AsyncLadoo) -> None:
        self._client = client


def path_param(value: str) -> str:
    """Quote one path segment, so an id can never change which route is called."""
    if not isinstance(value, str) or not value:  # pyright: ignore[reportUnnecessaryIsInstance]
        raise ValueError(f"Expected a non-empty string for a path parameter, got {value!r}")
    return quote(value, safe="")
