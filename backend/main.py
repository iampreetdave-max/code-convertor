from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from api.models import DetectRequest, DetectResponse, ConvertRequest, ConvertResponse
from core.language_detector import LanguageDetector
from core.conversion_engine import ConversionEngine

# Initialize FastAPI app
app = FastAPI(
    title="Code Converter API",
    description="Convert code between Python, JavaScript, and Java",
    version="2.0"
)

# Allow frontend to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize core modules
detector = LanguageDetector()
engine = ConversionEngine()


@app.get("/")
def root():
    """Health check endpoint."""
    return {
        "status": "Backend running",
        "version": "2.0",
        "supported_pairs": engine.get_supported_pairs()
    }


@app.post("/detect-language", response_model=DetectResponse)
def detect_language(req: DetectRequest):
    """
    Detect source code language with confidence score.

    Args:
        req: DetectRequest with code

    Returns:
        DetectResponse with detected_language, confidence, reason, and alternatives
    """
    try:
        if not req.code.strip():
            raise ValueError("Code cannot be empty")

        result = detector.detect(req.code)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection error: {str(e)}")


@app.post("/convert", response_model=ConvertResponse)
def convert_code(req: ConvertRequest):
    """
    Convert code between supported languages.

    Args:
        req: ConvertRequest with code, source_language, target_language

    Returns:
        ConvertResponse with converted_code, confidence, warnings, and metadata
    """
    try:
        if not req.code.strip():
            raise ValueError("Code cannot be empty")

        if not req.source_language:
            raise ValueError("Source language must be specified")

        if not req.target_language:
            raise ValueError("Target language must be specified")

        result = engine.convert(
            code=req.code,
            source_language=req.source_language,
            target_language=req.target_language,
            strict_mode=req.strict_mode
        )
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion error: {str(e)}")
