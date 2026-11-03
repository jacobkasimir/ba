# Current Gateway Policy

The policy enforced by code is intentionally narrow. MCP policy/context is
informational only; the deterministic gateway is the enforcement authority.

## Supported request

The gateway accepts only one PostgreSQL syntax-tree structure corresponding to
`SELECT COUNT(*) FROM public.patient_dimension`. It requires one statement,
then maps the accepted proposal to gateway-owned SQL. It does not execute an
arbitrary submitted SQL string. Aliases, filters, joins, grouping, limits,
subqueries, other tables, identifiers, and other statement types are rejected.

The gateway authenticates callers with the shared `X-Gateway-Key` value. This
does not constitute a complete authentication or deployment security design.

## Execution and output

The gateway uses a read-only transaction, a one-second lock timeout, and a
five-second statement timeout. The Compose database initialization uses the
same `DB_NAME` for PostgreSQL and the gateway, and supplies `DB_PASSWORD` to
the role script as `QUERY_RO_PASSWORD`. The role script grants the gateway
role `CONNECT` on that database and `SELECT` on the fixture table. These
initialization grants apply only when PostgreSQL initializes a new data
volume; an existing volume is not migrated automatically.

`MIN_CELL_COUNT` defaults to 5 and values below 5 are refused. Positive counts
below the configured threshold are returned with status `suppressed` and a
`null` value. A count of zero is returned as zero. The threshold is a demo
default; the final value remains open in Decision D-013.

Audit events are written to SQLite. A failed receipt write prevents execution;
a failed final audit write prevents release of the response. The audit data
does not include raw submitted SQL or result values. Authentication failures
and request-body validation failures are not audited.

## Limits

This policy does not provide general query support, concept-level validation,
clinical semantic checks, protection against repeated-query inference,
complete resource controls, or suitability for real patient data. It is
independent of any LLM; an LLM is not implemented in this repository.
