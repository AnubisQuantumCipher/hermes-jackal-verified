# JACKAL Receipt Contract

`jackal-hermes-receipt-v1` contains exactly:

- `schema`
- `operation`
- `request`
- `result`
- `instrument`
- `receipt_sha256`

The digest is SHA-256 over canonical JSON of the first five fields: UTF-8, sorted keys, compact separators, and non-finite JSON numbers forbidden.

## Status invariants

- `exact`: canonical exact text is authoritative; decimal approximation is a non-claim.
- `estimated`: may contain a heuristic error estimate; never a bound.
- `checked`: must include verification metadata; never identity proof.
- `bounded`: must include an ordered finite enclosure. For integration, width must not exceed the requested tolerance plus the adapter's 1e-9 relative serialization allowance.
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

A recomputed receipt digest does not rescue semantic poison such as a reversed enclosure. Digest validity and result validity are separate obligations.
