# JACKAL Verified — Agent Instructions

Use this snippet in `AGENTS.md`, `CLAUDE.md`, `.cursorrules`, or another agent's standing-instruction file when that agent does not load Hermes plugin skills.

## Verified computation policy

JACKAL Verified is available through Hermes Agent's `jackal-verified` plugin. Route deterministic STEM work through its typed tools when doing so improves correctness or claim discipline:

- exact fractions, factorials, combinations, powers, and large integers → `jackal_exact`;
- ordinary finite IEEE-f64 expression evaluation → `jackal_evaluate`;
- symbolic derivatives → `jackal_differentiate`, reported as checked rather than proved;
- integration → `jackal_integrate` with an explicit `fast_estimate`, `adaptive_estimate`, or `bounded` tier;
- possible values, thresholds, and denominator-zero analysis → `jackal_range_bound`;
- supported physical models with assumptions → `jackal_claim_card`;
- consequential exact, bounded, or model-based outputs → validate with `jackal_verify_receipt`.

Never silently downgrade a bounded request. Never call an estimate a bound, a sampled check a proof, a model fingerprint physical truth, or a matching digest mathematical correctness. Treat `refused` and `indeterminate` as valid outcomes. Preserve the returned assumptions and non-claims.

The approved public JACKAL package/evaluator/checker SHA-256 identities are:

- package `8ed047183bdd6259fc3d9b22ab87003389eabf9c4da1722024848c016fc4ec09`;
- evaluator `820c0722e46a0800115c404ea1c9251c6f72fe8c6897bdabe437f342f9310b6c`;
- proved checker `2186b43f8e45b7b3e55e189d64e92f15999664f5194caed929d14b29b006f59b`.

This snippet describes routing and reporting discipline only. Non-Hermes agents still need an authorized mechanism to call the Hermes plugin; do not invent a shell or network interface.