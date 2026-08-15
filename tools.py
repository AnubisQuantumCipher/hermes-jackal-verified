"""Fail-closed JACKAL subprocess adapter and receipt validator."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import tempfile
import time
from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping

PLUGIN_ROOT = Path(__file__).resolve().parent
BINARY = PLUGIN_ROOT / "bin" / "jackal-native"
CHECKER = PLUGIN_ROOT / "bin" / "jackal_cert_check"
# v1.3.0 formal-receipt package epoch. Evaluator and checker identities are
# unchanged; the package adds the canonical embedded-certificate receipt and
# independent verifier shared with the upstream wrapper and plugin.
APPROVED_SHA256 = "820c0722e46a0800115c404ea1c9251c6f72fe8c6897bdabe437f342f9310b6c"
APPROVED_CHECKER_SHA256 = "2186b43f8e45b7b3e55e189d64e92f15999664f5194caed929d14b29b006f59b"
APPROVED_GAUSSIAN_PRODUCER_SHA256 = "20c24622b786940a8e82198f2364fb7593e761902fa0736289b179642f1e4306"
APPROVED_GAUSSIAN_CHECKER_SHA256 = "11c741f04b811aa8621db4da5c5dc05e292ead8c0e6a854739f6068757470612"
SCHEMA = "jackal-hermes-receipt-v2"
FORMAL_THEOREM = "cert_check_sound"
GAUSSIAN_FORMAL_THEOREM = "gaussian_integral_check_sound"
# The evaluator + two proved checkers ship inside ONE vendored, verified upstream
# v1.3.0 release tarball (each checker exceeds GitHub's 100 MB file limit
# uncompressed; the deterministic tarball is about 79 MB). It is admitted — hash-verified, safely
# extracted, manifest-verified, per-binary SHA/arch/mode-verified — into a
# private snapshot before either binary is executed. No LFS, no network fetch,
# no stripping; a plain git clone carries everything (offline-capable).
PKG_TARBALL = PLUGIN_ROOT / "pkg" / "jackal-v1.3.0-macos-arm64.tar.gz"
PKG_SHA256 = "13e6a3cb6145522ffe8323bc01b84a505b8647c3f2017f43e4813c38e9b5a7ac"
PKG_DIRNAME = "jackal-v1.3.0-macos-arm64"
MAX_OUTPUT_BYTES = 2_000_000
MAX_INTEGER_DIGITS = 100_000
MAX_EXPONENT = 1_000_000
OPERATIONS = {
    "jackal_exact": {"exact", "refused", "indeterminate"},
    "jackal_evaluate": {"estimated", "refused", "indeterminate"},
    "jackal_differentiate": {"checked", "refused", "indeterminate"},
    "jackal_integrate": {"estimated", "bounded", "formal-bounded", "refused", "indeterminate"},
    "jackal_range_bound": {"formal-bounded", "refused", "indeterminate"},
    "jackal_claim_card": {"model-based", "refused", "indeterminate"},
}


class JackalError(RuntimeError):
    pass


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _plugin_manifest_sha256() -> str:
    """Identity of the manifest that seals the complete native plugin tree."""
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
    v = _finite(value, "numeric argument")
    return format(v, ".17g")


def _rational_arg(value: Any, name: str) -> str:
    """Canonical exact rational for the formal lane.

    JSON numbers are interpreted through their shortest decimal spelling;
    strings may use decimal/scientific or `p/q` notation.  The canonical
    integer/fraction is what the proved checker binds.
    """
    if isinstance(value, bool):
        raise JackalError(f"{name} must be a finite rational")
    try:
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError
        q = Fraction(str(value))
    except (ValueError, ZeroDivisionError) as exc:
        raise JackalError(f"{name} must be a finite rational") from exc
    return str(q.numerator) if q.denominator == 1 else f"{q.numerator}/{q.denominator}"


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
    """Extract with path-traversal / special-file protection: every member must
    be a regular file or dir landing strictly inside `dest` (no absolute paths,
    no '..', no symlinks/devices/hardlinks)."""
    import posixpath
    import tarfile
    dest = dest.resolve()

    def _is_appledouble(name: str) -> bool:
        # macOS `tar` stores extended attributes as AppleDouble `._X` sidecars
        # and a `__MACOSX/` tree. They are extraction-time metadata, never
        # package content; the real files remain fully SHA-verified below.
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
    """SHA256SUMS is the package's exact inventory: every listed file must exist
    and match; no shipped file (besides SHA256SUMS) may be unlisted."""
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
    """Require a Mach-O arm64 executable (0xcffaedfe / cputype 0x0100000c)."""
    with path.open("rb") as f:
        head = f.read(8)
    if len(head) < 8:
        return False
    magic = head[:4]
    cputype = int.from_bytes(head[4:8], "little")
    return magic in (b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe") and (cputype & 0x0100000C) == 0x0100000C


def _admit_package() -> dict[str, Any]:
    """Admit the vendored release tarball into a private snapshot ONCE:
    verify tarball SHA-256 → safe-extract into a 0700 dir → verify SHA256SUMS
    inventory → verify evaluator/checker SHA-256 + Mach-O arm64 + set 0500.
    Returns the verified snapshot paths. Cached for the process."""
    global _ADMITTED
    if _ADMITTED is not None:
        ev, ck = Path(_ADMITTED["evaluator"]), Path(_ADMITTED["checker"])
        gp = Path(_ADMITTED["gaussian_producer"])
        gc = Path(_ADMITTED["gaussian_checker"])
        if (ev.is_file() and ck.is_file() and gp.is_file() and gc.is_file()
                and _sha(ev) == APPROVED_SHA256
                and _sha(ck) == APPROVED_CHECKER_SHA256
                and _sha(gp) == APPROVED_GAUSSIAN_PRODUCER_SHA256
                and _sha(gc) == APPROVED_GAUSSIAN_CHECKER_SHA256):
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
    ev, ck = pkg / "jackal-native", pkg / "jackal_cert_check"
    gp, gc = pkg / "gaussian_certificate.py", pkg / "jackal_gaussian_check"
    if _sha(ev) != APPROVED_SHA256:
        raise JackalError(f"admitted evaluator identity mismatch: {_sha(ev)}")
    if _sha(ck) != APPROVED_CHECKER_SHA256:
        raise JackalError(f"admitted checker identity mismatch: {_sha(ck)}")
    if _sha(gp) != APPROVED_GAUSSIAN_PRODUCER_SHA256:
        raise JackalError(f"admitted Gaussian producer identity mismatch: {_sha(gp)}")
    if _sha(gc) != APPROVED_GAUSSIAN_CHECKER_SHA256:
        raise JackalError(f"admitted Gaussian checker identity mismatch: {_sha(gc)}")
    if not _arch_ok(ev) or not _arch_ok(ck) or not _arch_ok(gc):
        raise JackalError("admitted binary is not a Mach-O arm64 executable")
    ev.chmod(0o500)
    ck.chmod(0o500)
    gp.chmod(0o500)
    gc.chmod(0o500)
    _ADMITTED = {"snapshot": str(snap), "package": str(pkg),
                  "evaluator": str(ev), "checker": str(ck),
                  "gaussian_producer": str(gp), "gaussian_checker": str(gc),
                  "evaluator_sha256": APPROVED_SHA256, "checker_sha256": APPROVED_CHECKER_SHA256,
                  "gaussian_producer_sha256": APPROVED_GAUSSIAN_PRODUCER_SHA256,
                  "gaussian_checker_sha256": APPROVED_GAUSSIAN_CHECKER_SHA256}
    return _ADMITTED


def _binary_identity() -> dict[str, Any]:
    adm = _admit_package()
    ev = Path(adm["evaluator"])
    return {"name": "jackal-native", "sha256": adm["evaluator_sha256"], "size": ev.stat().st_size}


def _invoke(argv: list[str], timeout: int = 180) -> dict[str, Any]:
    adm = _admit_package()
    instrument = _binary_identity()
    started = time.time()
    # Execute the admitted evaluator directly from its private 0500 snapshot
    # (admitted once via the hash+manifest+arch-verified package). Re-hash
    # before and after so a same-run replacement is caught; same-user process
    # compromise remains outside this plugin's local threat boundary.
    snapshot = Path(adm["evaluator"])
    with tempfile.TemporaryDirectory(prefix="jackal-verified-") as tmp:
        if _sha(snapshot) != instrument["sha256"]:
            raise JackalError("JACKAL executable changed before execution")
        try:
            proc = subprocess.run(
                [str(snapshot), *argv], text=True, capture_output=True, timeout=max(1, min(int(timeout), 3600)),
                shell=False, stdin=subprocess.DEVNULL, cwd=tmp,
                env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "HOME": tmp, "LANG": "C.UTF-8"},
            )
        except subprocess.TimeoutExpired as exc:
            return {"released": False, "status": "indeterminate", "reason": "execution-timeout", "detail": str(exc), "instrument": instrument}
        if _sha(snapshot) != instrument["sha256"]:
            raise JackalError("JACKAL execution snapshot changed during execution")
    if len(proc.stdout.encode()) > MAX_OUTPUT_BYTES or len(proc.stderr.encode()) > MAX_OUTPUT_BYTES:
        raise JackalError("JACKAL output exceeded the adapter limit")
    if _sha(snapshot) != instrument["sha256"]:
        raise JackalError("JACKAL executable changed during execution")
    if proc.returncode != 0:
        meaningful = [line.strip() for line in proc.stderr.splitlines() if "panicked at" not in line and not line.startswith("note:") and line.strip()]
        reason = meaningful[-1].removeprefix("ANUBIS_PANIC: ") if meaningful else "JACKAL refused without a diagnostic"
        return {"released": False, "status": "refused", "reason": reason, "exit_code": proc.returncode, "instrument": instrument, "duration_ms": round((time.time()-started)*1000, 3)}
    return {"released": True, "exit_code": 0, "stdout": proc.stdout.strip(), "instrument": instrument, "duration_ms": round((time.time()-started)*1000, 3)}


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


def _receipt(operation: str, request: Mapping[str, Any], result: Mapping[str, Any], instrument: Mapping[str, Any]) -> dict[str, Any]:
    core = {"schema": SCHEMA, "operation": operation, "request": dict(request), "result": dict(result), "instrument": dict(instrument)}
    core["receipt_sha256"] = hashlib.sha256(_canonical(core)).hexdigest()
    return core


def _error(operation: str, exc: BaseException) -> str:
    return json.dumps({"success": False, "operation": operation, "error": str(exc), "error_type": exc.__class__.__name__}, sort_keys=True)


def _finish(operation: str, request: dict[str, Any], raw: dict[str, Any], result: dict[str, Any] | None = None) -> str:
    if not raw["released"]:
        receipt = _receipt(operation, request, {k: v for k, v in raw.items() if k != "instrument"}, raw["instrument"])
        return json.dumps({"success": True, "receipt": receipt}, ensure_ascii=False, sort_keys=True)
    receipt = _receipt(operation, request, result or {}, raw["instrument"])
    return json.dumps({"success": True, "receipt": receipt}, ensure_ascii=False, sort_keys=True)


def exact(args: Mapping[str, Any], timeout: int = 180, max_chars: int = 8192) -> str:
    op = "jackal_exact"
    try:
        mode = str(args.get("mode", ""))
        if mode == "rational":
            expr = _expression(args.get("expression"), max_chars); request={"mode":mode,"expression":expr}; argv=["rat",expr]
        elif mode in {"big_add", "big_multiply", "big_power"}:
            a, b = str(args.get("a", "")), str(args.get("b", ""))
            if not a.isdigit() or not b.isdigit(): raise JackalError("a and b must contain decimal digits only")
            if len(a) > MAX_INTEGER_DIGITS or len(b) > MAX_INTEGER_DIGITS: raise JackalError("integer operand exceeds the adapter digit limit")
            if mode == "big_power" and int(b) > MAX_EXPONENT: raise JackalError("exponent exceeds the adapter limit")
            command={"big_add":"big-add","big_multiply":"big-mul","big_power":"big-pow"}[mode]; request={"mode":mode,"a":a,"b":b}; argv=[command,a,b]
        elif mode in {"factorial", "binomial"}:
            n=args.get("n"); r=args.get("r")
            if not isinstance(n,int) or isinstance(n,bool) or not 0<=n<=10000: raise JackalError("n must be an integer in 0..10000")
            if mode=="factorial": request={"mode":mode,"n":n}; argv=["big-fact",str(n)]
            else:
                if not isinstance(r,int) or isinstance(r,bool) or not 0<=r<=n: raise JackalError("r must be an integer in 0..n")
                request={"mode":mode,"n":n,"r":r}; argv=["big-ncr",str(n),str(r)]
        else: raise JackalError("unsupported exact mode")
        raw=_invoke(argv,timeout)
        if not raw["released"]: return _finish(op,request,raw)
        if mode=="rational":
            fields=_fields(raw["stdout"]); required={"status","parsed","exact","approx"}
            if not required <= fields.keys() or fields["status"]!="exact": raise JackalError("malformed exact-rational output")
            result={"status":"exact","parsed":fields["parsed"],"exact":fields["exact"],"approx":fields["approx"],"non_claims":["approx is IEEE-f64, not the exact result"]}
        else:
            value=raw["stdout"]
            if not value.isdigit(): raise JackalError("malformed exact-integer output")
            result={"status":"exact","value":value,"digits":len(value)}
        return _finish(op,request,raw,result)
    except Exception as exc: return _error(op,exc)


def evaluate(args: Mapping[str, Any], timeout: int = 180, max_chars: int = 8192) -> str:
    op="jackal_evaluate"
    try:
        expr=_expression(args.get("expression"),max_chars); request={"expression":expr}; raw=_invoke(["eval",expr],timeout)
        if not raw["released"]: return _finish(op,request,raw)
        value=_finite(raw["stdout"],"JACKAL result")
        return _finish(op,request,raw,{"status":"estimated","value":value,"rendered":raw["stdout"],"assurance":"IEEE-f64 evaluation","non_claims":["not exact","not a certified error bound"]})
    except Exception as exc:return _error(op,exc)


def differentiate(args: Mapping[str, Any], timeout: int = 180, max_chars: int = 8192) -> str:
    op="jackal_differentiate"
    try:
        expr=_expression(args.get("expression"),max_chars); request={"expression":expr}; raw=_invoke(["diff",expr],timeout)
        if not raw["released"]: return _finish(op,request,raw)
        lines=raw["stdout"].splitlines()
        if len(lines)<2 or " = " not in lines[0]: raise JackalError("malformed derivative output")
        fields=_fields(lines[1])
        if fields.get("status")!="checked": raise JackalError("derivative was not labeled checked")
        result={"status":"checked","derivative":lines[0].split(" = ",1)[1],"input_echo":lines[0].split(" = ",1)[0],"check":{"points":int(fields["points"]),"max_relative_deviation":_finite(fields["max-rel-dev"],"deviation"),"tolerance":_finite(fields["tolerance"],"tolerance")},"assurance":fields.get("assurance"),"domain_caveat":fields.get("domain-caveat"),"non_claims":["numeric sample check is not a proof of symbolic identity"]}
        return _finish(op,request,raw,result)
    except Exception as exc:return _error(op,exc)


def _formal_gaussian_integrate(expr: str, lower: str, upper: str,
                               tolerance: str, timeout: int) -> dict[str, Any]:
    """Run the plugin-sealed v1.3 Gaussian release gate and independently
    rehydrate its certificate through the admitted Lean checker."""
    import sys as _sys
    from types import SimpleNamespace

    fdir = str(PLUGIN_ROOT / "jackal_formal")
    if fdir not in _sys.path:
        _sys.path.insert(0, fdir)
    import gaussian_release as gr
    import receipt_verify as vr

    adm = _admit_package()
    gp = Path(adm["gaussian_producer"])
    gc = Path(adm["gaussian_checker"])
    plugin_sha = _plugin_manifest_sha256()
    with tempfile.TemporaryDirectory(prefix="jackal-gaussian-formal-") as tmp:
        formal_path = Path(tmp) / "formal-receipt.json"
        ns = SimpleNamespace(
            expression=expr, lower=lower, upper=upper, tolerance=tolerance,
            producer=str(gp), checker=str(gc),
            expected_producer=APPROVED_GAUSSIAN_PRODUCER_SHA256,
            expected_checker=APPROVED_GAUSSIAN_CHECKER_SHA256,
            receipt=str(formal_path), plugin_sha256=plugin_sha,
            release_epoch="v1.3.0", timeout=max(1, min(int(timeout), 3600)),
        )
        try:
            formal_receipt = gr.release(ns)
        except gr.Refusal as refusal:
            raise JackalError(f"formal-release-refused:{refusal.cls}") from refusal
        try:
            formal_verification = vr.verify_receipt(
                receipt=formal_receipt, checker=str(gc),
                expected_evaluator=APPROVED_GAUSSIAN_PRODUCER_SHA256,
                expected_checker=APPROVED_GAUSSIAN_CHECKER_SHA256,
                inventory_path=PLUGIN_ROOT / "jackal_formal" / "formal_coverage_inventory.json",
                expected_plugin=plugin_sha,
            )
        except vr.ReceiptRefusal as refusal:
            raise JackalError(f"formal-receipt-refused:{refusal.cls}") from refusal

    result = formal_receipt.get("result", {})
    if result.get("status") != "formal-bounded":
        raise JackalError("formal Gaussian path did not yield formal-bounded")
    return {
        "status": "formal-bounded",
        "certified_enclosure": [result["enclosure_lo"], result["enclosure_hi"]],
        "request_commitment": formal_receipt["request"]["request_commitment_b64"],
        "certificate_sha256": formal_receipt["certificate"]["sha256"],
        "cert_status": result["cert_status"],
        "operators": formal_receipt["fragment"]["expression_operators"],
        "coverage_row_ids": formal_receipt["fragment"]["coverage_row_ids"],
        "formal_receipt": formal_receipt,
        "formal_verification": formal_verification,
        "producer_sha256": APPROVED_GAUSSIAN_PRODUCER_SHA256,
        "checker_sha256": APPROVED_GAUSSIAN_CHECKER_SHA256,
    }


def integrate(args: Mapping[str, Any], timeout: int = 180, max_chars: int = 8192) -> str:
    op="jackal_integrate"
    try:
        expr=_expression(args.get("expression"),max_chars)
        assurance=str(args.get("assurance", ""))
        if assurance == "formal-bounded":
            lo_s = _rational_arg(args.get("lower"), "lower")
            hi_s = _rational_arg(args.get("upper"), "upper")
            tol_s = _rational_arg(args.get("tolerance"), "tolerance")
            if not Fraction(lo_s) < Fraction(hi_s):
                raise JackalError("lower must be less than upper")
            if Fraction(tol_s) <= 0:
                raise JackalError("tolerance must be positive")
            request = {"expression": expr, "lower": lo_s, "upper": hi_s,
                       "tolerance": tol_s, "assurance": assurance}
            try:
                rr = _formal_gaussian_integrate(expr, lo_s, hi_s, tol_s, timeout)
            except JackalError as error:
                raw = {"released": False, "status": "refused", "reason": str(error),
                       "instrument": {
                           "producer_sha256": APPROVED_GAUSSIAN_PRODUCER_SHA256,
                           "checker_sha256": APPROVED_GAUSSIAN_CHECKER_SHA256}}
                return _finish(op, request, raw)
            lo, hi = rr["certified_enclosure"]
            instrument = {
                "evaluator": {"name": "gaussian_certificate.py",
                              "sha256": rr["producer_sha256"]},
                "checker": {"name": "jackal_gaussian_check",
                             "sha256": rr["checker_sha256"]},
                "plugin": {"name": "jackal-verified",
                           "sha256": rr["formal_verification"]["plugin_sha256"]},
            }
            result = {
                "status": "formal-bounded",
                "enclosure": {"lower": lo, "upper": hi,
                              "width": str(Fraction(hi) - Fraction(lo))},
                "request_commitment": rr["request_commitment"],
                "certificate_sha256": rr["certificate_sha256"],
                "formal_receipt": rr["formal_receipt"],
                "cert_status": rr["cert_status"],
                "operators": rr["operators"],
                "coverage_row_ids": rr["coverage_row_ids"],
                "theorem": GAUSSIAN_FORMAL_THEOREM,
                "assurance": "theorem-backed exact-rational Gaussian enclosure; zero libm",
                "non_claims": [
                    "admitted only for canonical exp(-A*(x-mu)^2), exact-square rational A, and a domain covering the proved core",
                    "unsupported formal integration requests refuse without bounded fallback",
                    "not universal correctness; not an exact value",
                    "conditional on the recorded Lean/Mathlib/checker/build and executable-identity TCB",
                ],
            }
            receipt = _receipt(op, request, result, instrument)
            return json.dumps({"success": True, "receipt": receipt}, ensure_ascii=False,
                              sort_keys=True)

        lower=_finite(args.get("lower"),"lower"); upper=_finite(args.get("upper"),"upper")
        if not lower<upper: raise JackalError("lower must be less than upper")
        request={"expression":expr,"lower":lower,"upper":upper,"assurance":assurance}
        if assurance=="fast_estimate":
            panels=args.get("panels",200)
            if not isinstance(panels,int) or isinstance(panels,bool) or panels<2 or panels>1000000 or panels%2: raise JackalError("panels must be an even integer in 2..1000000")
            request["panels"]=panels; argv=["integrate",expr,_number(lower),_number(upper),str(panels)]
        elif assurance in {"adaptive_estimate","bounded"}:
            tol=_finite(args.get("tolerance"),"tolerance")
            if tol<=0:raise JackalError("tolerance must be positive")
            request["tolerance"]=tol; argv=["integrate-adaptive" if assurance=="adaptive_estimate" else "integrate-bound",expr,_number(lower),_number(upper),_number(tol)]
        else:raise JackalError("assurance must be fast_estimate, adaptive_estimate, bounded, or formal-bounded")
        raw=_invoke(argv,timeout)
        if not raw["released"]: return _finish(op,request,raw)
        fields=_fields(raw["stdout"])
        if assurance=="bounded":
            if fields.get("status")!="bounded":raise JackalError("bounded request did not return bounded status")
            lo,hi,lo_s,hi_s=_enclosure(raw["stdout"],"integral-enclosure"); width=hi-lo
            if width > request["tolerance"]*(1+1e-9):raise JackalError("enclosure exceeds requested tolerance")
            result={"status":"bounded","enclosure":{"lower":lo_s,"upper":hi_s,"width":width},"method":fields.get("method"),"mode":fields.get("mode"),"assurance":fields.get("assurance"),"non_claims":["not an exact value","conditional on the stated floating-point/libm model"]}
        else:
            if fields.get("status")!="estimated":raise JackalError("estimate request did not return estimated status")
            result={"status":"estimated","value":_finite(fields.get("integral"),"integral"),"method":fields.get("method"),"assurance":fields.get("assurance"),"error_estimate":fields.get("richardson-error-estimate") or fields.get("achieved-error-estimate"),"non_claims":["error estimate is not a mathematical bound"]}
        return _finish(op,request,raw,result)
    except Exception as exc:return _error(op,exc)


def _formal_range_bound(expr: str, lower: str, upper: str, timeout: int) -> dict[str, Any]:
    """Snapshot the evaluator AND the proved checker into a private 0500
    execution root, then run the upstream v1.3.0 shared release validator:
    emit certificate → proved checker ACCEPT → identity/TOCTOU/request bindings
    → formal-status gate → canonical embedded-certificate receipt → independent
    checker re-run. Returns both validator and formal receipts; raises
    JackalError on any refusal (no bounded fallback)."""
    import sys as _sys
    fdir = str(PLUGIN_ROOT / "jackal_formal")
    if fdir not in _sys.path:
        _sys.path.insert(0, fdir)
    import release_validate as rv  # vendored, from jackal_formal/
    import receipt_verify as vr  # vendored independent formal-receipt verifier
    adm = _admit_package()  # evaluator + checker from the verified private snapshot
    ev, ck = Path(adm["evaluator"]), Path(adm["checker"])
    plugin_sha = _plugin_manifest_sha256()
    with tempfile.TemporaryDirectory(prefix="jackal-formal-") as tmp:
        wd = Path(tmp) / "run"
        wd.mkdir(mode=0o700)
        formal_path = Path(tmp) / "formal-receipt.json"
        try:
            receipt = rv.validate_release(
                expr=expr, lo=lower, hi=upper, evaluator=str(ev), checker=str(ck),
                expected_evaluator=APPROVED_SHA256, expected_checker=APPROVED_CHECKER_SHA256,
                workdir=str(wd), formal_receipt_path=str(formal_path),
                plugin_sha256=plugin_sha, release_epoch="v1.3.0")
        except rv.ReleaseRefusal as r:
            raise JackalError(f"formal-release-refused:{r.cls}") from r
        formal_receipt = json.loads(formal_path.read_text())
        try:
            formal_verification = vr.verify_receipt(
                receipt=formal_receipt, checker=str(ck),
                expected_evaluator=APPROVED_SHA256,
                expected_checker=APPROVED_CHECKER_SHA256,
                inventory_path=PLUGIN_ROOT / "jackal_formal" / "formal_coverage_inventory.json",
                expected_plugin=plugin_sha)
        except vr.ReceiptRefusal as r:
            raise JackalError(f"formal-receipt-refused:{r.cls}") from r
    if receipt.get("status") != "formal-bounded":
        raise JackalError("formal path did not yield formal-bounded")
    receipt["formal_receipt"] = formal_receipt
    receipt["formal_verification"] = formal_verification
    return receipt


def range_bound(args: Mapping[str, Any], timeout: int = 180, max_chars: int = 8192) -> str:
    """Formal, checker-verified range enclosure. Releases `formal-bounded` ONLY
    when the packaged proved checker accepts the certificate the packaged
    evaluator emitted for this exact request, with evaluator+checker identity,
    TOCTOU, and request bindings — otherwise refuses (no bounded fallback)."""
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
            rr = _formal_range_bound(expr, lo_s, hi_s, timeout)
        except JackalError as je:
            raw = {"released": False, "status": "refused", "reason": str(je),
                   "instrument": {"evaluator_sha256": APPROVED_SHA256,
                                  "checker_sha256": APPROVED_CHECKER_SHA256}}
            return _finish(op, request, raw)
        instrument = {"evaluator": {"name": "jackal-native", "sha256": rr["evaluator_sha256"]},
                      "checker": {"name": "jackal_cert_check", "sha256": rr["checker_sha256"]},
                      "plugin": {"name": "jackal-verified",
                                 "sha256": rr["formal_verification"]["plugin_sha256"]}}
        result = {
            "status": "formal-bounded",
            "enclosure": {"lower": rr["certified_enclosure"][0], "upper": rr["certified_enclosure"][1]},
            "input": {"lower": rr["input"][0], "upper": rr["input"][1]},
            "expr_commitment": rr["expr_commitment"],
            "request_commitment": rr["request_commitment"],
            "certificate_sha256": rr["certificate_sha256"],
            "formal_receipt": rr["formal_receipt"],
            "cert_status": rr["cert_status"],
            "operators": rr["operators"],
            "theorem": FORMAL_THEOREM,
            "assurance": rr["assurance"],
            "non_claims": [
                "formal-bounded = checker-accepted, Runs-derived enclosure of the exact semantics over the modeled fragment",
                "conditional on the recorded TCB (libm<=2ulp const node, Lean kernel + checker build, canonical rational codec)",
                "not universal correctness; not an exact value",
                "superset may be wider than the attained range"],
        }
        receipt = _receipt(op, request, result, instrument)
        return json.dumps({"success": True, "receipt": receipt}, ensure_ascii=False, sort_keys=True)
    except Exception as exc:
        return _error(op, exc)


def claim_card(args: Mapping[str, Any], timeout: int = 180, max_chars: int = 8192) -> str:
    op="jackal_claim_card"
    try:
        model=str(args.get("model",""))
        if model!="projectile":raise JackalError("only the projectile model is currently supported")
        speed=_finite(args.get("speed"),"speed"); angle=_finite(args.get("angle_degrees"),"angle_degrees"); gravity=_finite(args.get("gravity"),"gravity")
        if speed<=0 or gravity<=0:raise JackalError("speed and gravity must be positive")
        request={"model":model,"speed":speed,"angle_degrees":angle,"gravity":gravity}; raw=_invoke(["claim-card",model,_number(speed),_number(angle),_number(gravity)],timeout)
        if not raw["released"]:return _finish(op,request,raw)
        lines=raw["stdout"].splitlines(); fields={}
        for line in lines:fields.update(_fields(line))
        canonical=fields.get("canonical"); printed=fields.get("fingerprint.sha256")
        if not canonical or not printed:raise JackalError("claim card omitted canonical preimage or fingerprint")
        recomputed=hashlib.sha256(canonical.encode()).hexdigest()
        if recomputed!=printed:raise JackalError("claim-card fingerprint mismatch")
        result={"status":"model-based","model":fields.get("model"),"assumptions":next((line.split("=",1)[1] for line in lines if line.startswith("assumptions=")),None),"non_claims":next((line.split("=",1)[1] for line in lines if line.startswith("non-claims=")),None),"canonical":canonical,"fingerprint_sha256":printed,"fingerprint_recomputed":True,"card_text":raw["stdout"]}
        return _finish(op,request,raw,result)
    except Exception as exc:return _error(op,exc)


def _recheck_formal_receipt(receipt: Mapping[str, Any]) -> list[str]:
    """Authoritative v1.2 formal re-verification.

    The native Hermes receipt carries the upstream canonical
    ``jackal-formal-receipt-v1`` object.  Re-run the upstream independent
    verifier on it, then bind the outer Hermes fields to the verifier-derived
    request, enclosure, certificate, operator, and instrument identities.
    """
    errs: list[str] = []
    result = receipt.get("result") if isinstance(receipt, dict) else None
    request = receipt.get("request") if isinstance(receipt, dict) else None
    instrument = receipt.get("instrument") if isinstance(receipt, dict) else None
    if not isinstance(result, dict) or not isinstance(request, dict) or not isinstance(instrument, dict):
        return ["formal receipt malformed"]
    formal_receipt = result.get("formal_receipt")
    if not isinstance(formal_receipt, dict):
        return ["formal receipt missing canonical jackal-formal-receipt-v1 object"]
    import sys as _sys
    fdir = str(PLUGIN_ROOT / "jackal_formal")
    if fdir not in _sys.path:
        _sys.path.insert(0, fdir)
    try:
        import receipt_verify as vr
    except Exception as exc:
        return errs + [f"formal verifier unavailable: {exc}"]
    try:
        adm = _admit_package()
        is_gaussian = result.get("theorem") == GAUSSIAN_FORMAL_THEOREM
        checker_path = adm["gaussian_checker"] if is_gaussian else adm["checker"]
        evaluator_sha = (APPROVED_GAUSSIAN_PRODUCER_SHA256
                         if is_gaussian else APPROVED_SHA256)
        checker_sha = (APPROVED_GAUSSIAN_CHECKER_SHA256
                       if is_gaussian else APPROVED_CHECKER_SHA256)
        out = vr.verify_receipt(
            receipt=formal_receipt, checker=checker_path,
            expected_evaluator=evaluator_sha,
            expected_checker=checker_sha,
            inventory_path=PLUGIN_ROOT / "jackal_formal" / "formal_coverage_inventory.json",
            expected_plugin=_plugin_manifest_sha256())
    except vr.ReceiptRefusal as r:
        return errs + [f"formal receipt re-verification refused: {r.cls}"]
    except Exception as exc:
        return errs + [f"checker re-verification failed: {exc}"]

    # Bind every outer Hermes field to verifier-derived formal evidence.
    canonical_req = formal_receipt.get("request", {})
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
    if (not is_gaussian
            and result.get("expr_commitment") != formal_receipt.get("certificate", {}).get("sexp")):
        errs.append("expr commitment does not match certificate")
    if result.get("certificate_sha256") != out["certificate_sha256"]:
        errs.append("certificate digest does not match checker input")
    if sorted(result.get("operators") or []) != list(out["expression_operators"]):
        errs.append("operators do not match certificate")
    if instrument.get("evaluator", {}).get("sha256") != out["evaluator_sha256"]:
        errs.append("outer evaluator identity does not match formal verifier")
    if instrument.get("checker", {}).get("sha256") != out["checker_sha256"]:
        errs.append("outer checker identity does not match formal verifier")
    if instrument.get("plugin", {}).get("sha256") != out["plugin_sha256"]:
        errs.append("outer plugin identity does not match formal verifier")
    return errs


def verify(receipt: Any) -> dict[str, Any]:
    errors=[]
    if not isinstance(receipt,dict):return {"valid":False,"errors":["receipt must be an object"]}
    required={"schema","operation","request","result","instrument","receipt_sha256"}
    if set(receipt)!=required:errors.append("receipt keyset mismatch")
    if receipt.get("schema")!=SCHEMA:errors.append("unsupported receipt schema")
    core={k:receipt.get(k) for k in ("schema","operation","request","result","instrument")}
    try: expected=hashlib.sha256(_canonical(core)).hexdigest()
    except Exception:expected=""
    if receipt.get("receipt_sha256")!=expected:errors.append("receipt digest mismatch")
    instrument=receipt.get("instrument")
    result=receipt.get("result")
    status=result.get("status") if isinstance(result,dict) else None
    # Instrument identity: enforced strictly for RELEASED statuses only. A
    # refusal/indeterminate carries no value, so its instrument is informational
    # (the flat evaluator+checker pair). Formal releases carry a nested
    # evaluator+checker pair (both pinned); weaker released lanes carry the flat
    # single evaluator.
    if status not in {"refused", "indeterminate"}:
        if isinstance(instrument,dict) and "evaluator" in instrument:
            ev=instrument.get("evaluator"); ck=instrument.get("checker")
            gaussian_formal = (status == "formal-bounded" and isinstance(result, dict)
                               and result.get("theorem") == GAUSSIAN_FORMAL_THEOREM)
            expected_ev = (APPROVED_GAUSSIAN_PRODUCER_SHA256
                           if gaussian_formal else APPROVED_SHA256)
            expected_ck = (APPROVED_GAUSSIAN_CHECKER_SHA256
                           if gaussian_formal else APPROVED_CHECKER_SHA256)
            if not (isinstance(ev,dict) and ev.get("sha256")==expected_ev):
                errors.append("evaluator identity mismatch")
            if not (isinstance(ck,dict) and ck.get("sha256")==expected_ck):
                errors.append("checker identity mismatch")
        else:
            if not (isinstance(instrument,dict)
                    and instrument.get("sha256")==APPROVED_SHA256
                    and (instrument.get("name")=="jackal-native")):
                errors.append("instrument identity mismatch")
    if not isinstance(result,dict):errors.append("result must be an object")
    else:
        operation=receipt.get("operation")
        if operation not in OPERATIONS: errors.append("unknown operation")
        elif status not in OPERATIONS[operation]: errors.append("status is invalid for operation")
        request=receipt.get("request")
        if not isinstance(request,dict): errors.append("request must be an object")
        if status in {"refused","indeterminate"}:
            if result.get("released") is not False: errors.append("non-release status must set released=false")
            if not isinstance(result.get("reason"),str) or not result.get("reason"): errors.append("non-release status requires a reason")
        if status=="formal-bounded":
            # A recomputed outer digest must NOT legitimize a formal claim that
            # is not actually checker-backed and fragment-covered (§487).
            is_gaussian = result.get("theorem") == GAUSSIAN_FORMAL_THEOREM
            if result.get("theorem") not in {FORMAL_THEOREM, GAUSSIAN_FORMAL_THEOREM}:
                errors.append("formal receipt missing/incorrect theorem id")
            if not re.fullmatch(r"[0-9a-f]{64}", str(result.get("certificate_sha256",""))): errors.append("formal receipt missing certificate digest")
            expected_cert_status = "gaussian-formal-bounded" if is_gaussian else "bounded"
            if result.get("cert_status")!=expected_cert_status:
                errors.append(f"formal receipt cert_status must be {expected_cert_status}")
            if not (isinstance(instrument,dict) and "evaluator" in instrument and "checker" in instrument):
                errors.append("formal receipt requires evaluator+checker identities")
            enc=result.get("enclosure")
            try:
                from fractions import Fraction as _F
                lo=_F(str(enc["lower"])); hi=_F(str(enc["upper"]))
                if lo>hi: errors.append("reversed enclosure")
            except Exception: errors.append("malformed formal enclosure")
            ops=result.get("operators")
            if not isinstance(ops,list) or not ops: errors.append("formal receipt missing operators")
            elif is_gaussian:
                if sorted(ops) != ["exp", "mul", "neg", "pow2", "sub"]:
                    errors.append("Gaussian formal receipt operator set mismatch")
                if result.get("coverage_row_ids") != ["gaussian-exp-square-integral-v1"]:
                    errors.append("Gaussian formal receipt coverage row mismatch")
            else:
                try:
                    import sys as _s
                    _s.path.insert(0, str(PLUGIN_ROOT/"jackal_formal"))
                    import formal_status_gate as _g
                    formal=_g.formal_operators(_g.load_inventory())
                    nonf=[o for o in ops if o not in formal]
                    if nonf: errors.append(f"formal receipt operators outside fragment: {nonf}")
                except Exception as _e: errors.append(f"coverage check failed: {_e}")
            if not isinstance(result.get("request_commitment"),str) or not result.get("request_commitment"):
                errors.append("formal receipt missing request commitment")
            # Authoritative gate: re-run the proved checker on the carried
            # certificate and bind every self-reported field to its verdict. The
            # cheap structural checks above are only a fast pre-filter; this is
            # what makes a recomputed outer digest unable to forge a formal claim.
            errors.extend(_recheck_formal_receipt(receipt))
        if status=="exact":
            mode=request.get("mode") if isinstance(request,dict) else None
            if mode=="rational":
                if not all(isinstance(result.get(k),str) and result.get(k) for k in ("parsed","exact","approx")):
                    errors.append("malformed exact rational result")
            elif mode in {"big_add","big_multiply","big_power","factorial","binomial"}:
                value=result.get("value"); digits=result.get("digits")
                if not isinstance(value,str) or not value.isdigit() or digits!=len(value): errors.append("malformed exact integer result")
            else: errors.append("unsupported exact receipt mode")
        if status=="checked":
            check=result.get("check")
            if not isinstance(result.get("derivative"),str) or not result.get("derivative"): errors.append("checked result requires a derivative")
            try:
                if not isinstance(check,dict) or isinstance(check.get("points"),bool) or int(check.get("points")) <= 0: raise ValueError
                _finite(check.get("max_relative_deviation"),"deviation"); _finite(check.get("tolerance"),"tolerance")
            except Exception: errors.append("malformed derivative check metadata")
        if status=="bounded":
            enc=result.get("enclosure")
            try:
                lo=_finite(enc["lower"],"lower");hi=_finite(enc["upper"],"upper")
                if lo>hi:errors.append("reversed enclosure")
                request=receipt.get("request",{})
                if "tolerance" in request and hi-lo>_finite(request["tolerance"],"tolerance")*(1+1e-9):errors.append("enclosure exceeds requested tolerance")
            except Exception:errors.append("malformed enclosure")
        if status=="model-based":
            if result.get("fingerprint_sha256")!=hashlib.sha256(str(result.get("canonical","")).encode()).hexdigest():errors.append("claim-card fingerprint mismatch")
            expected_model={"projectile":"ideal-projectile"}.get(request.get("model")) if isinstance(request,dict) else None
            if expected_model is None or result.get("model")!=expected_model: errors.append("claim-card model mismatch")
        if status not in {"formal-bounded","exact","estimated","checked","bounded","model-based","refused","indeterminate"}:errors.append("unknown epistemic status")
    if isinstance(instrument,dict) and "evaluator" in instrument:
        ident={"evaluator_sha256":instrument.get("evaluator",{}).get("sha256"),"checker_sha256":instrument.get("checker",{}).get("sha256")}
    else:
        ident={"instrument_sha256":instrument.get("sha256") if isinstance(instrument,dict) else None}
    return {"valid":not errors,"errors":errors,"receipt_sha256":receipt.get("receipt_sha256"),**ident}


def verify_receipt(args: Mapping[str, Any], **_: Any) -> str:
    try:return json.dumps({"success":True,"verification":verify(args.get("receipt"))},sort_keys=True)
    except Exception as exc:return _error("jackal_verify_receipt",exc)
