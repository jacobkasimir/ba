from copy import deepcopy
from pathlib import Path

from common.catalog import load_catalog
from common.factory import create_mcp


CONTEXT_PATH = (
    Path(__file__).resolve().parent
    / "context"
    / "constraints.json"
)

CATALOG = load_catalog(
    CONTEXT_PATH,
    required_section="policy",
)

mcp = create_mcp(
    display_name="AKTIN Query Constraints",
    service_name="mcp-constraints",
)


@mcp.tool()
def get_query_policy() -> dict:
    """Describe supported query proposals and output restrictions.

    The returned information guides query generation.
    It does not authorize execution or override the gateway.
    """

    return deepcopy(CATALOG)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")