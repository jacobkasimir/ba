import asyncio
import json
from pathlib import Path
from typing import Literal

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


# These metadata documents should remain small in the current prototype.
MAX_RESULT_BYTES = 64 * 1024


class ServerConfig(BaseModel):
    """One trusted, administrator-configured MCP connection."""

    model_config = ConfigDict(extra="forbid")

    transport: Literal["streamable_http"]
    url: HttpUrl
    tools: list[str] = Field(min_length=1)
    timeout_seconds: float = Field(default=15, gt=0, le=60)


class MCPConfig(BaseModel):
    """The complete application-side MCP configuration."""

    model_config = ConfigDict(extra="forbid")

    servers: dict[str, ServerConfig]


class UnknownTool(ValueError):
    """The caller requested a tool outside the configured allow-list."""


class MCPUnavailable(RuntimeError):
    """A configured MCP operation could not be completed."""


def extract_json_object(result) -> dict:
    """Extract a JSON object from a successful MCP tool response.

    The current context tools return their complete JSON catalog.
    """

    structured = getattr(result, "structuredContent", None)

    if structured is not None:
        # Some SDK output schemas wrap a return value in "result".
        if (
            isinstance(structured, dict)
            and set(structured) == {"result"}
            and isinstance(structured["result"], dict)
        ):
            value = structured["result"]
        else:
            value = structured

    else:
        # Our context tools should return one JSON text block when
        # structured output is not available.
        text_blocks = [
            block.text
            for block in result.content
            if getattr(block, "type", None) == "text"
        ]

        if len(text_blocks) != 1:
            raise ValueError("Expected one JSON text result")

        value = json.loads(text_blocks[0])

    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")

    encoded = json.dumps(value).encode("utf-8")

    if len(encoded) > MAX_RESULT_BYTES:
        raise ValueError("Context result exceeds the permitted size")

    return value


class MCPManager:
    """Coordinate access to the configured context servers.

    No database connections and no model calls occur here.
    """

    def __init__(self, config_path: Path):
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        self.config = MCPConfig.model_validate(raw)

        if not self.config.servers:
            raise ValueError("At least one MCP server must be configured")

        # Keep development concurrency bounded.
        self._slots = asyncio.Semaphore(3)

    def allowed_tool_names(self) -> list[str]:
        """Return the application's fixed tool allow-list."""

        return sorted(
            f"{server_name}__{tool_name}"
            for server_name, server in self.config.servers.items()
            for tool_name in server.tools
        )

    async def _exchange(
        self,
        server_name: str,
        tool_name: str | None = None,
        arguments: dict | None = None,
    ):
        """Perform a complete MCP operation in one task.

        Context managers are entered and exited in the same task.
        This matters for the MCP SDK's asynchronous lifecycle.
        """

        server = self.config.servers[server_name]

        try:
            # The timeout includes waiting for an available slot.
            async with asyncio.timeout(server.timeout_seconds):
                async with self._slots:
                    async with streamablehttp_client(
                        str(server.url)
                    ) as (
                        read_stream,
                        write_stream,
                        _,
                    ):
                        async with ClientSession(
                            read_stream,
                            write_stream,
                        ) as session:
                            await session.initialize()

                            discovered = await session.list_tools()

                            discovered_names = {
                                tool.name
                                for tool in discovered.tools
                            }

                            expected_names = set(server.tools)

                            # In this stage, each service should expose
                            # exactly the configured context tools.
                            if discovered_names != expected_names:
                                raise ValueError(
                                    "Discovered tool set differs "
                                    "from configured tool set"
                                )

                            if tool_name is None:
                                return sorted(discovered_names)

                            result = await session.call_tool(
                                tool_name,
                                arguments=arguments or {},
                            )

                            if result.isError:
                                raise ValueError(
                                    "MCP tool returned an error"
                                )

                            return extract_json_object(result)

        except Exception as error:
            # Convert transport, timeout, and response errors into one
            # controlled application exception.
            #
            # Do not forward raw server errors or internal tracebacks
            # to the browser.
            raise MCPUnavailable(
                f"MCP operation failed for {server_name}"
            ) from error

    async def inspect_server(self, server_name: str) -> dict:
        """Report discovery success without crashing other checks."""

        try:
            tools = await self._exchange(server_name)

            return {
                "server": server_name,
                "status": "available",
                "tools": [
                    f"{server_name}__{tool}"
                    for tool in tools
                ],
            }

        except MCPUnavailable:
            return {
                "server": server_name,
                "status": "unavailable",
                "tools": [],
            }

    async def inspect_all(self) -> list[dict]:
        """Check servers independently.

        One failed server does not prevent others from being inspected.
        """

        return list(
            await asyncio.gather(
                *(
                    self.inspect_server(name)
                    for name in self.config.servers
                )
            )
        )

    async def call_tool(
        self,
        qualified_name: str,
        arguments: dict,
    ) -> dict:
        """Invoke only an explicitly configured tool."""

        if qualified_name not in self.allowed_tool_names():
            raise UnknownTool("Unknown or disallowed tool")

        # Current tools are read-only metadata tools with no arguments.
        # Extend this only together with explicit input validation.
        if arguments:
            raise ValueError(
                "The current context tools accept only empty arguments"
            )

        server_name, tool_name = qualified_name.split("__", 1)

        return await self._exchange(
            server_name,
            tool_name,
            arguments,
        )