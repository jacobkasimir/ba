from .database import open_database
from .policy import ApprovedPlan, EXECUTED_SQL


def execute_plan(plan: ApprovedPlan) -> int:
    """Execute a known gateway-owned operation.

    There is no function here that executes arbitrary submitted SQL.
    """

    if plan.operation != "patient_count":
        raise ValueError("Unknown approved operation")

    with open_database() as connection:
        with connection.transaction():
            # Defense in depth alongside the restricted database role.
            connection.execute("SET TRANSACTION READ ONLY")

            # Avoid waiting indefinitely for locks or expensive execution.
            connection.execute("SET LOCAL lock_timeout = '1s'")
            connection.execute("SET LOCAL statement_timeout = '5s'")

            row = connection.execute(EXECUTED_SQL).fetchone()

            if row is None:
                raise RuntimeError("The aggregate returned no row")

            return int(row[0])


def suppress_count(count: int, minimum_cell_count: int) -> int | None:
    """Hide small positive counts under the current demonstration policy."""

    if minimum_cell_count < 5:
        raise ValueError("Minimum cell count must be at least 5")

    if count < 0:
        raise ValueError("A count cannot be negative")

    if 0 < count < minimum_cell_count:
        return None

    return count