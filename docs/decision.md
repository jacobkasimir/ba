# Decision Log

Project: Prototype LLM-Based Query Support for the AKTIN Data Warehouse Using the Model Context Protocol
Author: J. Tietz

**How to use this file:** one entry per decision, newest at the bottom. Never delete an entry; if a decision changes, add a new entry and set the old one to `Superseded by D-xxx`. Status is `Accepted`, `Open` (not decided yet) or `Superseded`.

| ID | Date | Decision | Status |
|---|---|---|---|
| D-001 | 2026-10-08 | Python 3.12 for the prototype | Open |
| D-002 | 2026-10-08 | Virtual environment in `prototype/.venv`, versions saved with `pip freeze` | Open |
| D-003 | 2026-10-08 | Python backend with FastAPI | Accepted |
| D-004 | 2026-10-08 | Frontend in plain HTML/CSS/JavaScript without build step | Accepted |
| D-005 | 2026-10-08 | MCP Python SDK pinned to `mcp<2` | Accepted |
| D-006 | 2026-10-08 | MCP server configuration in `config/mcp_servers.json`; local stdio and remote HTTP transports | Accepted; local stdio superseded by D-019 |
| D-007 | 2026-10-08 | Build order: UI, backend, logging, MCP, only then the LLM; echo mode with `/tool` command | Accepted |
| D-008 | 2026-10-08 | Text completion from a fixed phrase list, not from an LLM | Accepted |
| D-009 | 2026-10-08 | Logs as JSON lines file, shown in the UI via a read-only API | Accepted |
| D-010 | 2026-10-08 | Safety and validation layer is deterministic and independent of the LLM | Accepted |
| D-011 | 2026-10-08 | Single private GitHub repository with fixed folder structure and `.gitignore` rules | Accepted |
| D-012 | 2026-10-08 | Usability measured with the System Usability Scale (SUS) | Accepted |
| D-013 | 2026-10-08 | Value of the minimum cell count k | Open |
| D-014 | 2026-10-08 | Source of the synthetic test data and the AKTIN concept hierarchy | Open |
| D-015 | 2026-10-08 | LLM provider and model, local versus external | Open |
| D-016 | 2026-10-13 | Unrecognized mock-mode input asks for clarification instead of defaulting to a case count | Accepted |
| D-017 | 2026-10-13 | Multiple MCP Servers instead of one | Accepted |
| D-018 | 2026-11-02 | Three local MCP servers: schema/concepts, constraints, and examples; each serves curated context only | Accepted |
| D-019 | 2026-11-02 | Use Streamable HTTP between locally Dockerized MCP servers and the application; this supersedes the local-stdio transport choice in D-006 for these services | Accepted |
| D-020 | 2026-11-01 | MCP context is informational; the deterministic query gateway remains the sole authority for SQL validation, execution, suppression, and audit | Accepted |
| D-021 | 2026-11-02 | MCP context is versioned, reviewed JSON metadata; MCP servers have no database credentials and do not execute SQL | Accepted |
| D-022 | 2026-11-02 | Test each MCP server independently, then test MCP discovery and invocation across containers; one server being unavailable must not prevent the others from being used | Accepted |

---

## D-001 Python 3.12 for the prototype
**Date:** 2026-10-08 **Status:** Open

**Context:** The system Python on the development machine (macOS) is 3.9.6. Recent versions of the MCP Python SDK need a newer Python.

**Decision:** Use Python 3.12, installed with Homebrew next to the system version. The project is always created with `python3.12 -m venv`.

**Alternatives considered:**
- *Keep Python 3.9.6:* too old for the SDK and its dependencies.
- *Python 3.13:* also available on the machine, but newer interpreters sometimes lack compatible wheels for dependencies.
- *Replace or remove the system Python:* rejected, macOS tooling may depend on it.

**Reason:** 3.12 is recent enough for the SDK, mature, and widely supported by libraries. Installing alongside the system Python cannot break anything.

**Consequences:** `python3` still points to 3.9.6 outside the virtual environment, so commands must use `python3.12` or the activated venv. The Python version is documented as part of the reproducibility information.

**Implementation status:** The gateway and MCP Dockerfiles use Python 3.12 images. The planned local development environment and the machine-specific interpreter details in this decision are not established by the repository.

## D-002 Virtual environment and dependency file
**Date:** 2026-10-08 **Status:** Open

**Context:** Reproducibility of the evaluation is a stated goal of the thesis.

**Decision:** One virtual environment in `prototype/.venv` (ignored by Git). `requirements.txt` is created with `pip freeze` and committed.

**Alternatives considered:**
- *Hand-written `requirements.txt` with direct dependencies only:* readable, but versions of transitive packages can drift.
- *Poetry or `uv` lockfiles:* more features, but one more tool to learn.
- *Docker for the application itself:* planned for the database only, to keep the application easy to debug.

**Reason:** `pip freeze` pins the exact versions used for the evaluation with no extra tooling.

**Consequences:** The file is long and contains transitive dependencies. It must be regenerated whenever a package changes.

**Implementation status:** The current services run as Docker Compose containers and use service-specific range-based requirements files. There is no tracked `prototype/.venv` or project-wide frozen `requirements.txt`; this open decision has not been implemented as written. `gateway/requirements.txt` and `mcp_servers/requirements.txt` are not exact locks.

## D-003 Python backend with FastAPI
**Date:** 2026-10-08 **Status:** Accepted

**Context:** The backend connects to MCP servers, runs the validation layer and serves the chat interface.

**Decision:** FastAPI with uvicorn.

**Alternatives considered:**
- *Streamlit or Gradio:* fastest to start, but limited control over layout, text completion and the log menu.
- *NiceGUI:* Python-only UI with more control, but a less common stack and less control over plain web behaviour.
- *Flask:* fine, but FastAPI has built-in async support, which fits the async MCP client.
- *Node.js backend:* the MCP SDK exists, but the validation layer and evaluation scripts are better placed in Python (SQL parsing, data analysis).

**Reason:** One language for backend, MCP client, validation layer and evaluation scripts; async support; automatic request validation.

**Consequences:** The frontend is a separate static application (see D-004).

**Implementation status:** `gateway/app/main.py` is a FastAPI query gateway, but no chat backend or application-side MCP client is present. The accepted chat-backend decision remains unimplemented.

## D-004 Frontend in plain HTML, CSS and JavaScript
**Date:** 2026-10-08 **Status:** Accepted

**Context:** Requirements: text-only chat, centered welcome header, anthracite/light/system theme, text completion, log menu.

**Decision:** Static files served by FastAPI, no framework and no build step.

**Alternatives considered:**
- *React or another framework:* professional ecosystem, but adds Node tooling and build complexity that does not serve the research question.
- *Streamlit or Gradio:* see D-003.

**Reason:** All requirements are small enough for plain JavaScript, and fewer moving parts make the prototype easier to explain and maintain.

**Consequences:** UI code must be kept tidy by hand. Model output is inserted with `textContent` and never as HTML, which prevents script injection through responses.

**Implementation status:** No frontend directory or static UI files are present. This accepted frontend design remains pending.

## D-005 MCP Python SDK pinned to `mcp<2`
**Date:** 2026-10-08 **Status:** Accepted

**Context:** `pip install mcp` installed version 2.x. The prototype code was written against 1.x. Errors seen: `streamablehttp_client` was renamed, and `FastMCP` was renamed to `MCPServer`.

**Decision:** Pin the SDK to `mcp<2` and record the exact installed version in `requirements.txt`.

**Alternatives considered:**
- *Migrate to 2.x now:* possible with the official migration guide, but costs time for no research benefit.
- *Support both versions:* only done for the HTTP client import, where a fallback is cheap.

**Reason:** The thesis studies the architecture, not the SDK. A stable, known API reduces risk during implementation and evaluation.

**Consequences:** The prototype is tied to an older SDK line. A migration to 2.x is documented as future work. The version must be named in the thesis.

**Implementation status:** `mcp_servers/requirements.txt` constrains the SDK to `mcp>=1.20,<2`, not to one exact version. `docs/mcp-runtime-requirements.txt` records `mcp==1.30.0`, but the MCP Dockerfile installs the range-based requirements file rather than that snapshot. The major-version constraint is in effect; exact runtime locking is not.

## D-006 MCP server configuration and transports
**Date:** 2026-10-08 **Status:** Accepted; local stdio superseded by D-019

**Context:** The chat should connect to one or several MCP servers, local or remote, now or later.

**Decision:** A JSON file (`config/mcp_servers.json`) lists the servers. Local servers use stdio, remote servers use HTTP. Tools are addressed as `<server>__<tool>`. A server that fails to connect is logged and does not stop the application.

**Alternatives considered:**
- *Hard-coded connection:* simpler, but each new server means a code change.
- *One MCP server per database versus one server with several connections:* both are possible. Separate servers isolate credentials and keep each safety configuration simple, so they are the default.

**Reason:** Adding a database becomes a configuration change, and a single failing server does not take down the system.

**Consequences:** Each server needs its own read-only role, allow-lists and minimum cell count. The HTTP branch is untested until a real remote server is connected.

**Implementation status:** `config/mcp_servers.json` lists three Streamable HTTP endpoints. There is no application-side configuration loader or MCP client. `mcp_servers/tests/check_mcp_tool.py` loads configuration for diagnostics, and `mcp_servers/smoke_test.py` contains hard-coded connection details; neither is an application loader. The context servers have no database roles and do not execute SQL.

## D-007 Build order and echo mode
**Date:** 2026-10-08 **Status:** Accepted

**Context:** The LLM is non-deterministic and the provider is not decided yet (D-015).

**Decision:** Build and test the UI, backend, logging and MCP connection first. Until an LLM is connected, the system runs in echo mode. The command `/tool <server>__<tool> {json}` calls an MCP tool directly.

**Alternatives considered:**
- *Connect the LLM first:* faster demo, but failures cannot be separated into UI, MCP and model problems.

**Reason:** Each layer can be tested on its own, which also supports the error analysis.

**Consequences:** The `/tool` command bypasses the LLM and must be removed or restricted before the usability study.

**Implementation status:** No chat application, echo mode, or `/tool` command is present. This remains an accepted build plan, not a description of current behavior.

## D-008 Text completion from a fixed phrase list
**Date:** 2026-10-08 **Status:** Accepted

**Context:** The input field should complete text while typing.

**Decision:** Suggestions come from `frontend/suggestions.json` (prefix match, Tab to accept, Esc to dismiss).

**Alternatives considered:**
- *LLM-based completion:* more flexible, but sends half-typed input to a model on each keystroke, adds latency and cost, and raises data protection questions.
- *No completion:* does not meet the requirement.

**Reason:** Instant, offline and no data leaves the browser.

**Consequences:** The phrase list must be maintained. It could be derived from the evaluation scenarios, and this must be disclosed to avoid biasing the evaluation.

**Implementation status:** The frontend and `frontend/suggestions.json` are absent; the accepted completion feature is not implemented.

## D-009 Logging as JSON lines
**Date:** 2026-10-08 **Status:** Accepted

**Context:** Every proposed and executed query must be traceable, and logs should be viewable in the UI.

**Decision:** One JSON object per line in `prototype/logs/app.log.jsonl`. Events include `user_message`, `assistant_message`, `tool_call`, `tool_result` and `error`. The API reads only this one file. The folder is ignored by Git.

**Alternatives considered:**
- *SQLite or a log database:* better querying, but more setup.
- *Plain text logs:* hard to filter.
- *Printing to the console only:* not persistent.

**Reason:** Simple, human-readable, easy to analyse with scripts, and suitable for the audit requirement.

**Consequences:** The whole file is read on each request, which is fine at thesis scale. Logs may contain user questions and results, so they must never be committed.

**Implementation status:** The application JSONL log and read-only UI API are absent. The gateway separately stores enforcement audit events in SQLite (see D-020); those records are not the conversation log described here.

## D-010 Deterministic safety layer, independent of the LLM
**Date:** 2026-10-08 **Status:** Accepted

**Context:** The LLM can hallucinate and can be manipulated by prompts. Safety must not depend on model behaviour.

**Decision:** A separate layer between the MCP server and the database checks queries before execution (SQL parsing, SELECT only, allow-lists of tables and concepts, no identifier columns) and results after execution (minimum cell counts, no patient-level output, audit log). A read-only database role is a further barrier. The LLM never holds database credentials.

**Alternatives considered:**
- *Safety rules only in the system prompt:* easy to bypass and not verifiable.
- *A second LLM as a guard:* adds non-determinism to the safety path.
- *Relying on database permissions alone:* does not enforce the aggregation and identifier rules.

**Reason:** Defense in depth with checks that can be unit-tested without a model.

**Consequences:** The layer is a main contribution and must be tested with adversarial inputs. Over-blocking may reduce usability, and this trade-off is evaluated.

## D-011 Repository structure and `.gitignore`
**Date:** 2026-10-08 **Status:** Accepted

**Context:** Code, prompts, evaluation data and thesis text should be versioned together.

**Decision:** One private GitHub repository (`bachelorthesis`) with the folders `expose/`, `thesis/`, `prototype/`, `evaluation/`, `prompts/` and `docs/`. The `.gitignore` in the repository root excludes LaTeX build files, `.env`, logs, data dumps, virtual environments and editor files.

**Alternatives considered:**
- *Separate repositories for thesis and prototype:* cleaner for reuse, but harder to keep in sync.
- *GitLab of the institute:* to be clarified with the supervisors.

**Reason:** One history ties each evaluation run to an exact code state. Private visibility and ignore rules keep secrets and sensitive data out.

**Consequences:** No real patient data, credentials or raw logs may be committed. Evaluation states are tagged.

**Implementation status:** The current root contains `artifacts/`, `config/`, `database/`, `docs/`, `evaluation/`, `gateway/`, and `mcp_servers/`. `evaluation/` contains empty `development/` and `frozen_test/` directories. The planned `expose/`, `thesis/`, `prototype/`, and `prompts/` directories are absent, as is a root `.gitignore` (there is an `artifacts/.gitignore`). This entry records the original structure plan rather than the current layout.

## D-012 Usability measured with SUS
**Date:** 2026-10-08 **Status:** Accepted

**Context:** Usability must be rated by technically and domain-oriented users.

**Decision:** Use the System Usability Scale after defined tasks, scored 0 to 100.

**Alternatives considered:**
- *UEQ or other questionnaires:* richer dimensions, but longer.
- *Think-aloud sessions only:* qualitative depth, harder to compare.
- *Custom questionnaire:* no validation or benchmarks.

**Reason:** SUS is short, widely used and has published benchmarks, which suits a small study.

**Consequences:** Small samples limit generalisation. Participant number and tasks are to be agreed with the supervisors.

## D-013 Value of the minimum cell count k
**Date:** 2026-10-08 **Status:** Open

**Context:** Aggregated results with very small groups can identify individuals.

**Options:** a small value such as 3, 5 or 10; the right choice depends on AKTIN governance and on the data.

**To decide:** agree the value with the supervisors and AKTIN, then record it here with the reason. Until then, the value is read from configuration (`MIN_CELL_COUNT`) and not hard-coded.

**Implementation status:** The gateway currently defaults `MIN_CELL_COUNT` to 5 and refuses configured values below 5. This demonstration setting does not settle the governance decision for the evaluation.

## D-014 Synthetic test data and concept hierarchy
**Date:** 2026-10-08 **Status:** Open

**Context:** The prototype needs an i2b2 PostgreSQL database with the AKTIN concept hierarchy but no real patient data.

**Options:** a test environment or dump provided by AKTIN; synthetic data generated for the thesis; the i2b2 demo data (weaker match with AKTIN concepts).

**To decide:** ask the supervisors what exists. The source and generation method must be documented, because it limits the generalisability of the results.

**Implementation status:** `database/init/01-schema.sql` creates only `public.patient_dimension(patient_num)` with 20 synthetic rows, and the schema MCP metadata identifies it as `synthetic-connectivity-fixture`. It is a connectivity fixture, not the planned synthetic AKTIN/i2b2 dataset or concept hierarchy. The `evaluation/development/` and `evaluation/frozen_test/` directories are empty; this source decision remains open.

## D-015 LLM provider and model
**Date:** 2026-10-08 **Status:** Open

**Context:** Choice affects cost, quality, reproducibility and the data protection analysis (which data reach the LLM).

**Options:** an external API model; a locally hosted open-weight model; a comparison of both.

**To decide:** clarify with the supervisors which deployments are allowed. Record the model name, version and parameters for every evaluation run, and repeat requests because outputs are non-deterministic.

## D-016 Unrecognized mock-mode input
**Date:** 2026-10-13 **Status:** Accepted

**Context:** The deterministic mock planner originally mapped every input that did not match a specialized keyword to `case_count`. A greeting or typo such as “Hwllo” therefore returned a plausible-looking count unrelated to the user's intent.

**Decision:** The planner returns `clarify` unless the input matches a supported aggregate category or explicit case-count wording. The chat then lists supported analysis types and asks the user to rephrase. It does not issue SQL for the `clarify` intent.

**Reason:** A clear clarification is safer and less confusing than silently guessing. This is deterministic keyword routing, not fuzzy spelling correction or an LLM response.

**Consequences:** Mock mode supports a bounded phrase set documented in `docs/mock-mode.md`. Wording outside that set may require rephrasing even when its meaning is reasonable. Evaluation scenario E08 checks that unknown input does not fall through to a count.

**Implementation status:** No mock planner or chat application is present, so this accepted behavior is not currently implemented in the repository.

## D-017 Multi-MCP Server Architecture
**Date:** 2026-10-13 **Status:** Accepted 

**Context:** I can use one MCP server that handles everything, from translation to validation and finally querying. Or I use the approach from Yang et. al. that integrated a multi MCP-server approach for that problem. Each server to handles a different task.

**Decision:** Usage of multiple Servers, because the advantages of such a model overcome the one-model approaches. 

**Reason:** The study showed that an iterative approach, with multiple servers for different tasks improves efficiency over all known benchmarks in Text2SQL generation. Regardless of the model that is used a LLM. Before handling the validation of the SQL query, the first steps entirely concentrate on semantical correctness.

## D-018 Three local MCP servers for separate context responsibilities
**Date:** 2026-11-02 **Status:** Accepted

**Context:** The prototype uses multiple MCP servers rather than one combined server (D-017). The current development database is a small synthetic connectivity fixture; the synthetic AKTIN/i2b2 dataset and concept hierarchy are not yet available (D-014).

**Decision:** Implement three separately running local MCP servers:
1. **Schema and concepts server:** serves curated table, column, relationship, and, when available, concept-hierarchy metadata.
2. **Constraints server:** describes supported query patterns and interpretation/output restrictions.
3. **Examples server:** serves curated development examples, not frozen evaluation questions or expected results.

Initially, the schema server describes only the current test database. Concept-hierarchy content will be added only when an approved hierarchy and its mappings are available.

**Alternatives considered:**
- *One MCP server with three tools:* fewer processes, but combines responsibilities that should be independently maintained and tested.
- *A separate MCP server for every small context file or feature:* more services without a clear benefit at the current prototype scale.

**Reason:** Separate responsibilities make context sources easier to test, document, and update. The chosen three-server design is a bounded implementation of D-017, not a claim that adding servers by itself improves security or accuracy.

**Consequences:** The application must connect to multiple MCP endpoints and combine their responses. Each server adds configuration and test work. Context versions and tool names must be documented. The servers do not connect to PostgreSQL or execute SQL.


## D-019 Streamable HTTP for local Dockerized MCP servers
**Date:** 2026-11-02 **Status:** Accepted

**Context:** D-006 specifies stdio for local servers and HTTP for remote servers. In this implementation, the local MCP servers run as separate Docker Compose services. The application needs to communicate with each service over the Docker network.

**Decision:** Use MCP Streamable HTTP for these three Dockerized services, using their internal Compose DNS names and the `/mcp` endpoint:
- `http://mcp-schema:8000/mcp`
- `http://mcp-constraints:8000/mcp`
- `http://mcp-examples:8000/mcp`

Do not publish MCP service ports on the host unless a documented local debugging need requires it.

**Supersedes:** This entry supersedes only the local-stdio transport choice in D-006 for the three Dockerized context services. D-006's JSON server configuration, server/tool addressing, and intent to handle a failed server without stopping the application remain applicable.

**Alternatives considered:**
- *Run local MCP servers as subprocesses over stdio:* consistent with D-006, but does not match the selected separate-container deployment without additional process-management work.
- *Publish each service on a host port:* convenient for direct host access, but unnecessarily exposes endpoints for the current internal application.
- *Combine the servers into one process:* fewer connections, but does not implement the selected separately running server architecture.

**Reason:** Streamable HTTP provides explicit service endpoints and works with container-to-container communication. The services remain local; using HTTP does not mean they are remotely hosted.

**Consequences:** The application needs a separate MCP client connection for each server. Container DNS, service readiness, allowed-host configuration, and transport errors must be tested. Host validation is not authentication, and Docker network membership is not a complete security boundary. These endpoints must not be exposed to an untrusted network without additional controls.

**Implementation status:** The three services and Streamable HTTP endpoints are configured in Compose, but no application client connects to them. The diagnostic smoke test does connect and invokes tools sequentially; it is not integrated with an application or test runner.


## D-020 The query gateway remains the enforcement authority
**Date:** 2026-11-01 **Status:** Accepted

**Context:** The schema, constraints, and examples servers provide information to the application and future LLM. Context can be incomplete, stale, or influenced by untrusted input. The exposé requires safety checks to be independent of the LLM (D-010).

**Decision:** MCP context is informational only. The deterministic query gateway is the sole authority for:
- validating proposed SQL;
- enforcing database/table/column and operation allow-lists;
- controlling read-only execution;
- validating result shape and aggregation level;
- applying suppression rules; and
- recording execution and policy decisions.

The LLM and MCP servers do not receive database credentials. No MCP context server exposes a SQL-execution tool.

**Alternatives considered:**
- *Trust the constraints returned by MCP:* rejected because descriptive context cannot enforce policy.
- *Let an MCP server validate and execute SQL:* rejected for this implementation because it would combine context provision with the independent safety boundary.
- *Use a second LLM as a safety checker:* rejected because model-generated safety decisions are not deterministic enforcement.

**Reason:** Maintaining one independent enforcement point makes the security boundary explicit and supports tests that do not require an LLM.

**Consequences:** Changes to MCP descriptions do not change gateway permissions. Gateway policy changes require their own tests and review. The prototype must not describe MCP-based instructions as a security control.

**Implementation status:** `gateway/app/policy.py`, `gateway/app/execution.py`, and `gateway/app/audit.py` implement the enforcement boundary for one count-query structure. Audit records are persisted in SQLite at `/app/audit/events.sqlite` by default; application conversation logging remains separate and unimplemented under D-009.


## D-021 Curated, versioned JSON metadata with no database access
**Date:** 2026-11-02 **Status:** Accepted

**Context:** The initial schema is small, and the synthetic AKTIN/i2b2 schema and concept source remain to be confirmed (D-014). MCP context should be reproducible and reviewable.

**Decision:** Store each server's initial context in a separate version-controlled JSON file:
- schema and concepts metadata;
- constraints metadata;
- development examples.

Each document contains a context version and dataset identifier. The servers load their own document and serve only its curated content. They do not connect to PostgreSQL, receive database credentials, or return database records.

Development examples must not contain frozen final-test questions, reference outputs, or results that reveal expected evaluation answers.

**Alternatives considered:**
- *Read database metadata dynamically at each request:* rejected for the initial prototype because it gives the context service unnecessary database access and makes context behavior depend on live database state.
- *Store all context in Python source:* rejected because separate data files are easier to review and update.
- *Use a vector database immediately:* rejected because the current context is small and does not justify another dependency.

**Reason:** Versioned files support review, reproducibility, and a smaller permission scope.

**Consequences:** Schema changes do not automatically update the metadata. A context change requires review, a version update where appropriate, rebuilding the affected service, and regression tests. JSON structure and content must be validated. As the ontology grows, context retrieval must be bounded rather than returning the entire hierarchy for every request.


## D-022 Independent server and integration testing
**Date:** 2026-11-02 **Status:** Accepted

**Context:** Separate MCP services create separate startup, network, and tool-invocation failure modes. The application should be able to distinguish a context-service failure from a model or gateway failure.

**Decision:** Test the MCP services at two levels:
1. Unit tests for metadata loading, returned fields, versions, and example/policy consistency.
2. MCP integration tests for connection, initialization, tool discovery, and invocation against each container.

The application will handle an unavailable context server explicitly and log the failure. It must not silently treat missing schema or constraints as approval to execute a query. The final degraded-mode behavior—fail the request or proceed using another approved source—must be specified per context type before model integration.

**Alternatives considered:**
- *Test only through the final chat interface:* rejected because it would make MCP failures difficult to isolate.
- *Assume that a running container means MCP is working:* rejected because service startup does not prove protocol initialization or tool calls work.

**Reason:** Layered tests make service, protocol, and orchestration failures distinguishable.

**Consequences:** Unit tests can run without PostgreSQL or a model. Integration tests require the MCP services and their Docker network. The application must not make a successful query depend on fabricated context when an essential context service is unavailable.

**Implementation status:** `mcp_servers/tests/test_context.py` calls server tool functions directly. `mcp_servers/smoke_test.py` performs protocol initialization, discovery, and invocation against the three services sequentially, and fails if any server is unavailable. Independent degraded-mode behavior is not implemented because there is no application client.
