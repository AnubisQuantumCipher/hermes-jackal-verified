# Third-party notices

## JACKAL candidate package

- Source: `https://github.com/AnubisQuantumCipher/jackal`
- Source build commit:
  `5311e9e265b75e2d10ee3da9ccd298283b1a0672`
- Alignment receipt commit:
  `d50308ac4325a564d89596f190186b62e6f4de22`
- Candidate artifact: `jackal-v1.7.3-macos-arm64.tar.gz`
- SHA-256:
  `9100bc77abd02dfdc1449d23d6fa211e041ad34b38e545024a9311bdb16cf93e`
- Size: 158,362,324 bytes
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
