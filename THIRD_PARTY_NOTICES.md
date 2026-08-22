# Third-party notices

## JACKAL candidate package

- Source: `https://github.com/AnubisQuantumCipher/jackal`
- Source build commit:
  `957ac893b243814d9059e6e104c21e0ce68e9ef5`
- Alignment receipt commit:
  `0bca7da98def582bb0ce34a7dfb9b540e599d1b1`
- Candidate artifact: `jackal-v1.7.3-macos-arm64.tar.gz`
- SHA-256:
  `b317849234208ab6f435e5bad1336e4bf4d039981811323e35138c2e0a4ee68d`
- Size: 158,363,755 bytes
- Vendored representation:
  `pkg/jackal-v1.7.3-macos-arm64.tar.gz.part00` and `.part01`
- Release state: unpublished `v1.7.3-candidate`; no public release URL is
  asserted
- License: MIT; see the upstream source repository and package notices

The two vendored files are ordered raw byte parts. Their concatenation is the
candidate artifact identified above.

## Z3 program-replay dependency

- Source: `https://github.com/Z3Prover/z3`
- Version: 4.15.4
- License: MIT
- Approved macOS 26 arm64 binary SHA-256:
  `ae6c8df33db9c9ae9a80b6044e77cd66529a141d8b25f0620f1e89b409594f48`
- CI Homebrew bottle SHA-256:
  `9f57f90f63a0995a9b56b6f4c94a1c29bd8fd9a474e09f78cba7f64aaf25708c`
- Vendoring: not vendored; CI provisions and verifies the exact external
  replay dependency

## Hermes Agent

This plugin targets the Hermes Agent plugin API (`manifest_version: 1`,
`api_version: 1`). Hermes is a separate work; nothing from Hermes is
vendored here.
