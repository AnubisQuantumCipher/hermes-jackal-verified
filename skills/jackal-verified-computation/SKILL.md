---
name: jackal-verified-computation
description: Use JACKAL for exact, bounded, or checked STEM work.
version: 1.3.0
author: Anubis Quantum Cipher contributors
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [JACKAL, Mathematics, Verification, Interval-Arithmetic]
    related_skills: [adversarial-calculator-audit, evidence-first-claims-audit]
---

# JACKAL Verified Computation

Use the profile-local `jackal-verified` plugin as a deterministic computational trust layer. Select the weakest lane that satisfies the user's actual assurance requirement, preserve JACKAL's epistemic class, and never turn a refusal or estimate into a stronger claim.

## When to Use

- Exact fractions, combinatorics, factorials, powers, and large integers.
- Symbolic derivatives that should be checked before release.
- Numerical integration where estimate versus bound materially changes the answer.
- Range, threshold, denominator-zero, and sensitivity questions over intervals.
- Model-based projectile calculations requiring explicit assumptions and a recomputable fingerprint.
- Any arithmetic where language-model mental computation would reduce reliability.
- Do not use JACKAL for unsupported general CAS solving, theorem proving, arbitrary-precision reals, or as evidence that a physical model matches reality.

## Prerequisites

- The `jackal-verified` native Hermes plugin is enabled in the active profile. When loaded from the plugin bundle, its explicit name is `jackal-verified:jackal-verified-computation`.
- Its vendored public JACKAL v1.3.0 package, evaluator, Gaussian producer, two proved checkers, and plugin manifest must match the approved SHA-256 identities; any mismatch fails before computation.
- A new Hermes session may be required after plugin installation because tool schemas remain stable during a conversation.

## Assurance Selection

| Need | Tool and mode | Permitted claim |
|---|---|---|
| Rational or integer truth | `jackal_exact` | exact within the supported grammar and budget |
| Ordinary finite-real evaluation | `jackal_evaluate` | IEEE-f64 evaluated value |
| Symbolic derivative | `jackal_differentiate` | numerically checked derivative, not identity proof |
| Fast exploratory integral | `jackal_integrate`, `fast_estimate` | grid-limited estimate |
| Better numerical integral | `jackal_integrate`, `adaptive_estimate` | local estimate with refusal semantics |
| General consequential integral | `jackal_integrate`, `bounded` | enclosure conditional on stated rounding/libm model |
| Canonical narrow Gaussian `exp(-A*(x-mu)^2)` with exact-square rational `A` | `jackal_integrate`, `formal-bounded` | zero-libm theorem-backed enclosure when the proved checker accepts; otherwise refusal |
| Possible values over an interval | `jackal_range_bound` | `formal-bounded` in the theorem-covered fragment; otherwise refusal |
| Physical model output | `jackal_claim_card` | model-based result conditional on assumptions |

When the user asks for "accurate," infer the consequence. Prefer `formal-bounded` only when the request is in the admitted Gaussian family, otherwise `bounded` for money, safety, irreversible decisions, or thresholds. Never silently downgrade either strong request.

## Procedure

1. **Classify the computation.** Identify exact, checked, estimated, bounded, or model-based intent. Completion: one assurance class is named before interpreting output.
2. **Call the typed JACKAL tool.** Do not construct a raw JACKAL shell command when the plugin tool covers the operation. Completion: the response includes `jackal-hermes-receipt-v2` and the approved instrument identity; `formal-bounded` results also carry the canonical nested `jackal-formal-receipt-v1`.
3. **Inspect status before value.** Treat `refused` and `indeterminate` as terminal computational outcomes unless the user explicitly accepts a weaker lane. Completion: no value from a prior or weaker run is substituted.
4. **Verify consequential receipts.** Call `jackal_verify_receipt` before relying on exact, bounded, or model-based results in consequential work. Completion: `valid=true`; otherwise report the validation errors and release no answer.
5. **Report the epistemic class.** Put exact value, enclosure, checked derivative, estimate, or model assumptions in the answer using the same class JACKAL returned. Completion: wording does not exceed evidence.
6. **Preserve residuals.** State the lane's non-claims when they affect the decision. Completion: estimates are not called bounds; checks are not called proofs; fingerprints are not called correctness evidence.

## Non-Inflation Rules

- `estimated` is never exact, certified, guaranteed, or bounded.
- `checked` is never formally proved.
- `bounded` is an enclosure, not an exact value.
- `formal-bounded` is universal only over checker-accepted requests in the declared fragment and recorded ModelTCB; it is never unqualified universal correctness.
- `model-based` is conditional on stated assumptions, not an observed fact.
- A matching SHA-256 identifies bytes; it does not authenticate an author or establish mathematical validity.
- A finite campaign cannot establish universal correctness.
- A refusal is an answer. Do not hide it by automatically calling a weaker lane.

## Pitfalls

- Fixed-grid estimates can miss narrow features even when refinement agrees. Use `bounded` for consequential integration.
- Interval enclosures can be conservative; range supersets need not be tight or attained.
- Ordinary `bounded` integration remains conditional on JACKAL's IEEE/libm model and a tested, not end-to-end mechanized, implementation. `formal-bounded` integration applies only to checker-accepted `gaussian-exp-square-integral-v1`; generic `exp`, non-square amplitudes, uncovered domains, and other integrands refuse without fallback.
- Symbolic numeric checking can miss domain-specific disagreement. Preserve domain caveats.
- Claim-card fingerprints bind canonical bytes but do not validate the physical assumptions.
- Plugin installation does not hot-add tools to an existing conversation. Start a new session after enabling it.

## Verification

For a consequential receipt:

1. Confirm `schema=jackal-hermes-receipt-v2`.
2. Call `jackal_verify_receipt` and require `valid=true`.
3. For `formal-bounded`, require a nested `jackal-formal-receipt-v1`, its embedded certificate, pinned producer/evaluator/checker/plugin identities, and checker-derived request/enclosure/coverage bindings. The theorem is `cert_check_sound` for range requests or `gaussian_integral_check_sound` for admitted Gaussian integration. Verification re-runs the matching proved checker; either outer digest alone is never sufficient.
4. Confirm the returned status matches the requested assurance.
5. For bounded integration, require ordered finite endpoints and width no greater than requested tolerance.
6. For claim cards, require independent fingerprint recomputation.
7. Report evaluator/checker SHA-256 identities alongside high-stakes formal results when auditability matters.

The plugin's local regression suite and plugin-doctor result establish adapter behavior separately from JACKAL's own mathematical claims.
