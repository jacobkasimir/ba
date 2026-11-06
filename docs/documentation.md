# Documentation development

The project documentation is served at `http://127.0.0.1:8080/project-docs/`
from the existing FastAPI origin. FastAPI's Swagger UI remains at
`http://127.0.0.1:8080/docs`; the project documentation does not replace it.

## Start the local documentation service

From the repository root, run:

```sh
docker compose up -d --build application docs
```

The application waits for the docs service to complete its initial generation.
The docs service has no published port and uses `network_mode: none`; only the
application serves the generated site. It receives no `.env`, credentials,
MCP configuration, or runtime data.

## Live Markdown updates

The docs service mounts `README.md`, `docs/`, and the evaluation report
directory read-only. It watches these files and `mkdocs.yml`. After saving a
Markdown file, the watcher waits briefly for a burst of editor writes, runs
`mkdocs build --strict --clean`, and updates the shared site volume. Refresh
the documentation page to see the new version. No image rebuild is needed.

Follow the watcher output with:

```sh
docker compose logs -f docs
```

## Live Python API docstrings

Selected `application/app/` and `gateway/app/` modules are mounted read-only
into the docs service. A change to a Python file triggers pdoc in a separate
import process for each `app` package, then rebuilds MkDocs. The entry-point
modules that read runtime secrets or initialize services are excluded. The
generated pdoc output lives in the `project_docs_api` named volume, not in the
source tree. No image rebuild is needed for docstring edits.

To manually regenerate pdoc and the static site once:

```sh
docker compose exec docs python /usr/local/bin/watch_docs.py --once
```

This also runs the strict MkDocs build. A failed build leaves the previous site
available and reports the error in the docs service logs.

## Static production build

Create a deployable static site in the ignored local artifact directory:

```sh
mkdir -p artifacts/project-docs
docker compose run --rm --no-deps \
  -v "$PWD/artifacts/project-docs:/site" \
  docs python /usr/local/bin/watch_docs.py --once
```

Publish the contents of `artifacts/project-docs/` on a static-file host. This
site build includes the current MkDocs pages and pdoc references. A static
production site does not watch the repository; content changes require a new
site build and publication. Changes to MkDocs/pdoc dependencies or the docs
Dockerfile also require rebuilding the docs image. In development, changes to
Markdown and watched Python docstrings are regenerated without an image rebuild.

## Generated Python API scope

The API reference includes selected public assistant, client, MCP, SQL policy,
and gateway schema modules. Application and gateway imports run in separate
processes with separate `PYTHONPATH` values because both packages are named
`app`. Service entry points (`app.main`) are excluded to avoid runtime
configuration and service initialization. The docs service mounts only the
selected Python source trees and does not mount local secrets or configuration.
