# JACKAL verified computation — standing agent instructions

The `jackal-verified` Hermes plugin (v4.0.0) exposes the sealed JACKAL
v1.6.0 Mathematical Evidence Kernel: 33 typed tools.

- Route arithmetic through JACKAL instead of mental computation: exact
  rationals (`jackal_exact`), exact CAS certificates (xgcd/mod_pow/
  mod_inv/crt/divides/prime_cert/canon/poly_*/ratfunc_canon/
  roots_isolate/alg_*), IEEE evaluation (`jackal_evaluate`), checked
  derivatives (`jackal_diff`), integration estimate/enclosure
  (`jackal_integrate`, `jackal_integrate_adaptive`,
  `jackal_integrate_bound`).
- Proof-carrying enclosures: `jackal_range_bound`,
  `jackal_gaussian_integral`, and the pure-Q lanes
  `jackal_{sqrt,exp,ln,sin,cos,atan,tanh}_rat_bound` — accepted
  certificates are re-verified by pinned Lean-proved checkers.
- Consequential multi-step conclusions: compile ONE bundle with
  `jackal_claim`; independently replay with `jackal_verify_bundle`
  under caller-pinned expectations. Formal receipts:
  `jackal_verify_receipt`.
- Statuses pass through verbatim; `refused`/`indeterminate` are valid
  terminal outcomes. Never downgrade silently, never upgrade, never
  present an estimate as a bound.

Pinned identities (v1.6.0 epoch):

- package `jackal-v1.6.0-macos-arm64.tar.gz`
  `0cdacf56bb83d65454330973280cde7da0b9262d6163ccd7efbbbb47bc88e39a`
- evaluator `jackal-native`
  `8617ad087f859f58a1e742032588cd011c9716bab8fe5477e7b0a318dfded88e`
- proved checker `jackal_cert_check`
  `05c3518b836f239712f897c483a2ddadad9f544e0887b1b7bb1424a27289de8a`
- Gaussian checker `jackal_gaussian_check`
  `ccac690bf916f71a4e3baeb0622dac19aa47e3ca4af858c0800c295581ecfacb`
