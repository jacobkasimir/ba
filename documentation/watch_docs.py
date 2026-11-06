#!/usr/bin/env python3
"""Event-driven docs watcher with a short debounce and serialized builds."""

from __future__ import annotations

import argparse
import logging
import threading
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from docs_pipeline import APPLICATION_MODULES, GATEWAY_MODULES, build


WORKSPACE = Path("/workspace")
SOURCE_ROOTS = (
    WORKSPACE / "docs",
    WORKSPACE / "evaluation" / "reports",
    Path("/source/application/app"),
    Path("/source/gateway/app"),
)
WATCH_FILES = {WORKSPACE / "README.md", WORKSPACE / "mkdocs.yml"}
WRITE_EVENT_TYPES = {"created", "modified", "moved", "deleted"}
WATCHED_PYTHON_FILES = {
    Path("/source/application/app") / f"{module.removeprefix('app.')}.py"
    for module in APPLICATION_MODULES
} | {
    Path("/source/gateway/app") / f"{module.removeprefix('app.')}.py"
    for module in GATEWAY_MODULES
} | {
    Path("/source/application/app/__init__.py"),
    Path("/source/gateway/app/__init__.py"),
}
DEBOUNCE_SECONDS = 0.75

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("docs-watch")


class Handler(FileSystemEventHandler):
    """Debounce source changes; a single lock prevents overlapping builds."""

    def __init__(self) -> None:
        self._timer_lock = threading.Lock()
        self._build_lock = threading.Lock()
        self._timer: threading.Timer | None = None

    @staticmethod
    def relevant(event: FileSystemEvent) -> bool:
        if event.is_directory:
            return False
        paths = [Path(event.src_path)]
        destination = getattr(event, "dest_path", None)
        if destination:
            paths.append(Path(destination))
        return any(
            path in WATCH_FILES
            or path.suffix.lower() == ".md"
            or path in WATCHED_PYTHON_FILES
            for path in paths
        )

    def on_any_event(self, event: FileSystemEvent) -> None:
        # Ignore opened/read events: pdoc and MkDocs read watched sources while
        # building and must not recursively schedule another build.
        if event.event_type not in WRITE_EVENT_TYPES or not self.relevant(event):
            return
        with self._timer_lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(
                DEBOUNCE_SECONDS,
                self.rebuild,
                args=(event.src_path,),
            )
            self._timer.daemon = True
            self._timer.start()

    def rebuild(self, changed_path: str) -> None:
        with self._build_lock:
            logger.info("Source changed (%s); regenerating pdoc and MkDocs", changed_path)
            try:
                build()
            except Exception:
                logger.exception("Documentation build failed; previous site remains available")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--once",
        action="store_true",
        help="Generate pdoc and build the static MkDocs site, then exit",
    )
    args = parser.parse_args()

    if args.once:
        build()
        return

    # Build before reporting healthy/starting the observer so the application
    # can wait on the docs service's site-volume healthcheck.
    build()
    observer = Observer()
    handler = Handler()
    observer.schedule(handler, str(WORKSPACE), recursive=False)
    for root in SOURCE_ROOTS:
        observer.schedule(handler, str(root), recursive=True)
    observer.start()
    logger.info("Watching Markdown, MkDocs config, and selected Python sources")
    try:
        observer.join()
    except KeyboardInterrupt:
        observer.stop()
        observer.join()


if __name__ == "__main__":
    main()
