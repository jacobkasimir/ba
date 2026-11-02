from copy import deepcopy
from pathlib import Path

from common.catalog import load_catalog
from common.factory import create_mcp


# Locate metadata relative to this file, not the working directory.
CONTEXT_PATH = (
    Path(__file__).resolve().parent
    / "context"
    / "schema.json"
)

CATALOG = load_catalog(
    CONTEXT_PATH,
    required_section="dataset",
)

mcp = create_mcp(
    display_name="AKTIN Schema Context",
    service_name="mcp-schema",
)


@mcp.tool()
def get_schema() -> dict:
    """Return curated table and column metadata.

    No PostgreSQL connection is made.
    No database rows or patient identifiers are returned.
    """

    # Prevent callers from mutating the shared in-memory catalog.
    return deepcopy(CATALOG)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")