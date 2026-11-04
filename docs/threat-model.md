# Current Security Boundaries and Limitations

This is a local research prototype, not a production-ready or fully secure
system. Do not enter real patient data or sensitive free text. The optional
assistant sends the current question and curated context to an external or
otherwise configured model provider.

## Trust boundaries and data flow

- The browser talks to the application only. It does not receive model,
  gateway, or database credentials and does not contact MCP, the gateway, or
  PostgreSQL directly.
- `LLM_API_KEY` and `APP_GATEWAY_KEY` are held in the application container
  environment. Compose maps `GATEWAY_API_KEY` to the application's gateway
  key and the gateway's key. These are shared service credentials, not user
  identities.
- In assistant mode, the provider receives the current question, the system
  prompt, and curated schema, constraints, and examples context. It does not
  receive previous chat history, gateway/database credentials, database
  records, or query results. The user question may itself contain sensitive
  data, which is why the UI warns users not to enter it.
- The gateway receives proposed SQL and `X-Gateway-Key`; it does not receive
  the natural-language question or MCP context. It validates an exact SQL
  structure and executes gateway-owned SQL. Its parser cannot prove that the
  count is semantically appropriate for the question.
- MCP context is informational. Curated metadata and prompt rules are
  vulnerable to being incomplete or misleading and are not authorization.
  The model cannot call arbitrary tools and has no SQL execution tool.
- The model proposes SQL but does not execute it. The application submits a
  proposal to the gateway, which remains authoritative for policy, audit,
  execution, and suppression. Because the assistant automatically submits
  supported proposals, the UI must disclose that a question can cause a
  gateway-approved read-only query.
- Assistant output calls the SQL `proposed_sql`; it must not be described as
  executed SQL. The gateway separately knows its `executed_sql`. Suppression
  is represented by `null`, never zero.

## Implemented controls

- The application-to-gateway client uses a shared `X-Gateway-Key`. The
  gateway requires it on `/query` and `/health/ready` and compares it in
  constant time.
- The gateway accepts one exact parsed count-query structure, not arbitrary
  SQL execution. It uses a read-only transaction, lock/statement timeouts,
  and a restricted local database role.
- Positive counts below `MIN_CELL_COUNT` are suppressed. A count of zero is
  distinct from suppression.
- The gateway writes a SQLite receipt before evaluation and an outcome before
  releasing the response. Audit write failures block the associated action.
- MCP services expose static context documents, have no database credentials,
  and do not execute SQL.
- Compose binds application and gateway ports to loopback and does not
  publish MCP ports. This is a local development assumption, not access
  control.
- Browser dynamic content uses text rendering and chat history is not
  persisted in local storage.

## Operational logs and retention

The application writes best-effort sanitized JSONL events for echo character
counts, MCP status, direct tool names/errors, and returned context versions.
It does not log complete chat messages, `/tool` arguments/results, or assistant
questions, prompts, proposals, and counts. The application has no log-reading
API.

The gateway's SQLite audit records request ID, time, policy version, submitted
SQL hash, event/reason code, and gateway-owned executed SQL after successful
execution. It omits raw submitted SQL and result counts. Authentication and
request-body validation failures are not audited. Neither application logs
nor SQLite audit storage is tamper-proof. The browser does not store chat
history, but upstream provider retention is outside this repository's
control.

## Limits and deployment assumptions

- No user authentication or authorization exists on the application routes.
  `X-Query-Action: submit` is not authentication. Anyone who can reach the
  app can submit explicit proposals; assistant mode may automatically send
  a proposal to the gateway.
- The gateway key is shared and gives the application access as one service
  identity. It is not scoped per browser user.
- `ENABLE_DEBUG_TOOLS=true` is set in the development Compose service. It
  permits configured MCP tool commands and should not be exposed to untrusted
  users.
- Docker networks and MCP host validation are not authentication boundaries.
- Gateway policy allows only one aggregate pattern and does not generally
  prevent repeated-query inference or validate clinical meaning.
- Startup does not check provider connectivity, MCP availability, or database
  readiness. Dependency errors appear when status checks or requests run.
- The database is a 20-row synthetic connectivity fixture, not evaluation or
  clinical data. `DB_USER` can be overridden for the gateway but the local
  init script creates the fixed role `user`.
- The provider may be external. Use only approved deployments and synthetic,
  non-sensitive questions; verify provider retention, processing, and
  structured-output behavior before broader use.
