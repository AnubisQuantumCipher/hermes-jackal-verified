# Changelog

All notable changes are documented here.

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
