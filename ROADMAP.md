# Roadmap

What we plan to do next, roughly in order. Nothing here has a date.

- **Publish to PyPI**, so `pip install ladoo` works. Until then, install from GitHub (see the README).
- **Regenerate on every API version.** Pick up each new dated version of the OpenAPI document, with a changelog entry for what changed.
- **Webhook payload types from the API.** The OpenAPI document doesn't describe webhook payloads yet, so `ladoo.types.webhooks` follows the docs by hand. Once the document includes them, they'll be generated like everything else.
- **Response metadata.** A way to read `RateLimit-*` headers and the `Ladoo-Version` a response used, without dropping to `httpx`.

Ideas and requests: open an issue.
