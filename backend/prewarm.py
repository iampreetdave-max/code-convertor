"""
Pre-warm the conversion cache for a demo file.

Runs the REAL conversion pipeline (patiently retrying through free-tier rate
limits) and stores the result, so during a demo the same input returns instantly
and cannot be rate-limited.

Usage (from backend/):
    python prewarm.py <file> [source_lang] [target ...]

Examples:
    python prewarm.py ../login.html                 # html -> every target
    python prewarm.py app.py python javascript java # specific targets
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.conversion_engine import ConversionEngine
from core.language_detector import LanguageDetector


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    path = sys.argv[1]
    try:
        code = open(path, "r", encoding="utf-8").read()
    except OSError as e:
        print(f"cannot read {path}: {e}")
        return 2

    engine = ConversionEngine()
    source = sys.argv[2].lower() if len(sys.argv) > 2 else \
        LanguageDetector().detect(code).detected_language
    if source not in engine.SOURCE_LANGUAGES:
        print(f"unsupported source '{source}'. one of: {engine.SOURCE_LANGUAGES}")
        return 2

    targets = [t.lower() for t in sys.argv[3:]] or \
        [t for t in engine.TARGET_LANGUAGES if t != source]

    print(f"{path}: {len(code.splitlines())} lines, source={source}")
    print(f"targets: {', '.join(targets)}\n")

    ok = 0
    for target in targets:
        for attempt in range(1, 7):          # patient: rate limits pass in ~60s
            try:
                res = engine.convert(code, source, target)
                good = res.conversion_confidence > 0 and res.converted_code.strip()
                if good:
                    cached = res.metadata.get("cached")
                    print(f"  [OK]   {source} -> {target:<11} "
                          f"conf={res.conversion_confidence} "
                          f"{'(already cached)' if cached else '(cached now)'}")
                    ok += 1
                    break
                reason = (res.warnings or ["unknown"])[0]
                print(f"  ...    {source} -> {target}: attempt {attempt} failed "
                      f"({reason[:60]}) - waiting")
            except Exception as e:
                print(f"  ...    {source} -> {target}: attempt {attempt} error "
                      f"({type(e).__name__}) - waiting")
            time.sleep(min(15 * attempt, 60))
        else:
            print(f"  [FAIL] {source} -> {target}: gave up")

    print(f"\n{ok}/{len(targets)} cached. Cache: {engine.cache.path} "
          f"({len(engine.cache)} entries)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
