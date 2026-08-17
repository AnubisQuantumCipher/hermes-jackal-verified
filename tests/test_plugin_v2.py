#!/usr/bin/env python3
"""v4.0.0 poison battery: surface parity, refusal passthrough, formal
variant round trips, receipt/bundle semantic poisons.  Exit-code driven;
run under default python AND `python3 -O` (optimized parity)."""
from __future__ import annotations

import importlib.util
import json
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_package():
    spec = importlib.util.spec_from_file_location(
        "jackal_verified", ROOT / "__init__.py",
        submodule_search_locations=[str(ROOT)])
    module = importlib.util.module_from_spec(spec)
    sys.modules["jackal_verified"] = module
    spec.loader.exec_module(module)
    return module


PKG = _load_package()
schemas = sys.modules["jackal_verified.schemas"]
tools = sys.modules["jackal_verified.tools"]

RESULTS: list[tuple[str, bool, str]] = []


def record(name: str, ok: bool, note: str = "") -> None:
    RESULTS.append((name, ok, note))
    print(f"{'PASS' if ok else 'FAIL'} {name} {note}"[:180])


class Context:
    def __init__(self):
        self.tools = {}

    def get_config(self, key, default=None):
        return default

    def register_tool(self, name, toolset, schema, handler):
        self.tools[name] = handler

    def register_skill(self, *a, **k):
        pass

    def register_system_prompt_section(self, *a, **k):
        pass


CTX = Context()
PKG.register(CTX)


def call(tool: str, args: dict) -> dict:
    return json.loads(CTX.tools[tool](args))


def main() -> int:
    # -- inventory parity against the vendored tarball -------------------
    with tarfile.open(tools.PKG_TARBALL) as tf:
        doc = json.loads(tf.extractfile(
            f"{tools.PKG_DIRNAME}/plugin/hermes/tools.json").read())
    upstream = sorted(t["name"] for t in doc["tools"])
    record("inventory-33", len(CTX.tools) == 33, f"n={len(CTX.tools)}")
    record("inventory-parity", sorted(CTX.tools) == upstream)
    record("schemas-generated-parity",
           sorted(schemas.ALL_TOOLS) == upstream)

    # -- refusal passthrough (stable classes, no downgrade) ---------------
    r = call("jackal_range_bound",
             {"expression": "tan(x)", "input_lo": "0", "input_hi": "1"})
    record("range-unsupported-refuses", r["status"] == "refused",
           r.get("reason", ""))
    r = call("jackal_sqrt_rat_bound",
             {"expression": "x^2", "input_lo": "0", "input_hi": "1"})
    record("sqrt-rat-fragment-refuses", r["status"] == "refused")
    r = call("jackal_exact", {"expression": "sqrt(2)"})
    record("exact-grammar-refuses", r["status"] == "refused")
    r = call("jackal_evaluate", {"expression": "sin(1)"})
    record("evaluate-never-formal",
           r["status"] not in ("formal-bounded",) and r["formal"] is False,
           f"status={r['status']}")

    # -- formal variant round trips (four lanes incl. v1.5 additions) ----
    lanes = [
        ("jackal_sqrt_rat_bound", {"expression": "sqrt(x)", "input_lo": "2",
                                    "input_hi": "3"}, "sqrt_rat"),
        ("jackal_ln_rat_bound", {"expression": "ln(x)", "input_lo": "1",
                                  "input_hi": "2"}, "ln_rat"),
        ("jackal_tanh_rat_bound", {"expression": "1-2/(exp(2*x)+1)",
                                    "input_lo": "0",
                                    "input_hi": "1"}, "tanh_rat"),
        ("jackal_atan_rat_bound", {"expression": "atan(x)", "input_lo": "0",
                                    "input_hi": "1"}, "atan_rat"),
    ]
    receipts = {}
    for tool, args, variant in lanes:
        out = call(tool, args)
        ok = (out.get("status") == "formal-bounded"
              and out.get("variant") == variant
              and isinstance(out.get("receipt"), dict))
        receipts[variant] = out.get("receipt")
        record(f"{variant}-round-trip", ok)

    # -- receipt semantic poisons (per lane) ------------------------------
    def verify(receipt: dict) -> dict:
        req = receipt["request"]
        return call("jackal_verify_receipt", {
            "receipt": receipt,
            "expected_release_epoch": receipt["release_epoch"],
            "expected_command": req["command"],
            "expected_expression": req["expression"],
            "expected_input_lo": req["input_lo"],
            "expected_input_hi": req["input_hi"],
        })

    for variant, receipt in receipts.items():
        if receipt is None:
            record(f"{variant}-poisons", False, "no receipt")
            continue
        base = json.dumps(receipt)
        v = verify(json.loads(base))
        record(f"{variant}-verify-genuine", v.get("status") == "verified",
               v.get("reason", v.get("verdict", "")))
        poisons = {
            "enclosure-tamper": ("result", "enclosure_hi", "99999"),
            "variant-swap": (None, "variant",
                             "range" if variant != "range" else "sqrt_rat"),
            "checker-forge": ("identities", "checker_sha256", "ab" * 32),
            "theorem-swap": ("theorem", "id", "not_a_theorem"),
        }
        for pname, (section, key, value) in poisons.items():
            bad = json.loads(base)
            target = bad if section is None else bad.get(section, {})
            target[key] = value
            out = verify(bad)
            record(f"{variant}-poison-{pname}",
                   out.get("status") == "refused", out.get("reason", ""))

    # -- claim bundle poisons ---------------------------------------------
    import hashlib
    request = {"schema": "jackal-claim-request-v1",
               "steps": [
                   {"id": "p", "op": "exact", "command": "mod-pow",
                    "args": ["3", "100", "7"]},
                   {"id": "t", "op": "threshold", "arg": "p", "cmp": "lt",
                    "threshold": "7"},
                   {"id": "d", "op": "decision", "arg": "t",
                    "decision_id": "v2", "action": "proceed",
                    "consequence_class": "decision-boundary"}],
               "root": "d"}
    out = call("jackal_claim", {"request": request})
    record("claim-compiles", out.get("status") == "ok")
    bundle = out["bundle"]
    root_node = next(n for n in bundle["nodes"] if n["id"] == bundle["root"])
    policy_sha = hashlib.sha256(json.dumps(
        bundle["policy"], sort_keys=True, separators=(",", ":"),
        ensure_ascii=False).encode()).hexdigest()
    pins = {"bundle": bundle,
            "expected_release_epoch": "v1.6.0",
            "expected_policy_sha256": policy_sha,
            "expected_root_proposition": root_node["proposition"],
            "verification_time_unix": "1786752000"}
    v = call("jackal_verify_bundle", pins)
    record("bundle-verifies", v.get("status") == "verified",
           v.get("reason", ""))
    wrong_epoch = dict(pins, expected_release_epoch="v1.5.0")
    v = call("jackal_verify_bundle", wrong_epoch)
    record("bundle-epoch-pin-bites", v.get("status") != "verified",
           v.get("reason", ""))
    wrong_policy = dict(pins, expected_policy_sha256="cd" * 32)
    v = call("jackal_verify_bundle", wrong_policy)
    record("bundle-policy-pin-bites", v.get("status") != "verified",
           v.get("reason", ""))
    tampered = json.loads(json.dumps(pins))
    node = tampered["bundle"]["nodes"][0]
    node_s = json.dumps(node["proposition"])
    node["proposition"] = json.loads(node_s.replace('"4"', '"5"', 1))
    v = call("jackal_verify_bundle", tampered)
    record("bundle-node-tamper-refuses",
           v.get("status") == "refused"
           and "node-id-mismatch" in json.dumps(v))

    failures = [name for name, ok, _ in RESULTS if not ok]
    print(f"VERDICT: {'PASS' if not failures else 'FAIL'} "
          f"rows={len(RESULTS)} failures={len(failures)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
