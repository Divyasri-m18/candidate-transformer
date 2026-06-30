# Multi-Source Candidate Data Transformer

A Python-based candidate data transformation pipeline developed for the **Eightfold Engineering Internship Assignment**.

This project ingests candidate information from multiple heterogeneous sources, normalizes inconsistent data, detects duplicate candidate records, resolves conflicts deterministically, tracks provenance and confidence, and generates a canonical candidate profile in JSON format.

---

# 🌐 Live Demo

### 🚀 Direct Application

https://divyasri-18-candidate-transformer.hf.space/

### 🤗 Hugging Face Space

https://huggingface.co/spaces/Divyasri-18/candidate-transformer

---

# 📂 GitHub Repository

https://github.com/Divyasri-m18/candidate-transformer

---

# Features

- Structured ATS JSON parsing
- Resume PDF parsing
- GitHub Public REST API integration
- Deterministic rule-based parsing
- Candidate data normalization
- Duplicate candidate detection
- Conflict resolution
- Confidence scoring
- Provenance tracking
- Configurable output projection
- Command Line Interface (CLI)
- Gradio Web Interface
- Live deployment using Hugging Face Spaces

---

# Project Structure

```
candidate-transformer/
│
├── config/
│   └── output_config.json
│
├── images/
│   └── final-output.png
│
├── inputs/
│   ├── ats.json
│   └── resume.pdf
│
├── output/
│   └── final_candidate.json
│
├── src/
│   ├── parser.py
│   ├── normalizer.py
│   ├── merger.py
│   ├── confidence.py
│   ├── projector.py
│   ├── schema.py
│   ├── utils.py
│   └── main.py
│
├── tests/
│
├── app.py
├── requirements.txt
├── README.md
└── .gitignore
```

---

# Architecture

```
                ATS JSON
                    │
                    │
             Resume PDF
                    │
                    │
          GitHub REST API
                    │
                    ▼
               Parser Layer
                    ▼
          Normalization Layer
                    ▼
        Duplicate Detection
                    ▼
       Conflict Resolution
                    ▼
         Confidence Scoring
                    ▼
        Provenance Tracking
                    ▼
         Projection Layer
                    ▼
      Canonical Candidate JSON
```

---

# Data Sources

## Structured Source

- ATS JSON

## Unstructured Sources

- Resume PDF
- GitHub Public REST API

---

# Technologies Used

- Python 3
- Gradio
- pdfplumber
- Requests
- JSON
- argparse
- pathlib
- dataclasses
- Regular Expressions (re)

---

# Installation

Clone the repository

```bash
git clone https://github.com/Divyasri-m18/candidate-transformer.git
```

Move into the project

```bash
cd candidate-transformer
```

Create virtual environment

```bash
python -m venv .venv
```

Activate virtual environment

Windows

```bash
.venv\Scripts\activate
```

Linux / macOS

```bash
source .venv/bin/activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

---

# Running the CLI

Run the complete transformation pipeline

```bash
python -m src.main
```

Display CLI help

```bash
python -m src.main --help
```

Run using GitHub profile

```bash
python -m src.main --github Divyasri-m18
```

---

# Running the Web UI

Launch the Gradio application

```bash
python app.py
```

Open your browser and visit

```
http://127.0.0.1:7860
```

or use the deployed application

https://divyasri-18-candidate-transformer.hf.space/

---

# Pipeline Overview

### 1. Parsing

The parser extracts candidate information from:

- ATS JSON
- Resume PDF
- GitHub Public API

No AI models or OCR are used.

Only deterministic parsing using:

- Regular Expressions
- String Processing
- JSON Parsing

---

### 2. Normalization

The normalization layer standardizes candidate information before merging.

Implemented normalizations include:

- Email normalization
- Phone number conversion to E.164 format
- Name normalization
- Date normalization (YYYY-MM)
- Skill canonicalization

Example

| Raw Value | Normalized |
|------------|------------|
| DIVYASRI.M018@gmail.com | divyasri.m018@gmail.com |
| 99447 23017 | +919944723017 |
| CPP | C++ |
| JS | JavaScript |
| py | Python |

---

# Duplicate Detection

Candidate records are matched using deterministic priority:

1. Email Address
2. Phone Number
3. Normalized Full Name (Fallback)

This allows the pipeline to identify duplicate records across multiple sources while preserving unique candidates.

---

# Conflict Resolution

When multiple sources contain different values, the pipeline resolves conflicts deterministically.

Priority Order

```
Resume PDF
      ↓
ATS JSON
      ↓
GitHub API
```

The selected value is stored while preserving provenance and confidence information.

---

# Confidence Scoring

Confidence scores indicate the reliability of each selected field.

| Source | Confidence |
|---------|-----------:|
| ATS JSON | 0.95 |
| Resume PDF | 0.85 |
| GitHub API | 0.75 |

---

# Provenance Tracking

Every selected field stores its origin.

Example

```json
{
  "email": {
    "source": "resume_pdf",
    "source_path": "inputs/resume.pdf",
    "raw_value": "DIVYASRI.M018@gmail.com"
  }
}
```

---

# Configurable Output Projection

The output schema is configurable using:

```
config/output_config.json
```

Supported features

- Select output fields
- Rename fields
- Include or exclude confidence
- Include or exclude provenance
- Missing value strategies

---

# Example Output

The pipeline generates a canonical candidate profile.

```
output/final_candidate.json
```

---

# Screenshots

## Final Output

The screenshot below shows the successful execution of the candidate transformation pipeline.

![Final Output](images/final-output.png)

---

# Future Improvements

- LinkedIn API Integration
- Additional ATS Connectors
- Batch Candidate Processing
- REST API Service
- Docker Support
- Database Integration

---

# Assignment Requirements Covered

- Structured Source
- Unstructured Source
- Multi-source Parsing
- Rule-based Parsing
- Data Normalization
- Duplicate Detection
- Conflict Resolution
- Confidence Scoring
- Provenance Tracking
- Configurable Projection
- Command Line Interface
- Minimal Web UI
- Live Deployment

---

# Author

**Divyasri M**

GitHub

https://github.com/Divyasri-m18

Hugging Face

https://huggingface.co/spaces/Divyasri-18/candidate-transformer

---

# License

This project was developed as part of the **Eightfold Engineering Internship Assignment** for educational and evaluation purposes.
