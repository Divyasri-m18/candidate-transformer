"""
Confidence scoring for extracted and merged field values.

Responsibilities:
  - Assign confidence scores based on source type (structured vs unstructured).
  - Adjust scores for extraction quality (e.g., regex match vs fuzzy parse).
  - Expose a consistent API used by parser, merger, and projector.
  - Ensure scores are deterministic for the same inputs.

Higher confidence values indicate more trustworthy field values during merge.
"""

from __future__ import annotations

from typing import Any


# Global priority mapping for conflict resolution (higher = more preferred)
PRIORITY_MAP: dict[str, int] = {
    "resume_pdf": 5,
    "ats_json": 4,
    "linkedin": 3,
    "github": 2,
    "recruiter_notes": 1,
}

# Global confidence scores mapping
CONFIDENCE_MAP: dict[str, float] = {
    "ats_json": 0.95,
    "resume_pdf": 0.85,
    "linkedin": 0.75,
    "github": 0.65,
    "recruiter_notes": 0.55,
}


def score_field(
    field_name: str,
    value: Any,
    source: str,
    *,
    extraction_hint: str | None = None,
) -> float:
    """
    Compute a deterministic confidence score for a single field value.

    Args:
        field_name: Name of the candidate field.
        value: The normalized or raw field value.
        source: Source identifier (e.g., 'ats_json', 'resume_pdf').
        extraction_hint: Optional hint about how the value was obtained.

    Returns:
        Confidence score in [0.0, 1.0].
    """
    if value is None or value == "" or value == [] or value == {}:
        return 0.0

    return CONFIDENCE_MAP.get(source, 0.0)


