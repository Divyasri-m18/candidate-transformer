"""
Field-level normalization for candidate data.

Responsibilities:
  - Normalize emails to lowercase.
  - Normalize phone numbers to E.164 format.
  - Normalize dates to YYYY-MM.
  - Map raw skill strings to canonical skill names.
  - Apply consistent trimming and casing rules where applicable.

Normalization is deterministic: the same raw input always yields the same output.
"""

from __future__ import annotations

import copy
import re
from typing import Any

from .utils import clean_string

# ---------------------------------------------------------------------------
# Skill canonicalization — keys are compared case-insensitively after strip.
# ---------------------------------------------------------------------------

_SKILL_CANONICAL: dict[str, str] = {
    "cpp": "C++",
    "c plus plus": "C++",
    "js": "JavaScript",
    "py": "Python",
    "postgres": "PostgreSQL",
}

# Month abbreviations and full names → zero-padded month number.
_MONTH_TO_NUM: dict[str, str] = {
    "jan": "01",
    "january": "01",
    "feb": "02",
    "february": "02",
    "mar": "03",
    "march": "03",
    "apr": "04",
    "april": "04",
    "may": "05",
    "jun": "06",
    "june": "06",
    "jul": "07",
    "july": "07",
    "aug": "08",
    "august": "08",
    "sep": "09",
    "sept": "09",
    "september": "09",
    "oct": "10",
    "october": "10",
    "nov": "11",
    "november": "11",
    "dec": "12",
    "december": "12",
}

# Already YYYY-MM or YYYY-M (single-digit month).
_ISO_YEAR_MONTH = re.compile(r"^(\d{4})-(\d{1,2})$")

# e.g. "Apr 2024", "August 2017"
_MONTH_NAME_YEAR = re.compile(
    r"^([A-Za-z]+)\s+(\d{4})$",
    re.IGNORECASE,
)

# Split "Apr 2024 - Present" or "Aug 2017 - May 2021"
_DATE_RANGE_SPLIT = re.compile(r"\s*-\s*")


def normalize_email(email: str) -> str:
    """
    Normalize an email address: trim whitespace and lowercase.

    Args:
        email: Raw email string.

    Returns:
        Normalized email, or empty string if input is blank.
    """
    if not email:
        return ""
    return email.strip().lower()


def normalize_phone(phone: str) -> str:
    """
    Normalize an Indian phone number to E.164 format (+91XXXXXXXXXX).

    Handles inputs with or without country code, spaces, and dashes.
    Non-Indian numbers that already start with '+' are digit-stripped and
    re-prefixed; unrecognizable input is returned trimmed unchanged.

    Args:
        phone: Raw phone string.

    Returns:
        E.164 phone string (e.g. ``+919876543210``), or trimmed original.
    """
    if not phone:
        return ""

    stripped = phone.strip()
    digits = re.sub(r"\D", "", stripped)

    # 10-digit Indian mobile without country code.
    if len(digits) == 10:
        return f"+91{digits}"

    # 12-digit number with leading 91 country code.
    if len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"

    # Already E.164-like with '+' prefix — keep digits only after '+'.
    if stripped.startswith("+"):
        return f"+{digits}" if digits else stripped

    return stripped


def normalize_skill(skill: str) -> str:
    """
    Map a single raw skill label to its canonical form.

    Unknown skills are returned trimmed with original casing preserved.

    Args:
        skill: Raw skill string.

    Returns:
        Canonical skill name.
    """
    if not skill:
        return ""

    trimmed = skill.strip()
    canonical = _SKILL_CANONICAL.get(trimmed.lower())
    return canonical if canonical is not None else trimmed


def normalize_skills(skills: list[str]) -> list[str]:
    """
    Canonicalize a skill list and remove duplicates while preserving order.

    Args:
        skills: List of raw skill strings.

    Returns:
        Deduplicated list of canonical skill names.
    """
    seen: set[str] = set()
    result: list[str] = []

    for skill in skills:
        canonical = normalize_skill(skill)
        if not canonical:
            continue
        # Case-sensitive dedup after canonicalization (C++ vs c++ resolved by map).
        if canonical in seen:
            continue
        seen.add(canonical)
        result.append(canonical)

    return result


def normalize_name(name: str) -> str:
    """
    Normalize a person name: trim, collapse whitespace, title case.

    Args:
        name: Raw full name.

    Returns:
        Normalized name string.
    """
    if not name:
        return ""
    return clean_string(name).title()


def normalize_date(date_str: str | None) -> str | None:
    """
    Normalize a single date string to YYYY-MM when possible.

    Supports ISO ``YYYY-MM``, ``Mon YYYY``, and full month names.
    Returns ``None`` for blank/``Present``/unparseable sentinel values.

    Args:
        date_str: Raw date string.

    Returns:
        ``YYYY-MM`` string, ``None`` for open-ended/present, or trimmed original.
    """
    if date_str is None:
        return None

    trimmed = date_str.strip()
    if not trimmed:
        return None

    if trimmed.lower() in {"present", "current", "now"}:
        return None

    iso_match = _ISO_YEAR_MONTH.match(trimmed)
    if iso_match:
        year, month = iso_match.groups()
        return f"{year}-{int(month):02d}"

    month_year_match = _MONTH_NAME_YEAR.match(trimmed)
    if month_year_match:
        month_token, year = month_year_match.groups()
        month_num = _MONTH_TO_NUM.get(month_token.lower())
        if month_num:
            return f"{year}-{month_num}"

    return trimmed


def normalize_dates(date_str: str) -> str:
    """
    Normalize a date or date-range string.

    Range separators (`` - ``) split the string; each part is normalized
    individually and rejoined. ``Present`` is preserved as-is.

    Examples:
        ``Apr 2024 - Present`` → ``2024-04 - Present``
        ``Aug 2017 - May 2021`` → ``2017-08 - 2021-05``

    Args:
        date_str: Raw date or range string.

    Returns:
        Normalized date/range string.
    """
    if not date_str:
        return ""

    trimmed = date_str.strip()
    parts = _DATE_RANGE_SPLIT.split(trimmed, maxsplit=1)

    if len(parts) == 1:
        normalized = normalize_date(parts[0])
        return normalized if normalized is not None else parts[0].strip()

    start_raw, end_raw = parts[0].strip(), parts[1].strip()

    if end_raw.lower() in {"present", "current", "now"}:
        start_norm = normalize_date(start_raw)
        start_out = start_norm if start_norm is not None else start_raw
        return f"{start_out} - Present"

    start_norm = normalize_date(start_raw)
    end_norm = normalize_date(end_raw)
    start_out = start_norm if start_norm is not None else start_raw
    end_out = end_norm if end_norm is not None else end_raw
    return f"{start_out} - {end_out}"


def _parse_date_range(date_range: str) -> tuple[str | None, str | None]:
    """
    Split a date range into normalized start_date and end_date (YYYY-MM).

    ``end_date`` is ``None`` when the range ends with Present/current.
    """
    if not date_range:
        return None, None

    parts = _DATE_RANGE_SPLIT.split(date_range.strip(), maxsplit=1)
    start = normalize_date(parts[0].strip())

    if len(parts) == 1:
        return start, None

    end_raw = parts[1].strip()
    if end_raw.lower() in {"present", "current", "now"}:
        return start, None

    return start, normalize_date(end_raw)


def normalize_candidate(raw: dict[str, Any]) -> dict[str, Any]:
    """
    Apply all normalization rules to a parsed candidate record.

    Works for both ATS JSON and resume PDF parser output shapes.
    Returns a deep copy — the input dict is never mutated.

    Args:
        raw: Parsed candidate dict from the parser layer.

    Returns:
        New dict with normalized field values.
    """
    candidate = copy.deepcopy(raw)

    if "full_name" in candidate and isinstance(candidate["full_name"], str):
        candidate["full_name"] = normalize_name(candidate["full_name"])

    if "email" in candidate and isinstance(candidate["email"], str):
        candidate["email"] = normalize_email(candidate["email"])

    if "phone" in candidate and isinstance(candidate["phone"], str):
        candidate["phone"] = normalize_phone(candidate["phone"])

    if "location" in candidate and isinstance(candidate["location"], str):
        candidate["location"] = clean_string(candidate["location"])

    if "skills" in candidate and isinstance(candidate["skills"], list):
        candidate["skills"] = normalize_skills(candidate["skills"])

    if "experience" in candidate and isinstance(candidate["experience"], list):
        candidate["experience"] = [
            _normalize_experience_entry(entry) for entry in candidate["experience"]
        ]

    if "education" in candidate and isinstance(candidate["education"], list):
        candidate["education"] = [
            _normalize_education_entry(entry) for entry in candidate["education"]
        ]

    return candidate


def _normalize_experience_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Normalize dates inside a single experience entry."""
    normalized = copy.deepcopy(entry)

    # ATS shape: explicit start_date / end_date fields.
    if "start_date" in normalized:
        normalized["start_date"] = normalize_date(normalized.get("start_date"))
    if "end_date" in normalized:
        normalized["end_date"] = normalize_date(normalized.get("end_date"))

    # Resume shape: combined date_range string.
    if "date_range" in normalized and isinstance(normalized["date_range"], str):
        raw_range = normalized["date_range"]
        normalized["date_range"] = normalize_dates(raw_range)
        start, end = _parse_date_range(raw_range)
        normalized["start_date"] = start
        normalized["end_date"] = end

    return normalized


def _normalize_education_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Normalize dates inside a single education entry."""
    normalized = copy.deepcopy(entry)

    if "start_date" in normalized:
        normalized["start_date"] = normalize_date(normalized.get("start_date"))
    if "end_date" in normalized:
        normalized["end_date"] = normalize_date(normalized.get("end_date"))

    if "date_range" in normalized and isinstance(normalized["date_range"], str):
        raw_range = normalized["date_range"]
        normalized["date_range"] = normalize_dates(raw_range)
        start, end = _parse_date_range(raw_range)
        normalized["start_date"] = start
        normalized["end_date"] = end

    return normalized
