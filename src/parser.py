"""
Source parsers for structured and unstructured candidate inputs.

Responsibilities:
  - Read ATS JSON (structured source) and map records to internal representations.
  - Extract text from resume PDFs (unstructured source) via pdfplumber.
  - Attach source metadata (source type, file path, raw payload reference).

Each parser returns parsed candidate fragments; normalization happens downstream.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pdfplumber

from .utils import clean_string, read_json_file

# ---------------------------------------------------------------------------
# Custom exceptions — callers can catch ParserError for any parser failure.
# ---------------------------------------------------------------------------


class ParserError(Exception):
    """Base exception for all parser-layer failures."""


class ParserFileNotFoundError(ParserError):
    """Raised when an input file does not exist."""


class ParserJsonError(ParserError):
    """Raised when JSON content is malformed or unreadable."""


class ParserStructureError(ParserError):
    """Raised when parsed content does not match the expected ATS shape."""


class PdfExtractionError(ParserError):
    """Raised when text cannot be extracted from a PDF."""


# ---------------------------------------------------------------------------
# Regex patterns for deterministic resume text parsing (no ML/OCR).
# ---------------------------------------------------------------------------

EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w.-]+\.\w+", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"\+?\d[\d\s\-()]{8,}\d")
GITHUB_PATTERN = re.compile(
    r"(?:https?://)?(?:www\.)?(github\.com/[\w\-]+)",
    re.IGNORECASE,
)
LOCATION_PATTERN = re.compile(
    r"^[A-Za-z\s]+,\s*[A-Za-z\s]+,\s*[A-Za-z\s]+$",
)
JOB_HEADER_PATTERN = re.compile(
    r"^(?P<company>.+?)\s*\|\s*(?P<location>.+?)\s*\|\s*(?P<date_range>.+)$",
)
EDUCATION_DATE_PATTERN = re.compile(
    r"^(?P<institution>.+?)\s*\|\s*(?P<date_range>.+)$",
)

SECTION_HEADERS = ("PROFESSIONAL SUMMARY", "EXPERIENCE", "EDUCATION", "SKILLS")


# ---------------------------------------------------------------------------
# ATS JSON parser
# ---------------------------------------------------------------------------


def read_ats_json(path: str | Path) -> dict[str, Any]:
    """
    Load and parse candidate data from an ATS JSON export file.

    Reads the file safely, validates basic structure, and returns the first
    candidate record enriched with source metadata. Values are returned as-is
    (no normalization).

    Args:
        path: Filesystem path to the ATS JSON file.

    Returns:
        Dictionary containing candidate fields plus a ``_source`` metadata block.

    Raises:
        ParserFileNotFoundError: If the file does not exist.
        ParserJsonError: If the file contains invalid JSON.
        ParserStructureError: If the JSON lacks a usable ``candidates`` array.
    """
    file_path = Path(path)

    if not file_path.is_file():
        raise ParserFileNotFoundError(f"ATS JSON file not found: {file_path}")

    try:
        data = read_json_file(file_path)
    except json.JSONDecodeError as exc:
        raise ParserJsonError(
            f"Malformed JSON in {file_path}: {exc.msg} (line {exc.lineno}, col {exc.colno})"
        ) from exc
    except OSError as exc:
        raise ParserError(f"Unable to read ATS JSON file {file_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ParserStructureError(
            f"Expected top-level JSON object in {file_path}, got {type(data).__name__}"
        )

    candidates = data.get("candidates")
    if not isinstance(candidates, list) or len(candidates) == 0:
        raise ParserStructureError(
            f"Expected non-empty 'candidates' array in {file_path}"
        )

    first_candidate = candidates[0]
    if not isinstance(first_candidate, dict):
        raise ParserStructureError(
            f"Expected candidate entry to be an object in {file_path}"
        )

    # Return a shallow copy so callers cannot mutate the original parsed tree.
    result = dict(first_candidate)
    result["_source"] = {
        "type": "ats_json",
        "path": str(file_path.resolve()),
        "export_source": data.get("source"),
        "exported_at": data.get("exported_at"),
    }
    return result


# ---------------------------------------------------------------------------
# Resume PDF parser
# ---------------------------------------------------------------------------


def read_resume_pdf(path: str | Path) -> dict[str, Any]:
    """
    Extract candidate fields from a resume PDF using pdfplumber.

    Args:
        path: Filesystem path to the resume PDF.

    Returns:
        Dictionary of extracted candidate fields plus a ``_source`` metadata block.

    Raises:
        ParserFileNotFoundError: If the PDF file does not exist.
        PdfExtractionError: If no text could be extracted from the PDF.
        ParserError: If the PDF cannot be opened or read.
    """
    file_path = Path(path)

    if not file_path.is_file():
        raise ParserFileNotFoundError(f"Resume PDF file not found: {file_path}")

    try:
        with pdfplumber.open(file_path) as pdf:
            page_texts = [page.extract_text() or "" for page in pdf.pages]
    except OSError as exc:
        raise ParserError(f"Unable to open PDF {file_path}: {exc}") from exc
    except Exception as exc:
        raise ParserError(f"Failed to read PDF {file_path}: {exc}") from exc

    full_text = "\n".join(text for text in page_texts if text.strip())
    if not full_text.strip():
        raise PdfExtractionError(f"No extractable text found in PDF: {file_path}")

    result = parse_resume_text(full_text)
    result["_source"] = {
        "type": "resume_pdf",
        "path": str(file_path.resolve()),
    }
    return result


def parse_resume_text(text: str) -> dict[str, Any]:
    """
    Parse structured candidate fields from raw resume text.

    Uses section headers and regex patterns only — deterministic, no AI/OCR.

    Args:
        text: Full plain-text content extracted from a resume PDF.

    Returns:
        Dictionary with keys: full_name, email, phone, location, skills,
        experience, education, github_url.
    """
    normalized_text = text.replace("\r\n", "\n").strip()
    sections = _split_sections(normalized_text)
    header_lines = _parse_header(normalized_text)

    return {
        "full_name": header_lines.get("full_name", ""),
        "email": _extract_email(header_lines.get("contact_line", normalized_text)),
        "phone": _extract_phone(header_lines.get("contact_line", normalized_text)),
        "location": header_lines.get("location", ""),
        "github_url": _extract_github(header_lines.get("contact_line", normalized_text)),
        "skills": _parse_skills(sections.get("SKILLS", "")),
        "experience": _parse_experience(sections.get("EXPERIENCE", "")),
        "education": _parse_education(sections.get("EDUCATION", "")),
    }


def _split_sections(text: str) -> dict[str, str]:
    """
    Split resume text into named sections using known header labels.

    Everything before the first known header is treated as the header block.
    """
    # Build a regex that finds any section header at the start of a line.
    header_alt = "|".join(re.escape(name) for name in SECTION_HEADERS)
    pattern = re.compile(rf"^({header_alt})", re.MULTILINE)

    matches = list(pattern.finditer(text))
    sections: dict[str, str] = {}

    for index, match in enumerate(matches):
        section_name = match.group(1)
        content_start = match.end()
        content_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[section_name] = text[content_start:content_end].strip()

    return sections


def _parse_header(text: str) -> dict[str, str]:
    """
    Parse the top-of-resume header (name, title, location, contact line).

    Assumes layout:
      Line 1: full name
      Line 2: job title (ignored here)
      Line 3: location (City, State, Country)
      Line 4: email | phone | github
    """
    # Header ends at the first section marker.
    header_end = len(text)
    for header in SECTION_HEADERS:
        marker = text.find(header)
        if marker != -1:
            header_end = min(header_end, marker)

    header_block = text[:header_end].strip()
    lines = [line.strip() for line in header_block.split("\n") if line.strip()]

    result: dict[str, str] = {}
    if not lines:
        return result

    result["full_name"] = lines[0]

    # Location is typically the first line matching "City, State, Country".
    for line in lines[1:]:
        if LOCATION_PATTERN.match(line):
            result["location"] = line
            break

    # Contact line contains pipe-separated email, phone, and optional GitHub.
    for line in lines[1:]:
        if "|" in line and ("@" in line or "github.com" in line.lower()):
            result["contact_line"] = line
            break

    return result


def _extract_email(text: str) -> str:
    """Return the first email address found in *text*, or empty string."""
    match = EMAIL_PATTERN.search(text)
    return match.group(0) if match else ""


def _extract_phone(text: str) -> str:
    """Return the first phone-like token found in *text*, or empty string."""
    match = PHONE_PATTERN.search(text)
    return clean_string(match.group(0)) if match else ""


def _extract_github(text: str) -> str:
    """Return the first GitHub URL/path found in *text*, or empty string."""
    match = GITHUB_PATTERN.search(text)
    return match.group(1) if match else ""


def _parse_skills(section_text: str) -> list[str]:
    """
    Parse the SKILLS section into a list of raw skill strings.

    Expects comma-separated skills on one or more lines.
    """
    if not section_text.strip():
        return []

    # Flatten newlines so wrapped skill lines still split correctly.
    flat = " ".join(line.strip() for line in section_text.split("\n") if line.strip())
    return [skill.strip() for skill in flat.split(",") if skill.strip()]


def _parse_experience(section_text: str) -> list[dict[str, Any]]:
    """
    Parse the EXPERIENCE section into a list of job dicts.

    Each job block follows the pattern:
      Title line
      Company | Location | Date range
      - bullet points...
    """
    if not section_text.strip():
        return []

    jobs: list[dict[str, Any]] = []
    lines = section_text.split("\n")

    index = 0
    while index < len(lines):
        line = lines[index].strip()

        # Skip blank lines between job blocks.
        if not line:
            index += 1
            continue

        # A job title line is immediately followed by a pipe-delimited header.
        if index + 1 < len(lines) and "|" in lines[index + 1]:
            title = line
            header_match = JOB_HEADER_PATTERN.match(lines[index + 1].strip())
            index += 2

            if header_match:
                bullets: list[str] = []
                while index < len(lines):
                    bullet_line = lines[index].strip()
                    if not bullet_line:
                        index += 1
                        break
                    if bullet_line.startswith("- "):
                        bullets.append(bullet_line[2:].strip())
                        index += 1
                        continue
                    # Next job title (no leading dash) ends the bullet list.
                    if "|" not in bullet_line and not bullet_line.startswith("-"):
                        break
                    index += 1

                jobs.append(
                    {
                        "title": title,
                        "company": header_match.group("company").strip(),
                        "location": header_match.group("location").strip(),
                        "date_range": header_match.group("date_range").strip(),
                        "description": "\n".join(f"- {b}" for b in bullets),
                    }
                )
                continue

        index += 1

    return jobs


def _parse_education(section_text: str) -> list[dict[str, Any]]:
    """
    Parse the EDUCATION section into a list of education entry dicts.

    Expected layout:
      Degree line
      Institution | Date range
      Optional detail line(s) e.g. CGPA
    """
    if not section_text.strip():
        return []

    lines = [line.strip() for line in section_text.split("\n") if line.strip()]
    entries: list[dict[str, Any]] = []

    index = 0
    while index < len(lines):
        degree_line = lines[index]
        index += 1

        institution = ""
        date_range = ""
        details: list[str] = []

        if index < len(lines):
            date_match = EDUCATION_DATE_PATTERN.match(lines[index])
            if date_match:
                institution = date_match.group("institution").strip()
                date_range = date_match.group("date_range").strip()
                index += 1

        # Collect remaining non-blank lines until the next degree-like entry.
        while index < len(lines):
            candidate = lines[index]
            if EDUCATION_DATE_PATTERN.match(candidate):
                break
            if candidate.startswith("B.") or candidate.startswith("M."):
                break
            details.append(candidate)
            index += 1

        entries.append(
            {
                "degree": degree_line,
                "institution": institution,
                "date_range": date_range,
                "details": "\n".join(details),
            }
        )

    return entries
