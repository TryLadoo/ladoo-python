# Changelog

This project follows [Semantic Versioning](https://semver.org). Each release targets one dated API version, noted below.

## Unreleased

## 0.1.0 (2026-11-22)

First release. API version `2026-11-16`.

- `Ladoo` and `AsyncLadoo` clients on httpx, reading `LADOO_API_KEY` by default.
- Methods for 155 `/v1` endpoints: calls, people, calendar bookings, agents and their tools, tests, workflows and versions, knowledge bases, scripts, webhook endpoints, phone numbers, members, teams, API keys and more.
- `TypedDict` types for every schema in the OpenAPI document.
- Automatic pagination for cursor-paginated lists, sync and async.
- Retries with backoff for network errors, 408, 409 `idempotency_key_in_use`, 429 and 5xx, honoring `Retry-After`.
- An `Idempotency-Key` on every POST, reused across retries.
- Typed exceptions with the API's `code`, `details` and `request_id`.
- `ladoo.webhooks`: `verify_signature`, `construct_event` and `construct_pre_call` for signed webhook and pre-call requests, with rotation and replay protection.
