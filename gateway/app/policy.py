import json
from dataclasses import dataclass

from pglast.parser import ParseError, parse_sql_json


POLICY_VERSION = "demo-patient-count-v1"

# This is the submitted query structure that we currently support.
SUPPORTED_PROPOSAL = (
    "SELECT COUNT(*) FROM public.patient_dimension"
)

# This SQL is owned by the gateway.
# The client does not control the string passed to PostgreSQL.
EXECUTED_SQL = (
    "SELECT COUNT(*) AS patient_count "
    "FROM public.patient_dimension"
)


class PolicyViolation(ValueError):
    """A safe-to-report rejection with a stable machine-readable code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ApprovedPlan:
    """A server-approved operation, not an arbitrary SQL string."""

    operation: str


def _without_source_positions(value):
    """Remove parser metadata that depends only on source formatting.

    Whitespace and comments change character positions in the input.
    They must not change our decision about an otherwise identical query.

    All other syntax-tree fields remain part of the comparison.
    """

    if isinstance(value, dict):
        return {
            key: _without_source_positions(item)
            for key, item in value.items()
            if key not in {
                "location",
                "stmt_location",
                "stmt_len",
            }
        }

    if isinstance(value, list):
        return [_without_source_positions(item) for item in value]

    return value


def _parse_statement(sql: str):
    """Parse exactly one PostgreSQL SELECT statement."""

    try:
        document = json.loads(parse_sql_json(sql))
    except ParseError:
        raise PolicyViolation(
            "invalid_sql",
            "The SQL could not be parsed.",
        ) from None

    statements = document.get("stmts", [])

    if len(statements) != 1:
        raise PolicyViolation(
            "statement_count",
            "Exactly one SQL statement is permitted.",
        )

    statement = statements[0]["stmt"]

    # This rejects INSERT, UPDATE, DELETE, CREATE, COPY, etc.
    # SELECT-specific restrictions are applied by exact structure matching.
    if set(statement) != {"SelectStmt"}:
        raise PolicyViolation(
            "statement_type",
            "Only the approved SELECT pattern is permitted.",
        )

    return _without_source_positions(statement)


# Parse the reference using the same parser as incoming proposals.
# This avoids maintaining a hand-written PostgreSQL AST representation.
APPROVED_STRUCTURE = _parse_statement(SUPPORTED_PROPOSAL)


def approve_query(sql: str) -> ApprovedPlan:
    """Accept only the exact approved syntax-tree structure.

    This deliberately rejects aliases, filters, grouping, joins,
    subqueries, LIMIT, and any other structure not yet supported.
    """

    proposed_structure = _parse_statement(sql)

    if proposed_structure != APPROVED_STRUCTURE:
        raise PolicyViolation(
            "unsupported_query",
            "This prototype currently supports only "
            "SELECT COUNT(*) FROM public.patient_dimension.",
        )

    return ApprovedPlan(operation="patient_count")