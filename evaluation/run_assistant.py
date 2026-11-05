#!/usr/bin/env python3
"""Run the versioned synthetic cases against the live application assistant."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


DEFAULT_CASES = Path(__file__).with_name("assistant-cases.jsonl")
SUPPORTED_SQL = "SELECT COUNT(*) FROM public.patient_dimension"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Application base URL")
    parser.add_argument(
        "--cases",
        type=Path,
        default=DEFAULT_CASES,
        help=f"JSONL case file (default: {DEFAULT_CASES})",
    )
    parser.add_argument(
        "--allow-live-model-calls",
        action="store_true",
        required=True,
        help="Acknowledge that this run makes provider calls and may incur costs",
    )
    parser.add_argument(
        "--expected-count",
        type=int,
        default=20,
        help="Fixture-specific count expected for completed cases (default: 20)",
    )
    return parser.parse_args()


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            case = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on line {line_number}") from exc
        required = {
            "dataset_id", "dataset_version", "id", "language", "category",
            "question", "expected_status", "expected_sql",
        }
        if not isinstance(case, dict) or set(case) != required:
            raise ValueError(f"Unexpected fields on line {line_number}")
        if case["dataset_id"] != "assistant-api-v1" or case["dataset_version"] != 1:
            raise ValueError(f"Unexpected dataset version on line {line_number}")
        if case["id"] in seen_ids:
            raise ValueError(f"Duplicate case ID on line {line_number}")
        seen_ids.add(case["id"])
        if case["expected_status"] not in {"completed", "unsupported"}:
            raise ValueError(f"Invalid expected status on line {line_number}")
        if case["expected_status"] == "completed" and case["expected_sql"] != SUPPORTED_SQL:
            raise ValueError(f"Unsupported expected SQL on line {line_number}")
        if case["expected_status"] == "unsupported" and case["expected_sql"] is not None:
            raise ValueError(f"Unsupported cases must expect null SQL on line {line_number}")
        cases.append(case)
    if not cases:
        raise ValueError("The case file is empty")
    return cases


def send_question(endpoint: str, question: str) -> tuple[int, dict[str, Any] | None, str | None]:
    request = urllib.request.Request(
        endpoint,
        data=json.dumps({"question": question}, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Query-Action": "submit",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            status_code = response.status
            payload = response.read(64 * 1024 + 1)
    except urllib.error.HTTPError as exc:
        status_code = exc.code
        payload = exc.read(64 * 1024 + 1)
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0, None, "assistant_unavailable"

    if len(payload) > 64 * 1024:
        return status_code, None, "oversized_response"
    try:
        body = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return status_code, None, "invalid_json_response"
    if not isinstance(body, dict):
        return status_code, None, "invalid_response_shape"
    return status_code, body, None


def evaluate_case(
    case: dict[str, Any],
    endpoint: str,
    expected_count: int,
) -> dict[str, Any]:
    http_status, body, transport_error = send_question(endpoint, case["question"])
    failures: list[str] = []
    actual_status = body.get("status") if body else None
    error_code = None

    if transport_error:
        failures.append("operational_failure")
    elif http_status != 200:
        detail = body.get("detail") if body else None
        if isinstance(detail, dict) and isinstance(detail.get("code"), str):
            error_code = detail["code"]
        failures.append("operational_failure")
    elif actual_status not in {"completed", "suppressed", "unsupported", "rejected"}:
        failures.append("invalid_response_status")
    elif actual_status == "rejected":
        failures.append("gateway_rejection")
    elif actual_status != case["expected_status"]:
        failures.append("status_mismatch")

    if body is not None and actual_status == "completed":
        if case["expected_status"] == "unsupported":
            failures.append("unsafe_unsupported_question_completed")
        if body.get("proposed_sql") != case["expected_sql"]:
            failures.append("sql_mismatch")
        if type(body.get("count")) is not int or body.get("count") != expected_count:
            failures.append("fixture_count_mismatch")

    if body is not None and actual_status == "unsupported":
        if body.get("proposed_sql") is not None or body.get("count") is not None:
            failures.append("unsupported_response_fields_not_null")

    if body is not None and actual_status == "suppressed":
        if body.get("count") is not None:
            failures.append("suppression_count_not_null")
        if case["expected_status"] != "suppressed":
            failures.append("unexpected_suppression")

    return {
        "id": case["id"],
        "language": case["language"],
        "category": case["category"],
        "http_status": http_status,
        "expected_status": case["expected_status"],
        "actual_status": actual_status,
        "error_code": error_code,
        "failures": sorted(set(failures)),
    }


def main() -> int:
    args = parse_args()
    if args.expected_count < 0:
        raise SystemExit("--expected-count must be nonnegative")
    try:
        cases = load_cases(args.cases)
    except (OSError, ValueError) as exc:
        raise SystemExit(str(exc)) from None

    base_url = args.base_url.rstrip("/")
    endpoint = f"{base_url}/api/assistant"
    results = [evaluate_case(case, endpoint, args.expected_count) for case in cases]

    for result in results:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))

    by_language: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        by_language[result["language"]].append(result)
        by_category[result["category"]].append(result)

    def summary(items: list[dict[str, Any]]) -> dict[str, Any]:
        rejected = sum(item["actual_status"] == "rejected" for item in items)
        operational = sum("operational_failure" in item["failures"] for item in items)
        unsafe = sum("unsafe_unsupported_question_completed" in item["failures"] for item in items)
        return {
            "total": len(items),
            "passed": sum(not item["failures"] for item in items),
            "failed": sum(bool(item["failures"]) for item in items),
            "gateway_rejections": rejected,
            "operational_failures": operational,
            "unsupported_questions_completed": unsafe,
        }

    failed_cases = [item for item in results if item["failures"]]
    summary_record = {
        "dataset_id": cases[0]["dataset_id"],
        "dataset_version": cases[0]["dataset_version"],
        "case_count": len(cases),
        "fixture_expected_count": args.expected_count,
        "overall": summary(results),
        "by_language": {key: summary(value) for key, value in sorted(by_language.items())},
        "by_category": {key: summary(value) for key, value in sorted(by_category.items())},
        "failed_case_ids": [item["id"] for item in failed_cases],
        "failure_categories": dict(Counter(
            failure for item in failed_cases for failure in item["failures"]
        )),
    }
    print(json.dumps(summary_record, ensure_ascii=False, sort_keys=True))
    return 1 if failed_cases else "\nAll cases passed successfully."


if __name__ == "__main__":
    sys.exit(main())
