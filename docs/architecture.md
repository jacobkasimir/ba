# Current Architecture

This repository contains a local Docker Compose prototype with a deterministic
query gateway and three MCP context services. It does not yet contain the
application/UI, an MCP client/orchestrator, or an LLM integration.

```text
                    Future application / LLM (not implemented)
                       |                         |
             context requests             SQL proposal + API key
                       v                         v
       MCP context services              FastAPI query gateway ---- PostgreSQL
       - mcp-schema                      (enforces policy)
       - mcp-constraints
       - mcp-examples
          returns context
```

The diagram shows intended connections, not running integration: no component
in this repository currently connects the MCP services to the gateway.

The MCP services expose Streamable HTTP at their internal Compose addresses:

| Compose service | MCP tool | Internal endpoint |
|---|---|---|
| `mcp-schema` | `get_schema` | `http://mcp-schema:8000/mcp` |
| `mcp-constraints` | `get_query_policy` | `http://mcp-constraints:8000/mcp` |
| `mcp-examples` | `get_examples` | `http://mcp-examples:8000/mcp` |

Compose does not publish MCP ports on the host. Each service reads its own
versioned JSON context document, has no database credentials, and does not
connect to PostgreSQL. Its context is informational and does not authorize a
query. The gateway independently validates the one currently supported query,
executes gateway-owned SQL, applies output suppression, and records audit
events. See [Gateway V1](gateway-v1.md) for its current behavior and limits.

The gateway is attached to both the Compose service network and the internal
database network. The MCP services are attached only to the service network;
PostgreSQL is attached only to the database network. Docker network membership
and MCP Host-header validation are not authentication or complete security
boundaries.

The Dockerfiles use Python 3.12. Gateway runtime dependencies are ranges in
`gateway/requirements.txt`; they are not an exact lock. MCP runtime
dependencies are ranges in `mcp_servers/requirements.txt`, which constrains
`mcp` to `>=1.20,<2`. The exact MCP SDK version in
`docs/mcp-runtime-requirements.txt` is 1.30.0, but that snapshot is not
installed by the MCP Dockerfile, which installs the range-based requirements.

The optional Compose `local-db` profile defines a PostgreSQL 16 service and a
small fixture. Its initialization script currently disagrees with Compose on
the database name and password variable, so a successful gateway database
setup is not verified. The fixture is not the planned synthetic AKTIN/i2b2
evaluation dataset.

The source has no frontend, application-to-MCP client, LLM, evaluation
pipeline, or final synthetic dataset. These remain unimplemented or unresolved,
not working parts of the current system.
