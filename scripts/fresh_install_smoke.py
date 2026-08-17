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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
    assert len(ctx.tools) == 33, f"expected 33 tools, got {len(ctx.tools)}"
    assert ctx.skills == ["jackal-verified-computation"], ctx.skills
    assert ctx.sections, "routing prompt section missing"

    exact = json.loads(ctx.tools["jackal_exact"]({"expression": "0.1+0.2"}))
    assert exact["status"] == "exact", exact
    assert exact["fields"]["exact"] == "3/10", exact

    formal = json.loads(ctx.tools["jackal_sqrt_rat_bound"](
        {"expression": "sqrt(x)", "input_lo": "2", "input_hi": "3"}))
    assert formal["status"] == "formal-bounded", formal

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

    print(f"FRESH_INSTALL_PASS tools={len(ctx.tools)} "
          f"skills={len(ctx.skills)} prompt_sections={len(ctx.sections)} "
          f"exact=3/10 formal=sqrt_rat bundle_replay=verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
