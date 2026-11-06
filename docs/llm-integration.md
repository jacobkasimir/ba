# Optional LLM Assistant Integration

This page describes the implemented optional assistant. It supports only a
total row count for the synthetic `public.patient_dimension` table. It is not
general clinical text-to-SQL, and the current 20-row fixture is not an
evaluation dataset.

## Request flow and module responsibilities

```text
POST /api/assistant {question} + X-Query-Action: submit
       |
       v
AssistantService
  1. ContextLoader -> schema, constraints, examples MCP tools (all arguments {})
  2. LLMClient -> structured propose/unsupported decision
  3. If proposed, GatewayClient -> POST /query {sql}
       |
       v
Gateway validates, audits, executes its fixed SQL, and suppresses if needed
       |
       v
AssistantReply {status, proposed_sql, count, reason, answer}
```

The assistant request is an explicit user action in the Assistant UI mode.
After a supported proposal, the application automatically submits that SQL
to the gateway. The model itself does not execute SQL; the gateway alone
decides whether to run its own fixed statement. The assistant response labels
the model's string `proposed_sql`, not executed SQL. The gateway separately
returns `executed_sql` on the explicit `/api/query` route, but that field is
not copied into `AssistantReply`.

Responsibilities:

| Module | Responsibility | Explicitly does not do |
|---|---|---|
| `assistant_api.py` | `POST /api/assistant`, request/action-header checks, safe error codes | Authenticate a user or execute SQL |
| `assistant_models.py` | Strict request, structured LLM decision, normalized outcome, and reply schemas | Establish semantic correctness or authorization |
| `assistant_context.py` | Concurrently load three configured JSON objects; 8-second overall timeout and 64 KiB combined bound | Treat context as approval or fabricate missing context |
| `assistant_bindings.py` | Bind the fixed context tools and normalize the gateway count response | Enforce SQL policy or execute SQL |
| `llm_client.py` | Send question/context to Chat Completions and validate a structured decision | Call MCP tools, access the database, or submit SQL |
| `assistant_service.py` | Orchestrate context → model → gateway; bound concurrency and total request time | Repair rejected SQL or generate a result narrative |
| `gateway_client.py` | Send `{ "sql": ... }` with `X-Gateway-Key`; bound response size/time and normalize transport/status failures | Decide whether SQL is safe |

The existing `POST /api/chat` Echo/debug flow, `GET /api/mcp/status`, and
explicit `POST /api/query` workflow remain separate. MCP context retrieval
through `/tool` returns metadata only. See [Application integration](app_mcp_integration.md).

## Scope and trust boundaries

The only supported question is the total row count of
`public.patient_dimension`, proposed as:

```sql
SELECT COUNT(*) FROM public.patient_dimension
```

Questions requiring filters, joins, patient-level records, other tables,
clinical interpretation, or other statistics should return `unsupported`.
The gateway parses one statement and compares its syntax tree with the
approved pattern. If accepted, it runs its own SQL:

```sql
SELECT COUNT(*) AS patient_count FROM public.patient_dimension
```

The model receives the current question and all three curated MCP documents
(schema, policy, and examples), together with the system prompt. It does not
receive previous chat messages, database credentials, gateway credentials,
database records, query results, or the gateway response. The gateway
receives the proposed SQL and service-to-service key, not the question or MCP
context. By default the application does not log assistant questions or model
output. A temporary `LLM_LOG_RAW_RESPONSES=true` diagnostic option logs the
provider's raw response body; see [Operations](operations.md#troubleshooting).

MCP data and prompt instructions are informational, not a security boundary.
The deterministic gateway is authoritative for policy, audit, execution, and
suppression. Gateway validation proves only that the SQL has the approved
syntax; it cannot prove that the count is a semantically correct answer to the
question. A proposal must not be described as executed SQL. A suppressed
`null` count is not zero.

## HTTP contracts

`POST /api/assistant` requires:

```http
Content-Type: application/json
X-Query-Action: submit
```

```json
{"question":"How many records are in the synthetic patient table?","language":"en"}
```

`question` is trimmed, must be nonblank, and is limited to 4,000 characters;
`language` is `de` or `en` and follows the selected UI language. Extra request
fields are rejected. Typical response bodies include nullable fields because
the response model does not omit `null` values:

```json
{"status":"completed","proposed_sql":"SELECT COUNT(*) FROM public.patient_dimension","count":20}
```

```json
{"status":"suppressed","proposed_sql":"SELECT COUNT(*) FROM public.patient_dimension","count":null}
```

```json
{"status":"unsupported","proposed_sql":null,"count":null,"reason":"The question is not a database query request.","answer":"A general answer to the question."}
```

When the model returns an empty SQL string, the application treats it as no
proposal. It returns the model's normal answer and reason, skips the gateway,
and the UI adds a localized notice that no database query was made and no SQL
was checked or sent. The UI language setting controls that notice; the model's
normal answer follows the selected UI language, even when the question itself
uses the other language. That answer is limited to one to three concise bullet
points, each on its own line. No supported-query example is shown in this case.

```json
{"status":"rejected","proposed_sql":"SELECT * FROM public.patient_dimension","count":null}
```

`completed`, `suppressed`, `unsupported`, and `rejected` are assistant result
statuses. A gateway SQL rejection is represented as `rejected`; a proposal
that the gateway accepts can complete or be suppressed. Operational errors
instead return non-2xx responses with `detail.code`, for example
`assistant_not_configured`, `context_unavailable`, `llm_provider_error`,
`invalid_llm_response`, `gateway_timeout`, or `invalid_gateway_response`.

For comparison, the gateway's `POST /query` response schema is:

```json
{
  "request_id":"example-id",
  "status":"ok",
  "columns":["patient_count"],
  "rows":[{"patient_count":20}],
  "executed_sql":"SELECT COUNT(*) AS patient_count FROM public.patient_dimension",
  "policy_version":"demo-patient-count-v1"
}
```

Suppression is `status: "suppressed"` and
`rows: [{"patient_count": null}]`. `POST /api/query` returns this gateway
response. The assistant API normalizes it to `status: "suppressed"` and
`count: null`.

## Configuration and startup behavior

The Compose application service receives these values from Compose
interpolation. `.env.example` leaves the feature disabled by default.

| Variable | Required | Meaning |
|---|---|---|
| `LLM_ENABLED` | No; defaults to `false` | Only the value `true` (case-insensitive) enables assistant construction. |
| `LLM_BASE_URL` | When enabled | Absolute HTTP(S) provider base URL, without credentials, query, or fragment. The client appends `chat/completions`. |
| `LLM_API_KEY` | When enabled | Bearer credential held in the application container environment. |
| `LLM_MODEL` | When enabled | Provider-accepted model/deployment identifier; no model list is discovered by the app. |
| `APP_GATEWAY_URL` | Required for assistant | Paired with `APP_GATEWAY_KEY`; Compose defaults to `http://host.docker.internal:8001`. |
| `APP_GATEWAY_KEY` | Required for assistant | Gateway service credential, mapped from `GATEWAY_API_KEY` in Compose. |
| `APP_GATEWAY_TIMEOUT` | No | Gateway timeout in seconds; Compose sets 12. |

If `LLM_ENABLED` is false or absent, the application still starts, Echo and
debug workflows remain available, and `/api/assistant` returns
`503 assistant_not_configured`. If enabled without gateway settings or any of
`LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`, application startup raises a
configuration error. An incomplete `APP_GATEWAY_URL`/`APP_GATEWAY_KEY` pair
also fails startup. URL syntax is validated at startup; provider credentials,
model existence, provider connectivity, MCP connectivity, and database
readiness are not verified then. MCP calls are lazy. A dependency failure
during a request becomes a controlled error.

Compose interpolation gives an exported shell variable precedence over `.env`.
For example, a shell-exported `LLM_ENABLED=false` overrides
`LLM_ENABLED=true` in `.env`; the running container must be recreated after
the effective value changes.

## Provider contract

`LLMClient` implements a constrained OpenAI-style Chat Completions contract;
this is not a claim of compatibility with every OpenAI-compatible service.
It sends:

- `POST {LLM_BASE_URL}/chat/completions` with Bearer authentication;
- a system message and a user message containing JSON for `question` and
  `context`;
- `response_format` of type `json_schema`, name `query_decision`, strict mode,
  using the `LLMDecision` schema;
- `max_completion_tokens: 512`.
- No temperature or other sampling settings are sent; provider/model defaults
  apply.

The selected deployment must accept that structured-output schema and the
`max_completion_tokens` parameter, and return a non-streaming JSON response
with `choices[0].message.content` containing a valid decision and
`choices[0].finish_reason == "stop"`. Refusals and tool calls are rejected.
The client does not retry, fall back to another parameter, or repair output.
Successful bodies are limited to 64 KiB; provider errors are exposed to the
application as safe codes. The development evaluation runner can opt in to
bounded provider diagnostic fields using `LLM_EVAL_PROVIDER_DIAGNOSTICS=1`.

For KI:connect deployments, use the versioned API base URL and a model ID
returned by `GET /v1/models`. In this repository's observed provider
contract, `max_tokens` was rejected and the client uses
`max_completion_tokens`. Deployment support for strict JSON Schema must still
be confirmed; a 400 provider response is reported as `llm_provider_error`.

## Errors and limits

| Condition | Behavior |
|---|---|
| Missing explicit action header | `403 explicit_query_action_required` |
| Assistant disabled | `503 assistant_not_configured` |
| Any MCP call fails, times out, returns malformed context, or combined context exceeds 64 KiB | `503 context_unavailable`; model is not called |
| More than two in-process assistant calls are active for over 250 ms waiting | `503 assistant_busy` |
| Assistant orchestration exceeds 45 seconds | `504 assistant_timeout` |
| Provider timeout | `504 llm_timeout` |
| Provider non-200 response | `502 llm_provider_error` |
| Provider transport unavailable | `502 llm_unavailable` |
| Invalid, truncated, refused, tool-call, or oversized provider response | `502 invalid_llm_response` |
| Gateway result has wrong shape | `502 invalid_gateway_response` |

Context calls run concurrently and have an 8-second aggregate timeout. The
LLM client has a 20-second timeout. Gateway calls use `APP_GATEWAY_TIMEOUT`.
Concurrency limits are per application process, not distributed. There is no
conversation memory, SQL repair loop, provider retry, or narrative result
generation.

## Privacy and operational logging

Only use synthetic, non-sensitive questions with an approved provider. A
question typed in assistant mode is sent to the configured model alongside
the static context documents. The result count is obtained only after the
model call and is not sent back to the model. Browser chat history is not
persisted by the UI.

The application gateway key and provider API key are held server-side in the
application container environment, normally sourced through ignored local
`.env` configuration. They are not exposed to browser code. The application
has no user authentication or authorization; `X-Query-Action: submit` only
marks explicit client intent. Compose publishes the app and gateway on
loopback for local development. These assumptions are not suitable for an
untrusted or public deployment.

Application JSONL events cover echo character counts, MCP status, direct tool
names, tool errors, and context versions; they omit full echo text, tool
arguments, and context results. The assistant route does not log the question,
prompt, proposal, or result by default. When raw-response diagnostics are
enabled, the provider response is written to container stdout, bounded to
64 KiB for successful responses and 8 KiB for non-200 responses. Treat those
logs as potentially sensitive and disable the option after debugging.
Separately, the gateway audit stores request ID,
timestamp, policy version, a SHA-256 hash of submitted SQL, event/reason, and
the gateway-owned executed SQL after execution. It does not store raw submitted
SQL or result counts. Receipt and final audit failures block execution or
result release respectively. Neither application operational logs nor
gateway audit records are tamper-proof.

## Testing and evaluation

Application tests include fake orchestration services and `httpx.MockTransport`
checks for provider and gateway HTTP contracts. Gateway tests replace database
execution with mocks. MCP unit tests call tools in-process; the separate
`mcp_servers/smoke_test.py` exercises MCP initialization, discovery, and calls
against containers. No repository test currently joins a live model, live MCP
servers, live gateway, and live PostgreSQL in one automated full end-to-end
test.

`evaluation/development/run_assistant_intent_eval.py` makes four real provider
requests using the versioned development cases and static synthetic context.
It checks expected action and exact supported SQL. It does not call MCP or the
gateway and may incur provider charges. See [Evaluation status](evaluation-plan.md).

## Repository consistency notes (2026-11-04)

- `application/app/assistant_bindings.py` now calls `MCPManager.call_tool`
  with the qualified `<server>__<tool>` name, and normalizes the actual
  `columns`/`rows[{patient_count}]` gateway response. Its adjacent function
  docstrings still contain older “replace/verify this adapter” wording; those
  comments are stale, but the current method call matches
  `application/app/mcp_client.py`.
- `application/app/gateway_client.py` sends `{"sql": ...}`, which matches
  `gateway/app/schemas.py`; its `build_gateway_payload` docstring still says
  to verify/add fields and is stale.
- Explicit SQL length limits differ: `application/app/query_api.py` accepts up
  to 10,000 characters, while `gateway/app/schemas.py` accepts 4,000. The
  application can therefore accept an explicit proposal that the gateway
  rejects. Assistant-generated SQL is separately limited to 2,000 characters.
- `application/tests/test_query_integration.py` still uses illustrative
  `{"status":"ok","count":20}` and suppressed fixtures for the explicit
  query passthrough tests. The real gateway returns `columns`, `rows`,
  `executed_sql`, and `policy_version`; those fixtures do not verify the real
  gateway response contract. Assistant normalization fixtures use the current
  gateway shape.
- `application/static/js/i18n.js` still has `demoNotice` and `aboutBody`
  translations claiming no language model is connected. The assistant mode
  exists; this documentation-only update does not alter frontend code.
- The database defaults align (`DB_NAME=aktin`, role `user`, and the
  `patient_dimension` table), but `DB_USER` is configurable in Compose while
  `database/init/02-role.sh` hard-codes `CREATE ROLE user`. A custom database
  user therefore needs a corresponding init-script change.
