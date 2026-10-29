"""First-marriage schedule of a female cohort: the Coale-McNeil model.

Sources:
- Coale, A. J. (1971). Age patterns of marriage. Population Studies 25(2),
  193-214. The observation that first-marriage schedules share one shape up
  to a shift and a scale.
- Coale, A. J., McNeil, D. R. (1972). The distribution by age of the
  frequency of first marriage in a female cohort. Journal of the American
  Statistical Association 67(340), 743-749. Source of the closed three-
  parameter form; not opened, cited through Kaneko (2003).
- Rodriguez, G., Trussell, J. (1980). Maximum likelihood estimation of the
  parameters of Coale's model nuptiality schedule from survey data. World
  Fertility Survey Technical Bulletin 7. The standardized density (R1) and
  its constants; verified through Kaneko (2003, eq. 2), whose bibliography
  (p. 260) lists the bulletin. The bulletin itself was not read.
- Kaneko, R. (2003). Elaboration of the Coale-McNeil nuptiality model as the
  generalized log gamma distribution. Demographic Research 9(10), 223-262,
  doi:10.4054/DemRes.2003.9.10. Equations 1-4 read on pp. 223-228.

Assumptions of the model as used here:
- The schedule is read as the calendar of a cohort without mortality (the
  single-decrement reading of first-marriage calendars), and marriage and
  mortality are independent. The hazard of a never-married woman alive at
  age x is then f(x) / (1 - F(x)).
- The schedule is stationary inside an era: a cohort calendar is applied as
  a period hazard to the women present at each tick, and the two readings
  coincide only in a stationary regime. Changes of nuptiality inside a run
  (crises, wars) are not modelled.
"""

from __future__ import annotations

import functools
import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from scipy.integrate import quad
from scipy.optimize import brentq
from scipy.special import gammainc, gammaincc

# Standardized Coale-McNeil density (mean 0, variance 1), Rodriguez and
# Trussell (1980) as reported by Kaneko (2003, eq. 2). The values are
# rounded to three decimals in the source: with them the normalizing
# constant beta / Gamma(alpha / beta) is 1.28082, while the source prints
# 1.2813 (the difference is the rounding of alpha and beta, checked
# numerically in the spec).
STANDARD_ALPHA = 1.145
STANDARD_BETA = 1.896
STANDARD_MU = -0.805

# Shape alpha / beta of the incomplete gamma form of the standardized
# schedule, and the normalizing constant K = beta / Gamma(alpha / beta) of
# (R1). Both depend only on the constants above, so they are computed once.
_ALPHA_OVER_BETA = STANDARD_ALPHA / STANDARD_BETA
_DENSITY_CONSTANT = STANDARD_BETA / math.gamma(_ALPHA_OVER_BETA)

# math.exp overflows a double above about 709.78. The density and the CDF
# have underflowed to 0.0 (and 1.0 for the lower incomplete gamma) long
# before, so beyond this exponent the function returns the limit instead of
# raising OverflowError.
_EXP_OVERFLOW_GUARD = 700.0

# Upper end of the observation window over which a historical mean age at
# first marriage is read, in years (upper bound of R5, same as SC-002). It is
# a modelling choice fixed by the spec, tunable heuristic, not verified against
# the observation window of any one source: Wrigley et al. (1997) is cited for
# the mean values, not for this ceiling.
OBSERVATION_CEILING_AGE = 50.0

# The location is searched on [min_age - LOCATION_BRACKET_SD * scale,
# OBSERVATION_CEILING_AGE]. Ten standard deviations below the minimum age is
# where the schedule has no mass in the window; the truncated mean at that
# end is the lowest value any location can give. Tunable bracket width,
# wide enough for every era of the spec (checked, spec section "Dal valore
# storico a u").
LOCATION_BRACKET_SD = 10.0

# Absolute tolerance of the root finder on the location, in years: far below
# the precision of any historical mean age (Brent 1973; scipy.optimize.brentq
# xtol). Tunable numerical tolerance.
LOCATION_XTOL_YEARS = 1e-6


def standard_density(z: float) -> float:
    """Standardized first-marriage density g_s(z) (R1).

    g_s(z) = beta / Gamma(alpha / beta)
             * exp[-alpha (z - mu) - exp(-beta (z - mu))]
           = K * y ** (alpha / beta) * exp(-y),   y = exp(-beta (z - mu))

    The second form is the same function, since exp(-alpha (z - mu)) =
    y ** (alpha / beta); it shares the argument y, and its overflow guard,
    with the closed-form CDF.

    Rodriguez and Trussell (1980); Kaneko (2003, eq. 2). Verified
    numerically: it integrates to 1, with mean 0 and variance 1.0008
    (the excess over 1 comes from the three-decimal rounding of alpha and
    beta in the source).

    Returns 0.0 where exp(-beta (z - mu)) would overflow, that is far left
    of the support, where the true density is below the smallest double.
    """
    y = _incomplete_gamma_argument(z)
    if y is None:
        return 0.0
    return _DENSITY_CONSTANT * y**_ALPHA_OVER_BETA * math.exp(-y)


def _incomplete_gamma_argument(z: float) -> float | None:
    """Return y = exp(-beta (z - mu)), or None where it would overflow."""
    t = -STANDARD_BETA * (z - STANDARD_MU)
    if t > _EXP_OVERFLOW_GUARD:
        return None
    return math.exp(t)


def standard_cdf(z: float) -> float:
    """Standardized first-marriage CDF G_s(z) (R1a), in closed form.

    G_s(z) = Q(alpha / beta, exp(-beta (z - mu)))

    with Q the regularized upper incomplete gamma function
    (scipy.special.gammaincc). Derivation (an original step, checked
    numerically against the integral of (R1) in the tests): in the integral
    of g_s(t) from -inf to z substitute y = exp(-beta (t - mu)). Then
    exp(-alpha (t - mu)) = y ** (alpha / beta) and dt = -dy / (beta y), so
    g_s(t) dt = -y ** (alpha / beta - 1) exp(-y) dy / Gamma(alpha / beta),
    and t from -inf to z is y from +inf down to exp(-beta (z - mu)). The
    integral is therefore Gamma(alpha / beta, y) / Gamma(alpha / beta) = Q.

    Returns 0.0 where y would overflow (far left of the support).
    """
    y = _incomplete_gamma_argument(z)
    if y is None:
        return 0.0
    return float(gammaincc(_ALPHA_OVER_BETA, y))


def _standard_lower(z: float) -> float:
    """Complement 1 - G_s(z) as the regularized LOWER incomplete gamma P.

    P(alpha / beta, y) equals 1 - Q(alpha / beta, y) but is computed
    directly, so a survival term built from it does not cancel when G_s(z)
    is close to 1 (first-marriage hazard (R3)). Returns 1.0 where y would
    overflow.
    """
    y = _incomplete_gamma_argument(z)
    if y is None:
        return 1.0
    return float(gammainc(_ALPHA_OVER_BETA, y))


@dataclass(frozen=True)
class FirstMarriageSchedule:
    """First-marriage schedule of one era (R2), Kaneko (2003, eq. 3-4).

    The standardized shape g_s is moved to the era by a location u and a
    scale b, and weighted by the share C of women who ever marry:

        f(x) = C * g_s((x - u) / b) / b        F(x) = C * G_s((x - u) / b)

    Attributes:
        location: u, the mean of the UNTRUNCATED distribution, in years. It is
            not the historical mean age at marriage, which is observed on
            marriages between the minimum age and the end of observation;
            location_from_observed_mean derives u from that value (R5).
        scale: b, the standard deviation of the untruncated distribution, in
            years.
        proportion: C, the share of women who ever marry, in (0, 1].
        min_age: m, the era minimum marriage age for women, in years.
    """

    location: float
    scale: float
    proportion: float
    min_age: float

    def density(self, x: float) -> float:
        """Frequency of first marriage at age x, f(x) of (R2)."""
        return self.proportion * standard_density((x - self.location) / self.scale) / self.scale

    def cdf(self, x: float) -> float:
        """Cumulative share married by age x, F(x) of (R2)."""
        return self.proportion * standard_cdf((x - self.location) / self.scale)

    def hazard(self, x: float) -> float:
        """Hazard of first marriage at age x for a never-married woman (R3).

        h(x) = f(x) / (1 - F(x)), the single-decrement hazard. The survival
        1 - F(x) is computed as (1 - C) + C * P(alpha / beta, y), with P the
        lower incomplete gamma, so it does not cancel to zero by
        subtraction when F(x) is close to 1. Returns 0.0 where the survival
        is not positive (FR-002), instead of dividing by zero.
        """
        z = (x - self.location) / self.scale
        survival = (1.0 - self.proportion) + self.proportion * _standard_lower(z)
        if survival <= 0.0:
            return 0.0
        return self.density(x) / survival

    def conditional_cdf(self, x: float) -> float:
        """Share of women married by age x among those who reach min_age single (R4).

        F*(x) = (F(x) - F(m)) / (1 - F(m)) for x >= m, and 0.0 below m. A woman
        reaches the minimum age m unmarried, so the mass F(m) that (R2) puts
        under m is never realized; the per-tick rule of tick_probability
        realizes exactly this conditioned calendar, because the hazard (R3)
        is unchanged by conditioning on being single at m. 1 - F(m) is
        strictly positive for every template the loader accepts (the loader
        requires a solvable (R5)), so no guard is needed.
        """
        if x < self.min_age:
            return 0.0
        mass_below_minimum = self.cdf(self.min_age)
        return (self.cdf(x) - mass_below_minimum) / (1.0 - mass_below_minimum)

    def tick_probability(self, x: float, years_per_tick: float) -> float:
        """Probability of a first marriage during one tick at age x (FR-002).

        p = 1 - exp(-h(x) * dt) with dt the tick length in years, the exact
        probability of at least one event of a constant-hazard process over
        the tick. 0.0 below the era minimum age.
        """
        if x < self.min_age:
            return 0.0
        return 1.0 - math.exp(-self.hazard(x) * years_per_tick)


def truncated_mean(
    location: float,
    scale: float,
    min_age: float,
    upper: float = OBSERVATION_CEILING_AGE,
) -> float:
    """Mean age at first marriage OBSERVED on [min_age, upper] (left side of R5).

    E[X | m <= X <= upper] = integral_m^upper x g_s((x - u)/b)/b dx
                             / [G_s((upper - u)/b) - G_s((m - u)/b)]

    The proportion C cancels in the ratio, so the result depends only on the
    location u, the scale b and the window. A historical mean age is an
    average over observed marriages, hence over this window, while u is the
    mean of the untruncated distribution; the two differ (u = 25.5 gives
    25.42 on [14, 50]). The numerator is integrated by scipy.integrate.quad,
    the denominator uses the closed-form CDF (R1a).
    """
    numerator, _ = quad(
        lambda x: x * standard_density((x - location) / scale) / scale, min_age, upper
    )
    denominator = standard_cdf((upper - location) / scale) - standard_cdf(
        (min_age - location) / scale
    )
    return numerator / denominator


def location_from_observed_mean(observed_mean: float, scale: float, min_age: float) -> float:
    """Solve (R5) for the location u that reproduces an observed mean age.

    Finds u such that truncated_mean(u, scale, min_age) equals observed_mean,
    by Brent's method (scipy.optimize.brentq) on
    [min_age - LOCATION_BRACKET_SD * scale, OBSERVATION_CEILING_AGE]. The
    truncated mean grows with u but does not cover every value.

    Raises:
        ValueError: when the truncated mean does not bracket observed_mean,
            with the reachable interval in the message; no location is
            invented in that case.
    """
    lower = min_age - LOCATION_BRACKET_SD * scale
    upper = OBSERVATION_CEILING_AGE
    try:
        return brentq(
            lambda u: truncated_mean(u, scale, min_age) - observed_mean,
            lower,
            upper,
            xtol=LOCATION_XTOL_YEARS,
        )
    except ValueError as error:
        reachable_low = truncated_mean(lower, scale, min_age)
        reachable_high = truncated_mean(upper, scale, min_age)
        raise ValueError(
            f"mean age {observed_mean} cannot be reproduced by the schedule: "
            f"the reachable interval for scale {scale} and minimum age {min_age} "
            f"is [{reachable_low:.2f}, {reachable_high:.2f}]"
        ) from error


@functools.lru_cache(maxsize=32)
def _schedule_for(
    mean_age: float, sd_age: float, proportion: float, min_age: float
) -> FirstMarriageSchedule:
    """Build the schedule of an era from its historical parameters (cached).

    mean_age is the OBSERVED mean age at first marriage (a template value),
    from which the location u is solved by (R5). The solve costs a root
    finder over numerical integrals, so the result is memoized per distinct
    parameter tuple: the template loader calls first_marriage_schedule (the public entry
    point) to validate a template, and the marriage market calls it again at
    run time as a cache hit. The
    32 entries are far above the number of eras (five at the time of writing).
    """
    location = location_from_observed_mean(mean_age, sd_age, min_age)
    return FirstMarriageSchedule(location, sd_age, proportion, min_age)


def first_marriage_schedule(couple_cfg: Mapping[str, Any]) -> FirstMarriageSchedule:
    """Return the cached schedule described by a template's `couple` section.

    Reads couple_cfg["first_marriage"]["mean_age_female"], ["sd_age_female"],
    ["proportion_ever_married_female"] and couple_cfg["min_marriage_age_female"].
    The dict is shared by the template loader cache across callers: it is
    only read here, and the derived location is never written back into it.
    """
    first_marriage = couple_cfg["first_marriage"]
    return _schedule_for(
        float(first_marriage["mean_age_female"]),
        float(first_marriage["sd_age_female"]),
        float(first_marriage["proportion_ever_married_female"]),
        float(couple_cfg["min_marriage_age_female"]),
    )
