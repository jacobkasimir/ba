# Current Security Boundaries and Limitations

This is a local research prototype, not a production-ready or fully secure
system. No real patient data should be used with the current implementation.

## Implemented boundaries

- The gateway requires a shared `X-Gateway-Key` for `/query` and readiness.
- The gateway accepts only one parsed query structure and executes its own
  fixed SQL for that operation.
- Database execution is read-only and applies statement and lock timeouts.
- A configurable minimum-count suppression rule is applied to the aggregate.
- The gateway writes SQLite audit events and blocks execution or result
  release when required audit writes fail.
- MCP servers expose only static curated context tools. They have no database
  credentials and do not execute SQL.
- Compose publishes the gateway only on loopback (`127.0.0.1:8001`) and does
  not publish MCP service ports. MCP services and PostgreSQL occupy separate
  Compose networks, with the gateway attached to both.

## Limits and absent components

- There is no application/UI, MCP client orchestration, or LLM integration in
  this repository. No claims about model access, prompts, or patient-data flow
  to a model can be tested here.
- A shared API key is not a complete identity or authorization system.
- Docker networks and MCP Host-header validation do not provide authentication
  or a complete security boundary.
- SQLite audit records are not tamper-proof; authentication and body-validation
  failures are not included.
- Repeated-query disclosure, broad resource exhaustion, and clinical semantic
  validity are not generally controlled. Only the one fixed aggregate shape is
  currently allowed.
- The included local database initialization has mismatched database and
  password variable names, so the intended database role setup is not verified.
- The current data is a synthetic connectivity fixture, not evaluation or
  clinical data.
