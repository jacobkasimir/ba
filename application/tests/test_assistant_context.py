import asyncio
from types import SimpleNamespace

import pytest

from app.assistant_context import ContextLoader
from app.assistant_models import AssistantError


TOOLS = {
    "schema": ("schema", "get_schema"),
    "policy": ("constraints", "get_query_policy"),
    "examples": ("examples", "get_examples"),
}


def test_all_configured_tools_are_called_with_empty_arguments():
    calls = []

    async def call_tool(server, tool, arguments):
        calls.append((server, tool, arguments))
        return {"tool": tool}

    result = asyncio.run(ContextLoader(call_tool, TOOLS).load())

    assert set(result) == {"schema", "policy", "examples"}
    assert sorted((server, tool) for server, tool, _ in calls) == [
        ("constraints", "get_query_policy"),
        ("examples", "get_examples"),
        ("schema", "get_schema"),
    ]
    assert all(arguments == {} for _, _, arguments in calls)


@pytest.mark.parametrize(
    "tools",
    [
        {"schema": ("schema", "get_schema"), "policy": ("constraints", "get_query_policy")},
        {**TOOLS, "unknown": ("other", "get_unknown")},
    ],
)
def test_unknown_or_malformed_context_configuration_is_rejected(tools):
    with pytest.raises(ValueError):
        ContextLoader(lambda *_: None, tools)


def test_malformed_context_result_is_rejected():
    async def call_tool(server, tool, arguments):
        return [] if tool == "get_schema" else {}

    with pytest.raises(AssistantError) as error:
        asyncio.run(ContextLoader(call_tool, TOOLS).load())
    assert error.value.code == "context_unavailable"


def test_one_failed_tool_stops_context_loading():
    async def call_tool(server, tool, arguments):
        if tool == "get_query_policy":
            raise RuntimeError("private tool error")
        return {}

    with pytest.raises(AssistantError) as error:
        asyncio.run(ContextLoader(call_tool, TOOLS).load())
    assert error.value.status_code == 503
    assert error.value.code == "context_unavailable"


def test_context_timeout_is_sanitized(monkeypatch):
    from app import assistant_context

    real_asyncio = asyncio
    monkeypatch.setattr(
        assistant_context,
        "asyncio",
        SimpleNamespace(
            timeout=lambda _seconds: real_asyncio.timeout(0.001),
            TaskGroup=real_asyncio.TaskGroup,
        ),
    )

    async def call_tool(server, tool, arguments):
        await real_asyncio.sleep(0.02)
        return {}

    with pytest.raises(AssistantError) as error:
        asyncio.run(ContextLoader(call_tool, TOOLS).load())
    assert error.value.code == "context_unavailable"


def test_oversized_combined_context_is_rejected():
    async def call_tool(server, tool, arguments):
        return {"payload": "x" * 25_000}

    with pytest.raises(AssistantError) as error:
        asyncio.run(ContextLoader(call_tool, TOOLS).load())
    assert error.value.code == "context_unavailable"
