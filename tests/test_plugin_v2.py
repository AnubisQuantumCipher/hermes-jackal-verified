#!/usr/bin/env python3
"""JACKAL plugin v2 poison suite (completion program Phase J, §515).

Every case runs through the ACTUAL public tool boundary (tools.range_bound /
evaluate / verify_receipt). No load-bearing `assert`; must give identical
verdicts under `python3` and `python3 -O`. Exit nonzero on any failure.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import tools  # noqa: E402

FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        FAILS.append(f"{name}: {detail}")
    print(f"  {'PASS' if cond else 'FAIL'} {name}{'' if cond else ' :: ' + detail}")


def receipt(out: str) -> dict:
    return json.loads(out)["receipt"]


def reseal(r: dict) -> dict:
    core = {k: r[k] for k in ("schema", "operation", "request", "result", "instrument")}
    r["receipt_sha256"] = hashlib.sha256(tools._canonical(core)).hexdigest()
    return r


def vok(r: dict) -> bool:
    return json.loads(tools.verify_receipt({"receipt": r}))["verification"]["valid"]


def main() -> int:
    # --- positive: every FORMAL operator family releases formal-bounded ---
    positives = {
        "poly": "x^2+x-1", "div": "1/(x+2)", "neg": "0-x", "pow0": "x^0",
        "sin": "sin(x)", "cos": "cos(x)", "abs": "abs(x-1)", "floor": "floor(x)",
        "min": "min(x,1)", "max": "max(x,1)", "nested": "min(x^2, sin(x)+2)",
    }
    for k, e in positives.items():
        r = receipt(tools.range_bound({"expression": e, "lower": 0, "upper": 2}))
        check(f"positive:{k}", r["result"]["status"] == "formal-bounded", str(r["result"].get("reason")))
        check(f"positive-verify:{k}", vok(r))

    base = receipt(tools.range_bound({"expression": "x^2+1", "lower": 1, "upper": 2}))

    # --- unsupported formal refuses (no bounded fallback) ---
    for e in ("sqrt(x)", "exp(x)", "ln(x+3)", "tan(x)", "x^-2", "x%2"):
        r = receipt(tools.range_bound({"expression": e, "lower": 1, "upper": 2}))
        check(f"unsupported-refuses:{e}", r["result"]["status"] == "refused" and r["result"].get("released") is False)

    # --- new v3.0.0 variant lanes: each releases through its own tool ---
    gauss = receipt(tools.gaussian_integral({
        "expression": "exp(-10000000000*(x-0.5000123456789)^2)",
        "lower": 0, "upper": 1, "tolerance": "1/1000"}))
    check("gaussian-formal", gauss["result"]["status"] == "formal-bounded"
          and gauss["result"]["variant"] == "gaussian")
    check("gaussian-verify", vok(gauss))

    sqrtR = receipt(tools.sqrt_rat_bound({"expression":"sqrt(x)","lower":"2","upper":"3"}))
    check("sqrt_rat-formal", sqrtR["result"]["status"] == "formal-bounded"
          and sqrtR["result"]["variant"] == "sqrt_rat")
    check("sqrt_rat-verify", vok(sqrtR))

    expR = receipt(tools.exp_rat_bound({"expression":"exp(x)","lower":"0","upper":"1"}))
    check("exp_rat-formal", expR["result"]["status"] == "formal-bounded"
          and expR["result"]["variant"] == "exp_rat")
    check("exp_rat-verify", vok(expR))

    # --- variant-specific mutation locks ---
    def poison_variant(base_receipt, name, mut):
        t = copy.deepcopy(base_receipt); mut(t); reseal(t)
        check(f"variant-poison:{name}", not vok(t))
    for label, br in (("gaussian", gauss), ("sqrt_rat", sqrtR), ("exp_rat", expR)):
        poison_variant(br, f"{label}-tamper-enclosure",
                       lambda t: t["result"].__setitem__("enclosure",{"lower":"0","upper":"0"}))
        poison_variant(br, f"{label}-swap-variant-label",
                       lambda t: t["result"].__setitem__("variant","range"))
        poison_variant(br, f"{label}-forge-cert-sha",
                       lambda t: t["result"].__setitem__("certificate_sha256","d"*64))
        poison_variant(br, f"{label}-swap-theorem",
                       lambda t: t["result"].__setitem__("theorem","nope"))
        poison_variant(br, f"{label}-forge-evaluator",
                       lambda t: t["instrument"]["evaluator"].__setitem__("sha256","b"*64))
        poison_variant(br, f"{label}-forge-checker",
                       lambda t: t["instrument"]["checker"].__setitem__("sha256","c"*64))

    # sqrt_rat + exp_rat lanes must refuse anything other than their exact admitted form
    for name, args in (
        ("sqrt_rat-refuses-poly", ("sqrt_rat_bound", {"expression":"x^2","lower":"1","upper":"2"})),
        ("exp_rat-refuses-poly",  ("exp_rat_bound",  {"expression":"x^2","lower":"1","upper":"2"})),
        ("exp_rat-refuses-negative-lo", ("exp_rat_bound", {"expression":"exp(x)","lower":"-1","upper":"1"})),
    ):
        r = receipt(getattr(tools, args[0])(args[1]))
        check(name, r["result"]["status"] == "refused" and r["result"]["released"] is False)

    # --- weaker lane cannot become formal ---
    ev = receipt(tools.evaluate({"expression": "2+3*4"}))
    check("evaluate-stays-estimated", ev["result"]["status"] == "estimated")
    check("evaluate-not-formal", ev["result"]["status"] != "formal-bounded")

    # --- semantic poisons with recomputed outer digest ---
    def poison(name, mut):
        t = copy.deepcopy(base); mut(t); reseal(t)
        check(f"poison:{name}", not vok(t))
    poison("reversed-enclosure", lambda t: t["result"].__setitem__("enclosure", {"lower": "9", "upper": "1"}))
    poison("forged-evaluator", lambda t: t["instrument"]["evaluator"].__setitem__("sha256", "b" * 64))
    poison("forged-checker", lambda t: t["instrument"]["checker"].__setitem__("sha256", "c" * 64))
    poison("wrong-theorem", lambda t: t["result"].__setitem__("theorem", "nope"))
    poison("non-fragment-op", lambda t: t["result"].__setitem__("operators", ["add", "exp"]))
    poison("missing-cert", lambda t: t["result"].__setitem__("certificate_sha256", ""))
    poison("cert-status-escalated", lambda t: t["result"].__setitem__("cert_status", "formal-bounded"))
    poison("drop-request-commitment", lambda t: t["result"].__setitem__("request_commitment", ""))
    poison("status-upgrade-estimated-to-formal", lambda t: (t.__setitem__("operation", "jackal_evaluate"),
                                                            t["result"].__setitem__("status", "formal-bounded")))

    # --- Hermes false-accept repair (§487): the exact four forgeries that once
    # passed a self-consistent verifier. Each carries a RECOMPUTED outer digest;
    # each must now be refused because verify() re-runs the proved checker on the
    # embedded certificate and binds every field to the checker's verdict. ---
    poison("hermes-ordered-wrong-enclosure", lambda t: t["result"].__setitem__("enclosure", {"lower": "0", "upper": "0"}))
    poison("hermes-changed-request", lambda t: t["request"].__setitem__("expression", "x^999"))
    poison("hermes-arbitrary-cert-digest", lambda t: t["result"].__setitem__("certificate_sha256", "d" * 64))
    poison("hermes-arbitrary-request-commitment", lambda t: t["result"].__setitem__("request_commitment", "deadbeef" * 8))
    poison("hermes-stripped-certificate",
           lambda t: t["result"]["formal_receipt"]["certificate"].pop("bytes_b64", None))
    # A genuine certificate for a DIFFERENT true request cannot be re-labeled as
    # this one: swap in the base cert but claim a wider [0,10] enclosure.
    poison("substituted-enclosure-claim", lambda t: t["result"].__setitem__("enclosure", {"lower": "0", "upper": "10"}))

    # --- v1 receipt cannot satisfy v2 verification ---
    v1 = copy.deepcopy(base); v1["schema"] = "jackal-hermes-receipt-v1"; reseal(v1)
    check("v1-receipt-rejected", not vok(v1))

    # --- digest tamper without reseal ---
    d = copy.deepcopy(base); d["result"]["enclosure"]["lower"] = "0"
    check("unsealed-tamper-rejected", not vok(d))

    # --- malformed / hostile input refuses cleanly ---
    for bad in ({"expression": "", "lower": 1, "upper": 2},
                {"expression": "x^2", "lower": 2, "upper": 1},
                {"expression": "x" * 20000, "lower": 0, "upper": 1}):
        out = json.loads(tools.range_bound(bad))
        ok = (out.get("success") is False) or (out.get("receipt", {}).get("result", {}).get("status") in {"refused", "indeterminate"})
        check(f"malformed:{str(bad)[:24]}", ok)

    # --- exact tool registration present ---
    check("tools-present", all(hasattr(tools, fn) for fn in
          ("range_bound", "evaluate", "verify_receipt", "exact", "differentiate", "integrate", "claim_card")))

    print(f"\nplugin-v2 poison suite: {len(FAILS)} failures")
    if FAILS:
        for f in FAILS:
            print("  FAIL", f, file=sys.stderr)
        print("VERDICT: FAIL")
        return 1
    print("VERDICT: PASS — formal positives verify; every poison refused/invalid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
