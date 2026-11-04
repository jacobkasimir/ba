from .assistant_models import QueryOutcome


# Replace these example server IDs with the exact IDs from
# config/mcp_servers.json.
#
# The tool names are taken from the repository brief.
CONTEXT_TOOLS = {
    "schema": ("schema", "get_schema"),
    "policy": ("constraints", "get_query_policy"),
    "examples": ("examples", "get_examples"),
}


async def call_context_tool(
    manager,
    server: str,
    tool: str,
    arguments: dict,
) -> dict:
    """
    Repository-specific adapter.

    Replace the call below with the exact MCPManager invocation already
    used by the existing /api/chat debug-tool implementation.

    Return the extracted JSON object, not an MCP protocol wrapper.
    """

    return await manager.call_tool(
        f"{server}__{tool}",
        arguments,
    )


def normalize_gateway_result(payload: dict) -> QueryOutcome:
    """Normalize the gateway's QueryResponse without weakening suppression."""

    if not isinstance(payload, dict):
        raise ValueError("Gateway response must be an object")

    if payload.get("columns") != ["patient_count"]:
        raise ValueError("Unexpected gateway result columns")

    rows = payload.get("rows")
    if not isinstance(rows, list) or len(rows) != 1:
        raise ValueError("Unexpected gateway result rows")

    row = rows[0]
    if not isinstance(row, dict) or "patient_count" not in row:
        raise ValueError("Unexpected gateway count row")

    count = row["patient_count"]

    if payload.get("status") == "ok":
        if type(count) is not int or count < 0:
            raise ValueError("Gateway returned an invalid count")
        return QueryOutcome(
            status="completed",
            count=count,
        )

    if payload.get("status") == "suppressed":
        if count is not None:
            raise ValueError("Suppressed gateway count must be null")
        return QueryOutcome(
            status="suppressed",
            count=None,
        )

    raise ValueError("Unexpected gateway outcome")
