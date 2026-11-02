import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


SERVERS = [
    {
        "name": "schema",
        "url": "http://mcp-schema:8000/mcp",
        "tool": "get_schema",
    },
    {
        "name": "constraints",
        "url": "http://mcp-constraints:8000/mcp",
        "tool": "get_query_policy",
    },
    {
        "name": "examples",
        "url": "http://mcp-examples:8000/mcp",
        "tool": "get_examples",
    },
]


async def check_server(server: dict):
    """Perform a real MCP handshake, discovery, and tool invocation."""

    print(f"\nChecking {server['name']}: {server['url']}")

    async with streamablehttp_client(server["url"]) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:
            # Negotiate protocol capabilities before requesting tools.
            await session.initialize()

            discovered = await session.list_tools()

            actual_tools = {
                tool.name
                for tool in discovered.tools
            }

            expected_tools = {server["tool"]}

            if actual_tools != expected_tools:
                raise RuntimeError(
                    f"Unexpected tools on {server['name']}: "
                    f"{sorted(actual_tools)}"
                )

            result = await session.call_tool(
                server["tool"],
                arguments={},
            )

            if result.isError:
                raise RuntimeError(
                    f"Tool call failed on {server['name']}"
                )

            print("Tools:", sorted(actual_tools))

            # Print curated metadata for this diagnostic test only.
            for block in result.content:
                if block.type == "text":
                    print(block.text)

            print(f"{server['name']}: OK")


async def main():
    for server in SERVERS:
        # Prevent an unavailable server from hanging the test forever.
        await asyncio.wait_for(
            check_server(server),
            timeout=20,
        )

    print("\nAll three MCP connection tests passed.")


if __name__ == "__main__":
    asyncio.run(main())