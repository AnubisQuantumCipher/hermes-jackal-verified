# Provenance — jackal-verified v5.0.0

## Upstream root (immutable public release)

| Field | Value |
|---|---|
| Repository | `https://github.com/AnubisQuantumCipher/jackal-calc` |
| Tag | `v1.7.0` (tag object `9014369439d7e92590503f86afd0bfdb4f7aac8d`) |
| Commit | `89ee68dcfae72a1ce9b079ea5cf60665c98f7abc` |
| Release asset | `jackal-v1.7.0-macos-arm64.tar.gz` |
| Asset SHA-256 | `21c7ede586f30a58772f321f7dbb36ab66213e199785489f99133710ac56096e` |
| Asset size | 118,862,060 bytes |
| Acquisition | unauthenticated public download; hash matched the release `SHA256SUMS`, the release receipt JSON, and the local double-build of the release commit |

The vendored copy lives as two raw byte parts
(`pkg/jackal-v1.7.0-macos-arm64.tar.gz.part00` + `.part01` — GitHub
rejects single files ≥ 100 MiB); their concatenation is byte-identical
to that public asset; admission re-verifies the pin, the
`EPOCH.json` receipt, the package's internal `SHA256SUMS`, and the
34-row `APPROVED_IDENTITIES` table before any tool executes.

## Key pinned identities (full table: `EPOCH.json`)

```text
evaluator  jackal-native         20b80827d3c5c2a5d0d5d6f5a84c692f230fb0f55b9c7d1fcad02a1d0b3a1083
checker    jackal_cert_check     05c3518b836f239712f897c483a2ddadad9f544e0887b1b7bb1424a27289de8a
checker    jackal_gaussian_check ccac690bf916f71a4e3baeb0622dac19aa47e3ca4af858c0800c295581ecfacb
checker    jackal_int_cert_check c858e3bfc0ff2809a808170caabbf090077cb54996e76f065dbcd26ffb067d49
frontend   jackal_hermes         e63bb66caf3fd0890c5f4de22a22ce61cc1aec52d4c82432171d87dc6a4d0ec3
source     jackal_calc.anb       638d28dc9811bb9359af27a1bcc5427717cdf894902011fbb230dc18bac63776
```

(The v4.0.0 rendering of this table carried a transcription typo in the
frontend hash; the value above is re-derived from the vendored package's
own `SHA256SUMS` and matches `EPOCH.json` and `tools.py` exactly.)

## Trust chain (acyclic)

```text
core release (tag v1.7.0, commit 89ee68dc…)
  → core package sha256 21c7ede5…
  → this plugin commit (pinned in the GitHub Release notes)
  → MANIFEST.json (jackal-plugin-manifest-v1, seals every tracked file)
  → EPOCH.json  (jackal-plugin-epoch-receipt-v1, binds upstream → vendored → skill)
  → bundled skill jackal-verified-computation v6.0.0
```

The core package does not reference this plugin.

## Upstream evidence scope (stated exactly)

The upstream release was sealed locally on Apple Silicon macOS with
`GATES: PASS (43 gates)` — Lean proof builds (now including the
composed-integral checker `jackal_int_cert_check`, theorem
`int_cert_sound`), 202/202 black-box acceptance (including the
jackal-calc#4 `rat approx=` regression pair), 108/108 hostile claim
matrix, 42/42 receipt-semantic mutations, the int-cert 31-row
positive/refusal/poison matrix, int-cert A→B→A (enclosure guards
proof-load-bearing), 5/5 engine differential with an mpmath oracle, and
49/49 package parity (all 34 tools exercised from the fresh-extracted
v1.7.0 package). Upstream hosted CI runs a documented subset (Lean
source closures for all three checker lanes + an engine-free 34-tool
claim-kernel admission job). This plugin's own CI (macos-14, Apple
Silicon) runs the plugin batteries against the exact vendored bytes.

`hermes plugins doctor <plugin> --ci` is expected to report
`registrations: 34 tool(s)` (see the release notes for the observed
run).

## Non-claims

SHA-256 identifies exact bytes only. Finite campaigns are bounded
evidence, not universal theorems. No source→native refinement, no
end-to-end formally verified executable, no replay prevention without an
external nonce store, no real-world input truth, no universal soundness
outside admitted fragments. The upstream producer for the composed
integral is untrusted by design; its fidelity to the engine's float
`bound_step` is differential-tested, not proved.
