# Changelog

All notable changes are documented here.

## 2.0.2 — 2026-08-14

### Fixed — formal receipt false accept (§487, Hermes-found; soundness)

- **`jackal_verify_receipt` now re-runs the proved checker.** In 2.0.0/2.0.1,
  `verify_receipt` validated a formal receipt against *itself*: it checked the
  theorem id, that `certificate_sha256` matched a hex pattern, that the enclosure
  was *ordered*, and that `request_commitment` was a *nonempty string* — but it
  never re-executed the checker, never recomputed the request commitment, and
  never confirmed the enclosure was the one the checker accepted. Because the
  outer receipt digest is unkeyed, an auditor could mutate a genuine receipt and
  recompute the digest. Hermes demonstrated four true false accepts this way:
  an ordered-but-wrong enclosure `[0,0]`, a changed request (`x^2+1 → x^999`),
  an arbitrary certificate digest, and an arbitrary request commitment — all
  returned `valid=true`. The 2.0.0 changelog's claim that "a recomputed outer
  digest cannot legitimize a mismatch" was therefore false as shipped.
- **Repair.** Formal receipts now **carry the exact certificate** the checker
  accepted (`result.certificate`, base64). `verify_receipt` decodes it, confirms
  its digest, re-admits the pinned package, and **re-runs `jackal_cert_check` on
  those exact bytes** via the shared release validator — then binds every
  self-reported field (enclosure, request commitment, expr commitment,
  certificate digest, operator set, derived status) to what the checker actually
  accepted. No receipt-authored field is load-bearing; a recomputed digest can
  no longer forge a formal claim. A formal receipt with the certificate stripped
  is refused (it is not independently re-checkable).
- **Regressions.** The four exact Hermes forgeries, the stripped-certificate
  case, and a wider-enclosure substitution are pinned in `tests/test_plugin_v2.py`
  and refuse under both `python3` and `python3 -O`.

### Fixed — hosted CI gate (Hermes-found)

- `.github/workflows/ci.yml` pinned the removed `bin/jackal-native` against the
  old v1.0.0 hash, so every v2 run failed before any test executed. The gate now
  pins the vendored **package** (`pkg/jackal-v1.1.0-macos-arm64.tar.gz`,
  SHA-256 `95588591…`) — what the plugin actually admits — and runs both the
  unit/admission suite and the v2 formal+poison suite (the latter under `-O` too).

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
