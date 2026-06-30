"""
Canonical candidate data model and JSON schema definitions.

Responsibilities:
  - Define typed structures (dataclasses or TypedDicts) for candidate entities.
  - Document expected fields: identity, contact, experience, education, skills, etc.
  - Provide helpers to create empty records and validate required shapes.
  - Serve as the single source of truth for internal record structure.

Keeps schema concerns separate from parsing, normalization, and merging logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Provenance:
    """Tracks where a field value originated."""

    source: str = ""
    source_path: str = ""
    raw_value: Any = None


@dataclass
class CandidateRecord:
    """
    Internal canonical representation of a candidate.

    Fields will be expanded as the pipeline is built out step by step.
    """

    candidate_id: str = ""
    email: str = ""
    phone: str = ""
    skills: list[str] = field(default_factory=list)
    provenance: dict[str, Provenance] = field(default_factory=dict)
    confidence: dict[str, float] = field(default_factory=dict)


def empty_candidate() -> CandidateRecord:
    """Return a new empty candidate record."""
    return CandidateRecord()
