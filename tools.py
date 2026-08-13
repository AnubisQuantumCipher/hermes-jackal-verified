"""Fail-closed JACKAL subprocess adapter and receipt validator."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Mapping

PLUGIN_ROOT = Path(__file__).resolve().parent
BINARY = PLUGIN_ROOT / "bin" / "jackal-native"
APPROVED_SHA256 = "609de1035be62a5183ad6555b97402567c9e4539b41806a5b52974f6be9030ae"
SCHEMA = "jackal-hermes-receipt-v1"
MAX_OUTPUT_BYTES = 2_000_000
MAX_INTEGER_DIGITS = 100_000
MAX_EXPONENT = 1_000_000
OPERATIONS = {
    "jackal_exact": {"exact", "refused", "indeterminate"},
    "jackal_evaluate": {"estimated", "refused", "indeterminate"},
    "jackal_differentiate": {"checked", "refused", "indeterminate"},
    "jackal_integrate": {"estimated", "bounded", "refused", "indeterminate"},
    "jackal_range_bound": {"bounded", "refused", "indeterminate"},
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


def _binary_identity() -> dict[str, Any]:
    if not BINARY.is_file() or not os.access(BINARY, os.X_OK):
        raise JackalError("approved JACKAL executable is missing or not executable")
    digest = _sha(BINARY)
    if digest != APPROVED_SHA256:
        raise JackalError(f"JACKAL executable identity mismatch: observed {digest}")
    return {"name": "jackal", "sha256": digest, "size": BINARY.stat().st_size}


def _invoke(argv: list[str], timeout: int = 180) -> dict[str, Any]:
    instrument = _binary_identity()
    started = time.time()
    try:
        proc = subprocess.run(
            [str(BINARY), *argv], text=True, capture_output=True, timeout=max(1, min(int(timeout), 3600)),
            shell=False, stdin=subprocess.DEVNULL, cwd=str(PLUGIN_ROOT),
            env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "HOME": str(PLUGIN_ROOT), "LANG": "C.UTF-8"},
        )
    except subprocess.TimeoutExpired as exc:
        return {"released": False, "status": "indeterminate", "reason": "execution-timeout", "detail": str(exc), "instrument": instrument}
    if len(proc.stdout.encode()) > MAX_OUTPUT_BYTES or len(proc.stderr.encode()) > MAX_OUTPUT_BYTES:
        raise JackalError("JACKAL output exceeded the adapter limit")
    observed_after = _sha(BINARY)
    if observed_after != instrument["sha256"]:
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


def range_bound(args: Mapping[str, Any], timeout: int = 180, max_chars: int = 8192) -> str:
    op="jackal_range_bound"
    try:
        expr=_expression(args.get("expression"),max_chars); lower=_finite(args.get("lower"),"lower"); upper=_finite(args.get("upper"),"upper")
        if not lower<upper:raise JackalError("lower must be less than upper")
        request={"expression":expr,"lower":lower,"upper":upper}; raw=_invoke(["range-bound",expr,_number(lower),_number(upper)],timeout)
        if not raw["released"]:return _finish(op,request,raw)
        fields=_fields(raw["stdout"]); lo,hi,lo_s,hi_s=_enclosure(raw["stdout"],"range-enclosure")
        if fields.get("status")!="bounded":raise JackalError("range result was not labeled bounded")
        return _finish(op,request,raw,{"status":"bounded","enclosure":{"lower":lo_s,"upper":hi_s,"width":hi-lo},"assurance":fields.get("assurance"),"non_claims":["superset may be wider than the attained range","conditional on the stated floating-point/libm model"]})
    except Exception as exc:return _error(op,exc)


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
    if (
        not isinstance(instrument,dict)
        or instrument.get("name") != "jackal"
        or instrument.get("sha256") != APPROVED_SHA256
        or not isinstance(instrument.get("size"), int)
        or instrument.get("size", 0) <= 0
    ): errors.append("instrument identity mismatch")
    result=receipt.get("result")
    if not isinstance(result,dict):errors.append("result must be an object")
    else:
        status=result.get("status")
        operation=receipt.get("operation")
        if operation not in OPERATIONS: errors.append("unknown operation")
        elif status not in OPERATIONS[operation]: errors.append("status is invalid for operation")
        if status=="bounded":
            enc=result.get("enclosure")
            try:
                lo=_finite(enc["lower"],"lower");hi=_finite(enc["upper"],"upper")
                if lo>hi:errors.append("reversed enclosure")
                request=receipt.get("request",{})
                if "tolerance" in request and hi-lo>_finite(request["tolerance"],"tolerance")*(1+1e-9):errors.append("enclosure exceeds requested tolerance")
            except Exception:errors.append("malformed enclosure")
        if status=="model-based" and result.get("fingerprint_sha256")!=hashlib.sha256(str(result.get("canonical","")).encode()).hexdigest():errors.append("claim-card fingerprint mismatch")
        if status not in {"exact","estimated","checked","bounded","model-based","refused","indeterminate"}:errors.append("unknown epistemic status")
    return {"valid":not errors,"errors":errors,"receipt_sha256":receipt.get("receipt_sha256"),"instrument_sha256":instrument.get("sha256") if isinstance(instrument,dict) else None}


def verify_receipt(args: Mapping[str, Any], **_: Any) -> str:
    try:return json.dumps({"success":True,"verification":verify(args.get("receipt"))},sort_keys=True)
    except Exception as exc:return _error("jackal_verify_receipt",exc)
