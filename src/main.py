"""
CLI entry point for the Multi-Source Candidate Data Transformer.

Responsibilities:
  - Parse command-line arguments (input paths, config path, output path).
  - Orchestrate the pipeline: parse -> normalize -> merge -> project -> write output.
  - Handle top-level errors and exit codes.

Business logic is delegated to parser, normalizer, merger, and projector modules.
"""

import argparse
from dataclasses import asdict
import json
import sys
from pathlib import Path
from typing import Any

from .normalizer import normalize_candidate
from .parser import read_ats_json, read_resume_pdf, ParserError
from .merger import merge_candidates
from .projector import load_output_config, project_candidates
from .utils import write_json_file

# Project root is one level above src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ATS_PATH = PROJECT_ROOT / "inputs" / "ats.json"
DEFAULT_RESUME_PATH = PROJECT_ROOT / "inputs" / "resume.pdf"
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "output_config.json"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "output" / "final_candidate.json"


def _print_section(title: str, data: Any) -> None:
    """Print a labeled JSON block."""
    print("========================")
    print(title)
    print("========================")
    print()
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print()


def main() -> int:
    """
    Step 7 entry point: Parse CLI arguments and run the candidate transformation pipeline.

    Returns:
        Process exit code (0 = success, non-zero = failure).
    """
    parser = argparse.ArgumentParser(
        description="Multi-Source Candidate Data Transformer CLI."
    )
    parser.add_argument(
        "--ats",
        type=str,
        default=str(DEFAULT_ATS_PATH),
        help="Path to ATS JSON input file."
    )
    parser.add_argument(
        "--resume",
        type=str,
        default=str(DEFAULT_RESUME_PATH),
        help="Path to Resume PDF input file."
    )
    parser.add_argument(
        "--config",
        type=str,
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to output projection configuration JSON file."
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(DEFAULT_OUTPUT_PATH),
        help="Path to save the projected output JSON file."
    )

    args = parser.parse_args()

    try:
        # 1. Parse
        raw_ats = read_ats_json(args.ats)
        raw_resume = read_resume_pdf(args.resume)

        # 2. Normalize
        normalized_ats = normalize_candidate(raw_ats)
        normalized_resume = normalize_candidate(raw_resume)

        # Attach raw dictionaries for provenance retrieval
        normalized_ats["_raw"] = raw_ats
        normalized_resume["_raw"] = raw_resume

        # 3. Merge
        merged_list = merge_candidates([normalized_ats, normalized_resume])

        # 4. Project
        try:
            config = load_output_config(args.config)
        except FileNotFoundError:
            print(f"Error: Configuration file not found at '{args.config}'", file=sys.stderr)
            return 1
        except json.JSONDecodeError as exc:
            print(f"Error: Configuration file at '{args.config}' contains invalid JSON: {exc}", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"Error: Unable to load configuration file: {exc}", file=sys.stderr)
            return 1

        projected_list = project_candidates(merged_list, config)

        # 5. Print Final Output JSON
        _print_section("FINAL OUTPUT JSON", projected_list)

        # 6. Save to disk if output path is specified
        if args.output:
            try:
                write_json_file(args.output, projected_list)
                print(f"Successfully saved projected candidates to '{args.output}'")
            except Exception as exc:
                print(f"Error: Failed to write output file to '{args.output}': {exc}", file=sys.stderr)
                return 1

        return 0

    except ParserError as exc:
        print(f"Parser Error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Unexpected Pipeline Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())



