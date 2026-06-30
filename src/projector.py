"""
Output projection using configurable field selection.

Responsibilities:
  - Load output_config.json and interpret projection rules.
  - Shape merged canonical records into the final JSON schema.
  - Include or exclude provenance and confidence based on config.
  - Serialize the result for writing to disk.

Separates "what we know" (internal model) from "what we emit" (output contract).
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .utils import read_json_file


def load_output_config(path: str) -> dict[str, Any]:
    """
    Load and validate the output projection configuration.

    Args:
        path: Filesystem path to output_config.json.

    Returns:
        Parsed configuration dict.
    """
    return read_json_file(path)


def project_candidate(
    candidate: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    """
    Project a merged candidate onto the configured output shape.
    This function does not mutate the input candidate.

    Args:
        candidate: Fully merged internal candidate record.
        config: Output projection configuration.

    Returns:
        Final candidate dict ready for JSON serialization.
    """
    projected: dict[str, Any] = {}

    include_confidence = config.get("include_confidence", True)
    include_provenance = config.get("include_provenance", True)
    fields = config.get("fields", [])
    rename_map = config.get("rename", {})
    on_missing = config.get("on_missing", {})
    default_missing_action = on_missing.get("default", "omit")

    proj_confidence: dict[str, float] = {}
    proj_provenance: dict[str, Any] = {}

    for field in fields:
        output_key = rename_map.get(field, field)
        val = candidate.get(field)

        # Check if missing or empty
        is_missing = val is None or val == "" or val == [] or val == {}

        if is_missing:
            action = on_missing.get(field, default_missing_action)
            if action == "null":
                projected[output_key] = None
            elif action == "empty_object":
                projected[output_key] = {}
            elif action == "omit":
                continue
        else:
            projected[output_key] = val

        # Handle confidence key and value if requested
        if include_confidence and "confidence" in candidate:
            conf_val = candidate["confidence"].get(field)
            if conf_val is not None:
                proj_confidence[output_key] = conf_val

        # Handle provenance key and value if requested
        if include_provenance and "provenance" in candidate:
            prov_val = candidate["provenance"].get(field)
            if prov_val is not None:
                if hasattr(prov_val, "__dataclass_fields__"):
                    proj_provenance[output_key] = asdict(prov_val)
                else:
                    proj_provenance[output_key] = prov_val

    if include_confidence:
        projected["confidence"] = proj_confidence

    if include_provenance:
        projected["provenance"] = proj_provenance

    return projected


def project_candidates(
    candidate_list: list[dict[str, Any]],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    Project a list of merged candidates onto the configured output shape.

    Args:
        candidate_list: List of fully merged candidate records.
        config: Output projection configuration.

    Returns:
        List of projected candidate dicts.
    """
    return [project_candidate(c, config) for c in candidate_list]

