# Third-party notices

## JACKAL candidate package

- Source: `https://github.com/AnubisQuantumCipher/jackal`
- Source build commit:
  `a281a6c4675381e99ee185d012eb35127bcd7c3c`
- Alignment receipt commit:
  `1f1e628955c5ab805d13273f8fb9c618747d6f7c`
- Candidate artifact: `jackal-v1.7.3-macos-arm64.tar.gz`
- SHA-256:
  `cafab1555d3ea7cf207fd5564464fbe35dfa9288cdd650fe226d9f7633254196`
- Size: 158,362,119 bytes
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
  `ae6c8df33db9ec5971749daf943567c204ed9f2d3001edbd46599f4540d7d6`
- CI Homebrew bottle SHA-256:
  `9f57f90f63a0995a9b56b6f4c94a1c29bd8fd9a474e09f78cba7f64aaf25708c`
- Vendoring: not vendored; CI provisions and verifies the exact external
  replay dependency

## Hermes Agent

This plugin targets the Hermes Agent plugin API (`manifest_version: 1`,
`api_version: 1`). Hermes is a separate work; nothing from Hermes is
vendored here.
