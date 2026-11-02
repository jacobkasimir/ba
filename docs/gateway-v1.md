# Query Gateway: Current Demonstration

This page describes the gateway code in this repository. It is a narrow
demonstration, not a general-purpose SQL gateway.

## Runtime and dataset

- Python image: `python:3.12-slim`.
- FastAPI application, started with Uvicorn.
- `pglast` is declared as `>=6,<8`; its exact installed version is not pinned
  here. The previously listed parser version `7.21` is not established by the
  dependency files.
- The gateway defaults to database `aktin` and uses
  `public.patient_dimension(patient_num BIGINT PRIMARY KEY)`.
- The schema initializer inserts 20 synthetic rows. This is a connectivity
  fixture, not the planned synthetic AKTIN/i2b2 evaluation dataset.
- The database login defaults to role `user`. The bundled local database
  initialization currently has mismatched database and password variable
  names; see [Operations](operations.md#compose-database-initialization).

## Validation and execution

- PostgreSQL syntax parsing with `pglast`.
- Exactly one statement is required.
- The parsed syntax tree must match the approved count-query structure;
  source-position metadata is excluded from the comparison.
- The only supported proposal is
  `SELECT COUNT(*) FROM public.patient_dimension`.
- Other SQL structures, including filters, joins, grouping, aliases,
  subqueries, and multiple statements, are rejected.
- The submitted SQL is not executed directly. The gateway chooses and executes
  its own SQL for the approved operation.
- Execution uses a read-only transaction and sets one-second lock and
  five-second statement timeouts. A restricted database role is also
  configured by the initialization script, if initialization succeeds.

This is not general SQL or clinical semantic validation. The implementation
currently supports only one aggregate operation.

## Output policy

- `MIN_CELL_COUNT` defaults to 5 and the gateway refuses values below 5.
- Positive counts below the configured threshold are suppressed.
- Zero is returned as zero; suppression is represented as `null` with status
  `suppressed`.
- The threshold is a demonstration default, not a confirmed evaluation policy.

## Audit

- Events are stored in SQLite at `/app/audit/events.sqlite` by default, on the
  Compose `gateway_audit` volume.
- Events cover receipt, policy rejection, database execution failure, and
  successful or suppressed completion. Submitted SQL is represented by a
  SHA-256 hash; the gateway-owned executed SQL is recorded after execution.
- An audit-write failure blocks execution if receipt logging fails and blocks
  result release if final logging fails.
- Authentication and request-body validation failures are not written to the
  audit database.
- This differs from accepted Decision D-009, which specifies JSONL application
  logging and a read-only UI API. Neither that application log nor the UI is
  implemented in this repository.

## Limitations

- Only one count-query structure is supported.
- No filters, joins, grouping, concepts, or clinical semantic validation.
- No general protection against repeated-query disclosure.
- No complete resource admission control.
- Authentication uses a shared API key; this is not a complete security
  control set.
- SQLite audit storage is not tamper-proof.
- The API is published on `127.0.0.1:8001` by Compose for development.
- Not suitable for real patient data.
