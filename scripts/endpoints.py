"""The SDK's map of API operations to Python names.

Each entry names one operation in ``openapi/openapi.json`` and where it lives
on the client. ``scripts/generate.py`` reads this table and the OpenAPI
document and writes ``src/ladoo/resources/_generated.py``.

Fields:
    ns:     dotted namespace on the client, e.g. ``"agents.tools"``.
    name:   method name.
    method: HTTP method.
    path:   path exactly as in the OpenAPI document.
    args:   Python names for the path parameters, in path order.

Operations that only the dashboard uses (OAuth callbacks, session routes)
are left out. Everything else in ``/v1`` is reachable through
``client.get()``/``client.post()`` and friends.
"""

from __future__ import annotations

from typing import NamedTuple


class Endpoint(NamedTuple):
    ns: str
    name: str
    method: str
    path: str
    args: tuple[str, ...] = ()


E = Endpoint

ENDPOINTS: list[Endpoint] = [
    # Calls
    E("calls", "list", "GET", "/v1/calls"),
    E("calls", "retrieve", "GET", "/v1/calls/{id}", ("call_id",)),
    E("calls", "analytics", "GET", "/v1/analytics/calls"),
    # People
    E("people", "list", "GET", "/v1/people"),
    E("people", "create", "POST", "/v1/people"),
    E("people", "retrieve", "GET", "/v1/people/{id}", ("person_id",)),
    E("people", "update", "PATCH", "/v1/people/{id}", ("person_id",)),
    E("people", "delete", "DELETE", "/v1/people/{id}", ("person_id",)),
    # Calendar
    E("calendar.bookings", "list", "GET", "/v1/calendar/bookings"),
    E("calendar.bookings", "cancel", "POST", "/v1/calendar/bookings/{id}/cancel", ("booking_id",)),
    E("calendar.bookings", "list_for_call", "GET", "/v1/calendar/calls/{call_id}/bookings", ("call_id",)),
    E("calendar", "busy", "GET", "/v1/calendar/busy"),
    E("calendar.confirmations", "retrieve", "GET", "/v1/calendar/confirmations"),
    E("calendar.confirmations", "update", "PATCH", "/v1/calendar/confirmations"),
    E("calendar.confirmations", "send_test", "POST", "/v1/calendar/confirmations/test"),
    # Webhooks
    E("webhook_endpoints", "list", "GET", "/v1/webhook-endpoints"),
    E("webhook_endpoints", "create", "POST", "/v1/webhook-endpoints"),
    E("webhook_endpoints", "retrieve", "GET", "/v1/webhook-endpoints/{id}", ("endpoint_id",)),
    E("webhook_endpoints", "update", "PATCH", "/v1/webhook-endpoints/{id}", ("endpoint_id",)),
    E("webhook_endpoints", "delete", "DELETE", "/v1/webhook-endpoints/{id}", ("endpoint_id",)),
    E("webhook_endpoints", "send_test", "POST", "/v1/webhook-endpoints/{id}/test", ("endpoint_id",)),
    E("webhook_endpoints", "rotate_secret", "POST", "/v1/webhook-endpoints/{id}/rotate-secret", ("endpoint_id",)),
    E("webhook_endpoints.deliveries", "list", "GET", "/v1/webhook-endpoints/{id}/deliveries", ("endpoint_id",)),
    E("webhook_endpoints.deliveries", "redeliver", "POST", "/v1/webhook-deliveries/{id}/redeliver", ("delivery_id",)),
    E("webhook_event_types", "list", "GET", "/v1/webhook-event-types"),
    # Agents
    E("agents", "list", "GET", "/v1/agents"),
    E("agents", "create", "POST", "/v1/agents"),
    E("agents", "retrieve", "GET", "/v1/agents/{id}", ("agent_id",)),
    E("agents", "update", "PATCH", "/v1/agents/{id}", ("agent_id",)),
    E("agents", "delete", "DELETE", "/v1/agents/{id}", ("agent_id",)),
    E("agents", "publish", "POST", "/v1/agents/{id}/publish", ("agent_id",)),
    E("agents", "update_notifications", "PUT", "/v1/agents/{id}/notifications", ("agent_id",)),
    E("agents", "update_success_criteria", "PUT", "/v1/agents/{id}/success-criteria", ("agent_id",)),
    E("agents", "update_variables", "PATCH", "/v1/agents/{id}/variables", ("agent_id",)),
    E("agents", "update_pre_call_webhook", "PUT", "/v1/agents/{id}/pre-call-webhook", ("agent_id",)),
    E(
        "agents",
        "rotate_pre_call_webhook_secret",
        "POST",
        "/v1/agents/{id}/pre-call-webhook/rotate-secret",
        ("agent_id",),
    ),
    E("agents", "assist", "POST", "/v1/agents/{id}/assist", ("agent_id",)),
    E("agents", "start_build", "POST", "/v1/agents/{id}/build", ("agent_id",)),
    E("agents", "retrieve_build", "GET", "/v1/agents/{id}/build", ("agent_id",)),
    E("agents.tools", "list", "GET", "/v1/agents/{id}/tools", ("agent_id",)),
    E("agents.tools", "create", "POST", "/v1/agents/{id}/tools", ("agent_id",)),
    E("agents.tools", "update", "PATCH", "/v1/agents/{id}/tools/{tool_id}", ("agent_id", "tool_id")),
    E("agents.tools", "delete", "DELETE", "/v1/agents/{id}/tools/{tool_id}", ("agent_id", "tool_id")),
    E("agents.tests", "list", "GET", "/v1/agents/{id}/tests", ("agent_id",)),
    E("agents.tests", "create", "POST", "/v1/agents/{id}/tests", ("agent_id",)),
    E("agents.tests", "suggest", "POST", "/v1/agents/{id}/tests/suggest", ("agent_id",)),
    E("agents.tests", "update", "PATCH", "/v1/agents/{id}/tests/{test_id}", ("agent_id", "test_id")),
    E("agents.tests", "delete", "DELETE", "/v1/agents/{id}/tests/{test_id}", ("agent_id", "test_id")),
    E("agents.tests", "create_from_call", "POST", "/v1/calls/{id}/test", ("call_id",)),
    E("agents.tests", "publish_check", "POST", "/v1/agents/{id}/tests/publish-check", ("agent_id",)),
    E("agents.tests", "retrieve_settings", "GET", "/v1/agents/{id}/tests/settings", ("agent_id",)),
    E("agents.tests", "update_settings", "PUT", "/v1/agents/{id}/tests/settings", ("agent_id",)),
    E("agents.tests.runs", "list", "GET", "/v1/agents/{id}/tests/runs", ("agent_id",)),
    E("agents.tests.runs", "create", "POST", "/v1/agents/{id}/tests/runs", ("agent_id",)),
    E("agents.tests.runs", "retrieve", "GET", "/v1/agents/{id}/tests/runs/{run_id}", ("agent_id", "run_id")),
    E("agents.tests.runs", "cancel", "POST", "/v1/agents/{id}/tests/runs/{run_id}/cancel", ("agent_id", "run_id")),
    E("agents.guardrails", "list", "GET", "/v1/agents/{id}/guardrails", ("agent_id",)),
    E("agents.guardrails", "update", "PUT", "/v1/agents/{id}/guardrails", ("agent_id",)),
    E("agents.workflow", "retrieve_draft", "GET", "/v1/agents/{id}/workflow/draft", ("agent_id",)),
    E("agents.workflow", "update_draft", "PUT", "/v1/agents/{id}/workflow/draft", ("agent_id",)),
    E("agents.workflow", "validate", "POST", "/v1/agents/{id}/workflow/validate", ("agent_id",)),
    E("agents.workflow", "publish_draft", "POST", "/v1/agents/{id}/workflow/draft/publish", ("agent_id",)),
    E("agents.workflow", "retrieve_published", "GET", "/v1/agents/{id}/workflow/published", ("agent_id",)),
    E("agents.workflow", "export", "GET", "/v1/agents/{id}/workflow/export", ("agent_id",)),
    E("agents.workflow", "import_file", "POST", "/v1/agents/{id}/workflow/import", ("agent_id",)),
    E("agents.workflow", "assist", "POST", "/v1/agents/{id}/workflow/assist", ("agent_id",)),
    E("agents.workflow", "test_code", "POST", "/v1/agents/{id}/workflow/code/test", ("agent_id",)),
    E("agents.versions", "list", "GET", "/v1/agents/{id}/versions", ("agent_id",)),
    E("agents.versions", "retrieve", "GET", "/v1/agents/{id}/versions/{v}", ("agent_id", "version")),
    E("agents.versions", "diff", "GET", "/v1/agents/{id}/versions/{a}/diff/{b}", ("agent_id", "a", "b")),
    E("agents.versions", "restore", "POST", "/v1/agents/{id}/versions/{v}/restore", ("agent_id", "version")),
    E("agents.knowledge_bases", "list", "GET", "/v1/agents/{id}/knowledge-bases", ("agent_id",)),
    E("agents.knowledge_bases", "set", "PUT", "/v1/agents/{id}/knowledge-bases", ("agent_id",)),
    E("agents.scripts", "list", "GET", "/v1/agents/{id}/scripts", ("agent_id",)),
    E("agents.scripts", "set", "PUT", "/v1/agents/{id}/scripts", ("agent_id",)),
    # Knowledge
    E("knowledge_bases", "list", "GET", "/v1/knowledge-bases"),
    E("knowledge_bases", "create", "POST", "/v1/knowledge-bases"),
    E("knowledge_bases", "retrieve", "GET", "/v1/knowledge-bases/{id}", ("knowledge_base_id",)),
    E("knowledge_bases", "update", "PATCH", "/v1/knowledge-bases/{id}", ("knowledge_base_id",)),
    E("knowledge_bases", "delete", "DELETE", "/v1/knowledge-bases/{id}", ("knowledge_base_id",)),
    E("knowledge_bases", "search", "POST", "/v1/knowledge-bases/{id}/search", ("knowledge_base_id",)),
    E("knowledge_bases", "add_answer", "POST", "/v1/knowledge-bases/{id}/answers", ("knowledge_base_id",)),
    E("knowledge_bases", "upload_file", "POST", "/v1/knowledge-bases/{id}/files", ("knowledge_base_id",)),
    E("knowledge_bases.sources", "create", "POST", "/v1/knowledge-bases/{id}/sources", ("knowledge_base_id",)),
    E(
        "knowledge_bases.sources",
        "retrieve",
        "GET",
        "/v1/knowledge-bases/{id}/sources/{source_id}",
        ("knowledge_base_id", "source_id"),
    ),
    E(
        "knowledge_bases.sources",
        "update",
        "PATCH",
        "/v1/knowledge-bases/{id}/sources/{source_id}",
        ("knowledge_base_id", "source_id"),
    ),
    E(
        "knowledge_bases.sources",
        "delete",
        "DELETE",
        "/v1/knowledge-bases/{id}/sources/{source_id}",
        ("knowledge_base_id", "source_id"),
    ),
    E(
        "knowledge_bases.sources",
        "refresh",
        "POST",
        "/v1/knowledge-bases/{id}/sources/{source_id}/refresh",
        ("knowledge_base_id", "source_id"),
    ),
    E(
        "knowledge_bases.sources",
        "retrieve_document",
        "GET",
        "/v1/knowledge-bases/{id}/sources/{source_id}/documents/{document_id}",
        ("knowledge_base_id", "source_id", "document_id"),
    ),
    # Scripts
    E("scripts", "list", "GET", "/v1/scripts"),
    E("scripts", "create", "POST", "/v1/scripts"),
    E("scripts", "upload", "POST", "/v1/scripts/files"),
    E("scripts", "retrieve", "GET", "/v1/scripts/{id}", ("script_id",)),
    E("scripts", "update", "PATCH", "/v1/scripts/{id}", ("script_id",)),
    E("scripts", "delete", "DELETE", "/v1/scripts/{id}", ("script_id",)),
    E("scripts", "generate_workflow", "POST", "/v1/scripts/{id}/generate-workflow", ("script_id",)),
    # Phone numbers
    E("phone_numbers", "list", "GET", "/v1/phone-numbers"),
    E("phone_numbers", "list_available", "GET", "/v1/phone-numbers/available"),
    E("phone_numbers", "buy", "POST", "/v1/phone-numbers"),
    E("phone_numbers", "assign_agent", "PUT", "/v1/phone-numbers/{id}/agent", ("phone_number_id",)),
    E("phone_numbers", "release", "DELETE", "/v1/phone-numbers/{id}", ("phone_number_id",)),
    # Blocked callers
    E("blocked_callers", "list", "GET", "/v1/blocked-callers"),
    E("blocked_callers", "create", "POST", "/v1/blocked-callers"),
    E("blocked_callers", "delete", "DELETE", "/v1/blocked-callers/{id}", ("blocked_caller_id",)),
    E("blocked_callers", "retrieve_settings", "GET", "/v1/blocked-callers/settings"),
    E("blocked_callers", "update_settings", "PUT", "/v1/blocked-callers/settings"),
    # Chat widgets
    E("chat_widgets", "list", "GET", "/v1/chat-widgets"),
    E("chat_widgets", "create", "POST", "/v1/chat-widgets"),
    E("chat_widgets", "retrieve", "GET", "/v1/chat-widgets/{id}", ("widget_id",)),
    E("chat_widgets", "update", "PATCH", "/v1/chat-widgets/{id}", ("widget_id",)),
    E("chat_widgets", "delete", "DELETE", "/v1/chat-widgets/{id}", ("widget_id",)),
    # Voices
    E("voices", "list", "GET", "/v1/voices"),
    E("voices", "retrieve", "GET", "/v1/voices/{id}", ("voice_id",)),
    E("voices", "speech", "POST", "/v1/voices/{id}/speech", ("voice_id",)),
    # Workspace and team
    E("workspace", "retrieve", "GET", "/v1/workspace"),
    E("workspace", "update", "PATCH", "/v1/workspace"),
    E("workspace", "attention", "GET", "/v1/attention"),
    E("members", "list", "GET", "/v1/members"),
    E("members", "create", "POST", "/v1/members"),
    E("members", "update", "PATCH", "/v1/members/{user_id}", ("user_id",)),
    E("members", "delete", "DELETE", "/v1/members/{user_id}", ("user_id",)),
    E("invitations", "list", "GET", "/v1/invitations"),
    E("invitations", "create", "POST", "/v1/invitations"),
    E("invitations", "resend", "POST", "/v1/invitations/{id}/resend", ("invitation_id",)),
    E("invitations", "delete", "DELETE", "/v1/invitations/{id}", ("invitation_id",)),
    E("teams", "list", "GET", "/v1/teams"),
    E("teams", "create", "POST", "/v1/teams"),
    E("teams", "update", "PATCH", "/v1/teams/{id}", ("team_id",)),
    E("teams", "delete", "DELETE", "/v1/teams/{id}", ("team_id",)),
    E("teams", "add_member", "POST", "/v1/teams/{id}/members", ("team_id",)),
    E("teams", "remove_member", "DELETE", "/v1/teams/{id}/members/{user_id}", ("team_id", "user_id")),
    E("teams", "update_on_call", "PUT", "/v1/teams/{id}/on-call", ("team_id",)),
    E("api_keys", "list", "GET", "/v1/api-keys"),
    E("api_keys", "create", "POST", "/v1/api-keys"),
    E("api_keys", "revoke", "DELETE", "/v1/api-keys/{id}", ("api_key_id",)),
    E("audit_events", "list", "GET", "/v1/audit-events"),
    E("billing", "retrieve", "GET", "/v1/billing"),
    # Agencies
    E("clients", "list", "GET", "/v1/clients"),
    E("clients", "create", "POST", "/v1/clients"),
    E("clients", "update", "PATCH", "/v1/clients/{id}", ("client_id",)),
    E("clients", "usage", "GET", "/v1/clients/usage"),
    E("clients", "update_billing", "PUT", "/v1/clients/{id}/billing", ("client_id",)),
    E("clients", "delete_billing", "DELETE", "/v1/clients/{id}/billing", ("client_id",)),
    E("brand", "retrieve", "GET", "/v1/brand"),
    E("brand", "update", "PATCH", "/v1/brand"),
    E("brand", "upload_logo", "PUT", "/v1/brand/logos/{variant}", ("variant",)),
    E("brand", "delete_logo", "DELETE", "/v1/brand/logos/{variant}", ("variant",)),
    # Integrations
    E("integrations.crm", "retrieve", "GET", "/v1/integrations/crm"),
    E("integrations.crm", "options", "GET", "/v1/integrations/crm/options"),
    E("integrations.crm", "preview_people_import", "GET", "/v1/integrations/crm/people-import"),
    E("integrations.crm", "import_people", "POST", "/v1/integrations/crm/people-import"),
    E("integrations.calendar", "retrieve", "GET", "/v1/integrations/calendar"),
    E("integrations.calendar", "booking_calendars", "GET", "/v1/integrations/booking-calendars"),
    # Testing
    E("test_sessions", "create", "POST", "/v1/test-sessions"),
    E("test_sessions", "delete", "DELETE", "/v1/test-sessions/{room_name}", ("room_name",)),
]
