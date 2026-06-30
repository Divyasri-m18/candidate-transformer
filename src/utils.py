"""
Shared utility helpers used across the pipeline.

Responsibilities:
  - JSON file read/write with consistent encoding and error handling.
  - Common string cleaning (strip, collapse whitespace).
  - Path helpers and small pure functions with no domain-specific logic.

Keeps cross-cutting concerns out of parser, normalizer, merger, and projector.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json_file(path: str | Path) -> Any:
    """
    Read and parse a JSON file.

    Args:
        path: Path to the JSON file.

    Returns:
        Parsed JSON content.
    """
    with Path(path).open(encoding="utf-8") as f:
        return json.load(f)


def write_json_file(path: str | Path, data: Any, *, indent: int = 2) -> None:
    """
    Write data to a JSON file with stable formatting.

    Args:
        path: Destination file path.
        data: JSON-serializable object.
        indent: Indentation level for pretty-printing.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False, sort_keys=True)


def clean_string(value: str) -> str:
    """Strip leading/trailing whitespace and collapse internal runs of spaces."""
    return " ".join(value.split())
