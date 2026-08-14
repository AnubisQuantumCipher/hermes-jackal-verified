#!/usr/bin/env python3
"""Plugin-boundary A→B→A for the formal re-check master gate (§487 repair proof).

The 2.0.2 fix makes `verify()` re-run the proved checker on the certificate the
receipt carries and bind every self-reported field to the checker's verdict. This
harness proves that gate is LOAD-BEARING: with it disabled (but tools.py still
importable and runnable), the four exact Hermes forgeries — an ordered-but-wrong
enclosure, a changed request, an arbitrary certificate digest, and an arbitrary
request commitment — are all admitted again. Restoring the exact pre-mutation
bytes (hash-verified) makes them refuse once more.

Protocol (matches the upstream cert_aba_mutations.py M1/M2 contract):
  A(pre)  every forgery refuses, the genuine receipt verifies.
  B       disable ONE gate in-source; the SAME forgeries are admitted; a compile
          error or crash is NOT a valid B.
  A(post) restore EXACT bytes (sha-verified), purge stale pyc, forgeries refuse.

Identical verdict under `python3` and `python3 -O`. Exit nonzero on any failure.
"""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools.py"
EVIDENCE = ROOT / "tests" / "evidence" / "aba_recheck_gate.json"
GATE_LINE = "errors.extend(_recheck_formal_receipt(receipt))"
GATE_DISABLED = "pass  # ABA-recheck-disabled"

sys.path.insert(0, str(ROOT))
import tools  # noqa: E402


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def reseal(r: dict) -> dict:
    core = {k: r[k] for k in ("schema", "operation", "request", "result", "instrument")}
    r["receipt_sha256"] = hashlib.sha256(tools._canonical(core)).hexdigest()
    return r


# One genuine formal receipt, emitted by the real evaluator+checker path.
BASE = json.loads(tools.range_bound({"expression": "x^2+1", "lower": 1, "upper": 2}))["receipt"]

FORGERIES: dict[str, dict] = {}
f = copy.deepcopy(BASE); f["result"]["enclosure"] = {"lower": "0", "upper": "0"}; FORGERIES["ordered-wrong-enclosure"] = reseal(f)
f = copy.deepcopy(BASE); f["request"]["expression"] = "x^999"; FORGERIES["changed-request"] = reseal(f)
f = copy.deepcopy(BASE); f["result"]["certificate_sha256"] = "d" * 64; FORGERIES["arbitrary-cert-digest"] = reseal(f)
f = copy.deepcopy(BASE); f["result"]["request_commitment"] = "deadbeef" * 8; FORGERIES["arbitrary-request-commitment"] = reseal(f)

# A subprocess re-imports tools fresh, so an on-disk source mutation takes effect
# (and its restoration reverts) without any in-process reload subtlety.
RUNNER = (
    "import json,sys; sys.path.insert(0, sys.argv[2]); import tools; "
    "r=json.load(open(sys.argv[1])); "
    "print(json.loads(tools.verify_receipt({'receipt':r}))['verification']['valid'])"
)


def verify_valid(receipt: dict) -> bool:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(receipt, fh)
        path = fh.name
    cp = subprocess.run([sys.executable, "-c", RUNNER, path, str(ROOT)],
                        capture_output=True, text=True, timeout=3600)
    out = cp.stdout.strip().splitlines()[-1] if cp.stdout.strip() else ""
    if out not in ("True", "False"):
        raise RuntimeError(f"runner did not yield a verdict: rc={cp.returncode} out={cp.stdout!r} err={cp.stderr[-400:]!r}")
    return out == "True"


def import_ok() -> bool:
    cp = subprocess.run([sys.executable, "-c", f"import sys; sys.path.insert(0,{str(ROOT)!r}); import tools"],
                        capture_output=True, text=True)
    return cp.returncode == 0


def main() -> int:
    orig = TOOLS.read_bytes()
    orig_hash = sha(orig)
    row: dict = {"gate": "formal-recheck-master", "source_hash_pre": orig_hash,
                 "forgeries": {}, "genuine": {}}
    fails: list[str] = []

    # A(pre): genuine verifies; every forgery refuses.
    row["genuine"]["A_pre_valid"] = verify_valid(BASE)
    if not row["genuine"]["A_pre_valid"]:
        fails.append("genuine receipt did not verify in A(pre)")
    for name, forgery in FORGERIES.items():
        v = verify_valid(forgery)
        row["forgeries"].setdefault(name, {})["A_pre_valid"] = v
        if v:
            fails.append(f"{name}: admitted in A(pre)")

    # B: disable the master gate in-source; forgeries must be admitted.
    if GATE_LINE not in orig.decode():
        fails.append("gate line not found in tools.py")
    else:
        mutated = orig.decode().replace(GATE_LINE, GATE_DISABLED, 1).encode()
        TOOLS.write_bytes(mutated)
        row["source_hash_mutated"] = sha(TOOLS.read_bytes())
        try:
            row["B_import_ok"] = import_ok()
            if not row["B_import_ok"]:
                fails.append("B invalid: tools.py did not import after mutation")
            else:
                for name, forgery in FORGERIES.items():
                    v = verify_valid(forgery)
                    row["forgeries"][name]["B_valid_admitted"] = v
                    if not v:
                        fails.append(f"{name}: NOT admitted in B (gate not solely load-bearing)")
        finally:
            # A(post): restore exact bytes, purge stale pyc.
            TOOLS.write_bytes(orig)
            for pyc in ROOT.glob("__pycache__/tools*.pyc"):
                pyc.unlink()

    row["source_hash_post"] = sha(TOOLS.read_bytes())
    row["restore_hash_verified"] = (row["source_hash_post"] == orig_hash)
    if not row["restore_hash_verified"]:
        fails.append("tools.py not restored to pre-mutation bytes")

    # A(post): forgeries refuse again; genuine still verifies.
    row["genuine"]["A_post_valid"] = verify_valid(BASE)
    if not row["genuine"]["A_post_valid"]:
        fails.append("genuine receipt did not verify in A(post)")
    for name, forgery in FORGERIES.items():
        v = verify_valid(forgery)
        row["forgeries"][name]["A_post_valid"] = v
        if v:
            fails.append(f"{name}: admitted in A(post)")

    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(json.dumps(row, indent=2, sort_keys=True) + "\n")

    print(f"gate={row['gate']} restore_hash_verified={row['restore_hash_verified']} B_import_ok={row.get('B_import_ok')}")
    for name, d in row["forgeries"].items():
        print(f"  {name}: A_pre={d.get('A_pre_valid')} B_admitted={d.get('B_valid_admitted')} A_post={d.get('A_post_valid')}")
    print(f"evidence={EVIDENCE.relative_to(ROOT)} sha256={sha(EVIDENCE.read_bytes())}")
    if fails:
        for m in fails:
            print("  FAIL", m, file=sys.stderr)
        print("VERDICT: FAIL")
        return 1
    print("VERDICT: PASS — master re-check gate is load-bearing (A→B→A on 4 forgeries), restored by hash")
    return 0


if __name__ == "__main__":
    sys.exit(main())
