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
from collections.abc import Mapping

HP_PARAM_KEYS = tuple("ABCDEFGH")


class UnderdeterminedFitError(ValueError):
    """Fewer observed ages than Heligman-Pollard parameters reach the fit."""


# Upper bound on the annual mortality probability returned by
# annual_mortality_probability. The geometric tick scaling at
# tick_mortality_probability computes (1 - q_annual) ** dt, which requires
# (1 - q_annual) to stay strictly above zero to avoid math.log(0) issues
# further downstream (e.g. in life-expectancy computations). Capping at
# 0.999 preserves three significant digits of the upper tail while
# guaranteeing a non-zero survival probability. Tunable design parameter;
# raising it closer to 1.0 sharpens the upper tail but risks numerical
# instability in downstream consumers.
_MAX_ANNUAL_MORTALITY_PROBABILITY: float = 0.999


def _unpack(params: Mapping[str, float]) -> tuple[float, ...]:
    return tuple(float(params[k]) for k in HP_PARAM_KEYS)


def _hp_components(age: float, params: Mapping[str, float]) -> tuple[float, float, float]:
    """Return (c1, c2, c3), the three HP components at the completed age.

    HP `q_x` is the probability of dying between EXACT ages `x` and `x + 1`,
    the life-table quantity (Preston, Heuveline & Guillot 2001, Demography,
    ch. 3; page not verified), so it is read at the completed age
    `floor(age)` and held over the whole year of age. Evaluated at the
    continuous age instead, a newborn spent its first year on a curve that
    falls steeply within months and realized about a third of `q(0)`
    (gate decision D-29-20, demography Plan 4).

    At `x = 0` the accident-hump term contains `ln 0`; its limit as
    `x -> 0+` is zero, so it is zero there and `q_0` is the formula's own
    value, `A ** (B ** C) + G` in odds. The earlier guard `max(age, 0.01)`
    shifted the age of all three terms instead and, with the pre-industrial
    `B = 0.017`, moved the infancy intercept by 59%, from `q_0 = 0.0291` to
    `0.0247`.
    """
    A, B, C, D, E, F, G, H = _unpack(params)  # noqa: N806 -- Heligman-Pollard (1980) parameter notation
    x = max(math.floor(age), 0)
    c1 = A ** ((x + B) ** C)
    c2 = D * math.exp(-E * (math.log(x) - math.log(F)) ** 2) if x > 0 else 0.0
    c3 = G * (H**x)
    return c1, c2, c3


def annual_mortality_probability(age: float, params: Mapping[str, float]) -> float:
    """Return the annual probability of death at the completed age `floor(age)`
    using HP (1980); see `_hp_components` for the convention.

    Converts the HP hazard q/p to a probability via q = (q/p) / (1 + q/p).
    """
    c1, c2, c3 = _hp_components(age, params)
    q_over_p = c1 + c2 + c3
    q = q_over_p / (1.0 + q_over_p)
    return min(q, _MAX_ANNUAL_MORTALITY_PROBABILITY)


def tick_mortality_probability(
    age: float,
    params: Mapping[str, float],
    tick_duration_hours: float,
    demography_acceleration: float = 1.0,
) -> float:
    """Scale the annual mortality probability to a single tick.

    The exact geometric conversion `1 - (1 - annual_q) ** dt`, at every
    age: the probability of surviving `dt` years at a constant annual
    hazard is `(1 - q) ** dt`. With `q` read at the completed age, the
    hazard is constant within each year of age (the constant-force
    assumption of the life table), so the ticks of one year compound back
    to exactly `q_x`.

    A linear branch `annual_q * dt` used to apply below `q = 0.1`, declared
    "accurate to better than 0.5%". Its relative error against the geometric
    form is about `q / 2`, so the claim held only for `q` near 0.01: round 11
    of the demography Plan 4 phase-6 gate measured an underestimate of up to
    4.71% at 82 under the pre-industrial template and 4.96% under
    `industrial`, and a spurious jump of about 5% between 82 and 83, where
    `q` crossed 0.1 and the branch switched. Nothing is saved by the
    approximation: one power is evaluated per agent per tick either way.
    `annual_mortality_probability` caps `q` below 1, so `1 - q` stays
    strictly positive.

    The tick must fit inside a year of age: `orchestrator.years_per_tick`
    computes `dt` and raises `TickLongerThanAYearError` above one simulated
    year, where the compounding claim above stops holding.
    """
    from epocha.apps.demography.orchestrator import years_per_tick

    dt = years_per_tick(tick_duration_hours, demography_acceleration)
    annual_q = annual_mortality_probability(age, params)
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
    does not converge, and UnderdeterminedFitError when fewer than eight
    ages have `q > 0`, since the eight parameters would then be
    underdetermined.

    The template mortality recalibration, an open work item (demography
    Plan 4 closed without it), is meant to feed this with q(x) columns
    from published life tables (Wrigley-Schofield 1981, HMD). The shipped
    template values were never produced by this fit, and the tests only
    exercise the algorithm against synthetic data.

    The residuals are relative, `q_hat / q - 1`, the objective commonly
    attributed to Heligman and Pollard (1980), not verified against the
    paper: passing `sigma = q` to
    `curve_fit` weighs every age by its own magnitude. Unweighted absolute
    residuals let the old ages dominate and stop the optimizer once the
    young ages are small in absolute terms; round 15 of the Plan 4 phase-6
    gate measured a maximum relative error of 0.57 on `sci_fi`'s own
    schedule, whose `q` spans 4.3e-6 to 8.3e-3 over ages 0-99. An age observed at `q = 0` has
    no relative deviation and is left out of the fit.
    """
    import numpy as np
    from scipy.optimize import curve_fit

    def _hp_model(x, *values):
        # The very function the simulation evaluates, so a fitted parameter
        # set reproduces the fitted q(x) when the mortality step reads it.
        params = dict(zip(HP_PARAM_KEYS, values, strict=True))
        return np.array([annual_mortality_probability(age, params) for age in x])

    if initial_guess is None:
        p0 = [0.005, 0.02, 0.1, 0.001, 10.0, 22.0, 0.00005, 1.1]
    else:
        p0 = [initial_guess[k] for k in HP_PARAM_KEYS]

    xs = np.asarray(ages, dtype=float)
    ys = np.asarray(observed_q, dtype=float)

    lower = [0.0, 0.0, 0.0, 0.0, 0.1, 1.0, 0.0, 1.0]
    upper = [0.1, 0.5, 1.0, 0.05, 50.0, 50.0, 0.001, 1.5]

    # Each observed age is one equation and each parameter one unknown. With
    # bounds `curve_fit` runs the trust-region solver, which accepts more
    # unknowns than equations and returns one of infinitely many parameter
    # sets as if it were a fit (round 16 of the Plan 4 phase-6 gate). A
    # schedule of zeros is the extreme case, zero equations, and is refused
    # by the same guard.
    observed = ys > 0.0
    observed_ages = int(np.count_nonzero(observed))
    if observed_ages < len(HP_PARAM_KEYS):
        raise UnderdeterminedFitError(
            f"Heligman-Pollard fit needs at least {len(HP_PARAM_KEYS)} ages with q > 0, "
            f"got {observed_ages} ages; the fit would be underdetermined."
        )
    try:
        popt, _ = curve_fit(
            _hp_model,
            xs[observed],
            ys[observed],
            p0=p0,
            sigma=ys[observed],
            bounds=(lower, upper),
            maxfev=10_000,
        )
    except RuntimeError as exc:
        raise RuntimeError("Heligman-Pollard fit did not converge") from exc

    return dict(zip(HP_PARAM_KEYS, (float(v) for v in popt)))
