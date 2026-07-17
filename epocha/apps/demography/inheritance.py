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
