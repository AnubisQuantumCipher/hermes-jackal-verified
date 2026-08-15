"""Schemas for JACKAL's narrow, assurance-aware tool surface."""


def _expr(description: str = "JACKAL expression") -> dict:
    return {"type": "string", "description": description, "minLength": 1, "maxLength": 8192}


def _rational_number(description: str) -> dict:
    return {"oneOf": [
        {"type": "number"},
        {"type": "string", "minLength": 1, "maxLength": 256},
    ], "description": description}


EXACT = {
    "name": "jackal_exact",
    "description": "Use JACKAL exact arithmetic for rational expressions or bounded big-integer operations. Prefer this over mental arithmetic when an exact result matters. Returns an instrument-bound receipt; never treats the decimal approximation as exact.",
    "parameters": {
        "type": "object",
        "properties": {
            "mode": {"type": "string", "enum": ["rational", "big_add", "big_multiply", "big_power", "factorial", "binomial"]},
            "expression": _expr("Exact rational expression; required only for rational mode."),
            "a": {"type": "string", "description": "First nonnegative integer operand."},
            "b": {"type": "string", "description": "Second nonnegative integer operand or exponent."},
            "n": {"type": "integer", "minimum": 0, "maximum": 10000},
            "r": {"type": "integer", "minimum": 0, "maximum": 10000},
        },
        "required": ["mode"],
    },
}

EVALUATE = {
    "name": "jackal_evaluate",
    "description": "Evaluate one finite real expression deterministically with JACKAL. This is IEEE-f64 evaluation, not exact or certified arithmetic; use jackal_exact or a bounded tool when stronger assurance is required.",
    "parameters": {"type": "object", "properties": {"expression": _expr()}, "required": ["expression"]},
}

DIFFERENTIATE = {
    "name": "jackal_differentiate",
    "description": "Differentiate an expression symbolically and release it only after JACKAL's numeric sample check. The result is checked, not a formal proof of identity; preserve domain caveats and non-claims.",
    "parameters": {"type": "object", "properties": {"expression": _expr("Expression in x")}, "required": ["expression"]},
}

INTEGRATE = {
    "name": "jackal_integrate",
    "description": "Integrate with an explicit assurance tier. formal-bounded is a zero-libm theorem-backed lane for the admitted canonical Gaussian family; unsupported formal requests refuse without fallback. bounded remains the conditional outward-rounded-f64/libm lane.",
    "parameters": {
        "type": "object",
        "properties": {
            "expression": _expr("Integrand in x"),
            "lower": _rational_number("Lower endpoint; exact rational strings are accepted for formal-bounded."),
            "upper": _rational_number("Upper endpoint; exact rational strings are accepted for formal-bounded."),
            "assurance": {"type": "string", "enum": ["fast_estimate", "adaptive_estimate", "bounded", "formal-bounded"]},
            "tolerance": _rational_number("Positive tolerance; required by adaptive_estimate, bounded, and formal-bounded."),
            "panels": {"type": "integer", "minimum": 2, "maximum": 1000000},
        },
        "required": ["expression", "lower", "upper", "assurance"],
    },
}

RANGE_BOUND = {
    "name": "jackal_range_bound",
    "description": "Compute a certified superset of an expression's range over an interval, or refuse. Use for threshold, denominator-zero, sensitivity, and possible-output questions.",
    "parameters": {
        "type": "object",
        "properties": {"expression": _expr("Expression in x"), "lower": {"type": "number"}, "upper": {"type": "number"}},
        "required": ["expression", "lower", "upper"],
    },
}

CLAIM_CARD = {
    "name": "jackal_claim_card",
    "description": "Produce a deterministic model-based JACKAL claim card with assumptions, non-claims, canonical preimage, sensitivity, and an independently recomputed SHA-256 fingerprint.",
    "parameters": {
        "type": "object",
        "properties": {
            "model": {"type": "string", "enum": ["projectile"]},
            "speed": {"type": "number", "exclusiveMinimum": 0},
            "angle_degrees": {"type": "number"},
            "gravity": {"type": "number", "exclusiveMinimum": 0},
        },
        "required": ["model", "speed", "angle_degrees", "gravity"],
    },
}

VERIFY_RECEIPT = {
    "name": "jackal_verify_receipt",
    "description": "Fail-closed validation of a receipt previously returned by a JACKAL plugin tool: schema, digest, executable identity, epistemic consistency, interval ordering, tolerance, and claim-card fingerprint.",
    "parameters": {
        "type": "object",
        "properties": {"receipt": {"type": "object", "description": "Receipt object returned by a JACKAL plugin tool."}},
        "required": ["receipt"],
    },
}
