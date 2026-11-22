# Examples

Each file runs on its own. Install the library and the example's framework:

```sh
pip install "git+https://github.com/TryLadoo/ladoo-python" fastapi uvicorn flask
```

| File | What it does |
| --- | --- |
| [`urgent_calls_to_slack.py`](urgent_calls_to_slack.py) | FastAPI webhook receiver. Verifies each event and posts urgent calls to a Slack channel. |
| [`custom_tool_flask.py`](custom_tool_flask.py) | Flask endpoint for an `order_status` custom tool the agent can call mid-call. |
| [`export_calls_csv.py`](export_calls_csv.py) | Writes the last N days of calls to a CSV file. |

They read secrets from environment variables. Nothing here should be committed with a real key or secret in it.
