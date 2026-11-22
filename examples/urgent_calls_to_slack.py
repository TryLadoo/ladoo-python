"""Post urgent calls to Slack.

Subscribe an endpoint to ``call.flagged_urgent`` (once):

    from ladoo import Ladoo
    endpoint = Ladoo().webhook_endpoints.create(
        url="https://hooks.example.com/ladoo",
        events=["call.flagged_urgent"],
        description="Urgent calls to Slack",
    )
    print(endpoint["secret"])  # shown once: save it as LADOO_WEBHOOK_SECRET

Then run:

    export LADOO_WEBHOOK_SECRET=whsec_...
    export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
    uvicorn urgent_calls_to_slack:app --port 3000
"""

from __future__ import annotations

import os

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request

from ladoo import SignatureVerificationError, webhooks
from ladoo.types import CallDetail

app = FastAPI()

WEBHOOK_SECRET = os.environ["LADOO_WEBHOOK_SECRET"]
SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]

# Ladoo can deliver an event more than once. Use a database or Redis in production;
# a set only remembers events until the process restarts.
seen_event_ids: set[str] = set()


@app.post("/ladoo")
async def ladoo_webhook(request: Request, background: BackgroundTasks) -> dict[str, bool]:
    try:
        event = webhooks.construct_event(
            await request.body(),
            request.headers.get("Ladoo-Signature"),
            WEBHOOK_SECRET,
        )
    except SignatureVerificationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if event["type"] == "call.flagged_urgent" and event["id"] not in seen_event_ids:
        seen_event_ids.add(event["id"])
        # Ladoo waits at most 10 seconds for a 2xx, so answer first and post to Slack after.
        background.add_task(post_to_slack, event["data"]["call"])
    return {"received": True}


def post_to_slack(call: CallDetail) -> None:
    extracted = call["extracted"] or {}
    caller = extracted.get("caller_name") or call["from_number"] or "Unknown caller"
    callback = extracted.get("callback_number") or call["from_number"] or "no number"
    text = f"*Urgent call from {caller}* ({callback})\n{call['summary'] or 'No summary yet.'}"
    httpx.post(SLACK_WEBHOOK_URL, json={"text": text}, timeout=10).raise_for_status()
