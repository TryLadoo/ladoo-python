from __future__ import annotations

from typing import AsyncIterator, Iterator, List, cast

import httpx
import pytest
import respx

from ladoo import AsyncLadoo, Ladoo
from ladoo import _client as client_module  # pyright: ignore[reportPrivateUsage]

BASE_URL = "https://api.ladoo.test"
API_KEY = "lsk_test0000000_notarealsecret"


def requests(route: respx.Route) -> List[httpx.Request]:
    return [cast(httpx.Request, call.request) for call in route.calls]  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]


@pytest.fixture
def mock() -> Iterator[respx.MockRouter]:
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
        yield router


@pytest.fixture
def client() -> Iterator[Ladoo]:
    with Ladoo(api_key=API_KEY, base_url=BASE_URL) as c:
        yield c


@pytest.fixture
async def async_client() -> AsyncIterator[AsyncLadoo]:
    async with AsyncLadoo(api_key=API_KEY, base_url=BASE_URL) as c:
        yield c


@pytest.fixture
def sleeps(monkeypatch: pytest.MonkeyPatch) -> List[float]:
    """Record retry delays instead of sleeping."""
    delays: List[float] = []

    async def fake_asleep(seconds: float) -> None:
        delays.append(seconds)

    monkeypatch.setattr(client_module, "_sleep", delays.append)
    monkeypatch.setattr(client_module, "_asleep", fake_asleep)
    return delays
