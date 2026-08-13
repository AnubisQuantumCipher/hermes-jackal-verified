#!/usr/bin/env python3
"""Verify every path sealed by MANIFEST.json and reject unsealed release files."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "MANIFEST.json"
EXCLUDED = {"MANIFEST.json", ".git"}


def release_files() -> set[str]:
    return {
        str(path.relative_to(ROOT))
        for path in ROOT.rglob("*")
        if path.is_file()
        and ".git" not in path.parts
        and "__pycache__" not in path.parts
        and path.name != ".DS_Store"
        and str(path.relative_to(ROOT)) not in EXCLUDED
    }


def main() -> int:
    document = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if document.get("schema") != "jackal-plugin-manifest-v1":
        raise SystemExit("unsupported manifest schema")
    files = document.get("files")
    if not isinstance(files, dict) or not files:
        raise SystemExit("manifest has no files")
    expected = release_files()
    sealed = set(files)
    if expected != sealed:
        raise SystemExit(f"manifest coverage mismatch: missing={sorted(expected-sealed)} extra={sorted(sealed-expected)}")
    for relative, digest in sorted(files.items()):
        path = ROOT / relative
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed != digest:
            raise SystemExit(f"digest mismatch: {relative}: {observed}")
    print(f"MANIFEST_PASS files={len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
