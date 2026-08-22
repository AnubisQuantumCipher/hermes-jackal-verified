#!/usr/bin/env python3
"""Generate/check the Hermes epoch receipt and package identity pin block."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS_PATH = ROOT / "tools.py"
EPOCH_PATH = ROOT / "EPOCH.json"
SKILL_PATH = ROOT / "skills/jackal-verified-computation/SKILL.md"
PACKAGE_BASE = "jackal-v1.7.3-macos-arm64.tar.gz"
PACKAGE_DIR = "jackal-v1.7.3-macos-arm64"
PACKAGE_SHA256 = "b317849234208ab6f435e5bad1336e4bf4d039981811323e35138c2e0a4ee68d"
PACKAGE_SIZE = 158363755
PLUGIN_VERSION = "6.0.0"
SKILL_VERSION = "7.0.0"
UPSTREAM_BUILD_COMMIT = "957ac893b243814d9059e6e104c21e0ce68e9ef5"
ALIGNMENT_RECEIPT_COMMIT = "0bca7da98def582bb0ce34a7dfb9b540e599d1b1"
BEGIN = "# BEGIN GENERATED PACKAGE IDENTITIES"
END = "# END GENERATED PACKAGE IDENTITIES"

IDENTITY_PATHS = (
    "MANIFEST.sha256",
    "atan_rat_producer.py",
    "capability_inventory_v1.json",
    "claim_bundle_verify.py",
    "claim_kernel.py",
    "claim_router.py",
    "domain_packs/core/manifest.json",
    "domain_packs/decision/manifest.json",
    "domain_packs/programming/manifest.json",
    "domain_packs/registry_v1.json",
    "evidence/compat_v173_floor.json",
    "evidence/lean_admission_audit_v173.json",
    "exact_verify.py",
    "exp_rat_producer.py",
    "formal_coverage_inventory.json",
    "formal_receipt.py",
    "formal_status_gate.py",
    "gaussian_certificate.py",
    "gaussian_proof_identity.json",
    "inference_registry_v1.json",
    "int_cert_producer.py",
    "int_cert_proof_identity.json",
    "int_cert_release.py",
    "isolated_entry.py",
    "jackal-native",
    "jackal_calc.anb",
    "jackal_cert_check",
    "jackal_gaussian_check",
    "jackal_int_cert_check",
    "ln_rat_producer.py",
    "plugin/hermes/bundle_hash.py",
    "plugin/hermes/jackal_hermes",
    "plugin/hermes/profiles/core.json",
    "plugin/hermes/profiles/formal.json",
    "plugin/hermes/profiles/full.json",
    "plugin/hermes/schemas/jackal_agent_profile.schema.json",
    "plugin/hermes/server.py",
    "plugin/hermes/tools.json",
    "program/inventory_safe_v1.json",
    "range_proof_identity.json",
    "receipt_verify.py",
    "release/claim/inference_registry_v1.json",
    "release/claim/unit_registry_v1.json",
    "release_validate.py",
    "sin_rat_producer.py",
    "sqrt_rat_producer.py",
    "tanh_rat_producer.py",
    "tools/anubis_program_verify.py",
    "tools/decision_verify.py",
    "tools/domain_pack_verify.py",
    "tools/exact_verify.py",
    "tools/test_exists_verify.py",
    "unit_registry_v1.json",
)


class GenerationError(RuntimeError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parts() -> list[Path]:
    found = sorted((ROOT / "pkg").glob(f"{PACKAGE_BASE}.part*"))
    if not found:
        raise GenerationError("vendored-parts-missing")
    for index, path in enumerate(found):
        if path.name != f"{PACKAGE_BASE}.part{index:02d}":
            raise GenerationError(f"vendored-parts-noncontiguous:{path.name}")
    return found


def package_bytes() -> bytes:
    data = b"".join(path.read_bytes() for path in parts())
    if len(data) != PACKAGE_SIZE or sha256(data) != PACKAGE_SHA256:
        raise GenerationError("vendored-package-identity")
    return data


def package_records() -> tuple[dict[str, bytes], dict[str, str], str]:
    regular: dict[str, bytes] = {}
    with tarfile.open(fileobj=io.BytesIO(package_bytes()), mode="r:gz") as archive:
        for member in archive.getmembers():
            if member.isfile():
                if not member.name.startswith(f"{PACKAGE_DIR}/"):
                    raise GenerationError(f"package-top-level:{member.name}")
                source = archive.extractfile(member)
                if source is None:
                    raise GenerationError(f"package-member-read:{member.name}")
                regular[member.name.removeprefix(f"{PACKAGE_DIR}/")] = source.read()
    sums_bytes = regular.pop("SHA256SUMS", None)
    if sums_bytes is None:
        raise GenerationError("package-sha256sums-missing")
    sums: dict[str, str] = {}
    for line in sums_bytes.decode("utf-8").splitlines():
        digest, separator, raw_path = line.partition("  ")
        relative = raw_path.removeprefix("./")
        if separator != "  " or len(digest) != 64 or not relative or relative in sums:
            raise GenerationError("package-sha256sums-shape")
        sums[relative] = digest
    if set(sums) != set(regular):
        raise GenerationError("package-sha256sums-closure")
    for relative, digest in sums.items():
        if sha256(regular[relative]) != digest:
            raise GenerationError(f"package-member-identity:{relative}")
    return regular, sums, sha256(sums_bytes)


def generated_documents() -> tuple[bytes, str]:
    regular, sums, sums_sha = package_records()
    missing = sorted(set(IDENTITY_PATHS) - set(sums))
    if missing:
        raise GenerationError(f"identity-path-missing:{missing}")
    catalog = json.loads(regular["plugin/hermes/tools.json"])
    inventory = json.loads(regular["capability_inventory_v1.json"])
    catalog_names = [row["name"] for row in catalog.get("tools", [])]
    inventory_names = [row["name"] for row in inventory.get("tools", [])]
    if (
        len(catalog_names) != 41
        or len(set(catalog_names)) != 41
        or catalog_names != inventory_names
        or inventory.get("tool_count") != 41
        or inventory.get("unique_tool_count") != 41
    ):
        raise GenerationError("package-capability-inventory")
    identities = {relative: sums[relative] for relative in IDENTITY_PATHS}
    epoch = {
        "identities": identities,
        "non_claims": [
            "SHA-256 identifies exact bytes; it is not authorship, authenticity, or mathematical correctness",
            "candidate bytes do not assert a public v1.7.3 tag or release asset",
            "architect trust-surface signoff is required before tag or release publication",
            "the core package does not reference this plugin",
        ],
        "plugin": {"name": "jackal-verified", "version": PLUGIN_VERSION},
        "schema": "jackal-plugin-epoch-receipt-v1",
        "skill": {
            "name": "jackal-verified-computation",
            "sha256": sha256(SKILL_PATH.read_bytes()),
            "version": SKILL_VERSION,
        },
        "tools": {
            "count": 41,
            "inventory_path": "capability_inventory_v1.json",
            "inventory_sha256": sums["capability_inventory_v1.json"],
            "source": "schemas.py generated from the vendored package catalog",
        },
        "upstream": {
            "alignment_receipt": {
                "commit": ALIGNMENT_RECEIPT_COMMIT,
                "path": "release/evidence/package_alignment_v173_candidate.json",
            },
            "build_commit": UPSTREAM_BUILD_COMMIT,
            "package": {
                "file_count": len(regular) + 1,
                "name": PACKAGE_BASE,
                "sha256": PACKAGE_SHA256,
                "sha256sums_sha256": sums_sha,
                "size_bytes": PACKAGE_SIZE,
            },
            "release_epoch": "v1.7.3",
            "release_state": "candidate",
            "release_url": None,
            "repository": "https://github.com/AnubisQuantumCipher/jackal",
            "tag": None,
            "verified_from": "two byte-identical local builds plus the immutable alignment receipt",
        },
        "vendored": {
            "note": "ordered part concatenation equals the reproducible candidate tarball bytes; no public release is asserted",
            "parts": [f"pkg/{path.name}" for path in parts()],
            "sha256": PACKAGE_SHA256,
        },
    }
    epoch_bytes = (json.dumps(epoch, indent=1, sort_keys=True) + "\n").encode("utf-8")
    identity_lines = [BEGIN, "APPROVED_IDENTITIES = {"]
    for relative, digest in identities.items():
        identity_lines.append(f"    {relative!r}: {digest!r},")
    identity_lines.extend(["}", END])
    return epoch_bytes, "\n".join(identity_lines)


def render_tools(source: str, block: str) -> str:
    package_pin_pattern = re.compile(r'^PKG_SHA256 = "[0-9a-f]{64}"$', re.MULTILINE)
    if len(package_pin_pattern.findall(source)) != 1:
        raise GenerationError("tools-package-pin")
    source = package_pin_pattern.sub(f'PKG_SHA256 = "{PACKAGE_SHA256}"', source, count=1)
    if BEGIN in source or END in source:
        if source.count(BEGIN) != 1 or source.count(END) != 1:
            raise GenerationError("tools-generated-markers")
        start = source.index(BEGIN)
        finish = source.index(END) + len(END)
        return source[:start] + block + source[finish:]
    pattern = re.compile(r"APPROVED_IDENTITIES = \{.*?\n\}\n\n_EXECUTABLES", re.DOTALL)
    if pattern.search(source) is None:
        raise GenerationError("tools-identity-block-missing")
    return pattern.sub(block + "\n\n_EXECUTABLES", source, count=1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--write", action="store_true")
    modes.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    try:
        epoch, block = generated_documents()
        tools_expected = render_tools(TOOLS_PATH.read_text(encoding="utf-8"), block)
        if arguments.write:
            EPOCH_PATH.write_bytes(epoch)
            TOOLS_PATH.write_text(tools_expected, encoding="utf-8")
        elif EPOCH_PATH.read_bytes() != epoch or TOOLS_PATH.read_text(encoding="utf-8") != tools_expected:
            raise GenerationError("generated-file-drift")
    except (GenerationError, OSError, ValueError, json.JSONDecodeError, tarfile.TarError) as error:
        print(f"EPOCH_GENERATION_REFUSED reason={error}")
        return 1
    print(f"EPOCH_GENERATION_PASS tools=41 identities={len(IDENTITY_PATHS)} package_sha256={PACKAGE_SHA256}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
