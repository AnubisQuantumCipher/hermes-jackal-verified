#!/usr/bin/env python3
"""Fresh-install smoke test for the standalone repository layout."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class Context:
    def __init__(self) -> None:
        self.tools: dict[str, object] = {}
        self.skills: list[tuple[str, Path]] = []
        self.sections: list[tuple[str, str]] = []

    def get_config(self, _name, default=None):
        return default

    def register_tool(self, name, handler, **_kwargs):
        self.tools[name] = handler

    def register_skill(self, name, path):
        self.skills.append((name, Path(path)))

    def register_system_prompt_section(self, section_id, content, **_kwargs):
        self.sections.append((section_id, content))


def main() -> int:
    spec = importlib.util.spec_from_file_location(
        "jackal_verified", ROOT / "__init__.py",
        submodule_search_locations=[str(ROOT)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        context = Context()
        module.register(context)
        exact = json.loads(context.tools["jackal_exact"]({"mode": "rational", "expression": "0.1+0.2"}))
        receipt = exact["receipt"]
        verdict = json.loads(context.tools["jackal_verify_receipt"]({"receipt": receipt}))
    finally:
        sys.modules.pop(spec.name, None)
    if receipt["result"]["exact"] != "3/10":
        raise SystemExit("fresh-install exact result mismatch")
    if verdict["verification"]["valid"] is not True:
        raise SystemExit("fresh-install receipt validation failed")
    if [name for name, _ in context.skills] != ["jackal-verified-computation"]:
        raise SystemExit("fresh-install skill registration failed")
    if not context.sections or "automatically" not in context.sections[0][1]:
        raise SystemExit("fresh-install routing registration failed")
    print(
        f"FRESH_INSTALL_PASS tools={len(context.tools)} skills={len(context.skills)} "
        f"prompt_sections={len(context.sections)} "
        f"exact={receipt['result']['exact']} receipt_valid=true"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
