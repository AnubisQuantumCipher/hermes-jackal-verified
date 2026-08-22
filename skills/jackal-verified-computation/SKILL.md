---
name: jackal-verified-computation
description: Route exact, bounded, formal, structural, claim, and Anubis program evidence through JACKAL.
version: 7.0.0
author: Anubis Quantum Cipher contributors
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [JACKAL, Mathematics, Verification, Interval-Arithmetic, Evidence]
related_skills: [adversarial-calculator-audit, evidence-first-claims-audit]
---

# JACKAL verified computation

<!-- JACKAL_CURRENT_SURFACE_V1_BEGIN -->
The v1.7.3 candidate exposes the ordered 41-tool full inventory recorded in
`release/capability_inventory_v1.json`. That generated inventory is the
capability-name, schema-identity, status, dependency, fragment, and refusal
source. Candidate evidence does not assert that a public v1.7.3 tag or release
exists.
<!-- JACKAL_CURRENT_SURFACE_V1_END -->

Use the `jackal-verified` plugin when the result needs an explicit evidence
class, independently replayable receipt, or named refusal. No silent downgrade
is permitted. Preserve `refused` and `indeterminate` as terminal outcomes
unless the caller explicitly requests a separate weaker lane.

## Establish the loaded surface

Start a new Hermes session after an install or upgrade because tool schemas are
loaded once per session. From a trusted plugin checkout, install an immutable
40-character commit and run:

```bash
hermes plugins install AnubisQuantumCipher/hermes-jackal-verified \
  --force --ref <FULL-40-CHAR-COMMIT> --enable
hermes plugins doctor jackal-verified --ci
```

Require exactly 41 unique registrations and the reviewed
`jackal-verified-computation` skill. A 34-tool discovery is the historical
plugin surface and does not provide the domain-pack or Anubis program tools.
For an unpublished candidate, use only the separately verified local package
and candidate commit; do not treat a future release URL as evidence.

Requirements are Apple Silicon macOS and Python 3.11 or newer. The plugin
vendors the entire content-pinned runtime, extracts it into a private snapshot,
checks the package SHA-256 and complete internal `SHA256SUMS`, then checks its
named trust-bearing identities. Any mismatch returns a plugin admission
refusal. The plugin is local native code, not a sandbox.

## Choose the front door

- Use `jackal_claim` for mixed, unit-aware, model-conditioned, policy-bearing,
  or consequential multi-step claims. Keep fallback disabled.
- Use `jackal_verify_bundle` for independent replay against caller-pinned
  epoch, policy digest, root proposition, verification time, and nonce.
- Use `jackal_verify_receipt` for formal receipt replay against
  caller-authorized request values and identities.
- Use a direct typed tool for one narrow operation. Do not create raw shell or
  generic-command substitutions when a typed tool covers the request.
- Use `jackal_test_exists` and `jackal_claim_cites_test` only for byte-exact
  source structure. Their consequence ceiling is informational; existence or
  citation resolution is not correctness, execution, assertion quality, or
  coverage.
- Use `jackal_decision_rank_v2` when the caller supplies a numeric criterion
  and a canonical unit. Use `jackal_decision_rank` only when the caller
  explicitly accepts the older unit-free boundary. A declared unit is not a
  measurement and neither tool chooses the criterion or values.
- Use `jackal_anubis_verify_program` for caller-selected Safe source/evidence
  bytes, `jackal_anubis_verify_program_receipt` to recompute a receipt from
  those bytes, and `jackal_anubis_check_program` only when the caller supplies
  the approved compiler and a new output root. None executes the artifact.

Expected values are authorization, not data discovery. Never copy an
`expected_*` value from the receipt or bundle being verified.

## Current 41-tool families

| Family | Typed tools | Returned boundary |
|---|---|---|
| Formal range/integral | `jackal_range_bound`, `jackal_gaussian_integral`, `jackal_integrate_bound_cert` | `formal-bounded` only after the selected checker accepts; otherwise `refused` |
| Formal pure-rational | `jackal_sqrt_rat_bound`, `jackal_exp_rat_bound`, `jackal_ln_rat_bound`, `jackal_sin_rat_bound`, `jackal_cos_rat_bound`, `jackal_atan_rat_bound`, `jackal_tanh_rat_bound` | named admitted unary fragment only; otherwise `refused` |
| Formal replay | `jackal_verify_receipt` | `verified` or `refused` against caller pins |
| Numeric/exact | `jackal_exact`, `jackal_evaluate`, `jackal_diff`, `jackal_integrate`, `jackal_integrate_adaptive`, `jackal_integrate_bound`, `jackal_solve` | exact, checked, estimated, bounded, refused, or indeterminate as returned |
| Exact algebra/number theory | `jackal_canon`, `jackal_poly_canon`, `jackal_poly_eq`, `jackal_poly_gcd`, `jackal_ratfunc_canon`, `jackal_roots_isolate`, `jackal_alg_sign`, `jackal_alg_cmp`, `jackal_xgcd`, `jackal_mod_pow`, `jackal_mod_inv`, `jackal_crt`, `jackal_divides`, `jackal_prime_cert` | exact result plus the catalog-declared certificate boundary |
| Claim graph | `jackal_claim`, `jackal_verify_bundle` | compiled bundle, or verified/refused/indeterminate replay |
| Source structure | `jackal_test_exists`, `jackal_claim_cites_test` | `structural-exact`, consequence-capped at informational, or refused |
| Decision ranking | `jackal_decision_rank`, `jackal_decision_rank_v2` | exact ordering over caller declarations, consequence-capped at decision-boundary, or refused |
| Anubis program evidence | `jackal_anubis_check_program`, `jackal_anubis_verify_program`, `jackal_anubis_verify_program_receipt` | verified-program-evidence or verified-program-receipt under inventory-safe-v1, or refused |

## Formal-bounded fragments

- Range accepts only the catalog-declared canonical-rational expression and
  interval fragment.
- Gaussian accepts only the canonical `exp(-A*(x-mu)^2)` request shape with
  canonical rational bounds and tolerance.
- Composed integral accepts only
  `num/var/neg/add/sub/mul/div/pow(0..4096)/sin/cos/abs` in `x`; it does not
  fall back to the weaker float integration lane.
- The seven pure-rational tools accept only their exact named unary form and
  documented rational domain. The tanh lane uses
  `1-2/(exp(2*x)+1)`; a general tanh expression is outside the fragment.

Current range, pure-rational, and composed-integral receipts use the
request-bound v1.7.2 proof identities even though the additive package epoch
is v1.7.3. The request-unbound v1.7.0 composed-integral identity is revoked,
not an alternative verifier path.

## Anubis program-evidence boundary

Require profile `inventory-safe-v1`, Safe mode, one exact source leaf, strict
v3 stage/file/consumer rosters, nonzero one-to-one proof paths, approved Z3
UNSAT replay, and independent RUP replay. Preserve these residuals:

- `no-source-to-vc-proof`
- `no-smt-to-cnf-proof`
- `policy-construct-totality-not-established`
- `no-source-native-refinement`
- `runtime-not-observed`
- `no-universal-language-soundness`

Refuse `contracted-safe-v1`. A producer-attested whole-function inventory does
not establish independent construct-total walker coverage. Never execute an
artifact to strengthen the returned status.

## Result handling

1. Classify the requested evidence lane before interpreting output.
2. Call the exact typed tool and inspect `status` before any value.
3. Preserve every returned status, assumption, non-claim, residual, route
   trace, receipt identity, and checker verdict.
4. For consequential formal receipts, replay with `jackal_verify_receipt` and
   independent pins. Range and pure-rational receipts use expected command
   `range-bound-cert`; Gaussian uses `integrate`; composed integral uses
   `integrate-bound-cert` and requires expected tolerance.
5. For consequential bundles, replay with `jackal_verify_bundle` and the
   caller's independent expectations.
6. If the requested lane refuses, report its named reason. Run a weaker lane
   only as a separately labeled call after explicit caller authorization.

`formal-bounded` covers only checker-admitted fragments. `bounded` integration
is conditional on the stated f64/libm model. `checked` derivative evidence is
sampled numeric agreement, not an identity theorem. `estimated` is never a
bound. Exact mathematics over supplied inputs does not validate their
real-world truth, and model-based mathematics does not validate the model.
