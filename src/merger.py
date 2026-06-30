from __future__ import annotations

from typing import Any

from .confidence import PRIORITY_MAP, score_field
from .schema import Provenance


def are_duplicates(c1: dict[str, Any], c2: dict[str, Any]) -> bool:
    """
    Check if two candidate records represent the same candidate.
    Matches are checked in priority order: Email, Phone, and normalized Full Name as fallback.
    """
    # 1. Email check
    email1 = c1.get("email", "").strip().lower() if c1.get("email") else ""
    email2 = c2.get("email", "").strip().lower() if c2.get("email") else ""
    if email1 and email2:
        return email1 == email2

    # 2. Phone check
    phone1 = c1.get("phone", "").strip() if c1.get("phone") else ""
    phone2 = c2.get("phone", "").strip() if c2.get("phone") else ""
    if phone1 and phone2:
        return phone1 == phone2

    # 3. Full name check (fallback)
    name1 = c1.get("full_name", "").strip().lower() if c1.get("full_name") else ""
    name2 = c2.get("full_name", "").strip().lower() if c2.get("full_name") else ""
    if name1 and name2:
        return name1 == name2

    return False


def is_exp_dup(e1: dict[str, Any], e2: dict[str, Any]) -> bool:
    """Check if two experience entries match exactly by normalized company and title."""
    c1 = e1.get("company", "").strip().lower()
    t1 = e1.get("title", "").strip().lower()
    c2 = e2.get("company", "").strip().lower()
    t2 = e2.get("title", "").strip().lower()
    return c1 == c2 and t1 == t2


def is_edu_dup(e1: dict[str, Any], e2: dict[str, Any]) -> bool:
    """Check if two education entries match exactly by normalized institution and degree."""
    inst1 = e1.get("institution", "").strip().lower()
    deg1 = e1.get("degree", "").strip().lower()
    inst2 = e2.get("institution", "").strip().lower()
    deg2 = e2.get("degree", "").strip().lower()
    return inst1 == inst2 and deg1 == deg2


def merge_dict_entries(e1: dict[str, Any], source1: str, e2: dict[str, Any], source2: str) -> dict[str, Any]:
    """Merge two sub-dictionaries key-by-key using source priority conflict resolution."""
    p1 = PRIORITY_MAP.get(source1, 0)
    p2 = PRIORITY_MAP.get(source2, 0)
    all_keys = set(e1.keys()) | set(e2.keys())
    merged_entry = {}
    for key in all_keys:
        if key == "_source_type":
            continue
        v1 = e1.get(key)
        v2 = e2.get(key)
        is_missing1 = v1 is None or v1 == "" or v1 == [] or v1 == {}
        is_missing2 = v2 is None or v2 == "" or v2 == [] or v2 == {}
        
        if is_missing1 and is_missing2:
            merged_entry[key] = None
        elif is_missing1:
            merged_entry[key] = v2
        elif is_missing2:
            merged_entry[key] = v1
        else:
            if p2 > p1:
                merged_entry[key] = v2
            else:
                merged_entry[key] = v1
    return merged_entry


def merge_list_entries(
    field_name: str,
    sorted_candidates: list[dict[str, Any]],
    is_dup_fn: Any,
) -> list[dict[str, Any]]:
    """Merge a list of sub-dictionaries (e.g. experience/education) across candidates."""
    merged_list: list[dict[str, Any]] = []
    for candidate in sorted_candidates:
        c_source = candidate.get("_source", {}).get("type", "")
        for entry in candidate.get(field_name, []):
            match_idx = -1
            for idx, m_entry in enumerate(merged_list):
                if is_dup_fn(entry, m_entry):
                    match_idx = idx
                    break
            if match_idx != -1:
                existing_entry = merged_list[match_idx]
                existing_source = existing_entry.get("_source_type", "")
                merged_entry = merge_dict_entries(existing_entry, existing_source, entry, c_source)
                merged_entry["_source_type"] = existing_source if PRIORITY_MAP.get(existing_source, 0) >= PRIORITY_MAP.get(c_source, 0) else c_source
                merged_list[match_idx] = merged_entry
            else:
                new_entry = dict(entry)
                new_entry["_source_type"] = c_source
                merged_list.append(new_entry)
    
    for entry in merged_list:
        entry.pop("_source_type", None)
    return merged_list


def merge_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Group duplicates and merge each group into a single canonical candidate.

    Args:
        candidates: Normalized candidate records from all sources.

    Returns:
        Deduplicated list of merged candidate records.
    """
    if not candidates:
        return []

    # Group duplicates into match clusters
    groups: list[list[dict[str, Any]]] = []
    for candidate in candidates:
        matched_group = None
        for group in groups:
            if any(are_duplicates(candidate, other) for other in group):
                matched_group = group
                break
        if matched_group is not None:
            matched_group.append(candidate)
        else:
            groups.append([candidate])

    merged_candidates: list[dict[str, Any]] = []

    for group in groups:
        # Sort candidates in group by source priority descending
        sorted_candidates = sorted(
            group,
            key=lambda c: PRIORITY_MAP.get(c.get("_source", {}).get("type", ""), 0),
            reverse=True
        )

        merged: dict[str, Any] = {
            "candidate_id": "",
            "full_name": "",
            "email": "",
            "phone": "",
            "location": None,
            "skills": [],
            "experience": [],
            "education": [],
            "github_url": "",
            "provenance": {},
            "confidence": {},
        }

        # 1. Merge scalar/object fields
        scalar_fields = ["candidate_id", "full_name", "email", "phone", "location", "github_url"]
        for field in scalar_fields:
            field_values = []
            for candidate in group:
                val = candidate.get(field)
                meta = candidate.get("_source", {})
                field_values.append((val, meta))

            winning_val, winning_meta = resolve_field_conflict(field, field_values)
            merged[field] = winning_val

            # Resolve confidence and provenance for this field
            source_type = winning_meta.get("type", "")
            source_path = winning_meta.get("path", "")
            
            # Find the raw value from the winning candidate
            raw_value = None
            if source_path:
                for candidate in group:
                    if candidate.get("_source", {}).get("path") == source_path:
                        raw_value = candidate.get("_raw", {}).get(field)
                        break

            merged["confidence"][field] = score_field(field, winning_val, source_type)
            if source_type:
                merged["provenance"][field] = Provenance(
                    source=source_type,
                    source_path=source_path,
                    raw_value=raw_value if raw_value is not None else winning_val
                )
            else:
                merged["provenance"][field] = Provenance()

        # 2. Merge Skills (ordered union)
        merged_skills: list[str] = []
        seen_skills: set[str] = set()
        for candidate in sorted_candidates:
            for skill in candidate.get("skills", []):
                if skill not in seen_skills:
                    merged_skills.append(skill)
                    seen_skills.add(skill)
        merged["skills"] = merged_skills

        # Provenance/Confidence for skills
        if sorted_candidates:
            top_meta = sorted_candidates[0].get("_source", {})
            top_raw_skills = sorted_candidates[0].get("_raw", {}).get("skills")
            merged["confidence"]["skills"] = score_field("skills", merged_skills, top_meta.get("type", ""))
            merged["provenance"]["skills"] = Provenance(
                source=top_meta.get("type", ""),
                source_path=top_meta.get("path", ""),
                raw_value=top_raw_skills if top_raw_skills is not None else merged_skills
            )

        # 3. Merge Experience
        merged_exp = merge_list_entries("experience", sorted_candidates, is_exp_dup)
        merged["experience"] = merged_exp

        if sorted_candidates:
            top_meta = sorted_candidates[0].get("_source", {})
            top_raw_exp = sorted_candidates[0].get("_raw", {}).get("experience")
            merged["confidence"]["experience"] = score_field("experience", merged_exp, top_meta.get("type", ""))
            merged["provenance"]["experience"] = Provenance(
                source=top_meta.get("type", ""),
                source_path=top_meta.get("path", ""),
                raw_value=top_raw_exp if top_raw_exp is not None else merged_exp
            )

        # 4. Merge Education
        merged_edu = merge_list_entries("education", sorted_candidates, is_edu_dup)
        merged["education"] = merged_edu

        if sorted_candidates:
            top_meta = sorted_candidates[0].get("_source", {})
            top_raw_edu = sorted_candidates[0].get("_raw", {}).get("education")
            merged["confidence"]["education"] = score_field("education", merged_edu, top_meta.get("type", ""))
            merged["provenance"]["education"] = Provenance(
                source=top_meta.get("type", ""),
                source_path=top_meta.get("path", ""),
                raw_value=top_raw_edu if top_raw_edu is not None else merged_edu
            )

        merged_candidates.append(merged)

    return merged_candidates


def resolve_field_conflict(
    field_name: str,
    values: list[tuple[Any, dict[str, Any]]],
) -> tuple[Any, dict[str, Any]]:
    """
    Pick a winning value for a field when sources disagree.

    Args:
        field_name: Name of the conflicting field.
        values: List of (value, metadata) pairs from each source.

    Returns:
        Tuple of (chosen_value, provenance_metadata).
    """
    # Filter out missing values
    valid_values = []
    for val, meta in values:
        is_missing = val is None or val == "" or val == [] or val == {}
        if not is_missing:
            valid_values.append((val, meta))

    if not valid_values:
        if values:
            return values[0][0], values[0][1]
        return None, {}

    winning_val, winning_meta = max(
        valid_values,
        key=lambda x: PRIORITY_MAP.get(x[1].get("type", ""), 0)
    )

    return winning_val, winning_meta


