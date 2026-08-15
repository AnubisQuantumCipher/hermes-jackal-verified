# JACKAL Verified for Hermes

[![CI](https://github.com/AnubisQuantumCipher/hermes-jackal-verified/actions/workflows/ci.yml/badge.svg)](https://github.com/AnubisQuantumCipher/hermes-jackal-verified/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Apple Silicon](https://img.shields.io/badge/platform-Apple%20Silicon-lightgrey.svg)](#platform-support)

**JACKAL Verified turns Hermes Agent into an assurance-aware STEM computation system.** It combines seven typed native tools with a companion skill that teaches Hermes when to request exact arithmetic, a checked derivative, a numerical estimate, a **proof-carrying formal enclosure**, or an explicitly model-based result.

**v2.0.0 — the formal lane is proof-carrying.** `jackal_range_bound` now releases `status=formal-bounded` only when a **Lean-proved certificate checker** (packaged alongside the evaluator) accepts the certificate the evaluator emitted for the exact request. Checker acceptance is connected by the theorem `cert_check_sound` to a `Runs`-derivation enclosure of the exact semantics over the mechanized operator fragment; anything outside that fragment refuses rather than releasing a value. Both binaries ship in one vendored, hash-verified release archive (byte-identical to the public jackal-calc v1.1.0 release asset), admitted into a private snapshot before use — a plain clone works offline. Weaker lanes (`exact`/`checked`/`estimated`/`model-based`) keep their epistemic class and can never be relabeled formal.

The plugin does not merely return numbers. It returns canonical `jackal-hermes-receipt-v2` receipts that bind the request commitment, epistemic status, result, residual non-claims, and exact evaluator + checker executable identities. A **formal receipt carries the exact certificate** the checker accepted; `jackal_verify_receipt` re-admits the pinned package and **re-runs the Lean-proved checker (`jackal_cert_check`) on those exact certificate bytes**, then binds every self-reported field — enclosure, request commitment, expression commitment, certificate digest, operator set, derived status — to what the checker actually accepted. No receipt-authored field is load-bearing, so a recomputed outer digest cannot forge a formal claim (this closes a false accept present through 2.0.1; see `CHANGELOG.md` 2.0.2). The checksum detects modification; it is not a signature or hostile-author authentication mechanism.

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

### Verify the vendored public package

```bash
shasum -a 256 pkg/jackal-v1.2.0-macos-arm64.tar.gz
```

Expected:

```text
3b63e86bd9d2cffafa33dde813c40919cc754343db2232b1c33072a3ec41e0a7
```

The plugin verifies this archive plus its complete internal inventory, evaluator, checker, architecture, and modes before execution from a private snapshot.

## Natural-language usage

Users do not normally call the skill or tool names themselves. In a new session, ask naturally:

### Exact arithmetic

> Compute `C(10000,5000)` exactly. Use deterministic computation, validate the receipt, and report the digit count and instrument identity.

### Checked symbolic differentiation

> Differentiate `x^(x^x)`. Release only a checked result and preserve the distinction between numeric checking and proof.

### Certified integration

> Compute a certified enclosure for `exp(-100000000*(x-0.1234567)^2)` from `0` to `1`, no wider than `1e-8`. Do not substitute an estimate if certification fails. Validate the receipt.

Representative bounded-lane result:

```text
status=bounded
enclosure=[0.00017724538401736711, 0.00017724538656304582]
width=2.54567870147486e-12
receipt_validation=valid
instrument_sha256=820c0722e46a0800115c404ea1c9251c6f72fe8c6897bdabe437f342f9310b6c
```

### Range analysis

> Can `1/x` be certified over `[-1,1]`? Use a range bound and treat refusal as an answer.

JACKAL refuses because the denominator interval contains zero. The plugin preserves that refusal rather than manufacturing a principal value.

### Model-based calculation

> Produce a projectile claim card for speed 20 m/s, angle 45 degrees, and gravity 9.80665 m/s². Validate its canonical fingerprint and list assumptions and non-claims.

## Receipt contract

Every computation returns `jackal-hermes-receipt-v2` with exactly:

```json
{
  "schema": "jackal-hermes-receipt-v2",
  "operation": "jackal_integrate",
  "request": {},
  "result": {},
  "instrument": {
    "name": "jackal",
    "sha256": "820c0722e46a...",
    "checker_sha256": "2186b43f8e45..."
  },
  "receipt_sha256": "..."
}
```

The receipt digest is SHA-256 over canonical UTF-8 JSON of the first five fields: sorted keys, compact separators, and non-finite JSON numbers forbidden.

Validation is deliberately two-layered:

1. **Integrity:** schema, exact keyset, canonical digest, and instrument identity.
2. **Semantics:** operation/status compatibility, required result fields, non-release invariants, ordered finite enclosures, requested-tolerance compliance, and claim-card fingerprint/model consistency.
3. **Formal re-check:** `formal-bounded` receipts carry the canonical nested `jackal-formal-receipt-v1`; validation re-admits the pinned package, runs the independent verifier, re-runs the proved checker on its embedded certificate, and binds the request, enclosure, commitments, operators, coverage, theorem, and evaluator/checker/plugin identities to the checker verdict.

A recomputed outer digest does not make a semantically malformed or forged formal result valid. The digest is an unkeyed integrity checksum, not author authentication; formal validity comes from re-executing the proved checker.

See [`skills/jackal-verified-computation/references/receipt-contract.md`](skills/jackal-verified-computation/references/receipt-contract.md) for the compact contract.

## Security architecture

- Seven curated tools; no generic command, endpoint, filesystem, or shell surface.
- `subprocess.run` with an argument list and `shell=False`.
- Restricted child environment.
- Public JACKAL v1.2.0 package pinned by archive SHA-256, safe extraction, complete internal `SHA256SUMS`, evaluator/checker SHA-256, Mach-O arm64, and executable-mode checks before execution from a private snapshot.
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

The regression suites cover:

- exact rational output and receipt validation;
- a full 3,011-digit `2^10000` comparison;
- checked exponent-tower differentiation;
- bounded narrow-Gaussian integration;
- fail-closed singular-range refusal;
- independent claim-card fingerprint recomputation;
- receipt tampering;
- semantic poison with a recomputed digest;
- cross-operation status forgery with a recomputed digest;
- missing exact/check metadata, contradictory refusal release, and model/request mismatch after recomputed digests;
- substituted executable identity;
- public-path A→B→A substitution while execution remains bound to a private admitted snapshot;
- the four recomputed-digest formal receipt forgeries found against v2.0.0/v2.0.1;
- stripped-certificate and substituted-enclosure refusal;
- load-bearing A→B→A of the master formal re-check gate, including `python3 -O` parity;
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
├── pkg/jackal-v1.2.0-macos-arm64.tar.gz  # evaluator + proved checker + formal verifier
├── jackal_formal/              # shared release validator/status/coverage gates
├── skills/
│   └── jackal-verified-computation/
│       ├── SKILL.md            # automatic assurance-selection discipline
│       └── references/receipt-contract.md
├── tests/test_plugin.py
├── tests/test_plugin_v2.py
├── tests/aba_recheck_gate.py
├── PROVENANCE.md
├── SECURITY.md
├── CONTRIBUTING.md
└── LICENSE
```

## Platform support

The plugin supports **Apple Silicon macOS only** because the pinned JACKAL v1.2.0 package contains Mach-O arm64 evaluator/checker artifacts. It fails closed if the archive, manifest, inventory, architecture, modes, evaluator, checker, or plugin manifest differs from the pinned identity.

Portable support should use one reviewed binary per platform with explicit OS/architecture selection and per-artifact digests. It must never fall back to an arbitrary `jackal` found on `PATH`.

## Evidence boundaries

JACKAL Verified makes strong but bounded claims:

- `exact` means exact within the supported grammar, operation, and compute budget.
- `checked` means sampled numerical challenge, not symbolic identity proof.
- `bounded` means an enclosure conditional on JACKAL's stated IEEE basic-operation and ≤2 ULP libm model and a tested—not end-to-end mechanized—implementation.
- `formal-bounded` means the independent v1.2 verifier re-ran the packaged proved checker on the canonical receipt's embedded certificate and the plugin re-bound the exact request/result/coverage/instrument identities; it still depends on the stated ModelTCB and does not prove source-to-native refinement.
- `model-based` means conditional on stated assumptions, not observed physical reality.
- SHA-256 identifies and checksums bytes; it does not authenticate an author or prove mathematical validity.
- Passing finite campaigns does not establish universal correctness.

The upstream JACKAL interval model includes Lean mechanization, but this plugin does not claim an end-to-end formal proof from Anubis source through the embedded native executable.

## Provenance

The vendored package is the public JACKAL CALC `v1.2.0` release artifact:

- Upstream: https://github.com/AnubisQuantumCipher/jackal-calc
- Commit: `cc533906182c887a8617cc741b91b926bcb41e22`
- Archive SHA-256: `3b63e86bd9d2cffafa33dde813c40919cc754343db2232b1c33072a3ec41e0a7`
- Evaluator SHA-256: `820c0722e46a0800115c404ea1c9251c6f72fe8c6897bdabe437f342f9310b6c`
- Proved checker SHA-256: `2186b43f8e45b7b3e55e189d64e92f15999664f5194caed929d14b29b006f59b`
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
