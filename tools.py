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
from pathlib import Path
from typing import Any, Mapping

PLUGIN_ROOT = Path(__file__).resolve().parent
BINARY = PLUGIN_ROOT / "bin" / "jackal-native"
CHECKER = PLUGIN_ROOT / "bin" / "jackal_cert_check"
# v1.1.0 formal epoch: the evaluator emits schema-v2 certificates the packaged
# proved checker requires. Both identities are load-bearing and pinned.
APPROVED_SHA256 = "820c0722e46a0800115c404ea1c9251c6f72fe8c6897bdabe437f342f9310b6c"
APPROVED_CHECKER_SHA256 = "2186b43f8e45b7b3e55e189d64e92f15999664f5194caed929d14b29b006f59b"
SCHEMA = "jackal-hermes-receipt-v2"
FORMAL_THEOREM = "cert_check_sound"
# The evaluator + proved checker ship inside ONE vendored, verified upstream
# v1.1.0 release tarball (the 131 MB checker exceeds GitHub's 100 MB file limit
# uncompressed; the tarball is 40 MB). It is admitted — hash-verified, safely
# extracted, manifest-verified, per-binary SHA/arch/mode-verified — into a
# private snapshot before either binary is executed. No LFS, no network fetch,
# no stripping; a plain git clone carries everything (offline-capable).
PKG_TARBALL = PLUGIN_ROOT / "pkg" / "jackal-v1.1.0-macos-arm64.tar.gz"
PKG_SHA256 = "95588591d4a17e687b9b870d15920c834276059058d38726d1d48640bbbb3c56"
PKG_DIRNAME = "jackal-v1.1.0-macos-arm64"
MAX_OUTPUT_BYTES = 2_000_000
MAX_INTEGER_DIGITS = 100_000
MAX_EXPONENT = 1_000_000
OPERATIONS = {
    "jackal_exact": {"exact", "refused", "indeterminate"},
    "jackal_evaluate": {"estimated", "refused", "indeterminate"},
    "jackal_differentiate": {"checked", "refused", "indeterminate"},
    "jackal_integrate": {"estimated", "bounded", "refused", "indeterminate"},
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
        if ev.is_file() and ck.is_file() and _sha(ev) == APPROVED_SHA256 and _sha(ck) == APPROVED_CHECKER_SHA256:
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
    if _sha(ev) != APPROVED_SHA256:
        raise JackalError(f"admitted evaluator identity mismatch: {_sha(ev)}")
    if _sha(ck) != APPROVED_CHECKER_SHA256:
        raise JackalError(f"admitted checker identity mismatch: {_sha(ck)}")
    if not _arch_ok(ev) or not _arch_ok(ck):
        raise JackalError("admitted binary is not a Mach-O arm64 executable")
    ev.chmod(0o500)
    ck.chmod(0o500)
    _ADMITTED = {"snapshot": str(snap), "package": str(pkg),
                 "evaluator": str(ev), "checker": str(ck),
                 "evaluator_sha256": APPROVED_SHA256, "checker_sha256": APPROVED_CHECKER_SHA256}
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


def integrate(args: Mapping[str, Any], timeout: int = 180, max_chars: int = 8192) -> str:
    op="jackal_integrate"
    try:
        expr=_expression(args.get("expression"),max_chars); lower=_finite(args.get("lower"),"lower"); upper=_finite(args.get("upper"),"upper")
        if not lower<upper: raise JackalError("lower must be less than upper")
        assurance=str(args.get("assurance", "")); request={"expression":expr,"lower":lower,"upper":upper,"assurance":assurance}
        if assurance=="fast_estimate":
            panels=args.get("panels",200)
            if not isinstance(panels,int) or isinstance(panels,bool) or panels<2 or panels>1000000 or panels%2: raise JackalError("panels must be an even integer in 2..1000000")
            request["panels"]=panels; argv=["integrate",expr,_number(lower),_number(upper),str(panels)]
        elif assurance in {"adaptive_estimate","bounded"}:
            tol=_finite(args.get("tolerance"),"tolerance")
            if tol<=0:raise JackalError("tolerance must be positive")
            request["tolerance"]=tol; argv=["integrate-adaptive" if assurance=="adaptive_estimate" else "integrate-bound",expr,_number(lower),_number(upper),_number(tol)]
        else:raise JackalError("assurance must be fast_estimate, adaptive_estimate, or bounded")
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
    execution root, then run the shared release validator (the upstream v1.1.0
    release path): emit certificate → proved checker ACCEPT → identity/TOCTOU/
    request bindings → formal-status gate → `formal-bounded`. Returns the
    validator receipt; raises JackalError on any refusal (no bounded fallback)."""
    import sys as _sys
    fdir = str(PLUGIN_ROOT / "jackal_formal")
    if fdir not in _sys.path:
        _sys.path.insert(0, fdir)
    import base64 as _b64
    import release_validate as rv  # vendored, from jackal_formal/
    adm = _admit_package()  # evaluator + checker from the verified private snapshot
    ev, ck = Path(adm["evaluator"]), Path(adm["checker"])
    with tempfile.TemporaryDirectory(prefix="jackal-formal-") as tmp:
        wd = Path(tmp) / "run"
        wd.mkdir(mode=0o700)
        try:
            receipt = rv.validate_release(
                expr=expr, lo=lower, hi=upper, evaluator=str(ev), checker=str(ck),
                expected_evaluator=APPROVED_SHA256, expected_checker=APPROVED_CHECKER_SHA256,
                workdir=str(wd))
        except rv.ReleaseRefusal as r:
            raise JackalError(f"formal-release-refused:{r.cls}") from r
        # Read the EXACT certificate the checker accepted, before the workdir is
        # cleaned. It travels in the receipt so the public verifier can re-run the
        # proved checker on it — a formal receipt must be independently
        # re-checkable, not merely self-consistent (§487 false-accept repair).
        cert_bytes = (wd / "cert.bytes").read_bytes()
    if receipt.get("status") != "formal-bounded":
        raise JackalError("formal path did not yield formal-bounded")
    if hashlib.sha256(cert_bytes).hexdigest() != receipt["certificate_sha256"]:
        raise JackalError("embedded certificate digest mismatch")
    receipt["certificate_b64"] = _b64.b64encode(cert_bytes).decode("ascii")
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
                      "checker": {"name": "jackal_cert_check", "sha256": rr["checker_sha256"]}}
        result = {
            "status": "formal-bounded",
            "enclosure": {"lower": rr["certified_enclosure"][0], "upper": rr["certified_enclosure"][1]},
            "input": {"lower": rr["input"][0], "upper": rr["input"][1]},
            "expr_commitment": rr["expr_commitment"],
            "request_commitment": rr["request_commitment"],
            "certificate_sha256": rr["certificate_sha256"],
            "certificate": rr["certificate_b64"],
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
    """Authoritative formal re-verification. Re-runs the PACKAGED PROVED CHECKER on
    the certificate carried in the receipt, then binds every self-reported field to
    what the checker actually accepted. A recomputed outer digest cannot launder a
    formal claim here, because none of the receipt's own fields are trusted — the
    truth comes from re-executing `jackal_cert_check` on the embedded bytes and
    re-deriving the request commitment from the request (§487 false-accept repair)."""
    import base64
    errs: list[str] = []
    result = receipt.get("result") if isinstance(receipt, dict) else None
    request = receipt.get("request") if isinstance(receipt, dict) else None
    if not isinstance(result, dict) or not isinstance(request, dict):
        return ["formal receipt malformed"]
    cert_b64 = result.get("certificate")
    if not isinstance(cert_b64, str) or not cert_b64:
        return ["formal receipt missing embedded certificate"]
    try:
        cert_bytes = base64.b64decode(cert_b64, validate=True)
    except Exception:
        return ["embedded certificate is not valid base64"]
    if hashlib.sha256(cert_bytes).hexdigest() != result.get("certificate_sha256"):
        errs.append("certificate digest does not match embedded certificate")
    expr = request.get("expression"); lo = request.get("lower"); hi = request.get("upper")
    if not (isinstance(expr, str) and isinstance(lo, str) and isinstance(hi, str)):
        return errs + ["formal request malformed"]
    import sys as _sys
    fdir = str(PLUGIN_ROOT / "jackal_formal")
    if fdir not in _sys.path:
        _sys.path.insert(0, fdir)
    try:
        import release_validate as rv
    except Exception as exc:
        return errs + [f"formal verifier unavailable: {exc}"]
    try:
        adm = _admit_package()
        with tempfile.TemporaryDirectory(prefix="jackal-verify-") as tmp:
            cp = Path(tmp) / "cert.bytes"
            fd = os.open(str(cp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            try:
                os.write(fd, cert_bytes)
            finally:
                os.close(fd)
            out = rv.validate_cert_file(
                cert_path=str(cp), expr=expr, lo=lo, hi=hi,
                evaluator=adm["evaluator"], checker=adm["checker"],
                expected_evaluator=APPROVED_SHA256, expected_checker=APPROVED_CHECKER_SHA256)
    except rv.ReleaseRefusal as r:
        return errs + [f"checker re-verification refused: {r.cls}"]
    except Exception as exc:
        return errs + [f"checker re-verification failed: {exc}"]
    # Bind every self-reported field to what the proved checker actually accepted.
    enc = result.get("enclosure") if isinstance(result.get("enclosure"), dict) else {}
    if [str(enc.get("lower")), str(enc.get("upper"))] != list(out["certified_enclosure"]):
        errs.append("enclosure does not match checker-accepted enclosure")
    if result.get("request_commitment") != out["request_commitment"]:
        errs.append("request commitment does not match recomputation")
    if result.get("expr_commitment") != out["expr_commitment"]:
        errs.append("expr commitment does not match certificate")
    if result.get("certificate_sha256") != out["certificate_sha256"]:
        errs.append("certificate digest does not match checker input")
    if sorted(result.get("operators") or []) != list(out["operators"]):
        errs.append("operators do not match certificate")
    if out.get("status") != "formal-bounded":
        errs.append("checker did not derive formal-bounded")
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
            if not (isinstance(ev,dict) and ev.get("sha256")==APPROVED_SHA256):
                errors.append("evaluator identity mismatch")
            if not (isinstance(ck,dict) and ck.get("sha256")==APPROVED_CHECKER_SHA256):
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
            if result.get("theorem")!=FORMAL_THEOREM: errors.append("formal receipt missing/incorrect theorem id")
            if not re.fullmatch(r"[0-9a-f]{64}", str(result.get("certificate_sha256",""))): errors.append("formal receipt missing certificate digest")
            if result.get("cert_status")!="bounded": errors.append("formal receipt cert_status must be bounded")
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
