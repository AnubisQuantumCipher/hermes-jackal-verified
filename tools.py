"""JACKAL Verified — Hermes-native adapter over the sealed v1.7.0 package.

Thirty-four typed tools (see `schemas.py`, GENERATED from the vendored
package's own `plugin/hermes/tools.json`).  Every call is a fail-closed
pass-through into the upstream `jackal_hermes` frontend running INSIDE an
admitted private snapshot of the vendored release tarball (split into raw
byte parts under `pkg/`; their concatenation is the exact bytes published
and hash-verified as the public JACKAL v1.7.0 GitHub release asset).

Trust model:
  T0  the plugin ships ONE upstream artifact: the release tarball, pinned
      by PKG_SHA256 and cross-checked against EPOCH.json at admission;
  T1  admission verifies the tarball hash, safe-extracts to a private
      0700 tempdir, verifies EVERY file against the package's internal
      SHA256SUMS (no missing, no extra), then re-verifies the
      APPROVED_IDENTITIES table (executables, producers, verifiers,
      registries, inventory, proof identities) byte-for-byte and checks
      Mach-O arm64 magic on the four native binaries;
  T2  every tool call re-hashes the frontend + trust-bearing files
      before AND after execution (TOCTOU);
  T3  responses are returned VERBATIM: the upstream status/assurance
      lanes (`exact`, `checked`, `estimated`, `bounded`, `formal-bounded`,
      `model-based`, `refused`, `indeterminate`) pass through untouched —
      the adapter can refuse on its own behalf but can never upgrade;
  T4  verification tools (`jackal_verify_receipt`, `jackal_verify_bundle`)
      run the upstream independent verifiers, which re-execute the pinned
      Lean-proved checkers / dependency-free bundle replay on the
      embedded evidence bytes — no producer-authored field is trusted.

The adapter adds NO mathematical behavior of its own.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import stat
import struct
import subprocess
import tarfile
import tempfile
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent

RELEASE_EPOCH = "v1.7.0"
# GitHub rejects single files >= 100 MiB, so the vendored release tarball is
# split into raw byte parts; admission concatenates them IN MEMORY and
# verifies PKG_SHA256 over the whole — the admitted bytes are exactly the
# published release asset.  PKG_TARBALL stays as a single-file OVERRIDE knob
# (tests / the A->B->A gate point it at forged tarballs); when set to a path
# that exists it takes precedence over the parts.
PKG_PARTS = (
    PLUGIN_ROOT / "pkg" / "jackal-v1.7.0-macos-arm64.tar.gz.part00",
    PLUGIN_ROOT / "pkg" / "jackal-v1.7.0-macos-arm64.tar.gz.part01",
)
PKG_TARBALL = PLUGIN_ROOT / "pkg" / "jackal-v1.7.0-macos-arm64.tar.gz"
PKG_SHA256 = "21c7ede586f30a58772f321f7dbb36ab66213e199785489f99133710ac56096e"
PKG_DIRNAME = "jackal-v1.7.0-macos-arm64"
EPOCH_RECEIPT = PLUGIN_ROOT / "EPOCH.json"

# Pinned identities inside the admitted package (from the package's own
# SHA256SUMS at seal time; re-verified from bytes at every admission).
APPROVED_IDENTITIES = {
    "jackal-native":
        "20b80827d3c5c2a5d0d5d6f5a84c692f230fb0f55b9c7d1fcad02a1d0b3a1083",
    "jackal_cert_check":
        "05c3518b836f239712f897c483a2ddadad9f544e0887b1b7bb1424a27289de8a",
    "jackal_gaussian_check":
        "ccac690bf916f71a4e3baeb0622dac19aa47e3ca4af858c0800c295581ecfacb",
    "jackal_int_cert_check":
        "c858e3bfc0ff2809a808170caabbf090077cb54996e76f065dbcd26ffb067d49",
    "plugin/hermes/jackal_hermes":
        "e63bb66caf3fd0890c5f4de22a22ce61cc1aec52d4c82432171d87dc6a4d0ec3",
    "plugin/hermes/server.py":
        "4d67ae76edee3f771ced809520ed6df873c77def8cf410eb79145d61af1009b8",
    "plugin/hermes/tools.json":
        "6271d2cf75f9227f10a842599c59229e3178fb929840a325ce83b1b4df1dbc1f",
    "plugin/hermes/bundle_hash.py":
        "826aae22af717736e4d98a6746d5d9f6b6767544cf479e1fcf7a46c2d7ab8aee",
    "gaussian_certificate.py":
        "20c24622b786940a8e82198f2364fb7593e761902fa0736289b179642f1e4306",
    "int_cert_producer.py":
        "b4240fdac3c77b2abd751595303b2b3a0e4bebd492b2ae57fa5ccf052cd50af4",
    "int_cert_release.py":
        "5a1e94189bfb1199444cbd73d55ba30845563fd56ca7d898df37caed6330a1e8",
    "sqrt_rat_producer.py":
        "4bc95c331430d2350facfb19da9aba483ab7b3698754e7af2e5deb797e097926",
    "exp_rat_producer.py":
        "1997ed81dfbd26a6d45a6689c515832bfbae05435d07e3dd2d6f156c57668ec1",
    "ln_rat_producer.py":
        "c88eb0153f0ec0ba401597a8945345e621a38df408bfd92a47a4b3abf7985740",
    "sin_rat_producer.py":
        "978f8d508c0921b5d8227a24ee7c7b97373a6041e55e4923cd94617a94a061dd",
    "atan_rat_producer.py":
        "824916bdb3420986f4a6eed8028760a96477e9e1df2febd03b9ca174216aef26",
    "tanh_rat_producer.py":
        "da03b6054dcdd3fe02588ec25fc7c201405e9d8ec5f3ab46ff45b49698ab5eb3",
    "claim_kernel.py":
        "0e33bed664d4a07015bafc135940e9e1c0af7912c0ccb94d7a3523423e996c5b",
    "claim_router.py":
        "ccab2cce27770297698ae107c59a8d147d81c5f2ff0cd7d686a11d4390d095eb",
    "claim_bundle_verify.py":
        "79d579d1be966e857436f67012e0fc79304dce789a66f590d77a2d57ccd97954",
    "exact_verify.py":
        "2c07e6257ce1524de3e31374371c6d5859dce710767156de2566ec77fa1883a7",
    "inference_registry_v1.json":
        "e7c999c34312288fc35d4e1ecab2cef244dd447174283f0e132e8ebee7277672",
    "unit_registry_v1.json":
        "d2d30dfe2a74d58a5ef31b551ea628106390bfccd72ad34d1cb37381c58d114c",
    "jackal_calc.anb":
        "638d28dc9811bb9359af27a1bcc5427717cdf894902011fbb230dc18bac63776",
    "formal_coverage_inventory.json":
        "18ff7b1d428dbc6f807fd4de27751ba415b33ef0b356088d7fa316ed74bb0ba6",
    "range_proof_identity.json":
        "1b2d623904930d748bfbf489637e0e8aa720188e7d68f5250e5bd8f257b89a67",
    "gaussian_proof_identity.json":
        "7d2ff9ed4934604eba30f3111a147d7e295fd79302f640f57aacd986a23e243c",
    "int_cert_proof_identity.json":
        "f0323e312d8b0e05a7200546fd819fc191d5f146d359bb14efec5b1575f16844",
    "receipt_verify.py":
        "e28a103ff07276a2aee270d5dbe234423b6c55a4bb08c0d67c94c06c7e62307c",
    "release_validate.py":
        "794bb90f884dd0b538a43f92a34f01f01a1c0ee3255e380fc9fc8646d86acb20",
    "formal_receipt.py":
        "e8fe9ccbdee6122e859d42cb5873daf7de6d365a6adefa5754e1ffc7066f2978",
    "formal_status_gate.py":
        "6aacf6c1ff4f6d43cd055ac09a6a7d0d8007258c7901f6759a76ef15a29b7203",
    "isolated_entry.py":
        "33be0aeb16eded6d1e4fd99fb41db46c52f70276e90c83c9ad48af267e0c87aa",
    "MANIFEST.sha256":
        "1276817efaa48cf4b9a941caae8ef56fd78433babc918cc15970f6b4351800e4",
}

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


def _package_bytes() -> bytes:
    """Exact release-tarball bytes: the single-file override if present,
    else the concatenation of the vendored parts (fail closed on absence)."""
    if PKG_TARBALL.is_file():
        return PKG_TARBALL.read_bytes()
    missing = [str(p) for p in PKG_PARTS if not p.is_file()]
    if missing:
        raise JackalError(f"package part missing: {missing}")
    return b"".join(p.read_bytes() for p in PKG_PARTS)


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
