# Contributing

Bug reports and pull requests are welcome. For anything large, open an issue first so we can agree on the approach.

## Setup

You need [uv](https://docs.astral.sh/uv/).

```sh
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run pyright && uv run mypy
```

Tests run offline against mocked responses. `tests/test_live.py` calls the real API, read-only, and runs only when `LADOO_API_KEY` is set. Use a key for a test workspace.

## Generated code

`src/ladoo/types/_generated.py` and `src/ladoo/resources/` are generated from `openapi/openapi.json` by `scripts/generate.py`. Don't edit them by hand.

- To pick up API changes, replace `openapi/openapi.json` with the current https://api.tryladoo.com/openapi.json and run `uv run python scripts/generate.py`.
- To add a method, add a line to `scripts/endpoints.py` and regenerate.
- CI fails if the generated files don't match the generator.

## Pull requests

- Keep each one to a single change, with tests.
- Add a line under "Unreleased" in `CHANGELOG.md` if users will notice the change.
- Never put real API keys, signing secrets, phone numbers or customer data in code, tests or issues. Use 555 numbers and made-up names.
