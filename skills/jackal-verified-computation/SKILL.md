---
name: jackal-verified-computation
description: Use JACKAL for exact, bounded, checked, or claim-compiled STEM work.
version: 5.0.0
author: Anubis Quantum Cipher contributors
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [JACKAL, Mathematics, Verification, Interval-Arithmetic, Evidence]
related_skills: [adversarial-calculator-audit, evidence-first-claims-audit]
---

# JACKAL verified computation (v1.6.0 kernel, 33 tools)

Use the `jackal-verified` plugin as a deterministic computational trust
layer. Select the weakest lane that satisfies the user's actual assurance
requirement, preserve JACKAL's epistemic class, and never turn a refusal
or estimate into a stronger claim.

## When to use

- Exact rational/integer truth, modular arithmetic, polynomial and
  algebraic-number certificates.
- Symbolic derivatives that should be numerically checked before release.
- Numerical integration where estimate versus bound materially changes
  the answer.
- Range, threshold, denominator-zero, and sensitivity questions over
  intervals.
- Proof-carrying Gaussian integrals and the seven pure-rational
  fragments — `sqrt`, `exp`, `ln`, `sin`, `cos`, `atan`, `tanh` over
  admitted rational intervals.
- Consequential multi-step conclusions: compile ONE deterministic,
  independently replayable claim bundle instead of prose.
- Any arithmetic where language-model mental computation would reduce
  reliability.
- Do NOT use JACKAL for unsupported general CAS solving, theorem proving,
  arbitrary-precision reals, or as evidence that a physical model matches
  reality.

## Prerequisites

- The `jackal-verified` native Hermes plugin v4.0.0 is enabled in the
  active profile. When loaded from the plugin bundle, its explicit skill
  name is `jackal-verified:jackal-verified-computation`.
- The plugin vendors the public JACKAL v1.6.0 package
  (`jackal-v1.6.0-macos-arm64.tar.gz`, SHA-256
  `0cdacf56bb83d65454330973280cde7da0b9262d6163ccd7efbbbb47bc88e39a`);
  admission verifies the tarball hash, the package's internal SHA256SUMS,
  and every pinned producer/checker identity before any computation. Any
  mismatch fails closed.
- A NEW Hermes session is required after plugin installation or upgrade:
  tool schemas load once per session.

## Assurance Selection

| Need | Tool | Honest class |
|---|---|---|
| Rational or integer truth | `jackal_exact` | exact within the supported grammar |
| Exact CAS certificate (gcd/modular/polynomial/algebraic) | `jackal_xgcd`, `jackal_mod_pow`, `jackal_mod_inv`, `jackal_crt`, `jackal_divides`, `jackal_prime_cert`, `jackal_canon`, `jackal_poly_canon`, `jackal_poly_eq`, `jackal_poly_gcd`, `jackal_ratfunc_canon`, `jackal_roots_isolate`, `jackal_alg_sign`, `jackal_alg_cmp` | exact + `jackal-exact-cert-v1` certificate, independently re-checkable |
| Ordinary finite-real evaluation | `jackal_evaluate` | IEEE-f64 evaluated value |
| Symbolic derivative | `jackal_diff` | numerically checked derivative, not identity proof |
| Fast exploratory integral | `jackal_integrate` | grid-limited estimate |
| Better numerical integral | `jackal_integrate_adaptive` | local estimate with refusal semantics |
| Consequential integral | `jackal_integrate_bound` | enclosure conditional on stated rounding/libm model |
| Possible values over an interval | `jackal_range_bound` | `formal-bounded`, `variant=range`, in the pure-Q theorem-covered fragment; otherwise refusal |
| Gaussian integral `exp(a*(x-b)^2)`, `a<0` | `jackal_gaussian_integral` | `formal-bounded`, `variant=gaussian`, through the zero-libm checker; otherwise refusal |
| `sqrt/exp/ln/sin/cos/atan/tanh` over admitted rational intervals | `jackal_sqrt_rat_bound`, `jackal_exp_rat_bound`, `jackal_ln_rat_bound`, `jackal_sin_rat_bound`, `jackal_cos_rat_bound`, `jackal_atan_rat_bound`, `jackal_tanh_rat_bound` | `formal-bounded`, `variant=<lane>_rat`, no libm on the proof-decision path; otherwise refusal |
| Mixed/policy-bearing multi-step claim | `jackal_claim` | compiled `jackal-claim-bundle-v1` with recomputed multidimensional assurance vector |
| Independent replay of a bundle | `jackal_verify_bundle` | `verified` / `refused` / `indeterminate` with a stable reason class |
| Formal receipt re-verification | `jackal_verify_receipt` | re-runs the pinned Lean-proved checker on the embedded certificate |

When the user asks for "accurate," infer the consequence. Prefer bounded
or formal lanes for money, safety, proofs, irreversible decisions, or
thresholds. Never silently downgrade a bounded request.

## Procedure

1. **Classify the computation.** Exact, checked, estimated, bounded,
   formal-bounded, model-based — or a composed claim. Completion: one
   assurance class (or `jackal_claim`) is named before interpreting
   output.
2. **Call the typed JACKAL tool.** Do not construct raw shell commands
   when a plugin tool covers the operation. Completion: the response
   carries `status` plus lane fields; formal lanes carry the canonical
   nested `jackal-formal-receipt-v1` with
   `variant=range|gaussian|sqrt_rat|exp_rat|ln_rat|sin_rat|cos_rat|atan_rat|tanh_rat`.
3. **Inspect status before value.** Treat `refused` and `indeterminate`
   as terminal computational outcomes unless the user explicitly accepts
   a weaker lane. Completion: no value from a prior or weaker run is
   substituted.
4. **Verify consequential evidence.** For formal receipts call
   `jackal_verify_receipt` with caller-pinned expectations and require
   `status=verified verdict=ACCEPT`. For claim bundles call
   `jackal_verify_bundle` with YOUR OWN expected epoch, root proposition,
   policy hash, and verification time — never pinned from the bundle
   itself. Completion: verification succeeds, or the refusal reason is
   reported and no answer is released.
5. **Report the epistemic class.** Use the same class JACKAL returned;
   include assumptions and non-claims for model-based or supplied-input
   work. Completion: wording does not exceed evidence.
6. **On refusal, stop or reroute honestly.** Name the stable refusal
   class; offer the weaker lane explicitly rather than silently
   substituting it.

## Non-inflation rules

- The nine formal lanes are distinct admitted fragments. Do not route a
  general integral through the Gaussian tool, a general radical through
  `sqrt_rat`, or an out-of-domain input through any `_rat` lane; refusal
  is the correct result outside each admitted form.
- `NO-libm-TCB` applies to the Gaussian and pure-Q `_rat` proof-decision
  paths as declared by their receipts; do not generalize it to ordinary
  evaluation, integration, or the full plugin.
- Ordinary `bounded` integration remains conditional on JACKAL's
  IEEE/libm model — never transfer `formal-bounded` language to it.
- Composed interval arithmetic inside claim bundles caps at
  `mathematical=bounded`; only admitted theorem-covered fragments earn
  `formal-bounded`.
- Exact math over an assumed physical model stays
  `model_validity=assumed`; formal math over supplied inputs stays
  `input_provenance=supplied`. A signature affects artifact provenance
  only.
- Fixed-grid estimates can miss narrow features even when refinement
  agrees. Interval enclosures can be conservative; supersets need not be
  tight or attained.
- Plugin installation does not hot-add tools to an existing conversation.
  Start a new session after enabling or upgrading.

## Verification checklist (consequential results)

1. Formal lanes: require the nested `jackal-formal-receipt-v1`, a
   recognized variant, pinned producer/checker identities, and
   checker-derived request/enclosure bindings. Require theorem
   `request_bound_certified_release` for `range` and every `_rat`
   variant, or `gaussian_integral_check_sound` for `gaussian`.
   Verification re-runs the variant-selected pinned checker on the
   embedded certificate; either outer digest alone is never sufficient.
2. Claim bundles: require `jackal_verify_bundle` = `verified` under
   caller-pinned epoch `v1.6.0`, root proposition, policy hash, and
   time; the recomputed assurance vector, consequence floors, and
   rendering must match — a tampered node refuses (`node-id-mismatch`).
3. Exact-CAS lanes: certificates are independently re-checkable; verify
   before relying on them in consequential work.
4. Report variant plus producer/checker SHA-256 identities alongside
   high-stakes formal results when auditability matters.

## Migrating from older plugin epochs

- v3.0.0 exposed 10 tools with three legacy names/shapes that do NOT
  exist in the 33-tool surface: `jackal_differentiate` → use
  `jackal_diff`; `jackal_claim_card` → compile the model claim through
  `jackal_claim` (op `model` + consequence class); the old mode-based
  `jackal_exact` arguments → `jackal_exact {"expression": "..."}`.
- The 33-tool surface equals the sealed upstream v1.6.0 plugin surface
  exactly; the plugin's local regression suite and admission gate
  establish adapter behavior separately from JACKAL's own mathematical
  claims.
