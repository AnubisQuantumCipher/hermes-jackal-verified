"""jackal-verified — typed, receipt-bearing access to the sealed JACKAL
v1.6.0 Mathematical Evidence Kernel (33 tools, pass-through adapter)."""
from __future__ import annotations

from pathlib import Path

from . import schemas, tools

_ROUTING_RULES = """JACKAL verified computation routing:
- Known single lane? Call the direct typed tool: exact rationals ->
  jackal_exact; IEEE evaluation -> jackal_evaluate; checked derivative ->
  jackal_diff; integration estimate/enclosure -> jackal_integrate /
  jackal_integrate_adaptive / jackal_integrate_bound; proved interval
  enclosures -> jackal_range_bound, jackal_gaussian_integral, and the
  pure-Q lanes jackal_{sqrt,exp,ln,sin,cos,atan,tanh}_rat_bound; exact
  CAS -> jackal_canon/poly_*/ratfunc_canon/roots_isolate/alg_*/xgcd/
  mod_pow/mod_inv/crt/divides/prime_cert.
- Mixed, policy-bearing, or consequential multi-step claims ->
  jackal_claim compiles one deterministic content-addressed evidence
  bundle (never a bare VERIFIED).
- Independent replay of a claim bundle -> jackal_verify_bundle with
  CALLER-pinned epoch/root-proposition/policy/time; formal receipts ->
  jackal_verify_receipt (re-runs the pinned Lean-proved checker).
- Statuses pass through verbatim (exact/checked/estimated/bounded/
  formal-bounded/model-based/refused/indeterminate). Refusal and
  indeterminate are valid terminal outcomes. Never silently downgrade,
  never upgrade, never substitute mental arithmetic for a refused lane.
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
