# Provenance — jackal-verified v4.0.0

## Upstream root (immutable public release)

| Field | Value |
|---|---|
| Repository | `https://github.com/AnubisQuantumCipher/jackal-calc` |
| Tag | `v1.6.0` (tag object `af5d94a622838f1ebf0f826d02426b26857f68e5`) |
| Commit | `19b763e9451276e72c7511ec8ba42bf828d096f6` |
| Release asset | `jackal-v1.6.0-macos-arm64.tar.gz` |
| Asset SHA-256 | `0cdacf56bb83d65454330973280cde7da0b9262d6163ccd7efbbbb47bc88e39a` |
| Asset size | 79,519,523 bytes |
| Acquisition | unauthenticated public download; hash matched the release `SHA256SUMS` and the release receipt JSON |

The vendored copy at `pkg/jackal-v1.6.0-macos-arm64.tar.gz` is
byte-identical to that public asset; admission re-verifies the pin, the
`EPOCH.json` receipt, the package's internal `SHA256SUMS`, and the
30-row `APPROVED_IDENTITIES` table before any tool executes.

## Key pinned identities (full table: `EPOCH.json`)

```text
evaluator  jackal-native         8617ad087f859f58a1e742032588cd011c9716bab8fe5477e7b0a318dfded88e
checker    jackal_cert_check     05c3518b836f239712f897c483a2ddadad9f544e0887b1b7bb1424a27289de8a
checker    jackal_gaussian_check ccac690bf916f71a4e3baeb0622dac19aa47e3ca4af858c0800c295581ecfacb
frontend   jackal_hermes         e63bb66caf3fd0890c5f4de22a22c9a4a44796de6fbb03f5ef46f1b1d5ed3082
source     jackal_calc.anb       34870c66276005272d9ab48a3cc1261ba0e0317a9e45089b1acfb07acc0efd25
```

## Trust chain (acyclic)

```text
core release (tag v1.6.0, commit 19b763e9…)
  → core package sha256 0cdacf56…
  → this plugin commit (pinned in the GitHub Release notes)
  → MANIFEST.json (jackal-plugin-manifest-v1, seals every tracked file)
  → EPOCH.json  (jackal-plugin-epoch-receipt-v1, binds upstream → vendored → skill)
  → bundled skill jackal-verified-computation v5.0.0
```

The core package does not reference this plugin.

## Upstream evidence scope (stated exactly)

The upstream release was sealed locally on Apple Silicon macOS with
`GATES: PASS (38 gates)` — Lean proof builds, 200/200 black-box
acceptance, 108/108 hostile claim matrix, 42/42 receipt-semantic
mutations, A→B→A tamper gates over seven claim trust layers, and 47/47
package parity (all 33 tools exercised from the fresh-extracted
package). Upstream hosted CI runs a documented subset (Lean source
closures + an engine-free claim-kernel admission job). This plugin's own
CI (macos-14, Apple Silicon) runs the plugin batteries above against the
exact vendored bytes.

`hermes plugins doctor <plugin> --ci` on Hermes v0.20.2 reports
`registrations: 33 tool(s)`.

## Non-claims

SHA-256 identifies exact bytes only. Finite campaigns are bounded
evidence, not universal theorems. No source→native refinement, no
end-to-end formally verified executable, no replay prevention without an
external nonce store, no real-world input truth, no universal soundness
outside admitted fragments.
