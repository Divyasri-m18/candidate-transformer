# Multi-Source Candidate Data Transformer

An Eightfold AI internship assignment that reads candidate data from multiple sources (structured ATS JSON and unstructured resume PDF), normalizes and merges records, and produces a canonical candidate JSON output.

## Project Structure

```
candidate-transformer/
├── inputs/          # Sample input files (ATS JSON, resume PDF)
├── output/          # Generated canonical candidate JSON
├── config/          # Output projection configuration
├── src/             # Application source code
├── tests/           # Unit and integration tests
├── requirements.txt
└── README.md
```

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

## Usage

Run the transformer pipeline:

```bash
python -m src.main [arguments]
```

### CLI Arguments

- `--ats PATH`: Path to ATS JSON input file (default: `inputs/ats.json`).
- `--resume PATH`: Path to Resume PDF input file (default: `inputs/resume.pdf`).
- `--config PATH`: Path to projection configuration JSON file (default: `config/output_config.json`).
- `--output PATH`: Path to save the final projected JSON file (default: `output/final_candidate.json`).

To view the help menu:

```bash
python -m src.main --help
```

## Status

- [x] Step 1: Project structure and placeholder modules
- [x] Step 2: Parser Component
- [x] Step 3: Normalization Component
- [x] Step 4: CLI Orchestration (Step 4 check)
- [x] Step 5: Merge Layer & Confidence Scoring
- [x] Step 6: Output Projection Layer
- [x] Step 7: Command Line Interface (CLI)

