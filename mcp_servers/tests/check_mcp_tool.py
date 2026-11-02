"""Check one running MCP server through the actual MCP protocol.

Usage inside the diagnostic container:

    python /tmp/check_mcp_tool.py schema /tmp/metadata.json

The MCP configuration path is supplied through MCP_CONFIG.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


CONFIG_PATH = Path(
    os.environ.get("MCP_CONFIG", "/tmp/mcp_servers.json")
)


def load_json(path: Path) -> dict:
    """Read a JSON object from a local, read-only test file."""

    value = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(value, dict):
        raise AssertionError(f"{path} must contain a JSON object")

    return value


def extract_tool_result(result) -> dict:
    """Read a JSON result returned by an MCP tool.

    Depending on the tested MCP SDK version, a tool result may appear
    as structured content or as a JSON-encoded text content block.
    """

    structured = getattr(result, "structuredContent", None)

    if structured is not None:
        # Some SDK responses wrap the Python return value in "result".
        if (
            isinstance(structured, dict)
            and set(structured) == {"result"}
            and isinstance(structured["result"], dict)
        ):
            return structured["result"]

        return structured

    for block in result.content:
        if getattr(block, "type", None) == "text":
            value = json.loads(block.text)

            if not isinstance(value, dict):
                raise AssertionError(
                    "Tool returned JSON, but not a JSON object"
                )

            return value

    raise AssertionError("Tool returned no usable JSON content")


async def check_server(server_name: str, metadata_path: Path) -> None:
    """Connect, initialize, discover, invoke, and compare."""

    configuration = load_json(CONFIG_PATH)
    server = configuration["servers"][server_name]

    if server["transport"] != "streamable_http":
        raise ValueError(
            f"{server_name} does not use Streamable HTTP"
        )

    expected_tool = server["expected_tool"]
    expected_metadata = load_json(metadata_path)

    print(f"Server: {server_name}")
    print(f"URL: {server['url']}")

    # This opens a real HTTP connection to the MCP server.
    async with streamablehttp_client(server["url"]) as (
        read_stream,
        write_stream,
        _,
    ):
        # The session implements MCP messages over that connection.
        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:
            # MCP clients must initialize before calling tools.
            await session.initialize()
            print("Initialization: OK")

            # Discover the tools exposed by this specific server.
            discovered = await session.list_tools()
            tool_names = {
                tool.name
                for tool in discovered.tools
            }

            print("Discovered tools:", sorted(tool_names))

            # In the current design, each server exposes exactly one tool.
            if tool_names != {expected_tool}:
                raise AssertionError(
                    f"Expected only {expected_tool!r}, "
                    f"received {sorted(tool_names)!r}"
                )

            # These three context tools currently take no arguments.
            response = await session.call_tool(
                expected_tool,
                arguments={},
            )

            if response.isError:
                raise AssertionError(
                    f"Tool {expected_tool!r} returned an MCP error"
                )

            actual_metadata = extract_tool_result(response)

            # The current tools return the complete JSON catalog.
            # If you intentionally transform their output, replace this
            # with checks for the fields they are meant to return.
            if actual_metadata != expected_metadata:
                raise AssertionError(
                    "Tool response differs from its metadata JSON file.\n"
                    f"Expected: {json.dumps(expected_metadata, sort_keys=True)}\n"
                    f"Actual:   {json.dumps(actual_metadata, sort_keys=True)}"
                )

            print(f"Tool call {expected_tool}: OK")
            print("Metadata comparison: OK")


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(
            "Usage: check_mcp_tool.py "
            "<schema|constraints|examples> <metadata-file>"
        )

    server_name = sys.argv[1]
    metadata_path = Path(sys.argv[2])

    # A failed connection should not leave this command hanging forever.
    asyncio.run(
        asyncio.wait_for(
            check_server(server_name, metadata_path),
            timeout=30,
        )
    )


if __name__ == "__main__":
    main()