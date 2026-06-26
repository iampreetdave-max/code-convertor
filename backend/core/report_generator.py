"""
Conversion Report Generator.

Generates detailed reports explaining the code conversion process.
Supports HTML and JSON formats for download.
"""

import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class ConversionStep:
    """A single step in the conversion process."""
    line_number: int
    original: str
    converted: str
    change_type: str  # "syntax", "type_inference", "structure", "method_mapping", "unchanged"
    explanation: str


@dataclass
class ConversionReport:
    """Complete conversion report."""
    timestamp: str
    source_language: str
    target_language: str
    original_code: str
    converted_code: str
    total_lines: int
    converted_lines: int
    confidence_score: float
    validation_score: Optional[int]
    validation_feedback: Optional[str]
    steps: List[ConversionStep]
    summary: Dict[str, int]  # Count of each change type
    warnings: List[str]
    conversion_method: str  # "llm" or "rule-based"


class ReportGenerator:
    """Generates conversion reports in various formats."""

    def __init__(self):
        self.change_explanations = {
            "syntax": "Syntax adaptation for target language",
            "type_inference": "Type inferred from context/usage",
            "structure": "Structural change (class wrapper, imports, etc.)",
            "method_mapping": "Method/function name mapped to equivalent",
            "unchanged": "No change needed",
            "control_flow": "Control flow structure converted",
            "exception": "Exception handling adapted",
            "string": "String formatting converted",
        }

    def analyze_conversion(
        self,
        original_code: str,
        converted_code: str,
        source_lang: str,
        target_lang: str
    ) -> List[ConversionStep]:
        """
        Analyze the conversion and identify changes.
        """
        original_lines = original_code.splitlines()
        converted_lines = converted_code.splitlines()
        steps = []

        # Track Python to Java specific changes
        if source_lang == "python" and target_lang == "java":
            steps.extend(self._analyze_python_to_java(original_lines, converted_lines))
        else:
            # Generic analysis
            steps.extend(self._analyze_generic(original_lines, converted_lines))

        return steps

    def _analyze_python_to_java(
        self,
        original_lines: List[str],
        converted_lines: List[str]
    ) -> List[ConversionStep]:
        """Analyze Python to Java conversion."""
        steps = []

        # Check for added structure (imports, class wrapper)
        for i, line in enumerate(converted_lines[:20]):  # Check first 20 lines
            if line.strip().startswith("import java"):
                steps.append(ConversionStep(
                    line_number=i + 1,
                    original="(added)",
                    converted=line,
                    change_type="structure",
                    explanation="Java import statement added for required classes"
                ))
            elif "public class" in line:
                steps.append(ConversionStep(
                    line_number=i + 1,
                    original="(added)",
                    converted=line,
                    change_type="structure",
                    explanation="Java requires all code inside a class"
                ))
            elif "public static void main" in line:
                steps.append(ConversionStep(
                    line_number=i + 1,
                    original="(added)",
                    converted=line,
                    change_type="structure",
                    explanation="Entry point for Java application"
                ))

        # Analyze original lines for what changed
        for i, orig_line in enumerate(original_lines):
            orig_stripped = orig_line.strip()
            if not orig_stripped:
                continue

            step = self._classify_python_line(i + 1, orig_stripped, converted_lines)
            if step:
                steps.append(step)

        return steps

    def _classify_python_line(
        self,
        line_num: int,
        orig_line: str,
        converted_lines: List[str]
    ) -> Optional[ConversionStep]:
        """Classify what happened to a Python line."""

        # Variable assignment with type inference
        if "=" in orig_line and not orig_line.startswith("if") and not orig_line.startswith("for"):
            if orig_line.startswith("#"):
                return ConversionStep(
                    line_number=line_num,
                    original=orig_line,
                    converted="// " + orig_line[1:].strip(),
                    change_type="syntax",
                    explanation="Python comment (#) converted to Java comment (//)"
                )

            var_match = orig_line.split("=")[0].strip()
            # Look for type inference
            if "[" in orig_line and "]" in orig_line:
                return ConversionStep(
                    line_number=line_num,
                    original=orig_line,
                    converted=f"List<...> {var_match} = new ArrayList<>(...);",
                    change_type="type_inference",
                    explanation="Python list converted to Java ArrayList with inferred generic type"
                )
            elif "{" in orig_line and ":" in orig_line:
                return ConversionStep(
                    line_number=line_num,
                    original=orig_line,
                    converted=f"Map<...> {var_match} = new HashMap<>(...);",
                    change_type="type_inference",
                    explanation="Python dict converted to Java HashMap with inferred types"
                )
            else:
                return ConversionStep(
                    line_number=line_num,
                    original=orig_line,
                    converted=f"<type> {var_match} = ...;",
                    change_type="type_inference",
                    explanation="Variable type inferred from assigned value"
                )

        # Print statement
        if orig_line.startswith("print("):
            return ConversionStep(
                line_number=line_num,
                original=orig_line,
                converted="System.out.println(...);",
                change_type="method_mapping",
                explanation="Python print() maps to Java System.out.println()"
            )

        # Function definition
        if orig_line.startswith("def "):
            return ConversionStep(
                line_number=line_num,
                original=orig_line,
                converted="public static <return_type> methodName(...) {",
                change_type="structure",
                explanation="Python function converted to Java method with inferred return type"
            )

        # Class definition
        if orig_line.startswith("class "):
            return ConversionStep(
                line_number=line_num,
                original=orig_line,
                converted="public class ClassName {",
                change_type="structure",
                explanation="Python class converted to Java public class"
            )

        # Control flow
        if orig_line.startswith("if "):
            return ConversionStep(
                line_number=line_num,
                original=orig_line,
                converted="if (...) {",
                change_type="control_flow",
                explanation="Condition wrapped in parentheses, colon replaced with brace"
            )

        if orig_line.startswith("elif "):
            return ConversionStep(
                line_number=line_num,
                original=orig_line,
                converted="} else if (...) {",
                change_type="control_flow",
                explanation="Python elif becomes Java else if"
            )

        if orig_line.startswith("for ") and " in " in orig_line:
            if "range(" in orig_line:
                return ConversionStep(
                    line_number=line_num,
                    original=orig_line,
                    converted="for (int i = 0; i < n; i++) {",
                    change_type="control_flow",
                    explanation="Python range-based for loop converted to C-style for loop"
                )
            else:
                return ConversionStep(
                    line_number=line_num,
                    original=orig_line,
                    converted="for (Type item : collection) {",
                    change_type="control_flow",
                    explanation="Python for-in converted to Java enhanced for loop"
                )

        if orig_line.startswith("while "):
            return ConversionStep(
                line_number=line_num,
                original=orig_line,
                converted="while (...) {",
                change_type="control_flow",
                explanation="Condition wrapped in parentheses, colon replaced with brace"
            )

        # Exception handling
        if orig_line.startswith("try:"):
            return ConversionStep(
                line_number=line_num,
                original=orig_line,
                converted="try {",
                change_type="exception",
                explanation="Python try block start"
            )

        if orig_line.startswith("except"):
            return ConversionStep(
                line_number=line_num,
                original=orig_line,
                converted="catch (Exception e) {",
                change_type="exception",
                explanation="Python except converted to Java catch with appropriate exception type"
            )

        # Method calls
        if ".append(" in orig_line:
            return ConversionStep(
                line_number=line_num,
                original=orig_line,
                converted=orig_line.replace(".append(", ".add("),
                change_type="method_mapping",
                explanation="Python list.append() maps to Java list.add()"
            )

        if ".upper()" in orig_line:
            return ConversionStep(
                line_number=line_num,
                original=orig_line,
                converted=orig_line.replace(".upper()", ".toUpperCase()"),
                change_type="method_mapping",
                explanation="Python str.upper() maps to Java String.toUpperCase()"
            )

        return None

    def _analyze_generic(
        self,
        original_lines: List[str],
        converted_lines: List[str]
    ) -> List[ConversionStep]:
        """Generic line-by-line analysis."""
        steps = []
        for i, (orig, conv) in enumerate(zip(original_lines, converted_lines)):
            if orig.strip() != conv.strip():
                steps.append(ConversionStep(
                    line_number=i + 1,
                    original=orig,
                    converted=conv,
                    change_type="syntax",
                    explanation="Syntax adapted for target language"
                ))
        return steps

    def generate_report(
        self,
        original_code: str,
        converted_code: str,
        source_lang: str,
        target_lang: str,
        confidence: float,
        validation_score: Optional[int] = None,
        validation_feedback: Optional[str] = None,
        warnings: List[str] = None,
        conversion_method: str = "llm"
    ) -> ConversionReport:
        """Generate a complete conversion report."""

        steps = self.analyze_conversion(original_code, converted_code, source_lang, target_lang)

        # Count change types
        summary = {}
        for step in steps:
            summary[step.change_type] = summary.get(step.change_type, 0) + 1

        return ConversionReport(
            timestamp=datetime.now().isoformat(),
            source_language=source_lang,
            target_language=target_lang,
            original_code=original_code,
            converted_code=converted_code,
            total_lines=len(original_code.splitlines()),
            converted_lines=len(converted_code.splitlines()),
            confidence_score=confidence,
            validation_score=validation_score,
            validation_feedback=validation_feedback,
            steps=steps,
            summary=summary,
            warnings=warnings or [],
            conversion_method=conversion_method
        )

    def to_json(self, report: ConversionReport) -> str:
        """Convert report to JSON string."""
        report_dict = asdict(report)
        return json.dumps(report_dict, indent=2)

    def to_html(self, report: ConversionReport) -> str:
        """Convert report to HTML string."""

        # Generate steps HTML
        steps_html = ""
        for step in report.steps[:50]:  # Limit to 50 steps for readability
            change_class = f"change-{step.change_type}"
            steps_html += f"""
            <div class="step {change_class}">
                <div class="step-header">
                    <span class="line-num">Line {step.line_number}</span>
                    <span class="change-type">{step.change_type.replace('_', ' ').title()}</span>
                </div>
                <div class="code-comparison">
                    <div class="original">
                        <strong>Python:</strong>
                        <code>{self._escape_html(step.original)}</code>
                    </div>
                    <div class="arrow">→</div>
                    <div class="converted">
                        <strong>Java:</strong>
                        <code>{self._escape_html(step.converted)}</code>
                    </div>
                </div>
                <div class="explanation">{step.explanation}</div>
            </div>
            """

        # Generate summary HTML
        summary_html = ""
        for change_type, count in report.summary.items():
            summary_html += f"<li><strong>{change_type.replace('_', ' ').title()}:</strong> {count} changes</li>"

        # Generate warnings HTML
        warnings_html = ""
        if report.warnings:
            warnings_html = "<h3>Warnings</h3><ul>"
            for warning in report.warnings:
                warnings_html += f"<li>{self._escape_html(warning)}</li>"
            warnings_html += "</ul>"

        # Validation section
        validation_html = ""
        if report.validation_score is not None:
            score_class = "high" if report.validation_score >= 7 else "medium" if report.validation_score >= 5 else "low"
            validation_html = f"""
            <div class="validation-section">
                <h3>Validation Results</h3>
                <div class="score {score_class}">
                    <span class="score-value">{report.validation_score}</span>
                    <span class="score-max">/10</span>
                </div>
                <p class="feedback">{self._escape_html(report.validation_feedback or '')}</p>
            </div>
            """

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Conversion Report</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 40px 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{
            text-align: center;
            font-size: 2.5rem;
            margin-bottom: 10px;
            background: linear-gradient(90deg, #00d4ff, #9b59b6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        .subtitle {{
            text-align: center;
            color: #888;
            margin-bottom: 40px;
        }}
        .header-info {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .info-card {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
        }}
        .info-card h3 {{
            font-size: 0.9rem;
            color: #888;
            margin-bottom: 8px;
        }}
        .info-card .value {{
            font-size: 1.8rem;
            font-weight: bold;
            color: #00d4ff;
        }}
        .code-section {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 40px;
        }}
        .code-block {{
            background: #0d1117;
            border-radius: 12px;
            overflow: hidden;
        }}
        .code-block h3 {{
            background: rgba(255, 255, 255, 0.1);
            padding: 12px 20px;
            font-size: 1rem;
        }}
        .code-block pre {{
            padding: 20px;
            overflow-x: auto;
            font-family: 'Fira Code', 'Consolas', monospace;
            font-size: 0.85rem;
            line-height: 1.6;
            white-space: pre-wrap;
            max-height: 400px;
            overflow-y: auto;
        }}
        .section {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
        }}
        .section h2 {{
            font-size: 1.5rem;
            margin-bottom: 20px;
            color: #00d4ff;
        }}
        .step {{
            background: rgba(0, 0, 0, 0.3);
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            border-left: 4px solid #666;
        }}
        .step.change-type_inference {{ border-left-color: #9b59b6; }}
        .step.change-structure {{ border-left-color: #3498db; }}
        .step.change-method_mapping {{ border-left-color: #2ecc71; }}
        .step.change-control_flow {{ border-left-color: #f39c12; }}
        .step.change-exception {{ border-left-color: #e74c3c; }}
        .step.change-syntax {{ border-left-color: #1abc9c; }}
        .step-header {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
        }}
        .line-num {{
            color: #888;
            font-size: 0.85rem;
        }}
        .change-type {{
            background: rgba(255, 255, 255, 0.1);
            padding: 2px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            text-transform: uppercase;
        }}
        .code-comparison {{
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 10px;
        }}
        .code-comparison .original,
        .code-comparison .converted {{
            flex: 1;
            background: rgba(0, 0, 0, 0.3);
            padding: 10px;
            border-radius: 6px;
        }}
        .code-comparison code {{
            font-family: 'Fira Code', monospace;
            font-size: 0.85rem;
            color: #e0e0e0;
            display: block;
            margin-top: 5px;
            word-break: break-all;
        }}
        .code-comparison .arrow {{
            font-size: 1.5rem;
            color: #00d4ff;
        }}
        .explanation {{
            color: #aaa;
            font-size: 0.9rem;
            font-style: italic;
        }}
        .summary-list {{
            list-style: none;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
        }}
        .summary-list li {{
            background: rgba(0, 0, 0, 0.2);
            padding: 10px 15px;
            border-radius: 6px;
        }}
        .validation-section {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .score {{
            display: inline-flex;
            align-items: baseline;
            padding: 20px 40px;
            border-radius: 12px;
            margin: 20px 0;
        }}
        .score.high {{ background: rgba(46, 204, 113, 0.2); }}
        .score.medium {{ background: rgba(241, 196, 15, 0.2); }}
        .score.low {{ background: rgba(231, 76, 60, 0.2); }}
        .score-value {{
            font-size: 4rem;
            font-weight: bold;
        }}
        .score.high .score-value {{ color: #2ecc71; }}
        .score.medium .score-value {{ color: #f1c40f; }}
        .score.low .score-value {{ color: #e74c3c; }}
        .score-max {{
            font-size: 1.5rem;
            color: #888;
        }}
        .feedback {{
            max-width: 600px;
            margin: 0 auto;
            color: #aaa;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            color: #666;
        }}
        @media (max-width: 768px) {{
            .code-section {{
                grid-template-columns: 1fr;
            }}
            .code-comparison {{
                flex-direction: column;
            }}
            .code-comparison .arrow {{
                transform: rotate(90deg);
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Code Conversion Report</h1>
        <p class="subtitle">Generated on {report.timestamp[:19].replace('T', ' ')}</p>

        <div class="header-info">
            <div class="info-card">
                <h3>Source Language</h3>
                <div class="value">{report.source_language.upper()}</div>
            </div>
            <div class="info-card">
                <h3>Target Language</h3>
                <div class="value">{report.target_language.upper()}</div>
            </div>
            <div class="info-card">
                <h3>Lines Converted</h3>
                <div class="value">{report.total_lines} → {report.converted_lines}</div>
            </div>
            <div class="info-card">
                <h3>Confidence</h3>
                <div class="value">{int(report.confidence_score * 100)}%</div>
            </div>
        </div>

        {validation_html}

        <div class="code-section">
            <div class="code-block">
                <h3>Original Python Code</h3>
                <pre>{self._escape_html(report.original_code)}</pre>
            </div>
            <div class="code-block">
                <h3>Converted Java Code</h3>
                <pre>{self._escape_html(report.converted_code)}</pre>
            </div>
        </div>

        <div class="section">
            <h2>Conversion Summary</h2>
            <ul class="summary-list">
                {summary_html}
            </ul>
        </div>

        {warnings_html}

        <div class="section">
            <h2>Conversion Details</h2>
            <p style="color: #888; margin-bottom: 20px;">
                Below is a breakdown of the key transformations made during conversion.
            </p>
            {steps_html}
        </div>

        <div class="footer">
            <p>Generated by Code Converter | Conversion Method: {report.conversion_method.upper()}</p>
        </div>
    </div>
</body>
</html>"""

        return html

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#39;"))
