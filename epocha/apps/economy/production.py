"""CES production function and per-agent output computation.

The Constant Elasticity of Substitution (CES) production function
generalizes Cobb-Douglas (sigma=1) and Leontief (sigma->0):

    Q = A * [sum_i(alpha_i * X_i^rho)]^(1/rho)

    where rho = (sigma - 1) / sigma

Source: Arrow, K., Chenery, H., Minhas, B., & Solow, R. (1961).
"Capital-labor substitution and economic efficiency." Review of
Economics and Statistics. Extended to 3+ factors per Shoven & Whalley
(1992), chapter 3.

Factor weights are normalized to sum to 1 internally. This ensures
the weights control only the relative importance of factors, while
the scale parameter A controls the absolute output level. Standard
practice in applied CGE (Shoven & Whalley 1992).
"""
from __future__ import annotations

import logging
import math

logger = logging.getLogger(__name__)

# Sigma threshold below which we use the Leontief approximation
# to avoid numerical instability (rho approaches negative infinity).
_LEONTIEF_THRESHOLD = 0.05

# Sigma threshold above which we use the Cobb-Douglas log-form
# to avoid numerical issues (rho approaches zero).
_COBB_DOUGLAS_THRESHOLD = 0.95
_COBB_DOUGLAS_UPPER = 1.05


def ces_production(
    *,
    scale: float,
    sigma: float,
    factor_weights: dict[str, float],
    factor_inputs: dict[str, float],
) -> float:
    """Compute CES production output.

    Args:
        scale: Total factor productivity (A). Multiplies final output.
        sigma: Elasticity of substitution. Controls factor substitutability:
            sigma < 1: complements (hard to substitute, pre-industrial)
            sigma = 1: Cobb-Douglas (unit elasticity)
            sigma > 1: substitutes (easy to substitute, modern)
            Tunable per era via template. Antras (2004) estimates sigma < 1
            for historical economies; Karabarbounis & Neiman (2014) estimate
            sigma > 1 for modern economies.
        factor_weights: {factor_code: weight}. Normalized internally to
            sum to 1. Controls relative importance of each factor.
        factor_inputs: {factor_code: quantity}. Actual input amounts.
            Missing factors default to 0.

    Returns:
        Production output Q >= 0.
    """
    if not factor_weights or not factor_inputs:
        return 0.0

    # Normalize weights to sum to 1
    weight_sum = sum(factor_weights.values())
    if weight_sum <= 0:
        return 0.0
    weights = {k: v / weight_sum for k, v in factor_weights.items()}

    # Collect (weight, input) pairs for factors that have positive weight
    pairs = []
    for factor, alpha in weights.items():
        x = factor_inputs.get(factor, 0.0)
        if alpha > 0:
            pairs.append((alpha, max(0.0, x)))

    if not pairs:
        return 0.0

    # Check if all inputs are zero
    if all(x == 0.0 for _, x in pairs):
        return 0.0

    # Leontief limit (sigma -> 0): Q = A * min(alpha_i * X_i)
    # As sigma approaches 0, the CES function converges to a fixed-proportions
    # technology where the bottleneck factor determines output.
    if sigma < _LEONTIEF_THRESHOLD:
        min_val = min(alpha * x if x > 0 else 0.0 for alpha, x in pairs)
        return scale * min_val

    # Cobb-Douglas limit (sigma -> 1): Q = A * prod(X_i^alpha_i)
    # Using log-form for numerical stability near the singularity at rho=0.
    if _COBB_DOUGLAS_THRESHOLD < sigma < _COBB_DOUGLAS_UPPER:
        log_q = 0.0
        for alpha, x in pairs:
            if x <= 0:
                return 0.0  # CD with zero input = zero output
            log_q += alpha * math.log(x)
        return scale * math.exp(log_q)

    # General CES: Q = A * [sum(alpha_i * X_i^rho)]^(1/rho)
    rho = (sigma - 1.0) / sigma

    inner_sum = 0.0
    for alpha, x in pairs:
        if x <= 0:
            if rho < 0:
                # With rho < 0, X^rho -> infinity as X -> 0
                # This means zero input makes the sum blow up
                # and the output approaches zero (complementarity)
                return 0.0
            # With rho > 0, X^rho -> 0, so zero input contributes nothing
            continue
        inner_sum += alpha * (x ** rho)

    if inner_sum <= 0:
        return 0.0

    return scale * (inner_sum ** (1.0 / rho))


def compute_agent_output(
    *,
    agent_role: str,
    zone_economy,
    properties_in_zone: list,
    role_production: dict,
    zone_type_resources: dict,
    zone_type: str,
    default_sigma: float,
) -> tuple[str, float]:
    """Compute what and how much an agent produces in one tick.

    Args:
        agent_role: The agent's role (e.g. "farmer", "merchant").
        zone_economy: The ZoneEconomy instance for the agent's zone.
        properties_in_zone: List of Property instances in the zone.
        role_production: Template config mapping roles to goods + skill weights.
        zone_type_resources: Template config mapping zone types to factor abundances.
        zone_type: The zone's type (urban, rural, etc.).
        default_sigma: CES sigma from the template.

    Returns:
        Tuple of (good_code, quantity_produced). If the agent's role
        is not mapped, produces the zone's dominant good.
    """
    # Determine what good this agent produces
    role_config = role_production.get(agent_role.lower())
    if role_config:
        good_code = role_config["good"]
        skill_weight = role_config.get("skill_weight", 1.0)
    else:
        # Fallback: produce the zone's dominant good (highest scale factor)
        prod_config = zone_economy.production_config
        if prod_config:
            good_code = max(prod_config, key=lambda g: prod_config[g].get("scale", 0))
        else:
            return ("subsistence", 0.0)
        # Unmapped roles are less efficient -- tunable design parameter
        skill_weight = 0.8

    # Get production config for this good in this zone
    good_prod = zone_economy.production_config.get(good_code, {})
    scale = good_prod.get("scale", 1.0)
    sigma = good_prod.get("sigma", default_sigma)
    factor_weights = good_prod.get("factors", {})

    # If no factor weights specified, use defaults from zone type
    if not factor_weights:
        factor_weights = zone_type_resources.get(zone_type, {"labor": 1.0})

    # Build factor inputs from zone resources and property capital.
    # Each factor's input comes from the zone's natural_resources (base
    # endowment), augmented by the zone_type_resources template defaults
    # when not specified. Property bonuses add to the capital factor.
    zone_resources = zone_economy.natural_resources
    zone_res = zone_type_resources.get(zone_type, {})

    # Capital: zone base + sum of production bonuses from properties
    # The zone provides a baseline capital level; properties augment it.
    capital_base = zone_resources.get("capital", zone_res.get("capital", 0.5))
    capital_from_properties = sum(
        p.production_bonus.get(good_code, 0.0)
        for p in properties_in_zone
    )

    factor_inputs = {
        "labor": skill_weight,
        "capital": capital_base + capital_from_properties,
        "natural_resources": zone_resources.get(
            "natural_resources", zone_res.get("natural_resources", 0.5)
        ),
        "knowledge": zone_resources.get(
            "knowledge", zone_res.get("knowledge", 0.5)
        ),
    }

    output = ces_production(
        scale=scale,
        sigma=sigma,
        factor_weights=factor_weights,
        factor_inputs=factor_inputs,
    )

    return (good_code, output)
