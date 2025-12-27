from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# Allow frontend to call backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "Backend running"}


# Language Detection Logic
def detect_language(code: str):
    code = code.lower()

    if "def " in code and ":" in code:
        return "python"
    if "console.log" in code or "let " in code or "=>" in code:
        return "javascript"
    if "public static void main" in code or "system.out.println" in code:
        return "java"

    return "unknown"


# Request Models
class DetectRequest(BaseModel):
    code: str


class ConvertRequest(BaseModel):
    code: str
    source_language: str
    target_language: str


# Language Detection API
@app.post("/detect-language")
def detect(req: DetectRequest):
    language = detect_language(req.code)
    return {
        "detected_language": language
    }


# Code Conversion Logic
def convert_code(code: str, source: str, target: str):
    if source == "python" and target == "javascript":
        return code.replace("print(", "console.log(")

    if source == "javascript" and target == "python":
        return code.replace("console.log(", "print(")

    return "// Conversion not supported yet"


# Code Conversion API
@app.post("/convert")
def convert(req: ConvertRequest):
    result = convert_code(
        req.code,
        req.source_language,
        req.target_language
    )
    return {
        "converted_code": result
    }
