# JACKAL Verified for Hermes

[![CI](https://github.com/AnubisQuantumCipher/hermes-jackal-verified/actions/workflows/ci.yml/badge.svg)](https://github.com/AnubisQuantumCipher/hermes-jackal-verified/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: Apple Silicon](https://img.shields.io/badge/platform-Apple%20Silicon-lightgrey.svg)](#platform-support)

**JACKAL Verified turns Hermes Agent into an assurance-aware STEM computation system.** It combines ten typed native tools with a companion skill that teaches Hermes when to request exact arithmetic, a checked derivative, a numerical estimate, one of **four proof-carrying formal enclosures**, or an explicitly model-based result.

**v3.0.0 — four proof-carrying formal lanes.** JACKAL Verified now exposes four formal-bounded tools, each releasing `status=formal-bounded` only when the packaged Lean-proved checker (or the zero-libm Gaussian checker) accepts the certificate the producer emitted for the exact request. Every formal receipt is a canonical `jackal-formal-receipt-v1(variant=<lane>)` envelope; the plugin re-runs the pinned checker on the embedded certificate before verified is returned, and binds every self-reported field to the checker's verdict.

| Formal tool | Producer | Checker | Theorem | Fragment |
|---|---|---|---|---|
| `jackal_range_bound` | `jackal-native` (v1.4.2 evaluator) | `jackal_cert_check` (Lean-proved) | `request_bound_certified_release` | pure-Q range fragment over `num, var, add, sub, mul, div, neg, integer pow (n≥0), sin, cos, abs, floor, ceil, round, trunc, min, max` |
| `jackal_gaussian_integral` | `gaussian_certificate.py` (pure-Q Gaussian producer) | `jackal_gaussian_check` (zero-libm Gaussian checker) | `gaussian_integral_check_sound` | Gaussian family `exp(a·(x−b)²)`, `a<0` |
| `jackal_sqrt_rat_bound` | `sqrt_rat_producer.py` (pure-Q Newton bracket) | `jackal_cert_check` (sqrt_rat arm) | `request_bound_certified_release` | `sqrt(x)` on `[lo, hi]` with `lo ≥ 0` |
| `jackal_exp_rat_bound` | `exp_rat_producer.py` (pure-Q Taylor + certified remainder) | `jackal_cert_check` (exp_rat arm) | `request_bound_certified_release` | `exp(x)` on `[lo, hi]` with `lo ≥ 0` |

Anything outside the declared fragment **refuses** rather than releasing a value. All producers, both checkers, the coverage inventory, and the proof identities ship inside one vendored, hash-verified public JACKAL v1.4.2 release archive, admitted into a private snapshot before use — a plain clone works offline. Weaker lanes (`exact`/`checked`/`estimated`/`model-based`) keep their epistemic class and can never become formal.

The plugin does not merely return numbers. It returns canonical `jackal-hermes-receipt-v2` receipts that bind the request commitment, epistemic status, result, residual non-claims, and exact producer + checker executable identities. A **formal receipt carries the exact certificate** the checker accepted; `jackal_verify_receipt` re-admits the pinned package and re-runs the pinned checker on those exact certificate bytes, then binds every self-reported field — enclosure, request commitment, expression commitment, certificate digest, operator set, variant tag, derived status — to what the checker actually accepted. No receipt-authored field is load-bearing, so a recomputed outer digest cannot forge a formal claim.

```text
natural-language request
        ↓
Hermes automatically loads the companion skill
        ↓
assurance selection: exact | checked | estimated | formal-bounded | model-based
        ↓
typed native plugin tool
        ↓
producer (evaluator or pure-Q Python) → certificate
        ↓
pinned Lean-proved checker verifies certificate
        ↓
canonical receipt (variant=range|gaussian|sqrt_rat|exp_rat) + semantic re-check
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
| `jackal_range_bound` | Certified pure-Q range enclosure (`variant=range`) | `formal-bounded` |
| `jackal_gaussian_integral` | Zero-libm Gaussian integral enclosure (`variant=gaussian`) | `formal-bounded` |
| `jackal_sqrt_rat_bound` | Pure-Q `sqrt(x)` enclosure (`variant=sqrt_rat`) | `formal-bounded` |
| `jackal_exp_rat_bound` | Pure-Q `exp(x)` enclosure on `[lo, hi]`, `lo ≥ 0` (`variant=exp_rat`) | `formal-bounded` |
| `jackal_claim_card` | Projectile-model result with assumptions, non-claims, canonical preimage, sensitivity, and fingerprint | `model-based` |
| `jackal_verify_receipt` | Independent receipt digest, semantic validation, and formal re-check via pinned checker | validation verdict |

### Assurance is explicit

`jackal_integrate` requires the caller to choose an assurance tier:

- `fast_estimate` — fixed-grid Simpson with a disclosed Richardson estimate;
- `adaptive_estimate` — adaptive Simpson with refusal semantics, still not a mathematical bound;
- `bounded` — outward-rounded interval enclosure under JACKAL's stated IEEE/libm model.

A bounded request is **never silently downgraded**. If certification fails, the receipt says `refused` or `indeterminate`; it does not substitute a weaker number.

The formal-bounded lanes (`jackal_range_bound`, `jackal_gaussian_integral`, `jackal_sqrt_rat_bound`, `jackal_exp_rat_bound`) release only on checker ACCEPT — otherwise refuse. Each carries the exact certificate bytes the checker consumed.

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
shasum -a 256 pkg/jackal-v1.4.2-macos-arm64.tar.gz
```

Expected:

```text
30b1a7441cdd9c1b0f24ac6d187608d3235f1ced6c57469dc1b1f697f475b1a0
```

The plugin verifies this archive plus its complete internal inventory, evaluator, checkers, producers, architecture, and modes before execution from a private snapshot.

## Natural-language usage

Users do not normally call the skill or tool names themselves. In a new session, ask naturally:

### Exact arithmetic

> Compute `C(10000,5000)` exactly. Use deterministic computation, validate the receipt, and report the digit count and instrument identity.

### Checked symbolic differentiation

> Differentiate `x^(x^x)`. Release only a checked result and preserve the distinction between numeric checking and proof.

### Certified integration (bounded, conditional on the f64/libm model)

> Compute a conditional bounded enclosure for `exp(-100000000*(x-0.1234567)^2)` from `0` to `1`, no wider than `1e-8`. Do not substitute an estimate if certification fails.

### Formal-bounded range analysis (pure-Q, checker-attested)

> Bound the range of `min(x^2, sin(x)+2)` over `[0,2]`. Release only `formal-bounded` with the certificate the Lean-proved checker accepted; refuse anything outside the mechanized fragment.

### Zero-libm Gaussian integration

> Give me a formal-bounded enclosure of `exp(-1e10*(x-0.5)^2)` over `[0,1]` with tolerance `1/1000`. The proof decision must not depend on `libm`; validate the receipt via the pinned Gaussian checker.

### Pure-Q sqrt and exp lanes

> Enclose `sqrt(x)` on `[2,3]` and `exp(x)` on `[0,1]` under `NO-libm-TCB`. Return formal-bounded receipts (variant=sqrt_rat, variant=exp_rat); each certificate must be checker-accepted with re-verify=ACCEPT.

### Range hazard

> Can `1/x` be certified over `[-1,1]`? Use a range bound and treat refusal as an answer.

JACKAL refuses because the denominator interval contains zero. The plugin preserves that refusal rather than manufacturing a principal value.

### Model-based calculation

> Produce a projectile claim card for speed 20 m/s, angle 45 degrees, and gravity 9.80665 m/s². Validate its canonical fingerprint and list assumptions and non-claims.

## Receipt contract

Every computation returns `jackal-hermes-receipt-v2` with exactly:

```json
{
  "schema": "jackal-hermes-receipt-v2",
  "operation": "jackal_gaussian_integral",
  "request": {},
  "result": {
    "status": "formal-bounded",
    "variant": "gaussian",
    "enclosure": {"lower": "...", "upper": "..."},
    "theorem": "gaussian_integral_check_sound",
    "certificate_sha256": "...",
    "formal_receipt": { "schema": "jackal-formal-receipt-v1", "...": "..." }
  },
  "instrument": {
    "evaluator": {"name": "gaussian_certificate.py", "sha256": "..."},
    "checker":   {"name": "jackal_gaussian_check",   "sha256": "..."},
    "plugin":    {"name": "jackal-verified",         "sha256": "..."}
  },
  "receipt_sha256": "..."
}
```

Weaker lanes (`exact`, `estimated`, `checked`, `bounded`, `model-based`) return the same envelope with a single-binary `instrument = {"name": "jackal-native", "sha256": "..."}` block.

The receipt digest is SHA-256 over canonical UTF-8 JSON of the first five fields: sorted keys, compact separators, and non-finite JSON numbers forbidden.

Validation is deliberately three-layered:

1. **Integrity:** schema, exact keyset, canonical digest, and instrument identity.
2. **Semantics:** operation/status compatibility, required result fields, non-release invariants, ordered finite enclosures, requested-tolerance compliance, and claim-card fingerprint/model consistency.
3. **Formal re-check:** `formal-bounded` receipts carry the canonical nested `jackal-formal-receipt-v1(variant=…)`; validation re-admits the pinned package, runs the upstream independent verifier, re-runs the pinned checker on the embedded certificate, and binds the request, enclosure, commitments, operators, coverage, theorem, variant, and evaluator/checker/plugin identities to the checker verdict.

A recomputed outer digest does not make a semantically malformed or forged formal result valid. The digest is an unkeyed integrity checksum, not author authentication; formal validity comes from re-executing the proved checker.

See [`skills/jackal-verified-computation/references/receipt-contract.md`](skills/jackal-verified-computation/references/receipt-contract.md) for the compact contract.

## Security architecture

- Ten curated tools; no generic command, endpoint, filesystem, or shell surface.
- `subprocess.run` with an argument list and `shell=False`.
- Restricted child environment.
- Public JACKAL v1.4.2 package pinned by archive SHA-256, safe extraction, complete internal `SHA256SUMS`, evaluator/checker/producer SHA-256, Mach-O arm64, and executable-mode checks before execution from a private snapshot.
- Expression-length, output-size, certificate-size, and runtime bounds.
- Finite-number admission and interval-order validation.
- Explicit status vocabulary: `exact`, `estimated`, `checked`, `bounded`, `formal-bounded`, `model-based`, `refused`, `indeterminate`.
- Refusal-preserving behavior with no stale-success fallback.
- Independent claim-card fingerprint recomputation.
- No privileged Hermes capabilities and no core-tool overrides.

Native Hermes plugins execute with the user's authority; they are not sandboxed. Review the source and install only releases whose digests you trust. See [`SECURITY.md`](SECURITY.md).

## Tests and verification

Run the adapter and poison suites (both should exit 0):

```bash
python3 tests/test_plugin.py
python3 tests/test_plugin_v2.py
python3 tests/aba_recheck_gate.py
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
- the four recomputed-digest formal receipt forgeries (ordered-wrong-enclosure, changed-request, arbitrary-cert-digest, arbitrary-request-commitment) across **all four formal lanes** (range/gaussian/sqrt_rat/exp_rat), each A→B→A hash-verified — 16 cases total;
- stripped-certificate and substituted-enclosure refusal;
- variant-mutation locks (variant label swap, theorem swap, forged producer/checker identity, forged certificate);
- fragment refusal in variant lanes (sqrt_rat/exp_rat refuse anything but their admitted exact form; exp_rat refuses lower<0);
- malformed and hostile inputs;
- plugin registration of all ten tools, the bundled skill, and automatic routing policy.

Validate against Hermes's real plugin loader and registry:

```bash
hermes plugins doctor . --ci
```

Expected:

```text
OK: runtime discovery, manifest parsing, import, and registration passed
registrations: 10 tool(s), 0 hook(s)
```

Exercise the repository exactly as an installed standalone plugin:

```bash
python3 scripts/fresh_install_smoke.py
```

The smoke test registers all tools, the bundled skill, and the automatic routing section, then invokes exact arithmetic and validates its receipt.

CI runs the unit/poison suites, the ABA re-check gate, manifest consistency checks, Python compilation, and embedded-binary digest verification on Apple Silicon macOS.

## Repository layout

```text
.
├── plugin.yaml
├── __init__.py                            # Hermes registration (10 tools)
├── schemas.py                             # model-visible typed schemas
├── tools.py                               # fail-closed adapter and receipt validator
├── pkg/jackal-v1.4.2-macos-arm64.tar.gz   # evaluator + proved checker + Gaussian checker + producers
├── jackal_formal/                         # shared release validator, receipt verifier, coverage inventory, proof identities, source .anb
├── skills/
│   └── jackal-verified-computation/
│       ├── SKILL.md                       # automatic assurance-selection discipline
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

The plugin supports **Apple Silicon macOS only** because the pinned JACKAL v1.4.2 package contains Mach-O arm64 evaluator/checker artifacts. It fails closed if the archive, manifest, inventory, architecture, modes, evaluator, checkers, producers, or plugin manifest differs from the pinned identity.

Portable support should use one reviewed binary per platform with explicit OS/architecture selection and per-artifact digests. It must never fall back to an arbitrary `jackal` found on `PATH`.

## Evidence boundaries

JACKAL Verified makes strong but bounded claims:

- `exact` means exact within the supported grammar, operation, and compute budget.
- `checked` means sampled numerical challenge, not symbolic identity proof.
- `bounded` (from `jackal_integrate` at assurance=bounded) means an enclosure conditional on JACKAL's stated IEEE basic-operation and ≤2 ULP libm model and a tested — not end-to-end mechanized — implementation.
- `formal-bounded` means the pinned Lean-proved checker (or the zero-libm Gaussian checker) accepted the exact certificate the producer emitted for the exact request, and the plugin re-ran the checker on those bytes and re-bound every request/result/identity/coverage field to the checker's verdict; it depends on the recorded TCB (Lean kernel + toolchain, checker build, canonical rational codec) and does not prove source-to-native refinement.
- `model-based` means conditional on stated assumptions, not observed physical reality.
- SHA-256 identifies and checksums bytes; it does not authenticate an author or prove mathematical validity.
- Passing finite campaigns does not establish universal correctness.

The upstream JACKAL interval model includes Lean mechanization for `request_bound_certified_release` (range/sqrt_rat/exp_rat) and `gaussian_integral_check_sound` (Gaussian). This plugin does not claim an end-to-end formal proof from Anubis source through the embedded native evaluator.

## Provenance

The vendored package is the public JACKAL CALC `v1.4.2` release artifact:

- Upstream: https://github.com/AnubisQuantumCipher/jackal-calc
- Archive SHA-256: `30b1a7441cdd9c1b0f24ac6d187608d3235f1ced6c57469dc1b1f697f475b1a0`
- Evaluator SHA-256: `820c0722e46a0800115c404ea1c9251c6f72fe8c6897bdabe437f342f9310b6c`
- Proved range checker SHA-256: `b567b8a94ce7acd49ecaa807d86a5bb66d695fb0ce4fea2eb84f0073425984d7`
- Gaussian checker SHA-256: `42d3f3e74b90062c958baeda9ddf9ddd6f82ef3f8e4dd2b9ade5017239fe7a77`
- Gaussian producer SHA-256: `20c24622b786940a8e82198f2364fb7593e761902fa0736289b179642f1e4306`
- sqrt_rat producer SHA-256: `4bc95c331430d2350facfb19da9aba483ab7b3698754e7af2e5deb797e097926`
- exp_rat producer SHA-256: `ccbc48633bd3980613413399d552321eaa67b15bd101643e53b0dd5f10a37918`
- License: MIT

See [`PROVENANCE.md`](PROVENANCE.md) and [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Contributing

Contributions are welcome; see [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening a PR — the receipt schema, assurance vocabulary, executable-identity model, and formal re-check are load-bearing.

## License

MIT — see [`LICENSE`](LICENSE).

## Independence

This is an independent community plugin for [Hermes Agent](https://github.com/NousResearch/hermes-agent). No endorsement by Nous Research is implied.
