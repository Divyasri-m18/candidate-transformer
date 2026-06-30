# Multi-Source Candidate Data Transformer

A Python-based data transformation pipeline built as part of the Eightfold AI Internship Assignment.

The project consolidates candidate information from multiple heterogeneous sources, normalizes inconsistent data, resolves conflicts deterministically, tracks provenance and confidence, and produces a configurable canonical JSON profile.

---

## Features

- Parse structured ATS JSON records
- Extract candidate details from Resume PDF
- Normalize emails, phone numbers, dates, names, and skills
- Detect duplicate candidate profiles
- Deterministic conflict resolution
- Confidence scoring
- Provenance tracking
- Configurable output projection
- Command Line Interface (CLI)

---

## Project Structure

```
candidate-transformer/
│
├── inputs/
│   ├── ats.json
│   └── resume.pdf
│
├── output/
│
├── config/
│   └── output_config.json
│
├── src/
│   ├── parser.py
│   ├── normalizer.py
│   ├── merger.py
│   ├── confidence.py
│   ├── projector.py
│   ├── schema.py
│   └── main.py
│
├── tests/
│
├── requirements.txt
└── README.md
```

---

## Installation

```bash
python -m venv .venv
```

Windows

```bash
.venv\Scripts\activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

## Usage

Run with default inputs

```bash
python -m src.main
```

Run with custom inputs

```bash
python -m src.main \
  --ats inputs/ats.json \
  --resume inputs/resume.pdf \
  --config config/output_config.json \
  --output output/final_candidate.json
```

Show CLI help

```bash
python -m src.main --help
```

---

## Pipeline

```
ATS JSON
          \
           \
            Parse
              │
              ▼
         Normalize
              │
              ▼
 Merge & Conflict Resolution
              │
              ▼
 Confidence & Provenance
              │
              ▼
 Projection Layer
              │
              ▼
 Canonical JSON Output
```

---

## Technologies Used

- Python 3.11+
- pdfplumber
- argparse
- JSON
- Regular Expressions

---

## Output

The transformer produces a configurable canonical candidate profile in JSON format.

Features include:

- Configurable field projection
- Field renaming
- Confidence metadata
- Provenance metadata
- Deterministic output

---

## Assignment Coverage

- ✅ Structured source (ATS JSON)
- ✅ Unstructured source (Resume PDF)
- ✅ Parsing
- ✅ Normalization
- ✅ Duplicate detection
- ✅ Conflict resolution
- ✅ Confidence scoring
- ✅ Provenance tracking
- ✅ Configurable output
- ✅ Command Line Interface

---

## Future Improvements

- GitHub API integration
- LinkedIn integration
- Additional ATS connectors
- Batch processing
- REST API service

---
---

## Screenshot

### Final Output

The following screenshot shows the successful execution of the candidate transformation pipeline and the generated canonical JSON output.

![Final Output](images/Final Output JSON.png)
