"""Run the versioned intent cases against the configured real LLM provider.

Run from the repository root with LLM_BASE_URL, LLM_API_KEY, and LLM_MODEL
set. The runner never submits proposed SQL to the gateway.
"""

import asyncio
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "application"))

from app.llm_client import LLMClient  # noqa: E402


DATASET_PATH = Path(__file__).with_name("assistant-intent-v1.json")
CONTEXT_PATHS = {
    "schema": ROOT / "mcp_servers/schema/context/schema.json",
    "policy": ROOT / "mcp_servers/constraints/context/constraints.json",
    "examples": ROOT / "mcp_servers/examples/context/examples.json",
}
SUPPORTED_SQL = "SELECT COUNT(*) FROM public.patient_dimension"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


async def evaluate():
    required = ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise SystemExit("Missing required environment variables: " + ", ".join(missing))

    dataset = load_json(DATASET_PATH)
    context = {
        name: load_json(path)
        for name, path in CONTEXT_PATHS.items()
    }
    client = LLMClient(
        base_url=os.environ["LLM_BASE_URL"],
        api_key=os.environ["LLM_API_KEY"],
        model=os.environ["LLM_MODEL"],
    )

    failures = 0
    try:
        for index, case in enumerate(dataset["cases"], start=1):
            result = {
                "case": index,
                "question": case["question"],
                "expected_action": case["expected_action"],
            }
            try:
                decision = await client.propose(case["question"], context)
                result["actual_action"] = decision.action
                result["action_match"] = decision.action == case["expected_action"]
                if case["expected_action"] == "propose":
                    result["sql_match"] = decision.sql == SUPPORTED_SQL
                passed = result["action_match"] and result.get("sql_match", True)
                result["result"] = "PASS" if passed else "FAIL"
                failures += not passed
            except Exception as error:
                # AssistantError carries only a safe code; don't print provider
                # payloads, credentials, or exception diagnostics.
                result["result"] = "ERROR"
                result["error_code"] = getattr(error, "code", "evaluation_request_failed")
                provider_status = getattr(error, "provider_status_code", None)
                if provider_status is not None:
                    result["provider_http_status"] = provider_status
                if os.getenv("LLM_EVAL_PROVIDER_DIAGNOSTICS") == "1":
                    for name in (
                        "provider_error_code",
                        "provider_error_param",
                        "provider_error_message",
                    ):
                        value = getattr(error, name, None)
                        if value:
                            result[name] = value
                failures += 1
            print(json.dumps(result, ensure_ascii=False))
    finally:
        await client.aclose()

    print(json.dumps({
        "dataset_id": dataset["dataset_id"],
        "dataset_version": dataset["dataset_version"],
        "model": os.environ["LLM_MODEL"],
        "case_count": len(dataset["cases"]),
        "failures": failures,
    }, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(evaluate()))
