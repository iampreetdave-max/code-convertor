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
    construct: str
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
