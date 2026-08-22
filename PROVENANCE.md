# Provenance — jackal-verified v6.0.0 candidate

## Status

This document binds an unpublished candidate. It does not assert that a
JACKAL v1.7.3 tag, JACKAL v1.7.3 GitHub Release, jackal-verified v6.0.0 tag,
or jackal-verified v6.0.0 GitHub Release exists.

## Upstream candidate root

| Field | Value |
|---|---|
| Repository | `https://github.com/AnubisQuantumCipher/jackal` |
| Source build commit | `efece744fdc3f1362422b0ef999398702774e8e3` |
| Source tree | `3a40227d6255321e7d3956ba02f943ab37ce1d6f` |
| Worktree at build | clean |
| Package builder SHA-256 | `9fefb2741888c6d9bb268f2a4199a1bb776f52a333878ee900175615e2701801` |
| Alignment receipt | `release/evidence/package_alignment_v173_candidate.json` at commit `a482d94e7de72f1ea1562379749bac34e5406380` |
| Release state | `v1.7.3-candidate` |
| Public tag or asset | none asserted |

## Candidate package

| Field | Value |
|---|---|
| Name | `jackal-v1.7.3-macos-arm64.tar.gz` |
| SHA-256 | `d0c2c87d357aa9cae6551343215910032f30259e4a6b40cde0b64687cba107d4` |
| Bytes | 158,362,724 |
| Extracted bytes | 555,507,658 |
| Files including `SHA256SUMS` | 106 |
| Internal `SHA256SUMS` SHA-256 | `12e52bfd0b3fe3fc2f6f4c8acf4bd6d0d3c47be1ae9c334e8ef4b068c24e07e3` |
| Capability inventory SHA-256 | `b26606faab2acba95d42b964787b75029b84df3038cc047ae00e5234378aebd4` |

Two clean builds from the source build commit produced byte-identical
tarballs and byte-identical extracted directories. The plugin stores the
candidate package as:

```text
pkg/jackal-v1.7.3-macos-arm64.tar.gz.part00  99,614,720 bytes
pkg/jackal-v1.7.3-macos-arm64.tar.gz.part01  58,748,004 bytes
```

Admission hashes the ordered concatenation. There is no acquisition URL
because no public v1.7.3 release asset is asserted.

## Selected runtime identities

The complete 53-row table is generated into `EPOCH.json` and `tools.py`
from the package's internal `SHA256SUMS`.

```text
evaluator          jackal-native                   f11f3a429aa64dc0f09eb930e82bc3250e19eeb5a8a74b26b86683fafd72a655
range checker      jackal_cert_check               f7a82524d082b51a8d66f9bed653b9c8da51b5424386659c9048b9c0ae276545
Gaussian checker   jackal_gaussian_check           ccac690bf916f71a4e3baeb0622dac19aa47e3ca4af858c0800c295581ecfacb
integral checker   jackal_int_cert_check           f8347cbd18d520852aff56920d41f5e5b496ff192f584e41d84d1a818ff29617
Hermes frontend    plugin/hermes/jackal_hermes     e63bb66caf3fd0890c5f4de22a22ce61cc1aec52d4c82432171d87dc6a4d0ec3
Hermes catalog     plugin/hermes/tools.json         53c823f07db512b82e01a4f132ff43be426b4b227c436e8853c5144ae0504e87
inventory          capability_inventory_v1.json    b26606faab2acba95d42b964787b75029b84df3038cc047ae00e5234378aebd4
Lean audit         evidence/lean_admission_audit_v173.json
                                                   0dac3023ad4b53c83df8f659b195d4d027445916eaf38c34422c3f0637c062d5
program verifier   tools/anubis_program_verify.py  fd00b87501c980401583bbb9d1e87f7409fd04cd686b7d470e0aa380bf38195d
program policy     program/inventory_safe_v1.json  361979bf89b7c71a4b2c692d64756548833a2c363c269511b037726cab3ebacb
approved Z3        /opt/homebrew/bin/z3             ae6c8df33db9c9ae9a80b6044e77cd66529a141d8b25f0620f1e89b409594f48
```

## Capability alignment

The candidate package inventory and packaged Hermes catalog each contain the
same ordered 41 unique names. The plugin's generated `schemas.py` contains
the same 41 schemas, and `plugin.yaml` declares the same name set. The
inventory records kernel, Hermes, and Codex exposure, supported fragments,
status classes, refusal boundaries, and dependency identities.

The package-alignment receipt records:

- 14 live package-unification tests with zero skips;
- 60 package-parity rows with zero failures;
- 217 Codex-plugin repository tests;
- isolated Codex live acceptance discovering 41 tools and observing exact,
  formal-bounded, producer-refused, claim-bundle verified, and formal-receipt
  verified outcomes;
- Codex wrapper aggregate SHA-256
  `c69610183dd207fe8c476e686554f51454b83d96815ad63bea0e4f39dbadf0ac`.

Those are bounded executions over the named bytes, not universal correctness
claims.

## Lean admission audit

The packaged `jackal-lean-admission-audit-v1` record has semantic digest
`62991b7eb7dbe4ecbbff1562a9fee788de2c944bec9c4ff5cd11aecd81510e1e`.
It binds 42 tracked Lean source files, 27 unique release theorems, the three
checker binaries above, and exact theorem-axiom output.

Observed audit result:

- zero logical admissions;
- zero repository axiom declarations;
- zero unexpected or forbidden constructs;
- each release theorem reports only `propext`, `Classical.choice`, and
  `Quot.sound`;
- 37 `noncomputable` occurrences are classified as non-admissions;
- two allowlisted `implemented_by` occurrences are dump-only runtime mirrors
  and are outside the three checker roots.

A fresh full Lean build completed 17,369 jobs with exit status 0. The build
emitted non-fatal warnings; this record does not claim a warning-free build.

## Plugin generation and sealing

`scripts/generate_epoch.py` independently checks package size/hash, split
part continuity, tar layout, complete internal-manifest closure, exact
inventory/catalog equality, and all selected package identities. It generates
`EPOCH.json` and the identity table in `tools.py`.

`scripts/gen_schemas.py` generates `schemas.py` from the packaged catalog.
`MANIFEST.json` seals the plugin repository files after generation. The
bundled skill is v7.0.0; its exact SHA-256 is stored in `EPOCH.json` and is
checked by generation/tests. Package admission does not prove that a human or
agent obeyed the skill.

The program verifier's approved Z3 4.15.4 binary was built for macOS 26. Full
positive program-verification CI therefore uses the `macos-26` arm64 runner.
CI downloads Homebrew's Tahoe bottle by blob digest
`9f57f90f63a0995a9b56b6f4c94a1c29bd8fd9a474e09f78cba7f64aaf25708c`
and separately verifies the binary SHA-256 above before installation. Z3 is a
runtime replay dependency, not part of the vendored JACKAL tarball.

## Residual boundary

SHA-256 identifies exact bytes only. Neither local build observation nor a
hash authenticates the builder. The Lean audit does not prove the compiler,
Lean kernel, native-code extraction, operating system, hardware, or supply
chain. Program-evidence verification intentionally leaves policy-construct
totality, source-to-VC, SMT-to-CNF, source-native refinement, runtime behavior,
and universal language soundness unproved. Candidate evidence is not release
authority.
