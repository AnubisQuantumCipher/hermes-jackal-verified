"""Hermes adapter for the reproducible 41-tool JACKAL v1.7.3 candidate."""
from __future__ import annotations

from pathlib import Path

from . import schemas, tools

_ROUTING_RULES = """JACKAL v1.7.3 candidate routing (41-tool inventory):
- Route a known single operation to its exact typed tool: exact/CAS and
  number theory, checked derivatives, estimated or bounded integration,
  or the checker-admitted formal-bounded range/Gaussian/composed/rational
  fragments. Unsupported fragments refuse.
- Route byte-exact source/test structure to jackal_test_exists or
  jackal_claim_cites_test. These establish only the declared structural
  fact. Route caller-declared numeric option ordering to
  jackal_decision_rank or the closed-unit jackal_decision_rank_v2; neither
  establishes that the criterion or supplied values are correct.
- Route mixed, policy-bearing, or consequential multi-step claims through
  jackal_claim, then independently replay with jackal_verify_bundle using
  caller-pinned epoch, proposition, policy, and time. Replay formal receipts
  with jackal_verify_receipt and independent caller expectations.
- Route Anubis Safe-source evidence to jackal_anubis_verify_program or its
  receipt verifier. jackal_anubis_check_program requires the caller-pinned
  approved compiler. No program route executes the artifact; inventory-safe-v1
  leaves construct totality, source-to-VC, SMT-to-CNF, source-native,
  runtime-observation, and universal-soundness residuals open.
- Inspect status before value. Refused and indeterminate are terminal unless
  the caller explicitly requests a separate weaker lane. Never silently
  downgrade or substitute model arithmetic for a refused deterministic lane.
"""


def register(ctx) -> None:
    timeout = int(ctx.get_config("timeout_seconds", 180))
    max_chars = int(ctx.get_config("max_expression_chars", 8192))
    for name in schemas.ALL_TOOLS:
        ctx.register_tool(
            name=name,
            toolset="jackal_verified",
            schema=schemas.SCHEMAS[name],
            handler=tools.make_handler(name, timeout, max_chars),
        )
    skills_dir = Path(__file__).resolve().parent / "skills"
    if skills_dir.is_dir():
        for child in sorted(skills_dir.iterdir()):
            if child.is_dir() and (child / "SKILL.md").is_file():
                ctx.register_skill(child.name, child / "SKILL.md")
    ctx.register_system_prompt_section(
        "jackal-verified.routing", _ROUTING_RULES,
        position="after_memory", max_chars=1800)
