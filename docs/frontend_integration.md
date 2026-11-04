# Frontend Integration

The plain HTML/CSS/JavaScript frontend is served by the FastAPI application
from `application/static/`; it has no separate build step. It preserves the
Echo/developer tool workflow and explicit SQL proposal form, and adds a
separate Assistant mode when the backend feature is enabled. See
[LLM integration](llm-integration.md) for the assistant API and scope.

## Routes and workflows

Static routes include `GET /`, `/static/style.css`, `/static/app.js`, and the
JavaScript/CSS modules. The UI uses these application APIs:

| UI action | Route | Result |
|---|---|---|
| Echo / developer tools | `POST /api/chat` | Ordinary text is echoed; explicit `/tool` commands retrieve configured MCP context when enabled. |
| MCP status drawer | `GET /api/mcp/status` | Displays each server status independently. |
| Explicit SQL proposal | `POST /api/query` | Sends user-entered SQL with `X-Query-Action: submit`; gateway response is shown. |
| Assistant mode | `POST /api/assistant` | Sends the natural-language question with the action header; app gathers context, asks the model, and submits proposed SQL to the gateway. |

The assistant mode is not a display-only model call: after the model proposes
SQL, the application submits it to the gateway, which may execute its fixed
read-only query. The composer includes a scope and synthetic-data notice.
Assistant scope is only the total row count in
`public.patient_dimension`. A gateway-suppressed count is displayed as
suppressed, not as zero.

The browser does not contact MCP, the model provider, PostgreSQL, or the
gateway directly. Gateway and provider credentials stay in the application
environment. `X-Query-Action` makes a client action explicit; it is not
authentication.

## Presentation and local preferences

The interface supports German and English, dark/light/system themes, display
preferences, suggestion chips, prefix completion, MCP tool shortcuts, and
safe text rendering. Preferences are stored in versioned browser local
storage; chat history is not persisted there. Dynamic question, SQL, and
response content is written as text, not HTML.

There is a known copy inconsistency: `demoNotice` and `aboutBody` translations
in `application/static/js/i18n.js` still say no language model is connected,
although the assistant mode now exists. This documentation-only change does
not alter those frontend strings.

## Limits

`GET /health/live` currently returns `{"status":"running","mode":"echo"}`
with a hard-coded mode label; it does not report `LLM_ENABLED` or readiness of
the model, MCP services, gateway, or database. Use `/api/mcp/status` for MCP
availability, and gateway `/health/ready` for database readiness.

There is no browser authentication or authorization. The default Compose
binding is loopback-only, but a network-exposed deployment needs additional
access controls. The Logs panel is not backed by a log-reading endpoint.
