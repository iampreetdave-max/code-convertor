from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from api.models import (
    DetectRequest, DetectResponse,
    ConvertRequest, ConvertResponse,
    ValidateRequest, ValidateResponse,
    ReportRequest,
    ConvertAndValidateRequest, ConvertAndValidateResponse
)
from core.language_detector import LanguageDetector
from core.conversion_engine import ConversionEngine
from core.code_validator import CodeValidator
from core.report_generator import ReportGenerator
import os

# Initialize FastAPI app with increased limits for large code files
app = FastAPI(
    title="Code Converter API",
    description="Convert code between Python, JavaScript, and Java",
    version="2.0"
)

# Configure request size limits (10MB for large code files)
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB

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
validator = CodeValidator()
report_gen = ReportGenerator()


@app.get("/api/health")
def health_check():
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


@app.post("/validate", response_model=ValidateResponse)
def validate_code(req: ValidateRequest):
    """
    Validate converted code using Groq API.

    Args:
        req: ValidateRequest with converted_code, original_code, target_language

    Returns:
        ValidateResponse with score (1-10), feedback, issues, and suggestions
    """
    try:
        if not req.converted_code.strip():
            raise ValueError("Converted code cannot be empty")

        result = validator.validate(
            converted_code=req.converted_code,
            original_code=req.original_code,
            target_language=req.target_language
        )

        return ValidateResponse(
            score=result.score,
            is_valid=result.is_valid,
            feedback=result.feedback,
            issues=result.issues,
            suggestions=result.suggestions,
            compilation_check=result.compilation_check
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")


@app.post("/report")
def generate_report(req: ReportRequest):
    """
    Generate a conversion report.

    Args:
        req: ReportRequest with code and metadata

    Returns:
        HTML or JSON report based on format parameter
    """
    try:
        report = report_gen.generate_report(
            original_code=req.original_code,
            converted_code=req.converted_code,
            source_lang=req.source_language,
            target_lang=req.target_language,
            confidence=req.confidence,
            validation_score=req.validation_score,
            validation_feedback=req.validation_feedback,
            warnings=req.warnings,
            conversion_method="llm" if req.target_language == "java" else "rule-based"
        )

        if req.format.lower() == "json":
            return JSONResponse(content={"report": report_gen.to_json(report)})
        else:
            return HTMLResponse(content=report_gen.to_html(report))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation error: {str(e)}")


@app.post("/convert-full", response_model=ConvertAndValidateResponse)
def convert_and_validate(req: ConvertAndValidateRequest):
    """
    Full conversion pipeline: convert, validate, and optionally generate report.

    This is the main endpoint for the complete conversion experience.

    Args:
        req: ConvertAndValidateRequest with code and options

    Returns:
        ConvertAndValidateResponse with conversion, validation, and optional report
    """
    try:
        if not req.code.strip():
            raise ValueError("Code cannot be empty")

        # Step 1: Convert the code
        conversion_result = engine.convert(
            code=req.code,
            source_language=req.source_language,
            target_language=req.target_language,
            strict_mode=False
        )

        # Step 2: Validate (if requested)
        validation_result = None
        if req.run_validation and conversion_result.conversion_confidence > 0:
            val_result = validator.validate(
                converted_code=conversion_result.converted_code,
                original_code=req.code,
                target_language=req.target_language
            )
            validation_result = ValidateResponse(
                score=val_result.score,
                is_valid=val_result.is_valid,
                feedback=val_result.feedback,
                issues=val_result.issues,
                suggestions=val_result.suggestions,
                compilation_check=val_result.compilation_check
            )

        # Step 3: Generate report (if requested)
        report_html = None
        if req.generate_report:
            report = report_gen.generate_report(
                original_code=req.code,
                converted_code=conversion_result.converted_code,
                source_lang=req.source_language,
                target_lang=req.target_language,
                confidence=conversion_result.conversion_confidence,
                validation_score=validation_result.score if validation_result else None,
                validation_feedback=validation_result.feedback if validation_result else None,
                warnings=conversion_result.warnings,
                conversion_method=conversion_result.metadata.get("method", "rule-based")
            )
            report_html = report_gen.to_html(report)

        return ConvertAndValidateResponse(
            conversion=conversion_result,
            validation=validation_result,
            report_html=report_html
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion error: {str(e)}")


# Serve frontend - MUST be mounted after all API routes
frontend_path = os.path.join(os.path.dirname(__file__), "..")
app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
