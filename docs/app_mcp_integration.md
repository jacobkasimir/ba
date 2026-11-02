# Application-to-MCP Integration

## Purpose

Connect the FastAPI application to the three context MCP servers.

No LLM or SQL execution is implemented in this stage.

## Configuration

File: config/mcp_servers.json

Configured servers:
- schema
- constraints
- examples

Tool names:
- schema__get_schema
- constraints__get_query_policy
- examples__get_examples

## Deployment

The application runs in Docker on service_network.

Host endpoint:
http://127.0.0.1:8080

The application is not attached to database_network.
It receives no PostgreSQL credentials.

## MCP session lifecycle

Each operation:
1. Opens a connection.
2. Initializes MCP.
3. Discovers the tool set.
4. Optionally invokes a configured tool.
5. Closes the connection.

Connections are bounded by a timeout.
Concurrency is bounded.

Persistent connection pooling is not implemented.

## Development API

GET /health/live
GET /api/mcp/status
POST /api/chat

Ordinary messages use echo mode.

Development command:
 /tool server__tool {}

Only configured tools can be invoked.

## Failure behavior

One unavailable MCP server does not stop the application.

Calls to unavailable tools return a controlled error.
No replacement context is fabricated.

The behavior of full context assembly for LLM generation is not yet
implemented.

## Logging

Application events are appended as JSONL.

These operational logs are separate from the gateway query audit.

Full messages, credentials, and complete context results are not logged
by default.

A browser log viewer is not added by this implementation.

## Limitations

- Development-only tool commands.
- No user authentication.
- Loopback-only published application port.
- No LLM.
- No gateway submission from the application.
- No patient data.
- No full synthetic i2b2 dataset.
- No claim of production readiness.

## Verification record

Date:
Source commit:

- [ ] Application unit tests passed.
- [ ] All three tools work through /api/chat.
- [ ] Malformed requests are rejected.
- [ ] Unknown tools are rejected.
- [ ] One-server failure is isolated.
- [ ] Recovery after restarting a server works.
- [ ] JSONL records are valid.
- [ ] Application has no DB credentials.
- [ ] Existing gateway and MCP tests pass.