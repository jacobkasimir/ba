import asyncio
import json
from collections.abc import Awaitable, Callable

from .assistant_models import AssistantError


MCPCall = Callable[[str, str, dict], Awaitable[dict]]


class ContextLoader:
    def __init__(
        self,
        call_tool: MCPCall,
        tools: dict[str, tuple[str, str]],
    ) -> None:
        if set(tools) != {"schema", "policy", "examples"}:
            raise ValueError(
                "Context configuration requires schema, policy, examples"
            )

        self._call_tool = call_tool
        self._tools = tools

    async def load(self) -> dict:
        try:
            async with asyncio.timeout(8):
                tasks = {}

                async with asyncio.TaskGroup() as group:
                    for role, (server, tool) in self._tools.items():
                        tasks[role] = group.create_task(
                            self._call_tool(server, tool, {})
                        )

                context = {
                    role: task.result()
                    for role, task in tasks.items()
                }

            if not all(
                isinstance(value, dict)
                for value in context.values()
            ):
                raise ValueError("Context tools must return JSON objects")

            encoded = json.dumps(
                context,
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")

            if len(encoded) > 64 * 1024:
                raise ValueError("Combined context exceeds size limit")

            return context

        except Exception:
            raise AssistantError(
                503,
                "context_unavailable",
            ) from None