from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import List

import httpx
import pytest
import respx

import ladoo
from ladoo import Ladoo

from .conftest import API_KEY, BASE_URL, requests

ERROR = {"error": {"code": "not_found", "message": "No such call", "request_id": "req_123"}}


def test_reads_api_key_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LADOO_API_KEY", "lsk_fromenv")
    assert Ladoo().api_key == "lsk_fromenv"


def test_missing_api_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LADOO_API_KEY", raising=False)
    with pytest.raises(ladoo.LadooError, match="LADOO_API_KEY"):
        Ladoo()


def test_repr_hides_the_key(client: Ladoo) -> None:
    assert API_KEY not in repr(client)


def test_default_headers(client: Ladoo, mock: respx.MockRouter) -> None:
    route = mock.get("/v1/workspace").respond(json={"id": "w"})
    client.workspace.retrieve()
    headers = route.calls.last.request.headers
    assert headers["Authorization"] == f"Bearer {API_KEY}"
    assert headers["Ladoo-Version"] == ladoo.API_VERSION == "2026-11-16"
    assert headers["User-Agent"].startswith(f"ladoo-python/{ladoo.__version__}")
    assert "Idempotency-Key" not in headers


def test_api_version_can_be_pinned(mock: respx.MockRouter) -> None:
    route = mock.get("/v1/workspace").respond(json={})
    Ladoo(api_key=API_KEY, base_url=BASE_URL, api_version="2027-01-01").workspace.retrieve()
    assert route.calls.last.request.headers["Ladoo-Version"] == "2027-01-01"


def test_query_parameters(client: Ladoo, mock: respx.MockRouter) -> None:
    route = mock.get("/v1/calls").respond(json={"data": [], "next_cursor": None})
    since = datetime(2026, 11, 1, 9, 30, tzinfo=timezone(timedelta(hours=-5)))
    client.calls.list(from_=since, urgency="high", limit=5)
    params = route.calls.last.request.url.params
    assert params["from"] == "2026-11-01T14:30:00Z"
    assert params["urgency"] == "high"
    assert params["limit"] == "5"
    assert "cursor" not in params


def test_naive_datetimes_are_refused(client: Ladoo) -> None:
    with pytest.raises(ValueError, match="time zone"):
        client.calls.list(from_=datetime(2026, 11, 1))


def test_path_parameters_are_escaped(client: Ladoo, mock: respx.MockRouter) -> None:
    route = mock.get(url__regex=r".*").respond(json={})
    client.calls.retrieve("../workspace")
    assert route.calls.last.request.url.raw_path == b"/v1/calls/..%2Fworkspace"


def test_empty_path_parameter_is_refused(client: Ladoo) -> None:
    with pytest.raises(ValueError):
        client.calls.retrieve("")


def test_json_body_keeps_explicit_nulls(client: Ladoo, mock: respx.MockRouter) -> None:
    route = mock.patch("/v1/people/p1").respond(json={})
    client.people.update("p1", email=None, notes="Prefers mornings")
    body = json.loads(route.calls.last.request.content)
    assert body == {"email": None, "notes": "Prefers mornings"}
    assert route.calls.last.request.headers["Content-Type"] == "application/json"


def test_posts_get_an_idempotency_key(client: Ladoo, mock: respx.MockRouter) -> None:
    route = mock.post("/v1/people").respond(201, json={})
    client.people.create(name="Jordan Rivera", phone="+15555550100")
    client.people.create(name="Jordan Rivera", phone="+15555550100")
    first, second = (r.headers["Idempotency-Key"] for r in requests(route))
    assert first and second and first != second


def test_idempotency_key_can_be_set(client: Ladoo, mock: respx.MockRouter) -> None:
    route = mock.post("/v1/people").respond(201, json={})
    client.people.create(name="Jordan Rivera", request_options={"idempotency_key": "person-42"})
    assert route.calls.last.request.headers["Idempotency-Key"] == "person-42"


def test_request_options(client: Ladoo, mock: respx.MockRouter) -> None:
    route = mock.get("/v1/workspace").respond(json={})
    client.workspace.retrieve(request_options={"api_version": "2027-01-01", "headers": {"X-Trace": "abc"}})
    headers = route.calls.last.request.headers
    assert headers["Ladoo-Version"] == "2027-01-01"
    assert headers["X-Trace"] == "abc"


def test_with_options_shares_the_connection_pool(client: Ladoo) -> None:
    copy = client.with_options(max_retries=5, timeout=3)
    assert copy.max_retries == 5
    assert copy.timeout == 3
    assert copy._http is client._http  # pyright: ignore[reportPrivateUsage]
    assert copy.api_key == client.api_key
    copy.close()
    assert not client._http.is_closed  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize(
    ("status", "error_class"),
    [
        (400, ladoo.BadRequestError),
        (401, ladoo.AuthenticationError),
        (402, ladoo.PaymentRequiredError),
        (403, ladoo.PermissionDeniedError),
        (404, ladoo.NotFoundError),
        (409, ladoo.ConflictError),
        (413, ladoo.PayloadTooLargeError),
        (422, ladoo.UnprocessableEntityError),
        (418, ladoo.APIStatusError),
    ],
)
def test_errors_by_status(
    status: int, error_class: type[ladoo.APIStatusError], client: Ladoo, mock: respx.MockRouter
) -> None:
    mock.get("/v1/calls/c1").respond(status, json=ERROR)
    with pytest.raises(error_class) as info:
        client.calls.retrieve("c1")
    assert type(info.value) is error_class
    assert info.value.status_code == status
    assert info.value.code == "not_found"
    assert info.value.request_id == "req_123"
    assert "req_123" in str(info.value)


def test_error_details(client: Ladoo, mock: respx.MockRouter) -> None:
    body = {
        "error": {
            "code": "insufficient_scope",
            "message": "API key lacks the 'people:write' scope",
            "details": {"required": "people:write"},
            "request_id": "req_9",
        }
    }
    mock.post("/v1/people").respond(403, json=body)
    with pytest.raises(ladoo.PermissionDeniedError) as info:
        client.people.create(name="Jordan Rivera")
    assert info.value.details == {"required": "people:write"}
    assert info.value.body == body


def test_error_without_json_body(client: Ladoo, mock: respx.MockRouter) -> None:
    mock.get("/v1/workspace").respond(404, text="<html>nope</html>")
    with pytest.raises(ladoo.NotFoundError) as info:
        client.workspace.retrieve()
    assert info.value.code is None
    assert info.value.message == "Not Found"


def test_retries_429_honoring_retry_after(client: Ladoo, mock: respx.MockRouter, sleeps: List[float]) -> None:
    route = mock.post("/v1/people")
    route.side_effect = [
        httpx.Response(429, headers={"Retry-After": "3"}, json={"error": {"code": "rate_limited"}}),
        httpx.Response(201, json={"id": "p1"}),
    ]
    assert client.people.create(name="Jordan Rivera")["id"] == "p1"
    assert sleeps == [3.0]
    keys = {r.headers["Idempotency-Key"] for r in requests(route)}
    assert len(keys) == 1, "a retry must reuse the Idempotency-Key"


def test_retry_after_as_http_date(client: Ladoo, mock: respx.MockRouter, sleeps: List[float]) -> None:
    when = datetime.now(timezone.utc) + timedelta(seconds=10)
    mock.get("/v1/workspace").side_effect = [
        httpx.Response(503, headers={"Retry-After": when.strftime("%a, %d %b %Y %H:%M:%S GMT")}),
        httpx.Response(200, json={}),
    ]
    client.workspace.retrieve()
    assert 8 <= sleeps[0] <= 10


def test_long_retry_after_is_not_waited_out(client: Ladoo, mock: respx.MockRouter, sleeps: List[float]) -> None:
    mock.get("/v1/workspace").respond(429, headers={"Retry-After": "3600"})
    with pytest.raises(ladoo.RateLimitError):
        client.workspace.retrieve()
    assert sleeps == []


def test_retries_5xx_with_backoff_then_gives_up(client: Ladoo, mock: respx.MockRouter, sleeps: List[float]) -> None:
    route = mock.get("/v1/workspace").respond(500, json={"error": {"code": "internal_error", "message": "x"}})
    with pytest.raises(ladoo.InternalServerError):
        client.workspace.retrieve()
    assert route.call_count == 3
    assert len(sleeps) == 2
    assert 0.375 <= sleeps[0] <= 0.5
    assert 0.75 <= sleeps[1] <= 1.0


def test_no_retry_on_400(client: Ladoo, mock: respx.MockRouter, sleeps: List[float]) -> None:
    route = mock.get("/v1/workspace").respond(400, json={"error": {"code": "validation_failed"}})
    with pytest.raises(ladoo.BadRequestError):
        client.workspace.retrieve()
    assert route.call_count == 1


def test_retries_idempotency_key_in_use(client: Ladoo, mock: respx.MockRouter, sleeps: List[float]) -> None:
    mock.post("/v1/api-keys").side_effect = [
        httpx.Response(409, json={"error": {"code": "idempotency_key_in_use", "message": "x"}}),
        httpx.Response(201, json={"id": "k1"}),
    ]
    assert client.api_keys.create(name="Reports", preset="read_only")["id"] == "k1"


def test_no_retry_on_other_conflicts(client: Ladoo, mock: respx.MockRouter, sleeps: List[float]) -> None:
    route = mock.post("/v1/people").respond(409, json={"error": {"code": "phone_taken", "message": "x"}})
    with pytest.raises(ladoo.ConflictError):
        client.people.create(phone="+15555550100")
    assert route.call_count == 1


def test_max_retries_per_request(client: Ladoo, mock: respx.MockRouter, sleeps: List[float]) -> None:
    route = mock.get("/v1/workspace").respond(503)
    with pytest.raises(ladoo.InternalServerError):
        client.workspace.retrieve(request_options={"max_retries": 0})
    assert route.call_count == 1


def test_connection_errors_are_retried(client: Ladoo, mock: respx.MockRouter, sleeps: List[float]) -> None:
    mock.get("/v1/workspace").side_effect = [httpx.ConnectError("refused"), httpx.Response(200, json={"ok": True})]
    assert dict(client.workspace.retrieve()) == {"ok": True}
    assert len(sleeps) == 1


def test_connection_error(client: Ladoo, mock: respx.MockRouter, sleeps: List[float]) -> None:
    mock.get("/v1/workspace").side_effect = httpx.ConnectError("refused")
    with pytest.raises(ladoo.APIConnectionError):
        client.workspace.retrieve()


def test_timeout(client: Ladoo, mock: respx.MockRouter, sleeps: List[float]) -> None:
    mock.get("/v1/workspace").side_effect = httpx.ReadTimeout("slow")
    with pytest.raises(ladoo.APITimeoutError):
        client.workspace.retrieve()


def test_delete_returns_none(client: Ladoo, mock: respx.MockRouter) -> None:
    route = mock.delete("/v1/people/p1").respond(204)
    client.people.delete("p1")
    assert route.call_count == 1


def test_unwraps_data_lists(client: Ladoo, mock: respx.MockRouter) -> None:
    mock.get("/v1/agents").respond(json={"data": [{"id": "a1"}, {"id": "a2"}]})
    assert [a["id"] for a in client.agents.list()] == ["a1", "a2"]


def test_file_upload(client: Ladoo, mock: respx.MockRouter) -> None:
    route = mock.post("/v1/knowledge-bases/kb1/files").respond(201, json={"id": "s1"})
    client.knowledge_bases.upload_file("kb1", file=("menu.txt", b"Open 9 to 5", "text/plain"), name="Hours")
    request = route.calls.last.request
    assert request.headers["Content-Type"].startswith("multipart/form-data")
    assert b'name="name"' in request.content and b"Hours" in request.content
    assert b'filename="menu.txt"' in request.content and b"Open 9 to 5" in request.content


def test_binary_response(client: Ladoo, mock: respx.MockRouter) -> None:
    mock.post("/v1/voices/v1/speech").respond(200, content=b"ID3audio", headers={"Content-Type": "audio/mpeg"})
    assert client.voices.speech("v1", text="Thanks for calling.") == b"ID3audio"


def test_raw_request(client: Ladoo, mock: respx.MockRouter) -> None:
    route = mock.post("/v1/billing/portal").respond(json={"url": "https://billing.example.com/session"})
    assert client.request("POST", "/v1/billing/portal")["url"].startswith("https://")
    assert "Idempotency-Key" in route.calls.last.request.headers
    mock.get("/v1/calls").respond(json={"data": []})
    assert client.get("/v1/calls", params={"limit": 1}) == {"data": []}
