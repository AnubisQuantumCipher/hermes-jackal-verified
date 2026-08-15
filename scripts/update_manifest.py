#!/usr/bin/env python3
"""Regenerate the complete content-addressed plugin MANIFEST.json."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "MANIFEST.json"
EXCLUDED = {"MANIFEST.json"}


def release_files() -> list[Path]:
    return [
        path
        for path in sorted(ROOT.rglob("*"))
        if path.is_file()
        and ".git" not in path.parts
        and "__pycache__" not in path.parts
        and path.name != ".DS_Store"
        and str(path.relative_to(ROOT)) not in EXCLUDED
    ]


def main() -> int:
    files = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in release_files()
    }
    document = {"schema": "jackal-plugin-manifest-v1", "files": files}
    MANIFEST.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"MANIFEST_WRITTEN files={len(files)} sha256={hashlib.sha256(MANIFEST.read_bytes()).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
