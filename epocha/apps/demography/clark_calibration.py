"""Calibration of the innovation amplitude for the Clark class rule.

MODEL. Clark, G. (2014), *The Son Also Rises: Surnames and the History of
Social Mobility*, Princeton University Press, ISBN 9780691162546, and the
formal statement in Clark, Cummins, Hao & Diaz Vidal, *Surnames: a New Source
for the History of Social Mobility*, Explorations in Economic History 2014,
equations (3) and (4):

    y_t = x_t + u_t          observed status = latent status + observation error
    x_t = b*x_{t-1} + e_t    the latent process is an AR(1) WITH an innovation

with the same source giving the stationary identity `sigma^2 = b^2*sigma^2 +
sigma_e^2`. The rule as it shipped implemented only the contraction, with no
innovation at all, and that is not a simplification of Clark's model but a
model with the OPPOSITE asymptotic behaviour: without `e_t` every lineage
walks monotonically to the mean and the cross-sectional variance vanishes --
no mobility AND no stratification -- while Clark's model holds the variance
constant and reshuffles continuously. His low mobility is slow regression,
not freezing. Measured on the shipped rule: intergenerational mobility
exactly 0.0000 and a parent-child rank correlation of exactly 1.0000 from the
second generation, on a partition with two of the five ranks empty.

WHAT IS AND IS NOT ATTRIBUTED TO CLARK. The FORM of the constraint is his:
an AR(1) with an innovation, and the variance identity that ties the
innovation to the stationary dispersion. The persistence VALUE is not. His
universal constant of 0.75 -- "there is a universal constant of
intergenerational correlation of 0.75, from which deviations are rare and
predictable", with surname estimates between 0.7 and 0.9 -- applies to a
LATENT status that this model does not possess: here the class ladder IS the
state variable, not a noisy observation of something underlying it, so his
own attenuation factor `theta = sigma_x^2/(sigma_x^2 + sigma_u^2)` cannot be
computed and cannot be applied. `CLARK_PERSISTENCE = 0.7` is therefore a
declared, tunable design heuristic, and its numerical closeness to 0.75 is
meaningless and must not be read as corroboration. The direction of the
residual error is known and declared: on Clark's own arithmetic a single
observable indicator should persist LESS than this model persists.

WHY THE AMPLITUDE IS SOLVED AND NOT READ. The identity fixes the innovation
on a continuous scale, but the rule rounds to integer class labels and clamps
at both ends of the ladder, and neither operation is linear. Reading
`s_rank * sqrt(1 - b^2)` straight out of the identity lands at 102.26% of the
target dispersion. The amplitude is therefore DERIVED from the identity and
then SOLVED numerically against the realized post-rounding distribution.

WELL-POSEDNESS, which is part of the specification and not of the
implementation. The transition matrix depends on the zone class mean, which
is computed from the very distribution being solved for, so this is a
mean-field fixed point rather than a linear stationary-vector problem, and it
admits MULTIPLE solutions: at a small amplitude a population concentrated on
one rank stays there forever, and that is a genuine fixed point too. The
initial vector is therefore fixed by specification at uniform over the
ladder. And the map from amplitude to realized dispersion is NOT monotone: it
starts at 0.894 as the amplitude tends to zero, collapses to order 1e-4
around 0.075 -- ranks 1 and 3 leak into 2 far faster than 2 leaks back out --
and only then rises monotonically to 1.395 at sqrt(2). A bisection is
therefore bracketed above the dip, and targets outside the interval in which
the root is unique are refused rather than answered.
"""

from __future__ import annotations

import math
from functools import lru_cache

from scipy.special import ndtr

# Persistence of the Clark rule: a declared design heuristic, NOT Clark's 0.75.
# See the module docstring for why the two must not be conflated.
CLARK_PERSISTENCE = 0.7

# The class ladder. Input admits `enslaved` at rank 5 -- `_resolve_parent_rank`
# can return it -- while the output of `_rank_to_class_label` is capped at 4,
# so an agent may ENTER the chain at 5 and can never land there.
MAX_INPUT_RANK = 5
MAX_OUTPUT_RANK = 4
_OUTPUT_RANKS = tuple(range(MAX_OUTPUT_RANK + 1))

# Interval in which the amplitude-to-dispersion map is monotone and the root
# unique. Below the lower bound the map has already passed its collapse and
# two amplitudes give the same dispersion; above the upper bound no amplitude
# reaches the target at all.
S_RANK_MIN = 0.95
S_RANK_MAX = 1.39

# Bisection bracket, above the collapse. Its lower endpoint is where the map
# bottoms out; below it the sign does not change and the search is undefined.
_SIGMA_MIN = 0.075
_SIGMA_MAX = math.sqrt(2.0)
_BISECTION_TOL = 1e-12
_MAX_BISECTIONS = 200

# The inner mean-field fixed point has its OWN budget, deliberately distinct
# from the bisection's and from the one the truncated-normal grid uses: it
# counts fixed-point iterations on a five-state chain near a collapse point,
# where convergence is slowest, and needs far more of them.
#
# The cap is sized for the BRACKET and not for the whole domain, which is a
# deliberate limit rather than an oversight. Measured from the uniform start:
# 19 iterations at the top of the bracket, 40 at the operating amplitude that
# solves the declared target, 1,529 at 0.10, and 9,763 at the bracket's lower
# endpoint. Below it the picture changes qualitatively -- 1,409,260 at 0.05,
# and at 0.03 it does not settle within three million, because the innovation
# is too weak to move mass across a half-unit rounding cell and the
# distribution creeps indefinitely. Raising the cap would not buy an answer
# worth having down there: no admitted target has a root below the bracket,
# so refusing is the correct outcome and an unconverged dispersion returned
# as if settled would silently mis-calibrate every era using this rule.
_FIXED_POINT_TOL = 1e-15
_MAX_FIXED_POINT_ITERATIONS = 10_000


class ClarkCalibrationError(RuntimeError):
    """The calibration cannot answer: no unique root, or no convergence."""


def _transition_row(input_rank: float, zone_mean: float, sigma: float) -> list[float]:
    """Probabilities of each output rank for one input rank.

    The rule computes `b*parent + (1-b)*zone_mean + N(0, sigma)`, rounds to the
    nearest label and clamps to `[0, MAX_OUTPUT_RANK]`. Rounding makes label
    `k` the interval `(k - 0.5, k + 0.5)`; clamping makes the two end labels
    absorb their whole tails, which is why they are not symmetric cells.
    """
    centre = CLARK_PERSISTENCE * input_rank + (1.0 - CLARK_PERSISTENCE) * zone_mean
    if sigma <= 0.0:
        landed = min(MAX_OUTPUT_RANK, max(0, round(centre)))
        return [1.0 if k == landed else 0.0 for k in _OUTPUT_RANKS]

    row = []
    for k in _OUTPUT_RANKS:
        if k == 0:
            row.append(float(ndtr((0.5 - centre) / sigma)))
        elif k == MAX_OUTPUT_RANK:
            row.append(float(1.0 - ndtr((k - 0.5 - centre) / sigma)))
        else:
            upper = float(ndtr((k + 0.5 - centre) / sigma))
            lower = float(ndtr((k - 0.5 - centre) / sigma))
            row.append(upper - lower)
    return row


def _dispersion(distribution: list[float]) -> float:
    mean = sum(p * k for k, p in enumerate(distribution))
    variance = sum(p * (k - mean) ** 2 for k, p in enumerate(distribution))
    return math.sqrt(max(variance, 0.0))


def _step(distribution: list[float], sigma: float) -> list[float]:
    """One generation. `distribution` may span the input ranks `0..5`."""
    zone_mean = sum(p * k for k, p in enumerate(distribution))
    nxt = [0.0] * len(_OUTPUT_RANKS)
    for input_rank, weight in enumerate(distribution):
        if weight == 0.0:
            continue
        for k, probability in enumerate(_transition_row(input_rank, zone_mean, sigma)):
            nxt[k] += weight * probability
    total = sum(nxt)
    return [p / total for p in nxt] if total > 0 else nxt


def _uniform_start() -> list[float]:
    """The founding population the specification fixes: uniform on the ladder.

    Its own dispersion is sqrt(2), which is the reference every percentage in
    the amendment is quoted against.
    """
    return [1.0 / len(_OUTPUT_RANKS)] * len(_OUTPUT_RANKS)


def stationary_rank_distribution(sigma: float, initial: list[float] | None = None) -> list[float]:
    """Mean-field fixed point of the class chain at innovation `sigma`.

    Args:
        sigma: standard deviation of the innovation added before rounding.
        initial: starting distribution. Defaults to the uniform founding
            population the specification fixes. It is an ARGUMENT and not a
            constant because the fixed point is genuinely not unique -- a
            concentrated start is also a fixed point at small amplitudes --
            and a caller exploring that must be able to say so explicitly.
            May span the input ranks `0..5`; the result always spans `0..4`.

    Raises:
        ClarkCalibrationError: the iteration did not settle within its budget.
    """
    distribution = list(initial) if initial is not None else _uniform_start()
    if len(distribution) > MAX_INPUT_RANK + 1:
        raise ClarkCalibrationError(
            f"initial distribution spans {len(distribution)} ranks; the ladder "
            f"admits at most {MAX_INPUT_RANK + 1} on input"
        )
    total = sum(distribution)
    if total <= 0:
        raise ClarkCalibrationError("initial distribution carries no mass")
    distribution = [p / total for p in distribution]

    previous = _dispersion(distribution)
    for _ in range(_MAX_FIXED_POINT_ITERATIONS):
        distribution = _step(distribution, sigma)
        current = _dispersion(distribution)
        if abs(current - previous) < _FIXED_POINT_TOL:
            return distribution
        previous = current
    raise ClarkCalibrationError(
        f"class-rank fixed point did not settle in {_MAX_FIXED_POINT_ITERATIONS} "
        f"iterations at innovation {sigma}"
    )


def realized_rank_dispersion(sigma: float, initial: list[float] | None = None) -> float:
    """Stationary dispersion of the class ladder at innovation `sigma`."""
    return _dispersion(stationary_rank_distribution(sigma, initial=initial))


def realized_mobility(sigma: float) -> float:
    """Fraction of children whose rank differs from their parent's, at steady state.

    A sanity check, never the acceptance criterion: any positive innovation
    makes it positive, including one orders of magnitude below what the
    identity requires, so it cannot separate a calibrated amplitude from a
    token one. SC-012a is the root itself.
    """
    distribution = stationary_rank_distribution(sigma)
    zone_mean = sum(p * k for k, p in enumerate(distribution))
    stayers = 0.0
    for rank, weight in enumerate(distribution):
        if weight == 0.0:
            continue
        stayers += weight * _transition_row(rank, zone_mean, sigma)[rank]
    return 1.0 - stayers


@lru_cache(maxsize=64)
def solve_clark_innovation(target_dispersion: float) -> float:
    """Innovation amplitude whose stationary dispersion equals the target.

    Args:
        target_dispersion: the declared `class_rank.target_dispersion`, in rank
            units. Must lie in `[S_RANK_MIN, S_RANK_MAX]`.

    Raises:
        ClarkCalibrationError: the target lies outside the interval in which the
            root is unique, or the bisection did not converge.

    The refusal outside the interval is deliberate and is not defensive
    padding. Below it the map has already passed its collapse, so two
    amplitudes give the same dispersion and a bisection would converge on
    whichever side of the dip it happened to be bracketed against; above it no
    amplitude in the admitted range reaches the target at all. Returning a
    number in either case would be answering a question that has no answer.
    """
    if not (S_RANK_MIN <= target_dispersion <= S_RANK_MAX):
        raise ClarkCalibrationError(
            f"target dispersion {target_dispersion} outside "
            f"[{S_RANK_MIN}, {S_RANK_MAX}], the interval in which the root is "
            f"unique: below it the amplitude-to-dispersion map has not yet "
            f"passed its collapse and admits two roots, above it none"
        )

    low, high = _SIGMA_MIN, _SIGMA_MAX
    low_value = realized_rank_dispersion(low) - target_dispersion
    high_value = realized_rank_dispersion(high) - target_dispersion
    if low_value > 0 or high_value < 0:
        raise ClarkCalibrationError(
            f"bracket [{low}, {high}] does not straddle target dispersion "
            f"{target_dispersion}: the root is not unique there"
        )

    for _ in range(_MAX_BISECTIONS):
        middle = (low + high) / 2.0
        value = realized_rank_dispersion(middle) - target_dispersion
        if abs(value) < _BISECTION_TOL:
            return middle
        if value < 0:
            low = middle
        else:
            high = middle
    raise ClarkCalibrationError(
        f"bisection did not reach {_BISECTION_TOL} in {_MAX_BISECTIONS} steps "
        f"for target dispersion {target_dispersion}"
    )
