# AKTIN Insight Research Prototype

This repository contains a local Docker Compose prototype with a FastAPI web
application, three MCP context services, a separate query gateway, and an
optional PostgreSQL connectivity fixture. The chat is currently echo-only for
ordinary messages; no LLM integration or natural-language SQL generation is
implemented. See [Current Architecture](docs/architecture.md) and
[Frontend Integration](docs/frontend_integration.md).

## Start locally

Create a local environment file from the placeholder template and replace the
required placeholders with local-only values:

```sh
cp .env.example .env
```

The normal stack requires `DB_PASSWORD` and `GATEWAY_API_KEY`; the optional
PostgreSQL profile also requires `POSTGRES_ADMIN_PASSWORD`. Do not commit `.env`
or put credentials in `.env.example`.

Build and start the application, gateway, and MCP services:

```sh
docker compose build
docker compose up -d application gateway mcp-schema mcp-constraints mcp-examples
```

Open <http://127.0.0.1:8080/>. The application UI/API and gateway are bound to
loopback ports 8080 and 8001. MCP services have no published host ports.

To include the optional local PostgreSQL fixture, use:

```sh
docker compose --profile local-db up -d postgres
```

The fixture contains 20 synthetic rows and is not the planned evaluation
dataset. Initialization scripts run only for a new PostgreSQL data volume.
See [Operations](docs/operations.md) before changing or reusing that volume.

Stop the services with:

```sh
docker compose down
```

## Documentation

- [Architecture](docs/architecture.md)
- [Application and MCP integration](docs/app_mcp_integration.md)
- [Frontend behavior](docs/frontend_integration.md)
- [Operations and tests](docs/operations.md)
- [Threat model](docs/threat-model.md)
- [Gateway policy](docs/policy.md)
- [Evaluation status](docs/evaluation-plan.md)
