"""Every method in scripts/endpoints.py, against a mocked response shaped like the OpenAPI document says."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, cast

import httpx
import pytest
import respx

from ladoo import AsyncCursorPage, AsyncLadoo, Ladoo, SyncCursorPage

from .spec import spec, success_response

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from endpoints import ENDPOINTS, Endpoint


def method_for(client: object, ep: Endpoint) -> Callable[..., Any]:
    target: Any = client
    for part in ep.ns.split("."):
        target = getattr(target, part)
    return cast(Callable[..., Any], getattr(target, ep.name))


def call_args(ep: Endpoint) -> tuple[List[str], str]:
    args = [f"{name}-1" for name in ep.args]
    path = ep.path
    for template, value in zip(re.findall(r"{[^}]+}", ep.path), args):
        path = path.replace(template, value)
    return args, path


def needs_body(ep: Endpoint) -> bool:
    content = spec()["paths"][ep.path][ep.method.lower()].get("requestBody", {}).get("content", {})
    schema = content.get("application/json", {}).get("schema", {})
    if "$ref" in schema:
        schema = spec()["components"]["schemas"][schema["$ref"].split("/")[-1]]
    return "oneOf" in schema


def as_dict(value: object) -> Optional[Dict[str, object]]:
    return cast("dict[str, object]", value) if isinstance(value, dict) else None


def expected(body: object) -> object:
    """What a method returns for ``body``: plain and paginated lists give their items."""
    fields = as_dict(body)
    if fields is not None and (set(fields) == {"data"} or "next_cursor" in fields):
        return fields["data"]
    return body


def returned(result: object) -> object:
    if type(result) in (SyncCursorPage, AsyncCursorPage):
        return getattr(result, "data", None)
    return result


IDS = [f"{ep.ns}.{ep.name}" for ep in ENDPOINTS]


def test_every_endpoint_is_in_the_spec() -> None:
    for ep in ENDPOINTS:
        assert ep.method.lower() in spec()["paths"][ep.path], ep


def test_every_api_key_endpoint_has_a_method_or_is_left_out_on_purpose() -> None:
    covered = {(ep.method, ep.path) for ep in ENDPOINTS}
    missing: List[str] = []
    for path, ops in spec()["paths"].items():
        for method, op in ops.items():
            if any("ApiKey" in s for s in op.get("security", [])) and (method.upper(), path) not in covered:
                missing.append(f"{method.upper()} {path}")
    # OAuth callbacks, checkout flows and other dashboard steps stay on client.request().
    for item in missing:
        assert re.search(
            r"callback|authorize|/billing/|/stripe|assist-runs|/brand/mail-domain|/workspace/delete"
            r"|/integrations/(crm|calendar)|/integrations/calendars|people-import",
            item,
        ), f"{item} has no method; add it to scripts/endpoints.py or to this allowlist"


@pytest.mark.parametrize("ep", ENDPOINTS, ids=IDS)
def test_sync(ep: Endpoint, client: Ladoo, mock: respx.MockRouter) -> None:
    status, body = success_response(ep.method, ep.path)
    args, path = call_args(ep)
    if isinstance(body, bytes):
        route = mock.route(method=ep.method, path=path).mock(return_value=httpx.Response(status, content=body))
    elif body is None:
        route = mock.route(method=ep.method, path=path).mock(return_value=httpx.Response(status))
    else:
        fields = as_dict(body)
        if fields is not None and "next_cursor" in fields:
            fields["next_cursor"] = None
        route = mock.route(method=ep.method, path=path).mock(return_value=httpx.Response(status, json=body))

    fn = method_for(client, ep)
    result = fn(*args, {}) if needs_body(ep) else fn(*args)

    assert route.call_count == 1
    request = route.calls.last.request
    assert request.headers["Authorization"].startswith("Bearer lsk_")
    assert ("Idempotency-Key" in request.headers) == (ep.method == "POST")
    assert returned(result) == expected(body)


@pytest.mark.parametrize("ep", ENDPOINTS, ids=IDS)
async def test_async(ep: Endpoint, async_client: AsyncLadoo, mock: respx.MockRouter) -> None:
    status, body = success_response(ep.method, ep.path)
    args, path = call_args(ep)
    if isinstance(body, bytes):
        response = httpx.Response(status, content=body)
    elif body is None:
        response = httpx.Response(status)
    else:
        fields = as_dict(body)
        if fields is not None and "next_cursor" in fields:
            fields["next_cursor"] = None
        response = httpx.Response(status, json=body)
    route = mock.route(method=ep.method, path=path).mock(return_value=response)

    fn = method_for(async_client, ep)
    result = await (fn(*args, {}) if needs_body(ep) else fn(*args))

    assert route.call_count == 1
    assert returned(result) == expected(body)
