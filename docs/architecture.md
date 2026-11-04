# Current Architecture

The prototype has four distinct application workflows. Echo and `/tool`
commands remain available regardless of whether the optional assistant is
enabled. The browser talks only to the application; the application holds
service credentials.

```mermaid
flowchart LR
  UI[Browser UI]
  APP[FastAPI application]
  MCP[Three MCP context services]
  LLM[Configured Chat Completions deployment]
  GW[Query gateway]
  DB[(PostgreSQL)]

  UI -->|POST /api/chat: echo or explicit /tool| APP
  UI -->|POST /api/query: explicit SQL + action header| APP
  APP -->|POST /query + X-Gateway-Key| GW
  UI -->|POST /api/assistant: assistant mode only| APP
  APP -->|schema, policy, examples; arguments {}| MCP
  MCP -->|curated context| APP
  APP -->|question + context; JSON Schema decision| LLM
  LLM -->|proposed SQL or unsupported| APP
  APP -->|proposal; no natural-language question| GW
  GW -->|fixed gateway-owned aggregate SQL| DB
  GW -->|validated response and suppression status| APP
  APP -->|assistant outcome| UI
```

`POST /api/chat` echoes ordinary messages. If `ENABLE_DEBUG_TOOLS=true`, a
message in `/tool <server>__<tool> {json}` form invokes one configured MCP
tool. These direct tool results are context only; they do not submit SQL.

`POST /api/query` is the explicit SQL workflow. It accepts `{"sql":"..."}`
and requires `X-Query-Action: submit`. The application sends the SQL to the
gateway's `POST /query` endpoint using `X-Gateway-Key`.

`POST /api/assistant` is a separate optional workflow. The application loads
all three fixed MCP documents concurrently, sends the question and context to
the configured model, then submits a proposed SQL string to the gateway. The
model does not execute SQL. The application does not execute SQL either; the
gateway validates the proposal and runs its own fixed SQL if it approves it.
This assistant route therefore may cause a gateway-approved read-only query
without a separate SQL form submission. The browser must present that action
clearly.

The supported natural-language scope is only the total number of rows in
`public.patient_dimension`, using the proposal
`SELECT COUNT(*) FROM public.patient_dimension`. This is a synthetic
connectivity fixture, not clinical text-to-SQL. The gateway accepts only the
exact parsed structure of that query and executes its own count statement.
Its SQL policy cannot establish that the proposed query correctly answers
the user's natural-language intent.

MCP context is informational, not authorization. The prompt cannot enforce
query policy. The gateway alone enforces SQL structure, read-only execution,
audit, and output suppression. The proposal returned as `proposed_sql` must
not be described as executed SQL; the gateway response has a separate
`executed_sql` field. Suppressed `null` counts remain unknown/suppressed and
must never be rendered as zero. See [LLM integration](llm-integration.md) and
[Gateway policy](policy.md) for contracts and limitations.

## Compose network and database

The application and MCP services are on `service_network`. The gateway joins
`service_network` and the internal `database_network`; PostgreSQL joins only
`database_network`. Compose publishes application and gateway ports on
loopback and publishes no MCP ports. The default application gateway URL is
`http://host.docker.internal:8001`, overridable with `APP_GATEWAY_URL`.
Container networking is not authentication.

The optional `local-db` profile uses PostgreSQL 16. With default settings,
`DB_NAME` is consistently passed to PostgreSQL and the gateway, and the init
scripts create the gateway's default `user` role and grant it access to
`public.patient_dimension`. There is a configuration caveat: `DB_USER` is
overridable for the gateway, while `database/init/02-role.sh` always creates
the literal role `user`. Changing `DB_USER` without changing the init script
therefore breaks the local database login. Initializers run only for a new
PostgreSQL data volume. The 20-row fixture is not the planned AKTIN/i2b2
evaluation dataset.

The Python Docker images use Python 3.12. Runtime dependency files use version
ranges rather than a complete lock file. The MCP runtime requirement is
`mcp>=1.20,<2`; the separate `docs/mcp-runtime-requirements.txt` snapshot is
not what the MCP Dockerfile installs.
