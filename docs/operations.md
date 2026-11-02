# Local Docker Operations

The Compose file describes three MCP context services, the gateway, and an
optional PostgreSQL service under the `local-db` profile. Compose requires
`DB_PASSWORD` and `GATEWAY_API_KEY`; the PostgreSQL profile also requires
`POSTGRES_ADMIN_PASSWORD`. Supply these through a local environment file or
environment variables. Do not commit credentials. `.env.example` contains
demonstration values and must not be treated as production credentials.

To build and start the gateway and MCP services, with a configured environment:

```sh
docker compose build
docker compose up -d gateway mcp-schema mcp-constraints mcp-examples
```

The gateway is published on `127.0.0.1:8001`. MCP services listen on port 8000
inside the Compose network and have no published host ports. The gateway can
start without a database connection, but `/health/ready` and query execution
require a working database.

## Compose database initialization

The optional PostgreSQL service is enabled with:

```sh
docker compose --profile local-db up -d postgres
```

The included initialization is currently inconsistent: Compose creates the
`aktin` database and passes the role password as `QUERY_RO_PASSWORD`, while
`database/init/02-role.sh` reads `USER_PASSWORD` and grants connection to
`aktin_synth`. The script also runs only when PostgreSQL initializes an empty
data volume. Therefore these files do not currently establish a working
gateway role/database configuration. The source supports identifying this
mismatch, but correcting it would require a configuration change outside this
documentation task.

## Tests and MCP smoke check

The tests can be run using the Dockerfile test targets. These commands build
the test images and run the test suites; no test result is claimed here.

```sh
docker build --target test -t ba-gateway-tests ./gateway
docker run --rm -e GATEWAY_API_KEY=test-key ba-gateway-tests
docker build --target test -t ba-mcp-tests ./mcp_servers
docker run --rm ba-mcp-tests
```

Gateway tests cover parsing/policy, API response behavior, mocked database
execution, suppression, and audit failure handling. They do not verify a live
PostgreSQL connection or the Compose role setup. MCP unit tests directly call
the Python tool functions; they do not use the MCP protocol or containers.

`mcp_servers/smoke_test.py` performs MCP initialization, tool discovery, and
tool invocation against all three running services. With the MCP services
already running, invoke it inside the Compose network:

```sh
docker compose run --rm --no-deps --entrypoint python mcp-examples smoke_test.py
```

This smoke check is present but has no test-runner integration, and it has not
been run as part of this documentation review. It processes servers
sequentially and raises if any is unavailable; independent/degraded-mode
behavior is not implemented by an application because no application exists.

To stop services:

```sh
docker compose down
```

This does not remove named volumes. PostgreSQL data persists in `pgdata`, and
gateway audit data persists in `gateway_audit`.
