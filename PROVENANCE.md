# Provenance and Evidence

This document binds the public plugin release to its upstream computation instrument and records the gates that establish plugin behavior.

## Trust chain

```text
JACKAL source commit
→ pinned Anubis compiler and reproducible upstream build
→ official JACKAL v1.0.0 release binary
→ embedded binary digest
→ native Hermes plugin adapter
→ unit and poison suite
→ Hermes Plugin Doctor
→ live fresh-session invocation and receipt validation
```

## Embedded instrument

| Field | Value |
|---|---|
| Upstream repository | `https://github.com/AnubisQuantumCipher/jackal-calc` |
| Upstream release | `v1.0.0` |
| Source commit | `ae9a6f5174546610c1a71d113db0c199cbbcca0c` |
| `jackal_calc.anb` SHA-256 | `b74d078db6acc7b73f81001ed823643df037e4770b6062c15de411ff571f5384` |
| Release asset | `jackal-native` |
| Architecture | Mach-O 64-bit arm64 |
| Size | 1,386,400 bytes |
| Binary SHA-256 | `609de1035be62a5183ad6555b97402567c9e4539b41806a5b52974f6be9030ae` |
| License | MIT |

Upstream release URL:

`https://github.com/AnubisQuantumCipher/jackal-calc/releases/tag/v1.0.0`

The upstream release includes `SHA256SUMS`, and GitHub's release-asset metadata independently reports the same SHA-256 digest for `jackal-native`.

## Reproducibility inherited from JACKAL

JACKAL's own `PROVENANCE.md` records that repeated clean builds from the committed source under content-addressed Anubis compiler pin `anubis-a733565f237d` produced byte-identical native executables with the digest above. This plugin does not rebuild JACKAL during installation; it embeds and verifies that official artifact.

The plugin checks the digest immediately before execution and again after execution. A mismatch produces no computation result.

## Plugin verification performed before publication

### Unit and poison suite

Command:

```bash
python3 tests/test_plugin.py
```

Observed:

```text
Ran 12 tests
OK
```

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
- substituted executable rejection;
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

A new Hermes session automatically loaded `jackal-verified-computation`, invoked `jackal_integrate`, then invoked `jackal_verify_receipt`.

Request:

```text
certified enclosure for exp(-100000000*(x-0.1234567)^2)
over [0,1], tolerance 1e-8, no estimate fallback
```

Observed:

```text
status=bounded
enclosure=[0.00017724538401736711,0.00017724538656304582]
width=2.54567870147486e-12
receipt_validation=valid
instrument_sha256=609de1035be62a5183ad6555b97402567c9e4539b41806a5b52974f6be9030ae
```

The live session receipt was valid for that request. It is not a universal JACKAL proof.

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
- The upstream Lean development mechanizes the interval model, not the entire source-to-binary plugin chain.
- SHA-256 establishes byte identity and receipt integrity, not semantic truth by itself.
