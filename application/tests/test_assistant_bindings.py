import asyncio
from unittest.mock import AsyncMock

from app.assistant_bindings import call_context_tool


def test_context_tool_adapter_uses_qualified_tool_name():
    manager = type("Manager", (), {})()
    manager.call_tool = AsyncMock(return_value={"schema": "synthetic"})

    result = asyncio.run(
        call_context_tool(manager, "schema", "get_schema", {})
    )

    assert result == {"schema": "synthetic"}
    manager.call_tool.assert_awaited_once_with("schema__get_schema", {})
