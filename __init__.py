"""JACKAL Verified native Hermes plugin."""
from __future__ import annotations

from pathlib import Path

from . import schemas, tools


_ROUTING_RULES = """JACKAL verified computation is available in this session.
Use it automatically when deterministic arithmetic would improve reliability:
- jackal_exact for exact fractions, factorials, combinations, powers, or large integers;
- jackal_evaluate for ordinary finite IEEE-f64 expression evaluation;
- jackal_differentiate for symbolic derivatives released as checked, not proved;
- jackal_integrate with an explicit estimate or bounded assurance tier;
- jackal_range_bound for formal-bounded possible-value, threshold, or denominator-zero questions in the declared range fragment;
- jackal_gaussian_integral for formal-bounded Gaussian integrals of the form exp(a*(x-b)^2) via the zero-libm Gaussian checker;
- jackal_sqrt_rat_bound for formal-bounded pure-Q enclosures of sqrt(x) on [lo, hi];
- jackal_exp_rat_bound for formal-bounded pure-Q enclosures of exp(x) on [lo, hi] with lo >= 0;
- jackal_claim_card for the supported model with explicit assumptions;
- jackal_verify_receipt before relying on consequential exact, bounded, formal-bounded, or model-based results.
Never silently downgrade a bounded request, call an estimate a bound, call a check a proof,
or treat a matching digest as mathematical correctness. Refusal and indeterminate are valid outcomes.
"""


def register(ctx) -> None:
    timeout = ctx.get_config("timeout_seconds", default=180)
    max_chars = ctx.get_config("max_expression_chars", default=8192)

    def wrap(handler):
        return lambda args, **kwargs: handler(args or {}, timeout=timeout, max_chars=max_chars)

    ctx.register_tool(name="jackal_exact", toolset="jackal_verified", schema=schemas.EXACT, handler=wrap(tools.exact))
    ctx.register_tool(name="jackal_evaluate", toolset="jackal_verified", schema=schemas.EVALUATE, handler=wrap(tools.evaluate))
    ctx.register_tool(name="jackal_differentiate", toolset="jackal_verified", schema=schemas.DIFFERENTIATE, handler=wrap(tools.differentiate))
    ctx.register_tool(name="jackal_integrate", toolset="jackal_verified", schema=schemas.INTEGRATE, handler=wrap(tools.integrate))
    ctx.register_tool(name="jackal_range_bound", toolset="jackal_verified", schema=schemas.RANGE_BOUND, handler=wrap(tools.range_bound))
    ctx.register_tool(name="jackal_gaussian_integral", toolset="jackal_verified", schema=schemas.GAUSSIAN_INTEGRAL, handler=wrap(tools.gaussian_integral))
    ctx.register_tool(name="jackal_sqrt_rat_bound", toolset="jackal_verified", schema=schemas.SQRT_RAT_BOUND, handler=wrap(tools.sqrt_rat_bound))
    ctx.register_tool(name="jackal_exp_rat_bound", toolset="jackal_verified", schema=schemas.EXP_RAT_BOUND, handler=wrap(tools.exp_rat_bound))
    ctx.register_tool(name="jackal_claim_card", toolset="jackal_verified", schema=schemas.CLAIM_CARD, handler=wrap(tools.claim_card))
    ctx.register_tool(name="jackal_verify_receipt", toolset="jackal_verified", schema=schemas.VERIFY_RECEIPT, handler=tools.verify_receipt)

    skills_dir = Path(__file__).parent / "skills"
    for child in sorted(skills_dir.iterdir()):
        skill_md = child / "SKILL.md"
        if child.is_dir() and skill_md.is_file():
            ctx.register_skill(child.name, skill_md)

    # Plugin skills are explicitly loaded and namespaced by design. Keep the
    # minimal routing/non-inflation policy present in every fresh session so
    # users can ask naturally without knowing a skill or tool name.
    ctx.register_system_prompt_section(
        "jackal-verified.routing",
        _ROUTING_RULES,
        position="after_memory",
        max_chars=1800,
    )
