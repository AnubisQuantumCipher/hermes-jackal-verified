"""Fail-closed JACKAL subprocess adapter and receipt validator (v3.0.0).

Ten typed tools threading every call through the pinned v1.4.2 evaluator,
Lean-proved range checker (`jackal_cert_check`), zero-libm Gaussian checker
(`jackal_gaussian_check`), and the pure-Q sqrt_rat / exp_rat producers.

The formal lane emits canonical ``jackal-formal-receipt-v1`` envelopes with
a ``variant`` discriminator (``range`` | ``gaussian`` | ``sqrt_rat`` |
``exp_rat``) that ``jackal_verify_receipt`` re-executes end to end: the
pinned checker is re-run on the embedded certificate and every outer
Hermes field is bound to the checker's verdict.  A recomputed outer
digest cannot forge a formal claim.
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Mapping

PLUGIN_ROOT = Path(__file__).resolve().parent
SCHEMA = "jackal-hermes-receipt-v2"

# v1.4.2 pinned identities.  The evaluator (jackal-native) is byte-identical
# to v1.2.0/v1.3.0/v1.4.0/v1.4.1; the range checker is repinned to include
# the sqrt_rat + exp_rat arms.
APPROVED_SHA256 = "820c0722e46a0800115c404ea1c9251c6f72fe8c6897bdabe437f342f9310b6c"
APPROVED_CHECKER_SHA256 = "b567b8a94ce7acd49ecaa807d86a5bb66d695fb0ce4fea2eb84f0073425984d7"
APPROVED_GAUSSIAN_CHECKER_SHA256 = "42d3f3e74b90062c958baeda9ddf9ddd6f82ef3f8e4dd2b9ade5017239fe7a77"
APPROVED_GAUSSIAN_PRODUCER_SHA256 = "20c24622b786940a8e82198f2364fb7593e761902fa0736289b179642f1e4306"
APPROVED_SQRT_RAT_PRODUCER_SHA256 = "4bc95c331430d2350facfb19da9aba483ab7b3698754e7af2e5deb797e097926"
APPROVED_EXP_RAT_PRODUCER_SHA256 = "ccbc48633bd3980613413399d552321eaa67b15bd101643e53b0dd5f10a37918"

# The five formal tools bind through the same Lean theorems the upstream
# CertRequest.lean / GaussianCert.lean prove.  A receipt whose theorem id
# doesn't match the variant is refused.
FORMAL_THEOREM = "request_bound_certified_release"
GAUSSIAN_THEOREM = "gaussian_integral_check_sound"

RELEASE_EPOCH = "v1.4.2"

# The evaluator + proved checker + Gaussian checker + sqrt_rat / exp_rat
# producers ship inside ONE vendored, hash-verified upstream v1.4.2 release
# tarball.  It is admitted -- SHA + manifest + arch + mode -- into a private
# snapshot before any binary is executed.  No LFS, no network fetch, no
# stripping; a plain git clone carries everything (offline-capable).
PKG_TARBALL = PLUGIN_ROOT / "pkg" / "jackal-v1.4.2-macos-arm64.tar.gz"
PKG_SHA256 = "30b1a7441cdd9c1b0f24ac6d187608d3235f1ced6c57469dc1b1f697f475b1a0"
PKG_DIRNAME = "jackal-v1.4.2-macos-arm64"

MAX_OUTPUT_BYTES = 2_000_000
MAX_INTEGER_DIGITS = 100_000
MAX_EXPONENT = 1_000_000
MAX_CERT_BYTES = 1 << 20

OPERATIONS = {
    "jackal_exact": {"exact", "refused", "indeterminate"},
    "jackal_evaluate": {"estimated", "refused", "indeterminate"},
    "jackal_differentiate": {"checked", "refused", "indeterminate"},
    "jackal_integrate": {"estimated", "bounded", "refused", "indeterminate"},
    "jackal_range_bound": {"formal-bounded", "refused", "indeterminate"},
    "jackal_gaussian_integral": {"formal-bounded", "refused", "indeterminate"},
    "jackal_sqrt_rat_bound": {"formal-bounded", "refused", "indeterminate"},
    "jackal_exp_rat_bound": {"formal-bounded", "refused", "indeterminate"},
    "jackal_claim_card": {"model-based", "refused", "indeterminate"},
    "jackal_verify_receipt": {"verified", "refused", "indeterminate"},
}


class JackalError(RuntimeError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    ).encode()


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _plugin_manifest_sha256() -> str:
    manifest = PLUGIN_ROOT / "MANIFEST.json"
    if not manifest.is_file():
        raise JackalError("plugin MANIFEST.json is missing")
    return _sha(manifest)


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise JackalError(f"{name} must be a finite number")
    try:
        out = float(value)
    except (TypeError, ValueError) as exc:
        raise JackalError(f"{name} must be a finite number") from exc
    if not math.isfinite(out):
        raise JackalError(f"{name} must be a finite number")
    return out


def _number(value: Any) -> str:
    return format(_finite(value, "numeric argument"), ".17g")


def _expression(value: Any, max_chars: int = 8192) -> str:
    if not isinstance(value, str):
        raise JackalError("expression must be text")
    text = value.strip()
    if not text:
        raise JackalError("expression must not be empty")
    if len(text) > max_chars:
        raise JackalError(f"expression exceeds {max_chars} characters")
    if any(ord(ch) < 32 for ch in text):
        raise JackalError("expression contains control characters")
    return text


_ADMITTED: dict[str, Any] | None = None


def _safe_extract(tar_path: Path, dest: Path) -> None:
    """Extract with path-traversal / special-file protection."""
    import posixpath
    import tarfile
    dest = dest.resolve()

    def _is_appledouble(name: str) -> bool:
        base = posixpath.basename(name.rstrip("/"))
        return base.startswith("._") or name.split("/", 1)[0] == "__MACOSX"

    with tarfile.open(tar_path, "r:gz") as tf:
        keep = []
        for m in tf.getmembers():
            if _is_appledouble(m.name):
                continue
            if not (m.isreg() or m.isdir()):
                raise JackalError(f"package contains a non-regular member: {m.name}")
            target = (dest / m.name).resolve()
            if dest != target and dest not in target.parents:
                raise JackalError(f"package member escapes extraction root: {m.name}")
            keep.append(m)
        tf.extractall(dest, members=keep)  # noqa: S202 — members validated above


def _verify_manifest(pkg: Path) -> None:
    """Every file in SHA256SUMS must exist and match; no unlisted shipped file."""
    sums = pkg / "SHA256SUMS"
    if not sums.is_file():
        raise JackalError("package SHA256SUMS is missing")
    listed: dict[str, str] = {}
    for line in sums.read_text().splitlines():
        if not line.strip():
            continue
        digest, _, name = line.partition("  ")
        listed[name.lstrip("./")] = digest
    for name, digest in listed.items():
        f = pkg / name
        if not f.is_file():
            raise JackalError(f"package manifest lists a missing file: {name}")
        if _sha(f) != digest:
            raise JackalError(f"package file hash mismatch: {name}")
    present = {str(p.relative_to(pkg)) for p in pkg.rglob("*") if p.is_file()}
    extra = present - set(listed) - {"SHA256SUMS"}
    if extra:
        raise JackalError(f"package contains unlisted files: {sorted(extra)}")


def _arch_ok(path: Path) -> bool:
    """Mach-O arm64 executable check."""
    with path.open("rb") as f:
        head = f.read(8)
    if len(head) < 8:
        return False
    magic = head[:4]
    cputype = int.from_bytes(head[4:8], "little")
    return (
        magic in (b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe")
        and (cputype & 0x0100000C) == 0x0100000C
    )


def _admit_package() -> dict[str, Any]:
    """Admit the vendored release tarball into a private snapshot once."""
    global _ADMITTED
    if _ADMITTED is not None:
        ev = Path(_ADMITTED["evaluator"])
        ck = Path(_ADMITTED["checker"])
        gck = Path(_ADMITTED["gaussian_checker"])
        if (ev.is_file() and ck.is_file() and gck.is_file()
                and _sha(ev) == APPROVED_SHA256
                and _sha(ck) == APPROVED_CHECKER_SHA256
                and _sha(gck) == APPROVED_GAUSSIAN_CHECKER_SHA256):
            return _ADMITTED
    if not PKG_TARBALL.is_file():
        raise JackalError("vendored release package is missing")
    if _sha(PKG_TARBALL) != PKG_SHA256:
        raise JackalError("release package tarball identity mismatch")
    snap = Path(tempfile.mkdtemp(prefix="jackal-admitted-"))
    os.chmod(snap, 0o700)
    _safe_extract(PKG_TARBALL, snap)
    pkg = snap / PKG_DIRNAME
    if not pkg.is_dir():
        raise JackalError("release package layout unexpected")
    _verify_manifest(pkg)
    ev = pkg / "jackal-native"
    ck = pkg / "jackal_cert_check"
    gck = pkg / "jackal_gaussian_check"
    gprod = pkg / "gaussian_certificate.py"
    sprod = pkg / "sqrt_rat_producer.py"
    eprod = pkg / "exp_rat_producer.py"
    for expected, path in (
        (APPROVED_SHA256, ev), (APPROVED_CHECKER_SHA256, ck),
        (APPROVED_GAUSSIAN_CHECKER_SHA256, gck),
        (APPROVED_GAUSSIAN_PRODUCER_SHA256, gprod),
        (APPROVED_SQRT_RAT_PRODUCER_SHA256, sprod),
        (APPROVED_EXP_RAT_PRODUCER_SHA256, eprod),
    ):
        if _sha(path) != expected:
            raise JackalError(f"admitted binary identity mismatch: {path.name} = {_sha(path)}")
    for binary in (ev, ck, gck):
        if not _arch_ok(binary):
            raise JackalError(f"admitted binary is not Mach-O arm64: {binary.name}")
    for path in (ev, ck, gck):
        path.chmod(0o500)
    for path in (gprod, sprod, eprod):
        path.chmod(0o400)
    _ADMITTED = {
        "snapshot": str(snap), "package": str(pkg),
        "evaluator": str(ev), "checker": str(ck),
        "gaussian_checker": str(gck), "gaussian_producer": str(gprod),
        "sqrt_rat_producer": str(sprod), "exp_rat_producer": str(eprod),
        "range_proof_identity": str(pkg / "range_proof_identity.json"),
        "gaussian_proof_identity": str(pkg / "gaussian_proof_identity.json"),
        "inventory": str(pkg / "formal_coverage_inventory.json"),
        "evaluator_sha256": APPROVED_SHA256,
        "checker_sha256": APPROVED_CHECKER_SHA256,
        "gaussian_checker_sha256": APPROVED_GAUSSIAN_CHECKER_SHA256,
        "gaussian_producer_sha256": APPROVED_GAUSSIAN_PRODUCER_SHA256,
        "sqrt_rat_producer_sha256": APPROVED_SQRT_RAT_PRODUCER_SHA256,
        "exp_rat_producer_sha256": APPROVED_EXP_RAT_PRODUCER_SHA256,
    }
    return _ADMITTED


def _binary_identity() -> dict[str, Any]:
    adm = _admit_package()
    ev = Path(adm["evaluator"])
    return {"name": "jackal-native", "sha256": adm["evaluator_sha256"], "size": ev.stat().st_size}


def _invoke(argv: list[str], timeout: int = 180) -> dict[str, Any]:
    adm = _admit_package()
    instrument = _binary_identity()
    started = time.time()
    snapshot = Path(adm["evaluator"])
    with tempfile.TemporaryDirectory(prefix="jackal-verified-") as tmp:
        if _sha(snapshot) != instrument["sha256"]:
            raise JackalError("JACKAL executable changed before execution")
        try:
            proc = subprocess.run(
                [str(snapshot), *argv], text=True, capture_output=True,
                timeout=max(1, min(int(timeout), 3600)),
                shell=False, stdin=subprocess.DEVNULL, cwd=tmp,
                env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "HOME": tmp, "LANG": "C.UTF-8"},
            )
        except subprocess.TimeoutExpired as exc:
            return {"released": False, "status": "indeterminate",
                    "reason": "execution-timeout", "detail": str(exc),
                    "instrument": instrument}
        if _sha(snapshot) != instrument["sha256"]:
            raise JackalError("JACKAL execution snapshot changed during execution")
    if len(proc.stdout.encode()) > MAX_OUTPUT_BYTES or len(proc.stderr.encode()) > MAX_OUTPUT_BYTES:
        raise JackalError("JACKAL output exceeded the adapter limit")
    if _sha(snapshot) != instrument["sha256"]:
        raise JackalError("JACKAL executable changed during execution")
    if proc.returncode != 0:
        meaningful = [line.strip() for line in proc.stderr.splitlines()
                      if "panicked at" not in line and not line.startswith("note:") and line.strip()]
        reason = (meaningful[-1].removeprefix("ANUBIS_PANIC: ")
                  if meaningful else "JACKAL refused without a diagnostic")
        return {"released": False, "status": "refused", "reason": reason,
                "exit_code": proc.returncode, "instrument": instrument,
                "duration_ms": round((time.time() - started) * 1000, 3)}
    return {"released": True, "exit_code": 0, "stdout": proc.stdout.strip(),
            "instrument": instrument,
            "duration_ms": round((time.time() - started) * 1000, 3)}


def _fields(line: str) -> dict[str, str]:
    return {k: v for k, v in re.findall(r"(?:^|\s)([a-zA-Z][a-zA-Z0-9_.-]*)=([^\s]+)", line)}


def _enclosure(text: str, key: str) -> tuple[float, float, str, str]:
    match = re.search(re.escape(key) + r"=\[([^,\]]+),([^\]]+)\]", text)
    if not match:
        raise JackalError(f"successful JACKAL output omitted {key}")
    lo_s, hi_s = match.group(1), match.group(2)
    lo, hi = _finite(lo_s, "lower enclosure"), _finite(hi_s, "upper enclosure")
    if lo > hi:
        raise JackalError("JACKAL returned a reversed enclosure")
    return lo, hi, lo_s, hi_s


def _receipt(operation: str, request: Mapping[str, Any],
             result: Mapping[str, Any], instrument: Mapping[str, Any]) -> dict[str, Any]:
    core = {"schema": SCHEMA, "operation": operation,
            "request": dict(request), "result": dict(result),
            "instrument": dict(instrument)}
    core["receipt_sha256"] = hashlib.sha256(_canonical(core)).hexdigest()
    return core


def _error(operation: str, exc: BaseException) -> str:
    return json.dumps({"success": False, "operation": operation,
                       "error": str(exc), "error_type": exc.__class__.__name__},
                      sort_keys=True)


def _finish(operation: str, request: dict[str, Any], raw: dict[str, Any],
            result: dict[str, Any] | None = None) -> str:
    if not raw["released"]:
        receipt = _receipt(operation, request,
                           {k: v for k, v in raw.items() if k != "instrument"},
                           raw["instrument"])
        return json.dumps({"success": True, "receipt": receipt},
                          ensure_ascii=False, sort_keys=True)
    receipt = _receipt(operation, request, result or {}, raw["instrument"])
    return json.dumps({"success": True, "receipt": receipt},
                      ensure_ascii=False, sort_keys=True)


# ---------------------------------------------------------------------------
# Weaker + exact lanes
# ---------------------------------------------------------------------------

def exact(args: Mapping[str, Any], timeout: int = 180, max_chars: int = 8192) -> str:
    op = "jackal_exact"
    try:
        mode = str(args.get("mode", ""))
        if mode == "rational":
            expr = _expression(args.get("expression"), max_chars)
            request = {"mode": mode, "expression": expr}
            argv = ["rat", expr]
        elif mode in {"big_add", "big_multiply", "big_power"}:
            a, b = str(args.get("a", "")), str(args.get("b", ""))
            if not a.isdigit() or not b.isdigit():
                raise JackalError("a and b must contain decimal digits only")
            if len(a) > MAX_INTEGER_DIGITS or len(b) > MAX_INTEGER_DIGITS:
                raise JackalError("integer operand exceeds the adapter digit limit")
            if mode == "big_power" and int(b) > MAX_EXPONENT:
                raise JackalError("exponent exceeds the adapter limit")
            command = {"big_add": "big-add", "big_multiply": "big-mul", "big_power": "big-pow"}[mode]
            request = {"mode": mode, "a": a, "b": b}
            argv = [command, a, b]
        elif mode in {"factorial", "binomial"}:
            n = args.get("n"); r = args.get("r")
            if not isinstance(n, int) or isinstance(n, bool) or not 0 <= n <= 10000:
                raise JackalError("n must be an integer in 0..10000")
            if mode == "factorial":
                request = {"mode": mode, "n": n}; argv = ["big-fact", str(n)]
            else:
                if not isinstance(r, int) or isinstance(r, bool) or not 0 <= r <= n:
                    raise JackalError("r must be an integer in 0..n")
                request = {"mode": mode, "n": n, "r": r}
                argv = ["big-ncr", str(n), str(r)]
        else:
            raise JackalError("unsupported exact mode")
        raw = _invoke(argv, timeout)
        if not raw["released"]:
            return _finish(op, request, raw)
        if mode == "rational":
            fields = _fields(raw["stdout"])
            required = {"status", "parsed", "exact", "approx"}
            if not required <= fields.keys() or fields["status"] != "exact":
                raise JackalError("malformed exact-rational output")
            result = {"status": "exact", "parsed": fields["parsed"],
                      "exact": fields["exact"], "approx": fields["approx"],
                      "non_claims": ["approx is IEEE-f64, not the exact result"]}
        else:
            value = raw["stdout"]
            if not value.isdigit():
                raise JackalError("malformed exact-integer output")
            result = {"status": "exact", "value": value, "digits": len(value)}
        return _finish(op, request, raw, result)
    except Exception as exc:
        return _error(op, exc)


def evaluate(args: Mapping[str, Any], timeout: int = 180, max_chars: int = 8192) -> str:
    op = "jackal_evaluate"
    try:
        expr = _expression(args.get("expression"), max_chars)
        request = {"expression": expr}
        raw = _invoke(["eval", expr], timeout)
        if not raw["released"]:
            return _finish(op, request, raw)
        value = _finite(raw["stdout"], "JACKAL result")
        return _finish(op, request, raw,
                       {"status": "estimated", "value": value, "rendered": raw["stdout"],
                        "assurance": "IEEE-f64 evaluation",
                        "non_claims": ["not exact", "not a certified error bound"]})
    except Exception as exc:
        return _error(op, exc)


def differentiate(args: Mapping[str, Any], timeout: int = 180, max_chars: int = 8192) -> str:
    op = "jackal_differentiate"
    try:
        expr = _expression(args.get("expression"), max_chars)
        request = {"expression": expr}
        raw = _invoke(["diff", expr], timeout)
        if not raw["released"]:
            return _finish(op, request, raw)
        lines = raw["stdout"].splitlines()
        if len(lines) < 2 or " = " not in lines[0]:
            raise JackalError("malformed derivative output")
        fields = _fields(lines[1])
        if fields.get("status") != "checked":
            raise JackalError("derivative was not labeled checked")
        result = {
            "status": "checked",
            "derivative": lines[0].split(" = ", 1)[1],
            "input_echo": lines[0].split(" = ", 1)[0],
            "check": {"points": int(fields["points"]),
                      "max_relative_deviation": _finite(fields["max-rel-dev"], "deviation"),
                      "tolerance": _finite(fields["tolerance"], "tolerance")},
            "assurance": fields.get("assurance"),
            "domain_caveat": fields.get("domain-caveat"),
            "non_claims": ["numeric sample check is not a proof of symbolic identity"],
        }
        return _finish(op, request, raw, result)
    except Exception as exc:
        return _error(op, exc)


def integrate(args: Mapping[str, Any], timeout: int = 180, max_chars: int = 8192) -> str:
    op = "jackal_integrate"
    try:
        expr = _expression(args.get("expression"), max_chars)
        lower = _finite(args.get("lower"), "lower")
        upper = _finite(args.get("upper"), "upper")
        if not lower < upper:
            raise JackalError("lower must be less than upper")
        assurance = str(args.get("assurance", ""))
        request = {"expression": expr, "lower": lower, "upper": upper,
                   "assurance": assurance}
        if assurance == "fast_estimate":
            panels = args.get("panels", 200)
            if (not isinstance(panels, int) or isinstance(panels, bool)
                    or panels < 2 or panels > 1000000 or panels % 2):
                raise JackalError("panels must be an even integer in 2..1000000")
            request["panels"] = panels
            argv = ["integrate", expr, _number(lower), _number(upper), str(panels)]
        elif assurance in {"adaptive_estimate", "bounded"}:
            tol = _finite(args.get("tolerance"), "tolerance")
            if tol <= 0:
                raise JackalError("tolerance must be positive")
            request["tolerance"] = tol
            command = "integrate-adaptive" if assurance == "adaptive_estimate" else "integrate-bound"
            argv = [command, expr, _number(lower), _number(upper), _number(tol)]
        else:
            raise JackalError("assurance must be fast_estimate, adaptive_estimate, or bounded")
        raw = _invoke(argv, timeout)
        if not raw["released"]:
            return _finish(op, request, raw)
        fields = _fields(raw["stdout"])
        if assurance == "bounded":
            if fields.get("status") != "bounded":
                raise JackalError("bounded request did not return bounded status")
            lo, hi, lo_s, hi_s = _enclosure(raw["stdout"], "integral-enclosure")
            width = hi - lo
            if width > request["tolerance"] * (1 + 1e-9):
                raise JackalError("enclosure exceeds requested tolerance")
            result = {"status": "bounded",
                      "enclosure": {"lower": lo_s, "upper": hi_s, "width": width},
                      "method": fields.get("method"), "mode": fields.get("mode"),
                      "assurance": fields.get("assurance"),
                      "non_claims": ["not an exact value",
                                     "conditional on the stated floating-point/libm model"]}
        else:
            if fields.get("status") != "estimated":
                raise JackalError("estimate request did not return estimated status")
            result = {"status": "estimated",
                      "value": _finite(fields.get("integral"), "integral"),
                      "method": fields.get("method"),
                      "assurance": fields.get("assurance"),
                      "error_estimate": fields.get("richardson-error-estimate")
                                        or fields.get("achieved-error-estimate"),
                      "non_claims": ["error estimate is not a mathematical bound"]}
        return _finish(op, request, raw, result)
    except Exception as exc:
        return _error(op, exc)


# ---------------------------------------------------------------------------
# Formal lanes (all four variants)
# ---------------------------------------------------------------------------

def _ensure_formal_modules() -> None:
    fdir = str(PLUGIN_ROOT / "jackal_formal")
    if fdir not in sys.path:
        sys.path.insert(0, fdir)


def _formal_instrument(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """Build the outer Hermes instrument block from a nested formal receipt."""
    identities = receipt.get("identities", {})
    return {
        "evaluator": {"name": "jackal-native"
                                if receipt.get("variant") in (None, "range")
                                else _producer_display_name(receipt.get("variant")),
                      "sha256": identities.get("evaluator_sha256")},
        "checker": {"name": "jackal_gaussian_check"
                             if receipt.get("variant") == "gaussian"
                             else "jackal_cert_check",
                    "sha256": identities.get("checker_sha256")},
        "plugin": {"name": "jackal-verified",
                   "sha256": identities.get("plugin_sha256")},
    }


def _producer_display_name(variant: str | None) -> str:
    return {
        "gaussian": "gaussian_certificate.py",
        "sqrt_rat": "sqrt_rat_producer.py",
        "exp_rat": "exp_rat_producer.py",
    }.get(variant or "", "producer")


def _range_release_bound(expr: str, lower: str, upper: str,
                         timeout: int) -> dict[str, Any]:
    """Range-lane release: engine emits cert -> checker ACCEPT -> receipt."""
    _ensure_formal_modules()
    import release_validate as rv  # noqa: E402
    adm = _admit_package()
    plugin_sha = _plugin_manifest_sha256()
    with tempfile.TemporaryDirectory(prefix="jackal-formal-") as tmp:
        wd = Path(tmp) / "run"; wd.mkdir(mode=0o700)
        formal_path = Path(tmp) / "formal-receipt.json"
        try:
            receipt = rv.validate_release(
                expr=expr, lo=lower, hi=upper,
                evaluator=adm["evaluator"], checker=adm["checker"],
                expected_evaluator=APPROVED_SHA256,
                expected_checker=APPROVED_CHECKER_SHA256,
                workdir=str(wd), formal_receipt_path=str(formal_path),
                plugin_sha256=plugin_sha, release_epoch=RELEASE_EPOCH,
            )
        except rv.ReleaseRefusal as r:
            raise JackalError(f"formal-release-refused:{r.cls}") from r
        formal_receipt = json.loads(formal_path.read_text())
    if receipt.get("status") != "formal-bounded":
        raise JackalError("formal path did not yield formal-bounded")
    receipt["formal_receipt"] = formal_receipt
    return receipt


def _gaussian_release_bound(expr: str, lower: str, upper: str, tolerance: str,
                            timeout: int) -> dict[str, Any]:
    """Gaussian lane: gaussian_certificate.py -> jackal_gaussian_check ACCEPT."""
    _ensure_formal_modules()
    import gaussian_release as gr  # noqa: E402
    import argparse
    adm = _admit_package()
    plugin_sha = _plugin_manifest_sha256()
    with tempfile.TemporaryDirectory(prefix="jackal-gaussian-") as tmp:
        receipt_path = Path(tmp) / "gaussian-receipt.json"
        ns = argparse.Namespace(
            expression=expr, lower=lower, upper=upper, tolerance=tolerance,
            producer=adm["gaussian_producer"], checker=adm["gaussian_checker"],
            expected_producer=APPROVED_GAUSSIAN_PRODUCER_SHA256,
            expected_checker=APPROVED_GAUSSIAN_CHECKER_SHA256,
            receipt=str(receipt_path),
            plugin_sha256=plugin_sha, release_epoch=RELEASE_EPOCH,
            timeout=max(1, min(int(timeout), 3600)),
        )
        try:
            gr.release(ns)
        except gr.Refusal as r:
            raise JackalError(f"gaussian-release-refused:{r.cls}") from r
        formal_receipt = json.loads(receipt_path.read_text())
    result_block = formal_receipt.get("result", {})
    return {
        "status": "formal-bounded",
        "certified_enclosure": [result_block.get("enclosure_lo"),
                                result_block.get("enclosure_hi")],
        "input": [formal_receipt.get("request", {}).get("canonical_lo"),
                  formal_receipt.get("request", {}).get("canonical_hi")],
        "canonical_tolerance": formal_receipt.get("request", {}).get("canonical_tolerance"),
        "expr_commitment": formal_receipt.get("certificate", {}).get("bytes_b64"),
        "request_commitment": formal_receipt.get("request", {}).get("request_commitment_b64"),
        "certificate_sha256": formal_receipt.get("certificate", {}).get("sha256"),
        "cert_status": result_block.get("cert_status"),
        "operators": formal_receipt.get("fragment", {}).get("expression_operators"),
        "assurance": "proof-carrying-certificate(gaussian;checker-accepted;NO-libm-TCB)",
        "formal_receipt": formal_receipt,
    }


def _variant_release_bound(variant: str, expr: str, lower: str, upper: str,
                           timeout: int) -> dict[str, Any]:
    """Pure-Q variant lanes (sqrt_rat / exp_rat): run producer -> checker -> emit envelope."""
    _ensure_formal_modules()
    import formal_receipt as fr  # noqa: E402
    adm = _admit_package()
    plugin_sha = _plugin_manifest_sha256()
    producer_key = f"{variant}_producer"
    admitted_expr = {"sqrt_rat": "sqrt(x)", "exp_rat": "exp(x)"}[variant]
    if expr.replace(" ", "") != admitted_expr:
        raise JackalError(f"plugin-fragment: {variant} admits ONLY `{admitted_expr}`")

    producer_path = Path(adm[producer_key])
    producer_sha = adm[f"{producer_key}_sha256"]
    checker_path = Path(adm["checker"])
    checker_sha = adm["checker_sha256"]

    if _sha(producer_path) != producer_sha:
        raise JackalError(f"producer-identity: {variant} producer bytes changed pre-invoke")
    if _sha(checker_path) != checker_sha:
        raise JackalError("checker-identity: cert-check bytes changed pre-invoke")

    with tempfile.TemporaryDirectory(prefix=f"jackal-{variant}-") as tmp:
        cert_path = Path(tmp) / f"{variant}.cert"
        proc = subprocess.run(
            [sys.executable, "-I", "-S", "-B", str(producer_path), "emit",
             "--expression", expr, "--lower", lower, "--upper", upper],
            capture_output=True, timeout=max(1, min(int(timeout), 3600)),
            stdin=subprocess.DEVNULL, cwd=tmp,
            env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
        )
        if _sha(producer_path) != producer_sha:
            raise JackalError("producer-toctou: producer bytes changed across call")
        if proc.returncode != 0:
            raw = (proc.stderr.decode("utf-8", "replace").strip()
                   or proc.stdout.decode("utf-8", "replace").strip())
            reason = raw.split("\n")[0].removeprefix("REFUSE ")[:300]
            raise JackalError(f"producer-refused:{reason}")
        cert_bytes = proc.stdout
        if len(cert_bytes) > MAX_CERT_BYTES:
            raise JackalError("certificate exceeds adapter limit")
        cert_path.write_bytes(cert_bytes)
        cproc = subprocess.run(
            [str(checker_path), str(cert_path), "range-bound-cert",
             expr, lower, upper],
            capture_output=True, text=True,
            timeout=max(1, min(int(timeout), 3600)),
            stdin=subprocess.DEVNULL, cwd=tmp,
            env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
        )
        if _sha(checker_path) != checker_sha:
            raise JackalError("checker-toctou: checker bytes changed across call")
        if cproc.returncode != 0 or "ACCEPT" not in cproc.stdout:
            detail = ((cproc.stdout + cproc.stderr).strip().split("\n")[0])[:300]
            raise JackalError(f"checker-rejected:{detail}")

    hdr = fr._parse_cert_header(cert_bytes)
    encl_lo, encl_hi = hdr.get("output", "").split(" ", 1)
    proof = fr.load_proof_identity_binding(Path(adm["range_proof_identity"]))
    inv_bytes = Path(adm["inventory"]).read_bytes()
    inv_sha = hashlib.sha256(inv_bytes).hexdigest()
    receipt = fr.build_variant_formal_receipt(
        variant=variant, release_epoch=RELEASE_EPOCH,
        request={"command": "range-bound-cert", "expression": expr,
                 "input_lo": lower, "input_hi": upper},
        enclosure=(encl_lo, encl_hi),
        cert_bytes=cert_bytes,
        producer_sha256=producer_sha, checker_sha256=checker_sha,
        canonical_lo=fr.canonical_rat(lower),
        canonical_hi=fr.canonical_rat(upper),
        request_commitment_b64=fr.request_commitment_b64(
            "range-bound-cert", expr, lower, upper),
        coverage_inventory_sha256=inv_sha,
        proof_identity=proof, plugin_sha256=plugin_sha,
    )
    return {
        "status": "formal-bounded",
        "certified_enclosure": [encl_lo, encl_hi],
        "input": [fr.canonical_rat(lower), fr.canonical_rat(upper)],
        "expr_commitment": receipt["certificate"]["sexp"],
        "request_commitment": receipt["request"]["request_commitment_b64"],
        "certificate_sha256": receipt["certificate"]["sha256"],
        "cert_status": receipt["result"]["cert_status"],
        "operators": receipt["fragment"]["expression_operators"],
        "assurance": receipt["assumptions"][1],  # NO-libm disclosure line
        "formal_receipt": receipt,
    }


def _formal_result_from_receipt(rr: dict[str, Any], variant: str,
                                theorem: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Assemble the outer Hermes result + instrument for a formal variant."""
    fr = rr["formal_receipt"]
    identities = fr.get("identities", {})
    non_claims_common = [
        "checker-accepted, variant-bound enclosure of the exact semantics",
        "conditional on the recorded TCB (Lean kernel + checker build, canonical rational codec)",
        "not universal correctness; not an exact value",
    ]
    non_claims = {
        "range": non_claims_common + ["ModelTCB.const (libm <= 2ulp)"],
        "gaussian": non_claims_common + ["gaussian-exp-square family only"],
        "sqrt_rat": non_claims_common + ["NO libm on the proof-decision path; sqrt(x) only"],
        "exp_rat": non_claims_common + ["NO libm on the proof-decision path; exp(x) on [lo, hi] with lo >= 0 only"],
    }[variant]
    instrument_name = {
        "range": "jackal-native",
        "gaussian": "gaussian_certificate.py",
        "sqrt_rat": "sqrt_rat_producer.py",
        "exp_rat": "exp_rat_producer.py",
    }[variant]
    checker_name = "jackal_gaussian_check" if variant == "gaussian" else "jackal_cert_check"
    result = {
        "status": "formal-bounded",
        "variant": variant,
        "enclosure": {"lower": rr["certified_enclosure"][0],
                      "upper": rr["certified_enclosure"][1]},
        "input": {"lower": rr["input"][0], "upper": rr["input"][1]},
        "expr_commitment": rr["expr_commitment"],
        "request_commitment": rr["request_commitment"],
        "certificate_sha256": rr["certificate_sha256"],
        "formal_receipt": rr["formal_receipt"],
        "cert_status": rr["cert_status"],
        "operators": sorted(rr["operators"] or []),
        "theorem": theorem,
        "assurance": rr.get("assurance"),
        "non_claims": non_claims,
    }
    if variant == "gaussian":
        result["tolerance"] = rr.get("canonical_tolerance")
    instrument = {
        "evaluator": {"name": instrument_name,
                      "sha256": identities.get("evaluator_sha256")
                                or identities.get("producer_sha256")},
        "checker": {"name": checker_name,
                    "sha256": identities.get("checker_sha256")},
        "plugin": {"name": "jackal-verified",
                   "sha256": identities.get("plugin_sha256")},
    }
    return result, instrument


def range_bound(args: Mapping[str, Any], timeout: int = 180, max_chars: int = 8192) -> str:
    """Formal range-bound release (variant=range) or refuse."""
    op = "jackal_range_bound"
    try:
        expr = _expression(args.get("expression"), max_chars)
        lower = _finite(args.get("lower"), "lower")
        upper = _finite(args.get("upper"), "upper")
        if not lower < upper:
            raise JackalError("lower must be less than upper")
        lo_s, hi_s = _number(lower), _number(upper)
        request = {"expression": expr, "lower": lo_s, "upper": hi_s,
                   "requested_assurance": "formal-bounded"}
        try:
            rr = _range_release_bound(expr, lo_s, hi_s, timeout)
        except JackalError as je:
            raw = {"released": False, "status": "refused", "reason": str(je),
                   "instrument": {"evaluator_sha256": APPROVED_SHA256,
                                  "checker_sha256": APPROVED_CHECKER_SHA256}}
            return _finish(op, request, raw)
        result, instrument = _formal_result_from_receipt(rr, "range", FORMAL_THEOREM)
        receipt = _receipt(op, request, result, instrument)
        return json.dumps({"success": True, "receipt": receipt},
                          ensure_ascii=False, sort_keys=True)
    except Exception as exc:
        return _error(op, exc)


def gaussian_integral(args: Mapping[str, Any], timeout: int = 180, max_chars: int = 8192) -> str:
    """Zero-libm Gaussian integral release (variant=gaussian) or refuse."""
    op = "jackal_gaussian_integral"
    try:
        expr = _expression(args.get("expression"), max_chars)
        lower = _finite(args.get("lower"), "lower")
        upper = _finite(args.get("upper"), "upper")
        if not lower < upper:
            raise JackalError("lower must be less than upper")
        tol_raw = args.get("tolerance")
        if isinstance(tol_raw, (int, float)) and not isinstance(tol_raw, bool):
            tolerance = _number(tol_raw)
        elif isinstance(tol_raw, str) and tol_raw:
            tolerance = tol_raw.strip()
        else:
            raise JackalError("tolerance must be a positive number or a canonical rational")
        lo_s, hi_s = _number(lower), _number(upper)
        request = {"expression": expr, "lower": lo_s, "upper": hi_s,
                   "tolerance": tolerance, "requested_assurance": "formal-bounded"}
        try:
            rr = _gaussian_release_bound(expr, lo_s, hi_s, tolerance, timeout)
        except JackalError as je:
            raw = {"released": False, "status": "refused", "reason": str(je),
                   "instrument": {"evaluator_sha256": APPROVED_GAUSSIAN_PRODUCER_SHA256,
                                  "checker_sha256": APPROVED_GAUSSIAN_CHECKER_SHA256}}
            return _finish(op, request, raw)
        result, instrument = _formal_result_from_receipt(rr, "gaussian", GAUSSIAN_THEOREM)
        receipt = _receipt(op, request, result, instrument)
        return json.dumps({"success": True, "receipt": receipt},
                          ensure_ascii=False, sort_keys=True)
    except Exception as exc:
        return _error(op, exc)


def sqrt_rat_bound(args: Mapping[str, Any], timeout: int = 180, max_chars: int = 8192) -> str:
    """Pure-Q sqrt(x) formal enclosure (variant=sqrt_rat) or refuse."""
    op = "jackal_sqrt_rat_bound"
    try:
        expr = _expression(args.get("expression"), max_chars)
        lower_raw = args.get("lower"); upper_raw = args.get("upper")
        lower = str(lower_raw) if isinstance(lower_raw, str) else _number(lower_raw)
        upper = str(upper_raw) if isinstance(upper_raw, str) else _number(upper_raw)
        request = {"expression": expr, "lower": lower, "upper": upper,
                   "requested_assurance": "formal-bounded"}
        try:
            rr = _variant_release_bound("sqrt_rat", expr, lower, upper, timeout)
        except JackalError as je:
            raw = {"released": False, "status": "refused", "reason": str(je),
                   "instrument": {"evaluator_sha256": APPROVED_SQRT_RAT_PRODUCER_SHA256,
                                  "checker_sha256": APPROVED_CHECKER_SHA256}}
            return _finish(op, request, raw)
        result, instrument = _formal_result_from_receipt(rr, "sqrt_rat", FORMAL_THEOREM)
        receipt = _receipt(op, request, result, instrument)
        return json.dumps({"success": True, "receipt": receipt},
                          ensure_ascii=False, sort_keys=True)
    except Exception as exc:
        return _error(op, exc)


def exp_rat_bound(args: Mapping[str, Any], timeout: int = 180, max_chars: int = 8192) -> str:
    """Pure-Q exp(x) formal enclosure (variant=exp_rat), lo >= 0, or refuse."""
    op = "jackal_exp_rat_bound"
    try:
        expr = _expression(args.get("expression"), max_chars)
        lower_raw = args.get("lower"); upper_raw = args.get("upper")
        lower = str(lower_raw) if isinstance(lower_raw, str) else _number(lower_raw)
        upper = str(upper_raw) if isinstance(upper_raw, str) else _number(upper_raw)
        request = {"expression": expr, "lower": lower, "upper": upper,
                   "requested_assurance": "formal-bounded"}
        try:
            rr = _variant_release_bound("exp_rat", expr, lower, upper, timeout)
        except JackalError as je:
            raw = {"released": False, "status": "refused", "reason": str(je),
                   "instrument": {"evaluator_sha256": APPROVED_EXP_RAT_PRODUCER_SHA256,
                                  "checker_sha256": APPROVED_CHECKER_SHA256}}
            return _finish(op, request, raw)
        result, instrument = _formal_result_from_receipt(rr, "exp_rat", FORMAL_THEOREM)
        receipt = _receipt(op, request, result, instrument)
        return json.dumps({"success": True, "receipt": receipt},
                          ensure_ascii=False, sort_keys=True)
    except Exception as exc:
        return _error(op, exc)


def claim_card(args: Mapping[str, Any], timeout: int = 180, max_chars: int = 8192) -> str:
    op = "jackal_claim_card"
    try:
        model = str(args.get("model", ""))
        if model != "projectile":
            raise JackalError("only the projectile model is currently supported")
        speed = _finite(args.get("speed"), "speed")
        angle = _finite(args.get("angle_degrees"), "angle_degrees")
        gravity = _finite(args.get("gravity"), "gravity")
        if speed <= 0 or gravity <= 0:
            raise JackalError("speed and gravity must be positive")
        request = {"model": model, "speed": speed,
                   "angle_degrees": angle, "gravity": gravity}
        raw = _invoke(["claim-card", model, _number(speed), _number(angle), _number(gravity)],
                      timeout)
        if not raw["released"]:
            return _finish(op, request, raw)
        lines = raw["stdout"].splitlines()
        fields: dict[str, str] = {}
        for line in lines:
            fields.update(_fields(line))
        canonical = fields.get("canonical"); printed = fields.get("fingerprint.sha256")
        if not canonical or not printed:
            raise JackalError("claim card omitted canonical preimage or fingerprint")
        recomputed = hashlib.sha256(canonical.encode()).hexdigest()
        if recomputed != printed:
            raise JackalError("claim-card fingerprint mismatch")
        result = {
            "status": "model-based", "model": fields.get("model"),
            "assumptions": next((line.split("=", 1)[1] for line in lines
                                  if line.startswith("assumptions=")), None),
            "non_claims": next((line.split("=", 1)[1] for line in lines
                                 if line.startswith("non-claims=")), None),
            "canonical": canonical, "fingerprint_sha256": printed,
            "fingerprint_recomputed": True, "card_text": raw["stdout"],
        }
        return _finish(op, request, raw, result)
    except Exception as exc:
        return _error(op, exc)


# ---------------------------------------------------------------------------
# Receipt verifier (variant-aware, re-runs the pinned Lean-proved checker)
# ---------------------------------------------------------------------------

def _recheck_formal_receipt(receipt: Mapping[str, Any]) -> list[str]:
    """Authoritative v1.4.2 formal re-verification with variant dispatch."""
    errs: list[str] = []
    result = receipt.get("result") if isinstance(receipt, dict) else None
    request = receipt.get("request") if isinstance(receipt, dict) else None
    instrument = receipt.get("instrument") if isinstance(receipt, dict) else None
    if (not isinstance(result, dict) or not isinstance(request, dict)
            or not isinstance(instrument, dict)):
        return ["formal receipt malformed"]
    formal_receipt = result.get("formal_receipt")
    if not isinstance(formal_receipt, dict):
        return ["formal receipt missing canonical jackal-formal-receipt-v1 object"]
    _ensure_formal_modules()
    try:
        import receipt_verify as vr  # noqa: E402
        import formal_receipt as fr  # noqa: E402
    except Exception as exc:  # noqa: BLE001
        return errs + [f"formal verifier unavailable: {exc}"]

    variant = fr.receipt_variant(formal_receipt)
    is_gaussian = variant == "gaussian"
    is_variant = variant in fr.RATIONAL_VARIANTS

    try:
        adm = _admit_package()
    except JackalError as exc:
        return errs + [f"package admission failed: {exc}"]

    if is_gaussian:
        checker_path = adm["gaussian_checker"]
        expected_evaluator = APPROVED_GAUSSIAN_PRODUCER_SHA256
        expected_checker = APPROVED_GAUSSIAN_CHECKER_SHA256
        proof_identity_path = Path(adm["gaussian_proof_identity"])
        expected_source = None
    elif variant == "sqrt_rat":
        checker_path = adm["checker"]
        expected_evaluator = APPROVED_SQRT_RAT_PRODUCER_SHA256
        expected_checker = APPROVED_CHECKER_SHA256
        proof_identity_path = Path(adm["range_proof_identity"])
        expected_source = None
    elif variant == "exp_rat":
        checker_path = adm["checker"]
        expected_evaluator = APPROVED_EXP_RAT_PRODUCER_SHA256
        expected_checker = APPROVED_CHECKER_SHA256
        proof_identity_path = Path(adm["range_proof_identity"])
        expected_source = None
    else:
        checker_path = adm["checker"]
        expected_evaluator = APPROVED_SHA256
        expected_checker = APPROVED_CHECKER_SHA256
        proof_identity_path = Path(adm["range_proof_identity"])
        # Range receipts carry the Anubis source SHA — read it from the
        # formal receipt's identities block for the cross-bind.
        expected_source = formal_receipt.get("identities", {}).get("source_anb_sha256")

    proof_ids = fr.load_proof_identity_binding(proof_identity_path)
    proof_file_expected = hashlib.sha256(proof_identity_path.read_bytes()).hexdigest()
    proof_digest_expected = proof_ids["identity_digest_sha256"]
    inv_sha_expected = hashlib.sha256(Path(adm["inventory"]).read_bytes()).hexdigest()

    # Assemble expected_request in the shape the upstream verifier accepts.
    canonical_req = formal_receipt.get("request", {})
    expected_request: dict[str, str] = {
        "command": canonical_req.get("command", ""),
        "expression": canonical_req.get("expression", ""),
        "input_lo": canonical_req.get("input_lo", ""),
        "input_hi": canonical_req.get("input_hi", ""),
    }
    if is_gaussian:
        expected_request["tolerance"] = canonical_req.get("tolerance", "")

    try:
        out = vr.verify_receipt(
            receipt=formal_receipt, checker=checker_path,
            expected_evaluator=expected_evaluator,
            expected_checker=expected_checker,
            inventory_path=Path(adm["inventory"]),
            expected_inventory_sha256=inv_sha_expected,
            proof_identity_path=proof_identity_path,
            expected_proof_identity_file=proof_file_expected,
            expected_proof_identity_digest=proof_digest_expected,
            expected_plugin=_plugin_manifest_sha256(),
            expected_source=expected_source,
            expected_release_epoch=formal_receipt.get("release_epoch"),
            expected_request=expected_request,
        )
    except vr.ReceiptRefusal as r:
        return errs + [f"formal receipt re-verification refused: {r.cls}"]
    except Exception as exc:  # noqa: BLE001
        return errs + [f"checker re-verification failed: {exc}"]

    # Bind outer Hermes fields to verifier-derived formal evidence.
    outer_variant = result.get("variant") or "range"
    if outer_variant != variant:
        errs.append(f"outer variant {outer_variant} != receipt variant {variant}")
    if (request.get("expression") != canonical_req.get("expression")
            or request.get("lower") != canonical_req.get("input_lo")
            or request.get("upper") != canonical_req.get("input_hi")):
        errs.append("outer request does not match canonical formal receipt")
    if is_gaussian and request.get("tolerance") != canonical_req.get("tolerance"):
        errs.append("outer tolerance does not match canonical formal receipt")
    enc = result.get("enclosure") if isinstance(result.get("enclosure"), dict) else {}
    if [str(enc.get("lower")), str(enc.get("upper"))] != list(out["enclosure"]):
        errs.append("enclosure does not match checker-accepted enclosure")
    if result.get("request_commitment") != out["request_commitment"]:
        errs.append("request commitment does not match recomputation")
    if is_variant:
        # variant receipts carry sexp inside certificate.sexp
        expected_expr_commitment = formal_receipt.get("certificate", {}).get("sexp")
    elif is_gaussian:
        # gaussian receipts carry the cert bytes; expose sha as commitment
        expected_expr_commitment = formal_receipt.get("certificate", {}).get("bytes_b64")
    else:
        expected_expr_commitment = formal_receipt.get("certificate", {}).get("sexp")
    if result.get("expr_commitment") != expected_expr_commitment:
        errs.append("expr commitment does not match certificate")
    if result.get("certificate_sha256") != out["certificate_sha256"]:
        errs.append("certificate digest does not match checker input")
    outer_ops = result.get("operators") or []
    if sorted(outer_ops) != list(out["expression_operators"]):
        errs.append("operators do not match certificate")
    ev = instrument.get("evaluator", {}) if isinstance(instrument, dict) else {}
    ck = instrument.get("checker", {}) if isinstance(instrument, dict) else {}
    pl = instrument.get("plugin", {}) if isinstance(instrument, dict) else {}
    if ev.get("sha256") != out["evaluator_sha256"]:
        errs.append("outer evaluator identity does not match formal verifier")
    if ck.get("sha256") != out["checker_sha256"]:
        errs.append("outer checker identity does not match formal verifier")
    if pl.get("sha256") != out["plugin_sha256"]:
        errs.append("outer plugin identity does not match formal verifier")
    return errs


def verify(receipt: Any) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(receipt, dict):
        return {"valid": False, "errors": ["receipt must be an object"]}
    required = {"schema", "operation", "request", "result", "instrument", "receipt_sha256"}
    if set(receipt) != required:
        errors.append("receipt keyset mismatch")
    if receipt.get("schema") != SCHEMA:
        errors.append("unsupported receipt schema")
    core = {k: receipt.get(k) for k in ("schema", "operation", "request", "result", "instrument")}
    try:
        expected = hashlib.sha256(_canonical(core)).hexdigest()
    except Exception:  # noqa: BLE001
        expected = ""
    if receipt.get("receipt_sha256") != expected:
        errors.append("receipt digest mismatch")
    instrument = receipt.get("instrument")
    result = receipt.get("result")
    status = result.get("status") if isinstance(result, dict) else None
    formal_variants = {
        "jackal_range_bound": "range",
        "jackal_gaussian_integral": "gaussian",
        "jackal_sqrt_rat_bound": "sqrt_rat",
        "jackal_exp_rat_bound": "exp_rat",
    }
    operation = receipt.get("operation")
    if status not in {"refused", "indeterminate"}:
        if operation in formal_variants:
            expected_evaluator = {
                "range": APPROVED_SHA256,
                "gaussian": APPROVED_GAUSSIAN_PRODUCER_SHA256,
                "sqrt_rat": APPROVED_SQRT_RAT_PRODUCER_SHA256,
                "exp_rat": APPROVED_EXP_RAT_PRODUCER_SHA256,
            }[formal_variants[operation]]
            expected_checker = (APPROVED_GAUSSIAN_CHECKER_SHA256
                                if operation == "jackal_gaussian_integral"
                                else APPROVED_CHECKER_SHA256)
            if (not isinstance(instrument, dict)
                    or not isinstance(instrument.get("evaluator"), dict)
                    or instrument["evaluator"].get("sha256") != expected_evaluator):
                errors.append("evaluator identity mismatch")
            if (not isinstance(instrument, dict)
                    or not isinstance(instrument.get("checker"), dict)
                    or instrument["checker"].get("sha256") != expected_checker):
                errors.append("checker identity mismatch")
        else:
            if not (isinstance(instrument, dict)
                    and instrument.get("sha256") == APPROVED_SHA256
                    and instrument.get("name") == "jackal-native"):
                errors.append("instrument identity mismatch")
    if not isinstance(result, dict):
        errors.append("result must be an object")
    else:
        if operation not in OPERATIONS:
            errors.append("unknown operation")
        elif status not in OPERATIONS[operation]:
            errors.append("status is invalid for operation")
        request = receipt.get("request")
        if not isinstance(request, dict):
            errors.append("request must be an object")
        if status in {"refused", "indeterminate"}:
            if result.get("released") is not False:
                errors.append("non-release status must set released=false")
            if not isinstance(result.get("reason"), str) or not result.get("reason"):
                errors.append("non-release status requires a reason")
        if status == "formal-bounded":
            expected_theorem = (GAUSSIAN_THEOREM
                                if operation == "jackal_gaussian_integral"
                                else FORMAL_THEOREM)
            if result.get("theorem") != expected_theorem:
                errors.append("formal receipt missing/incorrect theorem id")
            if not re.fullmatch(r"[0-9a-f]{64}", str(result.get("certificate_sha256", ""))):
                errors.append("formal receipt missing certificate digest")
            variant_expected = formal_variants.get(operation)
            if result.get("variant") != variant_expected:
                errors.append(f"formal receipt variant mismatch: {result.get('variant')} != {variant_expected}")
            expected_cert_status = ("gaussian-formal-bounded"
                                    if operation == "jackal_gaussian_integral"
                                    else "bounded")
            if result.get("cert_status") != expected_cert_status:
                errors.append("formal receipt cert_status must match variant")
            if not (isinstance(instrument, dict)
                    and "evaluator" in instrument and "checker" in instrument):
                errors.append("formal receipt requires evaluator+checker identities")
            enc = result.get("enclosure")
            try:
                from fractions import Fraction as _F
                lo = _F(str(enc["lower"])); hi = _F(str(enc["upper"]))
                if lo > hi:
                    errors.append("reversed enclosure")
            except Exception:  # noqa: BLE001
                errors.append("malformed formal enclosure")
            ops = result.get("operators")
            if not isinstance(ops, list) or not ops:
                errors.append("formal receipt missing operators")
            if not isinstance(result.get("request_commitment"), str) or not result.get("request_commitment"):
                errors.append("formal receipt missing request commitment")
            errors.extend(_recheck_formal_receipt(receipt))
        if status == "exact":
            mode = request.get("mode") if isinstance(request, dict) else None
            if mode == "rational":
                if not all(isinstance(result.get(k), str) and result.get(k)
                           for k in ("parsed", "exact", "approx")):
                    errors.append("malformed exact rational result")
            elif mode in {"big_add", "big_multiply", "big_power", "factorial", "binomial"}:
                value = result.get("value"); digits = result.get("digits")
                if (not isinstance(value, str) or not value.isdigit()
                        or digits != len(value)):
                    errors.append("malformed exact integer result")
            else:
                errors.append("unsupported exact receipt mode")
        if status == "checked":
            check = result.get("check")
            if not isinstance(result.get("derivative"), str) or not result.get("derivative"):
                errors.append("checked result requires a derivative")
            try:
                if (not isinstance(check, dict) or isinstance(check.get("points"), bool)
                        or int(check.get("points")) <= 0):
                    raise ValueError
                _finite(check.get("max_relative_deviation"), "deviation")
                _finite(check.get("tolerance"), "tolerance")
            except Exception:  # noqa: BLE001
                errors.append("malformed derivative check metadata")
        if status == "bounded":
            enc = result.get("enclosure")
            try:
                lo = _finite(enc["lower"], "lower"); hi = _finite(enc["upper"], "upper")
                if lo > hi:
                    errors.append("reversed enclosure")
                if isinstance(request, dict) and "tolerance" in request:
                    if hi - lo > _finite(request["tolerance"], "tolerance") * (1 + 1e-9):
                        errors.append("enclosure exceeds requested tolerance")
            except Exception:  # noqa: BLE001
                errors.append("malformed enclosure")
        if status == "model-based":
            if result.get("fingerprint_sha256") != hashlib.sha256(
                    str(result.get("canonical", "")).encode()).hexdigest():
                errors.append("claim-card fingerprint mismatch")
            expected_model = {"projectile": "ideal-projectile"}.get(
                request.get("model") if isinstance(request, dict) else None)
            if expected_model is None or result.get("model") != expected_model:
                errors.append("claim-card model mismatch")
        if status not in {"formal-bounded", "exact", "estimated", "checked",
                          "bounded", "model-based", "refused", "indeterminate"}:
            errors.append("unknown epistemic status")
    if isinstance(instrument, dict) and "evaluator" in instrument:
        ident = {"evaluator_sha256": instrument.get("evaluator", {}).get("sha256"),
                 "checker_sha256": instrument.get("checker", {}).get("sha256")}
    else:
        ident = {"instrument_sha256": instrument.get("sha256")
                                        if isinstance(instrument, dict) else None}
    return {"valid": not errors, "errors": errors,
            "receipt_sha256": receipt.get("receipt_sha256"), **ident}


def verify_receipt(args: Mapping[str, Any], **_: Any) -> str:
    try:
        return json.dumps({"success": True,
                           "verification": verify(args.get("receipt"))},
                          sort_keys=True)
    except Exception as exc:  # noqa: BLE001
        return _error("jackal_verify_receipt", exc)
