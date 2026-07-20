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
from typing import Any

from django.core.exceptions import FieldDoesNotExist


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
