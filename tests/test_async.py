from __future__ import annotations

import json
from typing import List

import httpx
import pytest
import respx

import ladoo
from ladoo import AsyncLadoo

from .conftest import requests


async def test_retrieve(async_client: AsyncLadoo, mock: respx.MockRouter) -> None:
    route = mock.get("/v1/calls/c1").respond(json={"id": "c1", "summary": "Leaking water heater"})
    call = await async_client.calls.retrieve("c1")
    assert call["summary"] == "Leaking water heater"
    assert route.calls.last.request.headers["Ladoo-Version"] == ladoo.API_VERSION


async def test_create_with_retry(async_client: AsyncLadoo, mock: respx.MockRouter, sleeps: List[float]) -> None:
    route = mock.post("/v1/webhook-endpoints")
    route.side_effect = [
        httpx.Response(502),
        httpx.Response(201, json={"id": "we1", "secret": "whsec_test"}),
    ]
    endpoint = await async_client.webhook_endpoints.create(
        url="https://hooks.example.com/ladoo", events=["call.completed"]
    )
    assert endpoint["secret"] == "whsec_test"
    assert len(sleeps) == 1
    assert json.loads(route.calls.last.request.content) == {
        "url": "https://hooks.example.com/ladoo",
        "events": ["call.completed"],
    }
    assert len({r.headers["Idempotency-Key"] for r in requests(route)}) == 1


async def test_errors(async_client: AsyncLadoo, mock: respx.MockRouter) -> None:
    mock.get("/v1/people/nope").respond(404, json={"error": {"code": "not_found", "message": "x", "request_id": "r"}})
    with pytest.raises(ladoo.NotFoundError):
        await async_client.people.retrieve("nope")


async def test_timeout(async_client: AsyncLadoo, mock: respx.MockRouter, sleeps: List[float]) -> None:
    mock.get("/v1/workspace").side_effect = httpx.ConnectTimeout("slow")
    with pytest.raises(ladoo.APITimeoutError):
        await async_client.workspace.retrieve()
    assert len(sleeps) == 2


async def test_with_options(async_client: AsyncLadoo, mock: respx.MockRouter) -> None:
    route = mock.get("/v1/workspace").respond(json={})
    await async_client.with_options(api_version="2027-01-01").workspace.retrieve()
    assert route.calls.last.request.headers["Ladoo-Version"] == "2027-01-01"


async def test_raw_request(async_client: AsyncLadoo, mock: respx.MockRouter) -> None:
    mock.get("/v1/attention").respond(json={"data": []})
    assert await async_client.get("/v1/attention") == {"data": []}
