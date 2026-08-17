#!/usr/bin/env python3
"""A->B->A gate: the admission pin-loop in tools.py is load-bearing.

Builds four semantically tampered variants of the vendored release
tarball whose INTERNAL SHA256SUMS is made self-consistent again, so the
outer tarball hash gate and the internal-manifest gate both pass and the
ONLY line standing between the poison and admission is the
APPROVED_IDENTITIES re-verification loop:

    raise JackalError(f"pinned identity mismatch: {rel}: {got}")

Protocol per forgery: A(pre) the poisoned package must REFUSE admission
for exactly that reason (and the genuine package must admit); B: disable
the gate line on disk (sha-checkpointed byte patch), re-import in a
fresh subprocess, and the SAME poison must be ADMITTED (proving no other
gate catches it); A(post) restore the exact original bytes (sha-verified,
stale pyc purged) and the poison must refuse again.

Writes tests/evidence/aba_recheck_gate.json.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools.py"
EVIDENCE = ROOT / "tests" / "evidence" / "aba_recheck_gate.json"
# The vendored release is split into raw byte parts (GitHub 100 MiB limit);
# forgeries are built from the exact concatenated bytes.
PKG_PARTS = (ROOT / "pkg" / "jackal-v1.7.0-macos-arm64.tar.gz.part00",
             ROOT / "pkg" / "jackal-v1.7.0-macos-arm64.tar.gz.part01")
DIRNAME = "jackal-v1.7.0-macos-arm64"

# The identity-enforcement pair under test: the admission pin loop AND
# the per-call TOCTOU pre-verification.  B disables BOTH, proving that
# with the pinned-identity enforcement suite off, tampered bytes reach
# execution — i.e. nothing else stands in the way.
GATE_PAIR = [
    (('            raise JackalError('
      'f"pinned identity mismatch: {rel}: {got}")'),
     ('            pass  # ABA-recheck-disabled'
      ' (pinned identity mismatch suppressed)')),
    ('            return _refusal("plugin-toctou-pre", rel)',
     '            pass  # ABA-recheck-disabled (toctou-pre suppressed)'),
]
IDENTITY_GATE_REASONS = {"plugin-admission-failed", "plugin-toctou-pre"}

FORGERIES = {
    "server-py-mutated": ("plugin/hermes/server.py", b"\n# poisoned\n"),
    "frontend-mutated": ("plugin/hermes/jackal_hermes", b"\n# poisoned\n"),
    "evaluator-appended": ("jackal-native", b"P"),
    "tools-json-mutated": ("plugin/hermes/tools.json", b" "),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pkg_bytes() -> bytes:
    return b"".join(p.read_bytes() for p in PKG_PARTS)


def build_forged_tarball(member_rel: str, suffix: bytes, dest: Path) -> str:
    """Rewrite one member + the internal SHA256SUMS; return new outer sha."""
    import io as _io
    with tarfile.open(fileobj=_io.BytesIO(pkg_bytes()), mode="r:gz") as tf:
        members = tf.getmembers()
        blobs = {}
        for m in members:
            if m.isreg():
                blobs[m.name] = tf.extractfile(m).read()
    target = f"{DIRNAME}/{member_rel}"
    assert target in blobs, target
    blobs[target] = blobs[target] + suffix
    sums_name = f"{DIRNAME}/SHA256SUMS"
    lines = []
    for line in blobs[sums_name].decode().splitlines():
        digest, _, name = line.partition("  ")
        rel = name.strip().lstrip("./")
        full = f"{DIRNAME}/{rel}"
        if full == target:
            digest = sha(blobs[target])
        lines.append(f"{digest}  {name.strip()}")
    blobs[sums_name] = ("\n".join(lines) + "\n").encode()
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w",
                      format=tarfile.USTAR_FORMAT) as out:
        for m in members:
            if not m.isreg():
                info = tarfile.TarInfo(m.name)
                info.type = m.type
                info.mode = m.mode
                info.mtime = m.mtime
                out.addfile(info)
                continue
            data = blobs[m.name]
            info = tarfile.TarInfo(m.name)
            info.size = len(data)
            info.mode = m.mode
            info.mtime = m.mtime
            out.addfile(info, io.BytesIO(data))
    with open(dest, "wb") as f:
        gz = gzip.GzipFile(filename="", mode="wb", fileobj=f, mtime=0,
                           compresslevel=1)
        gz.write(buf.getvalue())
        gz.close()
    return sha(dest.read_bytes())


PROBE = r"""
import json, sys
sys.path.insert(0, {root!r})
import importlib.util
spec = importlib.util.spec_from_file_location(
    "jackal_verified", {root!r} + "/__init__.py",
    submodule_search_locations=[{root!r}])
module = importlib.util.module_from_spec(spec)
sys.modules["jackal_verified"] = module
spec.loader.exec_module(module)
tools = sys.modules["jackal_verified.tools"]
from pathlib import Path
tools.PKG_TARBALL = Path({tarball!r})
tools.PKG_SHA256 = {outer_sha!r}
# Isolate the pin loop: give the probe an epoch receipt consistent with
# the (possibly forged) tarball so the earlier epoch/outer-hash gates
# pass and ONLY the APPROVED_IDENTITIES loop can catch the poison.
import json as _json, tempfile as _tempfile
_doc = _json.loads(tools.EPOCH_RECEIPT.read_text())
_doc["upstream"]["package"]["sha256"] = {outer_sha!r}
_doc["vendored"]["sha256"] = {outer_sha!r}
_tmp = Path(_tempfile.mkstemp(suffix=".json")[1])
_tmp.write_text(_json.dumps(_doc))
tools.EPOCH_RECEIPT = _tmp
out = json.loads(tools.make_handler("jackal_exact", 180, 8192)(
    {{"expression": "1+1"}}))
print(json.dumps({{"status": out.get("status"),
                   "reason": out.get("reason", ""),
                   "detail": out.get("detail", "")}}))
"""


def probe(tarball: Path, outer_sha: str) -> dict:
    code = PROBE.format(root=str(ROOT), tarball=str(tarball),
                        outer_sha=outer_sha)
    p = subprocess.run([sys.executable, "-c", code], capture_output=True,
                       text=True, timeout=600)
    lines = [l for l in (p.stdout or "").strip().splitlines() if l]
    try:
        return json.loads(lines[-1])
    except Exception:
        return {"status": "error", "reason": "probe-crashed",
                "detail": (p.stderr or "")[-300:]}


def purge_pyc() -> None:
    for p in ROOT.rglob("__pycache__"):
        for f in p.iterdir():
            f.unlink()
        p.rmdir()


def main() -> int:
    src = TOOLS.read_bytes()
    src_sha_pre = sha(src)
    text = src.decode()
    for gate, _ in GATE_PAIR:
        assert gate in text, f"gate line not found in tools.py: {gate!r}"

    genuine_blob = pkg_bytes()
    genuine_sha = sha(genuine_blob)
    rows = {}
    ok_all = True
    with tempfile.TemporaryDirectory(prefix="jackal-aba-") as td:
        genuine_path = Path(td) / "genuine.tar.gz"
        genuine_path.write_bytes(genuine_blob)
        forged = {}
        for name, (rel, suffix) in FORGERIES.items():
            dest = Path(td) / f"{name}.tar.gz"
            forged[name] = (dest, build_forged_tarball(rel, suffix, dest))

        # A(pre): genuine admits; every forgery refuses on the pin loop.
        g = probe(genuine_path, genuine_sha)
        genuine_pre = g.get("status") == "exact" or (
            g.get("status") not in ("refused", "error"))
        rows["genuine"] = {"A_pre": g}
        ok_all &= genuine_pre
        for name, (dest, outer) in forged.items():
            r = probe(dest, outer)
            a_pre_ok = (r.get("status") == "refused"
                        and r.get("reason") == "plugin-admission-failed"
                        and "pinned identity mismatch" in r.get("detail", ""))
            rows[name] = {"A_pre": r, "A_pre_refused_for_reason": a_pre_ok}
            ok_all &= a_pre_ok
            print(f"A_pre {name}: "
                  f"{'refused-for-reason' if a_pre_ok else 'UNEXPECTED'} "
                  f"{r.get('detail', '')[:80]}")

        # B: disable the identity-enforcement pair; tampered bytes must
        # now reach execution (no identity-gate refusal fires).
        mutated = text
        for gate, disabled in GATE_PAIR:
            mutated = mutated.replace(gate, disabled)
        TOOLS.write_bytes(mutated.encode())
        purge_pyc()
        src_sha_mutated = sha(TOOLS.read_bytes())
        for name, (dest, outer) in forged.items():
            r = probe(dest, outer)
            admitted = r.get("reason") not in IDENTITY_GATE_REASONS \
                and r.get("status") != "error"
            rows[name]["B"] = r
            rows[name]["B_admitted_without_gate"] = admitted
            ok_all &= admitted
            print(f"B {name}: "
                  f"{'admitted-without-gate' if admitted else 'STILL REFUSED'}"
                  f" status={r.get('status')} reason={r.get('reason', '')}")

        # A(post): restore exact bytes, purge, forgeries refuse again.
        TOOLS.write_bytes(src)
        purge_pyc()
        src_sha_post = sha(TOOLS.read_bytes())
        restore_ok = src_sha_post == src_sha_pre
        ok_all &= restore_ok
        for name, (dest, outer) in forged.items():
            r = probe(dest, outer)
            a_post_ok = (r.get("status") == "refused"
                         and "pinned identity mismatch" in r.get("detail", ""))
            rows[name]["A_post"] = r
            rows[name]["A_post_refused"] = a_post_ok
            ok_all &= a_post_ok
            print(f"A_post {name}: "
                  f"{'refused' if a_post_ok else 'UNEXPECTED'}")

    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps({
        "schema": "jackal-plugin-aba-recheck-v2",
        "gate_lines": [g.strip() for g, _ in GATE_PAIR],
        "source_hash_pre": src_sha_pre,
        "source_hash_mutated": src_sha_mutated,
        "source_hash_post": src_sha_post,
        "restore_hash_verified": restore_ok,
        "forgeries": rows,
    }, indent=2, sort_keys=True) + "\n")
    print(f"evidence={EVIDENCE}")
    print(f"VERDICT: {'PASS' if ok_all else 'FAIL'} — identity-enforcement "
          f"pair is load-bearing across {len(FORGERIES)} forgeries")
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
