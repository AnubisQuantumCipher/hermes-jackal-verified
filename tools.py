"""Hermes-native adapter over the reproducible JACKAL v1.7.3 candidate.

Forty-one typed tools are generated from the vendored package catalog. Every
call invokes the package's `jackal_hermes` frontend inside an admitted private
snapshot of the exact candidate tarball bytes split under `pkg/`.

Trust model:
  T0  the plugin ships ONE upstream artifact: the candidate package, pinned
      by PKG_SHA256 and cross-checked against EPOCH.json at admission;
  T1  admission verifies the tarball hash, safe-extracts to a private
      0700 tempdir, verifies EVERY file against the package's internal
      SHA256SUMS (no missing, no extra), then re-verifies the
      APPROVED_IDENTITIES table (executables, producers, verifiers,
      registries, inventory, proof identities) byte-for-byte and checks
      Mach-O arm64 magic on the four native binaries;
  T2  every tool call re-hashes the frontend + trust-bearing files
      before AND after execution (TOCTOU);
  T3  after requiring one JSON object with a status field, the adapter emits
      that parsed runtime object as JSON; plugin admission, argument-length,
      timeout, execution, and transport failures produce named local refusals;
  T4  formal-receipt, claim-bundle, structural, decision, and Anubis-program
      verification routes invoke their packaged checkers. Each route retains
      its catalog-declared ceiling and caller-pin requirements; program replay
      starts at the explicitly documented Z3/CNF/RUP boundary and never
      executes the compiled artifact.

The adapter adds NO mathematical behavior of its own.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import stat
import struct
import subprocess
import tarfile
import tempfile
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent

RELEASE_EPOCH = "v1.7.3"
# GitHub rejects single files >= 100 MiB, so the vendored candidate package is
# split into raw byte parts; admission concatenates them IN MEMORY and
# verifies PKG_SHA256 over the whole — the admitted bytes are exactly the
# reproducible candidate tarball. Parts are discovered fail-closed:
# `pkg/<name>.partNN` must be contiguous from part00 and must EXACTLY match
# the ordered `vendored.parts` list declared in the pinned EPOCH.json
# receipt — a gap, extra, or undeclared part refuses before any bytes are
# trusted.  PKG_TARBALL stays as a single-file OVERRIDE knob (tests / the
# A->B->A gate point it at forged tarballs); when set to a path that exists
# it takes precedence over the parts.
PKG_TARBALL = PLUGIN_ROOT / "pkg" / "jackal-v1.7.3-macos-arm64.tar.gz"
PKG_SHA256 = "c030076186791a551d7818412e39ea895da0f16a2fad88877554ff390c284d9c"
PKG_DIRNAME = "jackal-v1.7.3-macos-arm64"
EPOCH_RECEIPT = PLUGIN_ROOT / "EPOCH.json"

# Pinned identities inside the admitted package (from the package's own
# SHA256SUMS at seal time; re-verified from bytes at every admission).
# BEGIN GENERATED PACKAGE IDENTITIES
APPROVED_IDENTITIES = {
    'MANIFEST.sha256': '7baffdb7f1cb1d537c61549c2f9681202356707b5ea96ff9e9cd79ad1d103ba9',
    'atan_rat_producer.py': '824916bdb3420986f4a6eed8028760a96477e9e1df2febd03b9ca174216aef26',
    'capability_inventory_v1.json': '9b3003291d7c323af462406038dea61ece7ec1bb1bf57da1f619b70e4875c409',
    'claim_bundle_verify.py': 'e0fcb9540c730bd9bb492b528ed42d29d49fc775b3aa0f9b831b6264fd68fd22',
    'claim_kernel.py': '77b0f85ad5fb7214f88898b60ea29ea9fd7be740c38b655388444e6e5181f348',
    'claim_router.py': '02328cf177a0423bdc5cbca6ec0ea946bb0679bbd3dc6c24140d32598e575afb',
    'domain_packs/core/manifest.json': '8babbc2966f7a269a0aefe15495e83c70351795f63cc3468f75c36bb5046ee8a',
    'domain_packs/decision/manifest.json': '79b5d90d50c2343fdc93f1f92f0ea36bfa1e6c1c239ab6572aea8ad237ccbd65',
    'domain_packs/programming/manifest.json': 'a8668782c1be9553e80b044a70327a3f767779b6552a2d3401454d01aa1b43ba',
    'domain_packs/registry_v1.json': '1a3b2c95dcdc7c7337fbe0ecb34043b70c3697752d6dc585f45f3c7d4f1b0706',
    'evidence/compat_v173_floor.json': '5b4e78e1f2b3e1ed7d0459a12f229ffe27886c179198a656a5a9dc5343f8b45e',
    'evidence/lean_admission_audit_v173.json': 'b715e4e464893a66a1bc66144544d07643d1bdf5dbe6fb3b8bcbb8a88fc925a6',
    'exact_verify.py': '2c07e6257ce1524de3e31374371c6d5859dce710767156de2566ec77fa1883a7',
    'exp_rat_producer.py': '1997ed81dfbd26a6d45a6689c515832bfbae05435d07e3dd2d6f156c57668ec1',
    'formal_coverage_inventory.json': '6373641cd7833bb46a08f44acf683a119e0a637c8acb88d22797b81188d896b6',
    'formal_receipt.py': '235f85bcf5892939231fb8cfd51d74a6f5482b747e43dd3b546f57d021d40d35',
    'formal_status_gate.py': '6aacf6c1ff4f6d43cd055ac09a6a7d0d8007258c7901f6759a76ef15a29b7203',
    'gaussian_certificate.py': '20c24622b786940a8e82198f2364fb7593e761902fa0736289b179642f1e4306',
    'gaussian_proof_identity.json': '7d2ff9ed4934604eba30f3111a147d7e295fd79302f640f57aacd986a23e243c',
    'inference_registry_v1.json': 'c70b33d5aee8071b5125e6a5f8ffe5226fc22a137d920c17d9b3463968be13f0',
    'int_cert_producer.py': 'b4240fdac3c77b2abd751595303b2b3a0e4bebd492b2ae57fa5ccf052cd50af4',
    'int_cert_proof_identity.json': 'a8aefff85666d35cfd5412b10ae3d404260e91a98de53d5f0d2bb9f88f4ffbdf',
    'int_cert_release.py': '427c557ef18db2c70f4e3d9a746da359d2e503184508eab401b70a1424b3b587',
    'isolated_entry.py': '01ae7b5b7b21c2af1a32d384d5bb8ab6eb0656fe8133209b2ebb42d712bedf77',
    'jackal-native': 'f11f3a429aa64dc0f09eb930e82bc3250e19eeb5a8a74b26b86683fafd72a655',
    'jackal_calc.anb': 'f579b6f59bc024d24914487b0cd0f18ea43dea1be52708a05a66dc885d80bb4e',
    'jackal_cert_check': 'f7a82524d082b51a8d66f9bed653b9c8da51b5424386659c9048b9c0ae276545',
    'jackal_gaussian_check': 'ccac690bf916f71a4e3baeb0622dac19aa47e3ca4af858c0800c295581ecfacb',
    'jackal_int_cert_check': 'f8347cbd18d520852aff56920d41f5e5b496ff192f584e41d84d1a818ff29617',
    'ln_rat_producer.py': 'c88eb0153f0ec0ba401597a8945345e621a38df408bfd92a47a4b3abf7985740',
    'plugin/hermes/bundle_hash.py': '826aae22af717736e4d98a6746d5d9f6b6767544cf479e1fcf7a46c2d7ab8aee',
    'plugin/hermes/jackal_hermes': 'e63bb66caf3fd0890c5f4de22a22ce61cc1aec52d4c82432171d87dc6a4d0ec3',
    'plugin/hermes/profiles/core.json': '49f33ba23cca5ab940f1929604f61491bc914d092f291cda4fe4f06b37d042d3',
    'plugin/hermes/profiles/formal.json': '9be2b3144486311d9ba7f1d41c5033eb8e2553e9d12b71d46e512401f57a084b',
    'plugin/hermes/profiles/full.json': '0db937da01737bbc0341a591ecd23e55008d8ffc02368517c7d1e7da8b309dec',
    'plugin/hermes/schemas/jackal_agent_profile.schema.json': '3522c0c9b5fc4740eda1720647ed2055611313a4d9d144116f179419e439898e',
    'plugin/hermes/server.py': '4c42725d797ac78ed20d3e843e602b1c60c88bd13f74e06c65a6b4016b3b7daf',
    'plugin/hermes/tools.json': '53c823f07db512b82e01a4f132ff43be426b4b227c436e8853c5144ae0504e87',
    'program/inventory_safe_v1.json': '361979bf89b7c71a4b2c692d64756548833a2c363c269511b037726cab3ebacb',
    'range_proof_identity.json': '84963be9b0a8851a03a38ae71da558b3e9d2c37d9d55ad7da31afbd23188499c',
    'receipt_verify.py': '44f37a7db525e67dc994348eda5ae2ed75e8d0b6ec7ea1d4f86e3ee31c0f9396',
    'release/claim/inference_registry_v1.json': 'c70b33d5aee8071b5125e6a5f8ffe5226fc22a137d920c17d9b3463968be13f0',
    'release/claim/unit_registry_v1.json': 'd2d30dfe2a74d58a5ef31b551ea628106390bfccd72ad34d1cb37381c58d114c',
    'release_validate.py': '38c631570eaf581027489ae1a4eaf7f63c16f393df24f7b999119ef50c6dbff6',
    'sin_rat_producer.py': '978f8d508c0921b5d8227a24ee7c7b97373a6041e55e4923cd94617a94a061dd',
    'sqrt_rat_producer.py': '4bc95c331430d2350facfb19da9aba483ab7b3698754e7af2e5deb797e097926',
    'tanh_rat_producer.py': 'da03b6054dcdd3fe02588ec25fc7c201405e9d8ec5f3ab46ff45b49698ab5eb3',
    'tools/anubis_program_verify.py': 'ee32089a4a3501dced306630ecc8e63e8442c584cfedf0ac9f512ad95a65c831',
    'tools/decision_verify.py': 'f1ad7c9fbd4c1d899dbb4bebabbbeb97e97a56bd4b279ad7d8ec3722bf12e0f6',
    'tools/domain_pack_verify.py': '22984f511208af2d7a318f1a43306d95a4b0f61876d8b44f34f39a2ded6d573d',
    'tools/exact_verify.py': '2c07e6257ce1524de3e31374371c6d5859dce710767156de2566ec77fa1883a7',
    'tools/test_exists_verify.py': '598cb99e1eb70c9410ca87345efee346f73e43aaf3625427dca17ea04231caea',
    'unit_registry_v1.json': 'd2d30dfe2a74d58a5ef31b551ea628106390bfccd72ad34d1cb37381c58d114c',
}
# END GENERATED PACKAGE IDENTITIES

_EXECUTABLES = ("jackal-native", "jackal_cert_check", "jackal_gaussian_check",
                "jackal_int_cert_check")
_FRONTEND = "plugin/hermes/jackal_hermes"
_TOCTOU_FILES = (
    "plugin/hermes/jackal_hermes",
    "plugin/hermes/server.py",
    "plugin/hermes/tools.json",
    "plugin/hermes/bundle_hash.py",
    "jackal-native",
    "jackal_cert_check",
    "jackal_gaussian_check",
    "jackal_int_cert_check",
    "MANIFEST.sha256",
)


class JackalError(RuntimeError):
    """Fail-closed plugin-boundary error (never a downgraded answer)."""


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _discover_parts() -> tuple[Path, ...]:
    """Ordered vendored part files, fail closed.

    Rules: every `pkg/<tarball-name>.partNN` present on disk must form a
    contiguous run starting at part00, and the resulting ordered relative
    list must EQUAL the `vendored.parts` declaration in the pinned
    EPOCH.json receipt.  Any gap, duplicate index, extra file, undeclared
    part, or declared-but-missing part refuses.
    """
    base = PKG_TARBALL.name
    pkg_dir = PLUGIN_ROOT / "pkg"
    found: dict[int, Path] = {}
    for p in sorted(pkg_dir.glob(f"{base}.part*")):
        suffix = p.name[len(base):]
        m = re.fullmatch(r"\.part(\d{2,})", suffix)
        if m is None:
            raise JackalError(f"malformed part name: {p.name}")
        idx = int(m.group(1))
        if idx in found:
            raise JackalError(f"duplicate part index: {p.name}")
        found[idx] = p
    if not found:
        raise JackalError("no vendored package parts found")
    indices = sorted(found)
    if indices != list(range(len(indices))):
        raise JackalError(f"non-contiguous part indices: {indices}")
    ordered = tuple(found[i] for i in indices)
    try:
        declared = json.loads(EPOCH_RECEIPT.read_text()) \
            .get("vendored", {}).get("parts")
    except (OSError, json.JSONDecodeError) as exc:
        raise JackalError(f"epoch receipt unreadable: {exc}") from exc
    observed = [f"pkg/{p.name}" for p in ordered]
    if declared != observed:
        raise JackalError(
            f"vendored parts diverge from EPOCH.json: declared={declared} "
            f"observed={observed}")
    return ordered


def _package_bytes() -> bytes:
    """Exact candidate-package bytes: the single-file override if present,
    else the concatenation of the discovered, receipt-declared parts."""
    if PKG_TARBALL.is_file():
        return PKG_TARBALL.read_bytes()
    return b"".join(p.read_bytes() for p in _discover_parts())


def _arch_ok(path: Path) -> bool:
    """Require a Mach-O arm64 (or arm64 slice of a fat) binary."""
    with open(path, "rb") as f:
        head = f.read(8)
    if len(head) < 8:
        return False
    magic = struct.unpack(">I", head[:4])[0]
    if magic in (0xCFFAEDFE, 0xFEEDFACF):  # MH_MAGIC_64 little/big
        cputype = struct.unpack("<I", head[4:8])[0] \
            if magic == 0xCFFAEDFE else struct.unpack(">I", head[4:8])[0]
        return cputype == 0x0100000C  # CPU_TYPE_ARM64
    if magic in (0xCAFEBABE, 0xCAFEBABF):  # fat
        return True
    return False


def _check_epoch_receipt() -> dict:
    doc = json.loads(EPOCH_RECEIPT.read_text())
    if doc.get("schema") != "jackal-plugin-epoch-receipt-v1":
        raise JackalError("epoch-receipt-schema")
    up = doc.get("upstream", {}).get("package", {})
    if up.get("sha256") != PKG_SHA256 or \
            doc.get("vendored", {}).get("sha256") != PKG_SHA256:
        raise JackalError("epoch-receipt-package-mismatch")
    if doc.get("upstream", {}).get("release_epoch") != RELEASE_EPOCH:
        raise JackalError("epoch-receipt-epoch-mismatch")
    ids = doc.get("identities", {})
    for path, want in APPROVED_IDENTITIES.items():
        got = ids.get(path)
        if got is not None and got != want:
            raise JackalError(f"epoch-receipt-identity-mismatch: {path}")
    return doc


def _safe_extract(tar: tarfile.TarFile, dest: Path) -> None:
    for member in tar.getmembers():
        name = member.name
        if name.startswith("/") or ".." in Path(name).parts:
            raise JackalError(f"unsafe archive member: {name}")
        if "__MACOSX" in name or Path(name).name.startswith("._"):
            raise JackalError(f"apple-double member: {name}")
        if not (member.isreg() or member.isdir()):
            raise JackalError(f"non-regular archive member: {name}")
    tar.extractall(dest)


def _verify_internal_manifest(pkg: Path) -> None:
    sums = (pkg / "SHA256SUMS").read_text().splitlines()
    listed: dict[str, str] = {}
    for line in sums:
        if not line.strip():
            continue
        digest, _, name = line.partition("  ")
        listed[name.strip().lstrip("./")] = digest.strip()
    on_disk = {str(p.relative_to(pkg)) for p in pkg.rglob("*") if p.is_file()}
    on_disk.discard("SHA256SUMS")
    missing = sorted(set(listed) - on_disk)
    extra = sorted(on_disk - set(listed))
    if missing or extra:
        raise JackalError(
            f"package manifest mismatch: missing={missing[:5]} extra={extra[:5]}")
    for name, want in listed.items():
        if _sha(pkg / name) != want:
            raise JackalError(f"package file hash mismatch: {name}")


_ADMITTED: dict | None = None


def _admit_package() -> dict:
    """Admit the vendored tarball once per process; fail closed forever."""
    global _ADMITTED
    if _ADMITTED is not None:
        return _ADMITTED
    _check_epoch_receipt()
    blob = _package_bytes()
    digest = hashlib.sha256(blob).hexdigest()
    if digest != PKG_SHA256:
        raise JackalError(
            f"package identity mismatch: {digest} != {PKG_SHA256}")
    snapdir = Path(tempfile.mkdtemp(prefix="jackal-verified-"))
    os.chmod(snapdir, 0o700)
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tf:
        _safe_extract(tf, snapdir)
    pkg = snapdir / PKG_DIRNAME
    if not pkg.is_dir():
        raise JackalError("package directory missing after extraction")
    _verify_internal_manifest(pkg)
    for rel, want in APPROVED_IDENTITIES.items():
        target = pkg / rel
        if not target.is_file():
            raise JackalError(f"pinned file missing: {rel}")
        got = _sha(target)
        if got != want:
            raise JackalError(f"pinned identity mismatch: {rel}: {got}")
    for rel in _EXECUTABLES:
        if not _arch_ok(pkg / rel):
            raise JackalError(f"unsupported binary architecture: {rel}")
        os.chmod(pkg / rel, 0o500)
    for p in pkg.rglob("*.py"):
        os.chmod(p, 0o400)
    os.chmod(pkg / _FRONTEND, 0o500)
    _ADMITTED = {"root": pkg, "snapdir": snapdir}
    return _ADMITTED


def _toctou_digests(pkg: Path) -> dict[str, str]:
    return {rel: _sha(pkg / rel) for rel in _TOCTOU_FILES}


def _refusal(reason: str, detail: str = "") -> str:
    out = {"status": "refused", "reason": reason}
    if detail:
        out["detail"] = detail[:400]
    return json.dumps(out, indent=2, sort_keys=True)


def _call_upstream(tool: str, args: dict, timeout: int) -> str:
    try:
        adm = _admit_package()
    except JackalError as exc:
        return _refusal("plugin-admission-failed", str(exc))
    pkg = adm["root"]
    pre = _toctou_digests(pkg)
    for rel in _TOCTOU_FILES:
        want = APPROVED_IDENTITIES.get(rel)
        if want is not None and pre[rel] != want:
            return _refusal("plugin-toctou-pre", rel)
    env = {
        "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
        "HOME": str(adm["snapdir"]),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }
    try:
        proc = subprocess.run(
            [str(pkg / _FRONTEND), "call", tool,
             json.dumps(args, ensure_ascii=False)],
            capture_output=True, text=True, timeout=timeout,
            stdin=subprocess.DEVNULL, cwd=str(pkg), env=env, shell=False)
    except subprocess.TimeoutExpired:
        return _refusal("plugin-timeout", f"{tool} exceeded {timeout}s")
    except OSError as exc:
        return _refusal("plugin-exec-failed", str(exc))
    post = _toctou_digests(pkg)
    if post != pre:
        changed = sorted(k for k in pre if pre[k] != post[k])
        return _refusal("plugin-toctou-post", ",".join(changed))
    stdout = (proc.stdout or "").strip()
    if not stdout:
        return _refusal("plugin-empty-response",
                        (proc.stderr or "").strip()[:200])
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError:
        return _refusal("plugin-transport-malformed", stdout[:200])
    if not isinstance(parsed, dict) or "status" not in parsed:
        return _refusal("plugin-response-shape", stdout[:200])
    return json.dumps(parsed, indent=2, sort_keys=True, ensure_ascii=False)


_EXPRESSION_KEYS = ("expression",)


def make_handler(tool: str, timeout: int, max_chars: int):
    """Build the Hermes-facing handler for one upstream tool."""
    def handler(args: dict | None = None, **_ignored) -> str:
        request = dict(args or {})
        for key in _EXPRESSION_KEYS:
            value = request.get(key)
            if isinstance(value, str) and len(value) > max_chars:
                return _refusal("plugin-args-too-long",
                                f"{key} exceeds {max_chars} chars")
        return _call_upstream(tool, request, timeout)
    handler.__name__ = f"tool_{tool}"
    return handler
