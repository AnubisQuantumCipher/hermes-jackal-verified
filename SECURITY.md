# Security Policy

## Supported versions

Security fixes are applied to the latest release. Receipts bind each computation to an exact executable digest, so changing the embedded JACKAL executable is an explicit compatibility and re-audit event.

## Report a vulnerability

Open a private GitHub security advisory for this repository. Do not publish an exploitable report before maintainers have had a reasonable opportunity to investigate.

Please include:

- affected version and commit;
- operating system and Hermes version;
- minimal reproduction;
- expected and observed behavior;
- whether the issue permits binary substitution, shell execution, receipt forgery, assurance downgrade, malformed-bound acceptance, or sensitive-data exposure.

## Security model

The plugin is local and offline. It exposes thirty-three fixed tools, not arbitrary command execution. It copies a content-pinned JACKAL executable into a private `0700` execution directory, verifies the snapshot, then invokes it with an argument array, `shell=False`, a restricted environment, and bounded input/output/runtime. The source and private snapshot are rechecked after execution.

Receipt validation has two independent layers:

1. canonical checksum validation (integrity/self-consistency, not signature authentication);
2. semantic validation of instrument identity, status vocabulary, interval ordering and tolerance, and claim-card fingerprints.

The plugin is not a sandbox. Like all native Hermes plugins, its Python code executes with the user's authority. Install only from a source and release digest you trust.

## Out of scope as security claims

- Universal correctness of JACKAL or Anubis.
- End-to-end formal verification of the plugin or embedded binary.
- Proof that every platform libm satisfies JACKAL's stated model.
- Physical validity of model-based claim cards.
