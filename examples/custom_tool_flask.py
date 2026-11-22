"""A custom tool the agent can call during a conversation: look up an order.

Ladoo sends the headers you configure on the tool, so give it a long random
token and check it here. Register the tool once:

    from ladoo import Ladoo
    Ladoo().agents.tools.create(
        "AGENT_ID",
        name="order_status",
        description="Look up an order's status and delivery date by its order number.",
        parameters={
            "type": "object",
            "properties": {
                "order_number": {"type": "string", "description": "The order number the caller reads out"},
            },
            "required": ["order_number"],
        },
        method="POST",
        url="https://tools.example.com/ladoo/order-status",
        headers=[{"name": "Authorization", "value": "Bearer <TOOL_TOKEN>"}],
        say_while_waiting="Let me look that up.",
        response_fields=[{"path": "status"}, {"path": "eta.date"}],
    )

Then run:

    export TOOL_TOKEN=...   # the same value as in the Authorization header above
    flask --app custom_tool_flask run --port 3000
"""

from __future__ import annotations

import hmac
import os
from typing import Any

from flask import Flask, abort, request

app = Flask(__name__)

TOOL_TOKEN = os.environ["TOOL_TOKEN"]

ORDERS = {
    "A1001": {"status": "shipped", "eta": {"date": "2026-11-24"}},
    "A1002": {"status": "processing", "eta": {"date": "2026-11-28"}},
}


@app.post("/ladoo/order-status")
def order_status() -> dict[str, Any]:
    supplied = request.headers.get("Authorization", "")
    if not hmac.compare_digest(supplied.encode(), f"Bearer {TOOL_TOKEN}".encode()):
        abort(401)

    # With no body template, Ladoo sends the model's arguments as the JSON body,
    # already checked against the tool's parameters.
    args: dict[str, Any] = request.get_json(silent=True) or {}
    order_number = str(args.get("order_number", "")).strip().upper()
    order = ORDERS.get(order_number)
    if order is None:
        return {"status": "not_found"}
    return order
