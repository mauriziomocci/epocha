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
import math
from collections import deque
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
#
# Fix M-1 (phase-6 audit round 1, T046): `ast.Pow` REMOVED. `9**9**9` is
# right-associative (`9**(9**9)`), producing an integer with over 369
# million digits; the auditor's own reproduction hung past 120 seconds
# computing it before being killed. Neither the node-type whitelist walk
# nor `_eval_node`'s numeric-constant guard can catch this by construction
# -- every individual node (three small-int `Constant`s, two `Pow`
# `BinOp`s) is well-typed and well-within-range; the danger is purely in
# the COMBINATION, invisible to a per-node check. Removing the operator
# eliminates the vector outright rather than attempting to bound operand
# magnitude (a much harder, more fragile defense). Verified: no era
# template under epocha/apps/demography/templates/ uses `**` anywhere --
# the single derived formula (`cunning`, identical across all five eras)
# is `0.4*(1-agreeableness) + 0.3*neuroticism + 0.3*intelligence`, needing
# neither `Pow` nor `Mod`. Removal costs nothing real.
#
# `ast.Mod` REMOVED on the SAME "surface not kept wide merely because
# today's inputs are trusted" reasoning (decision D5) -- NOT because Mod
# shares Pow's exponential-blowup risk. It does not: `a % b` is bounded by
# `b` and cannot compound into unbounded computation the way a
# right-associative `Pow` tower can; Mod's only actual failure mode
# (division by zero) is already covered by the `FormulaError` wrap in
# `evaluate_derived_formula` below, independent of whether Mod stays
# whitelisted. It is removed anyway because it is unused, unneeded by the
# one formula this evaluator serves, and every additional whitelisted
# operator is permanent audit surface for zero present benefit -- this
# project's own "burden of proof is on adding" principle, applied in
# reverse to an existing-but-unjustified feature rather than a new one.
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
    ast.USub,
    ast.UAdd,
)

# Fix NEW-3, first pass (phase-6 audit round 2, T046): maximum AST nesting
# depth a formula may reach, enforced during the SAME iterative whitelist
# walk that already visits every node (no extra tree traversal). Removing
# `ast.Pow` (fix M-1) closed the exponential-blowup vector, but
# `_eval_node`'s own recursive descent is a SEPARATE vector: a formula
# built entirely from whitelisted nodes (e.g. hundreds of nested unary
# minuses, `"-"*n + "x"`) still costs one Python stack frame per nesting
# level, and independently reproduced in this exact container: succeeds
# up to n=997, raises a bare `RecursionError` (not `FormulaError`) at
# n=998, both via a standalone script and via pytest. That crossover point
# is CALLER-STACK-DEPENDENT (a deeper caller, e.g. inside Django/Celery
# request handling, hits it at a smaller n than a bare script or test
# does), which is the reason for a proactive, fixed bound checked in THIS
# function rather than only reacting to wherever Python's own recursion
# ceiling happens to sit for a given caller. 50 is an order of magnitude
# more than any plausible arithmetic formula needs (the one real derived
# formula today, `cunning`, nests about 5-7 levels deep) while staying two
# orders of magnitude below Python's own default recursion limit (1000),
# leaving comfortable margin regardless of how deep the caller's own stack
# already is.
#
# NOTE (round 2's own claim, corrected in round 3): this comment used to
# say "ast.parse itself copes fine at every n tried up to 1200" -- true as
# far as it was tested, but MISLEADING: at n=5976 (`"-"*n + "x"`, same
# reproduction shape, much larger n), `ast.parse` itself raises a bare
# `MemoryError` (CPython's own PEG parser exhausting its internal stack
# allocator) BEFORE this depth bound -- which runs strictly after parsing
# succeeds -- ever gets a chance to fire. See `_MAX_FORMULA_EXPRESSION_
# LENGTH` immediately below for the separate, proactive fix that protects
# the PARSE stage itself, which this bound does not and cannot.
_MAX_FORMULA_TREE_DEPTH = 50

# Fix NEW-3, second pass (phase-6 audit round 3, T046): maximum character
# length a formula string may have, checked BEFORE `ast.parse` is ever
# called -- `_MAX_FORMULA_TREE_DEPTH` above protects `_eval_node`'s own
# descent AFTER a successful parse, but does nothing for a failure INSIDE
# the parse call itself. Independently reproduced: `ast.parse("-"*n + "x",
# mode="eval")` succeeds up to n=5900 and raises a bare `MemoryError`
# ("Parser stack overflowed - Python source too complex to parse") at
# n=5976 in this exact container -- CPython's own parser stack limit, not
# a symptom of the whole process running out of memory, but still an
# exception type the `Raises` contract never promised. A length bound was
# chosen over `except MemoryError` around the parse call: it stops the
# parser from ever seeing a pathological string at all, rather than
# reacting to however CPython's specific parser implementation happens to
# fail today (a `MemoryError` at a fixed internal stack depth is a CPython
# implementation detail, not a documented contract), and it avoids
# swallowing a broadly-typed exception that could also legitimately signal
# a real out-of-memory condition elsewhere. 500 characters is roughly 8.6x
# the one real derived formula today (`cunning`, 58 characters) -- ample
# headroom for a substantially more complex future formula (a dozen-plus
# terms) -- while staying more than an order of magnitude below n=5976,
# the measured parser danger zone.
_MAX_FORMULA_EXPRESSION_LENGTH = 500


def evaluate_derived_formula(expression: str, symbols: dict[str, float]) -> float:
    """Evaluate a derived-trait formula against a restricted arithmetic grammar.

    This is the evaluator for the design's `derived_trait_formulas` (design
    spec Sezione 4), e.g. the `cunning` Machiavellism proxy:

        cunning = 0.4*(1-agreeableness) + 0.3*neuroticism + 0.3*intelligence

    where the right-hand side is a template string stored in an era template
    file and `symbols` supplies the already-resolved trait values referenced
    by name.

    Security (decision D5): BEFORE anything else, `expression`'s raw
    character length is checked against `_MAX_FORMULA_EXPRESSION_LENGTH`
    (fix NEW-3, phase-6 audit round 3, T046 -- see that constant's own
    comment: a pathologically long expression can make `ast.parse` itself
    raise a bare `MemoryError`, a failure mode no later check can prevent
    since it happens INSIDE parsing). Only then is the expression parsed
    with `ast.parse(..., mode="eval")` and walked node by node,
    ITERATIVELY (never via Python call-stack recursion -- see the walk's
    own comment), against an explicit whitelist -- `Expression`, `BinOp`,
    `UnaryOp`, `Constant`, `Name`, and the arithmetic operators `Add`,
    `Sub`, `Mult`, `Div`, `USub`, `UAdd` (fix M-1, phase-6 audit round 1,
    T046: `Pow` and `Mod` removed -- see `_ALLOWED_NODE_TYPES`'s own
    comment for the full reasoning). The SAME walk also enforces
    `_MAX_FORMULA_TREE_DEPTH` (fix NEW-3, phase-6 audit round 2, T046 --
    see that constant's own comment): a formula built entirely from
    whitelisted nodes can still exhaust the evaluator's OWN recursive
    descent in `_eval_node` through sheer nesting depth, a separate vector
    from the operator-blowup `Pow`'s removal closed, and a separate stage
    from the pre-parse length check (this one runs AFTER a successful
    parse). Any other node type (function calls, attribute access,
    subscripts, comprehensions, boolean/comparison operators, lambdas, and
    so on), or a tree deeper than the bound, raises `FormulaError`.
    `eval()` on the raw string is never used. Formula templates come from
    versioned era template files rather than end-user input, but the
    evaluator does not treat that as license to widen the surface: today's
    trusted input is not a guarantee against a future caller feeding it
    untrusted data, and the whitelist is cheap defense in depth against
    turning a data file into a code-execution vector.

    A bare name is resolved only by exact lookup in `symbols`; a name absent
    from `symbols` raises `FormulaError`. This is also what blocks dunder
    names (e.g. `__import__`): they are refused on the same unknown-name
    path as any other name not present in the symbol table, with no special
    casing required.

    OVERFLOW (fix M-1 decision, examined not fixed): an operand large
    enough to overflow float arithmetic (e.g. `1e308*1e308`) yields `inf`
    rather than raising -- a valid Python float, not a crash. This is
    accepted rather than special-cased: no current era template's
    coefficients (all in or near [0, 1]) can reach anywhere near this
    magnitude, `_apply_derived_traits`'s own `max(lo, min(hi, raw_value))`
    clamp already bounds an `inf` result safely into the formula's
    declared range with no corruption, and distinguishing "genuine
    overflow" from "a future template that legitimately wants a large
    coefficient" is not a decision this evaluator should make unilaterally
    on the caller's behalf.

    Args:
        expression: the formula's right-hand side, e.g.
            "0.4*(1-agreeableness) + 0.3*neuroticism + 0.3*intelligence".
        symbols: mapping from trait name to its resolved numeric value.

    Returns:
        The formula's numeric result as a float.

    Raises:
        FormulaError: if `expression` is longer than
            `_MAX_FORMULA_EXPRESSION_LENGTH` (fix NEW-3, phase-6 audit
            round 3, T046 -- checked BEFORE parsing, since a pathologically
            long expression can make `ast.parse` itself raise a bare
            `MemoryError`; see that constant's own comment), is not valid
            Python syntax, uses any node type outside the whitelist, nests
            deeper than `_MAX_FORMULA_TREE_DEPTH` (fix NEW-3, phase-6 audit
            round 2, T046), references a name absent from `symbols`,
            contains a non-numeric constant, or if evaluating the
            (whitelisted) arithmetic itself raises -- fix M-1: this
            module's whole posture is to never crash the birth pipeline on
            template data (see `apply_social_inheritance`'s unknown-
            `class_rule` fallback, `apply_estate_tax`'s rate clamp), so a
            `ZeroDivisionError` from a template's own zero-valued
            denominator (or any other `ArithmeticError`), and a
            `RecursionError` from `_eval_node`'s own recursive descent on
            a pathologically nested but otherwise fully whitelisted tree,
            are both prevented from escaping raw -- the depth bound stops
            the latter proactively (see its own comment for why a fixed,
            caller-stack-independent bound was chosen over only reacting
            to wherever Python's recursion ceiling happens to sit).
    """
    if len(expression) > _MAX_FORMULA_EXPRESSION_LENGTH:
        raise FormulaError(
            f"formula exceeds the maximum length of "
            f"{_MAX_FORMULA_EXPRESSION_LENGTH} characters "
            f"({len(expression)} characters): {expression[:80]!r}..."
        )

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise FormulaError(f"invalid formula syntax: {expression!r}") from exc

    # Iterative (never Python call-stack recursive) breadth-first walk,
    # tracking each node's depth alongside it -- deliberately NOT
    # `ast.walk(tree)` (which visits every node but does not expose depth)
    # so the SAME single pass enforces both the node-type whitelist and
    # `_MAX_FORMULA_TREE_DEPTH` (fix NEW-3) without a second tree
    # traversal. Using an explicit `deque` worklist rather than a
    # recursive helper is deliberate: a recursive depth-CHECKER would
    # itself be vulnerable to the exact `RecursionError` this check exists
    # to prevent.
    worklist: deque[tuple[ast.AST, int]] = deque([(tree, 0)])
    while worklist:
        node, depth = worklist.popleft()
        if not isinstance(node, _ALLOWED_NODE_TYPES):
            raise FormulaError(
                f"disallowed construct {type(node).__name__!r} in formula: {expression!r}"
            )
        if depth > _MAX_FORMULA_TREE_DEPTH:
            raise FormulaError(
                f"formula nesting exceeds the maximum depth of "
                f"{_MAX_FORMULA_TREE_DEPTH}: {expression!r}"
            )
        worklist.extend((child, depth + 1) for child in ast.iter_child_nodes(node))

    try:
        return float(_eval_node(tree.body, symbols))
    except ArithmeticError as exc:
        raise FormulaError(f"arithmetic error evaluating formula: {expression!r}") from exc


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
        # Fix M-1: Pow and Mod dispatch branches removed along with their
        # whitelist entries above -- this is now genuinely unreachable
        # dead code for them, not merely untested, since the whitelist
        # walk in evaluate_derived_formula already rejects any tree
        # containing an ast.Pow or ast.Mod node before _eval_node ever
        # runs.
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

    CONTESTED AND DEFERRED (phase-6 audit round 1, T046, findings I-4 and
    I-5 -- flagged again in round 2 as a documentation-honesty gap, NOT
    resolved here): the audit's own analysis holds that this citation does
    not support the SINGLE-PARENT branch below as implemented (I-4,
    "polygenic variance collapse") and that "halves the genetic signal" is
    not the correct characterization of what `h2 * parent_T + (1 - h2) *
    noise_T` actually does relative to the two-parent case (I-5, contests
    "halving", not "doubling"). Both findings are DESIGN-LEVEL: the code
    faithfully implements what was specified, but the specification itself
    is disputed -- fixing it requires reopening the phase-2 heavy gate on
    the design spec, not a code patch on this branch, and is out of scope
    here by explicit instruction. This note exists so a reader does not
    take the formula or the "halves the genetic signal" claim below as
    settled; both are open, tracked separately, and NEITHER the formula
    NOR this docstring's own claim have been changed by this note.

    where `midparent_T = (mother_val + father_val) / 2` when both parents
    are known. `noise` models the environmental contribution as a draw from
    a Normal distribution whose mean and standard deviation are estimated
    from the tick-0 population and frozen thereafter (design spec Sezione
    4); it is drawn exactly once per call, via `rng.gauss(era_mean,
    era_sd)`, and always AFTER the midparent branch below so that the RNG
    sequence consumed by this function is independent of which branch ran.

    Fix I-1 (design spec's OWN fix numbering, predates the phase-6 audit
    entirely -- unrelated to, and NOT the same finding as, this module's
    unrelated audit finding also labelled "I-1", the social-class rank
    clamp far below in this file, always written `T046/I-1` to keep the
    two apart) -- single-parent fallback: when exactly one of mother_val /
    father_val is known (None for the other), the midparent term degrades
    to the known parent's value alone:

        child_T = h2 * parent_T + (1 - h2) * noise_T

    This halves the genetic signal relative to the two-parent case
    (CONTESTED, see the note at the top of this docstring -- findings I-4
    and I-5 dispute this characterization; deferred, not resolved here),
    which matches the real single-parent genetic flow rather than treating
    the missing parent as contributing zero. Documented as a deliberate
    simplification for genealogies where only one parent is resolved (adoption
    scenarios, or synthetic tick-0 genealogies without both parents recorded).

    Fix I-3 (phase-6 audit round 1, T046) -- neither parent known: when
    BOTH mother_val and father_val are None, the midparent term degrades
    further, to `era_mean` itself:

        child_T = h2 * era_mean + (1 - h2) * noise_T

    No parental signal survives here, so the child is drawn entirely from
    the era distribution -- genetically, this is the same statement the
    single-parent fallback makes taken to its limit (parental information
    degrades from two values, to one, to none). Mirrors
    `_regress_education_level`'s already-correct four-way fallback
    (mother-only / father-only / both / neither -> era_mean_education).
    Reachable from the real birth pipeline: none of the five Big Five
    personality traits is an `Agent` model column, so their values come
    from `(parent.personality or {}).get(name)` in `apply_trait_
    inheritance`, which returns None whenever neither parent's personality
    dict happens to carry that key -- before this fix, any such birth
    raised `TypeError` uncaught.

    The result is clamped to [lo, hi] (default [0.0, 1.0], the typical range
    for Agent personality/trait scalars); callers pass the trait-specific
    range when it differs.

    This function is pure: no ORM access, no global state. Given the same
    rng state and inputs it is fully deterministic, which is required for
    publication-grade reproducibility of the birth pipeline.

    Args:
        mother_val: mother's trait value, or None if the mother is unknown.
        father_val: father's trait value, or None if the father is unknown.
            Both may be None (fix I-3): the midparent term then falls back
            to era_mean rather than raising.
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
        parent_term = (mother_val + father_val) / 2
        signal_coefficient = h2
        # Var(midparent) = V/2 under random mating, so imposing V = era_sd^2
        # on V = h2^2 * V/2 + c^2 * era_sd^2 gives c^2 = 1 - h2^2/2.
        residual_scale = math.sqrt(1.0 - h2**2 / 2.0)
    elif mother_val is not None or father_val is not None:
        parent_term = mother_val if mother_val is not None else father_val
        # Cov(child, one parent) = V_A/2 against Var(one parent) = V_P, so the
        # regression coefficient on a single parent is h2/2 -- half of the
        # midparent one, and derived rather than postulated.
        signal_coefficient = h2 / 2.0
        residual_scale = math.sqrt(1.0 - h2**2 / 4.0)
    else:
        parent_term = era_mean
        signal_coefficient = 0.0
        # No parental signal survives, so the residual carries the whole
        # declared amplitude.
        residual_scale = 1.0

    # NOTE on the exponent, because getting it wrong is invisible to a slope
    # test: `h2` already holds h-squared, so the identity's h^4 is `h2**2`.
    # Writing `h2**4` inflates the standard deviation by 6.03% at h2 = 0.55
    # and the variance by 12.43%, and leaves the regression slope untouched.
    #
    # ONE draw, on every branch: the RNG stream a tick consumes must not
    # depend on which branch ran.
    residual = rng.gauss(0.0, residual_scale * era_sd)
    result = era_mean + signal_coefficient * (parent_term - era_mean) + residual
    return max(lo, min(hi, result))


# Environmental-noise prior kept ONLY as the defensive guard of amendment A9
# (2026-08-07): a template that passes validation cannot reach it, because
# clause 4 rejects any heritability key without its own era_noise entry. If it
# fires, the loader was bypassed or the transmitted set has reopened, and the
# call site logs a warning naming the character. The
# original design spec (Sezione 4) called for era_mean_T / era_sd_T estimated
# from the tick-0 population and frozen thereafter. That mechanism was never
# built, and amendment A2 replaced it: all five templates now declare a
# `trait_inheritance.era_noise` section giving, per era and per character, the
# mean and amplitude of the OBSERVED distribution the kernel must realize, and
# clause 5 of A9 refuses any pair outside the admissible region of A1. The two
# values below match what those templates declare today, which is why closing
# the fallback changed no shipped behaviour -- they were the silent default,
# and are now the explicit declaration.
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

    Trait set for step 1: exactly the keys of
    `template["trait_inheritance"]["heritability"]`, and nothing else.
    Amendment A9 (2026-08-07) CLOSED this set. Until then it was extended
    with every key found in either parent's `personality` dict -- an
    unvalidated JSONField populated by an LLM prompt -- so a key the model
    invented became a transmitted character governed by a fallback
    heritability and a noise pair no template declared. A key present in
    `personality` but absent from `heritability` is now left untouched on
    the child: it is data the agent carries, not a character this model
    transmits. The `"default"` sentinel that governed those keys was removed
    from the schema by the same amendment, and the loader rejects it.
    `social_class` is likewise not included: it carries no heritability entry
    and is governed by the social-inheritance rules (design spec Sezione 5).

    Trait names are collected in heritability dict order -- JSON insertion
    order, stable -- rather than via an unordered Python `set`. `rng.gauss`
    is drawn exactly once per trait (see `inherit_trait`), so an unordered
    iteration would make the RNG draw sequence depend on the interpreter's
    per-process string hash seed, breaking the bit-for-bit reproducibility
    the demography subsystem requires for identically seeded runs.

    era_mean / era_sd: read per-trait from
    `template["trait_inheritance"]["era_noise"][name]`, which amendment A2
    made a mandatory section and A9 clause 4 requires to carry one entry per
    declared character. `DEFAULT_ERA_MEAN` / `DEFAULT_ERA_SD` survive only as
    the defensive guard of A9: unreachable for a template that passed
    validation, and logged with the character's name if they ever fire.

    This function mutates `child` in place -- scalar attributes via
    `setattr`, personality entries via `child.personality[name] = value` --
    but never calls `child.save()`; persistence is the caller's
    responsibility, keeping this composable with however Plan 4 sequences
    the birth pipeline. All randomness is drawn from the passed `rng`; no
    global state, no hidden ORM writes, no calls to `inherit_trait` or
    `evaluate_derived_formula` outside their published contracts.

    Args:
        child: the newborn Agent instance (need not be saved yet).
            Precondition (fix M-2, phase-6 audit round 1, T046):
            `child.personality` must be a mutable dict by the time this
            function returns any personality-routed trait -- this function
            establishes that itself (initializing `None` to `{}`) rather
            than requiring the caller to guarantee it, since `child` is
            routinely unsaved at this point and Django only applies the
            `Agent.personality` field's `default=dict` when the
            constructor is called with the kwarg omitted entirely.
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
    # Fix M-2: guard child.personality before ANY personality-routed write
    # in this function or in _apply_derived_traits below (both share this
    # one child instance within the same call). The parent-side reads two
    # lines below are already defensive (`parent.personality or {}`); this
    # makes the child-side write equally so, instead of leaving it as an
    # undeclared precondition on the caller.
    if child.personality is None:
        child.personality = {}

    trait_inheritance = template["trait_inheritance"]
    heritability = trait_inheritance["heritability"]
    era_noise = trait_inheritance["era_noise"]

    # THE TRANSMITTED SET IS CLOSED (design-spec amendment A9, 2026-08-07).
    # It is exactly what `trait_inheritance.heritability` declares, and nothing
    # else. Until that amendment this list was extended with every key found in
    # either parent's `personality` dict -- a JSONField with no validators,
    # populated by an LLM prompt -- so a key the model invented became a
    # transmitted character governed by a hardcoded fallback heritability and a
    # hardcoded noise pair that no template had declared. Template validation
    # cannot close a set that runtime reopens, so the set is closed here, at the
    # only place that decides what gets transmitted.
    #
    # A key present in `personality` but absent from `heritability` is now left
    # untouched on the child rather than inherited: it is data the agent carries,
    # not a character this model transmits.
    trait_names = list(heritability)

    child_model = type(child)
    symbols: dict[str, float] = {}

    for name in trait_names:
        h2 = heritability[name]
        noise_spec = era_noise.get(name)
        if noise_spec is None:
            # A9 requires the defensive guard to name the character when it
            # fires. For a template that passed validation it cannot: clause 4
            # rejects any heritability key without its own era_noise entry. If
            # this ever prints, the loader was bypassed or the set has reopened.
            logger.warning(
                "demography: no era_noise entry for transmitted character %r; "
                "falling back to (%s, %s). A valid template cannot reach this "
                "path -- the transmitted set has reopened.",
                name,
                DEFAULT_ERA_MEAN,
                DEFAULT_ERA_SD,
            )
            noise_spec = {}
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

# Fix T046/I-1 (phase-6 audit round 1 -- prefixed to distinguish this
# finding from `inherit_trait`'s unrelated, pre-existing design-spec fix
# also numbered "I-1"): _MAX_CLASS_RANK is the OUTPUT
# ceiling used by _rank_to_class_label's own clamp, and is deliberately
# _CLASS_RANK's max (4, "poor"), NOT _EXTENDED_CLASS_RANK's max (5,
# "enslaved"). Before this fix the clamp used the extended value, so any
# sampled-rule rank arithmetic (clark_regression, becker_tomes_elasticity_0.4,
# meritocratic) that rounded to 5 resolved to "enslaved" out of ordinary
# weighted-average-plus-noise math, with no enslaved parent anywhere --
# measured at 25.09% of children for two "poor" parents in an all-"poor"
# zone under becker_tomes (200,000-draw Monte Carlo, post-fix; matches the
# audit's own independent 25.4%/25.23% figures within Monte Carlo
# variance). "enslaved" as INPUT is still read correctly everywhere via
# _class_rank/_resolve_parent_rank against _EXTENDED_CLASS_RANK, unchanged
# by this fix -- only the numeric OUTPUT of _rank_to_class_label is capped.
# Rank 5 remains reachable exactly one way: patrilineal_rigid's string copy
# of an already-enslaved parent's own label, which never calls
# _rank_to_class_label at all. Mirrors _MERIT_RANK_SPAN below, which
# already excludes "enslaved" from meritocratic's span for the identical
# reason.
_MAX_CLASS_RANK = max(_CLASS_RANK.values())

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
#
# U-2 (phase-6 audit round 1, T046): clamping the output at both ladder ends
# (fix T046/I-1) means the realized rank distribution under this SD is NOT the
# unclamped Gaussian the 0.4 elasticity implies -- probability mass that
# would fall outside [0, 4] piles up at the nearest boundary instead.
# Measured at 200,000 draws per case (worst-case inputs, base_rank already
# at the pre-perturbation ladder boundary before noise is added): two
# "poor" parents in an all-"poor" zone (base_rank=4) put 74.61% of children
# at rank 4 "poor" and 23.12% at rank 3 "working", versus a floor-clamped-
# only baseline of 49.91% + 0.00% "enslaved" before this fix (the missing
# ~25 points is exactly the mass this fix moves off "enslaved"); two
# "elite" parents in an all-"elite" zone (base_rank=0) put 74.91% of
# children at rank 0 "elite" and 22.85% at rank 1 "wealthy", symmetric and
# unaffected by this fix since the low end was already correctly floored.
# Value left at 0.75 per instruction: this comment reports the measured
# effect, it does not retune the parameter.
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
    with the single-parent fallback philosophy of `inherit_trait`'s own
    design-spec fix I-1 elsewhere in this module (design numbering, NOT
    this file's audit-numbered `T046/I-1`).
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

    Precondition (fix I-2, phase-6 audit round 1, T046): `child.education_
    level` must already hold the regressed value by the time this runs --
    `apply_social_inheritance` guarantees this by running education-level
    regression before dispatching to this function. Calling this helper
    directly on a child whose `education_level` has not yet been regressed
    reproduces I-2's bug (merit computed from a stale/default value).
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
    parent's value alone, consistent with `inherit_trait`'s own design-spec
    fix I-1 (design numbering, NOT this file's audit-numbered `T046/I-1`);
    when neither parent is known, the midparent term degrades to
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

    1. Education-level regression runs FIRST (see `_regress_education_level`),
       using `template["social_inheritance"]["education_regression_rho"]`
       and `template["social_inheritance"].get("era_mean_education",
       DEFAULT_ERA_MEAN_EDUCATION)`, and writes `child.education_level`
       before anything else touches it.
    2. `template["social_inheritance"]["class_rule"]` then selects one of
       four branches -- `patrilineal_rigid`, `clark_regression`,
       `becker_tomes_elasticity_0.4`, `meritocratic` (see the per-branch
       helpers for citations and formulas). An unrecognized `class_rule`
       logs a warning and falls back to `patrilineal_rigid` rather than
       raising, matching this module's "never crash the birth pipeline on
       template data" posture (see `evaluate_derived_formula`'s
       fractional-tail handling in `resolve_birth_attributes` for the same
       philosophy applied elsewhere).

    Fix I-2 (phase-6 audit round 1, T046): this order was originally
    reversed -- class_rule ran first, education-level regression last. That
    put `meritocratic` (the only branch that reads `child.education_level`)
    in the position of reading a fresh newborn's untouched `Agent` field
    default (0.3) instead of the value this same function was about to
    compute for it, silently understating merit in the one era (sci_fi)
    whose whole premise is that education determines standing. Running
    regression first makes `child.education_level` correct and available
    to every branch that might come to depend on it, not just the one that
    does today, and it costs nothing: no branch other than `meritocratic`
    reads `education_level`, and `_regress_education_level` never reads
    `child.social_class`, so the two steps have no cyclic dependency and
    can run in either order except for this one read.

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

    # Fix I-2: regression runs BEFORE class_rule dispatch so that
    # `_apply_meritocratic` (the only branch reading `child.education_level`)
    # sees the correctly regressed value, not the untouched Agent field
    # default. See the docstring above for the full rationale.
    rho = social_inheritance["education_regression_rho"]
    era_mean_education = social_inheritance.get("era_mean_education", DEFAULT_ERA_MEAN_EDUCATION)
    child.education_level = _regress_education_level(mother, father, rho, era_mean_education)

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


def _resolve_grandparent_ids(parent_ids: list[int]) -> set[int]:
    """Grandparent ids: the recorded parents of the given `parent_ids`
    (typically an agent's own `parent_agent_id`/`other_parent_agent_id`),
    fetched with a single `values_list` query over at most `len(parent_ids)`
    rows -- the query reads the PARENTS' rows to project their own
    parentage columns, it never touches a grandparent row directly.

    Returns an empty set (0 queries) when `parent_ids` is empty, or when
    none of the given parents has a recorded parent of their own.

    Shared by `_resolve_extended_family_heirs` (Plan 3, T016/T017 -- the
    seed for the cousin traversal) and `assign_orphan_caretaker` (Plan 3,
    T024/T025 -- the seed for grandparent and aunt/uncle caretaker
    candidates), so the "grandparents of a given agent" lookup is defined
    exactly once.
    """
    from epocha.apps.agents.models import Agent

    if not parent_ids:
        return set()

    grandparent_id_pairs = Agent.objects.filter(id__in=parent_ids).values_list(
        "parent_agent_id", "other_parent_agent_id"
    )
    return {gid for pair in grandparent_id_pairs for gid in pair if gid is not None}


def _resolve_aunts_uncles(grandparent_ids: set[int], excluded_parent_ids: list[int]) -> list:
    """Children of `grandparent_ids` (via either parentage FK), excluding
    `excluded_parent_ids` -- typically the reference agent's own recorded
    parents, who are not "extended family" to that agent.

    Returns every matching row regardless of `is_alive`: callers filter on
    aliveness themselves. `_resolve_extended_family_heirs` needs dead
    aunts/uncles too, to walk down to their still-living children (first
    cousins are alive-or-dead descendants of a possibly-dead aunt/uncle);
    `assign_orphan_caretaker` filters to living ones directly, since a
    dead aunt/uncle can never be a caretaker.

    Query cost: exactly 1 query (0 when `grandparent_ids` is empty).
    """
    from epocha.apps.agents.models import Agent

    if not grandparent_ids:
        return []

    return list(
        Agent.objects.filter(
            Q(parent_agent_id__in=grandparent_ids) | Q(other_parent_agent_id__in=grandparent_ids)
        ).exclude(id__in=excluded_parent_ids)
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

    Steps 1-2 (grandparent ids, then their children) are delegated to
    `_resolve_grandparent_ids` / `_resolve_aunts_uncles`, shared with
    `assign_orphan_caretaker` below -- see those functions' own docstrings.

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

    grandparent_ids = _resolve_grandparent_ids(parent_ids)
    if not grandparent_ids:
        return []

    aunts_uncles = _resolve_aunts_uncles(grandparent_ids, parent_ids)
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
    lets the succession rules below split an amount across more than one
    heir without accumulating the "divide a total into N parts" rounding
    drift a naive `total / n` repeated N times would (e.g. `10_000.0 / 3
    == 3333.3333333333335`, and three such shares summed drift from
    `10_000.0` by roughly 1e-12).

    THE GUARANTEE, STATED PRECISELY (corrected, phase-6 audit round 4,
    T046 -- this docstring previously overstated it): what is EXACT, to
    full floating-point precision, is `running_sum + (total -
    running_sum) == total`, where `running_sum` is accumulated via THE
    SAME left-to-right `+=` this function itself uses below (confirmed
    over 50,000 random trials, zero failures) -- `running_sum` and `total`
    are always the same order of magnitude here (the former is a fraction
    of the latter, drawn from the same estate), so the pathological
    cancellation cases of `a + (b - a)` arithmetic (`a`, `b` of wildly
    different magnitude) do not arise in this domain. This is NOT the
    same claim as "`sum(allocation.values())` (the RETURNED dict, re-
    summed via a DIFFERENT method) always equals `total`" -- Python's
    builtin `sum()`, as of Python 3.12, uses a compensated/Neumaier
    summation algorithm for floats rather than naive left-to-right
    addition, and re-summing this function's own output that way can
    disagree with `total` by roughly 1e-16 relative error for a
    substantial fraction of random amounts: measured directly (not
    inferred) at 22.3% of random amounts for 7 heirs and 48.4% for 11,
    across many trials -- see `TestDistributeEstateConservationAdversarial`
    in `test_inheritance.py`, which found this independently while
    building an adversarial fixture and documents the exact figures.
    Every caller in this module that checks conservation via `sum(
    allocation.values())` (the natural, and only practical, way for a
    caller to verify it) is therefore checking a WEAKER property than
    this function's own internal identity proves -- true in the
    overwhelming majority of cases and exact for the amounts this
    module's own test suite specifically uses, but not a universal
    guarantee for arbitrary `total`/`n` combinations. This note changes
    no behavior; the allocation mechanism itself is unchanged.

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

    Fix C-2 (phase-6 audit round 1, T046) -- DEDUPLICATED by id, first
    occurrence wins: `_allocate_with_exact_remainder` assumes every id in
    its input appears exactly once; a heir whose id appeared TWICE in
    `[*children, *spouse]` would collapse to one dict key while the
    remainder-absorbing `running_sum` still counted it twice, silently
    losing one full share's worth of value. One person occupying two
    categories (a data anomaly this module does not otherwise validate
    against) still receives exactly ONE equal share, never two, and the
    conservation invariant below holds regardless. The membership set
    below is used only to filter, never iterated for output order --
    `recipients`' own order is built by iterating the original list, so
    this does not reintroduce the "observable result from a bare set"
    hazard this module avoids elsewhere.

    Returns an empty allocation (the treasury fallback) when there are
    neither children nor a spouse.
    """
    children = heirs.get("children", [])
    spouse = heirs.get("spouse", [])

    seen_ids: set[int] = set()
    recipients = []
    for agent in [*children, *spouse]:
        if agent.id not in seen_ids:
            seen_ids.add(agent.id)
            recipients.append(agent)

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
    step 1 actually receives the rest AND the spouse is not also a member
    of `pool`; step 2 is the degenerate case where the spouse is topped up
    beyond that fraction.

    Fix C-2 (phase-6 audit round 1, T046) -- SPOUSE ALSO A RESIDUARY HEIR:
    when `pool` is `siblings` (no children), the spouse can also BE one of
    those siblings (`form_couple` in `couple.py` performs no consanguinity
    check anywhere, and `marriage_market_radius: "same_zone"` concentrates
    marriage candidates in a small, often-related pool -- reachable, not
    theoretical). That person is then entitled to TWO genuinely separate
    amounts: their fixed spousal fraction, and their own residuary share
    from `_split_two_to_one(pool, residual)`. The assignment below ADDS the
    spousal fraction on top of whatever `_split_two_to_one` already
    computed for that same id, rather than overwriting it -- overwriting
    would silently destroy the residuary share and break the conservation
    invariant this whole user story exists to protect.

    Conservation: `spouse_amount + sum(residuary allocation) ==
    inheritable` exactly (see `_allocate_with_exact_remainder`, used
    inside `_split_two_to_one` for the residuary split) -- holds whether or
    not the spouse is also a residuary heir, since ADDING preserves
    whatever `_split_two_to_one` already summed to `residual`.

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
            allocation[spouse[0].id] = allocation.get(spouse[0].id, 0.0) + spouse_amount
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


def _distribute_matrilineal(
    heirs: dict[str, list], inheritable: float, *, precomputed_heirs: list | None = None
) -> dict[int, float]:
    """The entire `inheritable` amount passes to the children of the
    deceased's sisters, divided equally (Schneider, D.M. & Gough, K.
    (1961), "Matrilineal Kinship" -- schematic matrilineal succession).

    `precomputed_heirs` (fix NEW-7, phase-6 audit round 4, T046): when the
    caller (`distribute_estate`, itself passing through what
    `process_inheritance_batch` supplies) has already resolved the
    niece/nephew list -- e.g. because it also needs to thread the SAME
    list into `transfer_loans_as_lender` -- passing it here skips the
    query `_resolve_matrilineal_heirs` would otherwise issue, so a
    matrilineal death's sister-resolution queries are paid exactly once
    per tick, not once per consumer. `None` (the default, and every
    existing caller's behavior) falls back to resolving it here, unchanged
    from before this fix.

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
    nieces_and_nephews = (
        precomputed_heirs if precomputed_heirs is not None else _resolve_matrilineal_heirs(heirs)
    )
    if not nieces_and_nephews:
        return {}

    share = inheritable / len(nieces_and_nephews)
    ordered_shares = [(agent.id, share) for agent in nieces_and_nephews]
    return _allocate_with_exact_remainder(ordered_shares, inheritable)


def distribute_estate(
    deceased: Any,
    heirs: dict[str, list],
    rule: str,
    inheritable: float,
    *,
    matrilineal_heirs: list | None = None,
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
        matrilineal_heirs: fix NEW-7 (phase-6 audit round 4, T046) --
            keyword-only, optional. When `rule == "matrilineal"` and the
            caller has already resolved the niece/nephew list (e.g.
            `process_inheritance_batch`, which also threads it into
            `transfer_loans_as_lender`), passing it here skips a redundant
            `_resolve_matrilineal_heirs` query. `None` (the default, and
            every pre-existing caller's behavior) resolves it here as
            before. Ignored for every rule other than `matrilineal`.

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
        return _distribute_matrilineal(heirs, inheritable, precomputed_heirs=matrilineal_heirs)
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


def transfer_loans_as_lender(
    deceased: Any,
    heirs: dict[str, list],
    cash_allocation: dict[int, float],
    *,
    matrilineal_heirs: list | None = None,
) -> None:
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

    Fix I-6 (phase-6 audit round 1, T046) -- SIGNATURE CHANGE, THIRD
    ARGUMENT ADDED: before this fix, this function ignored `rule` entirely
    and round-robinned loans across EVERY category `heirs` happened to
    contain, regardless of which categories the era's actual succession
    rule would ever pay CASH to. Two concrete failures this produced: (1)
    under `nationalized`, cash is 100% seized by the treasury
    (`distribute_estate` always returns `{}`) while loans still went
    round-robin to the spouse and children -- the opposite of the modelled
    institution; (2) under `primogeniture`, cash goes 100% to ONE heir
    while loans spread across the spouse, every child, every sibling, AND
    `extended_family` -- a category NO succession rule ever pays cash to
    at all. The fix takes "the same distribution rule" (design spec
    Sezione 5's own words) at face value: `cash_allocation` is the exact
    dict `distribute_estate(deceased, heirs, rule, inheritable)` already
    returned to the caller for this SAME deceased -- its ids (never its
    amounts; a zero-value cash transfer still marks a real entitlement,
    see `process_inheritance_batch`'s ZERO-VALUE TRANSFERS note) are the
    ONLY population loans now round-robin across. `nationalized` therefore
    falls out of this rule for free (`cash_allocation == {}` routes to
    banking, the empty-allocation branch below), with no `rule`-specific
    branching needed inside this function at all.

    WHAT THIS STILL GENERALISES, AND WHAT IT NO LONGER DOES: the
    round-robin split across N eligible heirs (`heir_index = loan_index %
    N`) is unchanged and still the deliberately simple policy this
    docstring documented before -- the design spec does not specify HOW
    multiple loans should split among multiple CASH-eligible heirs, only
    that they follow the same rule's PRIORITY. What no longer happens:
    loans reaching a heir category the cash rule itself did not pay this
    time (an idle sibling under `primogeniture` when there was a child to
    inherit; `extended_family`, unconditionally, under every rule). The
    two are no longer independent mechanisms re-deriving overlapping but
    inconsistent heir sets -- they are now the same set, computed once by
    `distribute_estate` and threaded through.

    WHY `cash_allocation` IS PASSED IN RATHER THAN THIS FUNCTION CALLING
    `distribute_estate` ITSELF (a `rule: str` parameter was considered and
    rejected): the caller (`process_inheritance_batch`) already calls
    `distribute_estate(deceased, heirs, rule, inheritable)` once per
    deceased and has the result on hand -- re-deriving the FULL allocation
    a second time here (a `rule: str` parameter and an internal
    `distribute_estate` call) would waste a redundant pure-Python
    computation for four of five rules AND, under `matrilineal`, cost a
    second FULL sister-count query pass on top of the one already paid.
    Accepting the already-computed dict keeps this function's own query
    cost at zero EXTRA queries for `primogeniture`/`equal_split`/`shari'a`/
    `nationalized`. `matrilineal` is DISTINGUISHED BY CALLER (corrected,
    phase-6 audit round 5, T046 -- this sentence used to say `matrilineal`
    "still pays its own sister-count queries once here" unconditionally,
    which fix NEW-7 (phase-6 audit round 4, T046, below) made false for
    the path that matters): `process_inheritance_batch`, the production
    caller, resolves the niece/nephew list ONCE at the orchestrator level
    and THREADS it in via `matrilineal_heirs=`, so THIS function pays ZERO
    extra queries there too -- matching every other rule. Only a DIRECT
    caller that omits `matrilineal_heirs` (bypassing the orchestrator)
    still pays the lazy per-sister fallback described under fix NEW-1
    below; that fallback keeps this function correct and self-contained
    for such a caller, at the query cost inherent to resolving nieces and
    nephews at all, strictly cheaper than the two-full-passes alternative
    this design avoids.

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

    Heir selection: `cash_allocation`'s keys, in that dict's own insertion
    order (Python dicts preserve insertion order; every `_distribute_*`
    helper inside `distribute_estate` inserts keys in the module's
    established spouse-first / oldest-first priority order, so this order
    is already correct with no re-sorting needed here). `heirs` is still
    required alongside it, to resolve those bare ids back to the Agent
    instances a `Loan.lender` FK assignment needs (`cash_allocation` itself
    carries only ids and cash amounts, never Agent references) -- built as
    an id-to-Agent lookup from every category `heirs` contains. Loans are
    assigned ROUND-ROBIN across the eligible heirs (`heir_index =
    loan_index % len(eligible_heirs)`): a documented, deliberately simple
    policy choice unchanged by this fix -- the design spec does not
    specify HOW multiple loans should split among multiple heirs the rule
    entitles to cash, only THAT they follow the same rule's priority;
    round-robin is the natural, deterministic generalization to N heirs
    that guarantees every eligible heir receives at least one loan when
    loans outnumber heirs, without requiring this function to re-run a
    `distribute_estate`-style proportional split for a fundamentally
    different asset class.

    FIX NEW-1 (phase-6 audit round 2, T046) -- MATRILINEAL IDS ARE NOT
    ALWAYS IN `heirs`: the claim "a cash-eligible id is always drawn from
    `heirs`" was FALSE for `matrilineal`, and the audit reproduced the
    resulting `KeyError` end to end (one sister, one living niece/nephew,
    one active lender-side loan -- the lookup raised inside
    `process_inheritance_batch`'s `transaction.atomic()` block, rolling
    back the ENTIRE tick's batch). `_distribute_matrilineal`'s allocation
    ids are nieces/nephews, reached via `_resolve_matrilineal_heirs(heirs)`
    -- a relationship `resolve_heirs`'s own category ladder cannot reach
    at all (see that function's own docstring), so those ids are never
    inserted into `heirs`, unlike every other rule's ids.

    FIX NEW-7 (phase-6 audit round 4, T046) -- THE NEW-1 FIX ITSELF
    BROKE THE QUERY BUDGET, CORRECTED HERE: NEW-1's own original fix
    lazily called `_resolve_matrilineal_heirs(heirs)` INSIDE this function
    whenever the direct `heirs`-only lookup missed an id, and called that
    query cost "unavoidable" -- it was not. Measured before this fix: 6
    queries for four sisters, one niece, one loan (1 loan SELECT + 4
    sister queries + 1 `bulk_update`), directly contradicting the "up to 2
    queries" budget this docstring and `process_inheritance_batch`'s own
    QUERY BUDGET section both stated. `process_inheritance_batch` already
    holds `heirs` and already threads `distribute_estate`'s own result
    through as `cash_allocation` -- the exact pattern the WHY-
    `cash_allocation`-IS-PASSED-IN section above established one paragraph
    earlier applies identically here: resolve the niece/nephew list ONCE,
    at the orchestrator level, and thread it into BOTH `distribute_estate`
    (as `matrilineal_heirs=`, so `_distribute_matrilineal` does not
    re-resolve it either) and this function (same keyword), rather than
    letting each consumer re-derive it independently. `matrilineal_heirs`
    (see Args below) is that threaded value; the lazy `_resolve_
    matrilineal_heirs(heirs)` fallback still exists for callers that pass
    `matrilineal_heirs=None` (every pre-existing direct call in this
    module's own test suite, and any future caller that has not resolved
    it), so this remains backward compatible, just no longer the path
    `process_inheritance_batch` itself takes. An id still unresolvable
    even after both the threaded value and the lazy fallback are tried
    (not reachable by any of the five documented rules today, but this
    module's established "never crash on data it cannot fully explain"
    posture applies exactly the same way here) is dropped from the
    eligible pool with a WARNING logged (matching `apply_social_
    inheritance`'s unknown-`class_rule` fallback's own logging posture),
    rather than either raising or failing silently; if every id is
    unresolvable, this degrades to the same banking-transfer branch an
    empty `cash_allocation` already uses.

    Write path (efficiency requirement, load-bearing once Plan 4 wires this
    into the per-tick death pipeline): exactly ONE `SELECT` (the active
    lender-side loans, materialized into a list) followed by exactly ONE
    `bulk_update` `UPDATE`, regardless of how many loans the deceased held
    as lender -- never a per-loan `.save()` loop, which would make this
    function's cost scale with the deceased's loan-book size instead of
    staying O(1) in query count. `matrilineal` costs ZERO additional
    queries here (fix NEW-7) when the caller threads `matrilineal_heirs`,
    matching every other rule; only a DIRECT caller that omits it (bypassing
    `process_inheritance_batch`) still pays one query per sister via the
    lazy fallback.

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
            established priority/oldest-first order. Used to resolve
            `cash_allocation`'s ids back to Agent instances; under
            `matrilineal` this alone is insufficient (fix NEW-1 above) and
            is supplemented by `matrilineal_heirs` when the caller
            supplies it, or a lazy `_resolve_matrilineal_heirs(heirs)`
            call otherwise (fix NEW-7).
        cash_allocation: the dict `distribute_estate(deceased, heirs, rule,
            inheritable)` already returned for this SAME deceased (fix
            I-6) -- an id-to-cash-amount mapping; only its KEYS, in their
            existing insertion order, determine which heirs are eligible
            for a loan and in what round-robin order. An empty dict (the
            `nationalized` rule, always; any other rule when it resolved
            no heir at all) is treated identically to "no living heir";
            an id that stays unresolvable even after the matrilineal
            fallback (fix NEW-1) is dropped (with a warning logged, fix
            NEW-7), and if that empties the eligible set entirely, this
            also degrades to "no living heir".
        matrilineal_heirs: fix NEW-7 (phase-6 audit round 4, T046) --
            keyword-only, optional. The SAME already-resolved niece/nephew
            list the caller may also have threaded into `distribute_estate`
            (via its own `matrilineal_heirs` parameter) -- passing it here
            avoids this function's own lazy `_resolve_matrilineal_heirs`
            query entirely. `None` (the default) falls back to that lazy
            resolution, unchanged from fix NEW-1. Only consulted when the
            direct `heirs`-only lookup actually misses an id (i.e. under
            `matrilineal`); harmless to pass for any other rule, since it
            is never read there.

    Returns:
        None. Mutates `Loan` rows in the database directly.
    """
    from epocha.apps.economy.models import Loan

    active_loans = list(Loan.objects.filter(lender=deceased, lender_type="agent", status="active"))
    if not active_loans:
        return

    agents_by_id = {heir.id: heir for pool in heirs.values() for heir in pool}
    missing_ids = [heir_id for heir_id in cash_allocation if heir_id not in agents_by_id]
    if missing_ids:
        # Fix NEW-1 (phase-6 audit round 2, T046): matrilineal ids
        # (nieces/nephews) are never in `heirs` itself. Fix NEW-7 (phase-6
        # audit round 4, T046): prefer the caller-threaded, already-
        # resolved list (zero extra queries -- the path `process_
        # inheritance_batch` takes) over the lazy `_resolve_matrilineal_
        # heirs(heirs)` fallback (one query per sister -- only paid by a
        # direct caller that has not resolved it itself).
        resolved_matrilineal_heirs = (
            matrilineal_heirs
            if matrilineal_heirs is not None
            else _resolve_matrilineal_heirs(heirs)
        )
        agents_by_id.update({agent.id: agent for agent in resolved_matrilineal_heirs})

    unresolved_ids = [heir_id for heir_id in cash_allocation if heir_id not in agents_by_id]
    if unresolved_ids:
        # Fix NEW-7: not reachable by any of the five documented rules
        # today, but this module's established "never crash on data it
        # cannot fully explain" posture (see apply_social_inheritance's
        # unknown-class_rule warning) applies here too -- logged, not
        # silent, and not raised.
        logger.warning(
            "transfer_loans_as_lender: %d cash-eligible id(s) %s for deceased "
            "%s could not be resolved to a living heir Agent even after the "
            "matrilineal fallback; dropped from the loan-transfer pool",
            len(unresolved_ids),
            unresolved_ids,
            deceased.id,
        )

    eligible_heirs = [
        agents_by_id[heir_id] for heir_id in cash_allocation if heir_id in agents_by_id
    ]

    if not eligible_heirs:
        for loan in active_loans:
            loan.lender = None
            loan.lender_type = "banking"
        Loan.objects.bulk_update(active_loans, ["lender", "lender_type"])
        return

    heir_count = len(eligible_heirs)
    for index, loan in enumerate(active_loans):
        loan.lender = eligible_heirs[index % heir_count]

    Loan.objects.bulk_update(active_loans, ["lender"])


# ---------------------------------------------------------------------------
# Orphan caretaker assignment (Plan 3, T024/T025, user story 3 -- orphans
# are taken in). Design spec Sezione 5, "Gestione orfani (fix MISS-1)":
# "Quando entrambi i genitori biologici di un minorenne (age <
# adulthood_age) sono morti, il minore viene assegnato un caretaker_agent
# secondo la priorità seguente: parente vivente più vicino nella stessa
# zona (fratello, nonno, zio/zia), poi qualsiasi parente vivente ovunque,
# poi None (pupillo dello stato). Un orfano con caretaker_agent = None
# viene flaggato e Government.government_treasury copre la sua
# sussistenza (modellando il wardship statale). L'orfano riceve comunque
# la sua eredità direttamente; il caretaker amministra ma non possiede gli
# asset."
# ---------------------------------------------------------------------------


def assign_orphan_caretaker(minor: Any, tick: int) -> Any | None:
    """Assign `minor.caretaker_agent` to the nearest living relative, or
    flag state wardship when none exists (design spec Sezione 5, "Gestione
    orfani (fix MISS-1)").

    THE TWO-STAGE LADDER: stage 1 looks for a living relative in the
    minor's own zone, walking the kinship rungs in priority order --
    sibling, then grandparent, then aunt/uncle. Only when stage 1 finds
    NOBODY does stage 2 repeat the exact same kinship order across every
    zone. This means a same-zone aunt/uncle (the lowest-priority rung)
    outranks an other-zone sibling (the highest-priority rung) -- stage 1
    is exhausted in full before stage 2 is even considered, matching the
    design spec's own ordering: "parente vivente più vicino nella stessa
    zona ... poi qualsiasi parente vivente ovunque". Rationale: the spec
    prioritizes physical proximity (the same zone, where day-to-day care
    is practical) over kinship closeness once wardship is being decided --
    an orphan is better served by a present, if more distant, relative
    than an absent close one. Within a single kinship rung, ties break by
    `birth_tick` ascending (oldest first, on the same convention this
    module already uses for heir ordering -- see `_resolve_sibling_heirs`
    and `_resolve_extended_family_heirs`), then `id` ascending for a total,
    deterministic order.

    KINSHIP DEFINITIONS: sibling reuses `_resolve_sibling_heirs(minor)`
    verbatim -- the "either parentage FK" broadening documented there
    (a half-sibling sharing only `other_parent_agent` counts) applies here
    identically, avoided by direct reuse rather than a parallel
    re-implementation (DRY). Grandparent and aunt/uncle candidates reuse
    `_resolve_grandparent_ids` / `_resolve_aunts_uncles`, the same helpers
    `_resolve_extended_family_heirs` uses for its own grandparent-lineage
    traversal -- grandparent means a parent (either FK) of either of the
    minor's own two recorded parents; aunt/uncle means a living child
    (either FK) of a grandparent, excluding the minor's own parents.

    STATE WARD FLAG: when no living relative exists in either stage, this
    function returns None, leaves `minor.caretaker_agent` at None, and
    appends the string `"state_ward"` to `minor.conditions`. `conditions`
    (an existing `Agent` JSONField list, normally used for diseases and
    disabilities) is reused as the flag carrier because the plan is
    constrained to zero migrations (SC-005) and this field is otherwise
    unused for the minor at this point -- adding a dedicated boolean field
    would require a migration this plan does not authorize. The treasury
    actually covering the ward's subsistence (`Government.
    government_treasury`) is NOT this function's job: it is the per-tick
    job of the Plan 4 orchestrator, which reads the `"state_ward"` flag
    every tick that follows. Only the flag itself is set here.

    FIX MISS-1 (why this function exists at all): a caretaker only
    ADMINISTERS the minor's estate; the minor keeps direct ownership of
    whatever it inherited. This function enforces that boundary simply by
    never touching `Agent.wealth` on either `minor` or the chosen
    caretaker -- it writes exactly one field, `caretaker_agent`, and nothing
    else. Wealth transfer, if any, already happened earlier in the death
    pipeline via `distribute_estate`; this function never re-opens it.

    NO ADULTHOOD REQUIREMENT ON THE CARETAKER: the design spec is silent
    on whether a chosen caretaker must itself be an adult. This
    implementation imposes none -- a minor sibling can be selected as
    caretaker if it is the nearest living relative. Flagged here
    explicitly for the phase-6 adversarial audit rather than silently
    assumed; resolving it either way is a scientific/design decision, not
    an implementation default this function should invent.

    NO-SAVE CONTRACT (module-wide, matches `distribute_estate`'s "WITHOUT
    persisting" contract, T021): this function mutates the passed `minor`
    instance in memory ONLY -- it never calls `.save()`. Persisting the
    `caretaker_agent` write (and, for the state-ward path, the `conditions`
    write) is the caller's responsibility, exactly like every other
    resolver in this module leaves persistence to its caller.

    DECISION D3 (plan.md, "Pure functions, no global state"): this is one
    of the two Plan 4 orchestrator entry points this plan introduces (the
    other is `migration.py`'s `process_emergency_flight`). Neither module
    decides tick ordering -- that is the orchestrator's job -- so every
    input this function needs is passed explicitly rather than read from
    module-level state. `tick` is accepted for exactly this reason (API
    symmetry with the rest of the Plan 4 orchestrator surface, which
    threads `tick` through every step) but currently plays NO
    computational role inside this function -- there is no tick-dependent
    branch here today. Documented honestly rather than inventing a use
    for it: a future caller (e.g. one that logs a `DemographyEvent` at
    the moment of assignment) may need it, but that is out of this
    function's scope.

    EDGE CASE, untested by design (out of this task's scope): if `minor`
    has no recorded zone (`zone_id is None`), stage 1 is skipped entirely
    -- "same zone as the minor" is not a meaningful comparison when the
    minor itself is not located anywhere, so this falls straight through
    to stage 2 rather than comparing `None == None` against any
    equally-zoneless candidate.

    Args:
        minor: the orphaned minor `Agent` instance. Must be saved (have a
            primary key). The caller (the Plan 4 death orchestrator)
            guarantees `minor` is an orphaned minor -- this function does
            not itself verify age or parental death.
        tick: the current simulation tick, passed through for orchestrator
            API symmetry (decision D3). See the docstring section above --
            it has no computational effect in this implementation.

    Returns:
        The chosen caretaker `Agent`, or `None` when no living relative
        exists anywhere (the state-ward case).

    Query cost contract (bounded, independent of population size -- this
    runs once per newly-orphaned minor, and the Plan 4 orchestrator will
    call it every tick): up to 4 queries total -- (1) `_resolve_sibling_
    heirs` (0 or 1), (2) `_resolve_grandparent_ids` (0 or 1), (3) the
    grandparents' own `Agent` rows, fetched once to read their `zone_id` /
    `birth_tick` for ranking (0 when no grandparent id was found), (4)
    `_resolve_aunts_uncles` (0 or 1). 0 queries total when `minor` has no
    recorded parent at all. Every query filters on a small, already-
    resolved id set (the minor's own parent ids, then grandparent ids)
    rather than scanning the population.
    """
    from epocha.apps.agents.models import Agent

    def _sort_key(agent: Any) -> tuple[int, int]:
        birth_tick = agent.birth_tick if agent.birth_tick is not None else 0
        return (birth_tick, agent.id)

    siblings = _resolve_sibling_heirs(minor)

    parent_ids = [pid for pid in (minor.parent_agent_id, minor.other_parent_agent_id) if pid]
    grandparent_ids = _resolve_grandparent_ids(parent_ids)

    grandparents: list = []
    if grandparent_ids:
        grandparents = sorted(
            Agent.objects.filter(id__in=grandparent_ids, is_alive=True), key=_sort_key
        )

    aunts_uncles_raw = _resolve_aunts_uncles(grandparent_ids, parent_ids)
    aunts_uncles = sorted((agent for agent in aunts_uncles_raw if agent.is_alive), key=_sort_key)

    # Kinship rungs in priority order -- each pool is already living-only
    # and sorted ascending by (birth_tick, id).
    kinship_pools = (siblings, grandparents, aunts_uncles)

    def _first_match(zone_id: int | None) -> Any | None:
        for pool in kinship_pools:
            candidates = pool if zone_id is None else [a for a in pool if a.zone_id == zone_id]
            if candidates:
                return candidates[0]
        return None

    caretaker = None
    if minor.zone_id is not None:
        caretaker = _first_match(minor.zone_id)  # stage 1: same zone
    if caretaker is None:
        caretaker = _first_match(None)  # stage 2: any zone

    minor.caretaker_agent = caretaker
    if caretaker is None:
        minor.conditions.append("state_ward")

    return caretaker


# ---------------------------------------------------------------------------
# Mourning memories (Plan 3, T026/T027, user story 3 -- death leaves a
# mark). Design spec Sezione 5, "Cascata di memoria del lutto": the
# surviving spouse, surviving children, and every living agent tied to the
# deceased by a strong Relationship each receive one first-hand Memory of
# the death. Carrying that memory onward to socially-distant agents is NOT
# this function's job -- it is the existing per-tick `propagate_information`
# system's job (epocha/apps/agents/information_flow.py), which reads
# Memory.origin_agent (see the model's own `memory_propagation_idx` index,
# epocha/apps/agents/models.py) to derive decayed-weight hearsay/rumor
# copies for the wider society. This section only creates the direct,
# first-hand rows; it never calls `propagate_information` itself.
# ---------------------------------------------------------------------------

# Emotional weight assigned to every direct mourning memory. Design spec
# Sezione 5, "Cascata di memoria del lutto": the death of a close relation
# is modeled as a high-intensity, first-hand event -- 0.9 on Memory's own
# [0.0, 1.0] "trivial .. traumatic/ecstatic" scale (see the field's
# help_text, epocha/apps/agents/models.py). A documented, explicitly
# tunable design constant, not a magic number: it sits just below the 1.0
# ceiling, leaving headroom above it for a still more acute personal-
# survival event elsewhere in this plan (Plan 3's emergency-flight trapped-
# crisis memory in migration.py, scoped to a later task, uses a higher
# weight for imminent threat to the agent's own life).
MOURNING_MEMORY_WEIGHT = 0.9

# Strict lower bound (exclusive) on Relationship.strength for an agent to
# qualify as a "strong tie" mourning-memory recipient. Design spec Sezione
# 5: only relationships strong enough that the death is experienced first-
# hand, not merely heard about later, trigger a direct memory here. 0.6
# sits above Relationship.strength's own field midpoint (0.5, "weak" ..
# "very strong", see the field's help_text) -- a documented, explicitly
# tunable design threshold reserving first-hand grief for the upper tier
# of a relationship's strength range. TRAP 2 (verbatim, load-bearing):
# this constant gates `Relationship.strength`, the SOCIAL bond strength
# between two agents -- it must never be confused with `Agent.strength`,
# an unrelated inherited PHYSICAL trait (h^2 = 0.55, the Falconer & Mackay
# 1996 polygenic kernel at the top of this module) measuring how strong an
# agent's body is. Filtering the grief cascade on `Agent.strength` instead
# would deliver memories to muscular strangers instead of close friends --
# a category error, not a rounding difference.
MOURNING_TIE_STRENGTH_THRESHOLD = 0.6


def generate_mourning_memories(deceased: Any, tick: int) -> None:
    """Create one first-hand `Memory` of `deceased`'s death for every
    qualifying recipient (design spec Sezione 5, "Cascata di memoria del
    lutto").

    RECIPIENT CATEGORIES (a recipient qualifying under more than one
    category still receives exactly ONE memory -- see DEDUPLICATION
    below):

    1. Surviving spouse: the partner of `deceased`'s active Couple,
       resolved via `active_couple_for` (couple.py) -- the same helper
       `_resolve_spouse_heirs` uses for the estate ladder, reused here
       rather than re-querying `Couple` directly (DRY). `active_couple_for`
       does NOT itself filter on the partner's own aliveness (a couple
       with the deceased side already nulled by an earlier
       `dissolve_on_death` call is no longer "active", but the partner
       side is never checked) -- this function applies the "only if
       alive" qualifier itself, exactly like `_resolve_spouse_heirs` does.
    2. Surviving children: living agents recorded as having `deceased` as
       EITHER parentage FK (`parent_agent` or `other_parent_agent`) --
       the same "either FK" match `_resolve_children_heirs` uses for the
       estate ladder.
    3. Strong ties: living agents linked to `deceased` by a `Relationship`
       row with `strength > MOURNING_TIE_STRENGTH_THRESHOLD`, in EITHER
       direction (`deceased` as `agent_from` or as `agent_to`). See TRAP 2
       on `MOURNING_TIE_STRENGTH_THRESHOLD` above -- the filter is
       `Relationship.strength`, an inherited PHYSICAL trait on `Agent` is
       never consulted anywhere in this function.

    DEDUPLICATION: recipients are collected into a single `dict` keyed by
    agent id as each category is resolved, so an agent found under two
    categories (e.g. a child who is also recorded as a strong tie) simply
    overwrites its own dict entry and ends up with exactly one row in the
    final `Memory.objects.bulk_create` call, never two.

    DETERMINISM (project invariant -- bit-for-bit reproducibility across
    identically-seeded runs): the recipient dict is built in a fixed
    category order (spouse, then children, then strong ties) and every
    query within a category is itself deterministically ordered by the
    database (children and strong-tie rows are read in whatever stable
    order the query planner returns for a single unordered SELECT, but the
    OUTPUT this function produces -- the `Memory` rows -- is written in
    `agent_id` ascending order: recipients are sorted by id immediately
    before `bulk_create`, never iterated as a bare Python `set`, so the
    database `INSERT` order (and therefore the auto-incrementing `Memory.
    id` values) is reproducible run to run regardless of any incidental
    variation in the recipient-discovery queries' own row order.

    MEMORY ROW SHAPE (mirrors the conventions `information_flow.py`
    already establishes for `Memory` creation): `agent=recipient`,
    `content` an English sentence naming `deceased` (exact wording is this
    function's own choice, not part of the pinned contract),
    `emotional_weight=MOURNING_MEMORY_WEIGHT`,
    `source_type=Memory.SourceType.DIRECT` (first-hand experience, as
    opposed to `HEARSAY`/`RUMOR`/`PUBLIC`), `reliability=1.0` (a first-hand
    grief memory is never uncertain to the person experiencing it),
    `tick_created=tick`, `origin_agent=deceased` (the traceability/
    propagation-index FK `information_flow.py`'s hearsay/rumor derivation
    reads via `Memory.origin_agent`, e.g. its own `memory_propagation_idx`
    composite index).

    PERSISTENCE CONTRACT (nuance vs. this module's usual "no-save"
    resolvers): unlike `resolve_heirs` / `distribute_estate` /
    `assign_orphan_caretaker`, which return a pure value or mutate only
    the passed instance, this function DOES write to the database --
    exactly like `transfer_loans_as_lender` persists `Loan` reassignments
    directly, creating a brand-new `Memory` row has no "pure value"
    representation a caller could sensibly persist later, so the write
    happens here. What this function still never does is call `.save()`
    on the passed `deceased` instance itself -- `deceased` is read-only
    input (its `id`, `name`, and FK columns), never mutated or persisted.

    NO PROPAGATION HERE: this function never imports or calls
    `propagate_information` -- see the module section header above for
    why (that system runs later, per tick, and reads what this function
    wrote via `origin_agent`). An agent with no tie to `deceased` (not a
    spouse, not a child, no qualifying `Relationship`) receives nothing
    from this function, however geographically close (e.g. a same-zone
    agent with no recorded relationship).

    Args:
        deceased: the deceased Agent instance. Must be saved (queried by
            `id`/FK comparisons throughout). Never mutated or saved by
            this function.
        tick: the current simulation tick, written verbatim to every
            created `Memory.tick_created`.

    Returns:
        None. Mutates the database directly (new `Memory` rows); has no
        return value to persist, unlike this module's pure resolvers.

    Query cost contract (bounded, independent of population size -- this
    runs once per death, and the Plan 4 orchestrator will call it every
    tick): up to 5 queries total -- (1) `active_couple_for` (the `Couple`
    lookup), (2) fetching the partner's own `Agent` row (skipped, 0 extra
    queries, when there is no active couple), (3) the children fetch (one
    query, either-FK `Q` filter), (4) the strong-tie fetch (one query: a
    single `Relationship` queryset with an either-direction `Q` filter and
    `select_related("agent_from", "agent_to")` so reading which side is
    the recipient costs no further query), (5) one `Memory.objects.
    bulk_create` (skipped entirely, 0 queries, when no recipient was
    found at all). No per-recipient queries anywhere.
    """
    from epocha.apps.agents.models import Agent, Memory, Relationship
    from epocha.apps.demography.couple import active_couple_for

    recipients: dict[int, Any] = {}

    # Category 1: surviving spouse.
    couple = active_couple_for(deceased)
    if couple is not None:
        partner = couple.agent_b if couple.agent_a_id == deceased.id else couple.agent_a
        if partner is not None and partner.is_alive:
            recipients[partner.id] = partner

    # Category 2: surviving children, either parentage FK.
    children = Agent.objects.filter(
        Q(parent_agent=deceased) | Q(other_parent_agent=deceased), is_alive=True
    )
    for child in children:
        recipients[child.id] = child

    # Category 3: strong ties. TRAP 2 -- Relationship.strength, never
    # Agent.strength (see MOURNING_TIE_STRENGTH_THRESHOLD above). One
    # query for both directions; select_related avoids a further query
    # per relationship when reading which side is the recipient.
    strong_tie_relationships = Relationship.objects.filter(
        Q(agent_from=deceased) | Q(agent_to=deceased),
        strength__gt=MOURNING_TIE_STRENGTH_THRESHOLD,
    ).select_related("agent_from", "agent_to")
    for relationship in strong_tie_relationships:
        tie = (
            relationship.agent_to
            if relationship.agent_from_id == deceased.id
            else relationship.agent_from
        )
        if tie.is_alive:
            recipients[tie.id] = tie

    if not recipients:
        return

    content = f"{deceased.name} has died; the loss is felt first-hand."
    memories = [
        Memory(
            agent=recipient,
            content=content,
            emotional_weight=MOURNING_MEMORY_WEIGHT,
            source_type=Memory.SourceType.DIRECT,
            reliability=1.0,
            tick_created=tick,
            origin_agent=deceased,
        )
        for _, recipient in sorted(recipients.items(), key=lambda item: item[0])
    ]
    Memory.objects.bulk_create(memories)


# ---------------------------------------------------------------------------
# Batch orchestration (Plan 3, T028/T029, user story 3 -- the death-path
# entry point). Design spec Sezione 5: composes every mechanism this
# module built for user stories 1-3 into the single call the Plan 4
# orchestrator's death step (step 2/3 of its canonical six-step tick)
# makes once per tick, given that tick's freshly-deceased agents.
# ---------------------------------------------------------------------------

# Fix I-10 (phase-6 audit round 1, T046): FALLBACK currency code for
# Government.government_treasury credits (a plain {currency_code: amount}
# dict, see world/models.py) -- used ONLY when the simulation has no
# Currency row at all (the "simplified" economy tier, World.economy_level;
# Agent.wealth's own scalar-float layer needs no Currency row to function).
# Before this fix this constant (then named ESTATE_TAX_CURRENCY_CODE) was
# used UNCONDITIONALLY, so any simulation with a REAL primary currency --
# the design's own worked example uses LVR -- had its estate tax and
# heirless-estate credits pile into a "USD" treasury key no spending path
# ever reads: a permanently sequestered 40% of every estate under
# modern_democracy. process_inheritance_batch now resolves the
# simulation's actual primary Currency first (see PRIMARY CURRENCY
# RESOLUTION in that function's own docstring) and falls back to this
# constant only when no Currency row exists.
ESTATE_TAX_CURRENCY_FALLBACK_CODE = "USD"


def process_inheritance_batch(simulation: Any, tick: int, deceased_agents: Any) -> None:
    """Settle every death in `deceased_agents` for this `tick`: dissolve
    couples, settle each estate, transfer loans, generate mourning
    memories, assign caretakers to newly-orphaned minors, and emit one
    `DemographyEvent` per actual heir transfer (design spec Sezione 5).

    THIS IS THE PLAN 4 DEATH-PATH ENTRY POINT (orchestrator step 2/3):
    the only thing this function does NOT do is decide WHO died or WHEN --
    that is entirely the mortality module's and the orchestrator's job.
    This function is called once per tick with that tick's list of
    freshly-deceased agents and settles all of them.

    PRECONDITION (load-bearing throughout, never verified by this
    function itself): every agent in `deceased_agents` already has
    `is_alive=False` (and, where applicable, `death_tick` already set)
    BEFORE this call -- the caller sets it, not this function. This is
    what makes intra-tick chaining through a dead intermediate
    STRUCTURALLY IMPOSSIBLE rather than merely suppressed: `resolve_heirs`
    and every category it delegates to already filter `is_alive=True`, so
    a child who died in this SAME batch is mechanically excluded from
    being anyone's heir, with no special-cased recursion or suppression
    flag needed anywhere in this function (fix MISS-5, both the same-tick
    and the cross-tick case -- an agent who died in an EARLIER tick and is
    simply not `is_alive` behaves identically to one dying in this batch,
    for exactly the same structural reason).

    PROCESSING ORDER (fix C-3, the Simultaneous Death Act convention --
    design spec's OWN fix numbering, predates the phase-6 audit entirely;
    unrelated to this file's separate audit-numbered `T046/C-3` further
    below, the event-payload tax figure fix):
    `deceased_agents` -- which may be a list or a queryset, never assumed
    pre-ordered -- is normalized with `list()` once and sorted `age`
    DESCENDING (oldest first), `id` ASCENDING as the deterministic
    tiebreak for equal age. Processing an empty batch is a no-op (returns
    immediately, before reading `simulation.config` or opening a
    transaction).

    PRIMARY CURRENCY RESOLUTION (fix I-10, phase-6 audit round 1, T046):
    resolved ONCE for the whole batch, before the per-deceased loop --
    `Currency.objects.filter(simulation=simulation, is_primary=True).
    order_by("id").first()`, the exact same query every other treasury-
    adjacent caller in the codebase already uses (`economy/property_
    market.py`, `economy/credit.py`, `economy/context.py` all inline this
    identical filter; there is no shared PUBLIC helper to import instead --
    every existing caller inlines its own copy, so inlining here too is
    the consistent choice). Falls back to `ESTATE_TAX_CURRENCY_FALLBACK_
    CODE` ("USD") only when the simulation has no Currency row at all (the
    "simplified" economy tier). One extra query for the entire batch, not
    per deceased.

    PER-DECEASED STEPS:
    1. `resolve_heirs(deceased, template)`.
    2. `apply_estate_tax(deceased.wealth, rate, government,
       primary_currency_code)` -- `deceased.wealth` IS the estate's total
       cash value; this is the one place in the whole chain that decides
       that wiring (every pure resolver upstream takes `total_estate_value`
       as an opaque float precisely so this orchestrator, not they, makes
       that call).
    3. `distribute_estate(deceased, heirs, rule, inheritable)`.
    4. Accumulate this transfer into the batch-wide pending wealth-credit
       ledger (see WEALTH CREDITING below) rather than crediting
       immediately -- the same living heir may inherit from a SECOND
       decedent later in this same batch (the two-independent-transfers
       case), and crediting immediately per deceased would require a
       second read-modify-write that could double-apply or lose a credit
       under `bulk_update`'s all-at-once semantics.
    5. `transfer_loans_as_lender(deceased, heirs, allocation,
       matrilineal_heirs=matrilineal_heirs)` -- fix I-6: `allocation`
       (step 3's own result) is threaded straight through, so loans follow
       the exact same rule-entitled heir set cash just did. Fix NEW-7
       (phase-6 audit round 4, T046): `matrilineal_heirs` -- resolved ONCE,
       right after step 1, only when `rule == "matrilineal"` -- is ALSO
       threaded into both this call and step 3's `distribute_estate` call,
       so the sister-resolution query this rule needs is paid exactly
       once per deceased, not once per consumer.
    6. `generate_mourning_memories(deceased, tick)`.
    7. `dissolve_on_death(deceased, tick)` (decision D1) -- deliberately
       LAST among these steps, not first; see ORDERING CORRECTION below.
       Idempotent per partner, so this correctly handles fix MISS-4 (both
       partners of one Couple dying in the same batch) with no special-
       casing here: each call is safe regardless of whether the partner
       already died earlier in this same loop.
    8. Record every living child (`heirs["children"]`) as an orphan
       CANDIDATE for the caretaker pass below -- not yet acted on.

    ORDERING CORRECTION (discovered running T028's own RED tests against
    a first implementation that called `dissolve_on_death` FIRST, per a
    literal reading of the task's step list -- flagged here rather than
    silently fixed without a trace): `resolve_heirs`'s spouse category
    (`_resolve_spouse_heirs`) and `generate_mourning_memories`'s spouse
    recipient BOTH resolve the surviving partner through
    `active_couple_for(deceased)`, which only finds a `Couple` with
    `dissolved_at_tick__isnull=True`. Calling `dissolve_on_death` before
    either of them already nulls `deceased`'s own side of the `Couple` FK
    and sets `dissolved_at_tick` -- making the couple invisible to both
    lookups and silently discarding a living spouse's inheritance AND
    mourning memory, contradicting the design spec's own heir-priority
    item 1 (spouse first). `dissolve_on_death` itself is safe to call
    after both reads: `_resolve_spouse_heirs`'s own docstring already
    documents the nulled-FK case as a defensive guard for exactly this
    kind of call-order variation, so moving it here changes no other
    function's contract -- only the position of this call within THIS
    orchestrator's own sequence.

    CARETAKER ASSIGNMENT COMES LAST, AFTER EVERY DECEASED ABOVE IS FULLY
    PROCESSED (settled ordering decision): a minor orphaned by the LAST
    death in the batch must still be caught, and the "does this candidate
    still have a living parent" check must see the batch's FINAL
    aliveness state, not a partial one. Scoped to `heirs["children"]`
    collected during the loop above -- NOT a population-wide scan -- so
    the cost is bounded by this batch's own deaths, never by total
    population size. A candidate is actually orphaned and gets
    `assign_orphan_caretaker(child, tick)` called on it (T025's own
    contract: mutates `child` in memory only, never saves) when ALL of:
    it does not already have a `caretaker_agent`; it is a minor
    (`child.age < template["migration"]["adulthood_age"]`); and NEITHER
    of its own two recorded parents is still alive (checked with ONE
    query across every candidate's parent ids, never per-candidate).
    `assign_orphan_caretaker` itself still costs its own documented
    up-to-4-query search PER actual orphan (inherent to reusing that pure
    resolver rather than reimplementing its kinship ladder here) -- see
    QUERY BUDGET below.

    FAMILY-TOPOLOGY SCOPE (ratified 2026-07-20, logged for the phase-6
    audit as an open question, NOT a defect to fix here): orphan
    candidates are `heirs["children"]` ONLY -- the deceased's OWN
    grandchildren are never candidates, because `resolve_heirs` has no
    category that reaches two generations down (`extended_family` reaches
    the deceased's own grandparents' lineage, never descendants of the
    deceased's own children). This is a property of the CONVERGED design,
    not something this task is scoped to change.

    WEALTH CREDITING AND ZEROING (T028's persistence pin): after the full
    per-deceased loop, every deceased's wealth is set to exactly 0.0 and
    every credited heir's wealth is their PRE-BATCH database value plus
    the SUM of every transfer they received in this batch (one or more),
    computed with exactly ONE fresh `Agent.objects.filter(id__in=...)`
    read and ONE `Agent.objects.bulk_update(..., ["wealth"])` write for
    the WHOLE batch -- never a per-heir or per-deceased `.save()`. A
    transfer of exactly 0.0 (a heir-bearing but valueless estate) credits
    nothing and emits no event -- see ZERO-VALUE TRANSFERS below.

    ZERO-VALUE TRANSFERS: `distribute_estate` returns a non-empty
    allocation (e.g. `{heir.id: 0.0}`) for a heir-bearing estate whose
    `inheritable` happens to be 0.0 (a deceased with no wealth) -- this is
    NOT the same as the empty-`{}` "route to treasury" case (see
    `distribute_estate`'s own EMPTY ALLOCATION SHAPE note). This function
    treats a 0.0 allocation entry as nothing happened: no wealth credit,
    no `DemographyEvent` (an "actual heir transfer" moves value; a
    transfer of nothing is not one). Symmetrically, the empty-allocation
    treasury fallback is skipped when `inheritable` is 0.0 -- crediting
    0.0 to the treasury would cost a wasted `add_to_treasury` write for no
    observable effect.

    EVENT PAYLOAD (design spec Sezione 5, DemographyEvent payload
    schemas, `inheritance_transfer` row, line 1221 of the design spec):
    one `DemographyEvent(event_type=INHERITANCE_TRANSFER, simulation=
    simulation, tick=tick, primary_agent=deceased, secondary_agent=heir)`
    per actual (non-zero) transfer, with `payload = {"deceased_id",
    "heir_id", "assets": {"cash", "property_ids", "loans_as_lender"},
    "estate_tax_applied", "rule_used"}`. The design spec names these keys
    but not their exact semantics; this implementation PINS (per T028's
    own ratified decision): `cash` is this specific transfer's post-tax
    amount; `estate_tax_applied` is the ABSOLUTE tax amount ACTUALLY
    credited to the treasury by `apply_estate_tax` (fix T046/C-3, phase-6
    audit round 1: `total_estate_value - inheritable`, which reproduces
    `apply_estate_tax`'s own internally-clamped rate exactly via its
    conservation contract, never the raw unclamped
    `economic_inheritance.estate_tax_rate` template value) deducted from
    the deceased's WHOLE estate -- identical across every event sharing
    the same `deceased`, never a per-heir proportional fraction, since the
    design spec does not define one and inventing an unrequested split
    would be worse than repeating the estate-level figure; `rule_used` is
    the era template's
    `economic_inheritance.rule` string. `property_ids` and
    `loans_as_lender` are populated as empty lists -- a documented MVP
    simplification: no property-transfer mechanism exists in this module
    (property ownership is untouched by this function), and
    `transfer_loans_as_lender` persists loan reassignments directly
    without returning which specific loan ids moved to which heir,
    re-deriving that per event would cost an extra query per transfer for
    a value the settled contract explicitly leaves to this
    implementation's discretion. Events are appended to a list during the
    per-deceased loop (deterministic: deceased processed oldest-first,
    heirs within one deceased's allocation in `id` ascending order) and
    written with exactly ONE `DemographyEvent.objects.bulk_create` for the
    whole batch, never per-event `.save()`.

    TRANSACTION (conservation invariant, non-negotiable): the ENTIRE batch
    -- every `dissolve_on_death` call, every `apply_estate_tax` /
    `add_to_treasury` write, the wealth bulk_update, every
    `transfer_loans_as_lender` write, every `generate_mourning_memories`
    bulk_create, the caretaker bulk_update, and the final event
    bulk_create -- runs inside one `django.db.transaction.atomic()` block.
    A failure partway through rolls back everything, so an estate can
    never be left half-settled (e.g. treasury credited but heir wealth
    not, or vice versa) at any commit boundary reachable from outside this
    function.

    QUERY BUDGET (bounded per deceased, documented honestly): per
    deceased, roughly `dissolve_on_death`'s own cost (up to 2) +
    `resolve_heirs`'s own cost (up to 7) + 1 for `apply_estate_tax`'s
    treasury write (0 when the estate is non-positive) +
    `transfer_loans_as_lender`'s own cost (up to 2) +
    `generate_mourning_memories`'s own cost (up to 5). PLUS, once for the
    whole batch (not per deceased): 1 query to resolve the primary
    currency (fix I-10), 1 fetch + 1 `bulk_update` for wealth, 1 query + 1
    `bulk_update` for caretakers (skipped entirely when there are no
    orphan candidates), 1 `bulk_create` for events. On top of that,
    each ACTUAL newly-orphaned minor costs `assign_orphan_caretaker`'s own
    up-to-4-query search, AND -- fix NEW-7 (phase-6 audit round 4, T046) --
    each death under the `matrilineal` rule specifically costs one
    ADDITIONAL query per the deceased's own sister: resolved exactly ONCE
    here (right after `resolve_heirs`, step 1) and threaded into both
    `distribute_estate` and `transfer_loans_as_lender` via their shared
    `matrilineal_heirs=` keyword, so this rule's own sister-count cost is
    paid once per matrilineal death, not once per consumer of it (the
    pre-NEW-7 shape doubled it: 6 queries measured for four sisters, one
    niece, one loan, against a docstring that still claimed "up to 2").
    Zero for the other four rules. TOTAL COST SCALES LINEARLY WITH THE
    NUMBER OF DEATHS THIS TICK (and, for the caretaker pass, with the
    number of actual new orphans; for matrilineal deaths, with the
    deceased's own sibling count) -- NEVER quadratically, and never with
    total simulation population, since every query in this function
    filters on an already-resolved, batch-scoped id set.

    Args:
        simulation: the Simulation instance. Supplies `.config` (read for
            `demography_template`, same convention as
            `apply_inheritance_at_birth`) and is written onto every
            `DemographyEvent.simulation`.
        tick: the current simulation tick.
        deceased_agents: an iterable (list or queryset) of Agent
            instances, each already `is_alive=False` before this call.
            Normalized to a list and sorted once; never assumed
            pre-ordered.

    Returns:
        None. Persists directly -- unlike this module's pure resolvers,
        this IS the orchestrated entry point.
    """
    from django.db import transaction

    from epocha.apps.agents.models import Agent
    from epocha.apps.demography.couple import dissolve_on_death
    from epocha.apps.demography.models import DemographyEvent
    from epocha.apps.demography.template_loader import load_template
    from epocha.apps.economy.models import Currency
    from epocha.apps.world.government import add_to_treasury
    from epocha.apps.world.models import Government

    ordered_deceased = sorted(list(deceased_agents), key=lambda agent: (-agent.age, agent.id))
    if not ordered_deceased:
        return

    template_name = simulation.config.get("demography_template", "pre_industrial_christian")
    template = load_template(template_name)
    rate = template["economic_inheritance"]["estate_tax_rate"]
    rule = template["economic_inheritance"]["rule"]

    # Fix I-10: resolve the simulation's REAL primary currency once for the
    # whole batch (one extra query total, not per deceased) -- see
    # PRIMARY CURRENCY RESOLUTION above for why this mirrors economy/
    # property_market.py, economy/credit.py, and economy/context.py's own
    # identical inline query rather than a new cross-app helper.
    primary_currency = (
        Currency.objects.filter(simulation=simulation, is_primary=True).order_by("id").first()
    )
    primary_currency_code = (
        primary_currency.code if primary_currency is not None else ESTATE_TAX_CURRENCY_FALLBACK_CODE
    )
    adulthood_age = template["migration"]["adulthood_age"]

    with transaction.atomic():
        government = Government.objects.get(simulation=simulation)

        deceased_ids = {deceased.id for deceased in ordered_deceased}
        pending_credits: dict[int, float] = {}
        events_to_create: list[Any] = []
        orphan_candidates: dict[int, Any] = {}

        for deceased in ordered_deceased:
            # dissolve_on_death runs LAST among this deceased's Couple-
            # touching steps, not first -- see the docstring's ORDERING
            # CORRECTION note. resolve_heirs's spouse category and
            # generate_mourning_memories's spouse recipient both resolve
            # the partner through active_couple_for(deceased), which only
            # finds a couple with dissolved_at_tick__isnull=True; calling
            # dissolve_on_death first would already have nulled deceased's
            # own side and set dissolved_at_tick, making the couple
            # invisible to both lookups and silently discarding a living
            # spouse's inheritance and mourning memory.
            heirs = resolve_heirs(deceased, template)

            # Fix NEW-7 (phase-6 audit round 4, T046): resolved ONCE here,
            # threaded into both distribute_estate and transfer_loans_as_
            # lender below via their shared matrilineal_heirs= keyword, so
            # this rule's own sister-count query cost is paid exactly once
            # per matrilineal death, not once per consumer of it (see
            # transfer_loans_as_lender's own docstring for the full
            # before/after query-count account). None, and no query at
            # all, for every other rule.
            matrilineal_heirs = _resolve_matrilineal_heirs(heirs) if rule == "matrilineal" else None

            total_estate_value = deceased.wealth
            inheritable = apply_estate_tax(
                total_estate_value, rate, government, primary_currency_code
            )
            # Fix T046/C-3 (phase-6 audit round 1): derive the tax actually
            # applied from apply_estate_tax's own conservation contract
            # (total_estate_value == inheritable + tax_revenue, exactly,
            # per that function's own docstring) instead of recomputing
            # `total_estate_value * rate` with the RAW, unclamped template
            # rate. apply_estate_tax clamps rate into [0, 1] internally
            # before crediting the treasury -- a malformed rate (e.g. "40"
            # typed instead of "0.40") would otherwise make this payload
            # report a figure up to 100x the amount the treasury actually
            # received. total_estate_value - inheritable reproduces the
            # CLAMPED tax exactly, with no duplicated clamping logic and no
            # change to apply_estate_tax's own signature.
            tax_amount = (total_estate_value - inheritable) if total_estate_value > 0.0 else 0.0

            allocation = distribute_estate(
                deceased, heirs, rule, inheritable, matrilineal_heirs=matrilineal_heirs
            )

            if allocation:
                for heir_id, amount in sorted(allocation.items()):
                    if amount <= 0.0:
                        continue
                    pending_credits[heir_id] = pending_credits.get(heir_id, 0.0) + amount
                    events_to_create.append(
                        DemographyEvent(
                            simulation=simulation,
                            tick=tick,
                            event_type=DemographyEvent.EventType.INHERITANCE_TRANSFER,
                            primary_agent=deceased,
                            secondary_agent_id=heir_id,
                            payload={
                                "deceased_id": deceased.id,
                                "heir_id": heir_id,
                                "assets": {
                                    "cash": amount,
                                    "property_ids": [],
                                    "loans_as_lender": [],
                                },
                                "estate_tax_applied": tax_amount,
                                "rule_used": rule,
                            },
                        )
                    )
            elif inheritable > 0.0:
                # Empty allocation: no living heir (every category
                # exhausted) or the nationalized rule (always empty by
                # design) -- either way, distribute_estate's own contract
                # is that the entire post-tax remainder routes to the
                # treasury.
                add_to_treasury(government, primary_currency_code, inheritable)

            transfer_loans_as_lender(
                deceased, heirs, allocation, matrilineal_heirs=matrilineal_heirs
            )
            generate_mourning_memories(deceased, tick)

            # Safe to dissolve now: both couple-dependent reads above have
            # already run. dissolve_on_death is idempotent per partner
            # (T002/D1), so calling it here, once per deceased, correctly
            # handles fix MISS-4 regardless of which of the two partners
            # this loop reaches first.
            dissolve_on_death(deceased, tick)

            for child in heirs.get("children", []):
                orphan_candidates[child.id] = child

        # Wealth: one fresh read + one bulk_update for the whole batch,
        # never per-agent .save(). Deceased always end at exactly 0.0;
        # a heir's final wealth is their pre-batch database value plus
        # every credit accumulated above, however many decedents
        # contributed one.
        wealth_touched_ids = deceased_ids | set(pending_credits.keys())
        if wealth_touched_ids:
            agents_for_wealth = list(Agent.objects.filter(id__in=wealth_touched_ids))
            for agent in agents_for_wealth:
                base = 0.0 if agent.id in deceased_ids else agent.wealth
                agent.wealth = base + pending_credits.get(agent.id, 0.0)
            Agent.objects.bulk_update(agents_for_wealth, ["wealth"])

        # Caretaker assignment LAST -- see the docstring's CARETAKER
        # ASSIGNMENT section for why. Bounded to this batch's own
        # children, never a population-wide scan.
        if orphan_candidates:
            parent_ids_to_check = set()
            for child in orphan_candidates.values():
                if child.parent_agent_id:
                    parent_ids_to_check.add(child.parent_agent_id)
                if child.other_parent_agent_id:
                    parent_ids_to_check.add(child.other_parent_agent_id)

            still_alive_parent_ids = (
                set(
                    Agent.objects.filter(id__in=parent_ids_to_check, is_alive=True).values_list(
                        "id", flat=True
                    )
                )
                if parent_ids_to_check
                else set()
            )

            minors_to_update = []
            for child_id in sorted(orphan_candidates):
                child = orphan_candidates[child_id]
                if child.caretaker_agent_id is not None:
                    continue
                if child.age >= adulthood_age:
                    continue
                has_living_parent = (
                    child.parent_agent_id in still_alive_parent_ids
                    or child.other_parent_agent_id in still_alive_parent_ids
                )
                if has_living_parent:
                    continue
                assign_orphan_caretaker(child, tick)
                minors_to_update.append(child)

            if minors_to_update:
                Agent.objects.bulk_update(minors_to_update, ["caretaker_agent", "conditions"])

        if events_to_create:
            DemographyEvent.objects.bulk_create(events_to_create)
