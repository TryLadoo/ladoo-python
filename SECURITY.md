# Security

Please don't report security problems in public issues.

Email **support@tryladoo.com** with "Security" in the subject. Include what you found, how to reproduce it and the version you tested. We'll confirm we've received it and keep you posted while we fix it. Our disclosure policy is at https://tryladoo.com/security#disclosure.

This covers this library. For problems in the Ladoo service itself, use the same address.

If an API key or signing secret leaks, revoke it under **Settings → Developers** in Ladoo (or with `client.api_keys.revoke(...)` and `client.webhook_endpoints.rotate_secret(...)`) before anything else.
