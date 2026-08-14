# Changelog

All notable changes are documented here.

## 2.0.0 — 2026-08-14

### Added — proof-carrying formal lane (breaking receipt/status contract)

- **Packaged proved checker.** The plugin now ships the upstream JACKAL v1.1.0
  release as one vendored, verified 40 MB archive containing BOTH the evaluator
  (`jackal-native`, SHA-256 `820c0722…`) AND the Lean-proved certificate checker
  (`jackal_cert_check`, SHA-256 `2186b43f…`). The archive is byte-identical to
  the public jackal-calc v1.1.0 release asset (SHA-256 `95588591…`), so its
  provenance is independently verifiable. It is admitted — tarball-hash +
  safe-extract + SHA256SUMS-inventory + per-binary SHA/Mach-O-arm64/mode
  verified — into a private 0500 snapshot before either binary runs. A plain
  `git clone` carries everything; every calculator call is offline.
- **`jackal_range_bound` is now `formal-bounded`.** It runs the checker-verified
  release path (emit certificate → proved checker ACCEPT → evaluator/checker
  identity + TOCTOU + request-commitment bindings → formal-status gate) and
  releases `status=formal-bounded` ONLY on ACCEPT — otherwise refuses (no
  bounded fallback). Operators outside the mechanized fragment refuse.
- **`jackal-hermes-receipt-v2`.** Formal receipts bind the exact request
  commitment, evaluator + checker identities, certificate digest, `cert_status`
  (distinct from the released `formal-bounded`), the soundness theorem
  `cert_check_sound`, and the covered operator set. `jackal_verify_receipt`
  recomputes these semantic relationships; a recomputed outer digest cannot
  legitimize a request/result/identity/coverage mismatch.

### Boundary

- `formal-bounded` = a checker-accepted, `Runs`-derived enclosure of the exact
  semantics over the modeled fragment, under the recorded TCB. Weaker lanes
  (`estimated`/`checked`/`exact`/`model-based`) keep their class and can never
  become formal. v1 receipts cannot satisfy v2 formal verification.

## 1.0.1 — 2026-08-13

### Fixed

- Removed the remaining documentation overclaim that described an unkeyed SHA-256 checksum as byte authentication.
- Promoted the private-snapshot A→B→A public-path substitution challenge into the permanent regression suite.

## 1.0.0 — 2026-08-13

### Added

- Seven typed Hermes tools for exact arithmetic, finite-real evaluation, checked symbolic differentiation, explicit-tier integration, certified range bounds, model-based claim cards, and receipt validation.
- Content-pinned JACKAL v1.0.0 Apple Silicon executable with before/after identity checks.
- Canonical `jackal-hermes-receipt-v1` receipts.
- Semantic receipt validation beyond digest checking.
- Companion `jackal-verified-computation` skill for automatic assurance selection and non-inflation.
- Agent-neutral `AGENTS-SNIPPET.md` for systems that do not load Hermes plugin skills.
- Thirteen-test unit and poison suite covering plugin/skill/routing registration, binary substitution, receipt tampering, semantic receipt forgery, reversed intervals, cross-operation status forgery, hostile input, fail-closed hazards, and bounded narrow-peak computation.
