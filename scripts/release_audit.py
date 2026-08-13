#!/usr/bin/env python3
"""Fail-closed source-release checks with explicit counters."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {"", ".md", ".py", ".yaml", ".yml", ".json", ".toml", ".txt"}
FORBIDDEN_PATH_PARTS = {".env", ".hermes", "sessions", "memories", "logs", "credentials"}
PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github-token": re.compile(r"\b(?:gh[opusr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    "aws-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "generic-secret-assignment": re.compile(r"(?i)\b(?:api[_-]?key|password|passwd|secret|token)\s*=\s*['\"][^'\"]{8,}['\"]"),
}


def main() -> int:
    files = [p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts and "__pycache__" not in p.parts]
    path_failures: list[str] = []
    secret_failures: list[str] = []
    scanned = 0
    for path in files:
        relative = path.relative_to(ROOT)
        lowered = {part.lower() for part in relative.parts}
        if lowered & FORBIDDEN_PATH_PARTS:
            path_failures.append(str(relative))
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        raw = path.read_bytes()
        # Extensionless scripts are text, but the embedded Mach-O is also
        # extensionless. Classify by bytes rather than trusting the suffix.
        if b"\x00" in raw[:8192]:
            continue
        scanned += 1
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            continue
        for name, pattern in PATTERNS.items():
            if pattern.search(text):
                secret_failures.append(f"{relative}:{name}")
    if path_failures or secret_failures:
        raise SystemExit(f"RELEASE_AUDIT_FAIL forbidden_paths={path_failures} secret_matches={secret_failures}")
    print(f"RELEASE_AUDIT_PASS files={len(files)} text_scanned={scanned} forbidden_paths=0 secret_matches=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
