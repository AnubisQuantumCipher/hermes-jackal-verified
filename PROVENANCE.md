# Provenance and Evidence

This document binds the public plugin release to its upstream computation instrument and records the gates that establish plugin behavior.

## Trust chain

```text
JACKAL source commit
→ pinned Anubis compiler and reproducible upstream build
→ reproducible JACKAL v1.3.0 release archive
→ archive manifest + evaluator/producer/two-checker identities
→ native Hermes plugin adapter
→ formal/poison suites + A→B→A gate
→ Hermes Plugin Doctor
→ live fresh-session invocation and receipt validation
```

## Embedded instrument

| Field | Value |
|---|---|
| Upstream repository | `https://github.com/AnubisQuantumCipher/jackal-calc` |
| Upstream release | `v1.3.0` |
| Source commit | `696e190388f7a720eb907b08affb9266fb3f5f50` |
| `jackal_calc.anb` SHA-256 | `5d43df8de01adb86bb10a0a6cea28fb79faf03cd58be51654c3fa88c653e4a40` |
| Release asset | `jackal-v1.3.0-macos-arm64.tar.gz` |
| Architecture | Mach-O 64-bit arm64 |
| Archive size | 79,161,763 bytes |
| Archive SHA-256 | `13e6a3cb6145522ffe8323bc01b84a505b8647c3f2017f43e4813c38e9b5a7ac` |
| Evaluator SHA-256 | `820c0722e46a0800115c404ea1c9251c6f72fe8c6897bdabe437f342f9310b6c` |
| Proved checker SHA-256 | `2186b43f8e45b7b3e55e189d64e92f15999664f5194caed929d14b29b006f59b` |
| Gaussian producer SHA-256 | `20c24622b786940a8e82198f2364fb7593e761902fa0736289b179642f1e4306` |
| Gaussian checker SHA-256 | `11c741f04b811aa8621db4da5c5dc05e292ead8c0e6a854739f6068757470612` |
| License | MIT |

Upstream release URL:

`https://github.com/AnubisQuantumCipher/jackal-calc/releases/tag/v1.3.0`

The upstream release includes `RELEASE-SHA256SUMS`; the archive contains a complete internal `SHA256SUMS`. Anonymous download, GitHub asset metadata, and the vendored plugin bytes agree on the archive digest.

## Reproducibility inherited from JACKAL

JACKAL's own `PROVENANCE.md` records the content-addressed Anubis compiler pin `anubis-a733565f237d`; the evaluator is unchanged, while the Gaussian checker is built by the pinned Lean toolchain. The v1.3.0 archive rebuilt byte-for-byte identically with a fixed-metadata ustar writer. This plugin does not rebuild JACKAL during installation; it vendors and verifies that sealed archive.

The plugin verifies the archive, safe extraction, complete internal inventory, evaluator/producer/checker digests, Mach-O arm64 architecture, and modes before execution from a private snapshot. A mismatch produces no computation result.

## Plugin verification performed before publication

### Unit and poison suite

Command:

```bash
python3 tests/test_plugin.py
```

Observed:

The release gate requires the legacy 14-test adapter suite, the v2 formal/poison suite under normal Python and `python3 -O`, and the formal-recheck A→B→A mutation gate.

Covered controls:

- exact rational receipt;
- full large-integer output;
- checked symbolic derivative;
- narrow-peak bounded integration;
- singular-domain refusal;
- claim-card hash recomputation;
- tampered receipt rejection;
- reversed enclosure rejection after recomputed receipt digest;
- cross-operation status rejection after recomputed receipt digest;
- missing exact/check metadata, contradictory refusal release, and model/request mismatch rejection after recomputed digests;
- substituted executable rejection;
- private-snapshot resistance to public-path A→B→A substitution;
- exact rejection of the four recomputed-digest formal receipt forgeries;
- checker re-execution over the embedded certificate;
- A→B→A proof that removing the master formal re-check re-admits those forgeries;
- malformed-input rejection.
- registration of all seven tools, the bundled skill, and the automatic routing policy.

### Hermes loader integration

Command:

```bash
hermes plugins doctor . --ci
```

Observed:

```text
OK: runtime discovery, manifest parsing, import, and registration passed
registrations: 7 tool(s), 0 hook(s)
```

### Fresh-session live proof

A new standalone Hermes session (`20260814_181716_d5b5d4`) loaded personal skill v1.1.0, invoked the typed `jackal_range_bound` tool, and passed the exact returned receipt to typed `jackal_verify_receipt`.

Request:

```text
expression=x, lower=1, upper=2
requested_assurance=formal-bounded
```

Observed:

```text
status=formal-bounded
enclosure=[1,2]
theorem=cert_check_sound
certificate_sha256=c80a3a9175bac71b58268e373e472d43f68a97aad81a0eb8234ba50b0575b2e7
receipt_sha256=5cf17733fba230b8dc727aa735492c399570e825025d2da17360de81c68d215b
receipt_valid=true
evaluator_sha256=820c0722e46a0800115c404ea1c9251c6f72fe8c6897bdabe437f342f9310b6c
checker_sha256=2186b43f8e45b7b3e55e189d64e92f15999664f5194caed929d14b29b006f59b
errors=[]
```

The stored session transcript contains both typed calls and the verifier's `valid=true` result. An earlier fresh session (`20260814_181339_df5499`) altered a longer certificate while reconstructing the second tool argument; the verifier rejected it with digest mismatch and checker refusal. That rejection is retained as observed fail-closed behavior, not counted as a pass. The valid receipt above is evidence only for its exact request and recorded TCB, not a universal JACKAL proof.

### Standalone repository smoke test

Command:

```bash
python3 scripts/fresh_install_smoke.py
```

Observed:

```text
FRESH_INSTALL_PASS tools=7 skills=1 prompt_sections=1 exact=3/10 receipt_valid=true
```

## Non-claims

- The plugin does not prove universal correctness of JACKAL, Anubis, Python, Hermes, IEEE-754, or platform libm.
- Plugin tests establish the tested adapter behavior, not correctness for every expression.
- JACKAL's bounded lane is conditional on its disclosed arithmetic/libm model and tested implementation.
- The upstream Lean development mechanizes checker soundness for the declared fragment. The native evaluator is an untrusted certificate producer; the compiler/runtime and Lean kernel remain recorded TCB surfaces rather than universally proved components.
- SHA-256 establishes byte identity and receipt integrity, not semantic truth by itself.
