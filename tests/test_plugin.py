#!/usr/bin/env python3
"""Unit battery for the v4.0.0 pass-through adapter (33 tools)."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tarfile
import unittest
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


class Context:
    def __init__(self):
        self.tools: list[tuple[str, dict, object]] = []
        self.skills: list[tuple[str, Path]] = []
        self.sections: list[tuple[str, str]] = []

    def get_config(self, key, default=None):
        return default

    def register_tool(self, name, toolset, schema, handler):
        self.tools.append((name, schema, handler))

    def register_skill(self, name, path):
        self.skills.append((name, path))

    def register_system_prompt_section(self, name, text, **_):
        self.sections.append((name, text))


def call(handler, args):
    return json.loads(handler(args))


class JackalPluginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = Context()
        PKG.register(cls.ctx)
        cls.by_name = {name: handler for name, _, handler in cls.ctx.tools}

    # -- registration surface ------------------------------------------
    def test_registers_exactly_34_tools_skill_and_routing(self):
        self.assertEqual(len(self.ctx.tools), 34)
        self.assertEqual(sorted(self.by_name), sorted(schemas.ALL_TOOLS))
        self.assertIn("jackal_claim", self.by_name)
        self.assertIn("jackal_verify_bundle", self.by_name)
        self.assertIn("jackal_integrate_bound_cert", self.by_name)
        self.assertEqual([n for n, _ in self.ctx.skills],
                         ["jackal-verified-computation"])
        routing = self.ctx.sections[0][1]
        self.assertIn("Never silently downgrade", routing)
        self.assertIn("jackal_verify_bundle", routing)

    def test_schemas_match_vendored_tools_json(self):
        import io
        with tarfile.open(fileobj=io.BytesIO(tools._package_bytes()),
                          mode="r:gz") as tf:
            member = tf.extractfile(
                f"{tools.PKG_DIRNAME}/plugin/hermes/tools.json")
            doc = json.loads(member.read().decode("utf-8"))
        upstream = {t["name"] for t in doc["tools"]}
        self.assertEqual(upstream, set(schemas.ALL_TOOLS))
        for t in doc["tools"]:
            want_req = sorted(k for k, v in t["arguments"].items()
                              if v.get("required"))
            got_req = sorted(schemas.SCHEMAS[t["name"]]["parameters"]
                             .get("required", []))
            self.assertEqual(want_req, got_req, t["name"])

    # -- weaker/exact lanes --------------------------------------------
    def test_exact_round_trip(self):
        out = call(self.by_name["jackal_exact"], {"expression": "0.1+0.2"})
        self.assertEqual(out["status"], "exact")
        self.assertEqual(out["fields"]["exact"], "3/10")
        self.assertFalse(out["formal"])

    def test_exact_grammar_refusal_passthrough(self):
        out = call(self.by_name["jackal_exact"], {"expression": "sqrt(2)"})
        self.assertEqual(out["status"], "refused")
        self.assertTrue(out.get("reason"))

    def test_exact_cas_certificate_lane(self):
        out = call(self.by_name["jackal_xgcd"], {"a": "462", "b": "1071"})
        self.assertEqual(out["status"], "exact")
        self.assertIn("g", out["fields"])

    def test_evaluate_never_formal(self):
        out = call(self.by_name["jackal_evaluate"], {"expression": "sin(1)"})
        self.assertFalse(out["formal"])
        self.assertNotIn("formal", out["status"])

    def test_diff_is_checked(self):
        out = call(self.by_name["jackal_diff"], {"expression": "x^3"})
        self.assertEqual(out["status"], "checked")

    def test_integrate_bound_is_bounded(self):
        out = call(self.by_name["jackal_integrate_bound"],
                   {"expression": "x^2", "input_lo": "0", "input_hi": "1",
                    "tolerance": "0.001"})
        self.assertEqual(out["status"], "bounded")

    # -- formal lanes ----------------------------------------------------
    def _formal(self, tool, args):
        out = call(self.by_name[tool], args)
        self.assertEqual(out["status"], "formal-bounded", out)
        self.assertIn("receipt", out)
        return out

    def test_range_lane_round_trips_and_tamper_refuses(self):
        out = self._formal("jackal_range_bound",
                           {"expression": "x^2+1", "input_lo": "0",
                            "input_hi": "2"})
        receipt = out["receipt"]
        epoch = receipt["release_epoch"]
        req = receipt["request"]
        expected = {
            "receipt": receipt,
            "expected_release_epoch": epoch,
            "expected_command": req["command"],
            "expected_expression": req["expression"],
            "expected_input_lo": req["input_lo"],
            "expected_input_hi": req["input_hi"],
        }
        ver = call(self.by_name["jackal_verify_receipt"], expected)
        self.assertEqual(ver["status"], "verified", ver)
        # semantic tamper: widen the claimed enclosure upper bound
        bad = json.loads(json.dumps(expected))
        bad["receipt"]["result"]["enclosure_hi"] = "9999"
        ver2 = call(self.by_name["jackal_verify_receipt"], bad)
        self.assertEqual(ver2["status"], "refused")

    def test_sqrt_rat_lane_round_trips(self):
        out = self._formal("jackal_sqrt_rat_bound",
                           {"expression": "sqrt(x)", "input_lo": "2",
                            "input_hi": "3"})
        self.assertEqual(out["variant"], "sqrt_rat")

    def test_ln_rat_lane_round_trips(self):
        out = self._formal("jackal_ln_rat_bound",
                           {"expression": "ln(x)", "input_lo": "1",
                            "input_hi": "2"})
        self.assertEqual(out["variant"], "ln_rat")

    def test_int_cert_lane_round_trips_and_tamper_refuses(self):
        out = self._formal("jackal_integrate_bound_cert",
                           {"expression": "sin(x)", "input_lo": "0",
                            "input_hi": "1", "tolerance": "1/100"})
        receipt = out["receipt"]
        self.assertEqual(receipt["variant"], "int_cert")
        self.assertEqual(receipt["theorem"]["id"], "int_cert_sound")
        self.assertEqual(out["checker_rerun"], "ACCEPT")
        req = receipt["request"]
        expected = {
            "receipt": receipt,
            "expected_release_epoch": receipt["release_epoch"],
            "expected_command": req["command"],
            "expected_expression": req["expression"],
            "expected_input_lo": req["input_lo"],
            "expected_input_hi": req["input_hi"],
            "expected_tolerance": req["tolerance"],
        }
        ver = call(self.by_name["jackal_verify_receipt"], expected)
        self.assertEqual(ver["status"], "verified", ver)
        bad = json.loads(json.dumps(expected))
        bad["receipt"]["result"]["enclosure_hi"] = "9999"
        ver2 = call(self.by_name["jackal_verify_receipt"], bad)
        self.assertEqual(ver2["status"], "refused")

    def test_int_cert_fragment_refusal(self):
        out = call(self.by_name["jackal_integrate_bound_cert"],
                   {"expression": "tan(x)", "input_lo": "0",
                    "input_hi": "1", "tolerance": "1/10"})
        self.assertEqual(out["status"], "refused")

    def test_gaussian_lane_round_trips(self):
        out = self._formal("jackal_gaussian_integral",
                           {"expression":
                            "exp(-10000000000*(x-0.5000123456789)^2)",
                            "input_lo": "0", "input_hi": "1",
                            "tolerance": "1/1000000000000"})
        self.assertEqual(out["receipt"]["variant"], "gaussian")
        self.assertEqual(out["checker_rerun"], "ACCEPT")

    def test_formal_fragment_refusals(self):
        out = call(self.by_name["jackal_sqrt_rat_bound"],
                   {"expression": "x^2", "input_lo": "0", "input_hi": "1"})
        self.assertEqual(out["status"], "refused")
        out2 = call(self.by_name["jackal_exp_rat_bound"],
                    {"expression": "ln(x)", "input_lo": "1",
                     "input_hi": "2"})
        self.assertEqual(out2["status"], "refused")

    # -- claim kernel ----------------------------------------------------
    def test_claim_bundle_compile_replay_and_tamper(self):
        request = {"schema": "jackal-claim-request-v1",
                   "steps": [
                       {"id": "p", "op": "exact", "command": "mod-pow",
                        "args": ["3", "100", "7"]},
                       {"id": "t", "op": "threshold", "arg": "p",
                        "cmp": "lt", "threshold": "7"},
                       {"id": "d", "op": "decision", "arg": "t",
                        "decision_id": "unit", "action": "proceed",
                        "consequence_class": "decision-boundary"}],
                   "root": "d"}
        out = call(self.by_name["jackal_claim"], {"request": request})
        self.assertEqual(out["status"], "ok", out)
        bundle = out["bundle"]
        root_node = next(n for n in bundle["nodes"]
                         if n["id"] == bundle["root"])
        import hashlib
        policy_c = json.dumps(bundle["policy"], sort_keys=True,
                              separators=(",", ":"),
                              ensure_ascii=False).encode()
        pins = {
            "bundle": bundle,
            "expected_release_epoch": "v1.6.0",
            "expected_policy_sha256": hashlib.sha256(policy_c).hexdigest(),
            "expected_root_proposition": root_node["proposition"],
            "verification_time_unix": "1786752000",
        }
        ver = call(self.by_name["jackal_verify_bundle"], pins)
        self.assertEqual(ver["status"], "verified", ver)
        # tamper one node value -> stable refusal
        bad = json.loads(json.dumps(pins))
        node = bad["bundle"]["nodes"][0]
        node_s = json.dumps(node["proposition"])
        node["proposition"] = json.loads(node_s.replace('"4"', '"5"', 1))
        ver2 = call(self.by_name["jackal_verify_bundle"], bad)
        self.assertEqual(ver2["status"], "refused")
        self.assertIn("node-id-mismatch", json.dumps(ver2))

    # -- plugin-boundary fail-closed gates --------------------------------
    def test_package_identity_poison_fails_admission(self):
        original = tools.PKG_SHA256
        admitted = tools._ADMITTED
        try:
            tools.PKG_SHA256 = "0" * 64
            tools._ADMITTED = None
            out = call(self.by_name["jackal_exact"],
                       {"expression": "1+1"})
            self.assertEqual(out["status"], "refused")
            self.assertEqual(out["reason"], "plugin-admission-failed")
            self.assertIn("mismatch", out.get("detail", ""))
        finally:
            tools.PKG_SHA256 = original
            tools._ADMITTED = admitted

    def test_epoch_receipt_drift_fails_admission(self):
        import tempfile
        original = tools.EPOCH_RECEIPT
        admitted = tools._ADMITTED
        try:
            drifted = json.loads(original.read_text())
            drifted["upstream"]["package"]["sha256"] = "f" * 64
            tmp = Path(tempfile.mkstemp(suffix=".json")[1])
            tmp.write_text(json.dumps(drifted))
            tools.EPOCH_RECEIPT = tmp
            tools._ADMITTED = None
            out = call(self.by_name["jackal_exact"],
                       {"expression": "1+1"})
            self.assertEqual(out["status"], "refused")
            self.assertEqual(out["reason"], "plugin-admission-failed")
            self.assertIn("epoch-receipt", out.get("detail", ""))
            tmp.unlink()
        finally:
            tools.EPOCH_RECEIPT = original
            tools._ADMITTED = admitted

    def test_toctou_post_admission_mutation_refuses(self):
        adm = tools._admit_package()
        target = adm["root"] / "plugin/hermes/server.py"
        original_mode = target.stat().st_mode
        data = target.read_bytes()
        try:
            os.chmod(target, 0o600)
            target.write_bytes(data + b"\n# tampered\n")
            out = call(self.by_name["jackal_exact"],
                       {"expression": "1+1"})
            self.assertEqual(out["status"], "refused")
            self.assertIn("plugin-toctou", out["reason"])
        finally:
            target.write_bytes(data)
            os.chmod(target, original_mode)
        healed = call(self.by_name["jackal_exact"], {"expression": "1+1"})
        self.assertEqual(healed["status"], "exact")

    def test_overlong_expression_refused_at_plugin_boundary(self):
        out = call(self.by_name["jackal_exact"],
                   {"expression": "1+" * 5000 + "1"})
        self.assertEqual(out["status"], "refused")
        self.assertEqual(out["reason"], "plugin-args-too-long")


if __name__ == "__main__":
    unittest.main(verbosity=2)
