# JACKAL evidence contracts (v1.7.3 candidate)

The canonical per-tool facts are generated in
`release/capability_inventory_v1.json`. A package or plugin adapter may copy a
runtime result object, but the status becomes evidence only through the
runtime's named checker/verifier path and its pinned identities.

## Result classes

- `exact`: deterministic exact output inside the declared grammar; it is not a
  Lean theorem unless a separate formal lane says so.
- `checked`: sampled or challenged agreement, not an identity proof.
- `estimated`: a numerical estimate, never a bound.
- `bounded`: an enclosure conditional on the stated arithmetic/libm model.
- `formal-bounded`: a checker-accepted certificate inside one declared formal
  fragment.
- `model-based`: conditional on explicit model assumptions.
- `structural-exact`: byte-exact structure with an informational consequence
  ceiling; not correctness or coverage.
- `verified-program-evidence` / `verified-program-receipt`: replayed
  inventory-safe-v1 evidence; not formal-bounded and not runtime behavior.
- `refused` / `indeterminate`: no released mathematical value.

## Formal receipts

A canonical `jackal-formal-receipt-v1` binds variant, exact request,
certificate bytes and digest, producer/evaluator/checker identities, theorem,
coverage, assumptions, and non-claims. The dedicated verifier re-runs the
variant-selected checker against caller-pinned expectations. Range and
pure-rational variants use expected command `range-bound-cert`; Gaussian uses
`integrate`; composed integral uses `integrate-bound-cert` and binds tolerance.
The request-unbound v1.7.0 composed-integral identity is revoked.

## Claim bundles

`jackal_claim` produces a content-addressed `jackal-claim-bundle-v1` graph.
`jackal_verify_bundle` recomputes nodes, rules, assurance axes, consequence
floors, and rendering under caller-pinned epoch, policy digest, root
proposition, verification time, and nonce. Never copy those expectations from
the bundle being reviewed.

## Structural and decision certificates

Source-structure certificates bind exact file bytes and declaration/citation
facts, but never claim that a test executes, passes, asserts anything, or
covers prose. Decision certificates recompute an ordering over caller-declared
criterion, values, sense, and, for v2, a canonical unit. A unit is not a
measurement; the arithmetic does not validate the criterion or values.

## Program evidence

Program receipts bind caller-selected Safe source, strict v3 evidence bytes,
compiler, artifact, policy, verification time, profile, and nonce. Independent
verification replays approved Z3 UNSAT and RUP proof bytes without executing
the artifact. It does not establish source-to-VC, SMT-to-CNF,
policy-construct-totality, source-native refinement, runtime behavior, or
universal language soundness.

## Negative controls

Require pristine → tamper → pristine replay. Mutated request, epoch, policy,
root proposition, unit, node, certificate, checker identity, program roster,
artifact pin, or outer receipt semantics must refuse. Recomputing an unkeyed
outer digest never rescues semantic poison.
