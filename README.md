# CodeTransform - Universal Code Converter

A powerful web-based code converter that transforms code between programming languages with high accuracy and confidence scoring.

## Features

- **Bidirectional Conversion**: Python <-> JavaScript with 122+ tested conversion rules
- **File Upload**: Drag & drop or click to upload code files - auto-detects language from file extension
- **Smart Detection**: Auto-detects source language from code patterns
- **Download Converted Code**: One-click download with correct file extension (.py, .js, .java)
- **Copy to Clipboard**: Instantly copy converted code
- **Confidence Scoring**: Color-coded accuracy indicator (green/yellow/red)
- **Conversion History**: Track your recent conversions (stored locally)
- **Swap Languages**: Quick button to reverse conversion direction

## Supported Conversions

| From | To | Status |
|------|-----|--------|
| Python | JavaScript | Full Support |
| JavaScript | Python | Full Support |

### What Gets Converted

- Print statements & console logs
- Variable declarations
- If/elif/else statements
- For/while loops
- Functions & arrow functions
- String methods (len, append, join, split, etc.)
- Boolean values & operators
- Comments & docstrings
- F-strings & template literals
- Try/catch blocks

## Quick Start

### 1. Start the Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### 2. Open the Frontend

Open `frontend.html` in your browser (or use Live Server).

### 3. Convert Code

1. **Upload** a file or **paste** code directly
2. Select target language (source auto-detects)
3. Click **Convert**
4. **Download** or **Copy** the result

## File Extensions

| Extension | Language |
|-----------|----------|
| `.py` | Python |
| `.js` | JavaScript |
| `.ts` | TypeScript |
| `.java` | Java |
| `.cpp`, `.c` | C/C++ |
| `.rb` | Ruby |
| `.go` | Go |
| `.rs` | Rust |
| `.php` | PHP |

## API Endpoints

```
POST /detect-language  - Detect code language
POST /convert          - Convert code between languages
```

## Tech Stack

- **Frontend**: Vanilla JS + Tailwind CSS
- **Backend**: FastAPI + Python
- **No build tools required**

## License

MIT

---

Made with code by Preet
