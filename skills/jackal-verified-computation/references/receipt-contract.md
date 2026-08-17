# Evidence contracts (v1.7.0 kernel, plugin v5.0.0)

The plugin passes upstream responses through verbatim. Three evidence
shapes matter:

## Weaker/exact lanes
`{status, lane, formal: false, fields, engine_output, identities,
non_claims, assurance}` — `status` is the honest inventory-derived class
(`exact | checked | estimated | bounded | model-based | refused |
indeterminate`); status inflation is structurally impossible; exact-CAS
lanes additionally carry a `jackal-exact-cert-v1` certificate that is
independently re-checkable.

## Formal lanes
`{status: "formal-bounded", variant, receipt, checker_output,
checker_rerun}` where `receipt` is a canonical `jackal-formal-receipt-v1`
with `variant = range | gaussian | int_cert | sqrt_rat | exp_rat | ln_rat
| sin_rat | cos_rat | atan_rat | tanh_rat`, the embedded certificate,
pinned producer/checker/evaluator identities, and theorem
`request_bound_certified_release` (range + `_rat` variants),
`gaussian_integral_check_sound` (gaussian), or `int_cert_sound`
(int_cert — the v1.7.0 certified composed definite integral, checked by
the compiled `jackal_int_cert_check`; expected_tolerance is required at
verification exactly like gaussian). `jackal_verify_receipt`
re-runs the variant-selected pinned Lean-proved checker on the embedded
certificate bytes with caller-pinned expectations — recomputing either
outer digest alone is never sufficient.

## Claim bundles
`jackal_claim` → `{status: "ok", root, bundle_digest_sha256, rendering,
permitted_text, route_trace, bundle}` with a canonical
`jackal-claim-bundle-v1` graph. `jackal_verify_bundle` replays it under
CALLER-pinned `expected_release_epoch`, `expected_root_proposition`,
`expected_policy_sha256`, `verification_time_unix` (and optional nonce):
every node hash, rule application, assurance axis, consequence floor,
and rendering is recomputed; the result is `verified | refused |
indeterminate` with a stable reason class — never a bare VERIFIED badge.

Negative controls: a mutated node refuses `node-id-mismatch`; a swapped
variant/theorem/identity refuses; producer-authored statuses are never
trusted; refusals are terminal unless the caller explicitly accepts a
weaker lane.
