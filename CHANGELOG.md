# Changelog

## 4.0.0 — 2026-08-16

**The Mathematical Evidence Kernel epoch: 33 tools, faithful pass-through
over the sealed public JACKAL v1.6.0 release.**

- Vendored package re-pinned to the public `jackal-calc` v1.6.0 release
  asset `pkg/jackal-v1.6.0-macos-arm64.tar.gz` (sha256
  `0cdacf56bb83d65454330973280cde7da0b9262d6163ccd7efbbbb47bc88e39a`,
  79,519,523 bytes), verified byte-identical to the unauthenticated
  GitHub release download (upstream commit
  `19b763e9451276e72c7511ec8ba42bf828d096f6`, tag `v1.6.0`).
- Tool surface: 10 → **33** — the intact upstream 31-tool v1.5.0 floor
  (9 formal lanes incl. the five pure-Q fragments added in v1.5.0,
  7 numeric weaker lanes, 14 exact-CAS certificate lanes,
  `jackal_verify_receipt`) plus the two v1.6.0 claim-kernel front doors
  `jackal_claim` / `jackal_verify_bundle`.
- **Architecture: pass-through adapter.** Every tool call now executes
  the upstream `jackal_hermes` frontend inside the admitted package
  snapshot; the plugin adds no mathematical behavior of its own. The
  in-process `jackal_formal/` runtime copy is REMOVED (its drift class
  is gone with it); the admitted tarball is the runtime.
- Schemas are GENERATED from the vendored package's `tools.json`
  (`scripts/gen_schemas.py`); CI enforces byte-identical regeneration.
- New machine-readable epoch receipt `EPOCH.json`
  (`jackal-plugin-epoch-receipt-v1`), cross-checked at admission.
- Admission now verifies: tarball pin + epoch receipt + internal
  SHA256SUMS (complete, no extras) + 30-row `APPROVED_IDENTITIES` table
  + Mach-O arm64 magic; per-call TOCTOU re-hash before and after.
- Tests rewritten for the new boundary: 18-case unit battery, 36-row
  poison battery (default and `-O`), and an A→B→A gate proving the
  identity-enforcement pair (admission pin loop + TOCTOU-pre) is
  load-bearing across four package forgeries — with the pair disabled,
  tampered bytes reach execution and the upstream package's own
  bundle-hash / evaluator-identity layers still refuse (defense in
  depth, mechanically demonstrated).
- Bundled skill `jackal-verified-computation` → **5.0.0**: 33-tool
  routing model (direct lanes vs `jackal_claim` vs
  `jackal_verify_bundle`), refusal-not-downgrade discipline, v1.6.0
  identities, migration notes.
- BREAKING (v3 → v4): `jackal_differentiate` → `jackal_diff`;
  `jackal_claim_card` removed (route model claims through
  `jackal_claim`); `jackal_exact` arguments are now
  `{"expression": "..."}` (the sealed upstream shape). Receipts issued
  by older epochs keep verifying under their original caller-pinned
  expectations.

All notable changes are documented here.

## 3.0.0 — 2026-08-15

### Added — three new proof-carrying formal lanes

- **`jackal_gaussian_integral`** — Formal-bounded release of Gaussian integrals
  `exp(a·(x−b)²)` (a<0) via the vendored zero-libm Gaussian checker
  (`jackal_gaussian_check`, SHA-256 `42d3f3e74b90062c958baeda9ddf9ddd6f82ef3f8e4dd2b9ade5017239fe7a77`).
  Theorem `gaussian_integral_check_sound`. Emits
  `jackal-formal-receipt-v1(variant=gaussian)`.
- **`jackal_sqrt_rat_bound`** — Pure-Q `sqrt(x)` enclosure on `[lo, hi]` via
  `sqrt_rat_producer.py` (SHA-256 `4bc95c331430d2350facfb19da9aba483ab7b3698754e7af2e5deb797e097926`)
  and the Lean-proved range checker `jackal_cert_check`
  (SHA-256 `b567b8a94ce7acd49ecaa807d86a5bb66d695fb0ce4fea2eb84f0073425984d7`).
  Theorem `request_bound_certified_release`. **No libm on the proof-decision
  path.** Emits `jackal-formal-receipt-v1(variant=sqrt_rat)`.
- **`jackal_exp_rat_bound`** — Pure-Q `exp(x)` enclosure on `[lo, hi]` with
  `lo ≥ 0` via `exp_rat_producer.py`
  (SHA-256 `ccbc48633bd3980613413399d552321eaa67b15bd101643e53b0dd5f10a37918`)
  and the same Lean-proved range checker. Theorem
  `request_bound_certified_release`. **No libm on the proof-decision path.**
  Emits `jackal-formal-receipt-v1(variant=exp_rat)`.

### Changed — receipt schema (variant-aware, backward-compatible)

- Formal receipts now carry a mandatory `variant` field
  (`range | gaussian | sqrt_rat | exp_rat`). `jackal_verify_receipt` dispatches
  on `variant` to select the correct pinned checker binary, expected producer
  identity, and expected theorem id. Variant coverage is enforced by the outer
  Hermes verifier.
- Producer identity is now bound alongside the checker identity for every
  formal lane; a receipt's declared `instrument.evaluator.sha256` must match
  the lane's admitted producer SHA-256 or the receipt is refused.
- Plugin surface expanded to **10 tools** (from 7). Automatic routing policy
  updated. `plugin.yaml` bumped to `v3.0.0` and `provides_tools` listing all
  ten tools.

### Fixed — vendored release identity

- Re-pinned the vendored package to public JACKAL `v1.4.2`, archive SHA-256
  `30b1a7441cdd9c1b0f24ac6d187608d3235f1ced6c57469dc1b1f697f475b1a0`. Evaluator
  identity is unchanged (`820c0722…`).
- Vendored proof identities, coverage inventory, source `.anb`, and the
  upstream `gaussian_release.py` are now shipped alongside the release
  validator so the release path is self-contained.

### Regressions

- `tests/test_plugin.py` bumped to **18 unit tests**, including three new
  variant round-trips and a load-bearing variant-mutation lock (21 mutations
  across gaussian/sqrt_rat/exp_rat).
- `tests/test_plugin_v2.py` bumped to **76 poison cases**, including three
  new variant round-trips, 18 variant-mutation locks, and negative-fragment
  refusal for the sqrt_rat/exp_rat lanes.
- `tests/aba_recheck_gate.py` bumped to **16 A→B→A cases** (4 lanes × 4
  master-gate-only forgeries) — all pass with hash-verified restoration.

## 2.1.0 — 2026-08-15

### Added — upstream v1.2.0 formal-receipt closure

- Re-pinned the vendored package to public JACKAL `v1.2.0`, archive SHA-256
  `3b63e86bd9d2cffafa33dde813c40919cc754343db2232b1c33072a3ec41e0a7`.
  Evaluator (`820c0722…`) and proved checker (`2186b43f…`) identities are
  unchanged; the package adds the canonical `jackal-formal-receipt-v1`,
  independent receipt verifier, bundled formal adapter, and v1.2 evidence.
- `jackal_range_bound` now carries the upstream canonical formal receipt inside
  `jackal-hermes-receipt-v2`. The native plugin manifest SHA-256 is bound as the
  formal receipt's plugin identity.
- `jackal_verify_receipt` invokes the upstream independent verifier, which
  re-runs the pinned checker on the embedded certificate and re-derives request,
  enclosure, operator, coverage, and evaluator/checker/plugin bindings. It then
  cross-checks those results against the outer Hermes receipt.
- Updated the companion skill to distinguish ordinary conditional `bounded`
  integration from theorem-backed `formal-bounded` range analysis.

## 2.0.3 — 2026-08-14

### Fixed — immutable upstream package epoch

- Re-pinned the vendored formal package to public JACKAL `v1.1.1`, archive
  SHA-256 `8ed047183bdd6259fc3d9b22ab87003389eabf9c4da1722024848c016fc4ec09`
  (39,912,160 bytes). The evaluator (`820c0722…`) and proved checker
  (`2186b43f…`) are unchanged; only package labels and release identity moved.
- Restored public JACKAL `v1.1.0` to its original `95588591…` archive after an
  in-place replacement was detected. v1.1.1 is the corrected immutable
  successor; v2.0.3 binds to it instead of rewriting v2.0.2 history.
- Updated the bundled skill and receipt contract to schema v2. Formal receipts
  carry the exact certificate, and verification re-runs the proved checker on
  those bytes before accepting any formal result.

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
  pinned the vendored **package** (`pkg/jackal-v1.1.0-macos-arm64.tar.gz`,
  SHA-256 `95588591…`) — what the plugin actually admitted in that epoch — and ran both the
  unit/admission suite and the v2 formal+poison suite (the latter under `-O` too).

### Fixed — vendored/public tarball internal release identity (Hermes-found)

- The vendored (and public) v1.1.0 archive `95588591…` was internally labeled
  **`v1.0.4` / "PRIVATE … no public download is claimed"** in its `README.txt`,
  `MANIFEST.sha256`, `NON-CLAIMS.txt`, and `PROVENANCE-RECEIPT.txt` — false now
  that jackal-calc is public. The archive was rebuilt with correct `v1.1.0` /
  public / unsigned-ad-hoc labels (`release/build_package.sh`); the two shipped
  binaries are **unchanged and re-verified** (`jackal-native` `820c0722…`,
  `jackal_cert_check` `2186b43f…`), so the pinned evaluator/checker identities
  and the `cert_check_sound` trust chain are untouched. An attempted in-place
  re-pin to `b3750df8…` was later reversed: v1.1.0 was restored to `95588591…`,
  and the corrected package was published immutably as v1.1.1 for plugin 2.0.3.

## 2.0.0 — 2026-08-14

### Added — proof-carrying formal lane (breaking receipt/status contract)

- **Packaged proved checker.** The plugin now ships the upstream JACKAL v1.1.0
  release as one vendored, verified 40 MB archive containing BOTH the evaluator
  (`jackal-native`, SHA-256 `820c0722…`) AND the Lean-proved certificate checker
  (`jackal_cert_check`, SHA-256 `2186b43f…`). The archive is byte-identical to
  the public jackal-calc v1.1.0 release asset (SHA-256 `95588591…`; corrected and
  re-pinned to `b3750df8…` in 2.0.2, see below), so its
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
