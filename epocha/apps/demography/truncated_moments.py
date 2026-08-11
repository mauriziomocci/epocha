"""Stationary moments of the truncated polygenic transmission kernel.

The kernel of design-spec amendment A1 (2026-08-07) transmits a bounded
character on `[0, 1]` as

    two parents:    T = clip(m + b*((T_mother + T_father)/2 - m) + e)
    one parent:     T = clip(m + (b/2)*(T_parent - m) + e)
    no parent:      T = clip(m + e)

with the residual scaled so that, ABSENT truncation, the stationary
dispersion equals the declared `s`:

    e ~ N(0, s^2 * (1 - b^2/2))   two parents
    e ~ N(0, s^2 * (1 - b^2/4))   one parent
    e ~ N(0, s^2)                 no parent

Those three scales are not chosen: they follow from the variance identity
`V = b^2 * Var(parents) + c^2 * s^2` under random mating, imposing `V = s^2`
(amendment A1, "Derivazione dei coefficienti").

Truncation then removes some of that dispersion and piles the removed mass
on the bounds. How much depends on where `m` sits and how wide `s` is, and
there is no elementary closed form, so the amendment prescribes a
deterministic grid fixed point. This module is that computation, and A1's
admissible-region check number 3 is its only consumer.

METHOD, as A1 specifies it. Grid of 1201 nodes on `[0, 1]`. Truncation
semantics on the grid: mass beyond each bound is assigned to the boundary
node in full, never spread over the half cell -- the alternatives diverge,
and discarding-and-renormalising moves the reported boundary mass by up to
1.8 points at (0.80, 0.15), so the convention is fixed here rather than
left to the implementer. Initial vector: a truncated `N(m, s)`. Iterate
until the standard deviation moves by less than 1e-12 between two steps,
with a cap of 500 iterations -- measured, the worst admissible
configuration converges in 44 -- beyond which the caller must fail rather
than proceed on an unconverged value.

The fixed point is unique on the admissible region: four different initial
vectors reach the same one to nine significant figures (verified during the
phase-0 gate, round 8).

WHY THE SIGNAL IS RESAMPLED. The parent term is an affine image of the
midparent distribution, so its grid step is `b*h/2` rather than `h` and does
not align with the output grid. It is rebinned linearly onto the output
grid before the Gaussian convolution. The error that introduces is of order
`(h/(c*s))^2`, which at `h = 1/1200` and the amplitudes this model admits is
below 1e-6 -- four orders under the tolerance any consumer of these numbers
uses, and far below the 0.5 percentage points that separate an accepted pair
from a rejected one.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from scipy.signal import fftconvolve
from scipy.special import ndtr, ndtri

# Grid resolution mandated by amendment A1. Not tunable: two implementations
# that pick different resolutions report different observables for the same
# template, which is the failure the fixed convention exists to prevent.
GRID_NODES = 1201

# Convergence contract, also from A1.
CONVERGENCE_TOL = 1e-12
MAX_ITERATIONS = 500

# The Gaussian kernel is truncated at this many standard deviations. At six
# the mass discarded is 2e-9, five orders below CONVERGENCE_TOL.
_KERNEL_SIGMAS = 6.0

# A1's admissible-region check 3: the realized stationary amplitude must be at
# least this fraction of the declared amplitude, on the worst kinship branch.
MIN_AMPLITUDE_RATIO = 0.95

# A9 point 5: the class-rank target dispersion is exempt from the pair checks
# and carries its own bound, the interval in which A3 proves the root unique.
S_RANK_MIN = 0.95
S_RANK_MAX = 1.39


class FixedPointNotConvergedError(RuntimeError):
    """The grid iteration hit MAX_ITERATIONS without settling."""


def _branch_coefficients(coefficient: float) -> list[tuple[int, float, float]]:
    """Return `(parent_count, signal_coefficient, residual_scale)` per branch.

    The residual scales are the closed forms derived in A1; `coefficient` is
    `h^2` for a trait and `rho` for education.

    `parent_count` is load-bearing and not decoration: the two branches apply
    their coefficient to DIFFERENT random variables. Two parents contribute a
    midparent, whose variance is half the population's; one parent contributes
    its own value, at the population's full variance. Applying the
    single-parent coefficient to a midparent halves the parental variance that
    reaches the child and drives the stationary dispersion below what the
    residual scale was sized for -- measured, 95.81% instead of 97.85% at the
    education pair.
    """
    return [
        (2, coefficient, math.sqrt(1.0 - coefficient**2 / 2.0)),
        (1, coefficient / 2.0, math.sqrt(1.0 - coefficient**2 / 4.0)),
        (0, 0.0, 1.0),  # no parent: no parental signal survives
    ]


def _grid() -> tuple[np.ndarray, float]:
    nodes = np.linspace(0.0, 1.0, GRID_NODES)
    return nodes, float(nodes[1] - nodes[0])


def _clip_to_grid(values: np.ndarray, weights: np.ndarray, step: float) -> np.ndarray:
    """Bin a weighted point cloud onto the `[0, 1]` grid, folding the tails.

    Mass strictly outside `[0, 1]` lands wholly on the nearer boundary node,
    which is the truncation semantics A1 fixes.
    """
    positions = np.clip(values / step, 0.0, GRID_NODES - 1)
    lower = np.floor(positions).astype(np.intp)
    upper = np.minimum(lower + 1, GRID_NODES - 1)
    frac = positions - lower
    out = np.zeros(GRID_NODES)
    np.add.at(out, lower, weights * (1.0 - frac))
    np.add.at(out, upper, weights * frac)
    return out


def _gaussian_cell_kernel(sigma: float, step: float) -> np.ndarray:
    """Cell probabilities of `N(0, sigma)` on a grid of the given step."""
    half = max(1, int(math.ceil(_KERNEL_SIGMAS * sigma / step)))
    edges = (np.arange(-half, half + 2) - 0.5) * step
    cdf = ndtr(edges / sigma)
    return np.diff(cdf)


def _initial_distribution(era_mean: float, era_sd: float) -> np.ndarray:
    nodes, step = _grid()
    edges = np.empty(GRID_NODES + 1)
    edges[0] = -np.inf
    edges[-1] = np.inf
    edges[1:-1] = (nodes[:-1] + nodes[1:]) / 2.0
    cdf = ndtr((edges - era_mean) / era_sd)
    cdf[0], cdf[-1] = 0.0, 1.0
    return np.diff(cdf)


def _iterate_once(
    pmf: np.ndarray,
    era_mean: float,
    parent_count: int,
    signal_coefficient: float,
    residual_sd: float,
    step: float,
) -> tuple[np.ndarray, float]:
    """One application of the transmission kernel. Returns `(pmf, tail_mass)`.

    `tail_mass` is the probability that the PRE-truncation value falls outside
    `[0, 1]`, i.e. the population the clamp pins on a bound.
    """
    if parent_count == 0:
        signal_values = np.array([era_mean])
        signal_weights = np.array([1.0])
    elif parent_count == 1:
        # One parent contributes its OWN value, at the population's full
        # variance -- not a midparent, whose variance is half of it.
        signal_weights = pmf
        parent_values = np.arange(pmf.size) * step
        signal_values = era_mean + signal_coefficient * (parent_values - era_mean)
    else:
        parent_sum = np.convolve(pmf, pmf)  # pmf of T_mother + T_father
        midparent = np.arange(parent_sum.size) * step / 2.0
        signal_values = era_mean + signal_coefficient * (midparent - era_mean)
        signal_weights = parent_sum

    # Rebin the signal onto the output grid before convolving; see module
    # docstring for why the resample is needed and what it costs.
    signal_on_grid = _clip_to_grid(signal_values, signal_weights, step)

    kernel = _gaussian_cell_kernel(residual_sd, step)
    pre_clip = fftconvolve(signal_on_grid, kernel)
    offset = (kernel.size - 1) // 2

    body = pre_clip[offset : offset + GRID_NODES]
    below = float(pre_clip[:offset].sum())
    above = float(pre_clip[offset + GRID_NODES :].sum())

    result = body.copy()
    result[0] += below
    result[-1] += above
    total = result.sum()
    if total > 0:
        result /= total
    return result, (below + above) / max(total, 1e-300)


def _moments(pmf: np.ndarray) -> tuple[float, float]:
    nodes, _ = _grid()
    mean = float(np.dot(pmf, nodes))
    var = float(np.dot(pmf, (nodes - mean) ** 2))
    return mean, math.sqrt(max(var, 0.0))


@lru_cache(maxsize=512)
def _solve(
    era_mean: float,
    era_sd: float,
    parent_count: int,
    signal_coefficient: float,
    residual_sd: float,
) -> tuple[float, float, float]:
    """Return `(stationary_mean, stationary_sd, boundary_mass)` for one branch."""
    _, step = _grid()
    pmf = _initial_distribution(era_mean, era_sd)
    previous_sd = _moments(pmf)[1]
    tail = 0.0
    for iteration in range(1, MAX_ITERATIONS + 1):
        pmf, tail = _iterate_once(
            pmf, era_mean, parent_count, signal_coefficient, residual_sd, step
        )
        mean, sd = _moments(pmf)
        if abs(sd - previous_sd) < CONVERGENCE_TOL:
            return mean, sd, tail
        previous_sd = sd
    raise FixedPointNotConvergedError(
        f"stationary distribution did not settle in {MAX_ITERATIONS} iterations "
        f"for era_mean={era_mean}, era_sd={era_sd}, signal={signal_coefficient}"
    )


@dataclass(frozen=True)
class AdmissibleRegionResult:
    """Verdict of A1's admissible-region check for one declared pair.

    `boundary_mass_branch` is not decoration. A1 requires the reported
    boundary mass to declare which kinship branch produced it, because the
    branch that maximises it is not predictable from the configuration --
    generalising from one branch is the error this gate punished repeatedly.
    """

    accepted: bool
    reason: str
    realized_ratio: float
    boundary_mass: float
    boundary_mass_branch: str


def check_admissible_region(
    era_mean: float, era_sd: float, coefficients: tuple[float, ...]
) -> AdmissibleRegionResult:
    """Apply A1's three admissible-region checks to a declared `(m, s)` pair.

    Args:
        era_mean: declared mean of the observed distribution on `[0, 1]`.
        era_sd: declared amplitude of that distribution.
        coefficients: the transmission coefficients that govern the characters
            declared at this pair -- `h^2` for traits, `rho` for education.
            EVERY distinct value is checked; the class docstring above
            explains why the largest is not the least favourable.

    The third check is evaluated on the WORST of the three kinship branches
    AND on every declared coefficient, not on a conventional branch and not
    on the largest coefficient alone.

    Neither shortcut is safe, and both were tried. The two-parent branch
    fails to be the minimum in a majority of configurations, measured over a
    grid. And the realized amplitude is NOT monotone in the coefficient: at
    `(0.25, 0.15)` the worst branch measures 0.952679 at `c = 0.80` against
    0.952918 at `c = 0.95`, and at `(0.30, 0.15)` 0.974967 against 0.975658
    -- the larger coefficient is the more favourable one there. Evaluating
    `max(coefficients)` and calling it "the least favourable" was therefore
    a false claim in the previous version of this docstring, and one that
    could in principle admit a pair whose lower-coefficient character
    violates the floor. The violations of monotonicity measured about 7e-4,
    so no shipped template was affected; the fix is to stop relying on a
    property the function does not have rather than to bound the error.

    Cost: `_solve` is memoised per `(era_mean, era_sd, branch, signal,
    residual)`, so a group of characters sharing a coefficient costs one
    solve, not one per character.
    """
    if not (0.0 < era_mean < 1.0):
        return AdmissibleRegionResult(
            False,
            f"era_mean {era_mean} outside the open interval (0, 1)",
            float("nan"),
            float("nan"),
            "",
        )
    if era_sd <= 0.0:
        return AdmissibleRegionResult(
            False,
            f"era_sd {era_sd} is not strictly positive",
            float("nan"),
            float("nan"),
            "",
        )
    bhatia_davis = era_mean * (1.0 - era_mean)
    if era_sd**2 >= bhatia_davis:
        return AdmissibleRegionResult(
            False,
            f"era_sd {era_sd} violates the Bhatia-Davis bound, which constrains "
            f"every distribution on [0, 1]: s^2 = {era_sd**2:.4f} must be below "
            f"m(1-m) = {bhatia_davis:.4f}",
            float("nan"),
            float("nan"),
            "",
        )

    labels = ("two-parent", "single-parent", "no-parent")
    ratios: list[float] = []
    masses: list[float] = []
    case_labels: list[str] = []
    for coefficient in sorted(set(coefficients)):
        for index, (parents, signal, residual) in enumerate(_branch_coefficients(coefficient)):
            _, sd, tail = _solve(era_mean, era_sd, parents, signal, residual * era_sd)
            ratios.append(sd / era_sd)
            masses.append(tail)
            case_labels.append(f"{labels[index]} branch at coefficient {coefficient}")

    worst_ratio = min(ratios)
    worst_mass = max(masses)
    worst_mass_branch = case_labels[masses.index(worst_mass)]
    if worst_ratio < MIN_AMPLITUDE_RATIO:
        worst_ratio_branch = case_labels[ratios.index(worst_ratio)]
        return AdmissibleRegionResult(
            False,
            f"realized stationary amplitude {worst_ratio:.2%} of the declared "
            f"era_sd, below the {MIN_AMPLITUDE_RATIO:.0%} floor, on the "
            f"{worst_ratio_branch}, at era_mean {era_mean} and "
            f"era_sd {era_sd}",
            worst_ratio,
            worst_mass,
            worst_mass_branch,
        )
    return AdmissibleRegionResult(True, "", worst_ratio, worst_mass, worst_mass_branch)


def check_rank_dispersion(target_dispersion: float) -> AdmissibleRegionResult:
    """A9 point 5's own bound for the class-rank target dispersion.

    Exempt from the pair checks: it is not a pair on `[0, 1]` but a target
    dispersion on a rank scale. The interval is the one in which A3 proves the
    root of the Clark calibration unique.
    """
    if not (S_RANK_MIN <= target_dispersion <= S_RANK_MAX):
        return AdmissibleRegionResult(
            False,
            f"target_dispersion {target_dispersion} outside "
            f"[{S_RANK_MIN}, {S_RANK_MAX}], the interval in which A3 proves the "
            f"root of the Clark calibration unique",
            float("nan"),
            float("nan"),
            "",
        )
    return AdmissibleRegionResult(True, "", target_dispersion, float("nan"), "")


# ---------------------------------------------------------------------------
# Assortative mating (amendment A4, SC-017)
# ---------------------------------------------------------------------------


def assortative_amplitude_target(coefficient: float, parent_correlation: float) -> float:
    """Amplitude ratio A4 predicts when the parents correlate at `r`.

    Under random mating `Var(midparent) = V/2`; with correlated parents it is
    `V(1 + r)/2`, so the stationary variance solves

        V = b^2 * V * (1 + r)/2 + (1 - b^2/2) * s^2

    giving `sqrt(V)/s = sqrt((1 - b^2/2) / (1 - b^2(1 + r)/2))` (A4). The
    effect is to INFLATE the dispersion: `r > 0` feeds parental variance back
    into the child that the residual scale was not sized for.

    This is the UNTRUNCATED recursion. On the truncated family A1 adopts, the
    clamp removes part of that inflation, and the two answers separate; use
    `solve_assorted_stationary_state` for the family actually in force. This
    function is the target to report a measurement against, never a gate --
    SC-017 reports and does not reject.

    Raises:
        ValueError: if `r` is outside `[-1, 1]`, or if `1 - b^2(1+r)/2` is not
            strictly positive. The second cannot happen at `b <= 1`, but the
            domain is stated rather than left to a bound a future coefficient
            could break.
    """
    if not -1.0 <= parent_correlation <= 1.0:
        raise ValueError(f"parent correlation {parent_correlation} outside [-1, 1]")
    denominator = 1.0 - coefficient**2 * (1.0 + parent_correlation) / 2.0
    if denominator <= 0.0:
        raise ValueError(
            f"no stationary variance at coefficient {coefficient} and correlation "
            f"{parent_correlation}: the recursion is explosive"
        )
    return math.sqrt((1.0 - coefficient**2 / 2.0) / denominator)


@dataclass(frozen=True)
class AssortedStationaryState:
    """What SC-017 asks to be reported, in one object.

    `realized_parent_correlation` is the Pearson correlation between the two
    parents ON THE OBSERVED `[0, 1]` SCALE, which is what a population
    measurement would return and what A4's formula takes. It is strictly below
    the copula parameter that generated it whenever the clamp binds, because
    mass piled on a bound is tied and carries no covariance.
    """

    stationary_mean: float
    stationary_sd: float
    realized_parent_correlation: float
    boundary_mass: float
    untruncated_target: float


def _latent_edges(pmf: np.ndarray) -> np.ndarray:
    """Latent cell edges of the Gaussian copula for a given marginal.

    The copula is defined on `Z = Phi^-1(F(T))`, so a cell of the marginal maps
    to the interval between the standard-normal quantiles of its cumulative
    endpoints. Cells of zero mass collapse to a point and contribute nothing,
    which is the correct behaviour rather than a degeneracy to guard.
    """
    cumulative = np.clip(np.cumsum(pmf), 0.0, 1.0)
    edges = np.empty(pmf.size + 1)
    edges[0] = 0.0
    edges[1:] = cumulative
    edges[-1] = 1.0
    return ndtri(edges)


def _assorted_parent_sum(pmf: np.ndarray, copula_correlation: float) -> tuple[np.ndarray, float]:
    """Return `(pmf of T_mother + T_father, realized Pearson r)`.

    At `copula_correlation = 0` this reduces to `np.convolve(pmf, pmf)`, the
    independent case the rest of the module uses, and the tests assert that
    identity rather than assume it.

    The joint is built row by row from the conditional `Z_f | Z_m ~ N(rho*z,
    1 - rho^2)`: for each mother cell, the father's cell probabilities are
    differences of that conditional CDF at the latent edges. Summing the joint
    over `i + j` gives the distribution of the parental sum exactly, because
    both parents live on the same grid and the sum of two node indices IS the
    index of the sum -- the same reduction a convolution performs, generalised
    to a joint that no longer factorises.
    """
    size = pmf.size
    nodes, _ = _grid()
    if copula_correlation == 0.0:
        joint_sum = np.convolve(pmf, pmf)
        return joint_sum, 0.0

    edges = _latent_edges(pmf)
    # Representative latent position of each mother cell: the quantile of its
    # own mid-cumulative, which is the cell's conditional median rather than an
    # arbitrary endpoint.
    cumulative = np.clip(np.cumsum(pmf), 0.0, 1.0)
    mid = np.clip(cumulative - pmf / 2.0, 1e-15, 1.0 - 1e-15)
    z_mother = ndtri(mid)

    spread = math.sqrt(1.0 - copula_correlation**2)
    standardised = (edges[None, :] - copula_correlation * z_mother[:, None]) / spread
    conditional_cdf = ndtr(standardised)
    conditional = np.diff(conditional_cdf, axis=1)
    joint = pmf[:, None] * conditional
    total = joint.sum()
    if total > 0:
        joint /= total

    index_sum = (np.arange(size)[:, None] + np.arange(size)[None, :]).ravel()
    parent_sum = np.bincount(index_sum, weights=joint.ravel(), minlength=2 * size - 1)

    mean = float(np.dot(pmf, nodes))
    variance = float(np.dot(pmf, (nodes - mean) ** 2))
    cross = float(nodes @ joint @ nodes)
    realized = (cross - mean**2) / variance if variance > 0 else 0.0
    return parent_sum, realized


@lru_cache(maxsize=256)
def solve_assorted_stationary_state(
    era_mean: float,
    era_sd: float,
    coefficient: float,
    copula_correlation: float,
) -> AssortedStationaryState:
    """Stationary state of the two-parent branch under assortative mating.

    A4 quotes two crossing thresholds on the TRUNCATED family and calls them
    measured, but nothing in the repository could produce them: `_solve` takes
    `np.convolve(pmf, pmf)`, which is the sum of two INDEPENDENT draws by
    construction, and offers no correlation parameter. This function is the
    missing instrument, and the convention it fixes is the part A4 left open.

    THE CONVENTION, stated because more than one is defensible and two
    implementations picking differently would report different thresholds for
    the same era. Mating is a GAUSSIAN COPULA on the current marginal:
    `Z = Phi^-1(F(T))` for both parents, jointly normal with correlation
    `copula_correlation`. Chosen over the alternatives because it is the only
    one that (i) preserves the marginal, so the assortment changes who
    marries whom and nothing else, (ii) reduces to independence at zero,
    checked rather than assumed, and (iii) needs one parameter. Perfect
    rank ordering is the `copula_correlation = 1` limit.

    Point (i) holds EXACTLY for the continuous copula and only approximately
    for this discretisation, and the difference is stated with its
    configuration rather than as a bare number, because it varies by an order
    of magnitude across the pairs this model admits. The conditional is
    evaluated at one representative latent position per mother cell instead
    of integrated over the cell, so the construction is asymmetric: the
    MOTHER's marginal is reproduced to 2e-17 and the FATHER's is not. At a
    copula parameter of 0.8 the father's worst per-cell error measures
    1.483e-3 on the education pair's STATIONARY distribution -- the one this
    function actually solves -- against 1.110e-3 on that pair's initial
    distribution and 4.068e-5 on the centred trait pair. Quoting the smallest
    of the three without naming the configuration is the failure this module
    exists to correct, so all three are named and `test_assortative_mating.py`
    pins them.

    Re-solving both crossing thresholds against the symmetrised joint
    `0.5 * (J + J^T)` moves them by nothing at six decimals -- 0.540291 and
    0.712160 either way -- so the published figures are robust to the
    asymmetry; it was the claim of exactness that needed qualifying, not the
    numbers. The measurement
    reported is the realized Pearson correlation on the observed scale, not
    the copula parameter, because that is what counting a real population
    would return and what A4's formula consumes.

    Only the two-parent branch is solved: it is the only one where mating
    enters at all.
    """
    if not -1.0 < copula_correlation < 1.0:
        raise ValueError(f"copula correlation {copula_correlation} outside (-1, 1)")
    _, step = _grid()
    signal = coefficient
    residual_sd = era_sd * math.sqrt(1.0 - coefficient**2 / 2.0)
    kernel = _gaussian_cell_kernel(residual_sd, step)
    offset = (kernel.size - 1) // 2

    pmf = _initial_distribution(era_mean, era_sd)
    previous_sd = _moments(pmf)[1]
    for _ in range(MAX_ITERATIONS):
        parent_sum, realized_r = _assorted_parent_sum(pmf, copula_correlation)
        midparent = np.arange(parent_sum.size) * step / 2.0
        signal_values = era_mean + signal * (midparent - era_mean)
        signal_on_grid = _clip_to_grid(signal_values, parent_sum, step)

        pre_clip = fftconvolve(signal_on_grid, kernel)
        body = pre_clip[offset : offset + GRID_NODES]
        below = float(pre_clip[:offset].sum())
        above = float(pre_clip[offset + GRID_NODES :].sum())
        pmf = body.copy()
        pmf[0] += below
        pmf[-1] += above
        total = pmf.sum()
        if total > 0:
            pmf /= total
        boundary_mass = (below + above) / max(total, 1e-300)

        mean, sd = _moments(pmf)
        if abs(sd - previous_sd) < CONVERGENCE_TOL:
            return AssortedStationaryState(
                mean,
                sd,
                realized_r,
                boundary_mass,
                assortative_amplitude_target(coefficient, realized_r),
            )
        previous_sd = sd
    raise FixedPointNotConvergedError(
        f"assorted stationary distribution did not settle in {MAX_ITERATIONS} "
        f"iterations at era_mean={era_mean}, era_sd={era_sd}, "
        f"coefficient={coefficient}, copula={copula_correlation}"
    )
