from pydantic import BaseModel
from typing import List, Dict, Optional, Tuple


class DetectRequest(BaseModel):
    """Request to detect source code language."""
    code: str


class DetectResponse(BaseModel):
    """Response with detected language and confidence."""
    detected_language: str
    confidence: float  # 0.0-1.0
    reason: str
    alternatives: List[Tuple[str, float]] = []


class ConvertRequest(BaseModel):
    """Request to convert code between languages."""
    code: str
    source_language: str
    target_language: str
    strict_mode: bool = False


class UnsupportedConstruct(BaseModel):
    """Represents an unsupported construct found during conversion."""
    line: int
    code_construct: str  # renamed from 'construct' to avoid shadowing BaseModel
    type: str  # "error" or "warning"
    description: Optional[str] = None


class ConvertResponse(BaseModel):
    """Response with converted code and metadata."""
    converted_code: str
    source_language: str
    target_language: str
    conversion_confidence: float  # 0.0-1.0
    warnings: List[str] = []
    unsupported_constructs: List[Dict] = []
    unsupported_lines_count: int = 0
    conversion_level: int = 1  # 1, 2, or 3
    metadata: Dict = {}


class ValidateRequest(BaseModel):
    """Request to validate converted code."""
    converted_code: str
    original_code: str
    target_language: str = "java"


class ValidateResponse(BaseModel):
    """Response with validation results."""
    score: int  # 1-10
    is_valid: bool
    feedback: str
    issues: List[str] = []
    suggestions: List[str] = []
    compilation_check: str = "UNKNOWN"


class ReportRequest(BaseModel):
    """Request to generate conversion report."""
    original_code: str
    converted_code: str
    source_language: str
    target_language: str
    confidence: float
    validation_score: Optional[int] = None
    validation_feedback: Optional[str] = None
    warnings: List[str] = []
    format: str = "html"  # "html" or "json"


class ConvertAndValidateRequest(BaseModel):
    """Request for full conversion with validation."""
    code: str
    source_language: str
    target_language: str
    run_validation: bool = True  # renamed from 'validate' to avoid shadowing BaseModel
    generate_report: bool = False


class ConvertAndValidateResponse(BaseModel):
    """Response with conversion, validation, and optional report."""
    conversion: ConvertResponse
    validation: Optional[ValidateResponse] = None
    report_html: Optional[str] = None
