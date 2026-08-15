# JACKAL Receipt Contract

`jackal-hermes-receipt-v2` contains exactly:

- `schema`
- `operation`
- `request`
- `result`
- `instrument`
- `receipt_sha256`

The digest is SHA-256 over canonical JSON of the first five fields: UTF-8, sorted keys, compact separators, and non-finite JSON numbers forbidden. It is an unkeyed checksum for integrity and self-consistency, not a signature or hostile-author authentication mechanism.

## Status invariants

- `exact`: canonical exact text is authoritative; decimal approximation is a non-claim.
- `estimated`: may contain a heuristic error estimate; never a bound.
- `checked`: must include verification metadata; never identity proof.
- `bounded`: must include an ordered finite enclosure. For integration, width must not exceed the requested tolerance plus the adapter's 1e-9 relative serialization allowance.
- `formal-bounded`: must carry a canonical nested `jackal-formal-receipt-v1` containing the exact checker-accepted certificate in base64, its SHA-256, exact request and expression commitments, pinned evaluator/checker/plugin identities, theorem `cert_check_sound`, certificate status, admitted operator set, coverage rows, assumptions, and non-claims. Verification re-admits the package and re-runs the proved checker on those certificate bytes, then binds the outer Hermes fields to the verifier-derived request, enclosure, certificate, operators, and identities.
- `model-based`: canonical preimage SHA-256 must equal the printed fingerprint.
- `refused`: `released=false`, nonzero exit, named reason; no computed value.
- `indeterminate`: infrastructure did not complete; no mathematical claim.

## Validator negative controls

The validator rejects:

- any missing or extra top-level key;
- receipt digest mismatch;
- instrument digest mismatch;
- unknown status;
- malformed, reversed, or over-tolerance enclosure;
- claim-card fingerprint mismatch.
- a formal receipt without its nested canonical receipt or embedded certificate;
- a certificate digest that does not match the embedded bytes;
- a request, enclosure, commitment, operator set, evaluator/checker/plugin identity, coverage row, or theorem that does not match the re-executed checker result.

A recomputed receipt digest does not rescue semantic poison. The digest is an unkeyed integrity checksum; formal validity comes from re-running the proved checker on the embedded certificate and recomputing all bindings.
