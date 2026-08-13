# JACKAL Verified for Hermes

[![CI](https://github.com/AnubisQuantumCipher/hermes-jackal-verified/actions/workflows/ci.yml/badge.svg)](https://github.com/AnubisQuantumCipher/hermes-jackal-verified/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Apple Silicon](https://img.shields.io/badge/platform-Apple%20Silicon-lightgrey.svg)](#platform-support)

**JACKAL Verified turns Hermes Agent into an assurance-aware STEM computation system.** It combines seven typed native tools with a companion skill that teaches Hermes when to request exact arithmetic, a checked derivative, a numerical estimate, a certified enclosure, or an explicitly model-based result.

The plugin does not merely return numbers. It returns canonical, tamper-evident receipts that bind the request, epistemic status, result, residual non-claims, and exact JACKAL executable identity.

```text
natural-language request
        ↓
Hermes automatically loads the companion skill
        ↓
assurance selection: exact | checked | estimated | bounded | model-based
        ↓
typed native plugin tool
        ↓
content-pinned JACKAL executable
        ↓
canonical receipt + semantic validation
        ↓
honestly qualified answer
```

## Why this exists

Language models can decide which computation is needed while still being unreliable at the arithmetic layer or at describing how strongly a result is supported. JACKAL Verified separates those responsibilities:

- **Hermes** understands the user's objective and selects a tool.
- **JACKAL** performs deterministic computation.
- **The plugin** enforces executable identity, structured output, assurance preservation, and receipts.
- **The skill** prevents an estimate from being described as a bound, a sampled check as a proof, or a model fingerprint as physical truth.

## Capabilities

| Tool | Purpose | Returned status |
|---|---|---|
| `jackal_exact` | Exact rationals, addition/multiplication/powers of large integers, factorials, and binomial coefficients | `exact` |
| `jackal_evaluate` | Deterministic finite-real expression evaluation | `estimated` / IEEE-f64 |
| `jackal_differentiate` | Symbolic differentiation released only after JACKAL's numeric sample check | `checked` |
| `jackal_integrate` | Explicit `fast_estimate`, `adaptive_estimate`, or `bounded` integration | `estimated` or `bounded` |
| `jackal_range_bound` | Certified superset of an expression's range over an interval | `bounded` |
| `jackal_claim_card` | Projectile-model result with assumptions, non-claims, canonical preimage, sensitivity, and fingerprint | `model-based` |
| `jackal_verify_receipt` | Independent receipt digest and semantic validation | validation verdict |

### Assurance is explicit

`jackal_integrate` requires the caller to choose an assurance tier:

- `fast_estimate` — fixed-grid Simpson with a disclosed Richardson estimate;
- `adaptive_estimate` — adaptive Simpson with refusal semantics, still not a mathematical bound;
- `bounded` — outward-rounded interval enclosure under JACKAL's stated IEEE/libm model.

A bounded request is **never silently downgraded**. If certification fails, the receipt says `refused` or `indeterminate`; it does not substitute a weaker number.

## Installation

### Requirements

- Apple Silicon macOS (`arm64`).
- A current Hermes Agent installation.
- A fresh Hermes session after enabling the plugin, because tool schemas remain stable during a conversation.

Install directly from GitHub:

```bash
hermes plugins install https://github.com/AnubisQuantumCipher/hermes-jackal-verified.git
hermes plugins enable jackal-verified
hermes plugins doctor jackal-verified --ci
```

The repository includes the companion skill under `skills/jackal-verified-computation/`. Hermes registers it read-only as `jackal-verified:jackal-verified-computation`. A compact routing policy is also injected into each fresh session, so users can ask naturally without knowing the skill or tool name; the full namespaced skill remains available for explicit loading and inspection.

Then start a new session:

```bash
hermes
```

No API key, network service, or JACKAL installation is needed at runtime. The computation path is local and offline.

### Three integration homes

The project deliberately supports the same instruction at three scopes:

1. **Personal Hermes skill:** an editable copy under `~/.hermes/skills/` can carry machine-specific preferences.
2. **Plugin-bundled skill:** this repository registers the read-only namespaced skill `jackal-verified:jackal-verified-computation` and injects a compact automatic routing policy into every fresh enabled session.
3. **Agent-neutral standing instructions:** [`skills/AGENTS-SNIPPET.md`](skills/AGENTS-SNIPPET.md) can be copied into `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, or another agent's supported instruction file.

The public snippet does not pretend other agents can call Hermes tools directly. It teaches assurance selection and reporting discipline; an actual integration still needs an authorized tool bridge.

### Verify the embedded executable

```bash
shasum -a 256 bin/jackal-native
```

Expected:

```text
609de1035be62a5183ad6555b97402567c9e4539b41806a5b52974f6be9030ae
```

The plugin repeats this identity check before and after every invocation.

## Natural-language usage

Users do not normally call the skill or tool names themselves. In a new session, ask naturally:

### Exact arithmetic

> Compute `C(10000,5000)` exactly. Use deterministic computation, validate the receipt, and report the digit count and instrument identity.

### Checked symbolic differentiation

> Differentiate `x^(x^x)`. Release only a checked result and preserve the distinction between numeric checking and proof.

### Certified integration

> Compute a certified enclosure for `exp(-100000000*(x-0.1234567)^2)` from `0` to `1`, no wider than `1e-8`. Do not substitute an estimate if certification fails. Validate the receipt.

Observed v1.0.0 result:

```text
status=bounded
enclosure=[0.00017724538401736711, 0.00017724538656304582]
width=2.54567870147486e-12
receipt_validation=valid
instrument_sha256=609de1035be62a5183ad6555b97402567c9e4539b41806a5b52974f6be9030ae
```

### Range analysis

> Can `1/x` be certified over `[-1,1]`? Use a range bound and treat refusal as an answer.

JACKAL refuses because the denominator interval contains zero. The plugin preserves that refusal rather than manufacturing a principal value.

### Model-based calculation

> Produce a projectile claim card for speed 20 m/s, angle 45 degrees, and gravity 9.80665 m/s². Validate its canonical fingerprint and list assumptions and non-claims.

## Receipt contract

Every computation returns `jackal-hermes-receipt-v1` with exactly:

```json
{
  "schema": "jackal-hermes-receipt-v1",
  "operation": "jackal_integrate",
  "request": {},
  "result": {},
  "instrument": {
    "name": "jackal",
    "sha256": "609de1035be62a...",
    "size": 1386400
  },
  "receipt_sha256": "..."
}
```

The receipt digest is SHA-256 over canonical UTF-8 JSON of the first five fields: sorted keys, compact separators, and non-finite JSON numbers forbidden.

Validation is deliberately two-layered:

1. **Integrity:** schema, exact keyset, canonical digest, and instrument identity.
2. **Semantics:** known status, ordered finite enclosure, requested-tolerance compliance, and claim-card fingerprint recomputation.

An attacker cannot make a reversed enclosure valid merely by recomputing the outer receipt digest.

See [`skills/jackal-verified-computation/references/receipt-contract.md`](skills/jackal-verified-computation/references/receipt-contract.md) for the compact contract.

## Security architecture

- Seven curated tools; no generic command, endpoint, filesystem, or shell surface.
- `subprocess.run` with an argument list and `shell=False`.
- Restricted child environment.
- Content-pinned executable; SHA-256 checked before and after execution.
- Expression-length, output-size, and runtime bounds.
- Finite-number admission and interval-order validation.
- Explicit status vocabulary: `exact`, `estimated`, `checked`, `bounded`, `model-based`, `refused`, `indeterminate`.
- Refusal-preserving behavior with no stale-success fallback.
- Independent claim-card fingerprint recomputation.
- No privileged Hermes capabilities and no core-tool overrides.

Native Hermes plugins execute with the user's authority; they are not sandboxed. Review the source and install only releases whose digests you trust. See [`SECURITY.md`](SECURITY.md).

## Tests and verification

Run the adapter and poison suite:

```bash
python3 tests/test_plugin.py
```

The twelve tests cover:

- exact rational output and receipt validation;
- a full 3,011-digit `2^10000` comparison;
- checked exponent-tower differentiation;
- bounded narrow-Gaussian integration;
- fail-closed singular-range refusal;
- independent claim-card fingerprint recomputation;
- receipt tampering;
- semantic poison with a recomputed digest;
- cross-operation status forgery with a recomputed digest;
- substituted executable identity;
- malformed and hostile inputs.
- plugin registration of all seven tools, the bundled skill, and automatic routing policy.

Validate against Hermes's real plugin loader and registry:

```bash
hermes plugins doctor . --ci
```

Expected:

```text
OK: runtime discovery, manifest parsing, import, and registration passed
registrations: 7 tool(s), 0 hook(s)
```

Exercise the repository exactly as an installed standalone plugin:

```bash
python3 scripts/fresh_install_smoke.py
```

The smoke test registers all tools, the bundled skill, and the automatic routing section, then invokes exact arithmetic and validates its receipt.

CI runs the unit/poison suite, manifest consistency checks, Python compilation, and embedded-binary digest verification on Apple Silicon macOS.

## Repository layout

```text
.
├── plugin.yaml
├── __init__.py                 # Hermes registration
├── schemas.py                  # model-visible typed schemas
├── tools.py                    # fail-closed adapter and receipt validator
├── bin/jackal-native           # content-pinned JACKAL v1.0.0 arm64 binary
├── skills/
│   └── jackal-verified-computation/
│       ├── SKILL.md            # automatic assurance-selection discipline
│       └── references/receipt-contract.md
├── tests/test_plugin.py
├── PROVENANCE.md
├── SECURITY.md
├── CONTRIBUTING.md
└── LICENSE
```

## Platform support

The initial release supports **Apple Silicon macOS only** because JACKAL v1.0.0 currently publishes that native artifact. The plugin fails closed if the embedded executable is missing, non-executable, or has the wrong digest.

Portable support should use one reviewed binary per platform with explicit OS/architecture selection and per-artifact digests. It must never fall back to an arbitrary `jackal` found on `PATH`.

## Evidence boundaries

JACKAL Verified makes strong but bounded claims:

- `exact` means exact within the supported grammar, operation, and compute budget.
- `checked` means sampled numerical challenge, not symbolic identity proof.
- `bounded` means an enclosure conditional on JACKAL's stated IEEE basic-operation and ≤2 ULP libm model and a tested—not end-to-end mechanized—implementation.
- `model-based` means conditional on stated assumptions, not observed physical reality.
- SHA-256 authenticates bytes; it does not prove mathematical validity.
- Passing finite campaigns does not establish universal correctness.

The upstream JACKAL interval model includes Lean mechanization, but this plugin does not claim an end-to-end formal proof from Anubis source through the embedded native executable.

## Provenance

The embedded executable is the official JACKAL CALC `v1.0.0` release artifact:

- Upstream: https://github.com/AnubisQuantumCipher/jackal-calc
- Commit: `ae9a6f5174546610c1a71d113db0c199cbbcca0c`
- Binary SHA-256: `609de1035be62a5183ad6555b97402567c9e4539b41806a5b52974f6be9030ae`
- License: MIT

See [`PROVENANCE.md`](PROVENANCE.md) and [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Contributing

Contributions are welcome, particularly:

- explicit Linux and Windows JACKAL artifacts with sealed identities;
- additional typed JACKAL model tools;
- independent oracle adapters that preserve disagreements;
- receipt-schema evolution with strict backward compatibility;
- stronger negative controls and cross-platform CI.

Read [`CONTRIBUTING.md`](CONTRIBUTING.md) before changing an assurance or validation boundary.

## License

MIT. See [`LICENSE`](LICENSE).

This is an independent community plugin for [Hermes Agent](https://github.com/NousResearch/hermes-agent). No endorsement by Nous Research is implied.
