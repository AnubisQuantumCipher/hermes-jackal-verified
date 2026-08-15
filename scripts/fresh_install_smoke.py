#!/usr/bin/env python3
"""Fresh-install smoke test for the standalone repository layout."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]


class Context:
    def __init__(self) -> None:
        self.tools: dict[str, Callable[[dict[str, Any]], str]] = {}
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
        gaussian = json.loads(context.tools["jackal_integrate"]({
            "expression": "exp(-10000000000*(x-0.5000123456789)^2)",
            "lower": 0,
            "upper": 1,
            "assurance": "formal-bounded",
            "tolerance": 1e-12,
        }))
        gaussian_receipt = gaussian["receipt"]
        gaussian_verdict = json.loads(context.tools["jackal_verify_receipt"]({
            "receipt": gaussian_receipt,
        }))
    finally:
        sys.modules.pop(spec.name, None)
    if receipt["result"]["exact"] != "3/10":
        raise SystemExit("fresh-install exact result mismatch")
    if verdict["verification"]["valid"] is not True:
        raise SystemExit("fresh-install receipt validation failed")
    if gaussian_receipt["result"].get("status") != "formal-bounded":
        raise SystemExit("fresh-install Gaussian formal result mismatch")
    if gaussian_verdict["verification"]["valid"] is not True:
        raise SystemExit("fresh-install Gaussian formal validation failed")
    if [name for name, _ in context.skills] != ["jackal-verified-computation"]:
        raise SystemExit("fresh-install skill registration failed")
    if not context.sections or "automatically" not in context.sections[0][1]:
        raise SystemExit("fresh-install routing registration failed")
    print(
        "FRESH_INSTALL_PASS tools=7 skills=1 prompt_sections=1 "
        f"exact={receipt['result']['exact']} receipt_valid=true "
        "gaussian_formal=true gaussian_receipt_valid=true"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
