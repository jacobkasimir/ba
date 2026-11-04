# AKTIN Insight Research Prototype

This repository contains a local Docker Compose prototype with a browser UI,
FastAPI application, three read-only MCP context services, a query gateway,
and an optional PostgreSQL connectivity fixture. The UI keeps its Echo and
developer-tool workflow, supports explicit SQL submission, and has a separate
optional natural-language assistant. The assistant supports only the total
row count of the synthetic `public.patient_dimension` fixture; it is not
general clinical text-to-SQL.

See [Architecture](docs/architecture.md) for the request flows and
[LLM integration](docs/llm-integration.md) for the assistant contract,
configuration, provider requirements, and trust boundaries.

## Start locally

Copy the example file, then set local credentials in `.env`. Keep real values
out of version control. `LLM_ENABLED` defaults to `false`; enable it and set
the provider API base URL, API key, and deployment name only if you want the
assistant workflow.

```sh
cp .env.example .env
docker compose config --quiet
docker compose --profile local-db up -d --build
```

The local UI and application API are available at <http://127.0.0.1:8080/>;
the gateway is published at `127.0.0.1:8001`. MCP endpoints are internal to
the Compose network. The local PostgreSQL database has 20 synthetic rows and
is a connectivity fixture, not the planned AKTIN/i2b2 evaluation dataset.
Initialization scripts run only when PostgreSQL initializes an empty data
volume. See [Operations](docs/operations.md) before reusing that volume.

## Tests and evaluation

Each service has a Dockerfile `test` target. The application unit and
integration tests use fakes or in-memory HTTP transports; they do not exercise
a live provider, gateway, MCP network, or PostgreSQL. The MCP protocol smoke
test is separate. A four-case real-provider development evaluator is in
`evaluation/development/`; it calls the configured provider and can incur
charges. No live provider call is made by the test targets.

Exact commands and test boundaries are in [Operations](docs/operations.md).
The development evaluation set and its limits are described in
[Evaluation status](docs/evaluation-plan.md).

## Documentation

- [Architecture](docs/architecture.md)
- [Application and MCP integration](docs/app_mcp_integration.md)
- [Frontend behavior](docs/frontend_integration.md)
- [Operations, configuration, and tests](docs/operations.md)
- [LLM integration](docs/llm-integration.md)
- [Threat model](docs/threat-model.md)
- [Gateway policy](docs/policy.md)
- [Gateway implementation](docs/gateway-v1.md)
- [Evaluation status](docs/evaluation-plan.md)
