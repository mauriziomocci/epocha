"""Heligman-Pollard mortality model with per-era calibration.

Source:
- Heligman, L. & Pollard, J.H. (1980). The age pattern of mortality.
  Journal of the Institute of Actuaries 107(1), 49-80.

The three HP components (infant mortality, young-adult accident hump,
senescence) are decomposed explicitly so the cause-of-death attribution
can sample from the dominant component at the age of death.
"""
from __future__ import annotations

import math
import random
from typing import Mapping

HP_PARAM_KEYS = tuple("ABCDEFGH")


def _unpack(params: Mapping[str, float]) -> tuple[float, ...]:
    return tuple(float(params[k]) for k in HP_PARAM_KEYS)


def _hp_components(age: float, params: Mapping[str, float]) -> tuple[float, float, float]:
    """Return (c1, c2, c3) corresponding to the three HP components at age x."""
    A, B, C, D, E, F, G, H = _unpack(params)
    x = max(float(age), 0.01)
    c1 = A ** ((x + B) ** C)
    c2 = D * math.exp(-E * (math.log(x) - math.log(F)) ** 2) if x > 0 else 0.0
    c3 = G * (H ** x)
    return c1, c2, c3


def annual_mortality_probability(age: float, params: Mapping[str, float]) -> float:
    """Return the annual probability of death at age x using HP (1980).

    Converts the HP hazard q/p to a probability via q = (q/p) / (1 + q/p).
    """
    c1, c2, c3 = _hp_components(age, params)
    q_over_p = c1 + c2 + c3
    q = q_over_p / (1.0 + q_over_p)
    return min(q, 0.999)


def tick_mortality_probability(
    age: float,
    params: Mapping[str, float],
    tick_duration_hours: float,
    demography_acceleration: float = 1.0,
) -> float:
    """Scale the annual mortality probability to a single tick.

    For small q (q < 0.1, typical for most ages), the linear
    approximation `annual_q * dt` is accurate to better than 0.5%.
    For large q (infant mortality pre-industrial q ~ 0.25), the exact
    geometric conversion `1 - (1 - annual_q) ** dt` is used to avoid
    underestimation.
    """
    annual_q = annual_mortality_probability(age, params)
    dt = (tick_duration_hours / 8760.0) * demography_acceleration
    if annual_q < 0.1:
        return annual_q * dt
    return 1.0 - (1.0 - annual_q) ** dt


def sample_death_cause(
    age: float,
    params: Mapping[str, float],
    rng: random.Random,
) -> str:
    """Attribute the cause of death to the dominant HP component at age x.

    The three HP components map to the analytic labels:
    - Component 1 (A^...): "early_life_mortality"
    - Component 2 (D-term accident hump): "external_cause"
    - Component 3 (Gompertz senescence): "natural_senescence"

    The labels are analytics conventions, not medical classifications.
    """
    c1, c2, c3 = _hp_components(age, params)
    total = c1 + c2 + c3
    if total <= 0.0:
        return "natural_senescence"
    r = rng.random() * total
    if r < c1:
        return "early_life_mortality"
    if r < c1 + c2:
        return "external_cause"
    return "natural_senescence"


def fit_heligman_pollard(
    ages: list[float],
    observed_q: list[float],
    initial_guess: Mapping[str, float] | None = None,
) -> dict[str, float]:
    """Fit the eight HP parameters to observed annual mortality probabilities.

    Uses scipy.optimize.curve_fit with the HP functional form. Returns
    a dict {A, B, C, D, E, F, G, H}. Raises RuntimeError if the fit
    does not converge.

    Calibration task (Plan 4) feeds this with q(x) columns from
    published life tables (Wrigley-Schofield 1981, HMD). Plan 1 only
    tests the algorithm against synthetic data.
    """
    import numpy as np
    from scipy.optimize import curve_fit

    def _hp_model(x, A, B, C, D, E, F, G, H):
        x_safe = np.maximum(x, 0.01)
        c1 = A ** ((x_safe + B) ** C)
        c2 = D * np.exp(-E * (np.log(x_safe) - np.log(F)) ** 2)
        c3 = G * (H ** x_safe)
        q_over_p = c1 + c2 + c3
        return q_over_p / (1.0 + q_over_p)

    if initial_guess is None:
        p0 = [0.005, 0.02, 0.1, 0.001, 10.0, 22.0, 0.00005, 1.1]
    else:
        p0 = [initial_guess[k] for k in HP_PARAM_KEYS]

    xs = np.asarray(ages, dtype=float)
    ys = np.asarray(observed_q, dtype=float)

    # Degenerate input guard: a mortality schedule that is uniformly zero
    # has no HP interpretation (every component would need to vanish), so
    # we reject it early rather than let curve_fit silently minimise to the
    # boundary of the parameter space, which would produce misleading output.
    if not np.any(ys > 0.0):
        raise RuntimeError(
            "Heligman-Pollard fit did not converge: observed_q contains no "
            "positive values; a zero-mortality schedule is incompatible with "
            "the HP model."
        )

    lower = [0.0, 0.0, 0.0, 0.0, 0.1, 1.0, 0.0, 1.0]
    upper = [0.1, 0.5, 1.0, 0.05, 50.0, 50.0, 0.001, 1.5]

    try:
        popt, _ = curve_fit(
            _hp_model, xs, ys, p0=p0, bounds=(lower, upper), maxfev=10_000,
        )
    except RuntimeError as exc:
        raise RuntimeError("Heligman-Pollard fit did not converge") from exc

    return dict(zip(HP_PARAM_KEYS, (float(v) for v in popt)))
