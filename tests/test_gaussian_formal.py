#!/usr/bin/env python3
"""Plugin-level tracer for zero-libm formal Gaussian integration."""
from __future__ import annotations

import hashlib
import base64
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import tools  # noqa: E402


class GaussianFormalPluginTest(unittest.TestCase):
    def call(self, expression: str) -> dict:
        return json.loads(tools.integrate({
            "expression": expression,
            "lower": 0,
            "upper": 1,
            "assurance": "formal-bounded",
            "tolerance": 1e-12,
        }, timeout=120))

    def test_extreme_request_releases_checker_backed_formal_receipt(self) -> None:
        out = self.call("exp(-10000000000*(x-0.5000123456789)^2)")
        self.assertTrue(out["success"], out)
        receipt = out["receipt"]
        self.assertEqual(receipt["result"]["status"], "formal-bounded")
        self.assertEqual(receipt["result"]["theorem"],
                         "gaussian_integral_check_sound")
        self.assertTrue(tools.verify(receipt)["valid"])

        forged = json.loads(json.dumps(receipt))
        forged["result"]["enclosure"]["upper"] = "0"
        core = {key: forged[key] for key in
                ("schema", "operation", "request", "result", "instrument")}
        forged["receipt_sha256"] = hashlib.sha256(tools._canonical(core)).hexdigest()
        verified = tools.verify(forged)
        self.assertFalse(verified["valid"])
        self.assertTrue(any("formal" in error or "enclosure" in error
                            for error in verified["errors"]), verified)

        for name, mutate in {
            "checker-identity": lambda r: r["instrument"]["checker"].update(
                {"sha256": "0" * 64}),
            "theorem": lambda r: r["result"].update({"theorem": "cert_check_sound"}),
            "coverage": lambda r: r["result"].update(
                {"coverage_row_ids": ["add"]}),
            "tolerance": lambda r: r["request"].update(
                {"tolerance": "1/1000000000"}),
        }.items():
            changed = json.loads(json.dumps(receipt))
            mutate(changed)
            changed_core = {key: changed[key] for key in
                            ("schema", "operation", "request", "result", "instrument")}
            changed["receipt_sha256"] = hashlib.sha256(
                tools._canonical(changed_core)).hexdigest()
            verdict = tools.verify(changed)
            self.assertFalse(verdict["valid"], (name, verdict))

        semantic = json.loads(json.dumps(receipt))
        inner = semantic["result"]["formal_receipt"]
        cert = base64.b64decode(inner["certificate"]["bytes_b64"]).decode()
        cert = "\n".join("output 0 0" if line.startswith("output ") else line
                         for line in cert.splitlines()) + "\n"
        cert_bytes = cert.encode()
        inner["certificate"]["bytes_b64"] = base64.b64encode(cert_bytes).decode()
        inner["certificate"]["sha256"] = hashlib.sha256(cert_bytes).hexdigest()
        inner["result"]["enclosure_lo"] = "0"
        inner["result"]["enclosure_hi"] = "0"
        inner_body = {key: value for key, value in inner.items()
                      if key != "receipt_digest_sha256"}
        inner["receipt_digest_sha256"] = hashlib.sha256(
            tools._canonical(inner_body)).hexdigest()
        semantic["result"]["certificate_sha256"] = inner["certificate"]["sha256"]
        semantic["result"]["enclosure"] = {"lower": "0", "upper": "0", "width": "0"}
        semantic_core = {key: semantic[key] for key in
                         ("schema", "operation", "request", "result", "instrument")}
        semantic["receipt_sha256"] = hashlib.sha256(
            tools._canonical(semantic_core)).hexdigest()
        semantic_verdict = tools.verify(semantic)
        self.assertFalse(semantic_verdict["valid"], semantic_verdict)
        self.assertTrue(any("re-verification" in error or "checker" in error
                            for error in semantic_verdict["errors"]), semantic_verdict)

    def test_unsupported_formal_expression_refuses_without_fallback(self) -> None:
        out = self.call("exp(x)")
        self.assertTrue(out["success"], out)
        result = out["receipt"]["result"]
        self.assertEqual(result["status"], "refused")
        self.assertFalse(result["released"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
