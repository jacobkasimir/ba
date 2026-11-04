# Current Gateway Policy

The gateway is the deterministic enforcement boundary for both explicit
`POST /api/query` submissions and proposals automatically submitted by the
optional assistant. MCP documents and model prompt instructions do not
authorize or validate a query.

## Accepted SQL proposal

Gateway `POST /query` accepts `{"sql":"..."}` with a maximum SQL string
length of 4,000 characters. It requires the shared `X-Gateway-Key`. The
PostgreSQL parser must produce exactly one statement and the source-position
independent syntax tree must exactly match the approved structure for:

```sql
SELECT COUNT(*) FROM public.patient_dimension
```

Comments and formatting differences do not affect the tree comparison.
Aliases, filters, joins, grouping, limits, subqueries, other tables, patient
identifiers, additional statements, and other statement types are rejected.
Rejection returns HTTP 422 with a policy code. The gateway does not execute
the submitted SQL text. It maps the accepted operation to this gateway-owned
statement:

```sql
SELECT COUNT(*) AS patient_count FROM public.patient_dimension
```

The application's explicit `/api/query` request model allows up to 10,000
characters, so requests between 4,001 and 10,000 characters pass application
validation but are rejected by the gateway's 4,000-character limit. The
assistant LLM decision schema limits proposed SQL to 2,000 characters.

This policy checks SQL structure, not whether the query semantically answers
the user's natural-language question. The gateway does not receive that
question on either application submission route.

## Execution, response, suppression

Execution uses a read-only PostgreSQL transaction, one-second lock timeout,
and five-second statement timeout. The configured database role is intended
to be restricted to connection/schema/table read access. The Compose
initialization uses the same default `DB_NAME` for PostgreSQL and the gateway,
and the default `DB_USER=user` matches the role created by
`database/init/02-role.sh`. That script hard-codes role `user`; overriding
`DB_USER` without changing initialization makes the credentials inconsistent.
Init scripts run only on a new PostgreSQL data volume.

`MIN_CELL_COUNT` defaults to 5; the gateway refuses values below 5. Positive
counts below the threshold are suppressed. Zero is returned as zero; a
suppressed value is represented by status `suppressed` and
`patient_count: null`. Null must not be converted to zero. The threshold is a
demonstration default, not a resolved governance policy (Decision D-013).

The gateway response model is:

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

For a suppressed result, status is `suppressed` and the sole row contains
`{"patient_count":null}`. The application assistant adapter validates this
shape and returns normalized `completed`/`suppressed` statuses. The
`proposed_sql` in an assistant response is not the gateway's `executed_sql`.

## Authentication, audit, and errors

Gateway `/query` and `/health/ready` use constant-time comparison for the
shared `X-Gateway-Key`. This key authenticates the application service to the
gateway; it is not per-user identity. On `/query`, the gateway writes a
receipt before validation/execution and a final policy/execution outcome
before releasing a result. SQLite events include request ID, timestamp,
policy version, SHA-256 hash of submitted SQL, event and optional reason
code, plus gateway-owned executed SQL after successful execution. Raw
submitted SQL and result counts are not stored. Required audit write failures
block execution or response release. Authentication and body-validation
failures are not audited. SQLite audit storage is not tamper-proof.

The application gateway client maps 400/422 to `query_rejected`, 401/403 to
`gateway_authentication_failed`, 429 to `gateway_busy`, and other HTTP errors
to `gateway_error`. Transport timeout, unavailability, and malformed or
oversized responses have separate safe codes. The application `/api/query`
route requires `X-Query-Action: submit`; this is an explicit action marker,
not authentication.

## Limits

The policy is not general SQL support, concept validation, or clinical
semantic validation. It does not prevent repeated-query inference in
general, establish that a proposal matches the user's intent, or make this
fixture suitable for real patient data. See [Threat model](threat-model.md)
and [LLM integration](llm-integration.md).
