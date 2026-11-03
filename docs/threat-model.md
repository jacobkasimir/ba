# Current Security Boundaries and Limitations

This is a local research prototype, not a production-ready or fully secure
system. No real patient data should be used with the current implementation.

## Implemented boundaries

- The browser talks to the application. The application holds the
  `APP_GATEWAY_KEY` credential and sends it to the gateway as
  `X-Gateway-Key`; the credential is not returned to browser code.
- The application delegates query access to the gateway. It forwards a
  proposed SQL string, while the gateway independently validates the request
  and executes its own fixed SQL for the supported operation.
- The gateway requires a shared `X-Gateway-Key` for `/query` and readiness.
- Database execution is read-only and applies statement and lock timeouts.
- A configurable minimum-count suppression rule is applied to the aggregate.
- The gateway writes SQLite audit events and blocks execution or result
  release when required audit writes fail.
- MCP servers expose only static curated context tools. They have no database
  credentials and do not execute SQL. The application may use this context,
  but it does not authorize queries.
- Compose publishes the application and gateway only on loopback and does
  not publish MCP service ports. MCP services and PostgreSQL occupy separate
  Compose networks, with the gateway attached to both.
- The application can start without gateway configuration. In that mode,
  query submission fails closed with `503 gateway_unavailable`.

## Limits and absent components

- There is no LLM integration. No claims about model access, prompts, or
  patient-data flow to a model can be tested here.
- The application holds a reusable shared gateway credential. Compromise of
  the application or its environment exposes that credential and allows
  gateway requests. The gateway's independent fixed-query policy limits the
  supported query shape, but the shared key is not per-user authorization.
- `X-Query-Action: submit` is an explicit client action marker, not
  authentication. The application currently has no user identity or
  authorization layer; a caller who can reach it can submit proposals for the
  gateway to evaluate.
- A shared API key is not a complete identity or authorization system.
- Docker networks and MCP Host-header validation do not provide
  authentication or a complete security boundary.
- SQLite audit records are not tamper-proof; authentication and body-validation
  failures are not included.
- Repeated-query disclosure, broad resource exhaustion, and clinical semantic
  validity are not generally controlled. Only the one fixed aggregate shape is
  currently allowed.
- The current data is a synthetic connectivity fixture, not evaluation or
  clinical data.
