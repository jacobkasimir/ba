# Application and MCP Integration

The FastAPI application serves the static browser UI and exposes separate
Echo/debug, MCP status, explicit SQL, and optional assistant workflows. The
application-side MCP client connects to three configured Streamable HTTP
services. See [LLM integration](llm-integration.md) for the natural-language
workflow and model contract; this page focuses on application routes and MCP.

## Application routes

| Method and route | Request | Behavior |
|---|---|---|
| `GET /health/live` | — | Returns application liveness and the static `mode: "echo"` label. This label does not report `LLM_ENABLED`. |
| `GET /api/mcp/status` | — | Inspects configured MCP servers independently and returns each server's availability and tools. |
| `POST /api/chat` | `{"message":"..."}` | Echoes ordinary text; `/tool <server>__<tool> {json}` calls an allowed MCP tool only when debug tools are enabled. |
| `POST /api/query` | `{"sql":"..."}` + `X-Query-Action: submit` | Submits explicit SQL to gateway `POST /query`; returns the gateway response. |
| `POST /api/assistant` | `{"question":"..."}` + `X-Query-Action: submit` | Available only when configured; obtains MCP context, requests a model proposal, and sends a proposal to the gateway. |

The chat body field is `message`; no `session_id` is accepted. It is bounded
to 4,000 characters. `/tool` arguments must be a JSON object and the current
context tools accept `{}` only. Ordinary chat does not call the model. The
assistant route is separate, and can cause a gateway-approved read-only query
to run automatically after a proposal.

The `X-Query-Action` header is a client action marker, not authentication. The
application does not implement user identity or authorization. The gateway
key remains server-side and is sent only to the gateway as `X-Gateway-Key`.

## MCP configuration and lifecycle

`config/mcp_servers.json` configures:

| Server | Tool | Internal Compose endpoint |
|---|---|---|
| `schema` | `get_schema` | `http://mcp-schema:8000/mcp` |
| `constraints` | `get_query_policy` | `http://mcp-constraints:8000/mcp` |
| `examples` | `get_examples` | `http://mcp-examples:8000/mcp` |

For each operation, `MCPManager` creates a bounded Streamable HTTP session,
initializes it, discovers the configured tool set, calls the requested tool,
extracts a JSON object, and closes the session. Calls are not kept in a
persistent pool. Direct `/tool` requests use the qualified name
`<server>__<tool>` and are checked against the configured allow-list.

The assistant's fixed `CONTEXT_TOOLS` mapping loads all three tools with empty
arguments. `ContextLoader` calls them concurrently, expects JSON objects, and
caps the combined serialized context at 64 KiB. A failed tool or timeout
returns `context_unavailable`; the model is not called. Context descriptions
are informational. They do not authorize SQL or replace gateway enforcement.

MCP server startup and application startup do not establish that the MCP
protocol is reachable. `/api/mcp/status` tests each service independently;
`mcp_servers/smoke_test.py` performs actual MCP initialization, discovery, and
tool calls against running containers.

## Logging and browser behavior

The application appends best-effort sanitized JSONL events to `APP_LOG_PATH`.
Current events include Echo character count, MCP status, direct tool name,
tool error reason, and context version. It does not log full Echo text,
`/tool` arguments/results, assistant questions/prompts/proposals/results, or
provider/gateway keys. This application log is separate from the gateway's
SQLite audit. There is no logs API; the browser Logs panel says logs are
unavailable.

The frontend is plain HTML, CSS, and JavaScript served from
`application/static/`. It has an explicit Assistant / Echo and developer
tools selector, bilingual translations, visual preferences stored locally,
and no persisted chat history. Dynamic reply content is rendered with
`textContent`. Some translation strings still say that no LLM is connected;
see the remaining implementation inconsistencies in the main LLM guide.

## Deployment and limits

The application container is on `service_network`, not the internal database
network, and receives no PostgreSQL credentials. MCP services have no
database credentials and serve static curated metadata. The application
gateway client receives `APP_GATEWAY_KEY`; the model client receives
`LLM_API_KEY` only when enabled. Compose publishes application and gateway
ports on loopback and does not publish MCP ports.

No app authentication/authorization is implemented. `ENABLE_DEBUG_TOOLS` is
`true` in Compose for development and must not be exposed to untrusted users.
The fixture is not the planned synthetic AKTIN/i2b2 dataset. The browser's
health label `mode: "echo"` is static and should not be used to determine
assistant configuration.
