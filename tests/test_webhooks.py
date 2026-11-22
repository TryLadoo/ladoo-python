from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from ladoo import SignatureVerificationError, webhooks

SECRET = "whsec_test_secret"
OLD_SECRET = "whsec_old_secret"
NOW = 1_763_478_245
BODY = json.dumps(
    {
        "id": "5b0e3a4c-9d2f-4c1e-a7b4-2f6d8e1c0a93",
        "type": "call.flagged_urgent",
        "created_at": "2026-11-18T15:04:05.000Z",
        "workspace_id": "0f8f6d0e-2b1a-4c3d-9e8f-7a6b5c4d3e2f",
        "api_version": "2026-11-16",
        "data": {"call": {"id": "c1", "from_number": "+15555550100", "urgency": "high"}},
    }
).encode()


def signature(secret: str, body: bytes = BODY, t: int = NOW) -> str:
    return hmac.new(secret.encode(), f"{t}.".encode() + body, hashlib.sha256).hexdigest()


def test_sign_matches_the_documented_scheme() -> None:
    assert webhooks.sign(BODY, SECRET, timestamp=NOW) == f"t={NOW},v1={signature(SECRET)}"


def test_valid_signature() -> None:
    webhooks.verify_signature(BODY, f"t={NOW},v1={signature(SECRET)}", SECRET, now=NOW + 10)


def test_either_v1_matches_during_rotation() -> None:
    header = f"t={NOW},v1={signature(SECRET)},v1={signature(OLD_SECRET)}"
    webhooks.verify_signature(BODY, header, SECRET, now=NOW)
    webhooks.verify_signature(BODY, header, OLD_SECRET, now=NOW)


def test_several_secrets() -> None:
    header = f"t={NOW},v1={signature(OLD_SECRET)}"
    webhooks.verify_signature(BODY, header, [SECRET, OLD_SECRET], now=NOW)


def test_spaces_in_header() -> None:
    webhooks.verify_signature(BODY, f"t={NOW}, v1={signature(SECRET)}", SECRET, now=NOW)


@pytest.mark.parametrize(
    ("header", "message"),
    [
        (None, "Missing"),
        ("", "Missing"),
        ("garbage", "No timestamp"),
        (f"v1={signature(SECRET)}", "No timestamp"),
        (f"t=abc,v1={signature(SECRET)}", "Malformed timestamp"),
        (f"t={NOW}", "No v1"),
        (f"t={NOW},v0={signature(SECRET)}", "No v1"),
        (f"t={NOW},v1={signature('whsec_wrong')}", "No signature matches"),
        (f"t={NOW},v1=", "No signature matches"),
    ],
)
def test_bad_headers(header: str | None, message: str) -> None:
    with pytest.raises(SignatureVerificationError, match=message):
        webhooks.verify_signature(BODY, header, SECRET, now=NOW)


def test_tampered_body() -> None:
    with pytest.raises(SignatureVerificationError):
        webhooks.verify_signature(BODY + b" ", f"t={NOW},v1={signature(SECRET)}", SECRET, now=NOW)


def test_signature_from_another_timestamp() -> None:
    header = f"t={NOW + 1},v1={signature(SECRET)}"
    with pytest.raises(SignatureVerificationError):
        webhooks.verify_signature(BODY, header, SECRET, now=NOW)


@pytest.mark.parametrize("offset", [301, -301, 10_000])
def test_outside_tolerance(offset: int) -> None:
    with pytest.raises(SignatureVerificationError, match="tolerance"):
        webhooks.verify_signature(BODY, f"t={NOW},v1={signature(SECRET)}", SECRET, now=NOW + offset)


def test_custom_and_disabled_tolerance() -> None:
    header = f"t={NOW},v1={signature(SECRET)}"
    webhooks.verify_signature(BODY, header, SECRET, tolerance=3600, now=NOW + 3000)
    webhooks.verify_signature(BODY, header, SECRET, tolerance=None, now=NOW + 10**9)


def test_empty_secret_is_refused() -> None:
    with pytest.raises(SignatureVerificationError, match="secret"):
        webhooks.verify_signature(BODY, f"t={NOW},v1={signature('')}", "", now=NOW)
    with pytest.raises(SignatureVerificationError, match="secret"):
        webhooks.verify_signature(BODY, f"t={NOW},v1={signature(SECRET)}", [], now=NOW)


def test_construct_event() -> None:
    event = webhooks.construct_event(BODY, webhooks.sign(BODY, SECRET), SECRET)
    assert event["type"] == "call.flagged_urgent"
    assert event["data"]["call"]["urgency"] == "high"


def test_construct_event_accepts_str_and_bytearray() -> None:
    header = webhooks.sign(BODY, SECRET)
    assert webhooks.construct_event(BODY.decode(), header, SECRET)["id"]
    assert webhooks.construct_event(bytearray(BODY), header, SECRET)["id"]


def test_construct_event_checks_the_signature_first() -> None:
    with pytest.raises(SignatureVerificationError, match="No signature matches"):
        webhooks.construct_event(BODY, webhooks.sign(BODY, "whsec_wrong"), SECRET)


@pytest.mark.parametrize("body", [b"not json", b"[1, 2]"])
def test_construct_event_needs_a_json_object(body: bytes) -> None:
    with pytest.raises(SignatureVerificationError, match="JSON"):
        webhooks.construct_event(body, webhooks.sign(body, SECRET), SECRET)


def test_construct_pre_call() -> None:
    body = json.dumps(
        {
            "call_id": "8c2f6a1e-4b3d-4e5f-9a8b-7c6d5e4f3a2b",
            "agent_id": "3e1d2c4b-5a6f-4b7c-8d9e-0f1a2b3c4d5e",
            "kind": "live",
            "from": "+15555550199",
            "to": "+15555550100",
            "person": None,
        }
    ).encode()
    request = webhooks.construct_pre_call(body, webhooks.sign(body, SECRET), SECRET)
    assert request["from"] == "+15555550199"
    assert request["person"] is None
