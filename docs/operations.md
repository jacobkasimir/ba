# Local Docker Operations

The Compose project contains the browser application, query gateway, three
MCP context services, and an optional PostgreSQL 16 service in the
`local-db` profile. Required local database and gateway credentials are
`DB_PASSWORD` and `GATEWAY_API_KEY`; the local PostgreSQL profile additionally
requires `POSTGRES_ADMIN_PASSWORD`. The optional assistant has its own
provider configuration. See the table below and the detailed
[LLM integration guide](llm-integration.md).

## Start and stop

Create `.env` from the safe template and fill local values. `.env.example`
sets `LLM_ENABLED=false`; enabling the assistant requires setting it to
`true` and filling the provider variables. Shell environment variables take
precedence over `.env` during Compose interpolation, so an exported
`LLM_ENABLED=false` overrides `.env`'s `true`.

Validate and start the full local stack, including PostgreSQL:

```sh
docker compose config --quiet
docker compose --profile local-db up -d --build
```

To start the application, gateway, and MCP services without the local database
container:

```sh
docker compose config --quiet
docker compose up -d --build application gateway mcp-schema mcp-constraints mcp-examples
```

This second command still requires `GATEWAY_API_KEY` at Compose configuration
time. The gateway can start while PostgreSQL is unavailable, but `/health/ready`
and query execution require a working database. The application and gateway
are published at `127.0.0.1:8080` and `127.0.0.1:8001`; MCP services have no
published host ports. Compose does not define service readiness dependencies.
After changing environment variables, recreate the application container:

```sh
docker compose up -d --force-recreate application
```

The application service bind-mounts `./application/static` at `/app/static`.
Changes to HTML, CSS, and JavaScript files are served immediately, without
rebuilding or restarting the application container. Python/API changes still
require rebuilding and recreating the application service. This bind mount is
intended for local development; remove it in a deployment that packages the
frontend into the application image.

Stop services with `docker compose down`. This retains named volumes; it does
not delete PostgreSQL data, gateway audit records, or application logs.

## Configuration

Compose reads interpolation values from the invoking shell first, then its
project `.env`. The application receives the following variables:

| Variable | Default / requirement | Purpose |
|---|---|---|
| `LLM_ENABLED` | `false` | Enables the optional assistant only when its value lowercases to `true`. |
| `LLM_BASE_URL` | Required when enabled | Absolute HTTP(S) provider API base URL; the client appends `chat/completions`. |
| `LLM_API_KEY` | Required when enabled | Provider credential sent as a Bearer token; held by the application container. |
| `LLM_MODEL` | Required when enabled | Provider deployment/model identifier accepted by that endpoint. |
| `LLM_LOG_RAW_RESPONSES` | `false` | Temporary diagnostic opt-in that writes bounded raw provider response bodies to the application container log. May include generated content; keep disabled outside local debugging. |
| `APP_GATEWAY_URL` | `http://host.docker.internal:8001` in Compose | Gateway base URL; must be paired with `APP_GATEWAY_KEY`. |
| `APP_GATEWAY_KEY` | Mapped from `GATEWAY_API_KEY` | Shared server-to-server key sent as `X-Gateway-Key`. |
| `APP_GATEWAY_TIMEOUT` | `12` seconds | Application-to-gateway timeout. |
| `ENABLE_DEBUG_TOOLS` | `true` in Compose; otherwise `false` | Allows direct `/tool` commands on `/api/chat`. |
| `MCP_CONFIG_PATH` | Compose mount `/app/config/mcp_servers.json` | MCP server addresses, allowed tool names, and timeouts. |
| `APP_LOG_PATH` | Compose volume `/app/logs/app.log.jsonl` | Sanitized application operational JSONL events. |

The gateway and local database use these Compose variables:

| Variable | Default / requirement | Purpose |
|---|---|---|
| `GATEWAY_API_KEY` | Required | Gateway key; Compose also maps it to the application. |
| `DB_HOST`, `DB_PORT` | `postgres`, `5432` | Gateway database address. |
| `DB_NAME`, `DB_USER` | `aktin`, `user` | Gateway database and role. The init script creates the fixed role `user`; changing `DB_USER` alone breaks the local profile. |
| `DB_PASSWORD` | Required | Gateway role password and Compose `QUERY_RO_PASSWORD`. |
| `DB_SSLMODE`, `DB_SSLROOTCERT` | `disable`, empty | PostgreSQL TLS mode and optional CA file. |
| `POSTGRES_ADMIN_PASSWORD` | Required for `local-db` | PostgreSQL initialization administrator password. |
| `MIN_CELL_COUNT` | `5`, minimum `5` | Gateway suppression threshold. This demo setting is not a settled governance value. |
| `AUDIT_PATH` | `/app/audit/events.sqlite` | Gateway SQLite audit database path. |

The gateway requires `APP_GATEWAY_URL` and `APP_GATEWAY_KEY` together. If
`LLM_ENABLED=true` but gateway configuration is missing, startup fails. If the
assistant is disabled, `/api/assistant` returns `503 assistant_not_configured`;
the Echo/debug chat remains available. Invalid MCP configuration fails
application startup. MCP network availability is checked lazily during status
checks or requests. An enabled assistant also fails startup if required
provider variables are missing or invalid.

## Test, protocol, and provider commands

Build and run the Dockerfile test targets:

```sh
docker build --target test -t ba-application-tests ./application
docker run --rm ba-application-tests

docker build --target test -t ba-gateway-tests ./gateway
docker run --rm -e GATEWAY_API_KEY=test-key ba-gateway-tests

docker build --target test -t ba-mcp-tests ./mcp_servers
docker run --rm ba-mcp-tests
```

These are mocked/unit-level suites, with distinct boundaries:

- Application tests cover Echo/debug API behavior, assistant service
  orchestration with fake services, the LLM HTTP contract with
  `httpx.MockTransport`, and application-to-gateway HTTP behavior with a mock
  transport. They do not call a live model, MCP network, gateway, or database.
- Gateway tests mock database execution and audit failures. They test SQL
  parsing/policy, response and suppression behavior, not a live PostgreSQL
  connection or Compose database initialization.
- MCP unit tests call server functions in-process; they do not use the MCP
  wire protocol or running containers.
- There is no separate one-request provider smoke-test target. The four-case
  real-provider evaluator below is the repository's provider-facing check; it
  tests a small intent set rather than only endpoint connectivity.

The separate protocol smoke test performs MCP initialization, discovery, and
tool invocation against all three running services. Start the Compose stack,
then run:

```sh
docker compose run --rm --no-deps --entrypoint python mcp-examples smoke_test.py
```

The real-provider intent evaluation is not part of any Dockerfile test target.
It sends four requests to the configured provider and never submits proposals
to the gateway. It can incur provider charges. To run it in the application
image without mounting `.env` into the container:

```sh
docker compose run --rm \
  -v "$PWD/application:/workspace/application:ro" \
  -v "$PWD/evaluation:/workspace/evaluation:ro" \
  -v "$PWD/mcp_servers/schema/context:/workspace/mcp_servers/schema/context:ro" \
  -v "$PWD/mcp_servers/constraints/context:/workspace/mcp_servers/constraints/context:ro" \
  -v "$PWD/mcp_servers/examples/context:/workspace/mcp_servers/examples/context:ro" \
  -w /workspace application \
  python3 evaluation/development/run_assistant_intent_eval.py
```

Compose supplies the application service's configured environment. The
provider-specific requirements and runner limits are documented in
[LLM integration](llm-integration.md). There is no automated full end-to-end
test that connects a live provider, MCP services, gateway, and PostgreSQL.

## Troubleshooting

| Symptom | Check |
|---|---|
| `/api/assistant` returns `assistant_not_configured` | Check `LLM_ENABLED` inside the running application container. Recreate it after changing Compose variables. An exported shell variable overrides `.env`. |
| `/api/assistant` returns `context_unavailable` | Call `/api/mcp/status`; ensure all three MCP services are running and the configured tool names match `config/mcp_servers.json`. Context errors are deliberately collapsed to this code. |
| `llm_provider_error` | The provider returned non-200; the browser sees only a safe error code. The development evaluator can optionally print bounded provider error fields with `LLM_EVAL_PROVIDER_DIAGNOSTICS=1`. Confirm deployment ID, auth, and support for strict JSON Schema plus `max_completion_tokens`. |
| `invalid_llm_response` | Temporarily set `LLM_LOG_RAW_RESPONSES=true` in `.env`, recreate the application, retry once, and inspect `docker compose logs --since=5m application`. The response body is escaped and bounded (64 KiB for success, 8 KiB for provider errors). Turn the option off and recreate the application after debugging; logs may contain generated or echoed content. |
| `gateway_unavailable` / `gateway_authentication_failed` | Check the application gateway URL/key pair, gateway container, and shared key mapping. |
| Gateway returns `query_rejected` | The proposal did not match the exact supported SQL shape or gateway input constraints. No SQL repair/retry is performed. |
| Gateway readiness/query fails against local PostgreSQL | Check database status and logs. On an existing `pgdata` volume, init scripts do not rerun. With a custom `DB_USER`, the fixed `user` role from `database/init/02-role.sh` must also be reconciled. |

For a full teardown that also deletes data, inspect the named volumes before
using `docker compose down -v`; that command permanently removes persisted
database, audit, and log data.
