# JACKAL Verified — Hermes plugin (v6.0.0 candidate)

[![CI](https://github.com/AnubisQuantumCipher/hermes-jackal-verified/actions/workflows/ci.yml/badge.svg)](https://github.com/AnubisQuantumCipher/hermes-jackal-verified/actions/workflows/ci.yml)
![Platform](https://img.shields.io/badge/platform-macOS%20arm64-lightgrey)
![License](https://img.shields.io/badge/license-MIT-blue)

Typed, receipt-bearing access to the reproducible JACKAL v1.7.3 candidate
package from Hermes. The candidate exposes exactly 41 tools from the package's
canonical capability inventory.

> Candidate status: neither JACKAL v1.7.3 nor this plugin's v6.0.0 has been
> published as a release by this repository. The vendored bytes and candidate
> commits are review artifacts; they are not evidence of a public tag or
> release asset.

## Bound candidate

| Field | Value |
|---|---|
| JACKAL build commit | `957ac893b243814d9059e6e104c21e0ce68e9ef5` |
| Alignment receipt commit | `0bca7da98def582bb0ce34a7dfb9b540e599d1b1` |
| Package | `jackal-v1.7.3-macos-arm64.tar.gz` |
| Package SHA-256 | `b317849234208ab6f435e5bad1336e4bf4d039981811323e35138c2e0a4ee68d` |
| Package size | 158,363,755 bytes |
| Internal `SHA256SUMS` SHA-256 | `c0afbe8108517b30d36d8aab8ac3cddc0bae78588b41d86e976eee53da92be7f` |
| Capability inventory SHA-256 | `19930922418aa0f751c8ee3476f31677368e0c29c5f1c5ea8942ea7fb597d60c` |
| Release state | `v1.7.3-candidate` |

The package was built twice from the clean build commit and the two tarballs
were byte-identical. The dedicated alignment receipt is
`release/evidence/package_alignment_v173_candidate.json` in the JACKAL
repository. This plugin vendors those package bytes as two ordered raw parts
under `pkg/` because GitHub rejects a single file of at least 100 MiB.

## Acyclic trust chain

```text
JACKAL source build commit 957ac893b243814d9059e6e104c21e0ce68e9ef5
  -> two byte-identical candidate package builds
     (sha256 b317849234208ab6f435e5bad1336e4bf4d039981811323e35138c2e0a4ee68d)
  -> immutable JACKAL alignment receipt commit
     0bca7da98def582bb0ce34a7dfb9b540e599d1b1
  -> this plugin's ordered vendored parts
  -> scripts/generate_epoch.py
       -> EPOCH.json
       -> tools.py selected-identity table
  -> generated schemas.py + plugin.yaml 41-tool registration
  -> MANIFEST.json over this plugin candidate
```

The JACKAL package does not reference this plugin. Package delivery pins are
kept outside the package's semantic capability inventory, avoiding a
self-referential package-hash cycle.

## The 41-tool surface

| Family | Count | Tools and boundary |
|---|---:|---|
| Formal producers | 10 | `jackal_range_bound`, `jackal_gaussian_integral`, `jackal_integrate_bound_cert`, and `jackal_{sqrt,exp,ln,sin,cos,atan,tanh}_rat_bound`; only a checker-accepted fragment returns `formal-bounded` |
| Formal replay | 1 | `jackal_verify_receipt`; replays only the closed epoch/variant registry against independent caller expectations |
| Numeric and exact | 21 | `jackal_exact`, `jackal_evaluate`, `jackal_diff`, three integration lanes, `jackal_solve`, and fourteen exact algebra/number-theory tools |
| Claim graph | 2 | `jackal_claim`, `jackal_verify_bundle`; compilation plus caller-pinned independent replay |
| Source structure | 2 | `jackal_test_exists`, `jackal_claim_cites_test`; byte-exact structural facts with an informational consequence ceiling |
| Decision ranking | 2 | `jackal_decision_rank`, `jackal_decision_rank_v2`; exact ordering of caller-declared values, not validation of the criterion or measurements |
| Anubis program evidence | 3 | `jackal_anubis_check_program`, `jackal_anubis_verify_program`, `jackal_anubis_verify_program_receipt`; strict `inventory-safe-v1` verification without artifact execution |

The authoritative order, schemas, status classes, dependencies, fragments,
and refusal boundaries are in `capability_inventory_v1.json` inside the
vendored package. `scripts/gen_schemas.py` derives this plugin's schemas from
the same packaged catalog, and CI requires exact inventory/catalog/schema/
registration equality.

## Assurance boundaries

- `formal-bounded` applies only to the named Lean-checker fragment. An
  unsupported expression refuses; the plugin does not substitute a weaker
  numerical lane.
- `bounded`, `checked`, `estimated`, `exact`, and `model-based` retain their
  catalog-declared meanings. An estimate is not a bound, and exact arithmetic
  over supplied inputs does not establish that the inputs are true.
- Source-structure certificates establish declaration or citation structure,
  not correctness, test execution, assertions, or coverage.
- Decision certificates order caller-supplied numbers. A declared unit is not
  a measurement, and the selected criterion remains the caller's.
- Program verification checks exact source/evidence identities, strict v3
  rosters, producer-summary reconciliation, approved-Z3 UNSAT replay, and
  independent RUP replay. It leaves policy-construct totality, source-to-VC,
  SMT-to-CNF, source-native refinement, runtime behavior, and universal
  language soundness open.
- `refused` and `indeterminate` are terminal unless a caller explicitly asks
  for a separately labeled weaker lane.

## Adapter security model

1. Admission reconstructs the declared package parts, verifies the outer
   package hash and `EPOCH.json`, extracts only regular safe paths into a
   private `0700` directory, verifies complete internal `SHA256SUMS` closure,
   checks 53 selected trust-bearing identities, and checks the four native
   binaries for arm64 Mach-O format.
2. Each call re-hashes the frontend and nine runtime trust files before and
   after execution. The subprocess uses `shell=False`, no stdin, a restricted
   `PATH`, and the private directory as `HOME`.
3. The adapter requires one JSON object with a `status` field and serializes
   that parsed runtime object. Admission, argument-length, timeout, execution,
   and transport failures become named local refusals.
4. The generated epoch records the skill hash. Generator tests and the plugin
   manifest detect source drift; runtime package admission itself is not a
   proof that an operator followed the skill prompt.

The plugin is local native code, not a sandbox.

## Candidate installation for review

Install only an independently reviewed, immutable 40-character candidate
commit. Do not use a floating branch and do not treat this candidate as the
published v6 release.

```bash
hermes plugins install AnubisQuantumCipher/hermes-jackal-verified \
  --force --ref <FULL-40-CHAR-CANDIDATE-COMMIT> --enable
hermes plugins doctor jackal-verified --ci
# expected candidate registration: 41 tool(s)
```

Start a new Hermes session after install or upgrade because tool schemas are
loaded once per session. Requirements for the complete 41-tool positive path
are Apple Silicon macOS 26, Python 3.11 or newer, and the approved Z3 4.15.4
binary identity. Earlier macOS hosts may run other package lanes, but the
program verifier will refuse when the approved solver is unavailable or has a
different hash. The vendored JACKAL package itself runs without a first-call
download; Z3 is an external program-replay dependency and is not vendored.

## Usage sketches

```text
"what is 0.1 + 0.2 exactly"              -> jackal_exact -> exact 3/10
"enclose sqrt(x) on [2,3] with proof"    -> jackal_sqrt_rat_bound
"replay this formal receipt"             -> jackal_verify_receipt
"compile and replay this policy claim"   -> jackal_claim + jackal_verify_bundle
"does this exact file declare this test" -> jackal_test_exists
"rank these measured latencies in ms"    -> jackal_decision_rank_v2
"verify this Anubis evidence directory"  -> jackal_anubis_verify_program
```

Expected identity values are caller authorization, not data discovery. Never
copy an `expected_*` value out of the receipt or bundle being verified.

## Verification

```bash
python3 scripts/generate_epoch.py --check
python3 tests/production_alignment_test.py
python3 tests/test_plugin.py
python3 tests/test_plugin_v2.py
python3 -O tests/test_plugin_v2.py
python3 tests/parts_discovery_test.py
python3 tests/aba_recheck_gate.py
python3 scripts/fresh_install_smoke.py
python3 scripts/verify_manifest.py
python3 scripts/release_audit.py
python3 scripts/gen_schemas.py && git diff --exit-code schemas.py
```

The unit battery includes positive structural, decision, whole-program, and
program-receipt replay calls through the Hermes adapter. The hostile battery
also checks the new identity and unit refusal boundaries. CI runs the same
candidate gates on a macOS 26 arm64 runner and provisions the exact approved
Z3 binary from a separately hash-pinned Homebrew bottle.

## Migration from v5.0.0

The candidate change is additive at the tool-name level: the historical
v5.0.0 surface had 34 tools, and v6.0.0 adds two source-structure tools, two
decision tools, and three Anubis program-evidence tools. Existing formal
receipt compatibility remains governed by the closed registry: current range,
pure-rational, and composed-integral receipts use the request-bound v1.7.2
identities; the request-unbound v1.7.0 composed-integral identity remains
revoked.

## Non-claims

SHA-256 identifies bytes; it is not authorship, authenticity, or mathematical
correctness. The Lean audit does not prove the compiler, Lean kernel, native
code, operating system, hardware, or supply chain. Finite hostile campaigns
are bounded evidence, not universal theorems. No public v1.7.3 or v6.0.0
release, notarization, cross-platform support, source-to-native refinement,
runtime execution proof, external nonce store, or real-world input truth is
claimed here.

See `PROVENANCE.md`, `SECURITY.md`, and `THIRD_PARTY_NOTICES.md` for the exact
candidate boundary.

## License

MIT. The vendored JACKAL candidate is separately identified in
`THIRD_PARTY_NOTICES.md`.
