#!/usr/bin/env python3
"""Fail-closed battery for the generalized split-package part discovery.

v1.7.1: `tools._discover_parts()` derives the ordered `pkg/<name>.partNN`
list instead of hard-coding two parts.  This battery proves the discovery
refuses every malformed layout BEFORE any bytes are trusted:

  P1  genuine layout        -> concatenation equals the real vendored bytes
  P2  gap (part01 missing / renamed to part02) -> refuses (non-contiguous)
  P3  extra undeclared part02                  -> refuses (EPOCH divergence)
  P4  part missing entirely (only part00)      -> refuses (EPOCH divergence)
  P5  malformed suffix (partXX)                -> refuses (malformed name)
  P6  duplicate-index name (part00 twice via part000 ambiguity) -> refuses
  P7  empty pkg dir                            -> refuses (no parts)
  P8  EPOCH declares a part the disk lacks     -> refuses (declared-missing)

Each poison runs against a THROWAWAY plugin-root skeleton (hard links to the
real part bytes; the real tree is never modified).  Runnable under
`python3 -O` (assert-free checks).
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'} {name} {detail[:120]}")
    if not ok:
        FAILURES.append(name)


def load_tools_at(plugin_root: Path):
    """Import a fresh tools module bound to an arbitrary plugin root."""
    spec = importlib.util.spec_from_file_location(
        f"tools_probe_{plugin_root.name}", ROOT / "tools.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.PLUGIN_ROOT = plugin_root
    mod.PKG_TARBALL = plugin_root / "pkg" / mod.PKG_TARBALL.name
    mod.EPOCH_RECEIPT = plugin_root / "EPOCH.json"
    return mod


def skeleton(td: Path, parts: list[str], declared: list[str] | None) -> Path:
    """Build a throwaway plugin root: hard-linked real parts + EPOCH stub."""
    root = td / f"root-{len(list(td.iterdir()))}"
    (root / "pkg").mkdir(parents=True)
    real = sorted((ROOT / "pkg").glob("*.part*"))
    base = real[0].name.rsplit(".part", 1)[0]
    for i, name in enumerate(parts):
        src = real[min(i, len(real) - 1)]
        os.link(src, root / "pkg" / name)
    epoch = json.loads((ROOT / "EPOCH.json").read_text())
    if declared is not None:
        epoch["vendored"]["parts"] = declared
    (root / "EPOCH.json").write_text(json.dumps(epoch, indent=1,
                                                sort_keys=True))
    return root


def main() -> int:
    real_parts = sorted((ROOT / "pkg").glob("*.part*"))
    if not real_parts:
        print("RED: no real parts in pkg/", file=sys.stderr)
        return 2
    base = real_parts[0].name.rsplit(".part", 1)[0]
    real_names = [p.name for p in real_parts]
    real_declared = [f"pkg/{n}" for n in real_names]
    real_blob_sha = hashlib.sha256(
        b"".join(p.read_bytes() for p in real_parts)).hexdigest()

    with tempfile.TemporaryDirectory(prefix="jackal-parts-") as tds:
        td = Path(tds)

        # P1 genuine
        mod = load_tools_at(skeleton(td, real_names, real_declared))
        try:
            got = hashlib.sha256(mod._package_bytes()).hexdigest()
            check("P1-genuine-concat", got == real_blob_sha
                  and got == mod.PKG_SHA256, got[:16])
        except Exception as exc:  # noqa: BLE001
            check("P1-genuine-concat", False, str(exc))

        def expect_refusal(name: str, parts: list[str],
                           declared: list[str] | None,
                           needle: str) -> None:
            mod = load_tools_at(skeleton(td, parts, declared))
            try:
                mod._package_bytes()
                check(name, False, "ACCEPTED (wanted refusal)")
            except mod.JackalError as exc:
                check(name, needle in str(exc), str(exc))
            except Exception as exc:  # noqa: BLE001
                check(name, False, f"wrong error type: {exc}")

        # P2 gap: part01 renamed to part02
        expect_refusal("P2-gap-noncontiguous",
                       [f"{base}.part00", f"{base}.part02"],
                       real_declared, "non-contiguous")
        # P3 extra undeclared part02 (declared list stays the real one)
        expect_refusal("P3-extra-undeclared",
                       real_names + [f"{base}.part{len(real_names):02d}"],
                       real_declared, "diverge")
        # P4 only part00 on disk, full declaration
        expect_refusal("P4-part-missing",
                       [f"{base}.part00"], real_declared, "diverge")
        # P5 malformed suffix
        expect_refusal("P5-malformed-suffix",
                       real_names + [f"{base}.partXX"],
                       real_declared, "malformed part name")
        # P6 ambiguous zero-padded duplicate index (part000 == index 0)
        expect_refusal("P6-duplicate-index",
                       real_names + [f"{base}.part000"],
                       real_declared, "duplicate part index")
        # P7 empty pkg dir
        expect_refusal("P7-empty", [], real_declared, "no vendored")
        # P8 EPOCH declares one more part than the disk carries
        expect_refusal("P8-declared-missing",
                       real_names,
                       real_declared + [f"pkg/{base}.part99"], "diverge")

    print(f"PARTS_DISCOVERY_{'PASS' if not FAILURES else 'FAIL'} "
          f"rows={8} failures={len(FAILURES)}")
    return 0 if not FAILURES else 1


if __name__ == "__main__":
    sys.exit(main())
