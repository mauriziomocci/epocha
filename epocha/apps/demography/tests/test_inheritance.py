"""Unit tests for demography/inheritance.py.

Covers the polygenic additive inheritance kernel `inherit_trait`:
- two-parent midparent formula with an exact RNG-predicted expected value
- clamping of the raw result into [lo, hi]
- fix I-1 single-parent fallback (child_T = h2 * parent_T + (1 - h2) * noise)

Scientific reference: Falconer, D.S. & Mackay, T.F.C. (1996), Introduction
to Quantitative Genetics (4th ed.), Longman, chapter 8 (polygenic additive
model with environmental noise term).

Also covers `evaluate_derived_formula` (SC-006), the restricted AST-based
evaluator used to compute derived-trait formulas (design spec Sezione 4,
e.g. the `cunning` Machiavellism proxy) without exposing an eval() injection
surface.
"""

from __future__ import annotations

import random

import pytest

from epocha.apps.demography.inheritance import evaluate_derived_formula, inherit_trait


class TestInheritTraitTwoParents:
    """Two known parents: exact midparent + single-draw noise formula."""

    def test_matches_hand_computed_formula_with_seeded_rng(self):
        """h2 * midparent + (1 - h2) * noise, noise = rng.gauss(era_mean, era_sd).

        The expected value is computed independently with an identically
        seeded random.Random so the assertion is exact (mirrors the RNG
        sequence the implementation is expected to draw from), not merely
        plausible.
        """
        mother_val = 0.60
        father_val = 0.40
        h2 = 0.45
        era_mean = 0.50
        era_sd = 0.10

        expected_rng = random.Random(1234)
        expected_noise = expected_rng.gauss(era_mean, era_sd)
        midparent = (mother_val + father_val) / 2
        expected = h2 * midparent + (1 - h2) * expected_noise

        actual_rng = random.Random(1234)
        actual = inherit_trait(mother_val, father_val, h2, era_mean, era_sd, actual_rng)

        assert actual == pytest.approx(expected)

    def test_draws_gauss_exactly_once(self):
        """A single rng.gauss draw is consumed per call.

        Verified indirectly: two identically seeded RNGs, one consumed by
        inherit_trait and one consumed by a single manual gauss draw, must
        be left in the same state (their next draw agrees).
        """
        rng_under_test = random.Random(99)
        rng_reference = random.Random(99)

        inherit_trait(0.5, 0.5, 0.5, 0.5, 0.1, rng_under_test)
        rng_reference.gauss(0.5, 0.1)

        # Both RNGs must now be positioned identically: their next draw matches.
        assert rng_under_test.random() == rng_reference.random()


class TestInheritTraitClamping:
    """Clamp the raw polygenic result into [lo, hi] (default [0.0, 1.0])."""

    def test_clamps_above_hi(self):
        """Parents/h2/era chosen so the raw value exceeds 1.0; result is exactly 1.0."""
        # midparent = 1.0 (both parents at the trait ceiling), h2 = 1.0 removes
        # the noise term entirely and would give exactly 1.0 without help, so
        # push further: use an era_mean above the ceiling to force the raw
        # value above hi even with h2 < 1.
        mother_val = 1.0
        father_val = 1.0
        h2 = 0.5
        era_mean = 5.0  # far above hi=1.0, guarantees raw > 1.0 regardless of noise sign
        era_sd = 0.01

        rng = random.Random(7)
        result = inherit_trait(mother_val, father_val, h2, era_mean, era_sd, rng)

        assert result == 1.0

    def test_clamps_below_lo(self):
        """Parents/h2/era chosen so the raw value drops below 0.0; result is exactly 0.0."""
        mother_val = 0.0
        father_val = 0.0
        h2 = 0.5
        era_mean = -5.0  # far below lo=0.0, guarantees raw < 0.0 regardless of noise sign
        era_sd = 0.01

        rng = random.Random(7)
        result = inherit_trait(mother_val, father_val, h2, era_mean, era_sd, rng)

        assert result == 0.0

    def test_custom_bounds_are_respected(self):
        """Non-default lo/hi clamp the result into the custom range."""
        rng = random.Random(3)
        result = inherit_trait(
            0.5, 0.5, 0.5, era_mean=100.0, era_sd=0.01, rng=rng, lo=-10.0, hi=10.0
        )
        assert result == 10.0


class TestInheritTraitSingleParentFallback:
    """Fix I-1: exactly one known parent halves the genetic signal."""

    def test_mother_only_uses_mother_as_parent_t(self):
        """father_val is None: child_T = h2 * mother_val + (1 - h2) * noise."""
        mother_val = 0.70
        h2 = 0.4
        era_mean = 0.5
        era_sd = 0.1

        expected_rng = random.Random(42)
        expected_noise = expected_rng.gauss(era_mean, era_sd)
        expected = h2 * mother_val + (1 - h2) * expected_noise

        actual_rng = random.Random(42)
        actual = inherit_trait(mother_val, None, h2, era_mean, era_sd, actual_rng)

        assert actual == pytest.approx(expected)

    def test_father_only_uses_father_as_parent_t(self):
        """mother_val is None: child_T = h2 * father_val + (1 - h2) * noise."""
        father_val = 0.30
        h2 = 0.4
        era_mean = 0.5
        era_sd = 0.1

        expected_rng = random.Random(42)
        expected_noise = expected_rng.gauss(era_mean, era_sd)
        expected = h2 * father_val + (1 - h2) * expected_noise

        actual_rng = random.Random(42)
        actual = inherit_trait(None, father_val, h2, era_mean, era_sd, actual_rng)

        assert actual == pytest.approx(expected)

    def test_single_parent_does_not_raise(self):
        """Sanity check: single-parent calls complete without exception."""
        rng = random.Random(0)
        result = inherit_trait(0.5, None, 0.3, 0.5, 0.1, rng)
        assert isinstance(result, float)


class TestEvaluateDerivedFormulaHappyPath:
    """Arithmetic-only formulas resolve against the provided symbol table."""

    def test_matches_hand_computed_cunning_formula(self):
        """The actual `cunning` (Machiavellism proxy) derived-trait formula.

        cunning = 0.4*(1-agreeableness) + 0.3*neuroticism + 0.3*intelligence
        (design spec Sezione 4). Expected value computed independently in
        plain Python arithmetic from the same symbol values passed in.
        """
        symbols = {"agreeableness": 0.2, "neuroticism": 0.7, "intelligence": 0.8}
        expected = (
            0.4 * (1 - symbols["agreeableness"])
            + 0.3 * symbols["neuroticism"]
            + 0.3 * symbols["intelligence"]
        )

        result = evaluate_derived_formula(
            "0.4*(1-agreeableness) + 0.3*neuroticism + 0.3*intelligence", symbols
        )

        assert result == pytest.approx(expected)

    def test_unary_minus_resolves(self):
        """Simple arithmetic with a leading unary minus works."""
        symbols = {"neuroticism": 0.7}
        expected = -symbols["neuroticism"] + 1

        result = evaluate_derived_formula("-neuroticism + 1", symbols)

        assert result == pytest.approx(expected)


class TestEvaluateDerivedFormulaRefusals:
    """Security-critical: the evaluator must refuse anything beyond arithmetic.

    Five distinct refusal categories plus an unresolvable bare name, all of
    which must raise rather than silently degrade or execute arbitrary code.
    """

    def test_refuses_function_call(self):
        """A function call (e.g. abs(...)) is not arithmetic and must raise."""
        with pytest.raises(Exception):
            evaluate_derived_formula("abs(intelligence)", {"intelligence": 0.8})

    def test_refuses_attribute_access(self):
        """Attribute access (e.g. .__class__) is a potential injection vector."""
        with pytest.raises(Exception):
            evaluate_derived_formula("intelligence.__class__", {"intelligence": 0.8})

    def test_refuses_dunder_bare_name(self):
        """A bare dunder name not present in symbols must raise.

        __import__ is not a symbol supplied by any caller, so it is refused
        on the same path as any other unknown name -- there is no special
        casing that would let a dunder name resolve.
        """
        with pytest.raises(Exception):
            evaluate_derived_formula("__import__", {"intelligence": 0.8})

    def test_refuses_subscript(self):
        """Subscript access (e.g. name[0]) is refused."""
        with pytest.raises(Exception):
            evaluate_derived_formula("intelligence[0]", {"intelligence": 0.8})

    def test_refuses_comprehension(self):
        """List/set/dict/generator comprehensions are refused."""
        with pytest.raises(Exception):
            evaluate_derived_formula("[x for x in (1,2)]", {"intelligence": 0.8})

    def test_refuses_unknown_bare_name(self):
        """A bare name absent from the symbol table must raise, not resolve to 0."""
        with pytest.raises(Exception):
            evaluate_derived_formula("unknown_trait", {"intelligence": 0.8})
