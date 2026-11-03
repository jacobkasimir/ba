# Local Docker Operations

The Compose stack contains the browser application, query gateway, three MCP
context services, and an optional PostgreSQL service under the `local-db`
profile. The gateway requires `DB_PASSWORD` and `GATEWAY_API_KEY`. The
application receives the gateway URL from `APP_GATEWAY_URL` (default
`http://host.docker.internal:8001`) and the same credential through
`APP_GATEWAY_KEY`, which Compose maps from `GATEWAY_API_KEY`. The optional
PostgreSQL profile also requires `POSTGRES_ADMIN_PASSWORD`.

Start by copying `.env.example` to `.env`, then replace each placeholder with
local values. Do not commit `.env` or use real credentials in the example
file. `.env.example` contains placeholder values, not working credentials.
`GATEWAY_API_KEY` is a shared application-to-gateway credential; keep it
server-side and do not put it in browser configuration.

To build and start the application, gateway, and MCP services:

```sh
docker compose build
docker compose up -d application gateway mcp-schema mcp-constraints mcp-examples
```

The application UI and API are published on `127.0.0.1:8080`; the gateway is
published on `127.0.0.1:8001`. MCP services listen on port 8000 inside the
Compose network and have no published host ports. The application requires
`APP_GATEWAY_URL` and `APP_GATEWAY_KEY` together when gateway access is
configured. Without both, the app can start and serve non-query features, but
query submission returns `503 gateway_unavailable`. Compose configures both
for the normal stack and currently requires `GATEWAY_API_KEY` during Compose
configuration even when starting only the application service. The gateway
can start without a database connection, but `/health/ready` and query
execution require a working database.

## Configuration

Compose sets `MCP_CONFIG_PATH` to the read-only mounted
`config/mcp_servers.json` and `APP_LOG_PATH` to the persistent application log
volume. For direct application runs, these variables default to
`/app/config/mcp_servers.json` and `/app/logs/app.log.jsonl`. Configure:

| Variable | Required | Purpose |
|---|---|---|
| `APP_GATEWAY_URL` | Together with `APP_GATEWAY_KEY` | Gateway base URL; Compose defaults to `http://host.docker.internal:8001`. |
| `APP_GATEWAY_KEY` | Together with `APP_GATEWAY_URL` | Server-side credential sent as `X-Gateway-Key`; in Compose it comes from `GATEWAY_API_KEY`. |
| `APP_GATEWAY_TIMEOUT` | No | Gateway request timeout in seconds; defaults to `12`. |
| `MCP_CONFIG_PATH` | No | MCP server configuration path; defaults to `/app/config/mcp_servers.json`. |
| `APP_LOG_PATH` | No | Application event log path; defaults to `/app/logs/app.log.jsonl`. |
| `ENABLE_DEBUG_TOOLS` | No | Enables development MCP tool commands only when set to `true`; defaults to `false`. |

For the gateway and database variables, see `.env.example` and the Compose
environment section. The optional `local-db` profile can be started with:

```sh
docker compose --profile local-db up -d postgres
```

Compose passes `DB_NAME` to PostgreSQL as `POSTGRES_DB` and to the gateway as
`DB_NAME`. The role initialization connects to `POSTGRES_DB`, grants access to
that same database, and reads the role password from `QUERY_RO_PASSWORD`, which
Compose sources from `DB_PASSWORD`. Initialization scripts run only when
PostgreSQL initializes an empty data volume. If changing the database setup on
an existing volume, recreate or explicitly migrate that volume before
expecting the initialization scripts to run again.

## Tests and MCP smoke check

Build and run each test suite with its Dockerfile test target:

```sh
docker build --target test -t ba-application-tests ./application
docker run --rm ba-application-tests
docker build --target test -t ba-gateway-tests ./gateway
docker run --rm -e GATEWAY_API_KEY=test-key ba-gateway-tests
docker build --target test -t ba-mcp-tests ./mcp_servers
docker run --rm ba-mcp-tests
```

Application tests use temporary configuration and log files. Query integration
tests replace the gateway transport with an in-memory HTTP mock; they do not
need a running gateway or database. Gateway tests cover parsing/policy, API
response behavior, mocked database execution, suppression, and audit failure
handling. They do not verify a live PostgreSQL connection or the Compose role
setup. MCP unit tests directly call the Python tool functions; they do not use
the MCP protocol or containers.

`mcp_servers/smoke_test.py` performs MCP initialization, tool discovery, and
tool invocation against all three running services. With the MCP services
already running, invoke it inside the Compose network:

```sh
docker compose run --rm --no-deps --entrypoint python mcp-examples smoke_test.py
```

This smoke check has no test-runner integration. It processes servers
sequentially and raises if any is unavailable.

To stop services:

```sh
docker compose down
```

This does not remove named volumes. PostgreSQL data persists in `pgdata`, and
gateway audit and application logs persist in `gateway_audit` and
`application_logs`.
