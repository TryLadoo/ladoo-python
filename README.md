<p>
  <a href="https://tryladoo.com">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset=".github/assets/ladoo-wordmark-on-dark.svg">
      <img src=".github/assets/ladoo-wordmark.svg" alt="Ladoo" height="40">
    </picture>
  </a>
</p>

# Ladoo Python library

[![CI](https://github.com/TryLadoo/ladoo-python/actions/workflows/ci.yml/badge.svg)](https://github.com/TryLadoo/ladoo-python/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

The official Python client for the [Ladoo API](https://tryladoo.com/docs/developers). Ladoo answers a business's phone and website chat, books appointments and takes messages. Use this library to read calls, manage people and agents, and check the signatures on webhooks Ladoo sends you.

It depends only on `httpx` and `typing-extensions`.

## Install

```sh
pip install "git+https://github.com/TryLadoo/ladoo-python"
```

Not on npm/PyPI yet. Registry releases are on the [roadmap](ROADMAP.md). To pin a release, add its tag: `ladoo-python@v0.1.0`.

Python 3.9 or later.

## Quickstart

Create an API key under **Settings → Developers** in Ladoo and put it in `LADOO_API_KEY`.

```python
from ladoo import Ladoo

client = Ladoo()  # reads LADOO_API_KEY

for call in client.calls.list(urgency="high", limit=50):
    print(call["started_at"], call["from_number"], call["summary"])
```

The same with asyncio:

```python
import asyncio
from ladoo import AsyncLadoo


async def main() -> None:
    async with AsyncLadoo() as client:
        async for call in client.calls.list(urgency="high", limit=50):
            print(call["started_at"], call["from_number"], call["summary"])


asyncio.run(main())
```

Responses are plain dicts. Every one has a `TypedDict` in `ladoo.types`, generated from the [OpenAPI document](openapi/openapi.json), so your editor completes field names and your type checker catches typos.

Methods follow the API: `client.calls.retrieve(call_id)`, `client.people.create(...)`, `client.agents.tools.list(agent_id)`, `client.calendar.bookings.list(...)`, `client.webhook_endpoints.create(...)`, `client.knowledge_bases.search(...)`, `client.phone_numbers.list()` and so on.

## Recipes

### Verify webhook events

Ladoo signs every event with your endpoint's secret. Pass the raw body, before any JSON parsing:

```python
import os

from fastapi import FastAPI, HTTPException, Request
from ladoo import SignatureVerificationError, webhooks

app = FastAPI()


@app.post("/ladoo")
async def ladoo_webhook(request: Request) -> dict[str, bool]:
    try:
        event = webhooks.construct_event(
            await request.body(),
            request.headers.get("Ladoo-Signature"),
            os.environ["LADOO_WEBHOOK_SECRET"],
        )
    except SignatureVerificationError as e:
        raise HTTPException(status_code=400) from e

    if event["type"] == "call.flagged_urgent":
        call = event["data"]["call"]
        ...
    return {"received": True}
```

In Flask pass `request.get_data()`, in Django `request.body`. Signatures older than 5 minutes are refused. While a rotated secret is rolling out, pass both: `secret=[new_secret, old_secret]`. Ladoo can send an event more than once, so skip `event["id"]` values you've already handled.

[`examples/urgent_calls_to_slack.py`](examples/urgent_calls_to_slack.py) is a complete receiver.

### Look up the caller before the agent answers

A [pre-call webhook](https://tryladoo.com/docs/developers/pre-call-webhook) is signed the same way, with the agent's pre-call secret. Answer within one second:

```python
import os

from flask import Flask, request
from ladoo import webhooks
from ladoo.types import PreCallResponse

app = Flask(__name__)


@app.post("/ladoo/ring")
def ring() -> PreCallResponse:
    call = webhooks.construct_pre_call(
        request.get_data(), request.headers.get("Ladoo-Signature"), os.environ["LADOO_PRE_CALL_SECRET"]
    )
    customer = customers_by_phone.get(call["from"] or "")
    if customer is None:
        return {}
    return {
        "caller": {"name": customer.name},
        "variables": {"plan": customer.plan},
        "note_for_agent": f"Last visit was {customer.last_visit:%b %d}.",
    }
```

`webhooks.verify_signature(payload, header, secret)` checks a signature without parsing the body.

### Give the agent a custom tool

A [custom tool](https://tryladoo.com/docs/developers/custom-tools) is an HTTP endpoint the agent can call mid-conversation. Register it, with a header your server checks:

```python
client.agents.tools.create(
    agent_id,
    name="order_status",
    description="Look up an order's status and delivery date by its order number.",
    parameters={
        "type": "object",
        "properties": {"order_number": {"type": "string"}},
        "required": ["order_number"],
    },
    method="POST",
    url="https://tools.example.com/ladoo/order-status",
    headers=[{"name": "Authorization", "value": f"Bearer {tool_token}"}],
    response_fields=[{"path": "status"}, {"path": "eta.date"}],
)
```

[`examples/custom_tool_flask.py`](examples/custom_tool_flask.py) is the server side.

### Page through results

Iterating a list walks every page. To go a page at a time, use `.data` and `.next_page()`:

```python
from datetime import datetime, timedelta, timezone

since = datetime.now(timezone.utc) - timedelta(days=7)

page = client.calls.list(from_=since, limit=200)
print(len(page.data), page.has_next_page())
for page in page.iter_pages():
    save(page.data)
```

`from` is a Python keyword, so the parameter is `from_`. Datetimes must have a time zone.

[`examples/export_calls_csv.py`](examples/export_calls_csv.py) writes calls to a CSV file.

### Handle errors

```python
import ladoo

try:
    client.people.create(name="Jordan Rivera", phone="+15555550100")
except ladoo.ConflictError as e:
    if e.code == "phone_taken":
        print("Already in People:", e.details)
except ladoo.PermissionDeniedError as e:
    print(e.code, e.details)  # insufficient_scope {'required': 'people:write'}
except ladoo.APIStatusError as e:
    print(e.status_code, e.code, e.request_id)
```

Match on `e.code`, which is stable, not on the message. Quote `e.request_id` when you write to support. Network failures raise `ladoo.APIConnectionError` (`ladoo.APITimeoutError` for timeouts).

## Retries and idempotency

Network errors, `408`, `429`, `5xx` and `409 idempotency_key_in_use` are retried twice with exponential backoff, waiting out `Retry-After` when the API sends one. Every POST gets an `Idempotency-Key`, reused across its retries, so a retry never creates something twice. To make retries safe across processes too, pass your own:

```python
client.phone_numbers.buy(
    e164="+15555550142",
    type="local",
    request_options={"idempotency_key": f"buy-number-{order_id}"},
)
```

## Configuration

```python
client = Ladoo(
    api_key="lsk_...",  # default: LADOO_API_KEY
    api_version="2026-11-16",  # sent as Ladoo-Version
    base_url="https://api.tryladoo.com",
    max_retries=2,
    timeout=60.0,  # seconds, or an httpx.Timeout
)

client.with_options(timeout=5).calls.list()  # a copy that shares the connection pool
client.calls.retrieve(call_id, request_options={"timeout": 5, "max_retries": 0})
```

`api_version` defaults to the version this release was generated from, so responses match the types. You can bring your own `httpx.Client` (or `httpx.AsyncClient`) with `http_client=` for proxies or custom TLS.

For an endpoint without a method yet, `client.get()`, `client.post()`, `client.put()`, `client.patch()`, `client.delete()` and `client.request()` send it with the same auth, retries and errors:

```python
portal = client.post("/v1/billing/portal")
```

Set the `ladoo` logger to `INFO` to see retries.

## Development

```sh
uv sync
uv run pytest
uv run python scripts/generate.py   # after updating openapi/openapi.json
```

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Links

- [Developer docs](https://tryladoo.com/docs/developers) and [API reference](https://tryladoo.com/docs/developers/api-reference)
- [Changelog](CHANGELOG.md) and [roadmap](ROADMAP.md)
- Security issues: see [SECURITY.md](SECURITY.md)
- Help with your account or the API: support@tryladoo.com

MIT licensed. Copyright Ladoo LLC.
