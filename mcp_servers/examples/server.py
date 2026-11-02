from copy import deepcopy
from pathlib import Path

from common.catalog import load_catalog
from common.factory import create_mcp


CONTEXT_PATH = (
    Path(__file__).resolve().parent
    / "context"
    / "examples.json"
)

CATALOG = load_catalog(
    CONTEXT_PATH,
    required_section="examples",
)

mcp = create_mcp(
    display_name="AKTIN Development Examples",
    service_name="mcp-examples",
)


@mcp.tool()
def get_examples() -> dict:
    """Return curated development questions and SQL examples.

    Execution results and frozen evaluation questions are excluded.
    """

    return deepcopy(CATALOG)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")