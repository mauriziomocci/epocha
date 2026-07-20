"""Polygenic additive inheritance kernel for biological trait transmission.

Source:
- Falconer, D.S. & Mackay, T.F.C. (1996). Introduction to Quantitative
  Genetics (4th ed.), Longman, chapter 8 (polygenic additive model with
  an environmental noise term estimated at the population level).

Per-trait heritability (h^2) values used by callers of `inherit_trait` come
from trait-specific primary studies (e.g. Jang, Livesley & Vernon 1996 for
Big Five personality traits; Plomin & Deary 2015 for intelligence; Zietsch
et al. 2014 for biological fertility). Polderman et al. (2015), "Meta-
analysis of the heritability of human traits based on fifty years of twin
studies", Nature Genetics 47(7), 702-709, is cited only as the methodological
backbone corroborating polygenic additive inheritance across trait domains
(mean h^2 ~= 0.49 over 17,804 traits) -- it is NEVER the source of an
individual trait's h^2 value. The per-trait table and its citations live in
the demography design spec (docs/superpowers/specs/2026-04-18-demography-
design-it.md, Sezione 4) and in the era templates that carry the numeric
h^2 values consumed by the birth pipeline.
"""

from __future__ import annotations

import ast
import logging
from typing import Any

from django.core.exceptions import FieldDoesNotExist
from django.db.models import Q

from epocha.apps.demography.rng import get_seeded_rng
from epocha.apps.world.stratification import _CLASS_RANK

logger = logging.getLogger(__name__)


class FormulaError(ValueError):
    """Raised when a derived-trait formula uses a construct outside the
    arithmetic whitelist enforced by `evaluate_derived_formula`."""


# Node types allowed inside a derived-trait formula. Deliberately restricted
# to the arithmetic subset of the Python expression grammar: an expression
# wrapper, binary/unary operators, numeric constants, and bare names (which
# resolve only against the caller-supplied symbol table -- see
# `evaluate_derived_formula`). Anything not in this set (function calls,
# attribute access, subscripts, comprehensions, boolean/comparison
# operators, lambdas, ...) is refused.
_ALLOWED_NODE_TYPES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Constant,
    ast.Name,
    ast.Load,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Pow,
    ast.Mod,
    ast.USub,
    ast.UAdd,
)


def evaluate_derived_formula(expression: str, symbols: dict[str, float]) -> float:
    """Evaluate a derived-trait formula against a restricted arithmetic grammar.

    This is the evaluator for the design's `derived_trait_formulas` (design
    spec Sezione 4), e.g. the `cunning` Machiavellism proxy:

        cunning = 0.4*(1-agreeableness) + 0.3*neuroticism + 0.3*intelligence

    where the right-hand side is a template string stored in an era template
    file and `symbols` supplies the already-resolved trait values referenced
    by name.

    Security (decision D5): the expression is parsed with `ast.parse(...,
    mode="eval")` and walked node by node against an explicit whitelist --
    `Expression`, `BinOp`, `UnaryOp`, `Constant`, `Name`, and the arithmetic
    operators `Add`, `Sub`, `Mult`, `Div`, `Pow`, `Mod`, `USub`, `UAdd`. Any
    other node type (function calls, attribute access, subscripts,
    comprehensions, boolean/comparison operators, lambdas, and so on) raises
    `FormulaError`. `eval()` on the raw string is never used. Formula
    templates come from versioned era template files rather than end-user
    input, but the evaluator does not treat that as license to widen the
    surface: today's trusted input is not a guarantee against a future
    caller feeding it untrusted data, and the whitelist is cheap defense in
    depth against turning a data file into a code-execution vector.

    A bare name is resolved only by exact lookup in `symbols`; a name absent
    from `symbols` raises `FormulaError`. This is also what blocks dunder
    names (e.g. `__import__`): they are refused on the same unknown-name
    path as any other name not present in the symbol table, with no special
    casing required.

    Args:
        expression: the formula's right-hand side, e.g.
            "0.4*(1-agreeableness) + 0.3*neuroticism + 0.3*intelligence".
        symbols: mapping from trait name to its resolved numeric value.

    Returns:
        The formula's numeric result as a float.

    Raises:
        FormulaError: if `expression` is not valid Python syntax, uses any
            node type outside the whitelist, references a name absent from
            `symbols`, or contains a non-numeric constant.
    """
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise FormulaError(f"invalid formula syntax: {expression!r}") from exc

    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODE_TYPES):
            raise FormulaError(
                f"disallowed construct {type(node).__name__!r} in formula: {expression!r}"
            )

    return float(_eval_node(tree.body, symbols))


def _eval_node(node: ast.expr, symbols: dict[str, float]) -> float:
    """Recursively evaluate an AST node already verified against the whitelist.

    Kept separate from the whitelist walk in `evaluate_derived_formula` so
    that node-type validation always runs over the whole tree before any
    evaluation happens -- a malformed subtree is rejected before partial
    evaluation could have any observable side effect.
    """
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise FormulaError(f"non-numeric constant in formula: {node.value!r}")
        return node.value

    if isinstance(node, ast.Name):
        if node.id not in symbols:
            raise FormulaError(f"unknown symbol in formula: {node.id!r}")
        return symbols[node.id]

    if isinstance(node, ast.UnaryOp):
        operand = _eval_node(node.operand, symbols)
        if isinstance(node.op, ast.USub):
            return -operand
        if isinstance(node.op, ast.UAdd):
            return +operand
        raise FormulaError(f"disallowed unary operator: {type(node.op).__name__!r}")

    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left, symbols)
        right = _eval_node(node.right, symbols)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
        if isinstance(node.op, ast.Pow):
            return left**right
        if isinstance(node.op, ast.Mod):
            return left % right
        raise FormulaError(f"disallowed binary operator: {type(node.op).__name__!r}")

    raise FormulaError(f"disallowed construct {type(node).__name__!r} in formula")


def inherit_trait(
    mother_val: float | None,
    father_val: float | None,
    h2: float,
    era_mean: float,
    era_sd: float,
    rng,
    lo: float = 0.0,
    hi: float = 1.0,
) -> float:
    """Compute a child's trait value under polygenic additive inheritance.

    Formula (Falconer & Mackay 1996, ch. 8):

        child_T = h2 * midparent_T + (1 - h2) * noise_T
        noise_T ~ N(era_mean, era_sd)

    where `midparent_T = (mother_val + father_val) / 2` when both parents
    are known. `noise` models the environmental contribution as a draw from
    a Normal distribution whose mean and standard deviation are estimated
    from the tick-0 population and frozen thereafter (design spec Sezione
    4); it is drawn exactly once per call, via `rng.gauss(era_mean,
    era_sd)`, and always AFTER the midparent branch below so that the RNG
    sequence consumed by this function is independent of which branch ran.

    Fix I-1 -- single-parent fallback: when exactly one of mother_val /
    father_val is known (None for the other), the midparent term degrades
    to the known parent's value alone:

        child_T = h2 * parent_T + (1 - h2) * noise_T

    This halves the genetic signal relative to the two-parent case, which
    matches the real single-parent genetic flow rather than treating the
    missing parent as contributing zero. Documented as a deliberate
    simplification for genealogies where only one parent is resolved (adoption
    scenarios, or synthetic tick-0 genealogies without both parents recorded).

    The result is clamped to [lo, hi] (default [0.0, 1.0], the typical range
    for Agent personality/trait scalars); callers pass the trait-specific
    range when it differs.

    This function is pure: no ORM access, no global state. Given the same
    rng state and inputs it is fully deterministic, which is required for
    publication-grade reproducibility of the birth pipeline.

    Args:
        mother_val: mother's trait value, or None if the mother is unknown.
        father_val: father's trait value, or None if the father is unknown.
            At least one of mother_val / father_val must be provided.
        h2: heritability coefficient for this trait, in [0, 1].
        era_mean: mean of the era-specific environmental noise distribution.
        era_sd: standard deviation of the era-specific environmental noise
            distribution.
        rng: a random.Random-compatible instance exposing .gauss(mu, sigma).
        lo: lower clamp bound (default 0.0).
        hi: upper clamp bound (default 1.0).

    Returns:
        The child's inherited trait value, clamped to [lo, hi].
    """
    if mother_val is not None and father_val is not None:
        midparent = (mother_val + father_val) / 2
    elif mother_val is not None:
        midparent = mother_val
    else:
        midparent = father_val

    noise = rng.gauss(era_mean, era_sd)
    result = h2 * midparent + (1 - h2) * noise
    return max(lo, min(hi, result))


# Environmental-noise prior applied when neither the era template nor a
# caller-supplied noise spec provides era_mean/era_sd for a trait. The
# design spec (Sezione 4) calls for era_mean_T / era_sd_T estimated from the
# tick-0 population and frozen thereafter (Falconer & Mackay 1996, ch. 8 --
# environmental deviation estimated at the population level); no era
# template (verified: none of the five templates under
# epocha/apps/demography/templates/ declare a trait_inheritance.era_noise
# section) and no population-statistics module currently supply that
# estimate. DEFAULT_ERA_MEAN = 0.5 and DEFAULT_ERA_SD = 0.15 are a
# documented, explicitly tunable interim substitute: mean at the scale
# midpoint and a moderate spread for a generic [0, 1]-bounded trait. This is
# a deliberate simplification of the tick-0-population-estimation mechanism,
# scoped out of `apply_trait_inheritance` because it requires a
# population-statistics snapshot this function's signature does not carry;
# a later task must thread real per-trait era_mean/era_sd values through
# once that machinery exists.
DEFAULT_ERA_MEAN = 0.5
DEFAULT_ERA_SD = 0.15


def _agent_has_field(model_cls: type, name: str) -> bool:
    """Return True when `model_cls` has a concrete field named `name`.

    Used to route a heritable trait name to either a scalar Agent FloatField
    (e.g. `intelligence`) or an `Agent.personality` JSONB entry (e.g.
    `openness`, or an unpublished-h2 trait like `humor_style`). "Concrete"
    excludes reverse relations and many-to-many descriptors, which have no
    column on `model_cls` itself and are never valid inheritance
    destinations. No trait name is special-cased: a template change
    (renaming or adding a heritability key) is picked up automatically the
    next time this function runs.
    """
    try:
        field = model_cls._meta.get_field(name)
    except FieldDoesNotExist:
        return False
    return bool(getattr(field, "concrete", False))


def apply_trait_inheritance(child: Any, mother: Any, father: Any, template: dict, rng: Any) -> None:
    """Apply polygenic additive inheritance, then evaluate derived-trait formulas.

    Birth-pipeline orchestrator (design spec Sezione 4, "Responsibility
    contract"). Two passes, strictly ordered:

    1. Every heritable trait -- scalar Agent fields (e.g. `intelligence`)
       and `Agent.personality` JSONB entries alike (the Big Five, or
       unpublished-h2 traits like `humor_style`) -- is drawn through the
       polygenic additive kernel `inherit_trait` (Falconer & Mackay 1996,
       ch. 8).
    2. `derived_trait_formulas` (e.g. `cunning`, a Machiavellism proxy) are
       evaluated against the freshly inherited values from step 1, never
       against the parents' values directly. `cunning` has no published
       heritability and is therefore never drawn from the polygenic kernel.

    Trait set for step 1: every key in
    `template["trait_inheritance"]["heritability"]` except the "default"
    sentinel, plus any key present in `mother.personality` or
    `father.personality` that has no published h2 entry -- those inherit at
    `heritability["default"]` (0.30 in every current era template),
    documented in the design spec as a tunable default for personality
    traits without a primary-study h2 (e.g. `humor_style`,
    `attachment_style`). `social_class` is never included here: it carries
    no heritability entry in any era template and is governed by the
    social-inheritance rules (design spec Sezione 5), a separate mechanism.

    Trait names are collected in a deterministic order -- heritability
    dict order first (JSON insertion order, stable), then any extra
    personality-only names sorted lexicographically -- rather than via an
    unordered Python `set`. `rng.gauss` is drawn exactly once per trait
    (see `inherit_trait`), so an unordered iteration would make the RNG
    draw sequence depend on the interpreter's per-process string hash seed,
    breaking the bit-for-bit reproducibility the demography subsystem
    requires for identically seeded runs.

    era_mean / era_sd: read per-trait from
    `template["trait_inheritance"].get("era_noise", {})[name]` when
    present; otherwise `DEFAULT_ERA_MEAN` / `DEFAULT_ERA_SD` are used (see
    their docstring for the full rationale -- this is a documented interim
    substitute for the design spec's tick-0-population-estimated
    era_mean_T / era_sd_T, no era template currently declares an
    `era_noise` section).

    This function mutates `child` in place -- scalar attributes via
    `setattr`, personality entries via `child.personality[name] = value` --
    but never calls `child.save()`; persistence is the caller's
    responsibility, keeping this composable with however Plan 4 sequences
    the birth pipeline. All randomness is drawn from the passed `rng`; no
    global state, no hidden ORM writes, no calls to `inherit_trait` or
    `evaluate_derived_formula` outside their published contracts.

    Args:
        child: the newborn Agent instance (need not be saved yet).
        mother: the mother Agent instance, or None if unresolved.
        father: the father Agent instance, or None if unresolved.
        template: a demography era template dict as returned by
            `template_loader.load_template`, or an equivalent dict carrying
            at least `trait_inheritance.heritability` (and optionally
            `trait_inheritance.derived_trait_formulas` /
            `trait_inheritance.era_noise`).
        rng: a random.Random-compatible instance (see
            `demography.rng.get_seeded_rng`), consumed in the deterministic
            trait order described above.
    """
    trait_inheritance = template["trait_inheritance"]
    heritability = trait_inheritance["heritability"]
    default_h2 = heritability.get("default", 0.30)
    era_noise = trait_inheritance.get("era_noise", {})

    trait_names = [name for name in heritability if name != "default"]
    covered = set(trait_names)
    extra_names: set[str] = set()
    for parent in (mother, father):
        if parent is not None and parent.personality:
            extra_names.update(parent.personality.keys())
    extra_names -= covered
    trait_names.extend(sorted(extra_names))

    child_model = type(child)
    symbols: dict[str, float] = {}

    for name in trait_names:
        h2 = heritability.get(name, default_h2)
        noise_spec = era_noise.get(name, {})
        era_mean = noise_spec.get("era_mean", DEFAULT_ERA_MEAN)
        era_sd = noise_spec.get("era_sd", DEFAULT_ERA_SD)

        is_scalar = _agent_has_field(child_model, name)
        if is_scalar:
            mother_val = getattr(mother, name, None) if mother is not None else None
            father_val = getattr(father, name, None) if father is not None else None
        else:
            mother_val = (mother.personality or {}).get(name) if mother is not None else None
            father_val = (father.personality or {}).get(name) if father is not None else None

        value = inherit_trait(mother_val, father_val, h2, era_mean, era_sd, rng)

        if is_scalar:
            setattr(child, name, value)
        else:
            child.personality[name] = value
        symbols[name] = value

    _apply_derived_traits(child, trait_inheritance.get("derived_trait_formulas", {}), symbols)


def resolve_birth_attributes(template: dict, rng: Any) -> tuple[str, str]:
    """Draw a newborn's gender and sexual orientation from era-template priors.

    Two independent draws, strictly ordered so the RNG sequence this
    function consumes is predictable for identically-seeded reproducibility:

    1. Gender, from the secondary sex ratio at birth (males per female).
       `template["sex_ratio_at_birth"]` (e.g. 1.05 in every current era
       template except sci_fi's 1.0) is converted to a male probability via
       p_male = sex_ratio / (1 + sex_ratio), then a single `rng.random()` is
       drawn and compared against it. A ratio of 1.05 -- about 105 male
       births per 100 female births -- is biologically near-universal across
       human populations (Falconer & Mackay 1996, ch. 8, cite it as one of
       the best-documented constants in human genetics) and is nonetheless
       carried as a tunable per-era template parameter rather than a hard
       constant, since some era templates (sci_fi) deliberately deviate from
       it. This draw yields only "male" or "female": the biological
       secondary sex ratio is a birth-sex statistic, not a gender-identity
       distribution, so it structurally cannot produce "non_binary" (an
       `Agent.Gender` value describing identity, not birth sex).

    2. Sexual orientation, from `template["sexual_orientation_distribution"]`
       -- a second `rng.random()` is drawn and walked cumulatively over the
       distribution's own keys in their dict (JSON insertion) order, never
       sorted and never routed through a set: iterating in a different
       order would change which bucket a given uniform draw lands in and
       silently break reproducibility across identically-seeded runs. If
       the cumulative sum falls fractionally short of the draw (a
       floating-point tail from summing probabilities that nominally total
       1.0), the last key in iteration order is returned rather than
       raising, so a rounding artifact in a template's probabilities can
       never crash the birth pipeline.

       The modern-era default distribution (heterosexual 0.955, bisexual
       0.030, homosexual 0.015, no "asexual" entry) comes from Chandra, A.,
       Mosher, W.D., Copen, C. & Sionean, C. (2011), "Sexual behaviour,
       sexual attraction, and sexual identity in the United States: data
       from the 2006-2008 National Survey of Family Growth", National
       Health Statistics Reports 36. These are modern US self-report
       values, carried as tunable design parameters for eras (and future
       templates) where no comparable survey data exists -- not a claim
       that they hold universally across historical populations.

    This function is pure: no ORM access, no persistence, no global state.
    It consumes exactly two `rng.random()` draws, in the order documented
    above, so callers composing it with other rng-consuming steps (e.g.
    `apply_trait_inheritance`) can reason about the total draw count.

    Args:
        template: a demography era template dict as returned by
            `template_loader.load_template`, carrying at least
            `sex_ratio_at_birth` and `sexual_orientation_distribution`.
        rng: a random.Random-compatible instance exposing `.random()`.

    Returns:
        A (gender, orientation) tuple of two strings: gender is "male" or
        "female"; orientation is one of the keys of
        `template["sexual_orientation_distribution"]`.
    """
    sex_ratio = template["sex_ratio_at_birth"]
    p_male = sex_ratio / (1.0 + sex_ratio)
    gender = "male" if rng.random() < p_male else "female"

    distribution = template["sexual_orientation_distribution"]
    draw = rng.random()
    cumulative = 0.0
    orientation = None
    for key, probability in distribution.items():
        cumulative += probability
        if draw < cumulative:
            orientation = key
            break
    if orientation is None:
        orientation = list(distribution.keys())[-1]

    return gender, orientation


def _apply_derived_traits(
    child: Any, derived_trait_formulas: dict, symbols: dict[str, float]
) -> None:
    """Evaluate each derived-trait formula and write the result onto `child`.

    Called strictly after the polygenic pass in `apply_trait_inheritance`
    (design spec Sezione 4, "Responsibility contract"). `symbols` is the
    trait-name-to-value map already computed by that pass -- scoped to the
    traits `apply_trait_inheritance` actually just inherited, never the raw
    set of every Agent field, so a formula cannot accidentally resolve
    against an unrelated Agent attribute (e.g. `wealth`, `mood`) that
    happens to share a name. Each result is clamped to the formula's
    declared `range` and written to the matching Agent field or
    `Agent.personality` entry via the same scalar/personality routing used
    for inherited traits (currently `cunning` is the only derived trait,
    and it is a scalar field).
    """
    if not derived_trait_formulas:
        return

    child_model = type(child)
    for name, spec in derived_trait_formulas.items():
        raw_value = evaluate_derived_formula(spec["formula"], symbols)
        lo, hi = spec["range"]
        value = max(lo, min(hi, raw_value))

        if _agent_has_field(child_model, name):
            setattr(child, name, value)
        else:
            child.personality[name] = value


# ---------------------------------------------------------------------------
# Social inheritance (design spec Sezione 5): social-class transmission and
# education-level regression applied once per birth, independently of the
# polygenic biological pass above.
# ---------------------------------------------------------------------------

# Cross-module consistency note, flagged for the phase-6 adversarial audit:
# the canonical social-class rank ladder lives in
# epocha.apps.world.stratification._CLASS_RANK (wealth-percentile class
# assignment, 0 = elite .. 4 = poor). It is imported here rather than
# duplicated -- re-deriving the same five-way ranking in this module would
# violate the project's DRY rule and would silently drift from the
# stratification module's definition the next time either one changes.
# demography already depends on the world app (see
# epocha/apps/demography/context.py importing from economy, an analogous
# cross-app dependency), so this import does not introduce a new
# architectural layering violation.
#
# _CLASS_RANK has no "enslaved" entry: the stratification module assigns
# class purely from a wealth percentile each political cycle and never
# produces "enslaved", even though Agent.social_class's help_text
# (epocha/apps/agents/models.py) lists it as a valid value. The only path
# that can ever populate "enslaved" is patrilineal_rigid social inheritance
# carrying it forward from an already-enslaved father (pre-industrial
# templates model chattel slavery this way). _EXTENDED_CLASS_RANK below is
# therefore a strict superset of stratification's ladder, adding "enslaved"
# one rank below "poor" so this module's rank arithmetic (clark_regression,
# becker_tomes_elasticity_0.4, meritocratic) can place it correctly on the
# rare occasions it appears as a parent's class. A future change to
# _CLASS_RANK's five keys in the stratification module will silently desync
# this extension unless re-verified; flagged here rather than fixed, since a
# real fix would mean changing the stratification module itself, which is
# outside this task's scope.
_EXTENDED_CLASS_RANK: dict[str, int] = {**_CLASS_RANK, "enslaved": max(_CLASS_RANK.values()) + 1}
_RANK_TO_CLASS_LABEL: dict[int, str] = {rank: label for label, rank in _EXTENDED_CLASS_RANK.items()}
_MAX_CLASS_RANK = max(_EXTENDED_CLASS_RANK.values())

# Fallback rank for a social_class value absent from _EXTENDED_CLASS_RANK
# (defensive: a corrupted fixture, or a future class label added to
# Agent.social_class's free-text help_text without a matching ladder entry).
# "working" is the Agent model field's own default value, which makes it
# the least surprising fallback -- an unrecognized class is treated as
# ordinary rather than assumed elite or destitute.
_UNKNOWN_CLASS_FALLBACK_RANK = _EXTENDED_CLASS_RANK["working"]

# Rank-noise standard deviation for the becker_tomes_elasticity_0.4 sampling
# step. Solon (1999) and Chetty et al. (2014) report the point elasticity
# (0.4) but not a residual-variance term for a discrete five-level class
# ladder -- the underlying US intergenerational-mobility studies model
# continuous log-income, not discrete class rank, so no directly published
# standard deviation applies here. 0.75 (three-quarters of one rank step) is
# a documented, explicitly tunable design parameter chosen to produce
# visible sampling variability around the shifted mean without letting
# noise dominate the elasticity signal; it is not itself sourced from Solon
# or Chetty.
_BECKER_TOMES_RANK_NOISE_SD = 0.75

# Rank span the meritocratic rule maps merit onto: elite=0 .. poor=4, i.e.
# _CLASS_RANK's own un-extended span. Deliberately excludes "enslaved":
# meritocratic reassignment is the sci_fi template's speculative design
# choice (design spec Sezione 5, no citation), and a merit-based system
# reassigning servile status would not be a documented simplification but
# an invented one -- "enslaved" only ever reaches a child via
# patrilineal_rigid transmission from an already-enslaved father, never via
# merit.
_MERIT_RANK_SPAN = float(max(_CLASS_RANK.values()))

# Era-mean education-level prior applied when neither the era template nor
# a caller-supplied override provides era_mean_education. No era template
# currently declares a `social_inheritance.era_mean_education` key (verified
# across all five templates under epocha/apps/demography/templates/).
# 0.3 matches Agent.education_level's own field default
# (epocha/apps/agents/models.py), making the interim substitute consistent
# with the model's own baseline rather than an arbitrary scale midpoint.
# Documented, explicitly tunable placeholder in the same spirit as
# DEFAULT_ERA_MEAN / DEFAULT_ERA_SD above, pending a per-era value carried
# by the templates.
DEFAULT_ERA_MEAN_EDUCATION = 0.3


def _class_rank(social_class: str | None) -> int:
    """Resolve a social_class string to its rank on `_EXTENDED_CLASS_RANK`.

    Defensive: an unrecognized or missing value falls back to the "working"
    rank rather than raising `KeyError` (decision A) -- rank arithmetic
    must never crash the birth pipeline over a corrupted or unexpected
    class label.
    """
    if social_class is None:
        return _UNKNOWN_CLASS_FALLBACK_RANK
    return _EXTENDED_CLASS_RANK.get(social_class, _UNKNOWN_CLASS_FALLBACK_RANK)


def _rank_to_class_label(rank: float) -> str:
    """Round a continuous rank to the nearest class label.

    The raw rank is clamped to the ladder's valid range
    `[0, _MAX_CLASS_RANK]` before rounding, so an out-of-range arithmetic
    result (e.g. a large becker_tomes_elasticity_0.4 perturbation) always
    resolves to a real label instead of a `KeyError`.
    """
    clamped_rank = max(0, min(_MAX_CLASS_RANK, round(rank)))
    return _RANK_TO_CLASS_LABEL[clamped_rank]


def _resolve_parent_rank(mother: Any, father: Any) -> int:
    """Father's rank, falling back to the mother's when the father is
    unresolved, falling back further to the "working" rank when neither
    parent is known.

    The design spec documents the father-then-mother fallback explicitly
    only for patrilineal_rigid; the same fallback is applied here to
    clark_regression, becker_tomes_elasticity_0.4, and meritocratic so a
    missing father never crashes rank arithmetic in any rule -- consistent
    with the single-parent fallback philosophy of fix I-1 in
    `inherit_trait` elsewhere in this module.
    """
    if father is not None:
        return _class_rank(father.social_class)
    if mother is not None:
        return _class_rank(mother.social_class)
    return _UNKNOWN_CLASS_FALLBACK_RANK


def _apply_patrilineal_rigid(child: Any, mother: Any, father: Any) -> None:
    """child.social_class = father.social_class verbatim (Goody, J. (1976),
    "Production and Reproduction"; Wrigley, E.A. (1981), "Population
    History of England"). Falls back to the mother's class when the father
    is unresolved, and to the "working" rank when neither parent is known.

    A pure string copy -- not a rank round-trip -- so a servile "enslaved"
    father's status transmits to the child exactly, without ever passing
    through `_rank_to_class_label`'s rounding.
    """
    if father is not None:
        child.social_class = father.social_class
    elif mother is not None:
        child.social_class = mother.social_class
    else:
        child.social_class = _RANK_TO_CLASS_LABEL[_UNKNOWN_CLASS_FALLBACK_RANK]


def _apply_clark_regression(child: Any, mother: Any, father: Any, zone_class_mean: float) -> None:
    """70% inherited from the father's rank, 30% regression toward the
    zone's mean class rank (Clark, G. (2014), "The Son Also Rises: Surnames
    and the History of Social Mobility", Princeton University Press).

    Deterministic: no `rng` draw, matching the design spec's description of
    this rule as a fixed 70/30 weighting rather than a sampled outcome.
    """
    parent_rank = _resolve_parent_rank(mother, father)
    rank = 0.7 * parent_rank + 0.3 * zone_class_mean
    child.social_class = _rank_to_class_label(rank)


def _apply_becker_tomes(
    child: Any, mother: Any, father: Any, zone_class_mean: float, rng: Any
) -> None:
    """Intergenerational income elasticity 0.4 applied to class rank.

    The 0.4 elasticity value is attributed to Solon, G. (1999),
    "Intergenerational Mobility in the Labor Market", Handbook of Labor
    Economics 3A, and corroborated by Chetty, R. et al. (2014), "Is the
    United States Still a Land of Opportunity?", who report a 0.3-0.5
    range. Becker, G.S. & Tomes, N. (1979), "An Equilibrium Theory of the
    Distribution of Income and Intergenerational Mobility", Journal of
    Political Economy, is the founding theoretical framework for
    intergenerational elasticity but did not publish this specific value
    (decision C) -- the template key `becker_tomes_elasticity_0.4` names
    the framework, not the value's source.

    child_rank = 0.4 * parent_rank + 0.6 * zone_class_mean, plus a seeded
    Gaussian perturbation (see `_BECKER_TOMES_RANK_NOISE_SD`) drawn via
    `rng.gauss`, mapped back to the nearest label. Sampled, unlike
    clark_regression: the design spec describes this rule as drawing from a
    distribution shifted toward the parent's rank, not a fixed weighting.
    """
    parent_rank = _resolve_parent_rank(mother, father)
    base_rank = 0.4 * parent_rank + 0.6 * zone_class_mean
    perturbation = rng.gauss(0.0, _BECKER_TOMES_RANK_NOISE_SD)
    child.social_class = _rank_to_class_label(base_rank + perturbation)


def _apply_meritocratic(child: Any, mother: Any, father: Any) -> None:
    """20% inherited rank, 80% merit-based reassignment (sci_fi template's
    speculative design choice, design spec Sezione 5 -- no citation).

    Merit is the mean of the child's own already-inherited `intelligence`
    and `education_level` (both in [0, 1]); higher merit maps to a better,
    i.e. numerically lower, rank via `merit_rank = (1 - merit) *
    _MERIT_RANK_SPAN`. Deterministic: no `rng` draw.
    """
    parent_rank = _resolve_parent_rank(mother, father)
    merit = (child.intelligence + child.education_level) / 2.0
    merit_rank = (1.0 - merit) * _MERIT_RANK_SPAN
    rank = 0.2 * parent_rank + 0.8 * merit_rank
    child.social_class = _rank_to_class_label(rank)


def _regress_education_level(
    mother: Any, father: Any, rho: float, era_mean_education: float
) -> float:
    """child.education_level = rho * midparent_education + (1 - rho) *
    era_mean_education, clamped to [0.0, 1.0].

    Applied identically after every `class_rule` branch (design spec
    Sezione 5). Single-parent case degrades the midparent term to that
    parent's value alone, consistent with fix I-1 in `inherit_trait`; when
    neither parent is known, the midparent term degrades to
    `era_mean_education` itself so the formula still resolves to a
    well-defined value instead of raising.
    """
    mother_edu = mother.education_level if mother is not None else None
    father_edu = father.education_level if father is not None else None

    if mother_edu is not None and father_edu is not None:
        midparent_edu = (mother_edu + father_edu) / 2.0
    elif mother_edu is not None:
        midparent_edu = mother_edu
    elif father_edu is not None:
        midparent_edu = father_edu
    else:
        midparent_edu = era_mean_education

    value = rho * midparent_edu + (1.0 - rho) * era_mean_education
    return max(0.0, min(1.0, value))


def apply_social_inheritance(
    child: Any, mother: Any, father: Any, template: dict, zone_class_mean: float, rng: Any
) -> None:
    """Apply per-era social-class transmission, then education-level
    regression toward the era mean (design spec Sezione 5).

    Two strictly ordered steps:

    1. `template["social_inheritance"]["class_rule"]` selects one of four
       branches -- `patrilineal_rigid`, `clark_regression`,
       `becker_tomes_elasticity_0.4`, `meritocratic` (see the per-branch
       helpers for citations and formulas). An unrecognized `class_rule`
       logs a warning and falls back to `patrilineal_rigid` rather than
       raising, matching this module's "never crash the birth pipeline on
       template data" posture (see `evaluate_derived_formula`'s
       fractional-tail handling in `resolve_birth_attributes` for the same
       philosophy applied elsewhere).
    2. Every branch is followed by the education-level regression (see
       `_regress_education_level`), using
       `template["social_inheritance"]["education_regression_rho"]` and
       `template["social_inheritance"].get("era_mean_education",
       DEFAULT_ERA_MEAN_EDUCATION)`.

    `zone_class_mean` is supplied by the caller as the mean class rank
    (on the `_EXTENDED_CLASS_RANK` scale) for the child's zone; this
    function does not compute it.

    This function mutates `child` in place (`social_class` and
    `education_level`) but never calls `child.save()` -- persistence is
    the caller's responsibility, matching `apply_trait_inheritance`'s
    contract. All randomness is drawn from the passed `rng`
    (`becker_tomes_elasticity_0.4` is the only branch that consumes a
    draw); no global state, no set iteration.

    Args:
        child: the newborn Agent instance (need not be saved yet).
        mother: the mother Agent instance, or None if unresolved.
        father: the father Agent instance, or None if unresolved.
        template: a demography era template dict carrying at least
            `social_inheritance.class_rule` and
            `social_inheritance.education_regression_rho`.
        zone_class_mean: mean class rank of the child's zone.
        rng: a random.Random-compatible instance exposing `.gauss(mu,
            sigma)`.
    """
    social_inheritance = template["social_inheritance"]
    class_rule = social_inheritance["class_rule"]

    if class_rule == "patrilineal_rigid":
        _apply_patrilineal_rigid(child, mother, father)
    elif class_rule == "clark_regression":
        _apply_clark_regression(child, mother, father, zone_class_mean)
    elif class_rule == "becker_tomes_elasticity_0.4":
        _apply_becker_tomes(child, mother, father, zone_class_mean, rng)
    elif class_rule == "meritocratic":
        _apply_meritocratic(child, mother, father)
    else:
        logger.warning(
            "Unknown social_inheritance class_rule %r; falling back to patrilineal_rigid",
            class_rule,
        )
        _apply_patrilineal_rigid(child, mother, father)

    rho = social_inheritance["education_regression_rho"]
    era_mean_education = social_inheritance.get("era_mean_education", DEFAULT_ERA_MEAN_EDUCATION)
    child.education_level = _regress_education_level(mother, father, rho, era_mean_education)


# ---------------------------------------------------------------------------
# Birth-pipeline entry point (Plan 3, T014/T015, user story 1): wires the
# three independent inheritance mechanisms above behind a single call and a
# single deterministic RNG stream.
# ---------------------------------------------------------------------------


def _compute_zone_class_mean(zone: Any) -> float:
    """Mean class rank (on `_EXTENDED_CLASS_RANK`) of living agents in `zone`.

    Single query: `.values_list("social_class", flat=True)` fetches only the
    `social_class` column, avoiding both full Agent instantiation and any
    N+1 pattern -- every agent's class in the zone is read in one round
    trip. Filters `is_alive=True`, matching the dominant codebase convention
    for "current living population" queries (e.g. `couple.py`,
    `fertility.py`).

    Empty-zone guard: a zone with no living agents (a brand-new zone, or
    one whose entire prior population has died) has no well-defined
    arithmetic mean. Falls back to `_UNKNOWN_CLASS_FALLBACK_RANK` -- the
    "working" rank, the same fallback `_class_rank` itself uses for a
    single unrecognized label -- so `apply_social_inheritance`'s
    zone-mean-dependent branches (`clark_regression`,
    `becker_tomes_elasticity_0.4`) always receive a well-defined float and
    never need a special case of their own for an empty zone.
    """
    from epocha.apps.agents.models import Agent

    class_values = Agent.objects.filter(zone=zone, is_alive=True).values_list(
        "social_class", flat=True
    )
    ranks = [_class_rank(value) for value in class_values]
    if not ranks:
        return float(_UNKNOWN_CLASS_FALLBACK_RANK)
    return sum(ranks) / len(ranks)


def apply_inheritance_at_birth(
    child: Any, mother: Any, father: Any, simulation: Any, tick: int
) -> None:
    """Birth-pipeline entry point: apply every inheritance mechanism to a newborn.

    The single composable entry point a birth calls (design spec Sezione
    4/5, "Responsibility contract"; Plan 3 user story 1). Wires together
    this module's three independent building blocks --
    `apply_trait_inheritance`, `resolve_birth_attributes`,
    `apply_social_inheritance` -- so a caller (the Plan 4 birth
    orchestrator) does not need to know their internal ordering or share
    RNG state manually across them.

    Fixed step order (mandatory, not incidental -- see "RNG stream" below):

    1. `apply_trait_inheritance` -- polygenic biological traits (Falconer &
       Mackay 1996, ch. 8) and derived-trait formulas (e.g. `cunning`).
    2. `resolve_birth_attributes` -- gender and sexual orientation, exactly
       two `rng.random()` draws.
    3. `apply_social_inheritance` -- social_class transmission (one of four
       per-era class rules) and education_level regression toward the era
       mean.

    RNG stream: all three steps share a SINGLE `random.Random` instance,
    drawn once via `demography.rng.get_seeded_rng(simulation, tick,
    phase="inheritance")`, so together they consume one continuous,
    deterministic sequence rather than three independently-seeded ones.
    Changing the call order above would change which draw lands on which
    step and silently break bit-for-bit reproducibility across identically
    (simulation, tick)-seeded calls -- the same reproducibility contract
    `apply_trait_inheritance` and `resolve_birth_attributes` each document
    individually for their own internal draws.

    Template resolution: `simulation.config.get("demography_template",
    "pre_industrial_christian")` then `template_loader.load_template(...)`,
    with no try/except around the lookup -- matching how
    `couple.resolve_pair_bond_intents` / `couple.resolve_separate_intents`
    (this app's other mandatory, non-skippable per-tick template lookups)
    resolve their own template. A birth is not an optional action a caller
    can choose to skip the way `avoid_conception` is in
    `simulation.engine`; a misconfigured `demography_template` name is a
    configuration error that must surface immediately as a raised
    exception, not one this function silently papers over with a fallback
    template that would produce scientifically wrong inheritance under a
    mislabeled era.

    zone_class_mean: computed once via `_compute_zone_class_mean(mother.zone)`
    -- the child's zone is the mother's zone (a newborn has no location
    history of its own) -- before any of the three steps run, since
    `apply_social_inheritance` needs it and the query has no RNG
    interaction with the deterministic stream above.

    wealth: `child.wealth` is set to 0.0 unconditionally. A newborn
    inherits nothing financially at the moment of birth; wealth transfer
    from a deceased parent's estate (`economic_inheritance` in the era
    template) is a separate mechanism triggered at death, not birth, and is
    scoped to a later task.

    zone: `child.zone = mother.zone`, matching `Agent.zone`'s own
    help_text ("Current zone (denormalized for performance)") -- a newborn
    is physically located with its mother at birth.

    No-save contract: this function mutates `child` (and only `child`) in
    place and never calls `child.save()`, matching the contract already
    established by `apply_trait_inheritance` and `apply_social_inheritance`.
    Persistence stays the caller's responsibility, keeping this composable
    with however the Plan 4 orchestrator sequences and batches the birth
    pipeline (e.g. bulk-creating several newborns in one query).

    Args:
        child: the newborn Agent instance (need not be saved yet).
        mother: the mother Agent instance. A birth always has a mother;
            `mother.zone` supplies both the child's zone and the
            zone_class_mean query target.
        father: the father Agent instance, or None if unresolved -- the
            single-parent fallback already supported by every downstream
            mechanism this function calls.
        simulation: the Simulation instance; supplies `.config` (read for
            the `demography_template` key) and is passed through to
            `get_seeded_rng`.
        tick: the current simulation tick, passed through to
            `get_seeded_rng`.

    Raises:
        FileNotFoundError, ValueError: propagated unchanged from
            `template_loader.load_template` when `simulation.config`'s
            `demography_template` name does not resolve to a template file
            on disk, or fails the loader's own schema validation.
    """
    from epocha.apps.demography.template_loader import load_template

    template_name = simulation.config.get("demography_template", "pre_industrial_christian")
    template = load_template(template_name)

    zone_class_mean = _compute_zone_class_mean(mother.zone)

    rng = get_seeded_rng(simulation, tick, phase="inheritance")

    apply_trait_inheritance(child, mother, father, template, rng)

    gender, orientation = resolve_birth_attributes(template, rng)
    child.gender = gender
    child.sexual_orientation = orientation

    apply_social_inheritance(child, mother, father, template, zone_class_mean, rng)

    child.wealth = 0.0
    child.zone = mother.zone


# ---------------------------------------------------------------------------
# Heir resolution (Plan 3, T016/T017, user story 2 -- estate/succession).
# Resolves WHO occupies each category of the heir-priority ladder (design
# spec Sezione 5, "Ereditarietà economica alla morte"). Does not decide HOW
# the estate is split among the resolved heirs -- that is a separate,
# later mechanism (the per-era primogeniture / equal_split / shari'a /
# matrilineal / nationalized distribution rules, Plan 3 T019+).
# ---------------------------------------------------------------------------


def _resolve_spouse_heirs(deceased: Any) -> list:
    """The deceased's surviving partner, from their active Couple.

    Design spec Sezione 5, heir priority item 1: "Coniuge sopravvissuto
    (tramite Couple attiva)". Reuses `couple.active_couple_for` rather than
    querying `Couple` directly here -- the couple-membership query is
    already centralized there (`Q(agent_a=agent) | Q(agent_b=agent),
    dissolved_at_tick__isnull=True`), and duplicating it in this module
    would violate DRY and risk drifting from that definition.

    The partner is whichever of `couple.agent_a` / `couple.agent_b` is not
    the deceased. Side comparison uses the `_id` attributes (already loaded
    with the `Couple` instance, no extra query) rather than the FK
    descriptors themselves, so determining which side is the deceased never
    triggers a query. Once the non-deceased side is identified, accessing
    it (`couple.agent_a` or `couple.agent_b`) issues exactly one query to
    fetch the partner `Agent` row -- never both sides, since the other side
    is never touched.

    Handles the defensive case where the identified side is already `None`
    (a couple with the deceased-side FK nulled by an earlier
    `dissolve_on_death` call is no longer "active" under
    `active_couple_for`'s `dissolved_at_tick__isnull=True` filter, so this
    path is not reachable in the current call sequence; kept as a guard
    against a future caller composing this differently) -- returns an empty
    list rather than raising.

    Only a LIVING partner counts as an heir (a partner who died in the same
    tick, before their own `dissolve_on_death` ran, must not receive an
    estate on the way to their own death being resolved).

    Query cost: 1 query (`active_couple_for`) plus, only when an active
    couple is found, 1 more query to fetch the partner's `Agent` row. 0
    queries beyond the first when there is no active couple.
    """
    from epocha.apps.demography.couple import active_couple_for

    couple = active_couple_for(deceased)
    if couple is None:
        return []

    if couple.agent_a_id == deceased.id:
        partner = couple.agent_b
    elif couple.agent_b_id == deceased.id:
        partner = couple.agent_a
    else:
        # Neither side matches the deceased -- see the "defensive case" note
        # above. Not reachable via active_couple_for's own filter today.
        partner = None

    if partner is None or not partner.is_alive:
        return []
    return [partner]


def _resolve_children_heirs(deceased: Any) -> list:
    """Living children of the deceased, via EITHER parentage FK.

    Design spec Sezione 5, heir priority item 2: "Figli (tramite
    parent_agent + other_parent_agent)". A child is linked through
    `Agent.parent_agent` (mother, by Epocha convention) OR
    `Agent.other_parent_agent` (father); both routes count, since a
    deceased agent may be recorded as either parent depending on which
    parentage slot the birth pipeline assigned.

    Ordered oldest-first by `birth_tick` ascending (primogeniture, the
    default `economic_inheritance.rule` in every era template, depends on
    this order to pick "the eldest surviving heir"), tie-broken by `id` for
    a total, deterministic order when two children share a `birth_tick`.

    Query cost: exactly 1 query.
    """
    from epocha.apps.agents.models import Agent

    return list(
        Agent.objects.filter(
            Q(parent_agent=deceased) | Q(other_parent_agent=deceased),
            is_alive=True,
        ).order_by("birth_tick", "id")
    )


def _resolve_sibling_heirs(deceased: Any) -> list:
    """Living siblings of the deceased: agents sharing at least one
    non-null parent, excluding the deceased itself.

    Design spec Sezione 5, heir priority item 3, describes this narrowly as
    "Fratelli (parent_agent condiviso)" -- a shared mother only. This
    implementation deliberately broadens the match to either parentage FK
    (`parent_agent` OR `other_parent_agent` shared with the deceased's own
    corresponding parent), so a half-sibling who shares only the father
    (`other_parent_agent`) is also found. Documented broadening, not a
    contradiction: excluding known half-siblings from an estate ladder
    whose next fallback is "no heir at all -> government treasury" would be
    a worse simplification than widening the match.

    Reads `deceased.parent_agent_id` / `deceased.other_parent_agent_id`
    directly -- both already loaded as plain FK id columns on the passed
    instance, so this costs no query of its own.

    Query cost: exactly 1 query (0 when the deceased has no recorded
    parent at all, since there is then no basis to compare against).
    """
    from epocha.apps.agents.models import Agent

    parent_ids = {
        pid for pid in (deceased.parent_agent_id, deceased.other_parent_agent_id) if pid is not None
    }
    if not parent_ids:
        return []

    sibling_filter = Q(parent_agent_id__in=parent_ids) | Q(other_parent_agent_id__in=parent_ids)
    return list(
        Agent.objects.filter(sibling_filter, is_alive=True)
        .exclude(id=deceased.id)
        .order_by("birth_tick", "id")
    )


def _resolve_extended_family_heirs(deceased: Any, excluded_ids: set[int]) -> list:
    """Living descendants of the deceased's grandparents, bounded to two
    generations down from them -- aunts/uncles and first cousins.

    Design spec Sezione 5, heir priority item 4: "Famiglia estesa (lineage
    di nonno, fino a 2 generazioni)" -- grandparent lineage, up to two
    generations. Read as: reach the grandparent level (two generations up
    from the deceased), then walk down that lineage for up to two more
    generations, which lands back on the deceased's own generation:

    1. Grandparents (2 generations up): the parents of the deceased's own
       `parent_agent` / `other_parent_agent`.
    2. Aunts/uncles (1 generation down from the grandparents): the
       grandparents' children, excluding the deceased's own parents (who
       are not "extended" family).
    3. First cousins (2 generations down from the grandparents, the same
       generation as the deceased): the aunts/uncles' children.

    The traversal deliberately stops at first cousins -- it does not walk
    to great-aunts/uncles, second cousins, or a cousin's own children.
    Bounding the depth here is what keeps the query count independent of
    family size (see the cost note below), and matches the "up to 2
    generations" ceiling from the design spec.

    Returns an empty list when the deceased has no recorded parent at all
    (no basis to find a grandparent), or when neither recorded parent has
    a recorded parent of their own (no grandparent found).

    `excluded_ids` removes agents already counted under an earlier category
    in this same `resolve_heirs` call (children, siblings) -- defensive:
    the aunt/cousin traversal above is structurally disjoint from children
    and siblings, but a future template with unusual pedigree data should
    not double-count an heir across categories.

    Query cost: up to 3 queries -- (1) the deceased's parents' own parent
    ids (a `values_list` over at most 2 rows), (2) the aunts/uncles fetch,
    (3) the cousins fetch (skipped, 0 extra queries, when no aunts/uncles
    were found). 0 queries when the deceased has no recorded parent; 1
    query when no grandparent is found. Every query filters on a small,
    already-resolved id set (parents, then grandparents, then
    aunts/uncles) rather than scanning the population, so the cost does not
    grow with total agent count.
    """
    from epocha.apps.agents.models import Agent

    parent_ids = [pid for pid in (deceased.parent_agent_id, deceased.other_parent_agent_id) if pid]
    if not parent_ids:
        return []

    grandparent_id_pairs = Agent.objects.filter(id__in=parent_ids).values_list(
        "parent_agent_id", "other_parent_agent_id"
    )
    grandparent_ids = {gid for pair in grandparent_id_pairs for gid in pair if gid is not None}
    if not grandparent_ids:
        return []

    aunts_uncles = list(
        Agent.objects.filter(
            Q(parent_agent_id__in=grandparent_ids) | Q(other_parent_agent_id__in=grandparent_ids)
        ).exclude(id__in=parent_ids)
    )
    aunt_uncle_ids = {agent.id for agent in aunts_uncles}

    cousins: list = []
    if aunt_uncle_ids:
        cousins = list(
            Agent.objects.filter(
                Q(parent_agent_id__in=aunt_uncle_ids) | Q(other_parent_agent_id__in=aunt_uncle_ids)
            )
        )

    candidates = {agent.id: agent for agent in aunts_uncles + cousins}
    for excluded_id in excluded_ids | {deceased.id}:
        candidates.pop(excluded_id, None)

    def _sort_key(agent: Any) -> tuple[int, int]:
        birth_tick = agent.birth_tick if agent.birth_tick is not None else 0
        return (birth_tick, agent.id)

    living = [agent for agent in candidates.values() if agent.is_alive]
    living.sort(key=_sort_key)
    return living


def resolve_heirs(deceased: Any, template: dict) -> dict[str, list]:
    """Resolve every category of the heir-priority ladder for `deceased`.

    Design spec Sezione 5, "Ereditarietà economica alla morte": the ladder
    is `template["economic_inheritance"]["heir_priority"]`, identical
    across all five current era templates --
    `["spouse", "children", "siblings", "extended_family", "government"]`.
    This function resolves WHO occupies each category; it does not decide
    HOW the estate is split among them (a separate mechanism, the per-era
    `rule` -- primogeniture, equal_split, shari'a, matrilineal, nationalized
    -- scoped to a later task) or apply estate tax.

    Returns a dict keyed by every category present in `heir_priority`
    EXCEPT "government": only "spouse", "children", "siblings", and
    "extended_family" ever appear as keys, each mapped to a list of LIVING
    heirs in a deterministic order (birth_tick ascending, id tie-break; see
    each category's own resolver for the exact ordering rationale).
    "government" is never a key holding heir objects -- it is the ladder's
    terminal fallback, and is represented structurally by every OTHER
    category resolving to an empty list, not by a key of its own. A
    category absent from `heir_priority` in a future custom template is
    likewise simply absent from the returned dict, so callers can always
    branch with `heirs.get(category, [])` or an explicit `"category" in
    heirs` check without ever hitting `KeyError` for a category the
    template actually declares.

    Category order in `heir_priority` is followed exactly, and matters for
    one dependency: by the time "extended_family" is processed, whatever
    "children" and "siblings" already resolved to (if those categories
    appear earlier in `heir_priority`, as they do in every current
    template) is passed to `_resolve_extended_family_heirs` as an exclusion
    set, so an heir already counted under an earlier category is never
    double-counted under "extended_family". An unrecognized category name
    is logged at WARNING level and skipped, matching this module's
    established "never crash the birth/death pipeline on template data"
    posture (see `apply_social_inheritance`'s unknown-`class_rule`
    handling).

    Query cost contract (efficiency requirement -- this runs once per
    death today, and the Plan 4 death orchestrator will call it every
    tick): every category's query count is bounded independently of family
    size (see each resolver's own docstring for its exact cost). Worst
    case, with every category present and populated: 2 (spouse) + 1
    (children) + 1 (siblings) + 3 (extended_family) = 7 queries total.
    Categories with no matching heirs cost fewer queries (e.g. 0 extra
    queries for spouse when there is no active couple, 0 total for
    extended_family when the deceased has no recorded parent).

    Args:
        deceased: the deceased Agent instance. Must be saved (have a
            primary key) -- every resolver below compares against
            `deceased.id`.
        template: a demography era template dict as returned by
            `template_loader.load_template`, or an equivalent dict carrying
            at least `economic_inheritance.heir_priority`.

    Returns:
        A dict mapping each `heir_priority` category (except "government")
        to a list of living `Agent` heirs, always including the key even
        when the list is empty.
    """
    heir_priority = template["economic_inheritance"]["heir_priority"]
    heirs: dict[str, list] = {}

    for category in heir_priority:
        if category == "spouse":
            heirs["spouse"] = _resolve_spouse_heirs(deceased)
        elif category == "children":
            heirs["children"] = _resolve_children_heirs(deceased)
        elif category == "siblings":
            heirs["siblings"] = _resolve_sibling_heirs(deceased)
        elif category == "extended_family":
            already_counted_ids = {
                agent.id for agent in heirs.get("children", []) + heirs.get("siblings", [])
            }
            heirs["extended_family"] = _resolve_extended_family_heirs(deceased, already_counted_ids)
        elif category == "government":
            # Terminal fallback: represented by every other category being
            # empty, never by a key of its own -- see the docstring above.
            continue
        else:
            logger.warning("Unknown heir_priority category %r; skipped", category)

    return heirs


# ---------------------------------------------------------------------------
# Estate tax (Plan 3, T018/T019, user story 2 -- estate/succession). Routes
# the era's flat estate tax to the government treasury before the remainder
# is split among resolve_heirs's resolved heirs -- a separate, later
# distribution step (design spec Sezione 5, per-era primogeniture /
# equal_split / shari'a / matrilineal / nationalized rules, T020+).
# ---------------------------------------------------------------------------


def apply_estate_tax(
    total_estate_value: float, rate: float, government: Any, primary_currency_code: str
) -> float:
    """Route the era's estate tax to the government treasury, return the remainder.

    Design spec Sezione 5, "Ereditarietà economica alla morte": each era
    template's `economic_inheritance.estate_tax_rate` is a flat tax on the
    deceased's total estate value, applied before the remainder is split
    among the heirs `resolve_heirs` already resolved. Verified across all
    five current era templates: pre_industrial_christian 0.0,
    pre_industrial_islamic 0.0, industrial 0.15, modern_democracy 0.40,
    sci_fi 0.0. The modern-democracy rate of 0.40 corresponds to the
    top-bracket historical estate/inheritance tax rates documented in
    Piketty, T. (2014), "Capital in the Twenty-First Century", Harvard
    University Press, tables 14.1-14.2 (top marginal estate tax rates
    across France, the UK, the US, and Germany over the 20th century). The
    pre-industrial rate of 0.0 is not a claim that pre-industrial elites
    paid no death duties at all -- feudal relief payments and analogous
    transfer-of-power levies are modelled separately in the economy layer
    rather than folded into this "estate tax" line item, so this function
    correctly routes nothing for those eras without under-modelling the
    underlying phenomenon; it is simply out of this function's scope.

    Caller supplies `rate` (read from the resolved era template) and
    `primary_currency_code` (the simulation's primary currency code, the
    same code `add_to_treasury`'s other callers -- tax, expropriation --
    already use); this function does not resolve either from the template
    or the simulation itself, keeping it a pure two-line accounting step
    the caller composes with `resolve_heirs`.

    tax_revenue = total_estate_value * rate, credited to `government`'s
    treasury under `primary_currency_code` via `add_to_treasury` (imported
    lazily inside this function -- this module's established pattern for
    cross-app imports, see `_compute_zone_class_mean`,
    `_resolve_spouse_heirs`, `apply_inheritance_at_birth`'s
    `template_loader` import). The returned remainder,
    `total_estate_value * (1.0 - rate)`, is the amount later split among
    the resolved heirs.

    Conservation (load-bearing for whitepaper Sezione 4.2/4.8's accounting
    invariant): remainder + tax_revenue reproduces `total_estate_value`,
    exactly up to floating-point rounding. Neither value is rounded,
    clamped, or otherwise adjusted beyond what the multiplication itself
    introduces -- doing so would silently create or destroy money relative
    to the estate's true value.

    Degenerate inputs are guarded explicitly rather than left to produce
    nonsensical output, matching this module's established
    never-crash-on-template-data posture (see `apply_social_inheritance`'s
    unknown-`class_rule` fallback and `resolve_heirs`'s unknown-category
    skip):

    - `rate` outside [0, 1]: a template authoring error (e.g. a rate typed
      as a percentage, "40" instead of "0.40"). Logged at WARNING and
      clamped into [0, 1] -- a single malformed template value must not
      abort estate settlement for a real death.
    - `total_estate_value <= 0.0`: a well-formed settled estate is never
      negative; a non-positive value is a data anomaly (e.g. a caller
      passing an unfloored negative net worth). Treated as a zero estate --
      no treasury credit is issued and 0.0 is returned -- rather than
      letting a negative `total_estate_value * rate` silently debit the
      treasury through `add_to_treasury`.

    Args:
        total_estate_value: the deceased's total estate value, in the
            simulation's primary currency, before tax. Non-positive values
            are treated as a zero estate (see above): no treasury credit,
            remainder 0.0.
        rate: the era's `economic_inheritance.estate_tax_rate`, supplied by
            the caller from the resolved era template. Clamped into [0, 1]
            if the template value is out of range.
        government: the simulation's Government instance to credit.
        primary_currency_code: the simulation's primary currency code,
            supplied by the caller.

    Returns:
        The inheritable remainder: `total_estate_value * (1.0 - rate)` for
        a positive estate value, or 0.0 when `total_estate_value` is
        non-positive.
    """
    if rate < 0.0 or rate > 1.0:
        logger.warning(
            "economic_inheritance.estate_tax_rate %r outside [0, 1]; clamping before use",
            rate,
        )
        rate = max(0.0, min(1.0, rate))

    if total_estate_value <= 0.0:
        return 0.0

    tax_revenue = total_estate_value * rate
    remainder = total_estate_value * (1.0 - rate)

    from epocha.apps.world.government import add_to_treasury

    add_to_treasury(government, primary_currency_code, tax_revenue)

    return remainder


# ---------------------------------------------------------------------------
# Estate distribution (Plan 3, T020/T021, user story 2 -- estate/succession).
# Decides HOW the inheritable remainder `apply_estate_tax` returns is split
# among the heirs `resolve_heirs` already resolved -- the per-era rule named
# by `template["economic_inheritance"]["rule"]` (design spec Sezione 5:
# primogeniture, equal_split, shari'a, matrilineal, nationalized). Every
# function below is PURE: no `.save()`, no mutation of any heir Agent, no
# ORM writes at all (only the read-only queries the matrilineal rule needs
# to resolve nieces/nephews). Persistence -- crediting `Agent.wealth` from
# the returned allocation -- is the caller's responsibility, a later task
# (T029's `process_inheritance_batch`), matching the no-save contract
# `apply_trait_inheritance` / `apply_social_inheritance` already establish
# elsewhere in this module.
# ---------------------------------------------------------------------------


def _allocate_with_exact_remainder(
    ordered_shares: list[tuple[int, float]], total: float
) -> dict[int, float]:
    """Assign each entry its own raw share except the LAST, which absorbs
    whatever is left of `total` after the others -- the technique that
    makes the conservation contract (`sum(allocation.values()) == total`,
    exactly up to floating-point representation) hold for every succession
    rule below that splits an amount across more than one heir.

    Why this is needed: a raw per-heir share (`total / n`, or the
    units-weighted variant in `_split_two_to_one`) is itself subject to
    floating-point rounding, and summing `n` independently-rounded shares
    does not, in general, reproduce `total` bit-for-bit -- the classic
    "divide a total into N parts" rounding trap (e.g. `10_000.0 / 3 ==
    3333.3333333333335`, and three such shares summed drift from
    `10_000.0` by roughly 1e-12). Instead of accepting that drift, the LAST
    entry in `ordered_shares` is assigned `total - running_sum(all other
    entries)` rather than its own raw share. This single subtraction makes
    the sum of everything assigned exactly equal to `total`:
    `running_sum + (total - running_sum)` collapses algebraically to
    `total`, and holds to full floating-point precision here because
    `running_sum` and `total` are always the same order of magnitude (the
    former is a fraction of the latter, drawn from the same estate) --
    the pathological cancellation cases of naive `a + (b - a)` arithmetic
    (`a`, `b` of wildly different magnitude) do not arise in this domain.

    `ordered_shares` must already be in the caller's final deterministic
    order -- oldest-first, per this module's established convention (see
    `resolve_heirs`'s child/sibling/extended_family ordering) -- and never
    built from a Python `set`, whose iteration order is not guaranteed and
    would make which heir absorbs the remainder depend on interpreter hash
    seed rather than birth order. The heir LAST in that order is always the
    one that absorbs the remainder; every earlier heir receives exactly its
    own computed raw share.

    Args:
        ordered_shares: a list of (heir_id, raw_share) pairs, already in
            deterministic order.
        total: the amount the returned mapping must sum to exactly.

    Returns:
        A dict mapping each heir_id to its allocated amount; empty when
        `ordered_shares` is empty.
    """
    if not ordered_shares:
        return {}

    allocation: dict[int, float] = {}
    running_sum = 0.0
    for heir_id, raw_share in ordered_shares[:-1]:
        allocation[heir_id] = raw_share
        running_sum += raw_share

    last_id, _ = ordered_shares[-1]
    allocation[last_id] = total - running_sum
    return allocation


def _split_two_to_one(pool: list, amount: float) -> dict[int, float]:
    """Divide `amount` among `pool` so each MALE member receives twice a
    non-male (female or non-binary) member's share -- the general Quranic
    principle "for the male, the equivalent share of two females" (Q4:11),
    part of the classical fara'id inheritance system documented by Powers,
    D.S. (1986), "Studies in Qur'an and Hadith: The Formation of the
    Islamic Law of Inheritance". Used both for the deceased's own
    surviving children (the literal Sezione 5 `shari'a` rule) and, inside
    `_distribute_sharia`, as a documented simplification applying the same
    ratio to the deceased's siblings when there are no children -- standing
    in for the fuller classical residuary ('asaba) hierarchy, which this
    MVP does not model in full.

    NON-BINARY handling: a non-binary member of `pool` is treated as
    non-male, receiving one unit -- the same unit a daughter receives.
    Documented simplification: classical Islamic jurisprudence recognised
    no non-binary status.

    `total_units = 2 * (male count) + 1 * (non-male count)`;
    `unit_value = amount / total_units`. Deterministic: `pool`'s own
    oldest-first order (as every category `resolve_heirs` returns already
    is) is preserved, never re-sorted and never routed through a set. The
    last member of `pool` in that order absorbs the floating-point
    remainder via `_allocate_with_exact_remainder`, so the returned mapping
    sums to `amount` exactly.

    Args:
        pool: a non-empty list of heir Agent instances.
        amount: the amount to divide among them.

    Returns:
        A dict mapping each member's id to its allocated share.
    """
    from epocha.apps.agents.models import Agent

    total_units = sum(2 if agent.gender == Agent.Gender.MALE else 1 for agent in pool)
    unit_value = amount / total_units

    ordered_shares = [
        (agent.id, (2 if agent.gender == Agent.Gender.MALE else 1) * unit_value) for agent in pool
    ]
    return _allocate_with_exact_remainder(ordered_shares, amount)


def _eldest_male_then_female(pool: list) -> Any:
    """The eldest MALE member of `pool`; if there is none, the eldest
    non-male member (female or non-binary -- "ordered together", see
    `_distribute_primogeniture`'s NON-BINARY handling); `None` when `pool`
    is empty.

    `pool` must already be in oldest-first order (every category
    `resolve_heirs` returns already is) -- this function never re-sorts.
    Any male in `pool` outranks every non-male regardless of relative age
    (the first loop returns on the first male found, wherever it sits in
    birth order); among a pool with no male at all, `pool[0]` -- the
    eldest by construction -- is the answer.
    """
    from epocha.apps.agents.models import Agent

    for agent in pool:
        if agent.gender == Agent.Gender.MALE:
            return agent
    if pool:
        return pool[0]
    return None


def _distribute_primogeniture(heirs: dict[str, list], inheritable: float) -> dict[int, float]:
    """100% of `inheritable` to a single heir, cascading down the ladder
    (Blackstone, W. (1765), "Commentaries on the Laws of England"):

    1. The eldest surviving SON (`heirs["children"]`, filtered to
       `Agent.Gender.MALE`).
    2. If there is no son, the eldest surviving DAUGHTER.
    3. If there are no children at all, the surviving spouse
       (`heirs["spouse"]`; at most one entry, per this module's monogamy
       assumption -- see `_resolve_spouse_heirs`).
    4. If there is no spouse either, cascade to `heirs["siblings"]`,
       applying the SAME son-then-daughter preference one rung further
       down the heir-priority ladder. This sibling-level cascade is a
       documented extension beyond Blackstone's own text (which addresses
       lineal descent, not the collateral line): it applies the identical
       eldest-male-preference test for internal consistency, rather than
       leaving the estate stranded (and the conservation contract broken)
       when the deceased has neither children nor a spouse but does have
       living siblings.

    NON-BINARY handling: a non-binary heir is ordered together with the
    female heirs at every tier (step 2's "daughter" pool, step 4's
    "sister" pool) -- an older non-binary heir outranks a younger female
    heir and vice versa, purely by birth order within that combined pool
    (see `_eldest_male_then_female`). Documented pragmatic simplification:
    pre-modern inheritance law had no category for non-binary identity;
    this module records the choice explicitly rather than silently
    defaulting non-binary heirs to a category.

    Returns an empty allocation (the treasury fallback) when every tier is
    exhausted -- no children, no spouse, no siblings.
    """
    children = heirs.get("children", [])
    spouse = heirs.get("spouse", [])
    siblings = heirs.get("siblings", [])

    heir = _eldest_male_then_female(children)
    if heir is not None:
        return {heir.id: inheritable}

    if spouse:
        return {spouse[0].id: inheritable}

    heir = _eldest_male_then_female(siblings)
    if heir is not None:
        return {heir.id: inheritable}

    return {}


def _distribute_equal_split(heirs: dict[str, list], inheritable: float) -> dict[int, float]:
    """Cash divided equally among surviving children, with the spouse
    receiving a share equal to one child's (Napoleonic Code, 1804): with N
    children and a spouse, there are N+1 equal shares.

    NON-BINARY handling: every heir receives the same equal share
    regardless of gender -- no distinction is made.

    Recipient order (children in their own oldest-first order, spouse
    last) is fixed and deterministic, never a set; see
    `_allocate_with_exact_remainder` for why the LAST recipient in that
    order -- the spouse when present, otherwise the youngest child --
    absorbs the floating-point remainder so the total conserves exactly.

    Returns an empty allocation (the treasury fallback) when there are
    neither children nor a spouse.
    """
    children = heirs.get("children", [])
    spouse = heirs.get("spouse", [])
    recipients = [*children, *spouse]

    if not recipients:
        return {}

    share = inheritable / len(recipients)
    ordered_shares = [(agent.id, share) for agent in recipients]
    return _allocate_with_exact_remainder(ordered_shares, inheritable)


def _distribute_sharia(heirs: dict[str, list], inheritable: float) -> dict[int, float]:
    """Spouse receives 1/8 of `inheritable` when the deceased leaves
    children, otherwise 1/4; the remainder is divided among the children
    with each son receiving twice a daughter's share (Powers, D.S. (1986),
    "Studies in Qur'an and Hadith: The Formation of the Islamic Law of
    Inheritance" -- the fixed-share-plus-residuary structure of the
    classical fara'id system; see `_split_two_to_one` for the 2:1 ratio's
    own citation, Q4:11).

    NON-BINARY handling: a non-binary child receives a daughter's share (1
    unit). Documented simplification: classical Islamic jurisprudence
    recognised no non-binary status.

    Residuary cascade when the deceased leaves NO children -- a documented
    simplification of the fuller classical residuary ('asaba) hierarchy,
    which this MVP does not model in full (flagged here explicitly rather
    than silently invented; the original design spec itself only states
    "il resto cascade per regole coraniche" without specifying the
    mechanism). Mirrors `_distribute_primogeniture`'s own cascade depth
    (children -> spouse -> siblings, no further) for consistency between
    this module's two cascading rules:

    1. If there are living siblings (`heirs["siblings"]`), they divide the
       residual under the SAME 2:1 male:non-male ratio children would have
       used -- siblings are the closest real analogue to the classical
       'asaba (residuary agnate) heirs, the next priority tier after
       children in the actual fara'id system.
    2. Else, if there is a spouse and no sibling was found, the spouse
       absorbs the ENTIRE residual on top of their own fixed fraction
       (mirroring the real "radd" -- return of residue -- effect for a
       sole surviving Quranic heir): in this one case the spouse's total
       allocation is the WHOLE `inheritable` amount, not literally 1/4,
       since there is no residuary heir left to receive the other 3/4.
    3. Else (no heir of any kind), the allocation is empty -- the treasury
       fallback.

    The spouse's own fixed-fraction entry (1/8 or 1/4) is exact ONLY when
    step 1 actually receives the rest; step 2 is the degenerate case where
    the spouse is topped up beyond that fraction.

    Conservation: `spouse_amount + sum(residuary allocation) ==
    inheritable` exactly (see `_allocate_with_exact_remainder`, used
    inside `_split_two_to_one` for the residuary split).

    Returns an empty allocation (the treasury fallback) when there is
    neither a spouse, nor children, nor siblings.
    """
    children = heirs.get("children", [])
    spouse = heirs.get("spouse", [])
    siblings = heirs.get("siblings", [])

    spouse_fraction = 0.125 if children else 0.25
    spouse_amount = inheritable * spouse_fraction if spouse else 0.0
    residual = inheritable - spouse_amount

    if children:
        pool = children
    elif siblings:
        pool = siblings
    else:
        pool = []

    allocation: dict[int, float] = {}
    if pool:
        allocation = _split_two_to_one(pool, residual)
        if spouse:
            allocation[spouse[0].id] = spouse_amount
    elif spouse:
        # No sibling found either: the spouse is the sole heir and
        # absorbs the whole residual too (see docstring, step 2).
        allocation[spouse[0].id] = spouse_amount + residual

    return allocation


def _resolve_matrilineal_heirs(heirs: dict[str, list]) -> list:
    """Living children of the deceased's SISTERS (Schneider, D.M. & Gough,
    K. (1961), "Matrilineal Kinship") -- a relationship `resolve_heirs`'s
    own category ladder does not reach: its `extended_family` traversal
    walks the deceased's own grandparent lineage to aunts/uncles and first
    cousins, never down through a SIBLING's own descendants (nieces and
    nephews). Resolved here via a dedicated query per sister.

    "Sisters" are the FEMALE entries of `heirs["siblings"]`
    (`Agent.Gender.FEMALE` exactly) -- a non-binary sibling is not treated
    as an ambiguous match on the sister-selection side, since the
    matrilineal descent link's biological premise (a shared mother)
    requires an unambiguous sister to trace through. This is the
    sister-selection half of matrilineal's NON-BINARY handling; the
    child-selection half (below) needs no gender distinction at all.

    Each sister's living children are resolved by reusing
    `_resolve_children_heirs` -- despite that function's `deceased`
    parameter name (chosen for its original call site inside
    `resolve_heirs`), its body has no special-casing on "the deceased" as
    a concept: it purely finds the living children of whatever Agent
    instance is passed. Reusing it here for an arbitrary sister avoids
    duplicating the same `Q(parent_agent=X) | Q(other_parent_agent=X)`
    query pattern, per this module's DRY convention.

    Results from every sister are pooled and de-duplicated by id (defensive:
    two separate per-sister queries would return distinct Python objects
    for the same database row if a child were somehow reachable through two
    sisters), then sorted oldest-first by `(birth_tick, id)` -- built via a
    dict, then sorted explicitly, never through a Python `set`, so the
    final order is deterministic and reproducible.

    Returns an empty list when there are no sisters, or when no sister has
    a living child.
    """
    from epocha.apps.agents.models import Agent

    sisters = [agent for agent in heirs.get("siblings", []) if agent.gender == Agent.Gender.FEMALE]
    if not sisters:
        return []

    pooled: dict[int, Any] = {}
    for sister in sisters:
        for child in _resolve_children_heirs(sister):
            pooled[child.id] = child

    def _sort_key(agent: Any) -> tuple[int, int]:
        birth_tick = agent.birth_tick if agent.birth_tick is not None else 0
        return (birth_tick, agent.id)

    return sorted(pooled.values(), key=_sort_key)


def _distribute_matrilineal(heirs: dict[str, list], inheritable: float) -> dict[int, float]:
    """The entire `inheritable` amount passes to the children of the
    deceased's sisters, divided equally (Schneider, D.M. & Gough, K.
    (1961), "Matrilineal Kinship" -- schematic matrilineal succession).

    NON-BINARY handling: a non-binary niece/nephew receives the same equal
    share as any other -- no gender-role distinction is needed on the
    child-selection side, since matrilineal succession here is defined
    purely by biological descent from a sister, not by the heir's own
    gender (see `_resolve_matrilineal_heirs` for the sister-selection
    side's own NON-BINARY handling).

    Note: no era template currently selects the `matrilineal` rule --
    verified across all five current templates under
    `epocha/apps/demography/templates/` (pre_industrial_christian ->
    primogeniture, pre_industrial_islamic -> shari'a, industrial /
    modern_democracy / sci_fi -> equal_split). This rule exists for future
    custom templates and for completeness of the five documented
    succession systems (design spec Sezione 5).

    The deceased's OWN children never receive anything under this rule --
    only `heirs["siblings"]`'s female entries and their descendants are
    ever consulted; `heirs["children"]` is not read here at all.

    Deterministic order (oldest-first by `(birth_tick, id)`, from
    `_resolve_matrilineal_heirs`) is preserved, never a set; the last
    niece/nephew in that order absorbs the floating-point remainder via
    `_allocate_with_exact_remainder`, so the returned mapping sums to
    `inheritable` exactly.

    Returns an empty allocation (the treasury fallback) when the deceased
    has no sister, or no sister has a living child.
    """
    nieces_and_nephews = _resolve_matrilineal_heirs(heirs)
    if not nieces_and_nephews:
        return {}

    share = inheritable / len(nieces_and_nephews)
    ordered_shares = [(agent.id, share) for agent in nieces_and_nephews]
    return _allocate_with_exact_remainder(ordered_shares, inheritable)


def distribute_estate(
    deceased: Any, heirs: dict[str, list], rule: str, inheritable: float
) -> dict[int, float]:
    """Split `inheritable` among the heirs `resolve_heirs` already
    resolved, per the era's `economic_inheritance.rule` (design spec
    Sezione 5): `primogeniture`, `equal_split`, `shari'a`, `matrilineal`,
    `nationalized` -- see each `_distribute_*` helper's own docstring for
    its formula, citation, and NON-BINARY handling.

    Return shape (decision, documented per this module's convention of
    stating non-obvious choices explicitly): the mapping is keyed by each
    heir's `Agent.id` (a plain int), NOT by the Agent instance itself.
    Chosen for consistency with this module's established use of id-keyed
    sets/dicts for heir bookkeeping (`excluded_ids` in `resolve_heirs`,
    `aunt_uncle_ids` and the `candidates` dict in
    `_resolve_extended_family_heirs`), and because an id-keyed mapping is
    trivially and unambiguously summable/comparable by callers and tests
    without depending on Django Model's pk-based `__eq__`/`__hash__`
    semantics holding for every future caller.

    PURITY / no-save contract (CRITICAL for the conservation invariant
    below to be assertable in isolation): this function never calls
    `.save()` and never mutates any heir Agent instance -- it only reads
    `.id`, `.gender`, and (for `matrilineal`) `.birth_tick` off heirs
    already resolved by `resolve_heirs`, plus, for `matrilineal` only,
    issues read-only queries to resolve nieces/nephews. Returning a pure
    allocation mapping, rather than crediting `Agent.wealth` directly, is
    what makes the conservation contract assertable on the returned
    mapping alone, independent of any database state -- crediting the
    heirs' actual `wealth` field is the caller's responsibility (a later
    task, T029's `process_inheritance_batch`).

    CONSERVATION CONTRACT (non-negotiable, load-bearing for whitepaper
    Sezione 4.2/4.8's accounting invariant): for every rule that resolves
    at least one heir, `sum(allocation.values())` equals `inheritable`
    exactly, up to floating-point representation -- see
    `_allocate_with_exact_remainder` for the technique (the last heir in
    each rule's deterministic order absorbs the float remainder rather
    than every heir rounding independently). No value is ever lost or
    fabricated relative to `inheritable`.

    EMPTY ALLOCATION SHAPE: an empty `{}` return means "route the entire
    `inheritable` amount to the treasury", and covers TWO distinct
    situations that look identical on the mapping's shape alone -- the
    caller distinguishes them by the `rule` it already has on hand:
    - `nationalized`: always empty by design (Nove, A. (1969), "An
      Economic History of the USSR" -- Soviet-style expropriation; the
      ENTIRE estate is state property, not merely an untaxed remainder
      nobody claimed).
    - Every other rule, when it happens to resolve NO heir at all (e.g.
      `matrilineal` with no sister, or `primogeniture` / `equal_split` /
      `shari'a` with no children, spouse, or relevant collateral
      relatives): empty because there was genuinely nobody to inherit.

    Unknown `rule`: logged at WARNING and falls back to `equal_split`,
    matching this module's established never-crash-on-template-data
    posture (see `resolve_heirs`'s unknown-category skip and
    `apply_social_inheritance`'s unknown-`class_rule` fallback).

    Args:
        deceased: the deceased Agent instance. Not read by any rule
            today -- every rule derives its allocation purely from
            `heirs` -- kept in the signature for interface symmetry with
            `resolve_heirs(deceased, template)` (whose result is `heirs`,
            this function's own second argument) and so a future
            succession rule needing the deceased's own attributes (e.g.
            an explicit will/testament override) does not require another
            signature change.
        heirs: the dict `resolve_heirs(deceased, template)` returned --
            categories "spouse", "children", "siblings",
            "extended_family", each a list of living heir Agents in
            oldest-first order. A category absent from the dict is
            treated as an empty list (`heirs.get(category, [])`
            throughout every `_distribute_*` helper).
        rule: `template["economic_inheritance"]["rule"]` -- one of
            `primogeniture`, `equal_split`, `shari'a`, `matrilineal`,
            `nationalized`, or an unrecognized string (falls back to
            `equal_split` with a warning).
        inheritable: the amount to distribute -- the remainder
            `apply_estate_tax` already returned after routing the era's
            estate tax to the treasury.

    Returns:
        A dict mapping each allocated heir's `Agent.id` to the amount
        they receive; empty when no heir receives anything (see EMPTY
        ALLOCATION SHAPE above).
    """
    if rule == "primogeniture":
        return _distribute_primogeniture(heirs, inheritable)
    if rule == "equal_split":
        return _distribute_equal_split(heirs, inheritable)
    if rule == "shari'a":
        return _distribute_sharia(heirs, inheritable)
    if rule == "matrilineal":
        return _distribute_matrilineal(heirs, inheritable)
    if rule == "nationalized":
        return {}

    logger.warning("Unknown economic_inheritance rule %r; falling back to equal_split", rule)
    return _distribute_equal_split(heirs, inheritable)


# ---------------------------------------------------------------------------
# Loan transfer (Plan 3, T023, user story 2 -- estate/succession). Reassigns
# the deceased's outstanding CREDITS -- active loans where the deceased was
# the LENDER -- so a death never evaporates money someone else owes the
# deceased. Loans where the deceased was the BORROWER are a separate
# mechanism, entirely out of scope here (see the docstring below).
# ---------------------------------------------------------------------------


def transfer_loans_as_lender(deceased: Any, heirs: dict[str, list]) -> None:
    """Reassign the deceased's active lender-side loans to a living heir,
    or to the banking system when there is none.

    Design spec Sezione 5, "Loans ereditati (come lender)": the deceased's
    outstanding CREDITS (active loans where the deceased is `lender`, i.e.
    money owed TO them) transfer to their heirs under the same distribution
    priority the estate itself uses, rather than following the deceased
    into oblivion -- an asset (a claim on someone else's future repayment)
    must not evaporate merely because its holder died, on the same
    conservation posture `apply_estate_tax` and `distribute_estate` above
    already establish for cash and property.

    Scope (CRITICAL, read before touching this function): only loans where
    `deceased` is `lender` are considered. Loans where `deceased` is
    `borrower` -- the deceased's own DEBTS -- are entirely out of scope
    here; they are a separate mechanism (debt forgiveness / creditor claim
    against the estate) not implemented by this task. Only loans with
    `status="active"` are reassigned -- a `repaid`, `defaulted`, or
    `default_settled` loan has no live balance for the new holder to
    service and is left untouched.

    SPEC AMBIGUITY AND ITS RESOLUTION (flagged explicitly for the phase-6
    adversarial code audit): the design spec contradicts itself on what
    happens when there is no living heir. Sezione 5's own "Loans ereditati"
    paragraph states, in the same breath: "Se la regola non produce eredi
    umani (es. nationalized o nessuna famiglia), il loan trasferisce al
    banking system (lender=None, lender_type="banking") e continua a essere
    servito" -- immediately followed by "Loans agent-to-agent senza eredi
    vengono silenziosamente cancellati a MVP -- limitazione documentata."
    The spec's own FAQ (Sezione "Cosa succede ai loans dove il deceduto era
    il lender?") repeats the same transfer-then-contradict pattern, and
    "Known Limitations" item 9 independently restates the cancellation
    reading in isolation. These two readings cannot both be implemented:
    "transfers to the banking system and keeps being serviced" and
    "silently cancelled" describe mutually exclusive outcomes for the same
    loan. This function implements the BANKING TRANSFER reading, never
    cancellation -- silently cancelling an active credit would destroy
    real value and violate the exact conservation invariant (whitepaper
    Sezione 4.2/4.8, both CONVERGED) that this entire user story exists to
    protect; `apply_estate_tax` and `distribute_estate` conserve every
    unit of the estate's cash value; a heirless loan disappearing outright
    would silently reintroduce the leak this user story closes for cash.
    A future spec revision should reconcile the contradiction in the design
    document itself; until then, this docstring is the authoritative record
    of which reading the code implements and why.

    Heir selection: `heirs` is the dict `resolve_heirs(deceased, template)`
    already returned -- categories in `heir_priority` order (typically
    "spouse", "children", "siblings", "extended_family"), each a list of
    living heirs in the module's established oldest-first order (see
    `resolve_heirs`'s own docstring). This function flattens `heirs` by
    iterating its values in that same insertion order -- never re-sorted,
    never routed through a `set` -- reproducing the identical spouse-first,
    children-oldest-first priority ladder `distribute_estate` already
    applies to the estate's cash. Loans are then assigned ROUND-ROBIN across
    that flattened list (`heir_index = loan_index % len(flattened_heirs)`):
    a documented, deliberately simple policy choice -- the design spec does
    not specify HOW multiple loans should split across multiple heirs
    (only that they "transfer... using the same distribution rule" for the
    single-recipient primogeniture case; round-robin is the natural,
    deterministic generalization to N heirs that guarantees every heir with
    at least one loan-slot receives at least one loan when loans outnumber
    heirs, without requiring this function to re-run a full
    `distribute_estate`-style proportional split for a fundamentally
    different asset class).

    Write path (efficiency requirement, load-bearing once Plan 4 wires this
    into the per-tick death pipeline): exactly ONE `SELECT` (the active
    lender-side loans, materialized into a list) followed by exactly ONE
    `bulk_update` `UPDATE`, regardless of how many loans the deceased held
    as lender -- never a per-loan `.save()` loop, which would make this
    function's cost scale with the deceased's loan-book size instead of
    staying O(1) in query count.

    This function is NOT pure -- unlike `resolve_heirs` and
    `distribute_estate` above, it performs the ORM write itself (via
    `bulk_update`) rather than returning a value for the caller to persist.
    This is a deliberate departure from this module's usual no-save
    contract: a `Loan.lender` FK reassignment has no meaningful "allocation
    mapping" representation the way a cash split does (there is nothing to
    sum or conserve across the return value -- the loan's `principal` /
    `remaining_balance` are untouched), so returning a pure description for
    a separate persistence step would only add indirection without a
    conservation contract to protect.

    Args:
        deceased: the deceased Agent instance. Must be saved (queried by
            `id` against `Loan.lender`).
        heirs: the dict `resolve_heirs(deceased, template)` returned --
            values are lists of living heir Agent instances, in the
            established priority/oldest-first order. An empty dict, or a
            dict whose every value is an empty list, is treated identically
            to "no living heir".

    Returns:
        None. Mutates `Loan` rows in the database directly.
    """
    from epocha.apps.economy.models import Loan

    active_loans = list(Loan.objects.filter(lender=deceased, lender_type="agent", status="active"))
    if not active_loans:
        return

    flattened_heirs = [heir for pool in heirs.values() for heir in pool]

    if not flattened_heirs:
        for loan in active_loans:
            loan.lender = None
            loan.lender_type = "banking"
        Loan.objects.bulk_update(active_loans, ["lender", "lender_type"])
        return

    heir_count = len(flattened_heirs)
    for index, loan in enumerate(active_loans):
        loan.lender = flattened_heirs[index % heir_count]

    Loan.objects.bulk_update(active_loans, ["lender"])
