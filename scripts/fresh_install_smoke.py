#!/usr/bin/env python3
"""Fresh-install smoke: load the plugin exactly as Hermes would from a
plain clone, register, and exercise one exact lane, one formal lane, and
one claim-compile/replay round trip — no local JACKAL repository, no
network."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from program_fixture import POLICY_SHA256, VERIFY_TIME, make_v3_fixture, sha


class Context:
    def __init__(self):
        self.tools = {}
        self.skills = []
        self.sections = []

    def get_config(self, key, default=None):
        return default

    def register_tool(self, name, toolset, schema, handler):
        self.tools[name] = handler

    def register_skill(self, name, path):
        self.skills.append(name)

    def register_system_prompt_section(self, name, text, **_):
        self.sections.append(name)


def main() -> int:
    spec = importlib.util.spec_from_file_location(
        "jackal_verified", ROOT / "__init__.py",
        submodule_search_locations=[str(ROOT)])
    module = importlib.util.module_from_spec(spec)
    sys.modules["jackal_verified"] = module
    spec.loader.exec_module(module)
    ctx = Context()
    module.register(ctx)
    assert len(ctx.tools) == 41, f"expected 41 tools, got {len(ctx.tools)}"
    assert ctx.skills == ["jackal-verified-computation"], ctx.skills
    assert ctx.sections, "routing prompt section missing"

    exact = json.loads(ctx.tools["jackal_exact"]({"expression": "0.1+0.2"}))
    assert exact["status"] == "exact", exact
    assert exact["fields"]["exact"] == "3/10", exact

    formal = json.loads(ctx.tools["jackal_sqrt_rat_bound"](
        {"expression": "sqrt(x)", "input_lo": "2", "input_hi": "3"}))
    assert formal["status"] == "formal-bounded", formal

    composed = json.loads(ctx.tools["jackal_integrate_bound_cert"](
        {"expression": "sin(x)", "input_lo": "0", "input_hi": "1",
         "tolerance": "1/100"}))
    assert composed["status"] == "formal-bounded", composed
    assert composed["receipt"]["variant"] == "int_cert", composed
    assert composed["receipt"]["theorem"]["id"] == "int_cert_sound", composed

    request = {"schema": "jackal-claim-request-v1",
               "steps": [{"id": "p", "op": "exact", "command": "mod-pow",
                          "args": ["3", "100", "7"]}],
               "root": "p"}
    claim = json.loads(ctx.tools["jackal_claim"]({"request": request}))
    assert claim["status"] == "ok", claim
    bundle = claim["bundle"]
    root_node = next(n for n in bundle["nodes"] if n["id"] == bundle["root"])
    policy_sha = hashlib.sha256(json.dumps(
        bundle["policy"], sort_keys=True, separators=(",", ":"),
        ensure_ascii=False).encode()).hexdigest()
    verified = json.loads(ctx.tools["jackal_verify_bundle"]({
        "bundle": bundle,
        "expected_release_epoch": "v1.6.0",
        "expected_policy_sha256": policy_sha,
        "expected_root_proposition": root_node["proposition"],
        "verification_time_unix": "1786752000"}))
    assert verified["status"] == "verified", verified

    structural = json.loads(ctx.tools["jackal_test_exists"]({
        "file_path": "claim_kernel.py",
        "file_sha256": (
            "77b0f85ad5fb7214f88898b60ea29ea9"
            "fd7be740c38b655388444e6e5181f348"
        ),
        "symbol": "canonical_bytes",
        "declaration_line": "77",
        "declaration_count": "1",
    }))
    assert structural["status"] == "structural-exact", structural
    assert structural["checker_rerun"] == "ACCEPT", structural

    decision = json.loads(ctx.tools["jackal_decision_rank_v2"]({
        "decision_id": "fresh_install_v6",
        "criterion": "latency_ms",
        "unit": "ms",
        "sense": "min",
        "options": "alpha 120 beta 90",
    }))
    assert decision["status"] == "exact", decision
    assert decision["fields"]["selected"] == "beta", decision

    with tempfile.TemporaryDirectory(prefix="jackal-fresh-program-") as td:
        source, evidence, compiler_sha, artifact_sha, marker = make_v3_fixture(
            Path(td)
        )
        program_args = {
            "source_path": str(source),
            "evidence_dir": str(evidence),
            "expected_source_sha256": sha(source.read_bytes()),
            "expected_compiler_sha256": compiler_sha,
            "expected_artifact_sha256": artifact_sha,
            "expected_policy_sha256": POLICY_SHA256,
            "verification_time_unix": VERIFY_TIME,
            "profile": "inventory-safe-v1",
            "nonce": "fresh-install-v6",
        }
        program = json.loads(
            ctx.tools["jackal_anubis_verify_program"](program_args)
        )
        assert program["status"] == "verified-program-evidence", program
        replay = json.loads(ctx.tools["jackal_anubis_verify_program_receipt"](
            {**program_args, "receipt": program["receipt"]}
        ))
        assert replay["status"] == "verified-program-receipt", replay
        assert not marker.exists(), "program artifact executed"

    print(f"FRESH_INSTALL_PASS tools={len(ctx.tools)} "
          f"skills={len(ctx.skills)} prompt_sections={len(ctx.sections)} "
          f"exact=3/10 formal=sqrt_rat composed=int_cert "
          f"bundle_replay=verified structural=structural-exact "
          f"decision=beta program=verified-program-receipt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
