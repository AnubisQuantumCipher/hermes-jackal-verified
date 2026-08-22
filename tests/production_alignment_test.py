#!/usr/bin/env python3
"""Production-alignment contract for the candidate 41-tool Hermes plugin."""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import re
import subprocess
import sys
import tarfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PACKAGE_SHA256 = "d0c2c87d357aa9cae6551343215910032f30259e4a6b40cde0b64687cba107d4"
EXPECTED_TREE_SHA256 = "12e52bfd0b3fe3fc2f6f4c8acf4bd6d0d3c47be1ae9c334e8ef4b068c24e07e3"
EXPECTED_BUILD_COMMIT = "0ef98d4706c0be5660914b705083924886c813cb"
EXPECTED_ALIGNMENT_RECEIPT_COMMIT = "5c0223f2a73bdafdbf0cf6fe5132559ddb6b7f8e"
EXPECTED_TOOLS = [
    "jackal_range_bound",
    "jackal_gaussian_integral",
    "jackal_integrate_bound_cert",
    "jackal_verify_receipt",
    "jackal_sqrt_rat_bound",
    "jackal_exp_rat_bound",
    "jackal_ln_rat_bound",
    "jackal_sin_rat_bound",
    "jackal_cos_rat_bound",
    "jackal_atan_rat_bound",
    "jackal_tanh_rat_bound",
    "jackal_exact",
    "jackal_evaluate",
    "jackal_diff",
    "jackal_integrate",
    "jackal_integrate_adaptive",
    "jackal_integrate_bound",
    "jackal_solve",
    "jackal_canon",
    "jackal_poly_canon",
    "jackal_poly_eq",
    "jackal_poly_gcd",
    "jackal_ratfunc_canon",
    "jackal_roots_isolate",
    "jackal_alg_sign",
    "jackal_alg_cmp",
    "jackal_xgcd",
    "jackal_mod_pow",
    "jackal_mod_inv",
    "jackal_crt",
    "jackal_divides",
    "jackal_prime_cert",
    "jackal_claim",
    "jackal_verify_bundle",
    "jackal_test_exists",
    "jackal_claim_cites_test",
    "jackal_decision_rank",
    "jackal_decision_rank_v2",
    "jackal_anubis_check_program",
    "jackal_anubis_verify_program",
    "jackal_anubis_verify_program_receipt",
]


def load_plugin():
    spec = importlib.util.spec_from_file_location(
        "jackal_verified_alignment",
        ROOT / "__init__.py",
        submodule_search_locations=[str(ROOT)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load plugin")
    module = importlib.util.module_from_spec(spec)
    sys.modules["jackal_verified_alignment"] = module
    spec.loader.exec_module(module)
    return module


PLUGIN = load_plugin()
SCHEMAS = sys.modules["jackal_verified_alignment.schemas"]
TOOLS = sys.modules["jackal_verified_alignment.tools"]


def package_json(relative: str) -> dict:
    with tarfile.open(fileobj=io.BytesIO(TOOLS._package_bytes()), mode="r:gz") as archive:
        member = archive.extractfile(f"{TOOLS.PKG_DIRNAME}/{relative}")
        if member is None:
            raise AssertionError(f"missing package member: {relative}")
        return json.loads(member.read().decode("utf-8"))


def yaml_tool_names() -> list[str]:
    lines = (ROOT / "plugin.yaml").read_text(encoding="utf-8").splitlines()
    start = lines.index("provides_tools:") + 1
    end = lines.index("provides_skills: [jackal-verified-computation]")
    return [line.removeprefix("  - ") for line in lines[start:end]]


class ProductionAlignmentTest(unittest.TestCase):
    def test_package_inventory_schema_and_plugin_names_are_exactly_equal(self) -> None:
        inventory = package_json("capability_inventory_v1.json")
        catalog = package_json("plugin/hermes/tools.json")
        inventory_names = [row["name"] for row in inventory["tools"]]
        catalog_names = [row["name"] for row in catalog["tools"]]
        self.assertEqual(inventory["tool_count"], 41)
        self.assertEqual(inventory["unique_tool_count"], 41)
        self.assertEqual(inventory_names, EXPECTED_TOOLS)
        self.assertEqual(catalog_names, EXPECTED_TOOLS)
        self.assertEqual(sorted(SCHEMAS.ALL_TOOLS), sorted(EXPECTED_TOOLS))
        self.assertEqual(yaml_tool_names(), sorted(EXPECTED_TOOLS))

    def test_candidate_epoch_and_identity_cover_new_trust_families(self) -> None:
        epoch = json.loads((ROOT / "EPOCH.json").read_text(encoding="utf-8"))
        self.assertEqual(TOOLS.RELEASE_EPOCH, "v1.7.3")
        self.assertEqual(TOOLS.PKG_SHA256, EXPECTED_PACKAGE_SHA256)
        self.assertEqual(epoch["plugin"]["version"], "6.0.0")
        self.assertEqual(epoch["tools"]["count"], 41)
        self.assertEqual(epoch["upstream"]["release_state"], "candidate")
        self.assertEqual(epoch["upstream"]["package"]["sha256"], EXPECTED_PACKAGE_SHA256)
        self.assertEqual(epoch["upstream"]["package"]["sha256sums_sha256"], EXPECTED_TREE_SHA256)
        for relative in (
            "capability_inventory_v1.json",
            "tools/anubis_program_verify.py",
            "program/inventory_safe_v1.json",
            "domain_packs/registry_v1.json",
            "tools/domain_pack_verify.py",
            "tools/test_exists_verify.py",
            "tools/decision_verify.py",
        ):
            self.assertIn(relative, epoch["identities"], relative)
            self.assertEqual(TOOLS.APPROVED_IDENTITIES[relative], epoch["identities"][relative])
        skill = ROOT / "skills/jackal-verified-computation/SKILL.md"
        self.assertEqual(epoch["skill"]["sha256"], hashlib.sha256(skill.read_bytes()).hexdigest())

    def test_metadata_and_adapter_language_are_neutral(self) -> None:
        metadata = (ROOT / "plugin.yaml").read_text(encoding="utf-8")
        adapter = (ROOT / "__init__.py").read_text(encoding="utf-8")
        combined = (metadata + "\n" + adapter).lower()
        self.assertIn('version: "6.0.0"', metadata)
        self.assertIn("41 tools", metadata)
        self.assertIn("runtime result object", combined)
        for forbidden in (
            "statuses pass through verbatim",
            "status passthrough that never inflates",
            "inflation is structurally impossible",
        ):
            self.assertNotIn(forbidden, combined)

    def test_current_docs_describe_the_candidate_and_41_tool_surface(self) -> None:
        current_docs = (
            "README.md",
            "PROVENANCE.md",
            "SECURITY.md",
            "THIRD_PARTY_NOTICES.md",
            "skills/AGENTS-SNIPPET.md",
        )
        for relative in current_docs:
            document = (ROOT / relative).read_text(encoding="utf-8").lower()
            self.assertIn("v1.7.3", document, relative)
            self.assertIn("candidate", document, relative)
            self.assertNotIn("jackal-v1.7.0-macos-arm64", document, relative)
            self.assertNotIn("exposes thirty-four", document, relative)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for expected in (
            "41 tools",
            EXPECTED_BUILD_COMMIT,
            EXPECTED_ALIGNMENT_RECEIPT_COMMIT,
            EXPECTED_PACKAGE_SHA256,
        ):
            self.assertIn(expected, readme)
        for stale in ("7d935f0", "5bc45b70", "4671296"):
            self.assertNotIn(stale, readme)

    def test_skill_routes_current_claim_receipt_domain_and_program_surfaces(self) -> None:
        skill = (ROOT / "skills/jackal-verified-computation/SKILL.md").read_text(encoding="utf-8")
        for required in (
            "41-tool",
            "v1.7.3 candidate",
            "capability_inventory_v1.json",
            "jackal_claim",
            "jackal_verify_bundle",
            "jackal_verify_receipt",
            "jackal_test_exists",
            "jackal_decision_rank_v2",
            "jackal_anubis_verify_program",
            "jackal_anubis_verify_program_receipt",
            "policy-construct-totality-not-established",
            "No silent downgrade",
        ):
            self.assertIn(required, skill, required)
        referenced = {
            token.strip("`.,;:()[]")
            for token in skill.replace("/", " ").split()
            if token.strip("`.,;:()[]").startswith("jackal_")
        }
        self.assertTrue(referenced <= set(EXPECTED_TOOLS), sorted(referenced - set(EXPECTED_TOOLS)))

    def test_epoch_generator_reproduces_current_files(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-B", str(ROOT / "scripts/generate_epoch.py"), "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("EPOCH_GENERATION_PASS", completed.stdout)

    def test_z3_identity_is_consistent_across_ci_and_current_docs(self) -> None:
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        match = re.search(r"Z3_BINARY_SHA256: ([0-9a-f]{64})", workflow)
        self.assertIsNotNone(match)
        expected = match.group(1)
        for relative in ("PROVENANCE.md", "THIRD_PARTY_NOTICES.md"):
            document = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn(expected, document, relative)


if __name__ == "__main__":
    unittest.main(verbosity=2)
