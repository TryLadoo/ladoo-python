"""A smoke test against the real API. Runs only when LADOO_API_KEY is set; CI never sets it."""

from __future__ import annotations

import os

import pytest

from ladoo import Ladoo

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(not os.environ.get("LADOO_API_KEY"), reason="set LADOO_API_KEY to run"),
]


def test_read_only_smoke() -> None:
    with Ladoo() as client:
        workspace = client.workspace.retrieve()
        assert workspace["id"]
        page = client.calls.list(limit=1)
        assert isinstance(page.data, list)
