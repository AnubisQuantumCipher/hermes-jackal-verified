# Security policy

## Supported state

Security fixes are applied to published releases according to repository
policy. The v6.0.0 material and embedded JACKAL v1.7.3 package on this branch
are unpublished candidates and are not represented as supported releases.
Receipts and epoch metadata bind exact bytes, so replacing the embedded JACKAL
package is an explicit compatibility and re-audit event.

## Report a vulnerability

Open a private GitHub security advisory for this repository. Do not publish an
exploitable report before maintainers have had a reasonable opportunity to
investigate.

Include the affected plugin version and commit, operating system and Hermes
version, a minimal reproduction, expected and observed behavior, and whether
the issue permits package substitution, shell execution, receipt forgery,
assurance downgrade, malformed-bound acceptance, program-artifact execution,
or sensitive-data exposure.

## Runtime model

The candidate exposes 41 fixed typed tools. It is not a generic shell tool.
Most calls run the vendored JACKAL frontend only. The
`jackal_anubis_check_program` route may invoke a caller-selected local Anubis
binary solely as `build --evidence`, but only after its bytes match the closed
approved compiler identity; it never executes the compiled artifact.

Before the first call, the plugin:

1. reconstructs the exact declared package parts and verifies the outer
   package SHA-256 against both code and `EPOCH.json`;
2. safely extracts only regular files and directories into a private `0700`
   snapshot;
3. verifies complete internal `SHA256SUMS` closure with no missing or extra
   files;
4. verifies 53 selected evaluator, checker, producer, verifier, policy,
   inventory, profile, and proof-identity files;
5. requires arm64 Mach-O format for the four native binaries.

Each tool call re-hashes nine execution-path files before and after the
subprocess. Calls use an argument vector with `shell=False`, no stdin, a
restricted `PATH`, a private `HOME`, and a timeout. The adapter accepts only
one JSON object containing a `status` field. Admission, argument-length,
timeout, execution, empty-output, malformed-JSON, or response-shape failures
return named local refusals.

This is integrity and fail-closed plumbing, not a sandbox. The plugin's Python
and native code execute with the user's authority. Install only an immutable
commit and package identity that you trust.

## Evidence model

Formal receipts use a closed variant/epoch registry and caller-supplied
expected values. The independent verifier re-runs the selected pinned checker;
an outer receipt digest is not sufficient. Unsupported fragments and revoked
request-unbound composed-integral receipts refuse.

Claim bundles are replayed against caller-pinned epoch, policy digest, root
proposition, verification time, and nonce. Expected pins are authorization and
must not be copied from the object being verified.

Structural certificates prove only byte-exact declaration/citation structure.
Decision certificates prove only ordering over caller declarations. Their
consequence ceilings remain informational and decision-boundary respectively.

Anubis program evidence is checked under `inventory-safe-v1`: strict v3 file,
stage, consumer, and proof rosters; exact source/compiler/artifact/policy pins;
approved-Z3 UNSAT replay; and independent RUP replay. The verifier never
executes the artifact. It explicitly does not establish policy-construct
totality, source-to-VC proof, SMT-to-CNF proof, source-native refinement,
runtime behavior, or universal language soundness.

The approved Z3 4.15.4 binary identity is a macOS 26 build. The complete
positive 41-tool path is validated on macOS 26 arm64. On an earlier host, the
program route must refuse if that exact solver cannot execute; the adapter
must not substitute a newer or platform-specific Z3 build.

## Skill boundary

The bundled skill is executable guidance for tool selection and result
interpretation, not a runtime security boundary. Its hash is generated into
`EPOCH.json`, and source tests plus `MANIFEST.json` detect drift. Package
admission does not establish that an operator or model followed the prompt.

## Out of scope as security claims

- authorship or authenticity from SHA-256 alone;
- universal correctness of JACKAL, Anubis, Lean, or Hermes;
- end-to-end formal verification of the plugin or native binaries;
- proof that every platform `libm` satisfies a numerical model;
- source-to-native refinement or proof of runtime behavior;
- correctness or execution of a structurally identified test;
- truth of caller-supplied measurements, models, criteria, or real-world data;
- replay prevention without an external nonce store;
- notarization, sandboxing, or non-macOS execution.
