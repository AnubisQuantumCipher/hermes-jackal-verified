# Provenance — jackal-verified v6.0.0 candidate

## Status

This document binds an unpublished candidate. It does not assert that a
JACKAL v1.7.3 tag, JACKAL v1.7.3 GitHub Release, jackal-verified v6.0.0 tag,
or jackal-verified v6.0.0 GitHub Release exists.

## Upstream candidate root

| Field | Value |
|---|---|
| Repository | `https://github.com/AnubisQuantumCipher/jackal` |
| Source build commit | `5311e9e265b75e2d10ee3da9ccd298283b1a0672` |
| Source tree | `77968dcf1591df6c18413923b076e818b6b53f19` |
| Worktree at build | clean |
| Package builder SHA-256 | `109b5461e509c5c31cc426455ae0976afbe9a400b9eba9f3bd5028ccb1015723` |
| Alignment receipt | `release/evidence/package_alignment_v173_candidate.json` at commit `d50308ac4325a564d89596f190186b62e6f4de22` |
| Release state | `v1.7.3-candidate` |
| Public tag or asset | none asserted |

## Candidate package

| Field | Value |
|---|---|
| Name | `jackal-v1.7.3-macos-arm64.tar.gz` |
| SHA-256 | `9100bc77abd02dfdc1449d23d6fa211e041ad34b38e545024a9311bdb16cf93e` |
| Bytes | 158,362,324 |
| Extracted bytes | 555,505,387 |
| Files including `SHA256SUMS` | 106 |
| Internal `SHA256SUMS` SHA-256 | `fa2080c7c50a669c28b08e17739f559d1e22b4d8ca95fe31355e90f6b3c5aecf` |
| Capability inventory SHA-256 | `b4ce27e112e0a75683fc408c98f1c403ff92799ed5b792d569b7c3e61bea9b88` |

Two clean builds from the source build commit produced byte-identical
tarballs and byte-identical extracted directories. The plugin stores the
candidate package as:

```text
pkg/jackal-v1.7.3-macos-arm64.tar.gz.part00  99,614,720 bytes
pkg/jackal-v1.7.3-macos-arm64.tar.gz.part01  58,747,604 bytes
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
inventory          capability_inventory_v1.json    b4ce27e112e0a75683fc408c98f1c403ff92799ed5b792d569b7c3e61bea9b88
Lean audit         evidence/lean_admission_audit_v173.json
                                                   aff8108945c49282c9cfd089d207c65591e7cbc8387bf2d1d531194389fd00c2
program verifier   tools/anubis_program_verify.py  a0dbf14b6157de3f2f789fa54190e015575bafc2e1182ba3d30186afcb45e89a
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

- 13 live package-unification tests with zero skips;
- 60 package-parity rows with zero failures;
- 216 Codex-plugin repository tests;
- isolated Codex live acceptance discovering 41 tools and observing exact,
  formal-bounded, producer-refused, claim-bundle verified, and formal-receipt
  verified outcomes;
- Codex wrapper aggregate SHA-256
  `0690f76e219196642c8f7c502c48d74a4b3dcac074bc50aa4a624a4e0b081acf`.

Those are bounded executions over the named bytes, not universal correctness
claims.

## Lean admission audit

The packaged `jackal-lean-admission-audit-v1` record has semantic digest
`7544475a5db94a21ac4f33b1d66f6b849cb2b8331f787f87ac3bb96bde5c7ba7`.
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
