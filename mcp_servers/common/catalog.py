import json
from pathlib import Path


# Keep initial metadata small.
# Larger context later requires deliberate retrieval and size policies.
MAX_CONTEXT_BYTES = 64 * 1024


def load_catalog(
    path: Path,
    required_section: str,
) -> dict:
    """Load a curated local context document.

    The caller is server code, not an MCP user.
    No externally supplied filesystem path is accepted.
    """

    if path.stat().st_size > MAX_CONTEXT_BYTES:
        raise ValueError("Context document is too large")

    with path.open(encoding="utf-8") as file:
        catalog = json.load(file)

    if not isinstance(catalog, dict):
        raise ValueError("Context must be a JSON object")

    required_keys = {
        "context_version",
        "dataset_id",
        required_section,
    }

    if not required_keys.issubset(catalog):
        raise ValueError("Missing required context fields")

    if not isinstance(catalog["context_version"], str):
        raise ValueError("context_version must be a string")

    if not isinstance(catalog["dataset_id"], str):
        raise ValueError("dataset_id must be a string")

    return catalog