# JACKAL verified computation — standing agent instructions

The `jackal-verified` Hermes plugin (v5.0.0) exposes the sealed JACKAL
v1.7.0 Mathematical Evidence Kernel: 34 typed tools.

- Route arithmetic through JACKAL instead of mental computation: exact
  rationals (`jackal_exact`), exact CAS certificates (xgcd/mod_pow/
  mod_inv/crt/divides/prime_cert/canon/poly_*/ratfunc_canon/
  roots_isolate/alg_*), IEEE evaluation (`jackal_evaluate`), checked
  derivatives (`jackal_diff`), integration estimate/enclosure
  (`jackal_integrate`, `jackal_integrate_adaptive`,
  `jackal_integrate_bound`).
- Proof-carrying enclosures: `jackal_range_bound`,
  `jackal_gaussian_integral`, the certified composed integral
  `jackal_integrate_bound_cert` (v1.7.0, theorem `int_cert_sound`), and
  the pure-Q lanes `jackal_{sqrt,exp,ln,sin,cos,atan,tanh}_rat_bound` —
  accepted certificates are re-verified by pinned Lean-proved checkers.
- Consequential multi-step conclusions: compile ONE bundle with
  `jackal_claim`; independently replay with `jackal_verify_bundle`
  under caller-pinned expectations. Formal receipts:
  `jackal_verify_receipt`.
- Statuses pass through verbatim; `refused`/`indeterminate` are valid
  terminal outcomes. Never downgrade silently, never upgrade, never
  present an estimate as a bound.

Pinned identities (v1.7.0 epoch):

- package `jackal-v1.7.0-macos-arm64.tar.gz`
  `21c7ede586f30a58772f321f7dbb36ab66213e199785489f99133710ac56096e`
- evaluator `jackal-native`
  `20b80827d3c5c2a5d0d5d6f5a84c692f230fb0f55b9c7d1fcad02a1d0b3a1083`
- proved checker `jackal_cert_check`
  `05c3518b836f239712f897c483a2ddadad9f544e0887b1b7bb1424a27289de8a`
- Gaussian checker `jackal_gaussian_check`
  `ccac690bf916f71a4e3baeb0622dac19aa47e3ca4af858c0800c295581ecfacb`
- composed-integral checker `jackal_int_cert_check`
  `c858e3bfc0ff2809a808170caabbf090077cb54996e76f065dbcd26ffb067d49`
