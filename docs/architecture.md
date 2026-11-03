# Current Architecture

This repository contains a local Docker Compose prototype with a browser UI,
FastAPI application, deterministic query gateway, and three MCP context
services. There is no LLM integration.

```text
 Browser UI
    | chat, context, and query requests
    v
 FastAPI application --------------------------+
    | MCP context requests                     | SQL proposal + X-Gateway-Key
    v                                           v
 MCP context services                    FastAPI query gateway ---- PostgreSQL
 - mcp-schema                            (policy, execution, audit)
 - mcp-constraints
 - mcp-examples
    returns static context
```

The application serves the browser UI and API. Its MCP client calls the
configured context services for schema, query policy, and examples. Its query
route forwards a proposed SQL string to the gateway using the server-side
`APP_GATEWAY_KEY`. The browser does not receive this credential. The gateway
independently validates the proposal, executes gateway-owned SQL, applies
output suppression, and records audit events. Context returned by MCP services
is informational and does not authorize a query. See [Gateway V1](gateway-v1.md)
for current gateway behavior and limits.

The gateway is attached to both the Compose service network and the internal
database network. The application and MCP services are attached only to the
service network; PostgreSQL is attached only to the database network. The
application can start without gateway configuration, but query submission
returns `503 gateway_unavailable` until the gateway URL and key are configured.
Docker network membership and MCP Host-header validation are not authentication
or complete security boundaries.

The MCP services expose Streamable HTTP at their internal Compose addresses:

| Compose service | MCP tool | Internal endpoint |
|---|---|---|
| `mcp-schema` | `get_schema` | `http://mcp-schema:8000/mcp` |
| `mcp-constraints` | `get_query_policy` | `http://mcp-constraints:8000/mcp` |
| `mcp-examples` | `get_examples` | `http://mcp-examples:8000/mcp` |

Compose does not publish MCP ports on the host. Each service reads its own
versioned JSON context document, has no database credentials, and does not
connect to PostgreSQL.

The Dockerfiles use Python 3.12. Gateway runtime dependencies are ranges in
`gateway/requirements.txt`; they are not an exact lock. MCP runtime
dependencies are ranges in `mcp_servers/requirements.txt`, which constrains
`mcp` to `>=1.20,<2`. The exact MCP SDK version in
`docs/mcp-runtime-requirements.txt` is 1.30.0, but that snapshot is not
installed by the MCP Dockerfile, which installs the range-based requirements.

The optional Compose `local-db` profile defines a PostgreSQL 16 service and a
small fixture. Compose uses `DB_NAME` for both PostgreSQL initialization and
the gateway connection; the role initialization grants access to that
database and takes its password from `DB_PASSWORD` via `QUERY_RO_PASSWORD`.
Initialization scripts run only when PostgreSQL initializes an empty data
volume. The fixture is not the planned synthetic AKTIN/i2b2 evaluation
dataset.
