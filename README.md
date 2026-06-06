# CodeTransform

A web-based code converter that translates source code between Python and JavaScript using a rule-driven engine, complete with language auto-detection and per-conversion confidence scoring.

![Python](https://img.shields.io/badge/python-3.x-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104-009688)

## Overview

CodeTransform converts code between programming languages without relying on an external LLM service. The backend exposes a small FastAPI service that detects a snippet's language and applies a deterministic set of conversion rules to produce the target output, returning a confidence score and any warnings raised during translation. A single-file HTML frontend provides the user interface — paste or upload code, pick a target language, and convert.

The engine is intentionally rule-based, which makes conversions fast, offline, and predictable. Confidence scoring and warnings communicate where a translation may need manual review.

## Key Features

- **Python <-> JavaScript conversion** via a rule-based conversion engine
- **Automatic language detection** with a confidence score, a reason, and alternative guesses
- **Confidence scoring and warnings** returned with every conversion so low-certainty output is flagged
- **Strict mode** flag on the convert request for stricter translation behavior
- **File upload** in the frontend with language inferred from the file extension
- **Copy to clipboard and download** of converted code from the browser
- **Self-contained frontend** served as a static file directly by the backend — no build step

## How It Works

```
frontend.html  ──HTTP──►  FastAPI (main.py)
                              ├── LanguageDetector  → /detect-language
                              └── ConversionEngine  → /convert
                                      ├── python_to_javascript.py
                                      ├── javascript_to_python.py
                                      └── method_converter.py
```

The FastAPI app initializes a `LanguageDetector` and a `ConversionEngine` at startup. The `/detect-language` endpoint runs pattern-based detection on the submitted code. The `/convert` endpoint dispatches to the appropriate language-pair converter, applies method/string-API mappings, and returns the converted code with metadata. The frontend is mounted as static files at the root path, so the same server serves both the API and the UI.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/` | Health check; also serves the frontend. Reports version and supported language pairs |
| `POST` | `/detect-language` | Detect the language of a code snippet (returns language, confidence, reason, alternatives) |
| `POST` | `/convert` | Convert code between a source and target language (returns converted code, confidence, warnings) |

## Tech Stack

- **Backend:** FastAPI, Pydantic, served with Uvicorn
- **Frontend:** Single static HTML file (vanilla JS)
- **Testing:** pytest, pytest-asyncio, httpx

## Getting Started

### Prerequisites

- Python 3.x
- pip

### Install and Run

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

The server starts on `http://127.0.0.1:8000`. Because the frontend is mounted at the root, opening that URL in a browser serves the UI directly. You can also open `frontend.html` on its own and point it at the running backend.

### Run Tests

```bash
cd backend
pytest
```

## Project Structure

```
code-convertor/
├── frontend.html                 # Single-page UI (upload, convert, copy, download)
└── backend/
    ├── main.py                   # FastAPI app and endpoints
    ├── requirements.txt
    ├── api/                      # Request/response models
    ├── core/                     # LanguageDetector, ConversionEngine
    ├── converters/
    │   ├── base_converter.py
    │   ├── python_to_javascript.py
    │   ├── javascript_to_python.py
    │   └── method_converter.py
    ├── utils/
    └── tests/
```

## License

Released under the MIT License. See the `LICENSE` reference in the project for details.
