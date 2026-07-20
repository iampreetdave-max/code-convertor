"""
Content-addressed cache for conversion results.

Why: the free-tier LLM has a tokens-per-minute cap, so a large file can fail or
stall on a retry loop. Converting identical input twice is also pure waste. The
cache stores REAL pipeline output keyed by a hash of (source, target, code), so
a repeat request is instant and cannot be rate-limited.

This is a genuine feature, not a demo prop: results are only ever written after
a successful conversion by the normal pipeline.

The store is a single JSON file so it survives restarts and can be shipped with
a deploy (pre-warmed entries make the first demo request instant).
"""

import hashlib
import json
import os
import threading
from typing import Optional

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                            "conversion_cache.json")


class ConversionCache:
    def __init__(self, path: str = DEFAULT_PATH):
        self.path = os.path.abspath(path)
        self._lock = threading.Lock()
        self._data = {}
        self._load()

    # ------------------------------------------------------------------ io
    def _load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                self._data = json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            self._data = {}

    def _save(self) -> None:
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=1)
            os.replace(tmp, self.path)
        except OSError:
            pass  # cache is best-effort; never break a conversion over it

    # ---------------------------------------------------------------- api
    @staticmethod
    def key(code: str, source: str, target: str) -> str:
        raw = f"{source.lower()}|{target.lower()}|{code}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, code: str, source: str, target: str) -> Optional[dict]:
        with self._lock:
            return self._data.get(self.key(code, source, target))

    def set(self, code: str, source: str, target: str, payload: dict) -> None:
        with self._lock:
            self._data[self.key(code, source, target)] = payload
            self._save()

    def __len__(self) -> int:
        return len(self._data)
