import pytest

from app.execution import suppress_count
from app.policy import PolicyViolation, approve_query


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT COUNT(*) FROM public.patient_dimension",
        "select count(*) from public.patient_dimension;",
        """
        /* A harmless comment */
        SELECT COUNT(*)
        FROM public.patient_dimension;
        """,
    ],
)
def test_approved_query_is_accepted(sql):
    plan = approve_query(sql)

    assert plan.operation == "patient_count"


@pytest.mark.parametrize(
    "sql",
    [
        # Patient-level output is not allowed.
        "SELECT patient_num FROM public.patient_dimension",

        # Wildcard output is not allowed.
        "SELECT * FROM public.patient_dimension",

        # Database modifications are not allowed.
        "DELETE FROM public.patient_dimension",

        # Other tables are not allowed.
        "SELECT COUNT(*) FROM public.unknown_table",

        # Filters are outside the first policy.
        (
            "SELECT COUNT(*) FROM public.patient_dimension "
            "WHERE patient_num = 1"
        ),

        # Joins are outside the first policy.
        (
            "SELECT COUNT(*) FROM public.patient_dimension a "
            "JOIN public.patient_dimension b "
            "ON a.patient_num = b.patient_num"
        ),

        # Arbitrary function execution is not allowed.
        "SELECT pg_sleep(10)",

        # More than one statement is not allowed.
        (
            "SELECT COUNT(*) FROM public.patient_dimension;"
            "SELECT COUNT(*) FROM public.patient_dimension;"
        ),

        # LIMIT is not part of the approved structure.
        "SELECT COUNT(*) FROM public.patient_dimension LIMIT 1",

        # Invalid SQL must be rejected.
        "THIS IS NOT SQL",
    ],
)
def test_unsupported_queries_are_rejected(sql):
    with pytest.raises(PolicyViolation):
        approve_query(sql)


@pytest.mark.parametrize(
    "actual,expected",
    [
        (0, 0),
        (1, None),
        (4, None),
        (5, 5),
        (20, 20),
    ],
)
def test_suppression_boundaries(actual, expected):
    assert suppress_count(actual, 5) == expected