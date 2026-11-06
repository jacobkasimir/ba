#!/usr/bin/env python3
"""Generate separated pdoc references, then build the strict MkDocs site."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


WORKSPACE = Path("/workspace")
SOURCE_ROOT = Path("/source")
WORKTREE = Path("/worktree")
API_OUTPUT = Path("/generated")

APPLICATION_MODULES = (
    "app.assistant_api",
    "app.assistant_bindings",
    "app.assistant_context",
    "app.assistant_models",
    "app.assistant_service",
    "app.gateway_client",
    "app.llm_client",
    "app.mcp_client",
    "app.query_api",
)
GATEWAY_MODULES = (
    "app.policy",
    "app.schemas",
)


def run_pdoc(package_root: Path, modules: tuple[str, ...], target: Path) -> None:
    """Import only selected modules with that service's package root first."""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(package_root)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pdoc",
            "--docformat",
            "google",
            "-o",
            str(target),
            *modules,
        ],
        cwd=package_root,
        env=env,
        check=True,
    )


def replace_tree(source: Path, target: Path) -> None:
    """Replace one generated tree only after pdoc completed successfully."""
    target.parent.mkdir(parents=True, exist_ok=True)
    new_target = target.with_name(target.name + ".new")
    backup = target.with_name(target.name + ".old")
    shutil.rmtree(new_target, ignore_errors=True)
    shutil.rmtree(backup, ignore_errors=True)
    shutil.copytree(source, new_target)
    if target.exists():
        target.rename(backup)
    new_target.rename(target)
    shutil.rmtree(backup, ignore_errors=True)


def prepare_worktree() -> None:
    """Copy only mounted documentation sources into a disposable build tree."""
    shutil.rmtree(WORKTREE, ignore_errors=True)
    WORKTREE.mkdir(parents=True)
    # Rename README in the site source so MkDocs does not treat it as a
    # conflicting implicit alias for the explicit index.md home page.
    shutil.copy2(WORKSPACE / "README.md", WORKTREE / "project-overview.md")
    shutil.copytree(
        WORKSPACE / "docs",
        WORKTREE / "docs",
        ignore=shutil.ignore_patterns("api", "index.md"),
    )
    shutil.copy2(WORKSPACE / "docs" / "index.md", WORKTREE / "index.md")
    shutil.copytree(
        WORKSPACE / "evaluation" / "reports",
        WORKTREE / "evaluation" / "reports",
    )
    shutil.copytree(
        API_OUTPUT / "application",
        WORKTREE / "docs" / "api" / "application",
    )
    shutil.copytree(
        API_OUTPUT / "gateway",
        WORKTREE / "docs" / "api" / "gateway",
    )


def build() -> None:
    """Render API modules independently, then build MkDocs with strict links."""
    API_OUTPUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pdoc-") as temporary:
        temporary_root = Path(temporary)
        application_output = temporary_root / "application"
        gateway_output = temporary_root / "gateway"

        # These imports construct no services, clients, DB connections, or
        # configuration. In particular, application.main and gateway.main
        # are intentionally excluded because they load runtime configuration.
        run_pdoc(
            SOURCE_ROOT / "application",
            APPLICATION_MODULES,
            application_output,
        )
        run_pdoc(
            SOURCE_ROOT / "gateway",
            GATEWAY_MODULES,
            gateway_output,
        )

        replace_tree(application_output, API_OUTPUT / "application")
        replace_tree(gateway_output, API_OUTPUT / "gateway")

    prepare_worktree()

    subprocess.run(
        ["mkdocs", "build", "--strict", "--clean", "--config-file", str(WORKSPACE / "mkdocs.yml")],
        cwd=WORKTREE,
        check=True,
    )


if __name__ == "__main__":
    build()
