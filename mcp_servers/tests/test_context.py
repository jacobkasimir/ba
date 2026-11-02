import importlib

import pytest


# The test image packages all three implementations under distinct names.
SERVER_CASES = [
    ("schema_server.server", "get_schema"),
    ("constraints_server.server", "get_query_policy"),
    ("examples_server.server", "get_examples"),
]


def call_tool_function(
    module_name: str,
    function_name: str,
) -> dict:
    """Call a tool's Python implementation directly.

    This tests application logic, not MCP networking.
    """

    module = importlib.import_module(module_name)
    function = getattr(module, function_name)

    return function()


@pytest.mark.parametrize(
    "module_name,function_name",
    SERVER_CASES,
)
def test_context_has_identity(module_name, function_name):
    result = call_tool_function(module_name, function_name)

    assert isinstance(result["context_version"], str)
    assert result["dataset_id"] == (
        "synthetic-connectivity-fixture"
    )


@pytest.mark.parametrize(
    "module_name,function_name",
    SERVER_CASES,
)
def test_results_are_independent_copies(
    module_name,
    function_name,
):
    first = call_tool_function(module_name, function_name)
    first["context_version"] = "modified"

    second = call_tool_function(module_name, function_name)

    assert second["context_version"] != "modified"


def test_schema_matches_fixture():
    result = call_tool_function(
        "schema_server.server",
        "get_schema",
    )

    table = result["dataset"]["tables"][0]

    assert table["name"] == "patient_dimension"
    assert table["columns"][0]["name"] == "patient_num"


def test_constraints_are_informational():
    result = call_tool_function(
        "constraints_server.server",
        "get_query_policy",
    )

    assert result["authority"] == "informational_only"
    assert result["policy"]["version"] == (
        "demo-patient-count-v1"
    )


def test_examples_exclude_result_fields():
    result = call_tool_function(
        "examples_server.server",
        "get_examples",
    )

    forbidden = {
        "result",
        "expected_result",
        "expected_count",
        "patient_count",
    }

    for example in result["examples"]:
        assert example["usage"] == "development_only"
        assert forbidden.isdisjoint(example)


def test_examples_match_described_policy():
    constraints = call_tool_function(
        "constraints_server.server",
        "get_query_policy",
    )

    examples = call_tool_function(
        "examples_server.server",
        "get_examples",
    )

    allowed_sql = constraints["policy"]["supported_sql"]

    for example in examples["examples"]:
        assert example["sql"] == allowed_sql