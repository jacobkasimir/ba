# Gateway V1

Parser Version: 7.21

## Dataset

- Database: aktin
- Table: public.patient_dimension
- Column: patient_num
- Dataset contains synthetic connectivity-test rows only.

## Supported proposal

SELECT COUNT(*) FROM public.patient_dimension

## Validation

- PostgreSQL syntax parsing with pglast.
- Exactly one statement.
- Exact approved syntax-tree structure.
- Source-position metadata excluded from structural comparison.
- Unknown structures rejected.

## Execution

- Submitted SQL is not executed directly.
- Gateway-owned SQL is selected through an approved operation.
- Restricted database login.
- Read-only transaction.
- Statement and lock timeouts.

## Output policy

- Small positive counts below MIN_CELL_COUNT are suppressed.
- Zero is distinct from suppression.
- Suppressed values are represented as null.

## Audit

- Request receipt.
- Policy rejection.
- Database execution failure.
- Successful or suppressed response.
- Audit-write failure prevents result release.

## Limitations

- Only one count-query structure.
- No filters, joins, grouping, or concept hierarchy.
- No clinical semantic validation.
- No general protection against repeated-query disclosure.
- No complete resource admission control.
- Authentication uses a shared internal API key.
- SQLite audit storage is not tamper-proof.
- Authentication and body-validation failures are not in the audit table.
- Not suitable for real patient data.