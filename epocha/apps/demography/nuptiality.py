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

import math

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

# math.exp overflows a double above about 709.78. The density and the CDF
# have underflowed to 0.0 (and 1.0 for the lower incomplete gamma) long
# before, so beyond this exponent the function returns the limit instead of
# raising OverflowError.
_EXP_OVERFLOW_GUARD = 700.0


def standard_density(z: float) -> float:
    """Standardized first-marriage density g_s(z) (R1).

    g_s(z) = beta / Gamma(alpha / beta)
             * exp[-alpha (z - mu) - exp(-beta (z - mu))]

    Rodriguez and Trussell (1980); Kaneko (2003, eq. 2). Verified
    numerically: it integrates to 1, with mean 0 and variance 1.0008
    (the excess over 1 comes from the three-decimal rounding of alpha and
    beta in the source).

    Returns 0.0 where exp(-beta (z - mu)) would overflow, that is far left
    of the support, where the true density is below the smallest double.
    """
    t = -STANDARD_BETA * (z - STANDARD_MU)
    if t > _EXP_OVERFLOW_GUARD:
        return 0.0
    constant = STANDARD_BETA / math.gamma(STANDARD_ALPHA / STANDARD_BETA)
    return constant * math.exp(-STANDARD_ALPHA * (z - STANDARD_MU) - math.exp(t))


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
    return float(gammaincc(STANDARD_ALPHA / STANDARD_BETA, y))


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
    return float(gammainc(STANDARD_ALPHA / STANDARD_BETA, y))
