"""
Bulk batch runner for the Multi-Source Candidate Data Transformer.
Designed for high-throughput processing of large datasets (e.g. 100,000+ files)
using parallel CPU workers and O(N) Union-Find duplicate grouping.
"""

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.parser import read_ats_json, read_resume_pdf, ParserError
from src.normalizer import normalize_candidate
from src.merger import merge_candidates
from src.projector import load_output_config, project_candidates
from src.utils import write_json_file


def process_single_file(task: Tuple[str, str]) -> Tuple[str, str, Dict[str, Any] | None, str | None]:
    """
    Worker process target: Parses and normalizes a single document.
    
    Args:
        task: Tuple of (file_type, file_path).
        
    Returns:
        Tuple of (file_type, file_path, normalized_data, error_message).
    """
    file_type, file_path = task
    try:
        if file_type == "ats":
            raw_data = read_ats_json(file_path)
        else:
            raw_data = read_resume_pdf(file_path)
            
        normalized_data = normalize_candidate(raw_data)
        normalized_data["_raw"] = raw_data
        return file_type, file_path, normalized_data, None
    except ParserError as exc:
        return file_type, file_path, None, f"Parser Error: {exc}"
    except Exception as exc:
        return file_type, file_path, None, f"Unexpected Error: {exc}"


class UnionFind:
    """Disjoint-Set (Union-Find) structure for linear O(N) candidate grouping."""
    def __init__(self, size: int):
        self.parent = list(range(size))

    def find(self, i: int) -> int:
        path = []
        while self.parent[i] != i:
            path.append(i)
            i = self.parent[i]
        for node in path:
            self.parent[node] = i
        return i

    def union(self, i: int, j: int) -> bool:
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i != root_j:
            self.parent[root_i] = root_j
            return True
        return False


def run_bulk_pipeline(
    ats_dir: Path,
    resumes_dir: Path,
    config_path: Path,
    output_path: Path,
    max_workers: int | None
) -> None:
    """Run the batch processing and merging pipeline."""
    start_time = time.time()
    print("--------------------------------------------------")
    print("Multi-Source Candidate Data Transformer: Bulk Runner")
    print("--------------------------------------------------")
    
    # 1. Discover files
    tasks: List[Tuple[str, str]] = []
    if ats_dir.exists():
        for file in ats_dir.glob("**/*.json"):
            if file.name != "output_config.json" and "output" not in file.parts:
                tasks.append(("ats", str(file.resolve())))
                
    if resumes_dir.exists():
        for file in resumes_dir.glob("**/*.pdf"):
            tasks.append(("resume", str(file.resolve())))

    total_files = len(tasks)
    print(f"Discovered {total_files} candidate documents.")
    if total_files == 0:
        print("No files found to process. Exiting.")
        return

    # 2. Parallel Parsing & Normalization
    print(f"Parsing and normalizing files using {max_workers or 'all available'} CPU workers...")
    candidates: List[Dict[str, Any]] = []
    failed_files: List[Tuple[str, str]] = []

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_single_file, task): task for task in tasks}
        
        processed_count = 0
        for future in as_completed(futures):
            file_type, file_path, normalized_data, error_msg = future.result()
            processed_count += 1
            if normalized_data:
                candidates.append(normalized_data)
            else:
                failed_files.append((file_path, error_msg or "Unknown Error"))
                
            if processed_count % 100 == 0 or processed_count == total_files:
                print(f" Progress: {processed_count}/{total_files} files processed...", end="\r")
    print()

    # 3. Fast Grouping / Clustering
    print(f"Successfully parsed {len(candidates)} records. Grouping duplicates...")
    uf = UnionFind(len(candidates))
    
    # Build indexes for duplicate detection
    email_to_idx: Dict[str, int] = {}
    phone_to_idx: Dict[str, int] = {}
    name_to_idx: Dict[str, int] = {}

    for idx, c in enumerate(candidates):
        # Extract fields matching duplicate checking logic
        email = c.get("email", "").strip().lower() if c.get("email") else ""
        phone = c.get("phone", "").strip() if c.get("phone") else ""
        name = c.get("full_name", "").strip().lower() if c.get("full_name") else ""
        
        if email:
            if email in email_to_idx:
                uf.union(idx, email_to_idx[email])
            else:
                email_to_idx[email] = idx
                
        if phone:
            if phone in phone_to_idx:
                uf.union(idx, phone_to_idx[phone])
            else:
                phone_to_idx[phone] = idx
                
        if name:
            if name in name_to_idx:
                uf.union(idx, name_to_idx[name])
            else:
                name_to_idx[name] = idx

    # Cluster indices by root parent
    clusters = defaultdict(list)
    for idx in range(len(candidates)):
        root = uf.find(idx)
        clusters[root].append(candidates[idx])

    print(f"Grouped records into {len(clusters)} distinct candidate profiles.")

    # 4. Merge duplicate groups
    print("Merging duplicate source records...")
    merged_candidates: List[Dict[str, Any]] = []
    for root, group in clusters.items():
        # merge_candidates consolidates a group of duplicates using conflict resolution rules.
        merged_group = merge_candidates(group)
        if merged_group:
            merged_candidates.append(merged_group[0])

    # 5. Project final outputs
    print("Projecting candidate outputs...")
    if not config_path.exists():
        print(f"Error: Configuration file not found at '{config_path}'", file=sys.stderr)
        return
        
    config = load_output_config(config_path)
    projected_list = project_candidates(merged_candidates, config)

    # 6. Save results
    print(f"Saving final projected candidate dataset to '{output_path}'...")
    write_json_file(output_path, projected_list)

    # 7. Print metrics
    duration = time.time() - start_time
    print("--------------------------------------------------")
    print("Pipeline Execution Summary:")
    print("--------------------------------------------------")
    print(f"Total time elapsed:       {duration:.2f} seconds")
    print(f"Total files discovered:   {total_files}")
    print(f"Successfully processed:   {len(candidates)}")
    print(f"Unique merged candidates: {len(projected_list)}")
    print(f"Failed files count:       {len(failed_files)}")
    print("--------------------------------------------------")

    if failed_files:
        print("\nErrors encountered during batch run:")
        for path, error in failed_files[:10]:
            print(f" - {Path(path).name}: {error}")
        if len(failed_files) > 10:
            print(f" ... and {len(failed_files) - 10} more errors.")


def main() -> None:
    """CLI entry point for bulk candidate batch processing."""
    parser = argparse.ArgumentParser(
        description="High-Throughput Candidate Batch Process Pipeline."
    )
    parser.add_argument(
        "--ats-dir",
        type=str,
        default="inputs/",
        help="Directory containing ATS JSON files."
    )
    parser.add_argument(
        "--resumes-dir",
        type=str,
        default="inputs/",
        help="Directory containing Resume PDF files."
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config/output_config.json",
        help="Path to output configuration JSON."
    )
    parser.add_argument(
        "--output",
        type=str,
        default="output/bulk_candidates.json",
        help="Path to write the merged projected output JSON."
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of CPU worker processes (default: use all cores)."
    )

    args = parser.parse_args()

    run_bulk_pipeline(
        ats_dir=Path(args.ats_dir),
        resumes_dir=Path(args.resumes_dir),
        config_path=Path(args.config),
        output_path=Path(args.output),
        max_workers=args.workers
    )


if __name__ == "__main__":
    main()
