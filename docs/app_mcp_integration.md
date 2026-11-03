# Application Integration

## Current behavior

The FastAPI application serves the static browser interface, provides an echo
chat with optional development MCP tool invocation, and submits explicit SQL
proposals to the separate query gateway. There is no LLM integration: ordinary
chat messages are echoed and do not generate or execute SQL.

## Configuration and deployment

MCP server configuration is read from `config/mcp_servers.json` (mounted at
`/app/config/mcp_servers.json` in Compose). The application runs on
`service_network`, not `database_network`, and receives no PostgreSQL
credentials. The Compose-published application endpoint is
`http://127.0.0.1:8080`.

When configured, `APP_GATEWAY_URL` and `APP_GATEWAY_KEY` must be supplied
together. The application keeps the gateway key server-side and sends it as
`X-Gateway-Key`; it is not exposed to browser code. Direct application startup
without gateway settings is supported, but `/api/query` responds with
`503 gateway_unavailable`.

## Application API

| Method and route | Purpose |
|---|---|
| `GET /health/live` | Application liveness and current echo mode. |
| `GET /api/mcp/status` | Independently inspect configured MCP servers and discovered tools. |
| `POST /api/chat` | Echo an ordinary message or invoke a development tool command. |
| `POST /api/query` | Submit an explicit SQL proposal to the query gateway. |

`POST /api/chat` accepts `{"message":"..."}`. It does not accept a
`session_id`. A tool command has the form:

```text
/tool <server>__<tool> {"argument":"value"}
```

Only configured tools can be called, and tool commands require
`ENABLE_DEBUG_TOOLS=true`. The current context tools accept empty argument
objects. Ordinary messages return `mode: "echo"`; tool responses return
`mode: "tool"`. MCP results are informational context and do not run SQL.

`POST /api/query` accepts `{"sql":"..."}` and requires the explicit
`X-Query-Action: submit` header. The gateway independently validates the
proposal and controls execution, suppression, and audit. See
[Gateway V1](gateway-v1.md) for the supported query and limits.

## MCP lifecycle and failure behavior

For each tool operation, the application opens a bounded Streamable HTTP MCP
session, initializes it, discovers the configured tool, invokes it, and closes
the session. Calls are concurrency-bounded; persistent connection pooling is
not implemented.

Status checks inspect servers independently. One unavailable server does not
prevent the others from being reported or used. A call to an unavailable or
unknown tool returns a controlled error; missing context is not fabricated.

## Logging and browser behavior

Application operational events are appended as sanitized JSON Lines to
`APP_LOG_PATH` (Compose mounts a persistent application log volume). This is
separate from the gateway's SQLite query audit. Full chat text, tool arguments,
credentials, and full context results are not logged by default. The
application does not expose a logs API, so the browser Logs panel explains
that logs are unavailable there.

The browser UI supports English and German, local display preferences,
suggestion completion, individual MCP tool shortcuts, and the separate query
proposal form. It does not persist chat messages or expose gateway credentials.

## Limitations

- No LLM, natural-language query generation, or chat-driven SQL execution.
- The available database is a synthetic connectivity fixture, not the planned
  synthetic AKTIN/i2b2 evaluation dataset.
- No user identity or authorization layer; development tool commands must not
  be enabled on an untrusted deployment.
- No application log-reading API or browser log viewer.
- No claim of production readiness.

## Verification

The application test suite covers request validation, echo and tool behavior,
status reporting, gateway configuration and forwarding, and static asset
serving. Run it with the Docker test target described in
[Operations](operations.md#tests-and-mcp-smoke-check). The separate MCP smoke
check verifies discovery and invocation against running MCP containers.
