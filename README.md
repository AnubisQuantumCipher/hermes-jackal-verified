# JACKAL Verified — Hermes plugin

[![CI](https://github.com/AnubisQuantumCipher/hermes-jackal-verified/actions/workflows/ci.yml/badge.svg)](https://github.com/AnubisQuantumCipher/hermes-jackal-verified/actions/workflows/ci.yml)
![Platform](https://img.shields.io/badge/platform-macOS%20arm64-lightgrey)
![License](https://img.shields.io/badge/license-MIT-blue)

> [!IMPORTANT]
> **Production-alignment status (2026-08-22):** the mechanically verified
> [v6.0.0 candidate](https://github.com/AnubisQuantumCipher/hermes-jackal-verified/tree/936dab4458d4618f4ecf56c2da5c9f5cdbb9aef4)
> exposes exactly **41 tools** and binds the JACKAL v1.7.3 candidate package.
> The latest published plugin release remains **v5.0.0 with 34 tools** while
> trust-surface sign-off is pending. Everything below the next heading is the
> published v5 release reference; those historical 34-tool statements are not
> the current candidate count.

## Published release reference — v5.0.0 (34 tools)

Typed, receipt-bearing access to the sealed **JACKAL v1.7.0 Mathematical
Evidence Kernel** from Hermes: **34 tools**, every call executed inside an
admitted, hash-pinned private snapshot of the exact public release
package.

## Trust chain (acyclic)

```text
JACKAL v1.7.0 tag/commit (jackal @ 89ee68dcfae72a1ce9b079ea5cf60665c98f7abc)
  → public core package  jackal-v1.7.0-macos-arm64.tar.gz
    sha256 21c7ede586f30a58772f321f7dbb36ab66213e199785489f99133710ac56096e
  → this plugin's vendored copy (two raw byte parts under pkg/ — GitHub's
    100 MiB single-file limit; admission verifies the CONCATENATION equals
    the published asset byte-for-byte)
  → plugin release commit (pinned in the GitHub Release notes)
  → plugin MANIFEST.json + EPOCH.json (machine-readable epoch receipt)
  → bundled skill jackal-verified-computation v6.0.0
```

The core package never references this plugin; the plugin pins the core.

## Published v5.0.0: what its 34 tools are

- **10 proof-carrying formal lanes** — `jackal_range_bound`,
  `jackal_gaussian_integral`, the certified composed integral
  `jackal_integrate_bound_cert` (v1.7.0), and the pure-Q fragments
  `jackal_{sqrt,exp,ln,sin,cos,atan,tanh}_rat_bound`. An accepted result
  is `formal-bounded` with a canonical `jackal-formal-receipt-v1` whose
  embedded certificate is re-executed by the pinned Lean-proved checker
  (`request_bound_certified_release`; Gaussian:
  `gaussian_integral_check_sound`; composed integral: `int_cert_sound`
  via the compiled `jackal_int_cert_check`). Anything outside an
  admitted fragment refuses — never downgrades. The weaker float lane
  `jackal_integrate_bound` stays `bounded` and is NOT the certified
  lane.
- **21 honest weaker/exact lanes** — `jackal_exact`, `jackal_evaluate`,
  `jackal_diff`, `jackal_integrate`, `jackal_integrate_adaptive`,
  `jackal_integrate_bound`, `jackal_solve`, and the fourteen exact-CAS
  certificate lanes (`jackal_canon`, `jackal_poly_canon`,
  `jackal_poly_eq`, `jackal_poly_gcd`, `jackal_ratfunc_canon`,
  `jackal_roots_isolate`, `jackal_alg_sign`, `jackal_alg_cmp`,
  `jackal_xgcd`, `jackal_mod_pow`, `jackal_mod_inv`, `jackal_crt`,
  `jackal_divides`, `jackal_prime_cert`). Statuses (`exact`, `checked`,
  `estimated`, `bounded`, `model-based`, `refused`, `indeterminate`)
  pass through verbatim; inflation is structurally impossible.
- **2 claim-kernel front doors (v1.6.0)** — `jackal_claim` compiles a
  typed request into a content-addressed `jackal-claim-bundle-v1`
  evidence graph; `jackal_verify_bundle` independently replays a bundle
  under CALLER-pinned epoch/root-proposition/policy/time and recomputes
  every hash, rule, assurance axis, consequence floor, and rendering.
- **1 receipt verifier** — `jackal_verify_receipt` re-runs the
  variant-selected pinned checker on the embedded certificate bytes;
  no outer digest is ever sufficient.

Tool schemas are **generated** from the vendored package's own
`plugin/hermes/tools.json` (`scripts/gen_schemas.py`); CI regenerates
and requires byte equality, so the registered surface cannot drift from
the sealed upstream surface.

## Security model

1. **Admission** (once per process): tarball SHA-256 equals the pin AND
   the machine-readable `EPOCH.json` receipt; safe extraction into a
   0700 private tempdir (no traversal, no non-regular members, no
   Apple-Double); the package's internal `SHA256SUMS` verifies every
   file with none missing and none extra; the `APPROVED_IDENTITIES`
   table re-verifies 34 trust-bearing files byte-for-byte; Mach-O arm64
   magic on the four native binaries; executables locked to 0500.
2. **Per call**: TOCTOU — the frontend, server, tools.json, engine, and
   both checkers are re-hashed before AND after every invocation;
   subprocesses run `shell=False`, `stdin=DEVNULL`, restricted `PATH`,
   private `HOME`.
3. **Fail closed**: any mismatch refuses with a stable
   `plugin-admission-failed` / `plugin-toctou-*` class. The A→B→A gate
   (`tests/aba_recheck_gate.py`) proves the identity-enforcement pair is
   load-bearing — and that even with it disabled, the upstream package's
   own bundle-hash and evaluator-identity layers still refuse tampered
   bytes (defense in depth, mechanically demonstrated).

## Install

```bash
# Pin the EXACT full 40-character release commit from the v5.0.0
# GitHub Release notes — never a floating branch:
hermes plugins install AnubisQuantumCipher/hermes-jackal-verified \
  --force --ref <FULL-40-CHAR-RELEASE-COMMIT> --enable

hermes plugins doctor jackal-verified --ci
# expected: registrations: 34 tool(s)
```

**Start a NEW Hermes session after install/upgrade** — tool schemas load
once per session.

Requirements: Apple Silicon macOS (the vendored engine and checkers are
arm64 Mach-O; no cross-platform native execution is claimed), Python
3.11+. After installation everything runs locally — no first-call
network fetch.

## Usage sketches

```text
"what is 0.1 + 0.2 exactly"            → jackal_exact       → exact 3/10
"derivative of x^3, checked"           → jackal_diff        → checked
"enclose sqrt(x) on [2,3] with proof"  → jackal_sqrt_rat_bound → formal-bounded + receipt
"integral of sin(x) on [0,1], proven"  → jackal_integrate_bound_cert → formal-bounded + receipt
"is 3^100 mod 7 below 7, as evidence"  → jackal_claim       → claim bundle
"replay this bundle independently"     → jackal_verify_bundle → verified | refused
```

## Migrating from v4.0.0 (33 tools)

Purely additive: every v4.0.0 tool keeps its exact name and schema
(`COMPAT_FLOOR_PASS frozen_tools=31 live_tools=34` upstream). New in
v5.0.0: `jackal_integrate_bound_cert` — call it instead of
`jackal_integrate_bound` when you need a Lean-checked `formal-bounded`
composed enclosure over the certified fragment
(`num/var/neg/add/sub/mul/div/pow/sin/cos/abs` in `x`; everything else
refuses). Upstream `rat`/`jackal_exact` `approx=` is now a rendering of
the exact rational (issue jackal#4). Three v3.0.0 names/shapes
still do not exist (`jackal_differentiate` → `jackal_diff`;
`jackal_claim_card` → `jackal_claim`; mode-based `jackal_exact` args →
`{"expression": "..."}`). Formal receipts issued by older epochs keep
verifying under their original caller-pinned epoch/request
expectations.

## Tests and verification

```bash
python3 tests/test_plugin.py        # unit battery (20 cases)
python3 tests/test_plugin_v2.py     # poison battery (43 rows, also under -O)
python3 tests/aba_recheck_gate.py   # A→B→A identity-enforcement gate
python3 tests/parts_discovery_test.py  # split-part discovery fail-closed battery
python3 scripts/fresh_install_smoke.py
python3 scripts/verify_manifest.py
python3 scripts/release_audit.py
python3 scripts/gen_schemas.py && git diff --exit-code schemas.py
```

CI (`.github/workflows/ci.yml`) runs all of the above on `macos-14`
(Apple Silicon) against the exact vendored package bytes.

## Provenance

- Upstream: `AnubisQuantumCipher/jackal` tag `v1.7.0`, commit
  `89ee68dcfae72a1ce9b079ea5cf60665c98f7abc`; the vendored tarball is
  byte-identical to the unauthenticated public release asset (sha256
  `21c7ede586f30a58772f321f7dbb36ab66213e199785489f99133710ac56096e`).
- Key identities (full table in `EPOCH.json` and `PROVENANCE.md`):
  evaluator `jackal-native`
  `20b80827d3c5c2a5d0d5d6f5a84c692f230fb0f55b9c7d1fcad02a1d0b3a1083`,
  proved checker `jackal_cert_check`
  `05c3518b836f239712f897c483a2ddadad9f544e0887b1b7bb1424a27289de8a`,
  Gaussian checker `jackal_gaussian_check`
  `ccac690bf916f71a4e3baeb0622dac19aa47e3ca4af858c0800c295581ecfacb`,
  composed-integral checker `jackal_int_cert_check`
  `c858e3bfc0ff2809a808170caabbf090077cb54996e76f065dbcd26ffb067d49`.
- Upstream local evidence: `GATES: PASS (43 gates)` on the release
  bytes, including 202/202 black-box, 108/108 hostile claim matrix, and
  49/49 package parity over the v1.7.0 package — see the upstream
  release's evidence assets.

## Non-claims

SHA-256 identifies exact bytes — not authorship, authenticity, or
mathematical correctness. Finite hostile campaigns are strong bounded
evidence, not universal theorems. No source→native formal refinement, no
end-to-end formally verified executable, no replay prevention without an
external nonce store, no claim that supplied inputs are true in the
world, no universal soundness outside admitted fragments. See
`SECURITY.md` and the upstream `PROVENANCE.md` for the full boundary.

## License

MIT. Upstream JACKAL package: see `THIRD_PARTY_NOTICES.md`.
