# Contributing

Contributions are welcome when they preserve the plugin's fail-closed assurance contract.

## Development setup

1. Install Hermes Agent from its official documentation.
2. Clone this repository.
3. Run `python3 tests/test_plugin.py`.
4. Run `hermes plugins doctor . --ci`.

The embedded `bin/jackal-native` currently targets Apple Silicon macOS. Cross-platform work should add explicit platform artifacts and digest selection; never silently execute an unpinned binary found on `PATH`.

## Required invariants

A contribution must not:

- expose a generic JACKAL command or shell tool;
- use `shell=True`;
- silently downgrade `bounded` to `estimated`;
- classify a receipt digest as mathematical validity;
- accept unknown epistemic statuses;
- accept malformed, reversed, non-finite, or over-tolerance enclosures;
- skip executable identity checks;
- describe sampled derivative checking as proof;
- describe model-based output as observed reality.

## Pull requests

Include:

- the exact behavior changed;
- tests for positive behavior and at least one negative control;
- `python3 tests/test_plugin.py` output;
- `hermes plugins doctor . --ci` output;
- updated documentation and `MANIFEST.json` if sealed files changed;
- a bounded statement of what remains unverified.

Do not commit secrets, local Hermes configuration, sessions, logs, or receipts containing user data.
