"""
Gradio web interface for the Multi-Source Candidate Data Transformer.
Provides file uploads for ATS JSON and Resume PDF, an optional GitHub username,
and runs the parsing, normalization, merging, and projection pipeline.
"""

import json
import tempfile
import sys
from pathlib import Path
from typing import Optional
import gradio as gr

from src.parser import read_ats_json, read_resume_pdf, read_github_profile, ParserError
from src.normalizer import normalize_candidate
from src.merger import merge_candidates
from src.projector import load_output_config, project_candidates

# Project default paths
PROJECT_ROOT = Path(__file__).resolve().parent

def get_default_config_path() -> Path:
    path_in_config = PROJECT_ROOT / "config" / "output_config.json"
    if path_in_config.exists():
        return path_in_config
    # Fallback to root directory
    path_in_root = PROJECT_ROOT / "output_config.json"
    if path_in_root.exists():
        return path_in_root
    return path_in_config  # returns default path if neither exists



def process_pipeline(
    ats_file,
    resume_file,
    github_username: Optional[str]
):
    """
    Run candidate transformation pipeline on uploaded files.
    """
    if ats_file is None:
        return "Error: Please upload an ATS JSON file.", None
    if resume_file is None:
        return "Error: Please upload a Resume PDF file.", None

    try:
        # 1. Parse
        raw_ats = read_ats_json(ats_file.name)
        raw_resume = read_resume_pdf(resume_file.name)

        # 2. Normalize
        normalized_ats = normalize_candidate(raw_ats)
        normalized_resume = normalize_candidate(raw_resume)

        normalized_ats["_raw"] = raw_ats
        normalized_resume["_raw"] = raw_resume

        candidates_to_merge = [normalized_ats, normalized_resume]

        # Optional GitHub profile integration
        if github_username and github_username.strip():
            raw_github = read_github_profile(github_username.strip())
            normalized_github = normalize_candidate(raw_github)
            normalized_github["_raw"] = raw_github
            candidates_to_merge.append(normalized_github)

        # 3. Merge
        merged_list = merge_candidates(candidates_to_merge)

        # 4. Project
        config_path = get_default_config_path()
        if not config_path.exists():
            return f"Error: Configuration file not found at '{config_path}'", None
            
        config = load_output_config(config_path)
        projected_list = project_candidates(merged_list, config)

        output_str = json.dumps(projected_list, indent=2, ensure_ascii=False)

        # Save to a temporary file for download
        temp_dir = tempfile.gettempdir()
        output_filepath = Path(temp_dir) / "projected_candidate.json"
        with open(output_filepath, "w", encoding="utf-8") as f:
            f.write(output_str)

        return output_str, str(output_filepath)

    except ParserError as exc:
        return f"Parser Error: {exc}", None
    except Exception as exc:
        return f"Unexpected Pipeline Error: {exc}", None


# Define CSS for professional design
custom_css = """
footer {visibility: hidden}
"""

# Build Gradio UI
with gr.Blocks(title="Candidate Data Transformer") as demo:
    gr.Markdown("# Multi-Source Candidate Data Transformer")
    gr.Markdown(
        "Upload candidate records from multiple sources (structured ATS JSON and "
        "unstructured Resume PDF), resolve duplicates, and project the unified candidate."
    )
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 1. Upload Source Files")
            ats_input = gr.File(label="ATS JSON Input", file_types=[".json"])
            resume_input = gr.File(label="Resume PDF Input", file_types=[".pdf"])
            github_input = gr.Textbox(
                label="Optional GitHub Profile or Username",
                placeholder="e.g., Divyasri-m18 or https://github.com/Divyasri-m18"
            )
            transform_btn = gr.Button("Transform Candidate", variant="primary")
            
        with gr.Column(scale=2):
            gr.Markdown("### 2. Pipeline Results")
            json_output = gr.Code(label="Projected Candidate JSON", language="json")
            download_output = gr.File(label="Download Projected JSON Output")
            
    transform_btn.click(
        fn=process_pipeline,
        inputs=[ats_input, resume_input, github_input],
        outputs=[json_output, download_output]
    )

if __name__ == "__main__":
    demo.launch(css=custom_css)
