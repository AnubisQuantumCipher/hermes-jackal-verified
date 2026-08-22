# JACKAL verified computation — standing agent instructions

The `jackal-verified` v6.0.0 candidate exposes the reproducible JACKAL v1.7.3
candidate package as exactly 41 typed tools. Candidate status does not assert
a public v1.7.3 or v6.0.0 release.

- Route one known operation through its exact typed tool. Exact/CAS,
  number-theory, checked derivative, estimated integration, bounded
  integration, and formal-bounded lanes have different meanings.
- Route a mixed, unit-aware, model-conditioned, policy-bearing, or
  consequential claim through `jackal_claim`, then independently replay it
  with `jackal_verify_bundle` and caller-pinned expectations.
- Replay formal receipts with `jackal_verify_receipt`; never copy an
  `expected_*` value from the receipt being verified.
- Use `jackal_test_exists` and `jackal_claim_cites_test` only for byte-exact
  source structure. They do not establish correctness, execution, assertion
  quality, or coverage.
- Use `jackal_decision_rank_v2` for a caller-declared numeric criterion with
  a canonical unit. The unit is not a measurement, and neither decision tool
  establishes that the criterion or values are appropriate.
- Use `jackal_anubis_verify_program` for caller-selected Safe source/evidence
  bytes and `jackal_anubis_verify_program_receipt` for replay.
  `jackal_anubis_check_program` requires the exact approved compiler and a
  new output root. No program route executes the compiled artifact.
- Preserve `policy-construct-totality-not-established`, source-to-VC,
  SMT-to-CNF, source-native, runtime-observation, and universal-soundness
  residuals on program evidence.
- Inspect `status` before values. Preserve named refusals and indeterminate
  results. Never silently downgrade; run a weaker lane only as a separately
  labeled call after explicit caller authorization.

Candidate pins:

- package `jackal-v1.7.3-macos-arm64.tar.gz`
  `d0c2c87d357aa9cae6551343215910032f30259e4a6b40cde0b64687cba107d4`
- capability inventory
  `b26606faab2acba95d42b964787b75029b84df3038cc047ae00e5234378aebd4`
- evaluator `jackal-native`
  `f11f3a429aa64dc0f09eb930e82bc3250e19eeb5a8a74b26b86683fafd72a655`
- range checker `jackal_cert_check`
  `f7a82524d082b51a8d66f9bed653b9c8da51b5424386659c9048b9c0ae276545`
- Gaussian checker `jackal_gaussian_check`
  `ccac690bf916f71a4e3baeb0622dac19aa47e3ca4af858c0800c295581ecfacb`
- composed-integral checker `jackal_int_cert_check`
  `f8347cbd18d520852aff56920d41f5e5b496ff192f584e41d84d1a818ff29617`

Treat these hashes as byte identities, not authentication or universal
correctness claims.
