# Evaluation Status

## Development model-intent check

The repository has a small versioned development set at
`evaluation/development/assistant-intent-v1.json` and a real-provider runner
at `evaluation/development/run_assistant_intent_eval.py`. Four synthetic
English/German cases check supported total-count requests and out-of-scope or
adversarial requests. The runner checks the expected `propose` or
`unsupported` action and exact SQL for supported cases.

The runner reads the checked-in schema, constraints, and examples JSON as
context. It calls the configured model directly and does not call MCP
services, the application assistant API, the gateway, or PostgreSQL. It can
incur provider charges. It is not part of any Dockerfile's `test` target.
Instructions are in [Operations](operations.md#test-protocol-and-provider-commands).

The four cases are a development check, not a frozen final evaluation set or
evidence of broad model quality, clinical validity, or usability. They use the
current 20-row connectivity fixture metadata, not the planned synthetic
AKTIN/i2b2 dataset or concept hierarchy.

## Application API evaluation

`evaluation/assistant-cases.jsonl` is a 24-case synthetic set, versioned as
`assistant-api-v1`. It includes English and German supported-count paraphrases,
unsupported filters and tables, ambiguous questions, patient-level requests,
and prompt-injection attempts. Expected cases reflect the current gateway's
single permitted query. The fixture count is a separate runner check.

Run `evaluation/run_assistant.py` against the application to exercise context
retrieval, the configured model, gateway policy, and the result schema. The
runner requires `--allow-live-model-calls`, is not part of unit tests or CI, and
can incur provider costs. It prints per-case status/failure categories and
summaries by language and category without saving detailed response bodies.
See the [dated v1 report](../evaluation/reports/2026-11-05-assistant-api-v1.md)
for the initial result, reviewed prompt adjustment, and rerun. That report
preserves the first failure rather than replacing it with the rerun result.

This API evaluation is distinct from the four-case direct-provider intent
runner: the API runner reaches the configured MCP context and gateway, while
the direct-provider runner does not. Neither establishes broad semantic
correctness. Gateway approval alone does not prove that SQL answers the
natural-language question.

## Outstanding evaluation decisions

Decision D-012 accepts the System Usability Scale, but participant procedures,
tasks, sample size, and collected results are not evidenced by implementation
artifacts. Decision D-013 leaves the final suppression threshold open; the
gateway currently uses demo default 5. Decision D-014 leaves the data source
and concept hierarchy unresolved. Decision D-015 leaves the provider/model
governance choice open even though the application has an optional configurable
provider integration. A configured model in a local environment is not a
project-level model approval.

Before reporting a formal evaluation, document the approved synthetic data and
generation method, evaluation questions and scoring/reference method, exact
provider deployment and settings, suppression policy, and actual evaluation
procedure. Do not include real patient data, credentials, or raw operational
logs in evaluation artifacts.

## Test evidence boundaries

Application assistant tests use fake orchestration services. `test_llm_client`
uses `httpx.MockTransport`; it checks request/response handling, not model
quality. Application-to-gateway tests use an HTTP mock. Gateway tests replace
database execution. MCP unit tests call tool functions directly; the separate
MCP smoke script exercises protocol communication with running containers.
There is no automated full end-to-end test that joins a live provider, all MCP
services, the gateway, and PostgreSQL.
