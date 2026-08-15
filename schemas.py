"""Schemas for JACKAL's narrow, assurance-aware tool surface."""


def _expr(description: str = "JACKAL expression") -> dict:
    return {"type": "string", "description": description, "minLength": 1, "maxLength": 8192}


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
    "description": "Integrate an expression with an explicit assurance tier: fast_estimate, adaptive_estimate, or bounded. Never silently downgrades bounded requests; certification failure remains a refusal.",
    "parameters": {
        "type": "object",
        "properties": {
            "expression": _expr("Integrand in x"),
            "lower": {"type": "number"},
            "upper": {"type": "number"},
            "assurance": {"type": "string", "enum": ["fast_estimate", "adaptive_estimate", "bounded"]},
            "tolerance": {"type": "number", "exclusiveMinimum": 0},
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

GAUSSIAN_INTEGRAL = {
    "name": "jackal_gaussian_integral",
    "description": "Formal-bounded release of a Gaussian integral of the form exp(a*(x-b)^2) via the zero-libm Gaussian checker. Emits a jackal-formal-receipt-v1(variant=gaussian) that jackal_verify_receipt re-executes against the pinned checker.",
    "parameters": {
        "type": "object",
        "properties": {
            "expression": _expr("Gaussian-family expression exp(a*(x-b)^2), a<0"),
            "lower": {"type": "number"},
            "upper": {"type": "number"},
            "tolerance": {"oneOf": [{"type": "number", "exclusiveMinimum": 0}, {"type": "string", "minLength": 1}]},
        },
        "required": ["expression", "lower", "upper", "tolerance"],
    },
}

SQRT_RAT_BOUND = {
    "name": "jackal_sqrt_rat_bound",
    "description": "Pure-Q formal-bounded enclosure of sqrt(x) on a canonical rational interval [lo, hi] via a Lean-proved checker. Admits ONLY the exact form 'sqrt(x)'; NO libm on the proof-decision path. Emits a jackal-formal-receipt-v1(variant=sqrt_rat).",
    "parameters": {
        "type": "object",
        "properties": {
            "expression": _expr("Must be exactly 'sqrt(x)'"),
            "lower": {"oneOf": [{"type": "number"}, {"type": "string", "minLength": 1}]},
            "upper": {"oneOf": [{"type": "number"}, {"type": "string", "minLength": 1}]},
        },
        "required": ["expression", "lower", "upper"],
    },
}

EXP_RAT_BOUND = {
    "name": "jackal_exp_rat_bound",
    "description": "Pure-Q formal-bounded enclosure of exp(x) on [lo, hi] with lo >= 0 via a Lean-proved rational Taylor + certified remainder in the checker. Admits ONLY the exact form 'exp(x)'; NO libm on the proof-decision path. Emits a jackal-formal-receipt-v1(variant=exp_rat).",
    "parameters": {
        "type": "object",
        "properties": {
            "expression": _expr("Must be exactly 'exp(x)'"),
            "lower": {"oneOf": [{"type": "number", "minimum": 0}, {"type": "string", "minLength": 1}]},
            "upper": {"oneOf": [{"type": "number", "minimum": 0}, {"type": "string", "minLength": 1}]},
        },
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
