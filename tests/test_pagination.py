from __future__ import annotations

from typing import List

import httpx
import pytest
import respx

from ladoo import AsyncCursorPage, AsyncLadoo, Ladoo, SyncCursorPage

from .conftest import requests


def pages(mock: respx.MockRouter) -> respx.Route:
    route = mock.get("/v1/calls")
    route.side_effect = [
        httpx.Response(200, json={"data": [{"id": "c1"}, {"id": "c2"}], "next_cursor": "cur2"}),
        httpx.Response(200, json={"data": [{"id": "c3"}], "next_cursor": "cur3"}),
        httpx.Response(200, json={"data": [{"id": "c4"}], "next_cursor": None}),
    ]
    return route


def test_iterating_walks_every_page(client: Ladoo, mock: respx.MockRouter) -> None:
    route = pages(mock)
    ids = [call["id"] for call in client.calls.list(limit=2, urgency="high")]
    assert ids == ["c1", "c2", "c3", "c4"]
    params = [dict(r.url.params) for r in requests(route)]
    assert params == [
        {"limit": "2", "urgency": "high"},
        {"limit": "2", "urgency": "high", "cursor": "cur2"},
        {"limit": "2", "urgency": "high", "cursor": "cur3"},
    ]


def test_one_page_at_a_time(client: Ladoo, mock: respx.MockRouter) -> None:
    route = pages(mock)
    page = client.calls.list(limit=2)
    assert isinstance(page, SyncCursorPage)
    assert [c["id"] for c in page.data] == ["c1", "c2"]
    assert page.has_next_page()
    assert route.call_count == 1

    sizes = [len(p.data) for p in page.iter_pages()]
    assert sizes == [2, 1, 1]


def test_next_page_past_the_end(client: Ladoo, mock: respx.MockRouter) -> None:
    mock.get("/v1/people").respond(json={"data": [], "next_cursor": None})
    page = client.people.list()
    assert not page.has_next_page()
    with pytest.raises(StopIteration):
        page.next_page()


async def test_async_iterating_walks_every_page(async_client: AsyncLadoo, mock: respx.MockRouter) -> None:
    pages(mock)
    ids: List[str] = [call["id"] async for call in async_client.calls.list(limit=2)]
    assert ids == ["c1", "c2", "c3", "c4"]


async def test_async_await_gives_the_first_page(async_client: AsyncLadoo, mock: respx.MockRouter) -> None:
    route = pages(mock)
    page = await async_client.calls.list(limit=2)
    assert isinstance(page, AsyncCursorPage)
    assert [c["id"] for c in page.data] == ["c1", "c2"]
    assert route.call_count == 1

    second = await page.next_page()
    assert [c["id"] for c in second.data] == ["c3"]
    sizes = [len(p.data) async for p in second.iter_pages()]
    assert sizes == [1, 1]
