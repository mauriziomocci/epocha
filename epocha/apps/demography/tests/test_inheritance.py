"""Unit tests for demography/inheritance.py.

Covers the polygenic additive inheritance kernel `inherit_trait`:
- two-parent midparent formula with an exact RNG-predicted expected value
- clamping of the raw result into [lo, hi]
- fix I-1 single-parent fallback (child_T = h2 * parent_T + (1 - h2) * noise)
  -- design spec's own numbering, unrelated to this file's separate
  audit-numbered `T046/I-1` (the social-class rank clamp)

Scientific reference: Falconer, D.S. & Mackay, T.F.C. (1996), Introduction
to Quantitative Genetics (4th ed.), Longman, chapter 8 (polygenic additive
model with environmental noise term).

Also covers `evaluate_derived_formula` (SC-006), the restricted AST-based
evaluator used to compute derived-trait formulas (design spec Sezione 4,
e.g. the `cunning` Machiavellism proxy) without exposing an eval() injection
surface.

Also covers `apply_trait_inheritance` (Plan 3, T008/T009), the birth-pipeline
orchestrator that applies the polygenic pass to every heritable trait (scalar
Agent fields and Agent.personality JSONB entries alike) and then evaluates
`derived_trait_formulas` (e.g. `cunning`) against the freshly inherited
values, per the "Responsibility contract" in the design spec (Sezione 4).

Also covers `apply_social_inheritance` (Plan 3, T012/T013), the social-class
transmission and education-level regression mechanism (design spec Sezione
5): the four `class_rule` branches (patrilineal_rigid -- Goody 1976, Wrigley
1981; clark_regression -- Clark 2014; becker_tomes_elasticity_0.4 -- Solon
1999, Chetty et al. 2014; meritocratic -- speculative sci_fi design choice)
and the education-level regression toward the era mean that runs after
every rule.

Also covers `resolve_heirs` (Plan 3, T016/T017, user story 2 -- estate
succession) and `apply_estate_tax` (Plan 3, T018/T019, user story 2): the
flat estate tax routed to the government treasury before the remainder is
split among the resolved heirs (design spec Sezione 5, "Ereditarietà
economica alla morte"; the modern-democracy 0.40 rate corresponds to
Piketty, T. (2014), "Capital in the Twenty-First Century", tables
14.1-14.2).

Also covers `distribute_estate` (Plan 3, T020/T021, user story 2): the five
per-era succession rules that decide HOW the inheritable remainder is split
among `resolve_heirs`'s resolved heirs -- `primogeniture` (Blackstone, W.
(1765), "Commentaries on the Laws of England"), `equal_split` (Napoleonic
Code, 1804), `shari'a` (Powers, D.S. (1986), "Studies in Qur'an and Hadith:
The Formation of the Islamic Law of Inheritance"), `matrilineal` (Schneider,
D.M. & Gough, K. (1961), "Matrilineal Kinship"), and `nationalized` (Nove,
A. (1969), "An Economic History of the USSR").

Also covers `assign_orphan_caretaker` (Plan 3, T024/T025, user story 3 --
orphan caretaker assignment): the two-stage priority ladder (same zone,
then any zone, each walked sibling > grandparent > aunt/uncle), the
deterministic birth_tick/id tiebreak within a kinship rung, the state-ward
fallback (conditions flag) when no living relative exists anywhere, the
module-wide no-persistence contract, and fix MISS-1 -- the orphan keeps
direct ownership of its inheritance, the caretaker only administers
(design spec Sezione 5, "Gestione orfani (fix MISS-1)").

Also covers `generate_mourning_memories` (Plan 3, T026/T027, user story 3
-- death leaves a mark): surviving spouse, surviving children, and strong
ties (`Relationship.strength > 0.6`, either direction) each receive one
`Memory` with `emotional_weight = 0.9`, deduplicated when an agent
qualifies under more than one category. Trap 2: the filter is
`Relationship.strength`, NOT `Agent.strength` (an inherited physical
trait, h^2 = 0.55) -- filtering on the wrong field would send grief
memories to muscular agents instead of close friends (design spec Sezione
5, "Cascata di memoria del lutto").

Also covers `process_inheritance_batch` (Plan 3, T028/T029, user story 3
-- the death-path orchestrator): multiple same-tick deaths process oldest
(by `age`) first, `id` ascending tiebreak (fix C-3 -- design spec's own
numbering, unrelated to this file's separate audit-numbered `T046/C-3`,
the event-payload tax figure); estate tax applies
exactly once per actual heir transfer, never cumulatively when the same
living heir inherits from two different same-tick decedents; a dead
intermediate (same tick or an earlier one) is never a bequest conduit,
because every resolver already filters `is_alive=True` (fix MISS-5); one
`DemographyEvent` of type `INHERITANCE_TRANSFER` per actual transfer; the
batch composes `dissolve_on_death`, the estate chain
(`resolve_heirs`/`apply_estate_tax`/`distribute_estate`),
`transfer_loans_as_lender`, `assign_orphan_caretaker`, and
`generate_mourning_memories`, including the MISS-4 case where both
partners of one couple die in the same batch. PRECONDITION, load-bearing
throughout this section: every agent passed in `deceased_agents` already
has `is_alive=False` BEFORE the call -- the caller (Plan 4's mortality
step) sets it, not this function.

Also covers the SC-004 era coverage gate (Plan 3, T041, Phase 8 closure):
all five era templates drive BOTH the inheritance path
(`process_inheritance_batch`) and the migration path
(`coordinate_family_migration`, `evaluate_emergency_flight`) without
error, each asserted against era-appropriate outcomes -- estate tax rate,
succession rule signature, adulthood_age, and flight_trigger_ticks --
never merely "does not raise".
"""

from __future__ import annotations

import json
import logging
import os
import random
import subprocess
import sys

import pytest
from django.contrib.gis.geos import Point, Polygon

from epocha.apps.agents.models import Agent, Memory, Relationship
from epocha.apps.demography.couple import form_couple
from epocha.apps.demography.inheritance import (
    DEFAULT_ERA_MEAN,
    DEFAULT_ERA_MEAN_EDUCATION,
    DEFAULT_ERA_SD,
    FormulaError,
    apply_estate_tax,
    apply_inheritance_at_birth,
    apply_social_inheritance,
    apply_trait_inheritance,
    assign_orphan_caretaker,
    distribute_estate,
    evaluate_derived_formula,
    generate_mourning_memories,
    inherit_trait,
    process_inheritance_batch,
    resolve_birth_attributes,
    resolve_heirs,
    transfer_loans_as_lender,
)
from epocha.apps.demography.migration import (
    coordinate_family_migration,
    evaluate_emergency_flight,
)
from epocha.apps.demography.models import Couple, DemographyEvent
from epocha.apps.demography.rng import get_seeded_rng
from epocha.apps.demography.template_loader import load_template
from epocha.apps.economy.models import Currency, Loan
from epocha.apps.simulation.models import Simulation
from epocha.apps.users.models import User
from epocha.apps.world.government import add_to_treasury
from epocha.apps.world.models import Government, World, Zone


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
    """Fix I-1 (design spec's own numbering, NOT this file's separate
    audit-numbered `T046/I-1`): exactly one known parent halves the
    genetic signal."""

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


class TestInheritTraitBothParentsUnknown:
    """Fix I-3 (phase-6 audit round 1, T046): `inherit_trait(None, None,
    ...)` must fall back to `era_mean` instead of raising `TypeError`.

    Before this fix, the two-branch `if mother_val is not None and
    father_val is not None / elif mother_val is not None / else` chain
    left `midparent = father_val` on the final `else`, so when BOTH
    parent values are None, `midparent` is None too, and the `h2 *
    midparent` arithmetic two lines later raises `TypeError: unsupported
    operand type(s) for *: 'float' and 'NoneType'`. This state is
    reachable from the real birth pipeline: none of the five Big Five
    personality traits is an `Agent` model column, so their values come
    from `(parent.personality or {}).get(name)` in `apply_trait_
    inheritance`, which is None whenever neither parent happens to carry
    that particular key -- any such birth crashes uncaught. The fix
    mirrors `_regress_education_level`'s already-correct four-way
    fallback (mother-only / father-only / both / neither -> era_mean).
    """

    def test_both_parents_none_falls_back_to_era_mean_instead_of_raising(self):
        h2 = 0.4
        era_mean = 0.5
        era_sd = 0.1

        expected_rng = random.Random(11)
        expected_noise = expected_rng.gauss(era_mean, era_sd)
        # No parental signal: midparent degrades to era_mean itself, exactly
        # mirroring _regress_education_level's own neither-parent branch.
        expected = h2 * era_mean + (1 - h2) * expected_noise

        actual_rng = random.Random(11)
        actual = inherit_trait(None, None, h2, era_mean, era_sd, actual_rng)

        assert actual == pytest.approx(expected)

    def test_both_parents_none_still_draws_gauss_exactly_once(self):
        """RNG-sequence contract preserved: the neither-parent branch must
        not change how many draws this function consumes, or every OTHER
        trait's RNG position downstream in apply_trait_inheritance's fixed
        draw order would silently shift.
        """
        rng_under_test = random.Random(99)
        rng_reference = random.Random(99)

        inherit_trait(None, None, 0.5, 0.5, 0.1, rng_under_test)
        rng_reference.gauss(0.5, 0.1)

        assert rng_under_test.random() == rng_reference.random()


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


class TestEvaluateDerivedFormulaExhaustionVector:
    """Fix M-1 (phase-6 audit round 1, T046): `ast.Pow` must be refused.

    `9**9**9` is right-associative (`9**(9**9)`), producing an integer with
    over 369 million digits -- the auditor's own reproduction hung past
    120 seconds computing it before being killed. Neither the whitelist
    walk nor `_eval_node`'s numeric-constant guard catches this: every
    node involved (`BinOp`/`Pow`, three `Constant` nodes each holding the
    small int `9`) is individually well-typed and well-within-range: the
    danger is purely in the COMBINATION, which no per-node check can see.
    Removing `ast.Pow` from the whitelist eliminates the vector outright --
    verified morning-of that no era template uses `**` anywhere, so this
    costs nothing real, exactly matching decision D5's own stated posture
    (the surface is not kept wide merely because today's inputs are
    trusted).

    This test does NOT reproduce the 120-second hang itself (unsafe and
    slow to run in a unit test) -- it proves the STRUCTURAL fix instead:
    a small, fast `Pow` expression must now be refused by the whitelist
    walk before any evaluation happens, which is what removes the vector
    regardless of operand size.
    """

    def test_power_operator_is_refused(self):
        with pytest.raises(FormulaError):
            evaluate_derived_formula("2**3", {})

    def test_modulo_operator_is_refused(self):
        """`ast.Mod` removed too, on the same "surface not kept wide
        merely because today's inputs are trusted" reasoning from decision
        D5 -- NOT because Mod shares Pow's exponential-blowup risk (it
        does not: `a % b` is bounded by `b` and cannot compound into
        unbounded computation the way right-associative `Pow` towers can).
        No era template uses `%` either (verified alongside `**`), and
        this evaluator serves exactly one formula today (a weighted linear
        combination needing neither operator) -- an unused, unneeded
        operator is removed rather than grandfathered, matching this
        project's own preference for the smallest surface that does the
        job. Mod's only actual failure mode (division by zero) is already
        covered by the FormulaError wrap below, independent of whether
        Mod itself stays whitelisted.
        """
        with pytest.raises(FormulaError):
            evaluate_derived_formula("7 % 3", {})


class TestEvaluateDerivedFormulaRaisesContract:
    """Fix M-1 (phase-6 audit round 1, T046): the `Raises` contract in
    `evaluate_derived_formula`'s own docstring promises ONLY `FormulaError`
    -- this module's whole posture (see `apply_social_inheritance`'s
    unknown-`class_rule` fallback, `resolve_heirs`'s unknown-category
    skip, `apply_estate_tax`'s rate clamp) is to never crash the
    birth/death pipeline on template data. Before this fix, `1/0` raised
    a bare `ZeroDivisionError`, breaking that promise and that posture at
    once: a template author's zero-valued denominator (or a coefficient
    that happens to evaluate to zero) would crash the birth pipeline
    instead of raising the one exception type every caller is entitled to
    catch.
    """

    def test_division_by_zero_raises_formula_error_not_zero_division_error(self):
        with pytest.raises(FormulaError):
            evaluate_derived_formula("1/intelligence", {"intelligence": 0.0})

    def test_deeply_nested_formula_raises_formula_error_not_recursion_error(self):
        """Fix NEW-3, first pass (phase-6 audit round 2, T046):
        `ArithmeticError` alone (the previous fix, M-1) does not make the
        `Raises` contract true -- `_eval_node`'s own recursive descent is
        not an arithmetic error. Independently reproduced before this
        fix: `"-" * n + "x"` (n consecutive unary minuses) succeeds up to
        n=997 and raises a bare `RecursionError` at n=998 in this exact
        container (both via a bare script and via pytest -- `ast.parse`
        itself copes fine at every n tried up to 1200 at the time this
        test was written; a MUCH larger n was later found, in round 3, to
        break the PARSER itself before this depth bound ever runs -- see
        `test_pathologically_long_formula_raises_formula_error_not_memory_error`
        below for that separate fix and its own test). The specific
        crossover point for THIS `_eval_node`-recursion vector is
        environment- and caller-stack-dependent (a deeper caller stack,
        e.g. inside Django/Celery request handling, would hit it at a
        SMALLER n than a bare test does) -- which is itself the argument
        for a proactive, fixed depth bound rather than only reacting to
        wherever Python's own recursion ceiling happens to sit for a given
        caller. n=100 here is comfortably above `_MAX_FORMULA_TREE_DEPTH`
        (so the fix's own bound fires) and comfortably below where an
        unbounded implementation would ever risk `RecursionError` (so this
        test does not depend on tuning it close to either edge).
        """
        with pytest.raises(FormulaError):
            evaluate_derived_formula("-" * 100 + "intelligence", {"intelligence": 0.5})

    def test_pathologically_long_formula_raises_formula_error_not_memory_error(self):
        """Fix NEW-3, second pass (phase-6 audit round 3, T046): the depth
        bound above runs AFTER `ast.parse` -- it protects `_eval_node`'s
        own descent, but does nothing for a failure INSIDE the parse call
        itself. Independently reproduced before this fix: `ast.parse("-" *
        n + "x", mode="eval")` succeeds up to n=5900 and raises a bare
        `MemoryError("Parser stack overflowed - Python source too complex
        to parse")` at n=5976 in this exact container -- CPython's own PEG
        parser exhausting its internal stack allocator, a controlled,
        well-defined condition (not a symptom of the whole process running
        out of memory), but still an exception type the `Raises` contract
        never promised. Before this fix, `evaluate_derived_formula`'s own
        `except SyntaxError` around `ast.parse` does not catch
        `MemoryError`, so it escaped raw, exactly the same category of
        contract violation `RecursionError` was.

        FIX CHOSEN: a proactive `_MAX_FORMULA_EXPRESSION_LENGTH` bound,
        checked BEFORE `ast.parse` is ever called (see that constant's own
        comment for the exact reasoning) -- not a `try/except MemoryError`
        around the parse call. A length bound stops the parser from ever
        seeing a pathological string at all, rather than reacting to
        however CPython's specific parser implementation happens to fail
        today; catching `MemoryError` broadly is also the more fragile
        choice in general, since a genuine out-of-memory condition
        elsewhere in the process could raise the identical exception type
        for an unrelated reason a narrow `except` here should not swallow.

        n=5976 is used directly (the auditor's own measured threshold,
        reproduced independently first) rather than a smaller value, so
        this test doubles as a literal regression check against the exact
        failure that was reported, not just "some length that overflows
        the parser eventually".
        """
        with pytest.raises(FormulaError):
            evaluate_derived_formula("-" * 5976 + "x", {"x": 1.0})


class TestEvaluateDerivedFormulaRefusals:
    """Security-critical: the evaluator must refuse anything beyond arithmetic.

    Fix M-1 (phase-6 audit round 1, T046) -- TEST REMEDIATION: every case
    below asserts `pytest.raises(FormulaError)` SPECIFICALLY, never bare
    `Exception`. The audit's own measurement (reproduced independently
    before writing this class, via `float(eval(expr, {}, symbols))` against
    the six ORIGINAL payloads): five of the six raise even under a
    deliberately insecure `eval()`-based stand-in, for reasons that have
    nothing to do with any security refusal --
    `intelligence.__class__`/`__import__`/`[x for x in (1,2)]` raise
    `TypeError` only because `float()` chokes on a non-numeric intermediate
    result (a type object, a builtin function, a list); `intelligence[0]`
    raises `TypeError` only because a bare float is not subscriptable;
    `unknown_trait` raises `NameError` for an unrelated, legitimate reason
    (undefined name) that a naive `eval()` shares by coincidence, not by
    security design. A bare `pytest.raises(Exception)` cannot tell a real
    whitelist refusal apart from any of these incidental failures -- it
    would pass identically against `evaluate_derived_formula` and against
    an insecure `eval()` wrapper for 5 of these 6 payloads. Only
    `abs(intelligence)` actually discriminates under a naive `eval()` (it
    returns a clean `0.8`, no exception at all) -- which is exactly why a
    SECOND, more dramatic payload of the same shape is added below,
    matching the auditor's own illustrative example.

    Categories covered, beyond the original six (now FormulaError-specific):
    function call, attribute access, dunder bare name, subscript,
    comprehension, unknown bare name -- plus ten more node types the
    whitelist blocks but nothing tested before this fix (`BoolOp`,
    `Compare`, `Lambda`, `IfExp`, `NamedExpr`/walrus, `JoinedStr`/f-string,
    `Starred`, `Tuple`, `List`, `Dict`), plus both of `_eval_node`'s own
    non-numeric-constant guards (`str`, `bool` True/False, `None`, `bytes`,
    `Ellipsis`) -- these five pass the WHITELIST walk (`ast.Constant` IS an
    allowed node type) and are refused only by the SECOND, separate guard
    inside `_eval_node` itself, a genuinely different code path from the
    node-type walk and therefore worth testing independently of it.
    """

    def test_refuses_function_call(self):
        """A function call (e.g. abs(...)) is not arithmetic and must raise."""
        with pytest.raises(FormulaError):
            evaluate_derived_formula("abs(intelligence)", {"intelligence": 0.8})

    def test_refuses_function_call_that_would_return_a_valid_number_under_naive_eval(self):
        """The auditor's own illustrative bypass: `__import__('os').system(...)`
        returns the shell exit code (0 here), a perfectly valid float-
        convertible int -- independently verified before writing this test:
        `float(eval("__import__('os').system('true')", {}, {}))` returns
        `0.0` with NO exception at all under a naive eval-based stand-in. A
        test that only checks "some exception was raised" would not catch
        this: the payload must be refused by the WHITELIST WALK itself,
        before any evaluation (and therefore before any shell command)
        could ever run.
        """
        with pytest.raises(FormulaError):
            evaluate_derived_formula("__import__('os').system('true')", {})

    def test_refuses_attribute_access(self):
        """Attribute access (e.g. .__class__) is a potential injection vector."""
        with pytest.raises(FormulaError):
            evaluate_derived_formula("intelligence.__class__", {"intelligence": 0.8})

    def test_refuses_dunder_bare_name(self):
        """A bare dunder name not present in symbols must raise.

        __import__ is not a symbol supplied by any caller, so it is refused
        on the same path as any other unknown name -- there is no special
        casing that would let a dunder name resolve.
        """
        with pytest.raises(FormulaError):
            evaluate_derived_formula("__import__", {"intelligence": 0.8})

    def test_refuses_subscript(self):
        """Subscript access (e.g. name[0]) is refused."""
        with pytest.raises(FormulaError):
            evaluate_derived_formula("intelligence[0]", {"intelligence": 0.8})

    def test_refuses_comprehension(self):
        """List/set/dict/generator comprehensions are refused."""
        with pytest.raises(FormulaError):
            evaluate_derived_formula("[x for x in (1,2)]", {"intelligence": 0.8})

    def test_refuses_unknown_bare_name(self):
        """A bare name absent from the symbol table must raise, not resolve to 0."""
        with pytest.raises(FormulaError):
            evaluate_derived_formula("unknown_trait", {"intelligence": 0.8})

    def test_refuses_bool_op(self):
        """`and`/`or` (ast.BoolOp) are not arithmetic."""
        with pytest.raises(FormulaError):
            evaluate_derived_formula(
                "intelligence and neuroticism", {"intelligence": 0.8, "neuroticism": 0.5}
            )

    def test_refuses_comparison(self):
        """Comparison operators (ast.Compare) are not arithmetic."""
        with pytest.raises(FormulaError):
            evaluate_derived_formula(
                "intelligence > neuroticism", {"intelligence": 0.8, "neuroticism": 0.5}
            )

    def test_refuses_lambda(self):
        """A lambda (ast.Lambda) defines code, not a value."""
        with pytest.raises(FormulaError):
            evaluate_derived_formula("(lambda: intelligence)", {"intelligence": 0.8})

    def test_refuses_conditional_expression(self):
        """A ternary conditional (ast.IfExp) is refused."""
        with pytest.raises(FormulaError):
            evaluate_derived_formula(
                "intelligence if neuroticism else agreeableness",
                {"intelligence": 0.8, "neuroticism": 0.5, "agreeableness": 0.3},
            )

    def test_refuses_walrus_assignment(self):
        """A named/walrus expression (ast.NamedExpr) performs assignment,
        not arithmetic, and must be refused even though its own value
        would be numeric."""
        with pytest.raises(FormulaError):
            evaluate_derived_formula("(x := intelligence)", {"intelligence": 0.8})

    def test_refuses_f_string(self):
        """An f-string (ast.JoinedStr) is refused."""
        with pytest.raises(FormulaError):
            evaluate_derived_formula("f'{intelligence}'", {"intelligence": 0.8})

    def test_refuses_starred_expression(self):
        """A starred unpacking expression (ast.Starred) is refused."""
        with pytest.raises(FormulaError):
            evaluate_derived_formula("[*intelligence]", {"intelligence": 0.8})

    def test_refuses_tuple(self):
        """A tuple literal (ast.Tuple) is refused."""
        with pytest.raises(FormulaError):
            evaluate_derived_formula(
                "(intelligence, neuroticism)", {"intelligence": 0.8, "neuroticism": 0.5}
            )

    def test_refuses_list(self):
        """A list literal (ast.List) is refused."""
        with pytest.raises(FormulaError):
            evaluate_derived_formula(
                "[intelligence, neuroticism]", {"intelligence": 0.8, "neuroticism": 0.5}
            )

    def test_refuses_dict(self):
        """A dict literal (ast.Dict) is refused."""
        with pytest.raises(FormulaError):
            evaluate_derived_formula("{'a': intelligence}", {"intelligence": 0.8})

    def test_refuses_string_constant(self):
        """A string literal passes the node-type WHITELIST (ast.Constant is
        allowed) but is refused by _eval_node's own separate non-numeric-
        constant guard -- a genuinely different code path from every case
        above, worth testing independently."""
        with pytest.raises(FormulaError):
            evaluate_derived_formula("'hello'", {})

    def test_refuses_bool_constant(self):
        """True/False parse as ast.Constant with a bool value -- explicitly
        excluded by _eval_node's `isinstance(node.value, bool)` guard even
        though bool is technically an int subclass in Python."""
        with pytest.raises(FormulaError):
            evaluate_derived_formula("True", {})

    def test_refuses_none_constant(self):
        with pytest.raises(FormulaError):
            evaluate_derived_formula("None", {})

    def test_refuses_bytes_constant(self):
        with pytest.raises(FormulaError):
            evaluate_derived_formula("b'x'", {})

    def test_refuses_ellipsis_constant(self):
        with pytest.raises(FormulaError):
            evaluate_derived_formula("...", {})


# ---------------------------------------------------------------------------
# apply_trait_inheritance (Plan 3, T008/T009)
# ---------------------------------------------------------------------------

# Heritability keys in the pre_industrial_christian template (and every other
# era template -- verified identical across all five templates) that map to
# a concrete Agent model FloatField, versus keys with no matching field that
# therefore live inside Agent.personality JSONB. Split verified directly
# against epocha/apps/agents/models.py: Agent has intelligence,
# emotional_intelligence, creativity, strength, stamina, agility, fertility,
# and mental_health as scalar fields; openness, conscientiousness,
# extraversion, agreeableness, and neuroticism have no matching field and
# only exist inside the JSONB personality blob.
#
# Fix I-9 (phase-6 audit round 1, T046): mental_health moved here from
# PERSONALITY_HERITABLE_TRAITS. Every era template previously declared the
# heritability key as `mental_health_baseline`, which matches no Agent
# field -- the inherited value landed in `child.personality
# ["mental_health_baseline"]` (a dead JSONB key nothing reads) while
# `Agent.mental_health` never moved from its model default. All five
# template JSON files now declare `mental_health` (matching the field
# exactly), so `_agent_has_field`'s existing un-special-cased routing picks
# it up as a scalar automatically -- no routing code changed for this fix,
# only the template data.
SCALAR_HERITABLE_TRAITS = {
    "intelligence",
    "emotional_intelligence",
    "creativity",
    "strength",
    "stamina",
    "agility",
    "fertility",
    "mental_health",
}
PERSONALITY_HERITABLE_TRAITS = {
    "openness",
    "conscientiousness",
    "extraversion",
    "agreeableness",
    "neuroticism",
}


@pytest.fixture
def sim_with_zone(db):
    """Minimal scaffolding: user, simulation, world, zone (mirrors test_couple.py)."""
    user = User.objects.create_user(
        email="inheritance@epocha.dev",
        username="inheritanceuser",
        password="pass1234",
    )
    sim = Simulation.objects.create(
        name="InheritanceTest",
        seed=2026,
        owner=user,
        current_tick=10,
    )
    world = World.objects.create(simulation=sim, stability_index=0.7)
    zone = Zone.objects.create(
        world=world,
        name="InheritanceZone",
        zone_type="residential",
        boundary=Polygon.from_bbox((0, 0, 100, 100)),
        center=Point(50, 50),
    )
    return sim, zone


def _make_agent(sim, zone, name, personality=None, **kwargs):
    """Helper: create an Agent with sensible defaults (mirrors test_couple.py)."""
    defaults = dict(
        role="farmer",
        location=Point(50, 50),
        health=1.0,
        wealth=100.0,
        age=30,
        birth_tick=0,
        mood=0.5,
        education_level=0.5,
        social_class="working",
        gender=Agent.Gender.FEMALE,
        personality=personality if personality is not None else {},
    )
    defaults.update(kwargs)
    return Agent.objects.create(simulation=sim, name=name, zone=zone, **defaults)


class TestApplyTraitInheritanceHeritabilityCoverage:
    """Every heritable trait in the template is written to the child."""

    @pytest.mark.django_db
    def test_writes_every_heritability_trait_to_child(self, sim_with_zone):
        """Requirement 1: scalars (including mental_health, fix I-9) via
        getattr, Big Five via child.personality, for every key in
        heritability except "default".
        """
        sim, zone = sim_with_zone
        template = load_template("pre_industrial_christian")
        heritability = template["trait_inheritance"]["heritability"]
        trait_names = set(heritability) - {"default"}

        # Self-check: the two hand-verified splits above must exactly cover
        # every heritability key, or this test is silently under-testing.
        assert trait_names == SCALAR_HERITABLE_TRAITS | PERSONALITY_HERITABLE_TRAITS

        mother_personality = {name: 0.65 for name in PERSONALITY_HERITABLE_TRAITS}
        father_personality = {name: 0.35 for name in PERSONALITY_HERITABLE_TRAITS}
        mother = _make_agent(
            sim,
            zone,
            "Mother",
            personality=mother_personality,
            **{name: 0.65 for name in SCALAR_HERITABLE_TRAITS},
        )
        father = _make_agent(
            sim,
            zone,
            "Father",
            personality=father_personality,
            **{name: 0.35 for name in SCALAR_HERITABLE_TRAITS},
        )
        child = _make_agent(sim, zone, "Child")

        rng = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        apply_trait_inheritance(child, mother, father, template, rng)

        for name in SCALAR_HERITABLE_TRAITS:
            value = getattr(child, name)
            assert isinstance(value, float), f"{name} was not written as a scalar float"
            assert 0.0 <= value <= 1.0, f"{name}={value} outside [0, 1]"

        for name in PERSONALITY_HERITABLE_TRAITS:
            assert name in child.personality, f"{name} missing from child.personality"
            value = child.personality[name]
            assert isinstance(value, float), f"{name} was not written as a float"
            assert 0.0 <= value <= 1.0, f"{name}={value} outside [0, 1]"


class TestApplyTraitInheritanceDefaultHeritability:
    """Personality traits absent from the heritability table use default h2=0.30."""

    @pytest.mark.django_db
    def test_unpublished_personality_trait_uses_default_h2(self, sim_with_zone):
        """Requirement 2: humor_style (not in heritability) is inherited with
        default_h2 = heritability["default"] = 0.30, using the documented
        DEFAULT_ERA_MEAN / DEFAULT_ERA_SD noise prior since no era template
        carries a per-trait noise spec (verified: none of the five era
        templates declare era_mean/era_sd under trait_inheritance).

        A minimal synthetic template isolates humor_style as the only
        heritable trait, so the RNG draw sequence is unambiguous and the
        expected value can be hand-computed exactly against a rng cloned
        from the same seed/tick/phase (mirrors the exact-match style of
        TestInheritTraitTwoParents above).
        """
        sim, zone = sim_with_zone
        synthetic_template = {
            "trait_inheritance": {
                "heritability": {"default": 0.30},
                "derived_trait_formulas": {},
            }
        }
        mother_val = 0.8
        father_val = 0.2
        mother = _make_agent(sim, zone, "Mother", personality={"humor_style": mother_val})
        father = _make_agent(sim, zone, "Father", personality={"humor_style": father_val})
        child = _make_agent(sim, zone, "Child")

        expected_rng = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        expected = inherit_trait(
            mother_val, father_val, 0.30, DEFAULT_ERA_MEAN, DEFAULT_ERA_SD, expected_rng
        )

        actual_rng = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        apply_trait_inheritance(child, mother, father, synthetic_template, actual_rng)

        assert "humor_style" in child.personality
        assert child.personality["humor_style"] == pytest.approx(expected)


class TestApplyTraitInheritanceNeitherParentCarriesTheKey:
    """Fix I-3 (phase-6 audit round 1, T046): the birth pipeline itself
    reaches `inherit_trait(None, None, ...)`, not just a synthetic unit
    call. Every heritable personality trait routes through `(parent.
    personality or {}).get(name)`, which is None whenever a parent's
    personality dict does not happen to carry that key -- and unlike
    scalar Agent fields (which always have a real float default),
    nothing guarantees every parent's personality blob carries every
    heritability key. Before this fix, a birth where NEITHER parent
    carries a given key crashed the entire `apply_trait_inheritance` call
    -- and by extension the whole birth -- with an uncaught `TypeError`,
    invisible to the pre-existing suite only because every fixture there
    happens to populate all six personality keys on both parents.
    """

    @pytest.mark.django_db
    def test_neither_parent_carrying_a_heritable_personality_key_does_not_crash_the_birth(
        self, sim_with_zone
    ):
        sim, zone = sim_with_zone
        synthetic_template = {
            "trait_inheritance": {
                "heritability": {"default": 0.30, "openness": 0.55},
                "derived_trait_formulas": {},
            }
        }
        # Neither parent's personality dict carries "openness" -- both
        # parent reads resolve to None, reproducing I-3's exact trigger.
        mother = _make_agent(sim, zone, "Mother", personality={})
        father = _make_agent(sim, zone, "Father", personality={})
        child = _make_agent(sim, zone, "Child")

        rng = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        apply_trait_inheritance(child, mother, father, synthetic_template, rng)

        assert "openness" in child.personality
        assert isinstance(child.personality["openness"], float)
        assert 0.0 <= child.personality["openness"] <= 1.0


class TestApplyTraitInheritanceDerivedTrait:
    """cunning is computed at birth from the derived formula, not inherited."""

    @pytest.mark.django_db
    def test_cunning_matches_derived_formula_over_inherited_traits(self, sim_with_zone):
        """Requirement 3: cunning must equal evaluate_derived_formula applied
        to the child's own freshly-inherited traits -- not a polygenic draw
        of its own. Parents' `cunning` scalar field is set far from the
        expected derived value (0.95) so a regression that mistakenly
        inherits cunning biologically would be caught by the mismatch.
        """
        sim, zone = sim_with_zone
        template = load_template("pre_industrial_christian")
        heritability = template["trait_inheritance"]["heritability"]
        formula_spec = template["trait_inheritance"]["derived_trait_formulas"]["cunning"]

        mother_personality = {name: 0.65 for name in PERSONALITY_HERITABLE_TRAITS}
        father_personality = {name: 0.35 for name in PERSONALITY_HERITABLE_TRAITS}
        mother = _make_agent(
            sim,
            zone,
            "Mother",
            personality=mother_personality,
            cunning=0.95,
            **{name: 0.65 for name in SCALAR_HERITABLE_TRAITS},
        )
        father = _make_agent(
            sim,
            zone,
            "Father",
            personality=father_personality,
            cunning=0.95,
            **{name: 0.35 for name in SCALAR_HERITABLE_TRAITS},
        )
        child = _make_agent(sim, zone, "Child")

        rng = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        apply_trait_inheritance(child, mother, father, template, rng)

        symbols = {name: getattr(child, name) for name in SCALAR_HERITABLE_TRAITS}
        symbols.update({name: child.personality[name] for name in PERSONALITY_HERITABLE_TRAITS})
        lo, hi = formula_spec["range"]
        expected_cunning = max(
            lo, min(hi, evaluate_derived_formula(formula_spec["formula"], symbols))
        )

        assert child.cunning == pytest.approx(expected_cunning)
        assert not (heritability.get("cunning"))  # cunning has no published h2 entry


class TestApplyTraitInheritanceRequiresMutablePersonalityDict:
    """Fix M-2 (phase-6 audit round 1, T046): `child.personality[name] =
    value` (the personality-routed write inside the main trait loop)
    writes without a guard, while both parent reads two lines above
    (`(mother.personality or {}).get(name)`) are defensive. This is an
    undeclared precondition: `apply_trait_inheritance` never calls
    `child.save()` (see its own docstring), so `child` is routinely an
    unsaved, in-memory `Agent` at the point this function runs -- and
    Django only applies `Agent.personality`'s `default=dict` when the
    constructor is called with the `personality` kwarg omitted entirely.
    Any caller that explicitly sets `child.personality = None` (or passes
    `personality=None` to the constructor) before calling this function
    hits `TypeError: 'NoneType' object does not support item assignment`
    on the very first personality-routed trait.
    """

    @pytest.mark.django_db
    def test_child_personality_none_does_not_crash_on_first_personality_trait(self, sim_with_zone):
        sim, zone = sim_with_zone
        synthetic_template = {
            "trait_inheritance": {
                "heritability": {"default": 0.30, "openness": 0.55},
                "derived_trait_formulas": {},
            }
        }
        mother = _make_agent(sim, zone, "Mother", personality={"openness": 0.7})
        father = _make_agent(sim, zone, "Father", personality={"openness": 0.3})
        child = _make_agent(sim, zone, "Child")
        # Simulate the undeclared-precondition violation: an unsaved child
        # (this function never calls .save(), per its own docstring) whose
        # personality has not been initialized to a dict.
        child.personality = None

        rng = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        apply_trait_inheritance(child, mother, father, synthetic_template, rng)

        assert isinstance(child.personality, dict), (
            f"child.personality={child.personality!r} after apply_trait_"
            "inheritance -- the function must initialize it to a dict "
            "rather than requiring the caller to guarantee one"
        )
        assert "openness" in child.personality


class TestApplyTraitInheritanceMentalHealthKeyMatchesAgentField:
    """Fix I-9 (phase-6 audit round 1, T046): every era template must
    declare heritability under the key `mental_health`, matching
    `Agent.mental_health` (`epocha/apps/agents/models.py`) exactly --
    NOT `mental_health_baseline`, a name with no matching Agent field.
    Before this fix, all five templates declared `mental_health_baseline:
    0.40`, so the inherited value landed in `child.personality
    ["mental_health_baseline"]` (a JSONB key nothing reads) while `Agent.
    mental_health` never moved from its model default (0.8) -- mental
    health was silently never inherited, in every era, despite every
    template's own heritability table claiming h2=0.40 for it.

    `_agent_has_field` (see its docstring) special-cases nothing: once the
    template key matches the Agent field name, the existing scalar/
    personality routing in `apply_trait_inheritance` picks it up with no
    further code change -- this fix is a data change (template JSON), not
    a code change, exactly as `_agent_has_field`'s own documented design
    promises for a "template change (renaming ... a heritability key)".
    """

    @pytest.mark.parametrize(
        "template_name",
        [
            "pre_industrial_christian",
            "pre_industrial_islamic",
            "industrial",
            "modern_democracy",
            "sci_fi",
        ],
    )
    def test_every_era_template_declares_mental_health_at_h2_040(self, template_name):
        """Guards all five template JSON files independently -- a typo or
        incomplete rename in any single file would otherwise pass silently
        as long as the one template exercised by the exact-value test
        below happened to be correct.
        """
        template = load_template(template_name)
        heritability = template["trait_inheritance"]["heritability"]

        assert "mental_health_baseline" not in heritability, (
            f"{template_name}.json still declares the dead key "
            "'mental_health_baseline', which matches no Agent field"
        )
        assert heritability.get("mental_health") == pytest.approx(0.40), (
            f"{template_name}.json does not declare 'mental_health': 0.40 "
            f"-- got {heritability.get('mental_health')!r}"
        )

    @pytest.mark.django_db
    def test_agent_mental_health_field_is_actually_inherited_at_h2_040(self, sim_with_zone):
        """End-to-end proof, not just a JSON-shape check: Agent.mental_
        health must move away from its field default (0.8) in a manner
        that exactly matches inherit_trait's own h2=0.40 formula -- the
        same exact-match style as TestApplyTraitInheritanceDefaultHeritability
        above, replaying an identically seeded rng independently.
        """
        sim, zone = sim_with_zone
        template = load_template("pre_industrial_christian")
        heritability = template["trait_inheritance"]["heritability"]
        mental_health_h2 = heritability["mental_health"]
        assert mental_health_h2 == pytest.approx(0.40)

        mother_personality = {name: 0.65 for name in PERSONALITY_HERITABLE_TRAITS}
        father_personality = {name: 0.35 for name in PERSONALITY_HERITABLE_TRAITS}
        mother_mental_health = 0.9
        father_mental_health = 0.1
        # mental_health is set to a distinct value from the other scalar
        # traits' uniform 0.65/0.35 (rather than left to the generic
        # SCALAR_HERITABLE_TRAITS spread) so this test does not depend on
        # every other scalar trait coincidentally sharing the same value.
        other_scalar_traits = SCALAR_HERITABLE_TRAITS - {"mental_health"}
        mother = _make_agent(
            sim,
            zone,
            "Mother",
            personality=mother_personality,
            mental_health=mother_mental_health,
            **{name: 0.65 for name in other_scalar_traits},
        )
        father = _make_agent(
            sim,
            zone,
            "Father",
            personality=father_personality,
            mental_health=father_mental_health,
            **{name: 0.35 for name in other_scalar_traits},
        )
        child = _make_agent(sim, zone, "Child")

        expected_rng = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        actual_rng = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        apply_trait_inheritance(child, mother, father, template, actual_rng)

        # Independently replay the same deterministic trait order
        # (heritability dict order, "default" excluded) that apply_trait_
        # inheritance itself documents, consuming the identically seeded
        # expected_rng in lockstep, to compute mental_health's expected
        # value without depending on the implementation's own result.
        trait_names = [name for name in heritability if name != "default"]
        expected_mental_health = None
        for name in trait_names:
            h2 = heritability.get(name, heritability.get("default", 0.30))
            if name == "mental_health":
                expected_mental_health = inherit_trait(
                    mother_mental_health,
                    father_mental_health,
                    h2,
                    DEFAULT_ERA_MEAN,
                    DEFAULT_ERA_SD,
                    expected_rng,
                )
            else:
                # Consume the same single gauss draw every other trait in
                # the fixed order takes, to keep expected_rng's position
                # synchronized with actual_rng's up to and including
                # mental_health's own draw.
                is_scalar = name in SCALAR_HERITABLE_TRAITS
                m_val = getattr(mother, name) if is_scalar else mother_personality.get(name)
                f_val = getattr(father, name) if is_scalar else father_personality.get(name)
                inherit_trait(m_val, f_val, h2, DEFAULT_ERA_MEAN, DEFAULT_ERA_SD, expected_rng)

        assert expected_mental_health is not None, "mental_health missing from heritability order"
        assert child.mental_health == pytest.approx(expected_mental_health)
        assert child.mental_health != pytest.approx(0.8), (
            "child.mental_health is still the Agent field default -- "
            "mental_health was not inherited"
        )
        assert "mental_health_baseline" not in child.personality, (
            "the dead key 'mental_health_baseline' is still being written to child.personality"
        )


# ---------------------------------------------------------------------------
# resolve_birth_attributes (Plan 3, T010/T011)
# ---------------------------------------------------------------------------
#
# Pure function -- no ORM, no persistence -- so none of these tests use
# @pytest.mark.django_db. `load_template` reads a JSON fixture from disk,
# which needs no database.


def _expected_gender_and_orientation(template: dict, rng: random.Random) -> tuple[str, str]:
    """Independently replay the two documented rng draws against `rng`.

    Mirrors the draw order and selection rule specified for
    `resolve_birth_attributes`: gender first from a single `rng.random()`
    compared against p_male = sex_ratio / (1 + sex_ratio), then orientation
    from a second `rng.random()` walked cumulatively over
    `sexual_orientation_distribution` in the dict's own insertion order,
    falling back to the last key if the cumulative sum falls fractionally
    short of the draw.
    """
    sex_ratio = template["sex_ratio_at_birth"]
    p_male = sex_ratio / (1.0 + sex_ratio)
    gender_draw = rng.random()
    gender = "male" if gender_draw < p_male else "female"

    distribution = template["sexual_orientation_distribution"]
    orientation_draw = rng.random()
    cumulative = 0.0
    orientation = None
    for key, probability in distribution.items():
        cumulative += probability
        if orientation_draw < cumulative:
            orientation = key
            break
    if orientation is None:
        orientation = list(distribution.keys())[-1]

    return gender, orientation


class TestResolveBirthAttributesExactness:
    """Exact RNG-predicted (gender, orientation) pair for a seeded rng."""

    def test_matches_hand_replayed_two_draw_sequence(self):
        """The two draws (gender then orientation) are replayed independently
        against an identically-seeded random.Random and the documented
        selection rules, mirroring the exact-match style used for
        `inherit_trait` above.
        """
        template = load_template("pre_industrial_christian")

        expected_rng = random.Random(2026)
        expected = _expected_gender_and_orientation(template, expected_rng)

        actual_rng = random.Random(2026)
        actual = resolve_birth_attributes(template, actual_rng)

        assert actual == expected

    def test_matches_hand_replayed_two_draw_sequence_different_seed(self):
        """Same replay, a different seed, so the exactness check is not an
        artifact of one lucky seed value.
        """
        template = load_template("pre_industrial_christian")

        expected_rng = random.Random(777)
        expected = _expected_gender_and_orientation(template, expected_rng)

        actual_rng = random.Random(777)
        actual = resolve_birth_attributes(template, actual_rng)

        assert actual == expected


class TestResolveBirthAttributesValidDomain:
    """Over many seeds, the return values stay within their valid domains."""

    def test_gender_and_orientation_always_in_domain(self):
        template = load_template("pre_industrial_christian")
        valid_orientations = set(template["sexual_orientation_distribution"].keys())

        for seed in range(200):
            gender, orientation = resolve_birth_attributes(template, random.Random(seed))
            assert gender in {"male", "female"}
            assert orientation in valid_orientations


class TestResolveBirthAttributesSexRatioDirection:
    """The sex_ratio_at_birth parameter steers the gender draw as expected."""

    def test_high_sex_ratio_yields_mostly_male(self):
        """sex_ratio_at_birth = 99.0 -> p_male = 99/100 = 0.99: an overwhelming
        majority of "male" over a seeded batch. A strong-majority assertion
        keeps the test robust to which exact seeds land on the female side.
        """
        template = {
            "sex_ratio_at_birth": 99.0,
            "sexual_orientation_distribution": {"heterosexual": 1.0},
        }
        male_count = sum(
            1
            for seed in range(300)
            if resolve_birth_attributes(template, random.Random(seed))[0] == "male"
        )
        assert male_count > 270  # 90% of 300, well below the ~99% expectation

    def test_low_sex_ratio_yields_mostly_female(self):
        """sex_ratio_at_birth = 0.01 -> p_male = 0.01/1.01 ~= 0.0099: an
        overwhelming majority of "female" over a seeded batch.
        """
        template = {
            "sex_ratio_at_birth": 0.01,
            "sexual_orientation_distribution": {"heterosexual": 1.0},
        }
        female_count = sum(
            1
            for seed in range(300)
            if resolve_birth_attributes(template, random.Random(seed))[0] == "female"
        )
        assert female_count > 270  # 90% of 300, well below the ~99% expectation


class TestResolveBirthAttributesBucketCorrectness:
    """A degenerate distribution deterministically selects the non-zero bucket."""

    def test_zero_probability_bucket_is_never_selected(self):
        """{"heterosexual": 0.0, "homosexual": 1.0} returns "homosexual" on
        every draw: the cumulative sum after "heterosexual" stays at 0.0, so
        `draw < cumulative` never selects it (rng.random() draws are >= 0.0),
        and the cumulative sum after "homosexual" reaches 1.0, which every
        draw in [0.0, 1.0) satisfies.
        """
        template = {
            "sex_ratio_at_birth": 1.05,
            "sexual_orientation_distribution": {"heterosexual": 0.0, "homosexual": 1.0},
        }
        for seed in range(100):
            _, orientation = resolve_birth_attributes(template, random.Random(seed))
            assert orientation == "homosexual"


# ---------------------------------------------------------------------------
# apply_social_inheritance (Plan 3, T012/T013)
# ---------------------------------------------------------------------------
#
# Social-class transmission and education-level regression at birth (design
# spec Sezione 5, docs/superpowers/specs/2026-04-18-demography-design-it.md).
# Reuses the sim_with_zone fixture / _make_agent helper defined above for
# apply_trait_inheritance.

# Hand-maintained rank ladder mirroring
# epocha.apps.world.stratification._CLASS_RANK, extended with "enslaved" one
# rank below "poor". Kept independent of the implementation's own copy (the
# file's established exact-match testing style) so a test failure cannot be
# masked by trusting a constant the implementation might get wrong.
# Agent.social_class's help_text (epocha/apps/agents/models.py) lists
# "enslaved" as a valid value, but the stratification module (wealth-
# percentile class assignment) never assigns it -- it is only ever
# reachable through social inheritance (patrilineal_rigid transmission from
# an already-enslaved father in a pre-industrial template).
_TEST_CLASS_RANK = {
    "elite": 0,
    "wealthy": 1,
    "middle": 2,
    "working": 3,
    "poor": 4,
    "enslaved": 5,
}
_TEST_VALID_CLASS_LABELS = set(_TEST_CLASS_RANK)

# Fix T046/I-1 test remediation (phase-6 audit round 1): a set membership
# assertion against _TEST_VALID_CLASS_LABELS cannot catch T046/I-1, because
# "enslaved" is itself a member -- a test asserting `result in
# _TEST_VALID_CLASS_LABELS` passes whether or not the sampled-rule output
# clamp is active. The three SAMPLED rules (clark_regression,
# becker_tomes_elasticity_0.4, meritocratic) must never resolve to
# "enslaved" from non-enslaved inputs (see TestSampledClassRulesNever
# ProduceEnslaved below for the airtight Monte Carlo proof); their output-
# range assertions use this narrower set instead. patrilineal_rigid keeps
# using the full _TEST_VALID_CLASS_LABELS, since its string copy of an
# already-enslaved father legitimately produces "enslaved".
_TEST_VALID_SAMPLED_CLASS_LABELS = _TEST_VALID_CLASS_LABELS - {"enslaved"}


class TestApplySocialInheritancePatrilinealRigid:
    """class_rule = "patrilineal_rigid": verbatim copy of the father's class
    (Goody 1976; Wrigley 1981).
    """

    @pytest.mark.django_db
    def test_child_copies_fathers_class_exactly(self, sim_with_zone):
        sim, zone = sim_with_zone
        template = {
            "social_inheritance": {
                "class_rule": "patrilineal_rigid",
                "education_regression_rho": 0.5,
            }
        }
        mother = _make_agent(sim, zone, "Mother", social_class="middle", education_level=0.5)
        father = _make_agent(sim, zone, "Father", social_class="wealthy", education_level=0.6)
        child = _make_agent(sim, zone, "Child")

        rng = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        apply_social_inheritance(child, mother, father, template, zone_class_mean=2.0, rng=rng)

        assert child.social_class == "wealthy"

    @pytest.mark.django_db
    def test_enslaved_status_transmits_from_father(self, sim_with_zone):
        """A pure string copy transmits "enslaved" exactly like any other
        label -- the whole reason the extended rank ladder (_TEST_CLASS_RANK
        above, and its implementation counterpart per decision A) exists.
        """
        sim, zone = sim_with_zone
        template = {
            "social_inheritance": {
                "class_rule": "patrilineal_rigid",
                "education_regression_rho": 0.5,
            }
        }
        mother = _make_agent(sim, zone, "Mother", social_class="poor", education_level=0.2)
        father = _make_agent(sim, zone, "Father", social_class="enslaved", education_level=0.1)
        child = _make_agent(sim, zone, "Child")

        rng = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        apply_social_inheritance(child, mother, father, template, zone_class_mean=4.0, rng=rng)

        assert child.social_class == "enslaved"


class TestApplySocialInheritanceClarkRegression:
    """class_rule = "clark_regression": 70% father's rank / 30% regression
    toward the zone's mean class rank (Clark, G. (2014), "The Son Also
    Rises").
    """

    @pytest.mark.django_db
    def test_child_regresses_toward_zone_mean_between_father_and_mean(self, sim_with_zone):
        """A high-class father ("elite", rank 0) in a low-class zone
        (zone_class_mean = 4.0, the "poor" rank) must land the child
        strictly between the two ranks -- neither a plain copy of the
        father's class nor a jump straight to the zone mean. The 70/30
        weighting (child_rank = 0.7*0 + 0.3*4.0 = 1.2) makes this hold for
        any reasonable nearest-label rounding rule (floor, round, or ceil
        all land inside (0, 4.0)), so the assertion does not depend on the
        exact rounding tie-break the implementation chooses.

        NOT the weighting proof (phase-6 audit round 2, T046): this
        assertion, and the other two tests in this file that exercise
        `clark_regression` (the empty-zone-fallback test and the
        enslaved-father test), were shown by the round-2 audit's own
        algebra to jointly constrain the weight `w` in `rank = w*parent +
        (1-w)*zone_mean` only to roughly `w in (0.5, 0.875]` -- Clark's
        actual 0.7 is inside that range, but so is 0.6, 0.75, 0.8, or
        0.85; nothing here would go red if the implementation used any of
        them instead. See `test_weight_is_pinned_exactly_to_seventy_thirty`
        below for the test that actually pins 0.7/0.3, rather than merely
        being consistent with it.
        """
        sim, zone = sim_with_zone
        template = {
            "social_inheritance": {
                "class_rule": "clark_regression",
                "education_regression_rho": 0.4,
            }
        }
        mother = _make_agent(sim, zone, "Mother", social_class="elite", education_level=0.9)
        father = _make_agent(sim, zone, "Father", social_class="elite", education_level=0.9)
        child = _make_agent(sim, zone, "Child")

        rng = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        apply_social_inheritance(child, mother, father, template, zone_class_mean=4.0, rng=rng)

        assert child.social_class in _TEST_VALID_SAMPLED_CLASS_LABELS
        child_rank = _TEST_CLASS_RANK[child.social_class]
        assert 0 < child_rank < 4.0

    @pytest.mark.django_db
    def test_weight_is_pinned_exactly_to_seventy_thirty(self, sim_with_zone, monkeypatch):
        """Fix (round-1 test item; NOT actually resolved by the original
        version of this test, per phase-6 audit round 3, T046 -- see
        CORRECTION below): pins Clark's 70/30 weighting EXACTLY, closing
        the gap the class docstring above now documents -- the existing
        rounded-label assertions jointly permit any `w` in roughly
        `(0.5, 0.875]`.

        A single integer-rounded `social_class` label cannot, by
        construction, discriminate a real-valued weight to better than
        roughly one rounding bucket's width (~0.25 of the [0,4] rank
        span) -- `_rank_to_class_label` rounds to the NEAREST of 5 labels
        before the caller ever sees anything, and neither
        `_apply_clark_regression` nor `apply_social_inheritance` returns
        the raw continuous rank. This test bypasses that information loss
        by monkeypatching the MODULE-LEVEL `_rank_to_class_label` name
        `_apply_clark_regression` calls (a bare global lookup at call
        time, not a pre-bound reference, so patching the module attribute
        correctly intercepts it) to CAPTURE its input before delegating
        to the real implementation -- observing the exact pre-rounding
        value `_apply_clark_regression` computed, not merely the rounded
        label it produced.

        CORRECTION (phase-6 audit round 3, T046): the original version of
        this test used ONLY father rank 0 ("elite"). `rank = 0.7*parent +
        0.3*zone_mean` with `parent = 0` makes the PARENT term
        `0.7 * 0 = 0` regardless of what the 0.7 coefficient actually is
        -- the assertion `expected_rank = 0.7*0 + 0.3*4.0 == 1.2` holds
        for ANY value substituted for 0.7, so the test pinned only the
        ZONE-MEAN coefficient (0.3), never the parent coefficient the
        rule is named for. The comment that used to sit here claiming
        "any distinct parent_rank/zone_class_mean pair works equally
        well" was independently verified FALSE for exactly the pair this
        test used -- it is precisely the zero-parent-rank case that hides
        the hole. A second scenario below, with a NON-ZERO parent rank
        (3, "working"), is required to pin the 0.7 coefficient itself;
        neither scenario alone is sufficient, since the zero-parent case
        genuinely does still discriminate the zone-mean coefficient.
        """
        sim, zone = sim_with_zone
        template = {
            "social_inheritance": {
                "class_rule": "clark_regression",
                "education_regression_rho": 0.4,
            }
        }

        import epocha.apps.demography.inheritance as inheritance_module

        real_rank_to_class_label = inheritance_module._rank_to_class_label
        captured_ranks: list[float] = []

        def _capturing_rank_to_class_label(rank: float) -> str:
            captured_ranks.append(rank)
            return real_rank_to_class_label(rank)

        monkeypatch.setattr(
            inheritance_module, "_rank_to_class_label", _capturing_rank_to_class_label
        )
        rng = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")

        # Scenario 1: father rank 0 ("elite"). The parent term (0.7*0=0)
        # vanishes regardless of the 0.7 coefficient's actual value -- this
        # scenario pins ONLY the zone-mean coefficient (0.3), not the
        # parent coefficient, and is kept specifically so a reader can see
        # that fact demonstrated rather than merely asserted.
        mother_1 = _make_agent(sim, zone, "Mother1", social_class="elite", education_level=0.9)
        father_1 = _make_agent(sim, zone, "Father1", social_class="elite", education_level=0.9)
        child_1 = _make_agent(sim, zone, "Child1")
        apply_social_inheritance(
            child_1, mother_1, father_1, template, zone_class_mean=4.0, rng=rng
        )

        # Scenario 2: father rank 3 ("working"), zone_class_mean 2.0 --
        # NEITHER term vanishes here (0.7*3=2.1, 0.3*2.0=0.6), so this is
        # the scenario that actually pins the 0.7 parent coefficient: a
        # wrong coefficient (e.g. 0.65 or 0.79, both of which the round-3
        # audit found the OLD single-scenario test let through) changes
        # this expected value and this one alone.
        mother_2 = _make_agent(sim, zone, "Mother2", social_class="middle", education_level=0.5)
        father_2 = _make_agent(sim, zone, "Father2", social_class="working", education_level=0.5)
        child_2 = _make_agent(sim, zone, "Child2")
        apply_social_inheritance(
            child_2, mother_2, father_2, template, zone_class_mean=2.0, rng=rng
        )

        assert len(captured_ranks) == 2, (
            "expected exactly one _rank_to_class_label call per scenario "
            "from the deterministic clark_regression branch"
        )

        expected_rank_1 = 0.7 * 0 + 0.3 * 4.0
        assert captured_ranks[0] == pytest.approx(expected_rank_1), (
            f"scenario 1 (parent_rank=0): captured pre-rounding rank "
            f"{captured_ranks[0]!r} does not match {expected_rank_1!r}"
        )

        expected_rank_2 = 0.7 * 3 + 0.3 * 2.0
        assert captured_ranks[1] == pytest.approx(expected_rank_2), (
            f"scenario 2 (parent_rank=3, the one that actually pins the 0.7 "
            f"coefficient): captured pre-rounding rank {captured_ranks[1]!r} "
            f"does not match {expected_rank_2!r}"
        )


class TestSampledClassRulesNeverProduceEnslaved:
    """Fix T046/I-1 (phase-6 audit round 1 -- the audit's own top finding;
    prefixed to distinguish it from `inherit_trait`'s unrelated, pre-
    existing design-spec fix also numbered "I-1"):
    a rank arithmetic result from any of the three SAMPLED social-class
    rules (clark_regression, becker_tomes_elasticity_0.4, meritocratic)
    must NEVER resolve to "enslaved", even when both parents are already
    at the ladder's own worst non-enslaved rank ("poor") and the zone
    mean is equally poor. Rank 5 ("enslaved") is reserved exclusively for
    `patrilineal_rigid`'s pure string copy of an ALREADY-enslaved parent's
    own label (`_apply_patrilineal_rigid` never calls `_rank_to_class_label`
    at all) -- never a rounded numeric output from a weighted average plus
    Gaussian noise.

    MONTE CARLO, NOT A SINGLE DRAW: `becker_tomes_elasticity_0.4`'s
    additive Gaussian perturbation (`_BECKER_TOMES_RANK_NOISE_SD = 0.75`)
    means one seed proves nothing about whether the CLAMP itself is
    active -- it would only show that one particular draw happened to
    round below 5. 5,000 independently seeded trials from the exact
    worst-case input (poor parent, poor zone -- `base_rank` already at
    the un-extended ladder's own ceiling of 4 before any perturbation is
    even added) makes the assertion airtight: verified independently
    before this fix, at 200,000 draws, today's code produces "enslaved"
    in 25.09% of them (matching the phase-6 audit's own independently
    measured 25.4% and 25.23% figures within ordinary Monte Carlo
    variance across different seed sequences) -- at 5,000 trials, the
    probability of the clamp accidentally passing this test by chance
    (zero hits at a true ~25% rate) is on the order of 10^-622. After the
    fix it must be EXACTLY zero, not merely rare.
    """

    @pytest.mark.django_db
    def test_becker_tomes_never_produces_enslaved_from_poor_parents_in_a_poor_zone(
        self, sim_with_zone
    ):
        sim, zone = sim_with_zone
        template = {
            "social_inheritance": {
                "class_rule": "becker_tomes_elasticity_0.4",
                "education_regression_rho": 0.4,
            }
        }
        mother = _make_agent(sim, zone, "Mother", social_class="poor", education_level=0.2)
        father = _make_agent(sim, zone, "Father", social_class="poor", education_level=0.2)
        # One child instance reused across every trial -- apply_social_
        # inheritance only ever reads mother/father/zone_class_mean for
        # becker_tomes, never any pre-existing child state, so re-creating
        # a fresh Agent row per trial would only slow the test down for
        # no added rigor.
        child = _make_agent(sim, zone, "Child")

        trials = 5000
        enslaved_count = 0
        for seed in range(trials):
            rng = random.Random(seed)
            apply_social_inheritance(child, mother, father, template, zone_class_mean=4.0, rng=rng)
            if child.social_class == "enslaved":
                enslaved_count += 1

        assert enslaved_count == 0, (
            f"{enslaved_count}/{trials} children of two 'poor' (non-enslaved) "
            "parents in an all-'poor' (non-enslaved) zone were assigned "
            "'enslaved' -- the sampled-rule output clamp (fix T046/I-1) is not "
            "active"
        )

    @pytest.mark.django_db
    def test_clark_regression_never_produces_enslaved_even_from_an_enslaved_father(
        self, sim_with_zone
    ):
        """clark_regression has no additive noise term (deterministic) --
        unlike becker_tomes, it cannot organically drift above the ladder's
        ceiling from ordinary poor-but-not-enslaved inputs, since it is a
        pure convex combination of two ranks each already <= 4 (a weighted
        average of two values can never exceed the larger of the two). But
        an ENSLAVED father (rank 5, read as legitimate INPUT via
        `_resolve_parent_rank` -- `_class_rank` must still resolve
        "enslaved" correctly for reads, only the numeric OUTPUT is
        clamped) combined with a zone whose OWN mean is already 5.0 (every
        agent in the zone enslaved) drives `rank = 0.7*5 + 0.3*5.0 = 5.0`
        exactly, `round(5.0) == 5` -- reachable and, verified independently
        before this fix, resolves to "enslaved" today. Reserving rank 5
        for `patrilineal_rigid`'s string copy means clark_regression must
        cap this at "poor" (rank 4) instead, even when it is regressing
        FROM an enslaved parent, not just from ordinary poor ones.
        """
        sim, zone = sim_with_zone
        template = {
            "social_inheritance": {
                "class_rule": "clark_regression",
                "education_regression_rho": 0.4,
            }
        }
        father = _make_agent(sim, zone, "Father", social_class="enslaved")
        child = _make_agent(sim, zone, "Child")

        rng = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        apply_social_inheritance(child, None, father, template, zone_class_mean=5.0, rng=rng)

        assert child.social_class != "enslaved"


class TestApplySocialInheritanceBeckerTomes:
    """class_rule = "becker_tomes_elasticity_0.4": intergenerational income
    elasticity 0.4 (Solon 1999; Chetty et al. 2014), sampled rather than
    deterministic.
    """

    @pytest.mark.django_db
    def test_outcome_varies_across_seeds_and_stays_in_valid_label_set(self, sim_with_zone):
        """A batch of independent seeds must NOT all resolve to the same
        label as a deterministic copy would -- the rule samples a
        perturbation around the shifted mean -- and every result must stay
        inside the six valid social_class labels.
        """
        sim, zone = sim_with_zone
        template = {
            "social_inheritance": {
                "class_rule": "becker_tomes_elasticity_0.4",
                "education_regression_rho": 0.4,
            }
        }
        mother = _make_agent(sim, zone, "Mother", social_class="elite", education_level=0.9)
        father = _make_agent(sim, zone, "Father", social_class="elite", education_level=0.9)

        results = set()
        for seed in range(40):
            child = _make_agent(sim, zone, f"BeckerChild{seed}")
            rng = random.Random(seed)
            apply_social_inheritance(child, mother, father, template, zone_class_mean=3.0, rng=rng)
            results.add(child.social_class)

        assert results <= _TEST_VALID_SAMPLED_CLASS_LABELS
        assert len(results) > 1, "expected sampling variability, got a deterministic copy"


class TestApplySocialInheritanceMeritocratic:
    """class_rule = "meritocratic": 20% inherited, 80% merit-based
    reassignment from the child's own intelligence/education_level
    (speculative sci_fi design choice, design spec Sezione 5 -- no
    citation).
    """

    @pytest.mark.django_db
    def test_higher_merit_yields_a_numerically_lower_better_rank(self, sim_with_zone):
        """Two children of the same parents/zone, differing only in
        intelligence, must resolve to a strictly better (lower) rank for
        the high-merit child than for the low-merit child. Deterministic --
        meritocratic consumes no rng draws -- so the comparison holds
        exactly, not just on average.

        Since fix I-2 (phase-6 audit round 1, T046), `apply_social_
        inheritance` regresses `child.education_level` from the PARENTS
        before dispatching to `_apply_meritocratic`, overwriting whatever
        `education_level` a child was constructed with -- both children
        share the same mother/father here, so both end up with the exact
        same regressed education_level regardless of what this test passes
        to `_make_agent`. Only the `intelligence` each child is
        constructed with (a value `_apply_meritocratic` never overwrites)
        still differentiates merit, which is why it is the only field this
        test varies.
        """
        sim, zone = sim_with_zone
        template = {
            "social_inheritance": {
                "class_rule": "meritocratic",
                "education_regression_rho": 0.25,
            }
        }
        mother = _make_agent(sim, zone, "Mother", social_class="middle", education_level=0.5)
        father = _make_agent(sim, zone, "Father", social_class="middle", education_level=0.5)

        high_merit_child = _make_agent(sim, zone, "HighMeritChild", intelligence=0.95)
        low_merit_child = _make_agent(sim, zone, "LowMeritChild", intelligence=0.05)

        rng_high = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        apply_social_inheritance(
            high_merit_child, mother, father, template, zone_class_mean=2.0, rng=rng_high
        )
        rng_low = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        apply_social_inheritance(
            low_merit_child, mother, father, template, zone_class_mean=2.0, rng=rng_low
        )

        high_rank = _TEST_CLASS_RANK[high_merit_child.social_class]
        low_rank = _TEST_CLASS_RANK[low_merit_child.social_class]
        assert high_rank < low_rank


class TestApplySocialInheritanceMeritocraticReadsRegressedEducationLevel:
    """Fix I-2 (phase-6 audit round 1, T046): `_apply_meritocratic` must
    read the CHILD'S OWN regressed `education_level` (the value
    `_regress_education_level` computes from the parents), not the bare
    `Agent` model field default (0.3) that a fresh, not-yet-processed
    newborn still carries at the moment the `class_rule` branch used to
    run. Before this fix `apply_social_inheritance` dispatched the
    `class_rule` branch BEFORE its own education-level regression step, so
    every sampled/deterministic merit calculation silently used 0.3
    regardless of how educated the parents were.

    Two "middle" parents (rank 2) both at education_level=0.9, under
    sci_fi's own declared parameters (meritocratic, rho=0.2, era_mean_
    education defaults to 0.3 -- no era template overrides it): the
    correctly regressed child education_level is `0.2*0.9 + 0.8*0.3 =
    0.42` (matching the audit's own hand-computed figure exactly), giving
    merit `(0.9 + 0.42) / 2 = 0.66`, merit_rank `(1 - 0.66) * 4 = 1.36`,
    final rank `0.2*2 + 0.8*1.36 = 1.488`, rounding to 1 ("wealthy"). Read
    before regression (today's bug), the same child's education_level is
    still whatever it was set to going in -- 0.3 here, matching a fresh
    newborn's Agent field default -- giving merit 0.6, merit_rank 1.6,
    final rank 1.68, rounding to 2 ("middle") -- a full class worse,
    exactly the "demotes a child a full class" effect the audit measured.

    NOTE: `child.education_level` ends up 0.42 EITHER WAY once
    `apply_social_inheritance` returns, because the regression step at the
    end of that function is unconditional regardless of dispatch order --
    it is not itself a valid probe for I-2. Only `child.social_class`
    (computed from whichever value `_apply_meritocratic` read DURING its
    own execution, before or after regression depending on the fix)
    discriminates the bug.
    """

    @pytest.mark.django_db
    def test_meritocratic_uses_the_regressed_education_level_not_the_field_default(
        self, sim_with_zone
    ):
        sim, zone = sim_with_zone
        template = {
            "social_inheritance": {
                "class_rule": "meritocratic",
                "education_regression_rho": 0.2,
            }
        }
        mother = _make_agent(sim, zone, "Mother", social_class="middle", education_level=0.9)
        father = _make_agent(sim, zone, "Father", social_class="middle", education_level=0.9)
        # intelligence is set directly (a SCALAR_HERITABLE_TRAIT already
        # inherited by the time the full apply_inheritance_at_birth
        # pipeline reaches this step). education_level is set explicitly to
        # the Agent MODEL field's own default (0.3, epocha/apps/agents/
        # models.py) rather than left at the _make_agent test helper's
        # unrelated convenience default (0.5) -- this reproduces the exact
        # "fresh, not-yet-processed newborn" state I-2 describes, where
        # nothing has written education_level yet. The unconditional
        # regression step at the end of apply_social_inheritance overwrites
        # child.education_level to 0.42 regardless of dispatch order, so
        # only child.social_class (computed from whatever education_level
        # _apply_meritocratic read AT THE TIME it ran) can discriminate the
        # bug -- the final education_level value is not a valid probe.
        child = _make_agent(sim, zone, "Child", intelligence=0.9, education_level=0.3)

        rng = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        apply_social_inheritance(child, mother, father, template, zone_class_mean=2.0, rng=rng)

        assert child.education_level == pytest.approx(0.42), (
            f"child.education_level={child.education_level!r}, expected the "
            "regressed value 0.42 regardless of dispatch order -- this "
            "assertion documents the unconditional regression step, it does "
            "not by itself discriminate I-2"
        )
        assert child.social_class == "wealthy", (
            f"child.social_class={child.social_class!r}, expected 'wealthy' "
            "(rank 1) -- reading the unregressed field default (0.3) instead "
            "of 0.42 understates merit and demotes the child to 'middle' "
            "(rank 2)"
        )


class TestApplySocialInheritanceEducationRegression:
    """child.education_level = rho*(mother.education_level +
    father.education_level)/2 + (1-rho)*era_mean_education, clamped to
    [0.0, 1.0]. Runs identically after every class_rule (design spec
    Sezione 5). TRAP 1 guard: the field under test is `education_level`,
    never `education` -- Agent has no such attribute.
    """

    @pytest.mark.django_db
    def test_matches_hand_computed_formula_with_known_rho(self, sim_with_zone):
        sim, zone = sim_with_zone
        rho = 0.6
        mother_edu = 0.8
        father_edu = 0.4
        template = {
            "social_inheritance": {
                "class_rule": "patrilineal_rigid",
                "education_regression_rho": rho,
            }
        }
        mother = _make_agent(sim, zone, "Mother", social_class="middle", education_level=mother_edu)
        father = _make_agent(sim, zone, "Father", social_class="middle", education_level=father_edu)
        child = _make_agent(sim, zone, "Child")

        expected = rho * (mother_edu + father_edu) / 2.0 + (1.0 - rho) * DEFAULT_ERA_MEAN_EDUCATION

        rng = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        apply_social_inheritance(child, mother, father, template, zone_class_mean=2.0, rng=rng)

        assert not hasattr(child, "education")  # TRAP 1: no such field on Agent
        assert child.education_level == pytest.approx(expected)

    @pytest.mark.django_db
    def test_result_is_clamped_into_zero_one(self, sim_with_zone):
        """rho = 0.0 isolates the era-mean term: an out-of-range
        era_mean_education (only reachable via a template override -- the
        Agent.education_level field itself is not range-restricted at the
        DB level either, so this also guards against a future caller
        passing an out-of-range value) must still clamp the final
        education_level into [0.0, 1.0].
        """
        sim, zone = sim_with_zone
        mother = _make_agent(sim, zone, "Mother", social_class="middle", education_level=0.5)
        father = _make_agent(sim, zone, "Father", social_class="middle", education_level=0.5)

        template_high = {
            "social_inheritance": {
                "class_rule": "patrilineal_rigid",
                "education_regression_rho": 0.0,
                "era_mean_education": 2.0,
            }
        }
        child_high = _make_agent(sim, zone, "ChildHighEdu")
        rng_high = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        apply_social_inheritance(
            child_high, mother, father, template_high, zone_class_mean=2.0, rng=rng_high
        )
        assert child_high.education_level == 1.0

        template_low = {
            "social_inheritance": {
                "class_rule": "patrilineal_rigid",
                "education_regression_rho": 0.0,
                "era_mean_education": -1.0,
            }
        }
        child_low = _make_agent(sim, zone, "ChildLowEdu")
        rng_low = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        apply_social_inheritance(
            child_low, mother, father, template_low, zone_class_mean=2.0, rng=rng_low
        )
        assert child_low.education_level == 0.0

    @pytest.mark.django_db
    def test_single_parent_fallback_uses_that_parents_value_alone(self, sim_with_zone):
        """Consistent with `inherit_trait`'s own design-spec fix I-1
        (design numbering, NOT this file's separate audit-numbered
        `T046/I-1`): when only the mother is known, the midparent term
        degrades to her value alone.
        """
        sim, zone = sim_with_zone
        rho = 0.5
        mother_edu = 0.9
        template = {
            "social_inheritance": {
                "class_rule": "patrilineal_rigid",
                "education_regression_rho": rho,
            }
        }
        mother = _make_agent(sim, zone, "Mother", social_class="middle", education_level=mother_edu)
        child = _make_agent(sim, zone, "Child")

        expected = rho * mother_edu + (1.0 - rho) * DEFAULT_ERA_MEAN_EDUCATION

        rng = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        apply_social_inheritance(child, mother, None, template, zone_class_mean=2.0, rng=rng)

        assert child.education_level == pytest.approx(expected)


class TestApplySocialInheritanceUnknownClassRule:
    """Decision A/contract: an unrecognized class_rule must never raise."""

    @pytest.mark.django_db
    def test_unknown_class_rule_falls_back_to_patrilineal_rigid_with_warning(
        self, sim_with_zone, caplog
    ):
        sim, zone = sim_with_zone
        template = {
            "social_inheritance": {
                "class_rule": "not_a_real_rule",
                "education_regression_rho": 0.5,
            }
        }
        mother = _make_agent(sim, zone, "Mother", social_class="middle", education_level=0.5)
        father = _make_agent(sim, zone, "Father", social_class="wealthy", education_level=0.5)
        child = _make_agent(sim, zone, "Child")

        rng = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        with caplog.at_level(logging.WARNING):
            apply_social_inheritance(child, mother, father, template, zone_class_mean=2.0, rng=rng)

        assert child.social_class == "wealthy"
        assert any("not_a_real_rule" in message for message in caplog.messages)


class TestApplySocialInheritanceUnknownClassValue:
    """Decision A: an unrecognized social_class value is treated as the
    "working" rank rather than raising during rank arithmetic.
    """

    @pytest.mark.django_db
    def test_unknown_father_class_value_falls_back_to_working_rank(self, sim_with_zone):
        sim, zone = sim_with_zone
        template = {
            "social_inheritance": {
                "class_rule": "clark_regression",
                "education_regression_rho": 0.4,
            }
        }
        mother = _make_agent(sim, zone, "Mother", social_class="middle", education_level=0.5)
        father = _make_agent(
            sim, zone, "Father", social_class="not_a_real_class", education_level=0.5
        )
        child = _make_agent(sim, zone, "Child")

        rng = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        # "working" rank fallback (3): 0.7*3 + 0.3*2.0 = 2.7 -> rounds to 3.
        apply_social_inheritance(child, mother, father, template, zone_class_mean=2.0, rng=rng)

        assert child.social_class == "working"


# ---------------------------------------------------------------------------
# apply_inheritance_at_birth (Plan 3, T014/T015)
# ---------------------------------------------------------------------------
#
# The single birth-pipeline entry point wiring apply_trait_inheritance,
# resolve_birth_attributes, and apply_social_inheritance behind ONE
# deterministic RNG stream (design spec Sezione 4/5, "Responsibility
# contract"). Reuses sim_with_zone / _make_agent from above, plus
# SCALAR_HERITABLE_TRAITS / PERSONALITY_HERITABLE_TRAITS /
# _TEST_CLASS_RANK / _TEST_VALID_CLASS_LABELS already defined for the
# lower-level orchestrators.


class TestApplyInheritanceAtBirthEndToEnd:
    """A single call populates every inherited attribute on the child.

    Uses the real "pre_industrial_christian" template (the simulation.config
    default), exercising the full production template-resolution path
    rather than a synthetic dict.
    """

    @pytest.mark.django_db
    def test_populates_every_inherited_attribute_and_wealth_and_zone(self, sim_with_zone):
        sim, zone = sim_with_zone
        mother_personality = {name: 0.65 for name in PERSONALITY_HERITABLE_TRAITS}
        father_personality = {name: 0.35 for name in PERSONALITY_HERITABLE_TRAITS}
        mother = _make_agent(
            sim,
            zone,
            "Mother",
            personality=mother_personality,
            social_class="wealthy",
            education_level=0.6,
            **{name: 0.65 for name in SCALAR_HERITABLE_TRAITS},
        )
        father = _make_agent(
            sim,
            zone,
            "Father",
            personality=father_personality,
            social_class="middle",
            education_level=0.4,
            **{name: 0.35 for name in SCALAR_HERITABLE_TRAITS},
        )
        child = _make_agent(sim, zone, "Child")

        apply_inheritance_at_birth(child, mother, father, sim, sim.current_tick)

        for name in SCALAR_HERITABLE_TRAITS:
            value = getattr(child, name)
            assert isinstance(value, float), f"{name} was not written as a scalar float"
            assert 0.0 <= value <= 1.0, f"{name}={value} outside [0, 1]"

        for name in PERSONALITY_HERITABLE_TRAITS:
            assert name in child.personality, f"{name} missing from child.personality"
            value = child.personality[name]
            assert isinstance(value, float), f"{name} was not written as a float"
            assert 0.0 <= value <= 1.0, f"{name}={value} outside [0, 1]"

        assert child.gender in {"male", "female"}
        assert child.sexual_orientation in {"heterosexual", "bisexual", "homosexual"}
        assert child.social_class in _TEST_VALID_CLASS_LABELS
        assert 0.0 <= child.education_level <= 1.0
        assert child.wealth == 0.0
        assert child.zone == mother.zone


class TestApplyInheritanceAtBirthDeterminism:
    """SC-003: identical simulation seed and tick reproduce an identical
    child state bit for bit -- proof that the fixed step order feeds all
    three inheritance mechanisms from a single continuous RNG stream.

    SCOPE, STATED HONESTLY (phase-6 audit round 1, T046, M-1 test
    remediation): this test calls `apply_inheritance_at_birth` twice in
    ONE interpreter process, sharing one `PYTHONHASHSEED` -- it proves the
    function is a pure, repeatable computation given identical inputs (a
    real and useful property), but three independently-seeded `random.
    Random` instances would ALSO pass it, and it would NOT catch
    `apply_trait_inheritance`'s `sorted(extra_names)` at inheritance.py
    being deleted, since that would only change RNG draw ORDER across
    *different* hash seeds, not within one process replaying the same
    call twice. The genuine cross-process proof is
    `TestApplyTraitInheritanceDeterminismAcrossHashSeeds` below.
    """

    @pytest.mark.django_db
    def test_same_seed_and_tick_yields_identical_child_state(self, sim_with_zone):
        sim, zone = sim_with_zone
        mother = _make_agent(
            sim,
            zone,
            "Mother",
            social_class="wealthy",
            education_level=0.6,
            personality={name: 0.6 for name in PERSONALITY_HERITABLE_TRAITS},
            **{name: 0.6 for name in SCALAR_HERITABLE_TRAITS},
        )
        father = _make_agent(
            sim,
            zone,
            "Father",
            social_class="middle",
            education_level=0.4,
            personality={name: 0.4 for name in PERSONALITY_HERITABLE_TRAITS},
            **{name: 0.4 for name in SCALAR_HERITABLE_TRAITS},
        )
        child_a = _make_agent(sim, zone, "ChildA")
        child_b = _make_agent(sim, zone, "ChildB")

        apply_inheritance_at_birth(child_a, mother, father, sim, sim.current_tick)
        apply_inheritance_at_birth(child_b, mother, father, sim, sim.current_tick)

        for name in SCALAR_HERITABLE_TRAITS:
            assert getattr(child_a, name) == getattr(child_b, name), name
        for name in PERSONALITY_HERITABLE_TRAITS:
            assert child_a.personality[name] == child_b.personality[name], name
        assert child_a.gender == child_b.gender
        assert child_a.sexual_orientation == child_b.sexual_orientation
        assert child_a.social_class == child_b.social_class
        assert child_a.education_level == child_b.education_level
        assert child_a.wealth == child_b.wealth == 0.0
        assert child_a.zone == child_b.zone == mother.zone


class TestApplyInheritanceAtBirthEmptyZoneGuard:
    """A zone with zero living agents does not raise, and the zone-mean
    fallback rank is actually threaded through to a verifiable outcome.

    Uses the "industrial" template (class_rule = clark_regression,
    deterministic -- no rng draw), so the child's exact social_class can be
    hand-computed from the documented fallback rank
    (_UNKNOWN_CLASS_FALLBACK_RANK, the "working" rank = 3) rather than only
    asserting "no exception raised".
    """

    @pytest.mark.django_db
    def test_empty_zone_falls_back_to_working_rank_mean(self, sim_with_zone):
        sim, populated_zone = sim_with_zone
        empty_zone = Zone.objects.create(
            world=populated_zone.world,
            name="EmptyZone",
            zone_type="residential",
            boundary=Polygon.from_bbox((200, 200, 300, 300)),
            center=Point(250, 250),
        )
        sim.config = {"demography_template": "industrial"}

        mother = _make_agent(
            sim,
            populated_zone,
            "Mother",
            social_class="middle",
            personality={name: 0.5 for name in PERSONALITY_HERITABLE_TRAITS},
        )
        father = _make_agent(
            sim,
            populated_zone,
            "Father",
            social_class="middle",
            personality={name: 0.5 for name in PERSONALITY_HERITABLE_TRAITS},
        )
        # Reassign in memory only, never saved: the query the function runs
        # is Agent.objects.filter(zone=mother.zone, is_alive=True), so this
        # is sufficient to make that query return zero rows without
        # depending on the mother's own persisted row being agent-free.
        mother.zone = empty_zone
        child = _make_agent(sim, populated_zone, "Child")

        apply_inheritance_at_birth(child, mother, father, sim, sim.current_tick)

        # clark_regression: child_rank = 0.7*parent_rank + 0.3*zone_class_mean.
        # father.social_class = "middle" -> parent_rank = 2. Empty-zone
        # fallback -> zone_class_mean = 3.0 ("working" rank). rank =
        # 0.7*2 + 0.3*3.0 = 2.3 -> round(2.3) = 2 -> "middle". If the
        # fallback were anything else (e.g. 0.0 from an unguarded empty
        # mean), this would resolve to a different label.
        assert child.social_class == "middle"
        assert child.social_class in _TEST_VALID_SAMPLED_CLASS_LABELS
        assert child.zone == empty_zone


class TestApplyInheritanceAtBirthNoPersistence:
    """The function never calls child.save() -- persistence stays the
    caller's responsibility, matching apply_trait_inheritance's and
    apply_social_inheritance's own no-save contract.
    """

    @pytest.mark.django_db
    def test_child_mutations_are_not_persisted(self, sim_with_zone):
        sim, zone = sim_with_zone
        mother = _make_agent(
            sim,
            zone,
            "Mother",
            social_class="wealthy",
            personality={name: 0.5 for name in PERSONALITY_HERITABLE_TRAITS},
        )
        father = _make_agent(
            sim,
            zone,
            "Father",
            social_class="middle",
            personality={name: 0.5 for name in PERSONALITY_HERITABLE_TRAITS},
        )
        # _make_agent always calls Agent.objects.create(...), so the child
        # already has a pk and a persisted wealth=100.0 (the helper's own
        # default) before the call under test -- this is the case the task
        # flags explicitly: assert the function performed no save by
        # checking a field left unsaved in the database, since the fixture
        # helper itself always saves.
        child = _make_agent(sim, zone, "Child")
        assert child.pk is not None
        original_wealth = child.wealth
        assert original_wealth == 100.0

        apply_inheritance_at_birth(child, mother, father, sim, sim.current_tick)

        # In-memory mutation happened...
        assert child.wealth == 0.0
        # ...but was never persisted: re-fetching from the database still
        # shows the pre-call value, proving no save() occurred.
        persisted = Agent.objects.get(pk=child.pk)
        assert persisted.wealth == original_wealth == 100.0


# ---------------------------------------------------------------------------
# resolve_heirs (Plan 3, T016/T017, user story 2 -- estate/succession)
# ---------------------------------------------------------------------------
#
# The heir-priority ladder (design spec Sezione 5, "Ereditarietà economica
# alla morte"): every era template's economic_inheritance.heir_priority is
# ["spouse", "children", "siblings", "extended_family", "government"]
# (verified identical across all five templates under
# epocha/apps/demography/templates/). resolve_heirs resolves WHO occupies
# each category -- never how the estate is split among them, which is a
# separate later mechanism (T019+, the primogeniture/equal_split/shari'a/
# matrilineal/nationalized distribution rules).
#
# Reuses sim_with_zone / _make_agent from above.


def _heir_template() -> dict:
    """Minimal synthetic template carrying only what resolve_heirs reads.

    Mirrors the real heir_priority order from every era template (verified
    identical across all five in the design spec and the templates
    themselves), isolated from the rest of the demography_template schema so
    these tests do not depend on unrelated template sections.
    """
    return {
        "economic_inheritance": {
            "heir_priority": ["spouse", "children", "siblings", "extended_family", "government"],
        }
    }


class TestResolveHeirsSpouse:
    """spouse category: the surviving partner from the deceased's active
    Couple (design spec Sezione 5, heir priority item 1).
    """

    @pytest.mark.django_db
    def test_spouse_of_active_couple_is_the_sole_heir(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        partner = _make_agent(sim, zone, "Partner")
        form_couple(deceased, partner, formed_at_tick=1)

        heirs = resolve_heirs(deceased, _heir_template())

        assert heirs["spouse"] == [partner]

    @pytest.mark.django_db
    def test_no_active_couple_yields_empty_spouse_list(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")

        heirs = resolve_heirs(deceased, _heir_template())

        assert heirs["spouse"] == []


class TestResolveHeirsChildren:
    """children category: living children found through EITHER parentage FK
    (design spec Sezione 5, heir priority item 2: "tramite parent_agent +
    other_parent_agent"), oldest first (primogeniture-dependent ordering).
    """

    @pytest.mark.django_db
    def test_children_via_both_parent_fks_are_found_ordered_oldest_first(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")

        younger = _make_agent(sim, zone, "Younger", parent_agent=deceased, birth_tick=20)
        older = _make_agent(sim, zone, "Older", other_parent_agent=deceased, birth_tick=5)

        heirs = resolve_heirs(deceased, _heir_template())

        assert heirs["children"] == [older, younger]

    @pytest.mark.django_db
    def test_dead_children_are_excluded(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        _make_agent(sim, zone, "DeadChild", parent_agent=deceased, birth_tick=5, is_alive=False)
        living_child = _make_agent(sim, zone, "LivingChild", parent_agent=deceased, birth_tick=10)

        heirs = resolve_heirs(deceased, _heir_template())

        assert heirs["children"] == [living_child]


class TestResolveHeirsSiblings:
    """siblings category: living agents sharing at least one non-null parent
    with the deceased (either parent_agent or other_parent_agent), never
    including the deceased itself.
    """

    @pytest.mark.django_db
    def test_siblings_sharing_a_parent_are_found_excluding_deceased(self, sim_with_zone):
        sim, zone = sim_with_zone
        common_parent = _make_agent(sim, zone, "CommonParent")
        deceased = _make_agent(sim, zone, "Deceased", parent_agent=common_parent, birth_tick=10)
        sibling = _make_agent(sim, zone, "Sibling", parent_agent=common_parent, birth_tick=5)

        heirs = resolve_heirs(deceased, _heir_template())

        assert heirs["siblings"] == [sibling]
        assert deceased not in heirs["siblings"]

    @pytest.mark.django_db
    def test_half_sibling_via_other_parent_agent_is_found(self, sim_with_zone):
        """A half-sibling sharing only the father (other_parent_agent) must
        also be found -- the "either parent" broadening documented on
        resolve_heirs, wider than the design spec's literal single-FK
        prose.
        """
        sim, zone = sim_with_zone
        common_father = _make_agent(sim, zone, "CommonFather")
        deceased = _make_agent(
            sim, zone, "Deceased", other_parent_agent=common_father, birth_tick=10
        )
        half_sibling = _make_agent(
            sim, zone, "HalfSibling", other_parent_agent=common_father, birth_tick=5
        )

        heirs = resolve_heirs(deceased, _heir_template())

        assert heirs["siblings"] == [half_sibling]

    @pytest.mark.django_db
    def test_dead_siblings_are_excluded(self, sim_with_zone):
        sim, zone = sim_with_zone
        common_parent = _make_agent(sim, zone, "CommonParent")
        deceased = _make_agent(sim, zone, "Deceased", parent_agent=common_parent, birth_tick=10)
        _make_agent(
            sim, zone, "DeadSibling", parent_agent=common_parent, birth_tick=5, is_alive=False
        )

        heirs = resolve_heirs(deceased, _heir_template())

        assert heirs["siblings"] == []


class TestResolveHeirsExtendedFamily:
    """extended_family category: living descendants of the deceased's
    grandparents, bounded to two generations down from them -- aunts/uncles
    and first cousins (design spec Sezione 5, heir priority item 4:
    "Famiglia estesa (lineage di nonno, fino a 2 generazioni)") -- excluding
    whoever is already counted as a child or sibling, and excluding the
    deceased.
    """

    @pytest.mark.django_db
    def test_aunt_and_cousin_are_found_via_grandparent_lineage(self, sim_with_zone):
        sim, zone = sim_with_zone
        grandparent = _make_agent(sim, zone, "Grandparent")
        parent = _make_agent(sim, zone, "Parent", parent_agent=grandparent, birth_tick=-60)
        aunt = _make_agent(sim, zone, "Aunt", parent_agent=grandparent, birth_tick=-58)
        deceased = _make_agent(sim, zone, "Deceased", parent_agent=parent, birth_tick=-30)
        cousin = _make_agent(sim, zone, "Cousin", parent_agent=aunt, birth_tick=-5)

        heirs = resolve_heirs(deceased, _heir_template())

        extended_ids = {agent.id for agent in heirs["extended_family"]}
        assert extended_ids == {aunt.id, cousin.id}

    @pytest.mark.django_db
    def test_no_recorded_parents_yields_empty_extended_family(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Orphan")

        heirs = resolve_heirs(deceased, _heir_template())

        assert heirs["extended_family"] == []


class TestResolveHeirsGovernmentFallbackShape:
    """When every category resolves empty (no heirs at all), the returned
    dict still carries every category key from heir_priority except
    "government" itself -- the terminal treasury fallback is represented by
    every OTHER category being empty, not by a key holding objects -- and
    nothing raises (design spec Sezione 5, heir priority item 5).
    """

    @pytest.mark.django_db
    def test_isolated_agent_yields_every_category_empty_and_no_government_key(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Isolated")

        heirs = resolve_heirs(deceased, _heir_template())

        assert heirs == {
            "spouse": [],
            "children": [],
            "siblings": [],
            "extended_family": [],
        }
        assert "government" not in heirs


class TestResolveHeirsDeterminism:
    """Two calls against the same deceased agent return identical ordering
    in every category -- required for reproducible estate settlement.
    """

    @pytest.mark.django_db
    def test_repeated_calls_return_identical_ordering(self, sim_with_zone):
        sim, zone = sim_with_zone
        grandparent = _make_agent(sim, zone, "Grandparent")
        parent = _make_agent(sim, zone, "Parent", parent_agent=grandparent, birth_tick=-60)
        aunt = _make_agent(sim, zone, "Aunt", parent_agent=grandparent, birth_tick=-58)
        deceased = _make_agent(sim, zone, "Deceased", parent_agent=parent, birth_tick=-30)
        _make_agent(sim, zone, "Cousin", parent_agent=aunt, birth_tick=-5)
        partner = _make_agent(sim, zone, "Partner", birth_tick=-28)
        form_couple(deceased, partner, formed_at_tick=1)
        _make_agent(sim, zone, "Sibling", parent_agent=parent, birth_tick=-25)
        _make_agent(sim, zone, "ChildA", parent_agent=deceased, birth_tick=15)
        _make_agent(sim, zone, "ChildB", parent_agent=deceased, birth_tick=5)

        first = resolve_heirs(deceased, _heir_template())
        second = resolve_heirs(deceased, _heir_template())

        for category in ("spouse", "children", "siblings", "extended_family"):
            assert [agent.id for agent in first[category]] == [
                agent.id for agent in second[category]
            ], category


class TestResolveHeirsQueryBudget:
    """Efficiency requirement: resolve_heirs runs once per death today, and
    the Plan 4 birth/death orchestrator will call it every tick -- the total
    query count must stay bounded and independent of family size (no N+1).
    """

    @pytest.mark.django_db
    def test_full_ladder_stays_within_fixed_query_budget(
        self, sim_with_zone, django_assert_num_queries
    ):
        sim, zone = sim_with_zone
        grandparent = _make_agent(sim, zone, "Grandparent")
        parent = _make_agent(sim, zone, "Parent", parent_agent=grandparent, birth_tick=-60)
        aunt = _make_agent(sim, zone, "Aunt", parent_agent=grandparent, birth_tick=-58)
        _make_agent(sim, zone, "Cousin", parent_agent=aunt, birth_tick=-20)
        deceased = _make_agent(sim, zone, "Deceased", parent_agent=parent, birth_tick=-30)
        partner = _make_agent(sim, zone, "Partner", birth_tick=-28)
        form_couple(deceased, partner, formed_at_tick=1)
        _make_agent(sim, zone, "Sibling", parent_agent=parent, birth_tick=-25)
        _make_agent(sim, zone, "Child", parent_agent=deceased, birth_tick=1)

        # 7 queries total, documented in resolve_heirs's own docstring:
        # spouse (Couple lookup + partner fetch) = 2, children = 1,
        # siblings = 1, extended_family (grandparent ids + aunts/uncles +
        # cousins) = 3. Fixed regardless of how many agents populate each
        # category.
        with django_assert_num_queries(7):
            resolve_heirs(deceased, _heir_template())


# ---------------------------------------------------------------------------
# apply_estate_tax (Plan 3, T018/T019, user story 2 -- estate/succession).
# Routes the era's flat `economic_inheritance.estate_tax_rate` to the
# government treasury via `add_to_treasury`, and returns the inheritable
# remainder -- the amount a later distribution step (T020+) actually splits
# among `resolve_heirs`'s resolved heirs.
# ---------------------------------------------------------------------------

# Tolerance for the conservation assertions below (remainder + treasury
# delta == total_estate_value). At the magnitudes used in these tests
# (estates of a few thousand to ~12,000 units), IEEE 754 double precision's
# ~2^-52 relative epsilon bounds any single multiplication's rounding error
# to roughly 1e-12 in absolute terms; two multiplications plus one addition
# cannot plausibly accumulate beyond that by more than a small constant
# factor. 1e-6 is therefore several orders of magnitude more generous than
# the rounding error these operations can actually produce -- verified
# empirically (see the T018 implementation notes) to be exactly 0.0 for the
# representative estate values exercised here. Used explicitly rather than
# relying on pytest.approx's own default so the tolerance is a documented,
# reviewed choice, not an implicit one.
_CONSERVATION_TOLERANCE = 1e-6


@pytest.fixture
def sim_with_government(sim_with_zone):
    """Extends `sim_with_zone` with a saved Government row for treasury tests.

    `add_to_treasury` (epocha.apps.world.government) requires a real,
    already-saved Government instance -- it calls `government.save(
    update_fields=["government_treasury"])` -- so an in-memory-only stub
    would fail. Reuses `sim_with_zone` rather than duplicating its
    user/simulation/world/zone scaffolding.
    """
    sim, zone = sim_with_zone
    government = Government.objects.create(simulation=sim)
    return sim, zone, government


class TestApplyEstateTaxModernRate:
    """Modern-democracy era: `estate_tax_rate` 0.40 (Piketty 2014, tables
    14.1-14.2 -- top marginal estate/inheritance tax rates)."""

    @pytest.mark.django_db
    def test_treasury_grows_by_exactly_forty_percent_and_remainder_is_sixty_percent(
        self, sim_with_government
    ):
        sim, zone, government = sim_with_government
        total_estate_value = 10_000.0
        rate = 0.40

        remainder = apply_estate_tax(total_estate_value, rate, government, "USD")

        assert remainder == pytest.approx(6_000.0, abs=_CONSERVATION_TOLERANCE)

        # Read back from the database (not the in-memory `government`
        # object add_to_treasury already mutated) to prove the credit was
        # actually persisted, not merely held in memory.
        government.refresh_from_db()
        assert government.government_treasury["USD"] == pytest.approx(
            4_000.0, abs=_CONSERVATION_TOLERANCE
        )


class TestApplyEstateTaxConservation:
    """remainder + treasury delta reproduces `total_estate_value` exactly,
    up to floating-point rounding -- the load-bearing invariant for
    whitepaper Sezione 4.2/4.8's accounting."""

    @pytest.mark.django_db
    def test_remainder_plus_treasury_delta_equals_input_estate(self, sim_with_government):
        sim, zone, government = sim_with_government
        total_estate_value = 12_345.67
        rate = 0.40

        remainder = apply_estate_tax(total_estate_value, rate, government, "USD")

        government.refresh_from_db()
        treasury_delta = government.government_treasury["USD"]

        assert remainder + treasury_delta == pytest.approx(
            total_estate_value, abs=_CONSERVATION_TOLERANCE
        )


class TestApplyEstateTaxZeroRate:
    """Pre-industrial eras: `estate_tax_rate` 0.0 -- feudal dues are
    modelled separately in the economy layer, not as an estate tax here."""

    @pytest.mark.django_db
    def test_zero_rate_routes_nothing_and_returns_full_value(self, sim_with_government):
        sim, zone, government = sim_with_government
        total_estate_value = 5_000.0

        remainder = apply_estate_tax(total_estate_value, 0.0, government, "USD")

        assert remainder == pytest.approx(total_estate_value)

        government.refresh_from_db()
        # "Unchanged or absent": whether the implementation skips the
        # add_to_treasury call entirely for a zero delta, or calls it with
        # amount=0.0, the effective treasury value for this currency is 0.0
        # either way -- .get(..., 0.0) covers both outcomes.
        assert government.government_treasury.get("USD", 0.0) == pytest.approx(0.0)


class TestApplyEstateTaxCurrencyIsolation:
    """Crediting one currency code leaves other currency codes already
    present in the treasury untouched."""

    @pytest.mark.django_db
    def test_crediting_one_currency_leaves_others_untouched(self, sim_with_government):
        sim, zone, government = sim_with_government
        government.government_treasury = {"EUR": 250.0, "gold_solidus": 12.0}
        government.save(update_fields=["government_treasury"])

        apply_estate_tax(1_000.0, 0.40, government, "USD")

        government.refresh_from_db()
        assert government.government_treasury["EUR"] == pytest.approx(250.0)
        assert government.government_treasury["gold_solidus"] == pytest.approx(12.0)
        assert government.government_treasury["USD"] == pytest.approx(400.0)


class TestApplyEstateTaxDegenerateInputs:
    """Out-of-range rate is clamped, not raised; a non-positive estate
    value never produces a negative treasury credit."""

    @pytest.mark.django_db
    def test_rate_above_one_is_clamped_to_one(self, sim_with_government):
        sim, zone, government = sim_with_government
        total_estate_value = 1_000.0

        remainder = apply_estate_tax(total_estate_value, 1.5, government, "USD")

        assert remainder == pytest.approx(0.0)
        government.refresh_from_db()
        assert government.government_treasury["USD"] == pytest.approx(total_estate_value)

    @pytest.mark.django_db
    def test_negative_rate_is_clamped_to_zero(self, sim_with_government):
        sim, zone, government = sim_with_government
        total_estate_value = 1_000.0

        remainder = apply_estate_tax(total_estate_value, -0.2, government, "USD")

        assert remainder == pytest.approx(total_estate_value)
        government.refresh_from_db()
        assert government.government_treasury.get("USD", 0.0) == pytest.approx(0.0)

    @pytest.mark.django_db
    def test_negative_estate_value_produces_exactly_zero_treasury_credit(self, sim_with_government):
        """Fix M-1 (phase-6 audit round 1, T046) -- TEST REMEDIATION:
        `credited >= 0.0` is too loose -- an implementation crediting
        `abs(-500.0) * 0.40 = 200.0` (treating a negative estate as if its
        magnitude were taxable) would satisfy `>= 0.0` and pass, even
        though `apply_estate_tax`'s own documented contract is that a
        non-positive `total_estate_value` credits NOTHING at all (early
        return 0.0, before `add_to_treasury` is ever called) -- the exact
        answer is `0.0`, not merely "non-negative".
        """
        sim, zone, government = sim_with_government

        apply_estate_tax(-500.0, 0.40, government, "USD")

        government.refresh_from_db()
        credited = government.government_treasury.get("USD", 0.0)
        assert credited == 0.0

    @pytest.mark.django_db
    def test_zero_estate_value_returns_zero_and_credits_nothing(self, sim_with_government):
        sim, zone, government = sim_with_government

        remainder = apply_estate_tax(0.0, 0.40, government, "USD")

        assert remainder == pytest.approx(0.0)
        government.refresh_from_db()
        assert government.government_treasury.get("USD", 0.0) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# distribute_estate (Plan 3, T020/T021, user story 2 -- estate/succession).
# The five per-era succession rules that decide HOW the inheritable
# remainder from apply_estate_tax is split among resolve_heirs's resolved
# heirs (design spec Sezione 5): primogeniture (Blackstone 1765),
# equal_split (Napoleonic Code 1804), shari'a (Powers 1986), matrilineal
# (Schneider & Gough 1961), nationalized (Nove 1969). Reuses sim_with_zone /
# _make_agent / _heir_template / _CONSERVATION_TOLERANCE already defined
# above for resolve_heirs and apply_estate_tax.
#
# distribute_estate is a PURE function -- no .save(), no heir mutation --
# so every test below asserts on the returned allocation mapping alone,
# never touching the database beyond the read-only resolve_heirs call that
# builds its `heirs` argument.
# ---------------------------------------------------------------------------


class TestDistributeEstatePrimogeniture:
    """100% to a single heir, cascading children -> spouse -> siblings
    (Blackstone 1765); non-binary heirs ordered together with the female
    heirs at every tier.
    """

    @pytest.mark.django_db
    def test_eldest_son_takes_all_even_if_a_daughter_is_chronologically_older(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        _make_agent(
            sim,
            zone,
            "Daughter",
            parent_agent=deceased,
            birth_tick=1,
            gender=Agent.Gender.FEMALE,
        )
        younger_son = _make_agent(
            sim,
            zone,
            "YoungerSon",
            parent_agent=deceased,
            birth_tick=5,
            gender=Agent.Gender.MALE,
        )
        older_son = _make_agent(
            sim,
            zone,
            "OlderSon",
            parent_agent=deceased,
            birth_tick=3,
            gender=Agent.Gender.MALE,
        )

        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "primogeniture", 10_000.0)

        assert allocation == {older_son.id: 10_000.0}
        assert younger_son.id not in allocation

    @pytest.mark.django_db
    def test_daughters_only_eldest_daughter_takes_all(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        younger_daughter = _make_agent(
            sim,
            zone,
            "YoungerDaughter",
            parent_agent=deceased,
            birth_tick=10,
            gender=Agent.Gender.FEMALE,
        )
        older_daughter = _make_agent(
            sim,
            zone,
            "OlderDaughter",
            parent_agent=deceased,
            birth_tick=2,
            gender=Agent.Gender.FEMALE,
        )

        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "primogeniture", 8_000.0)

        assert allocation == {older_daughter.id: 8_000.0}
        assert younger_daughter.id not in allocation

    @pytest.mark.django_db
    def test_non_binary_child_ordered_with_daughters_by_birth_order(self, sim_with_zone):
        """No sons: the eldest of (daughters + non-binary children) wins,
        purely by birth order. Here the non-binary child is older than the
        daughter and inherits -- proof the two pools are merged, not that
        one categorically outranks the other.
        """
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        daughter = _make_agent(
            sim,
            zone,
            "Daughter",
            parent_agent=deceased,
            birth_tick=10,
            gender=Agent.Gender.FEMALE,
        )
        elder_non_binary = _make_agent(
            sim,
            zone,
            "ElderNonBinary",
            parent_agent=deceased,
            birth_tick=1,
            gender=Agent.Gender.NON_BINARY,
        )

        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "primogeniture", 5_000.0)

        assert allocation == {elder_non_binary.id: 5_000.0}
        assert daughter.id not in allocation

    @pytest.mark.django_db
    def test_no_children_cascades_to_spouse(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        partner = _make_agent(sim, zone, "Partner")
        form_couple(deceased, partner, formed_at_tick=1)

        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "primogeniture", 6_000.0)

        assert allocation == {partner.id: 6_000.0}

    @pytest.mark.django_db
    def test_no_children_no_spouse_cascades_to_eldest_brother(self, sim_with_zone):
        sim, zone = sim_with_zone
        common_parent = _make_agent(sim, zone, "CommonParent")
        deceased = _make_agent(sim, zone, "Deceased", parent_agent=common_parent, birth_tick=10)
        sister = _make_agent(
            sim,
            zone,
            "Sister",
            parent_agent=common_parent,
            birth_tick=2,
            gender=Agent.Gender.FEMALE,
        )
        brother = _make_agent(
            sim,
            zone,
            "Brother",
            parent_agent=common_parent,
            birth_tick=5,
            gender=Agent.Gender.MALE,
        )

        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "primogeniture", 3_000.0)

        assert allocation == {brother.id: 3_000.0}
        assert sister.id not in allocation

    @pytest.mark.django_db
    def test_no_heirs_at_all_yields_empty_allocation(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Isolated")

        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "primogeniture", 1_000.0)

        assert allocation == {}


class TestDistributeEstateEqualSplit:
    """Cash divided equally among children, with the spouse receiving a
    share equal to one child's (Napoleonic Code 1804): N children + spouse
    = N+1 equal shares.
    """

    @pytest.mark.django_db
    def test_three_children_and_spouse_yield_four_equal_shares(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        partner = _make_agent(sim, zone, "Partner")
        form_couple(deceased, partner, formed_at_tick=1)
        child_a = _make_agent(sim, zone, "ChildA", parent_agent=deceased, birth_tick=1)
        child_b = _make_agent(sim, zone, "ChildB", parent_agent=deceased, birth_tick=2)
        child_c = _make_agent(sim, zone, "ChildC", parent_agent=deceased, birth_tick=3)

        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "equal_split", 8_000.0)

        expected_share = 2_000.0
        for heir_id in (child_a.id, child_b.id, child_c.id, partner.id):
            assert allocation[heir_id] == pytest.approx(expected_share, abs=_CONSERVATION_TOLERANCE)
        assert sum(allocation.values()) == pytest.approx(8_000.0, abs=_CONSERVATION_TOLERANCE)


class TestDistributeEstateSharia:
    """Spouse takes 1/8 with children present, else 1/4; sons receive
    exactly twice a daughter's share (Powers 1986).
    """

    @pytest.mark.django_db
    def test_spouse_takes_one_eighth_with_children_and_son_takes_double_daughter(
        self, sim_with_zone
    ):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        partner = _make_agent(sim, zone, "Partner")
        form_couple(deceased, partner, formed_at_tick=1)
        son = _make_agent(
            sim, zone, "Son", parent_agent=deceased, birth_tick=1, gender=Agent.Gender.MALE
        )
        daughter = _make_agent(
            sim,
            zone,
            "Daughter",
            parent_agent=deceased,
            birth_tick=2,
            gender=Agent.Gender.FEMALE,
        )

        inheritable = 8_000.0
        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "shari'a", inheritable)

        assert allocation[partner.id] == pytest.approx(1_000.0, abs=_CONSERVATION_TOLERANCE)
        assert allocation[son.id] == pytest.approx(
            2 * allocation[daughter.id], abs=_CONSERVATION_TOLERANCE
        )
        assert sum(allocation.values()) == pytest.approx(inheritable, abs=_CONSERVATION_TOLERANCE)

    @pytest.mark.django_db
    def test_spouse_takes_one_quarter_without_children(self, sim_with_zone):
        """No children: the spouse's fixed share drops to 1/4; the
        residual cascades to the deceased's siblings -- the documented
        simplification of the classical residuary hierarchy described on
        `_distribute_sharia`.
        """
        sim, zone = sim_with_zone
        common_parent = _make_agent(sim, zone, "CommonParent")
        deceased = _make_agent(sim, zone, "Deceased", parent_agent=common_parent, birth_tick=10)
        partner = _make_agent(sim, zone, "Partner", birth_tick=8)
        form_couple(deceased, partner, formed_at_tick=1)
        _make_agent(sim, zone, "Sibling", parent_agent=common_parent, birth_tick=5)

        inheritable = 4_000.0
        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "shari'a", inheritable)

        assert allocation[partner.id] == pytest.approx(1_000.0, abs=_CONSERVATION_TOLERANCE)
        assert sum(allocation.values()) == pytest.approx(inheritable, abs=_CONSERVATION_TOLERANCE)


class TestDistributeShariaRaddBranchSpouseSoleHeir:
    """Fix M-1 (phase-6 audit round 1, T046) -- TEST REMEDIATION: no
    existing fixture builds a deceased with a spouse and NEITHER children
    NOR siblings, so `_distribute_sharia`'s radd branch (`inheritance.py`,
    `elif spouse: allocation[spouse[0].id] = spouse_amount + residual`)
    never ran -- deleting that line, which routes the WHOLE estate to a
    surviving spouse (mirroring the real "radd", return of residue, effect
    for a sole surviving Qur'anic heir per `_distribute_sharia`'s own
    docstring step 2), passed every test before this fix. It is also the
    one shari'a path where conservation could break silently -- the
    spouse's fixed fraction (1/4, no children) is topped up by the ENTIRE
    residual here rather than only receiving it via the residuary
    `_split_two_to_one` split every other populated-pool case goes
    through, so nothing else in this module's test suite would notice a
    regression that dropped the `+ residual` term.
    """

    @pytest.mark.django_db
    def test_spouse_alone_with_no_children_or_siblings_receives_the_whole_estate(
        self, sim_with_zone
    ):
        sim, zone = sim_with_zone
        # No parent_agent recorded on `deceased` -> _resolve_sibling_heirs
        # has no basis to find a sibling at all (0 extra queries, per its
        # own documented cost contract).
        deceased = _make_agent(sim, zone, "Deceased")
        partner = _make_agent(sim, zone, "Partner")
        form_couple(deceased, partner, formed_at_tick=1)

        inheritable = 10_000.33
        heirs = resolve_heirs(deceased, _heir_template())
        assert heirs["children"] == []
        assert heirs["siblings"] == []
        assert [agent.id for agent in heirs["spouse"]] == [partner.id]

        allocation = distribute_estate(deceased, heirs, "shari'a", inheritable)

        assert allocation == {partner.id: inheritable}, (
            f"allocation={allocation!r} -- the radd branch must route the "
            "ENTIRE estate to the sole surviving spouse, exactly, not merely "
            "their fixed 1/4 fraction"
        )
        assert sum(allocation.values()) == inheritable


class TestDistributeShariaSpouseAlsoSiblingConservesValue:
    """Fix C-2 (phase-6 audit round 1, T046): `_distribute_sharia` splits
    the residual among `pool` (the deceased's siblings, absent children)
    via `_split_two_to_one`, then OVERWRITES `allocation[spouse[0].id]`
    with the spouse's fixed fraction -- if the spouse is ALSO one of the
    siblings in `pool` (reachable: `couple.py`'s `form_couple` has no
    consanguinity check anywhere, and `marriage_market_radius: "same_zone"`
    concentrates candidates in a small, often-related pool), that
    overwrite silently destroys the sibling residuary share
    `_split_two_to_one` already computed for the very same person, instead
    of the two shares -- fixed spousal fraction and residuary sibling
    share -- adding together as two genuinely separate entitlements.
    """

    @pytest.mark.django_db
    def test_spouse_who_is_also_a_sibling_receives_both_shares_not_just_one(self, sim_with_zone):
        sim, zone = sim_with_zone
        common_parent = _make_agent(sim, zone, "CommonParent")
        deceased = _make_agent(
            sim,
            zone,
            "Deceased",
            parent_agent=common_parent,
            birth_tick=10,
            gender=Agent.Gender.MALE,
        )
        # form_couple performs no consanguinity check (verified: no such
        # check exists anywhere in couple.py) -- a same-zone sibling is as
        # valid a marriage candidate as any other agent to this module.
        spouse_and_sibling = _make_agent(
            sim,
            zone,
            "SpouseSibling",
            parent_agent=common_parent,
            birth_tick=8,
            gender=Agent.Gender.MALE,
        )
        other_sibling = _make_agent(
            sim,
            zone,
            "OtherSibling",
            parent_agent=common_parent,
            birth_tick=6,
            gender=Agent.Gender.MALE,
        )
        form_couple(deceased, spouse_and_sibling, formed_at_tick=1)

        inheritable = 1_000.0
        heirs = resolve_heirs(deceased, _heir_template())
        assert {agent.id for agent in heirs["siblings"]} == {
            spouse_and_sibling.id,
            other_sibling.id,
        }
        assert [agent.id for agent in heirs["spouse"]] == [spouse_and_sibling.id]

        allocation = distribute_estate(deceased, heirs, "shari'a", inheritable)

        assert sum(allocation.values()) == pytest.approx(
            inheritable, abs=_CONSERVATION_TOLERANCE
        ), (
            f"allocation {allocation} sums to {sum(allocation.values())}, not the "
            f"full {inheritable} -- the spouse-is-also-sibling overwrite destroyed value"
        )
        # No children: spouse_fraction = 0.25 -> spouse_amount = 250.0;
        # residual = 750.0 split 2:1 male:male between the two brothers,
        # 375.0 each via _split_two_to_one. The spouse-sibling receives
        # BOTH entitlements added together (625.0 = 250.0 + 375.0), not
        # merely one or the other.
        assert allocation[spouse_and_sibling.id] == pytest.approx(
            625.0, abs=_CONSERVATION_TOLERANCE
        )
        assert allocation[other_sibling.id] == pytest.approx(375.0, abs=_CONSERVATION_TOLERANCE)


class TestDistributeEqualSplitDuplicateHeirConservesValue:
    """Fix C-2 (phase-6 audit round 1, T046): `_distribute_equal_split`
    builds `recipients = [*children, *spouse]` and hands it straight to
    `_allocate_with_exact_remainder` -- if the SAME id appears twice in
    that list, the returned dict collapses the two entries into one key
    while `_allocate_with_exact_remainder`'s own `running_sum` still
    counts the share twice (once per LIST entry, not per unique id), so
    the final entry's `total - running_sum` absorbs a share nobody's
    dict key actually holds, and the allocation's total falls short of
    `inheritable`.

    Unlike the sharia case above (realistically reachable via a same-zone,
    consanguinity-unchecked marriage), a spouse who is ALSO a CHILD of the
    same deceased has no realistic path through this module's own heir
    resolution -- parentage and spousal edges are structurally distinct
    relations resolved by different mechanisms. This test constructs the
    duplicate directly, proving the shared `_allocate_with_exact_remainder`
    shape is not silently exploitable by any future caller that builds
    `recipients` less carefully, not that today's pipeline currently
    reaches this exact combination on its own.
    """

    @pytest.mark.django_db
    def test_a_duplicate_id_in_recipients_does_not_lose_value(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        shared_agent = _make_agent(sim, zone, "SharedAgent", parent_agent=deceased, birth_tick=1)
        other_child = _make_agent(sim, zone, "OtherChild", parent_agent=deceased, birth_tick=2)

        # shared_agent appears in BOTH categories -- the duplicate-id shape
        # C-2 flags, constructed directly since this exact combination has
        # no realistic path through resolve_heirs.
        heirs = {"children": [shared_agent, other_child], "spouse": [shared_agent]}

        allocation = distribute_estate(deceased, heirs, "equal_split", 900.0)

        assert sum(allocation.values()) == pytest.approx(900.0), (
            f"allocation {allocation} sums to {sum(allocation.values())}, not the "
            "full 900.0 -- the duplicate id silently lost a share"
        )
        # Deduplicated: 2 unique heirs, 450.0 each -- not 300.0 (as if 3
        # positional slots were each paid independently) and not 600.0 (as
        # if the duplicate were paid twice under one key).
        assert allocation[shared_agent.id] == pytest.approx(450.0)
        assert allocation[other_child.id] == pytest.approx(450.0)


class TestDistributeEstateMatrilineal:
    """Estate passes to the children of the deceased's SISTERS (Schneider
    & Gough 1961); the deceased's own children never receive anything
    under this rule.
    """

    @pytest.mark.django_db
    def test_sisters_children_inherit_not_the_deceaseds_own_children(self, sim_with_zone):
        sim, zone = sim_with_zone
        common_parent = _make_agent(sim, zone, "CommonParent")
        deceased = _make_agent(sim, zone, "Deceased", parent_agent=common_parent, birth_tick=10)
        sister = _make_agent(
            sim,
            zone,
            "Sister",
            parent_agent=common_parent,
            birth_tick=5,
            gender=Agent.Gender.FEMALE,
        )
        niece = _make_agent(sim, zone, "Niece", parent_agent=sister, birth_tick=20)
        nephew = _make_agent(sim, zone, "Nephew", parent_agent=sister, birth_tick=25)
        own_child = _make_agent(sim, zone, "OwnChild", parent_agent=deceased, birth_tick=30)

        inheritable = 6_000.0
        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "matrilineal", inheritable)

        assert set(allocation.keys()) == {niece.id, nephew.id}
        assert own_child.id not in allocation
        assert allocation[niece.id] == pytest.approx(3_000.0, abs=_CONSERVATION_TOLERANCE)
        assert sum(allocation.values()) == pytest.approx(inheritable, abs=_CONSERVATION_TOLERANCE)

    @pytest.mark.django_db
    def test_no_sisters_yields_empty_allocation(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")

        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "matrilineal", 2_000.0)

        assert allocation == {}


class TestDistributeEstateNationalized:
    """100% to the state (Nove 1969, Soviet-style expropriation): the
    allocation is always empty, regardless of which heirs survive --
    "empty" here means the whole amount routes to the treasury, not that
    no heirs were found.
    """

    @pytest.mark.django_db
    def test_allocation_is_always_empty_even_with_surviving_heirs(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        partner = _make_agent(sim, zone, "Partner")
        form_couple(deceased, partner, formed_at_tick=1)
        _make_agent(sim, zone, "Child", parent_agent=deceased, birth_tick=1)

        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "nationalized", 9_000.0)

        assert allocation == {}


class TestDistributeEstateUnknownRule:
    """An unrecognized rule falls back to equal_split with a WARNING log,
    matching this module's established never-crash-on-template-data
    posture.
    """

    @pytest.mark.django_db
    def test_unknown_rule_falls_back_to_equal_split_with_warning(self, sim_with_zone, caplog):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        child_a = _make_agent(sim, zone, "ChildA", parent_agent=deceased, birth_tick=1)
        child_b = _make_agent(sim, zone, "ChildB", parent_agent=deceased, birth_tick=2)

        heirs = resolve_heirs(deceased, _heir_template())
        with caplog.at_level(logging.WARNING):
            allocation = distribute_estate(deceased, heirs, "not_a_real_rule", 4_000.0)

        assert allocation[child_a.id] == pytest.approx(2_000.0, abs=_CONSERVATION_TOLERANCE)
        assert allocation[child_b.id] == pytest.approx(2_000.0, abs=_CONSERVATION_TOLERANCE)
        assert any("not_a_real_rule" in message for message in caplog.messages)


class TestDistributeEstateConservation:
    """Sum of the allocation equals `inheritable` exactly, up to
    floating-point representation, for every rule that resolves at least
    one heir -- the load-bearing invariant for whitepaper Sezione 4.2/4.8's
    accounting (see `_allocate_with_exact_remainder`'s docstring for the
    remainder-absorption technique).

    CORRECTED CLAIM (phase-6 audit round 1, T046, M-1 test remediation):
    this class previously claimed `10_000.33` "does NOT divide evenly
    across two or three heirs" -- independently verified false while
    fixing this: `sum([10_000.33/n]*n) == 10_000.33` is exactly `True` in
    IEEE 754 for every n from 2 through 11 (checked directly in Python).
    `_CONSERVATION_TOLERANCE`'s `pytest.approx` below therefore never
    exercises anything -- every test in this class passes verbatim even
    if `_allocate_with_exact_remainder` is replaced by naive division
    (confirmed by temporarily making that exact swap and watching nothing
    fail; see `TestDistributeEstateConservationAdversarial` below, which
    replaces this fixture's premise with amounts independently verified,
    in Python, to genuinely NOT divide evenly, and which DOES fail under
    that same swap). This class is kept for its other value (rule
    coverage, sibling-cascade / children-present branches) but is no
    longer the adversarial proof its own docstring used to claim -- that
    proof lives in `TestDistributeEstateConservationAdversarial`.
    """

    @pytest.mark.django_db
    def test_primogeniture_conserves(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        _make_agent(sim, zone, "Son", parent_agent=deceased, birth_tick=1, gender=Agent.Gender.MALE)

        inheritable = 10_000.33
        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "primogeniture", inheritable)

        assert sum(allocation.values()) == pytest.approx(inheritable, abs=_CONSERVATION_TOLERANCE)

    @pytest.mark.django_db
    def test_equal_split_conserves_with_three_children_and_spouse(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        partner = _make_agent(sim, zone, "Partner")
        form_couple(deceased, partner, formed_at_tick=1)
        _make_agent(sim, zone, "ChildA", parent_agent=deceased, birth_tick=1)
        _make_agent(sim, zone, "ChildB", parent_agent=deceased, birth_tick=2)
        _make_agent(sim, zone, "ChildC", parent_agent=deceased, birth_tick=3)

        inheritable = 10_000.33
        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "equal_split", inheritable)

        assert sum(allocation.values()) == pytest.approx(inheritable, abs=_CONSERVATION_TOLERANCE)

    @pytest.mark.django_db
    def test_sharia_conserves_with_children(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        partner = _make_agent(sim, zone, "Partner")
        form_couple(deceased, partner, formed_at_tick=1)
        _make_agent(sim, zone, "Son", parent_agent=deceased, birth_tick=1, gender=Agent.Gender.MALE)
        _make_agent(
            sim,
            zone,
            "Daughter",
            parent_agent=deceased,
            birth_tick=2,
            gender=Agent.Gender.FEMALE,
        )
        _make_agent(
            sim,
            zone,
            "NonBinaryChild",
            parent_agent=deceased,
            birth_tick=3,
            gender=Agent.Gender.NON_BINARY,
        )

        inheritable = 10_000.33
        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "shari'a", inheritable)

        assert sum(allocation.values()) == pytest.approx(inheritable, abs=_CONSERVATION_TOLERANCE)

    @pytest.mark.django_db
    def test_sharia_conserves_without_children_via_sibling_cascade(self, sim_with_zone):
        sim, zone = sim_with_zone
        common_parent = _make_agent(sim, zone, "CommonParent")
        deceased = _make_agent(sim, zone, "Deceased", parent_agent=common_parent, birth_tick=10)
        partner = _make_agent(sim, zone, "Partner", birth_tick=8)
        form_couple(deceased, partner, formed_at_tick=1)
        _make_agent(
            sim,
            zone,
            "Brother",
            parent_agent=common_parent,
            birth_tick=5,
            gender=Agent.Gender.MALE,
        )
        _make_agent(
            sim,
            zone,
            "Sister",
            parent_agent=common_parent,
            birth_tick=6,
            gender=Agent.Gender.FEMALE,
        )

        inheritable = 10_000.33
        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "shari'a", inheritable)

        assert sum(allocation.values()) == pytest.approx(inheritable, abs=_CONSERVATION_TOLERANCE)

    @pytest.mark.django_db
    def test_matrilineal_conserves_with_three_nieces_and_nephews(self, sim_with_zone):
        sim, zone = sim_with_zone
        common_parent = _make_agent(sim, zone, "CommonParent")
        deceased = _make_agent(sim, zone, "Deceased", parent_agent=common_parent, birth_tick=10)
        sister = _make_agent(
            sim,
            zone,
            "Sister",
            parent_agent=common_parent,
            birth_tick=5,
            gender=Agent.Gender.FEMALE,
        )
        _make_agent(sim, zone, "Niece", parent_agent=sister, birth_tick=20)
        _make_agent(sim, zone, "Nephew", parent_agent=sister, birth_tick=25)
        _make_agent(sim, zone, "SecondNephew", parent_agent=sister, birth_tick=27)

        inheritable = 10_000.33
        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "matrilineal", inheritable)

        assert sum(allocation.values()) == pytest.approx(inheritable, abs=_CONSERVATION_TOLERANCE)


class TestDistributeEstateConservationAdversarial:
    """Fix M-1 (phase-6 audit round 1, T046) -- TEST REMEDIATION: the
    genuinely adversarial conservation proof `TestDistributeEstateConservation`
    above no longer is (see its corrected docstring). Both amounts below
    were found by directly checking, in Python, which ones make NAIVE
    division (`share = amount/n` reconstructed via `sum([share]*n)`, i.e.
    what `_allocate_with_exact_remainder`'s remainder-absorption technique
    exists to avoid) NOT reproduce the target exactly:

        59778.33 / 7  -> naive reconstruction = 59778.329999999994
                          (drift -7.28e-12 from the target)
        214368.56 / 11 -> naive reconstruction = 214368.55999999997
                          (drift -2.91e-11 from the target)

    -- and separately confirming, in Python, that the REAL implementation
    (`distribute_estate` -> `_allocate_with_exact_remainder`) produces a
    sum equal to the target EXACTLY for these same amounts (not merely
    within tolerance): `sum(allocation.values()) == inheritable` is
    literal Python `True`, no `pytest.approx` anywhere in this class.
    7 and 11 heirs deliberately (not 2, 3, or 4, which `10_000.33`
    happens to divide exactly for all the way up to 11 -- see the note
    above -- and not chosen from that "nice" amount at all).

    DISCRIMINATION VERIFIED BY MUTATION (per the audit's own required
    proof standard): `_allocate_with_exact_remainder` was temporarily
    replaced with naive per-heir division (`{heir_id: amount / len(...)
    for heir_id, _ in ordered_shares}`, dropping the remainder-absorption
    entirely) and both tests below were re-run. Both failed --
    `59778.329999999994 != 59778.33` and `214368.55999999997 !=
    214368.56` -- exactly the drift figures measured independently above,
    confirming these tests actually exercise the mechanism they exist to
    protect. The mutation was then reverted; `git diff` showed zero
    residual changes to `inheritance.py` afterward.

    NUANCE WORTH RECORDING (found while building this fixture, not
    something the phase-6 audit round 1 itself asserted): the guarantee
    `_allocate_with_exact_remainder`'s own docstring proves is narrower
    than "the sum of the returned dict's values equals total" for an
    ARBITRARY amount -- it is `running_sum + (total - running_sum) ==
    total`, which does hold universally (confirmed over 50,000 random
    trials, 0 failures), computed via the SAME left-to-right accumulation
    the function uses internally. Re-summing the returned dict's values
    via Python's own `sum()` builtin (which, as of Python 3.12, uses a
    compensated/Neumaier summation algorithm for floats, NOT naive
    left-to-right addition) is a DIFFERENT computation and can disagree
    with the target by 1-2 ULP for a substantial fraction of random
    amounts -- independently measured at roughly 22% of random amounts
    for n=7 and 48% for n=11 across 20,000 trials each. The two amounts
    used below were specifically chosen to avoid this: they are not
    "any amount that fails naive division", they are amounts independently
    confirmed to ALSO satisfy `sum(allocation.values()) == inheritable`
    exactly via Python's real `sum()`. A test built from an arbitrary
    adversarial-for-naive-division amount, without this second check,
    would be flaky.
    """

    @pytest.mark.django_db
    def test_equal_split_conserves_exactly_across_seven_heirs(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        partner = _make_agent(sim, zone, "Partner")
        form_couple(deceased, partner, formed_at_tick=1)
        for i in range(6):
            _make_agent(sim, zone, f"Child{i}", parent_agent=deceased, birth_tick=i + 1)

        inheritable = 59778.33
        heirs = resolve_heirs(deceased, _heir_template())
        assert len(heirs["children"]) + len(heirs["spouse"]) == 7

        allocation = distribute_estate(deceased, heirs, "equal_split", inheritable)

        assert sum(allocation.values()) == inheritable, (
            f"sum(allocation.values())={sum(allocation.values())!r} != "
            f"inheritable={inheritable!r} -- exact conservation broke across 7 heirs"
        )

    @pytest.mark.django_db
    def test_matrilineal_conserves_exactly_across_eleven_nieces_and_nephews(self, sim_with_zone):
        sim, zone = sim_with_zone
        common_parent = _make_agent(sim, zone, "CommonParent")
        deceased = _make_agent(sim, zone, "Deceased", parent_agent=common_parent, birth_tick=10)
        sister = _make_agent(
            sim,
            zone,
            "Sister",
            parent_agent=common_parent,
            birth_tick=5,
            gender=Agent.Gender.FEMALE,
        )
        for i in range(11):
            _make_agent(sim, zone, f"NieceOrNephew{i}", parent_agent=sister, birth_tick=20 + i)

        inheritable = 214368.56
        heirs = resolve_heirs(deceased, _heir_template())
        allocation = distribute_estate(deceased, heirs, "matrilineal", inheritable)
        assert len(allocation) == 11

        assert sum(allocation.values()) == inheritable, (
            f"sum(allocation.values())={sum(allocation.values())!r} != "
            f"inheritable={inheritable!r} -- exact conservation broke across 11 nieces/nephews"
        )


# ---------------------------------------------------------------------------
# T022 (Plan 3, user story 2 -- estate/succession, SC-002): end-to-end
# conservation across the FULL chain estate -> apply_estate_tax ->
# distribute_estate, for every one of the five per-era succession rules.
#
# The tests above (TestApplyEstateTaxConservation, TestDistributeEstate
# Conservation) each already prove conservation for one leg of the chain in
# isolation: apply_estate_tax's own remainder + treasury delta, and
# distribute_estate's own allocation sum. Neither, alone, proves the two
# legs compose correctly end to end. This class is the guard for that
# composition -- the actual invariant whitepaper Sezione 4.2 ("Economia
# comportamentale") and Sezione 4.8 ("Economia -- livello base") both state
# and both of which are already CONVERGED: no value is created or destroyed
# when an estate is settled, whichever succession rule the era template
# selects.
#
# The treasury side of the equation is read back from the DATABASE (via
# government.refresh_from_db()), never from apply_estate_tax's own return
# value or from add_to_treasury's in-memory mutation -- this is what proves
# the money actually landed in a persisted row, not merely that the
# arithmetic leading up to the write was correct.
# ---------------------------------------------------------------------------


def _build_deceased_for_primogeniture(sim, zone):
    """A single son: primogeniture's cascade resolves him as sole heir."""
    deceased = _make_agent(sim, zone, "Deceased")
    _make_agent(sim, zone, "Son", parent_agent=deceased, birth_tick=1, gender=Agent.Gender.MALE)
    return deceased


def _build_deceased_for_equal_split(sim, zone):
    """Spouse + two children: three equal shares, none of which divides
    total_estate_value evenly -- exercises the remainder-absorption path.
    """
    deceased = _make_agent(sim, zone, "Deceased")
    partner = _make_agent(sim, zone, "Partner")
    form_couple(deceased, partner, formed_at_tick=1)
    _make_agent(sim, zone, "ChildA", parent_agent=deceased, birth_tick=1)
    _make_agent(sim, zone, "ChildB", parent_agent=deceased, birth_tick=2)
    return deceased


def _build_deceased_for_sharia(sim, zone):
    """Spouse + son + daughter: exercises both the spouse's fixed fraction
    and the 2:1 male:female residuary split in the same allocation.
    """
    deceased = _make_agent(sim, zone, "Deceased")
    partner = _make_agent(sim, zone, "Partner")
    form_couple(deceased, partner, formed_at_tick=1)
    _make_agent(sim, zone, "Son", parent_agent=deceased, birth_tick=1, gender=Agent.Gender.MALE)
    _make_agent(
        sim, zone, "Daughter", parent_agent=deceased, birth_tick=2, gender=Agent.Gender.FEMALE
    )
    return deceased


def _build_deceased_for_matrilineal(sim, zone):
    """A sister with two living children: matrilineal never reads the
    deceased's own children or spouse, only descendants of sisters.
    """
    common_parent = _make_agent(sim, zone, "CommonParent")
    deceased = _make_agent(sim, zone, "Deceased", parent_agent=common_parent, birth_tick=10)
    sister = _make_agent(
        sim, zone, "Sister", parent_agent=common_parent, birth_tick=5, gender=Agent.Gender.FEMALE
    )
    _make_agent(sim, zone, "Niece", parent_agent=sister, birth_tick=20)
    _make_agent(sim, zone, "Nephew", parent_agent=sister, birth_tick=25)
    return deceased


def _build_deceased_for_nationalized(sim, zone):
    """Spouse + child present and living: proves the empty allocation is
    "nationalized by design", not "nobody was found" (see
    TestDistributeEstateNationalized above).
    """
    deceased = _make_agent(sim, zone, "Deceased")
    partner = _make_agent(sim, zone, "Partner")
    form_couple(deceased, partner, formed_at_tick=1)
    _make_agent(sim, zone, "Child", parent_agent=deceased, birth_tick=1)
    return deceased


class TestFullEstateChainConservation:
    """SC-002: sum(distribute_estate(...).values()) + (treasury delta from
    apply_estate_tax, read from the database) == the deceased's total
    estate, exactly within `_CONSERVATION_TOLERANCE`, for every one of the
    five succession rules, under a non-zero tax rate (0.40, the
    modern_democracy rate -- see TestApplyEstateTaxModernRate).

    `total_estate_value` is deliberately 12_345.67 (matching
    TestApplyEstateTaxConservation) rather than a round number, so the
    conservation assertion is not accidentally satisfied by inputs that
    happen to divide evenly at every step of the chain.
    """

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "rule, build_deceased",
        [
            ("primogeniture", _build_deceased_for_primogeniture),
            ("equal_split", _build_deceased_for_equal_split),
            ("shari'a", _build_deceased_for_sharia),
            ("matrilineal", _build_deceased_for_matrilineal),
            ("nationalized", _build_deceased_for_nationalized),
        ],
    )
    def test_full_chain_conserves_total_estate(self, sim_with_government, rule, build_deceased):
        sim, zone, government = sim_with_government
        deceased = build_deceased(sim, zone)

        total_estate_value = 12_345.67
        rate = 0.40

        heirs = resolve_heirs(deceased, _heir_template())
        inheritable = apply_estate_tax(total_estate_value, rate, government, "USD")

        government.refresh_from_db()
        tax_treasury_delta = government.government_treasury["USD"]

        allocation = distribute_estate(deceased, heirs, rule, inheritable)

        if rule == "nationalized":
            # nationalized (Nove 1969): distribute_estate's allocation is
            # empty BY DESIGN -- the entire post-tax remainder is state
            # property, not an unclaimed leftover (see the EMPTY
            # ALLOCATION SHAPE note in distribute_estate's own docstring).
            # distribute_estate is a pure function that only ever returns
            # an id-keyed allocation mapping; crediting the nationalized
            # remainder to the treasury is explicitly the CALLER's
            # responsibility (a later task, T029's
            # process_inheritance_batch), not distribute_estate's own. This
            # test simulates that caller step directly via add_to_treasury
            # -- the same primitive apply_estate_tax itself already used
            # for the tax leg -- so the chain closes end to end, then
            # re-reads the treasury from the database a second time to
            # prove the nationalized remainder, and not merely the tax,
            # actually landed.
            assert allocation == {}
            add_to_treasury(government, "USD", inheritable)
            government.refresh_from_db()
            total_treasury_delta = government.government_treasury["USD"]
            assert total_treasury_delta == pytest.approx(
                total_estate_value, abs=_CONSERVATION_TOLERANCE
            )
        else:
            allocation_total = sum(allocation.values())
            assert allocation_total + tax_treasury_delta == pytest.approx(
                total_estate_value, abs=_CONSERVATION_TOLERANCE
            )


# ---------------------------------------------------------------------------
# transfer_loans_as_lender (Plan 3, T023, user story 2 -- estate/succession).
# Reassigns the deceased's outstanding CREDITS (active loans where the
# deceased was the LENDER) to a living heir, or to the banking system when
# no living heir exists, so an agent's death never evaporates money someone
# else owes them -- the same conservation posture as apply_estate_tax /
# distribute_estate above, applied to the deceased's loan book rather than
# their cash/property estate.
# ---------------------------------------------------------------------------


def _make_loan(sim, borrower, lender=None, lender_type="agent", status="active", **kwargs):
    """Helper: create a Loan with sensible defaults (mirrors the pattern in
    epocha/apps/economy/tests/test_credit.py).
    """
    defaults = dict(
        principal=1_000.0,
        interest_rate=0.05,
        remaining_balance=1_000.0,
        issued_at_tick=0,
        due_at_tick=None,
    )
    defaults.update(kwargs)
    return Loan.objects.create(
        simulation=sim,
        borrower=borrower,
        lender=lender,
        lender_type=lender_type,
        status=status,
        **defaults,
    )


class TestTransferLoansAsLenderToLivingHeir:
    """An active loan where the deceased was the lender moves to a living
    heir, drawn from the heirs dict resolve_heirs already resolved.
    """

    @pytest.mark.django_db
    def test_active_loan_reassigned_to_sole_living_heir(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        heir = _make_agent(sim, zone, "Heir", parent_agent=deceased, birth_tick=1)
        borrower = _make_agent(sim, zone, "Borrower")
        loan = _make_loan(sim, borrower, lender=deceased)

        transfer_loans_as_lender(deceased, {"children": [heir]}, {heir.id: 0.0})

        loan.refresh_from_db()
        assert loan.lender_id == heir.id
        assert loan.lender_type == "agent"
        assert loan.status == "active"

    @pytest.mark.django_db
    def test_multiple_active_loans_round_robin_across_heirs_in_priority_order(self, sim_with_zone):
        """Round-robin over the flattened heir list, in the same
        spouse-first / children-oldest-first priority order the estate
        distribution rules use -- every heir must receive at least one
        loan when loans outnumber heirs, and no loan is dropped.
        """
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        spouse = _make_agent(sim, zone, "Spouse")
        form_couple(deceased, spouse, formed_at_tick=1)
        child = _make_agent(sim, zone, "Child", parent_agent=deceased, birth_tick=1)
        borrower = _make_agent(sim, zone, "Borrower")
        loans = [_make_loan(sim, borrower, lender=deceased) for _ in range(3)]

        heirs = resolve_heirs(deceased, _heir_template())
        assert [agent.id for agent in heirs["spouse"]] == [spouse.id]
        assert [agent.id for agent in heirs["children"]] == [child.id]

        # Same spouse-first / oldest-first order distribute_estate itself
        # would have produced (e.g. under equal_split) -- this test is
        # about round-robin ordering, not any specific rule's formula.
        cash_allocation = {spouse.id: 0.0, child.id: 0.0}
        transfer_loans_as_lender(deceased, heirs, cash_allocation)

        for loan in loans:
            loan.refresh_from_db()
        new_lender_ids = {loan.lender_id for loan in loans}
        # Both heirs receive at least one loan (3 loans, 2 heirs,
        # round-robin) -- no heir is skipped and no loan is dropped.
        assert new_lender_ids == {spouse.id, child.id}
        assert loans[0].lender_id == spouse.id
        assert loans[1].lender_id == child.id
        assert loans[2].lender_id == spouse.id


class TestTransferLoansAsLenderFollowsTheCashDistributionRule:
    """Fix I-6 (phase-6 audit round 1, T046): loans must follow the SAME
    distribution rule cash uses (design spec Sezione 5, "Loans ereditati
    (come lender)": "usando la stessa regola di distribuzione"), not an
    unconditional round-robin across every heir category `resolve_heirs`
    happens to return regardless of `rule`. The fix reuses the caller's
    OWN already-computed `cash_allocation` (`distribute_estate`'s return
    value) as the third argument, rather than re-deriving heir eligibility
    inside this function via a `rule: str` parameter and an internal
    `distribute_estate` call.

    RATIONALE, RESTATED (phase-6 audit round 5, T046 -- this docstring
    previously argued the rejected alternative "would double this
    function's query cost under matrilineal specifically", which fix
    NEW-7 (phase-6 audit round 4, T046) made no longer strictly true: post
    NEW-7, a hypothetical internal `distribute_estate` call here could
    ALSO be handed the already-resolved `matrilineal_heirs` this function
    already receives, so it would not necessarily re-pay the sister-count
    queries either). The alternative is still rejected, on the grounds
    that remain accurate: it would recompute the SAME allocation a second
    time via a second, independent code path (a redundant pure-Python
    computation for `primogeniture`/`equal_split`/`shari'a`/`nationalized`
    regardless of query cost), creating two sources of truth for "who is
    cash-eligible under this rule" that could drift from each other if
    `distribute_estate`'s own logic ever changed without both call sites
    being updated in lockstep -- accepting the caller's own already-
    computed `cash_allocation` keeps there being exactly one.

    Under `nationalized`, `distribute_estate` always returns `{}` even
    with living heirs present, so loans now correctly follow cash to the
    banking system instead of escaping nationalization. Under every other
    rule, only the ids `cash_allocation` actually contains receive a loan
    -- never a category (e.g. `extended_family`) no rule ever pays cash to,
    and never a category (e.g. `siblings`, absent under `primogeniture`
    when there are children or a spouse) the rule's own cascade did not
    reach this time.
    """

    @pytest.mark.django_db
    def test_nationalized_routes_loans_to_banking_even_with_a_living_heir(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        heir = _make_agent(sim, zone, "Heir", parent_agent=deceased, birth_tick=1)
        borrower = _make_agent(sim, zone, "Borrower")
        loan = _make_loan(sim, borrower, lender=deceased)

        heirs = {"children": [heir]}
        cash_allocation = distribute_estate(deceased, heirs, "nationalized", 1_000.0)
        assert cash_allocation == {}, (
            "sanity check: nationalized must yield an empty cash allocation"
        )

        transfer_loans_as_lender(deceased, heirs, cash_allocation)

        loan.refresh_from_db()
        assert loan.lender_id is None
        assert loan.lender_type == "banking"

    @pytest.mark.django_db
    def test_primogeniture_routes_loans_only_to_the_single_cash_heir_not_the_whole_family(
        self, sim_with_zone
    ):
        """Primogeniture pays 100% of CASH to a single heir (the eldest
        son, or eldest daughter absent a son) -- loans must follow that
        SAME single heir, never spread to the spouse, other children, or
        siblings the cash rule never touches this time.
        """
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        spouse = _make_agent(sim, zone, "Spouse")
        form_couple(deceased, spouse, formed_at_tick=1)
        eldest_son = _make_agent(
            sim, zone, "EldestSon", parent_agent=deceased, gender=Agent.Gender.MALE, birth_tick=1
        )
        younger_daughter = _make_agent(
            sim,
            zone,
            "YoungerDaughter",
            parent_agent=deceased,
            gender=Agent.Gender.FEMALE,
            birth_tick=5,
        )
        borrower = _make_agent(sim, zone, "Borrower")
        loans = [_make_loan(sim, borrower, lender=deceased) for _ in range(3)]

        heirs = {"spouse": [spouse], "children": [eldest_son, younger_daughter]}
        cash_allocation = distribute_estate(deceased, heirs, "primogeniture", 1_000.0)
        assert cash_allocation == {eldest_son.id: 1_000.0}

        transfer_loans_as_lender(deceased, heirs, cash_allocation)

        for loan in loans:
            loan.refresh_from_db()
        lender_ids = {loan.lender_id for loan in loans}
        assert lender_ids == {eldest_son.id}, (
            f"loans went to {lender_ids}, expected only the eldest son "
            f"{eldest_son.id} -- the same heir primogeniture pays cash to"
        )

    @pytest.mark.django_db
    def test_matrilineal_routes_loans_to_nieces_and_nephews_without_crashing(self, sim_with_zone):
        """Fix NEW-1 (phase-6 audit round 2, T046): `cash_allocation`'s
        ids under `matrilineal` are nieces/nephews, resolved by
        `_resolve_matrilineal_heirs` via a dedicated query per sister --
        `resolve_heirs`'s own category ladder cannot reach a sibling's
        descendants at all (see `_resolve_matrilineal_heirs`'s own
        docstring), so those ids are NEVER inserted into `heirs` itself.
        Before this fix, `agents_by_id[heir_id]` assumed every
        `cash_allocation` id was always drawn from `heirs` -- true for
        `primogeniture`/`equal_split`/`shari'a`/`nationalized`, false for
        `matrilineal` -- raising `KeyError` and, inside
        `process_inheritance_batch`'s `transaction.atomic()` block, rolling
        back the ENTIRE tick's inheritance batch over one matrilineal
        estate with an active lender-side loan.
        """
        sim, zone = sim_with_zone
        common_parent = _make_agent(sim, zone, "CommonParent")
        deceased = _make_agent(sim, zone, "Deceased", parent_agent=common_parent, birth_tick=10)
        sister = _make_agent(
            sim,
            zone,
            "Sister",
            parent_agent=common_parent,
            birth_tick=5,
            gender=Agent.Gender.FEMALE,
        )
        niece = _make_agent(sim, zone, "Niece", parent_agent=sister, birth_tick=20)
        borrower = _make_agent(sim, zone, "Borrower")
        loan = _make_loan(sim, borrower, lender=deceased)

        heirs = resolve_heirs(deceased, _heir_template())
        assert heirs["children"] == []
        assert niece.id not in {agent.id for pool in heirs.values() for agent in pool}, (
            "sanity check: the niece must NOT be reachable from heirs itself"
        )

        cash_allocation = distribute_estate(deceased, heirs, "matrilineal", 1_000.0)
        assert cash_allocation == {niece.id: 1_000.0}

        transfer_loans_as_lender(deceased, heirs, cash_allocation)

        loan.refresh_from_db()
        assert loan.lender_id == niece.id
        assert loan.lender_type == "agent"


class TestTransferLoansAsLenderNoLivingHeir:
    """No living heir at all: the loan transfers to the banking system
    (lender=None, lender_type="banking") and KEEPS being serviced -- the
    conserving resolution of the spec's self-contradiction (see
    transfer_loans_as_lender's own docstring for the full account).
    """

    @pytest.mark.django_db
    def test_no_heirs_transfers_to_banking_system_and_stays_active(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        borrower = _make_agent(sim, zone, "Borrower")
        loan = _make_loan(sim, borrower, lender=deceased)

        transfer_loans_as_lender(deceased, {"spouse": [], "children": [], "siblings": []}, {})

        loan.refresh_from_db()
        assert loan.lender_id is None
        assert loan.lender_type == "banking"
        assert loan.status == "active"


class TestTransferLoansAsLenderUnresolvableIdWarnsAndDegradesToBanking:
    """Fix NEW-7 (phase-6 audit round 4, T046) -- TEST REMEDIATION (phase-6
    audit round 5, T046): the `unresolved_ids` branch (a `cash_allocation`
    id that stays unresolvable even after the matrilineal fallback) had no
    test -- the round-4 auditor found it was the ONE mutation that
    survived a full pass: deleting the whole warning block left every one
    of 371 tests green.

    NOT REACHABLE THROUGH ANY OF THE FIVE DOCUMENTED RULES TODAY: every
    id `distribute_estate` can ever put in a real `cash_allocation` is
    drawn from `heirs` itself (four rules) or from `_resolve_matrilineal_
    heirs(heirs)` (the fifth) -- this branch is a DEFENSIVE guard against
    a caller-contract violation, not a path the real birth/death pipeline
    can reach. This test constructs `cash_allocation` directly, naming an
    id reachable from NEITHER `heirs` NOR any sister, specifically to
    exercise that defensive path -- it does not claim this scenario
    arises from any of the five documented succession rules.
    """

    @pytest.mark.django_db
    def test_unresolvable_id_logs_a_warning_and_degrades_to_banking_transfer(
        self, sim_with_zone, caplog
    ):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        borrower = _make_agent(sim, zone, "Borrower")
        loan = _make_loan(sim, borrower, lender=deceased)

        # A real Agent, but deliberately never placed in `heirs` and with
        # no sister for _resolve_matrilineal_heirs to find either -- an id
        # `distribute_estate` could never actually produce, constructed
        # here only to reach the defensive branch directly.
        unreachable_agent = _make_agent(sim, zone, "UnreachableAgent")
        heirs = {"children": [], "siblings": []}
        cash_allocation = {unreachable_agent.id: 500.0}

        with caplog.at_level(logging.WARNING, logger="epocha.apps.demography.inheritance"):
            transfer_loans_as_lender(deceased, heirs, cash_allocation)

        assert "could not be resolved" in caplog.text, (
            f"expected a WARNING about the unresolvable id; captured log text: {caplog.text!r}"
        )
        assert str(unreachable_agent.id) in caplog.text, (
            f"expected the unresolvable id {unreachable_agent.id} named in the warning; "
            f"captured log text: {caplog.text!r}"
        )

        loan.refresh_from_db()
        assert loan.lender_id is None
        assert loan.lender_type == "banking"
        assert loan.status == "active"


class TestTransferLoansAsLenderScopeGuards:
    """Non-active loans and borrower-side loans are never touched."""

    @pytest.mark.django_db
    @pytest.mark.parametrize("status", ["repaid", "defaulted"])
    def test_non_active_loan_is_untouched(self, sim_with_zone, status):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        heir = _make_agent(sim, zone, "Heir", parent_agent=deceased, birth_tick=1)
        borrower = _make_agent(sim, zone, "Borrower")
        loan = _make_loan(sim, borrower, lender=deceased, status=status)

        transfer_loans_as_lender(deceased, {"children": [heir]}, {heir.id: 0.0})

        loan.refresh_from_db()
        assert loan.lender_id == deceased.id
        assert loan.lender_type == "agent"
        assert loan.status == status

    @pytest.mark.django_db
    def test_loan_where_deceased_is_borrower_is_untouched(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        heir = _make_agent(sim, zone, "Heir", parent_agent=deceased, birth_tick=1)
        other_lender = _make_agent(sim, zone, "OtherLender")
        loan = _make_loan(sim, deceased, lender=other_lender)

        transfer_loans_as_lender(deceased, {"children": [heir]}, {heir.id: 0.0})

        loan.refresh_from_db()
        assert loan.lender_id == other_lender.id
        assert loan.borrower_id == deceased.id
        assert loan.status == "active"

    @pytest.mark.django_db
    def test_banking_lender_type_loan_with_null_lender_is_untouched(self, sim_with_zone):
        """A loan already carried by the banking system (lender=None) has
        no bearing on the deceased's own lender-side loan book and must
        never be touched, even though its lender FK happens to be null
        like a freshly-transferred heirless loan would be.
        """
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        heir = _make_agent(sim, zone, "Heir", parent_agent=deceased, birth_tick=1)
        borrower = _make_agent(sim, zone, "Borrower")
        loan = _make_loan(sim, borrower, lender=None, lender_type="banking")

        transfer_loans_as_lender(deceased, {"children": [heir]}, {heir.id: 0.0})

        loan.refresh_from_db()
        assert loan.lender_id is None
        assert loan.lender_type == "banking"


class TestTransferLoansAsLenderQueryBudget:
    """Efficiency requirement: Plan 4 will call this once per death, every
    tick -- the write path must not become N+1 as the deceased's loan book
    grows (see this module's established query-budget convention, e.g.
    TestResolveHeirsQueryBudget above).
    """

    @pytest.mark.django_db
    def test_write_count_is_bounded_independent_of_loan_count(
        self, sim_with_zone, django_assert_num_queries
    ):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        spouse = _make_agent(sim, zone, "Spouse")
        form_couple(deceased, spouse, formed_at_tick=1)
        child = _make_agent(sim, zone, "Child", parent_agent=deceased, birth_tick=1)
        borrower = _make_agent(sim, zone, "Borrower")
        for _ in range(5):
            _make_loan(sim, borrower, lender=deceased)

        heirs = {"spouse": [spouse], "children": [child]}
        cash_allocation = {spouse.id: 0.0, child.id: 0.0}

        # 1 query to fetch the deceased's active lender-side loans, plus 1
        # bulk_update UPDATE for the reassignment -- 2 queries regardless
        # of loan count, never N+1 individual .save() calls. Resolving
        # eligible_heirs from cash_allocation's ids is pure Python (no
        # query), so fix I-6 does not change this budget.
        with django_assert_num_queries(2):
            transfer_loans_as_lender(deceased, heirs, cash_allocation)

    @pytest.mark.django_db
    def test_matrilineal_costs_two_queries_when_the_caller_threads_the_resolved_heirs(
        self, sim_with_zone, django_assert_num_queries
    ):
        """Fix NEW-7 (phase-6 audit round 4, T046): NEW-1's fix (round 2)
        made this function's own query cost under `matrilineal` unbounded
        in sibling count -- a lazy `_resolve_matrilineal_heirs(heirs)`
        fallback (one query per sister) fired every time, since a niece/
        nephew id is never in `heirs` itself. The auditor measured 6
        queries for four sisters, one niece, one loan (1 loan SELECT + 4
        sister queries + 1 `bulk_update`), directly contradicting this
        function's own documented "up to 2 queries" budget.

        This test proves the budget is TRUE AGAIN for the path that
        matters -- `process_inheritance_batch` now resolves the niece/
        nephew list ONCE (paying exactly the sister-count queries
        `distribute_estate` already needed regardless) and THREADS it
        into both `distribute_estate` and this function via the new
        `matrilineal_heirs` keyword, the same pattern the I-6 fix already
        established for `cash_allocation` one paragraph above this one.
        FOUR sisters are used deliberately -- if the query cost still
        scaled with sibling count, this test would need 4 extra queries;
        threading keeps it at exactly 2, proving no re-resolution happens
        inside this function when the caller has already done it.
        """
        sim, zone = sim_with_zone
        common_parent = _make_agent(sim, zone, "CommonParent")
        deceased = _make_agent(sim, zone, "Deceased", parent_agent=common_parent, birth_tick=10)
        sisters = [
            _make_agent(
                sim,
                zone,
                f"Sister{i}",
                parent_agent=common_parent,
                birth_tick=5 + i,
                gender=Agent.Gender.FEMALE,
            )
            for i in range(4)
        ]
        niece = _make_agent(sim, zone, "Niece", parent_agent=sisters[0], birth_tick=20)
        borrower = _make_agent(sim, zone, "Borrower")
        _make_loan(sim, borrower, lender=deceased)

        heirs = resolve_heirs(deceased, _heir_template())
        cash_allocation = {niece.id: 1_000.0}

        # 1 query to fetch active lender-side loans, plus 1 bulk_update --
        # 2 queries regardless of sister count, when the caller threads
        # the already-resolved niece/nephew list (`matrilineal_heirs`)
        # instead of relying on the lazy `_resolve_matrilineal_heirs(heirs)`
        # fallback this function still uses for callers that don't thread it.
        with django_assert_num_queries(2):
            transfer_loans_as_lender(deceased, heirs, cash_allocation, matrilineal_heirs=[niece])


# ---------------------------------------------------------------------------
# assign_orphan_caretaker (Plan 3, T024/T025, user story 3 -- orphan
# caretaker assignment, fix MISS-1)
# ---------------------------------------------------------------------------
#
# Design spec Sezione 5, "Gestione orfani (fix MISS-1)": "Quando entrambi i
# genitori biologici di un minorenne (age < adulthood_age) sono morti, il
# minore viene assegnato un caretaker_agent secondo la priorità seguente:
# parente vivente più vicino nella stessa zona (fratello, nonno, zio/zia),
# poi qualsiasi parente vivente ovunque, poi None (pupillo dello stato). Un
# orfano con caretaker_agent = None viene flaggato e
# Government.government_treasury copre la sua sussistenza (modellando il
# wardship statale). L'orfano riceve comunque la sua eredità direttamente;
# il caretaker amministra ma non possiede gli asset."
#
# The treasury-subsistence flow itself is Plan 4's per-tick orchestrator
# job and is NOT asserted here -- only the state-ward flag this function is
# responsible for (a "state_ward" entry appended to Agent.conditions) is.
#
# `assign_orphan_caretaker` does not exist yet (implemented in T025); the
# import above therefore fails at collection time with "cannot import name
# 'assign_orphan_caretaker'", this file's established RED-first signal for
# a not-yet-implemented function (see e.g. T016/T018/T020/T023's own RED
# commits).
#
# The caller (the future Plan 4 death orchestrator) guarantees `minor` is
# an orphaned minor before calling this function -- no test here exercises
# adulthood, aliveness, or "still has a living parent" guards on `minor`
# itself; those are explicitly out of scope for T024 per the task
# description.


def _make_other_zone(world, name="OtherZone"):
    """A second `Zone` on the same `World`, for the cross-zone caretaker-
    priority tests below (design spec Sezione 5, Gestione orfani, fix
    MISS-1: stage 1 of the ladder is scoped to "la stessa zona" of the
    minor, so distinguishing same-zone from other-zone candidates is
    load-bearing here). Mirrors the `Zone` creation kwargs used by the
    `sim_with_zone` fixture above, with a disjoint bounding box so the two
    zones are geometrically distinct.
    """
    return Zone.objects.create(
        world=world,
        name=name,
        zone_type="residential",
        boundary=Polygon.from_bbox((200, 200, 300, 300)),
        center=Point(250, 250),
    )


class TestAssignOrphanCaretakerSameZoneKinshipPriority:
    """Stage 1 of the ladder (same zone as the minor) walks the kinship
    rungs in order: sibling > grandparent > aunt/uncle.
    """

    @pytest.mark.django_db
    def test_same_zone_sibling_beats_same_zone_grandparent_and_aunt_uncle(self, sim_with_zone):
        sim, zone = sim_with_zone
        grandparent = _make_agent(sim, zone, "Grandparent", birth_tick=-100)
        mother = _make_agent(
            sim, zone, "Mother", parent_agent=grandparent, is_alive=False, birth_tick=-60
        )
        _make_agent(sim, zone, "Aunt", parent_agent=grandparent, birth_tick=-58)
        sibling = _make_agent(sim, zone, "Sibling", parent_agent=mother, birth_tick=5)
        minor = _make_agent(sim, zone, "Minor", parent_agent=mother, age=10, birth_tick=10)

        caretaker = assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert caretaker == sibling

    @pytest.mark.django_db
    def test_same_zone_grandparent_beats_same_zone_aunt_uncle_when_no_sibling(self, sim_with_zone):
        sim, zone = sim_with_zone
        grandparent = _make_agent(sim, zone, "Grandparent", birth_tick=-100)
        mother = _make_agent(
            sim, zone, "Mother", parent_agent=grandparent, is_alive=False, birth_tick=-60
        )
        _make_agent(sim, zone, "Aunt", parent_agent=grandparent, birth_tick=-58)
        minor = _make_agent(sim, zone, "Minor", parent_agent=mother, age=10, birth_tick=10)

        caretaker = assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert caretaker == grandparent

    @pytest.mark.django_db
    def test_same_zone_aunt_uncle_is_picked_when_no_sibling_or_grandparent_are_same_zone(
        self, sim_with_zone
    ):
        """The grandparent itself lives in a different zone (so it is not a
        stage-1 candidate), but its child -- the minor's aunt -- lives in
        the minor's own zone and is found through the grandparent lineage.
        """
        sim, zone = sim_with_zone
        other_zone = _make_other_zone(zone.world)
        grandparent = _make_agent(sim, other_zone, "Grandparent", birth_tick=-100)
        mother = _make_agent(
            sim, zone, "Mother", parent_agent=grandparent, is_alive=False, birth_tick=-60
        )
        aunt = _make_agent(sim, zone, "Aunt", parent_agent=grandparent, birth_tick=-58)
        minor = _make_agent(sim, zone, "Minor", parent_agent=mother, age=10, birth_tick=10)

        caretaker = assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert caretaker == aunt


class TestAssignOrphanCaretakerStageOneBeatsStageTwo:
    """A same-zone relative at a LOWER-priority kinship rung still outranks
    a HIGHER-priority kinship rung relative in a different zone -- stage 1
    (same zone) is exhausted in full before stage 2 (any zone) is even
    considered.
    """

    @pytest.mark.django_db
    def test_same_zone_grandparent_beats_other_zone_sibling(self, sim_with_zone):
        sim, zone = sim_with_zone
        other_zone = _make_other_zone(zone.world)
        grandparent = _make_agent(sim, zone, "Grandparent", birth_tick=-100)
        mother = _make_agent(
            sim, zone, "Mother", parent_agent=grandparent, is_alive=False, birth_tick=-60
        )
        _make_agent(sim, other_zone, "Sibling", parent_agent=mother, birth_tick=5)
        minor = _make_agent(sim, zone, "Minor", parent_agent=mother, age=10, birth_tick=10)

        caretaker = assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert caretaker == grandparent

    @pytest.mark.django_db
    def test_same_zone_aunt_uncle_beats_other_zone_sibling(self, sim_with_zone):
        """The grandparent itself lives in a different zone (so it is not a
        stage-1 candidate and cannot out-rank the aunt on the grandparent
        rung) -- only the aunt qualifies for stage 1, and she must still
        beat the other-zone sibling.
        """
        sim, zone = sim_with_zone
        other_zone = _make_other_zone(zone.world)
        grandparent = _make_agent(sim, other_zone, "Grandparent", birth_tick=-100)
        mother = _make_agent(
            sim, zone, "Mother", parent_agent=grandparent, is_alive=False, birth_tick=-60
        )
        aunt = _make_agent(sim, zone, "Aunt", parent_agent=grandparent, birth_tick=-58)
        _make_agent(sim, other_zone, "Sibling", parent_agent=mother, birth_tick=5)
        minor = _make_agent(sim, zone, "Minor", parent_agent=mother, age=10, birth_tick=10)

        caretaker = assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert caretaker == aunt


class TestAssignOrphanCaretakerStageTwoAnyZonePriority:
    """When stage 1 (same zone) finds nobody, stage 2 walks the same
    kinship ladder across every zone.
    """

    @pytest.mark.django_db
    def test_other_zone_sibling_beats_other_zone_grandparent(self, sim_with_zone):
        sim, zone = sim_with_zone
        other_zone = _make_other_zone(zone.world)
        grandparent = _make_agent(sim, other_zone, "Grandparent", birth_tick=-100)
        mother = _make_agent(
            sim, other_zone, "Mother", parent_agent=grandparent, is_alive=False, birth_tick=-60
        )
        sibling = _make_agent(sim, other_zone, "Sibling", parent_agent=mother, birth_tick=5)
        minor = _make_agent(sim, zone, "Minor", parent_agent=mother, age=10, birth_tick=10)

        caretaker = assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert caretaker == sibling

    @pytest.mark.django_db
    def test_single_other_zone_relative_is_assigned_when_no_same_zone_candidate(
        self, sim_with_zone
    ):
        sim, zone = sim_with_zone
        other_zone = _make_other_zone(zone.world)
        grandparent = _make_agent(sim, other_zone, "Grandparent", birth_tick=-100)
        mother = _make_agent(
            sim, other_zone, "Mother", parent_agent=grandparent, is_alive=False, birth_tick=-60
        )
        minor = _make_agent(sim, zone, "Minor", parent_agent=mother, age=10, birth_tick=10)

        caretaker = assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert caretaker == grandparent


class TestAssignOrphanCaretakerNoLivingRelativeStateWard:
    """No living relative anywhere (neither zone): returns None,
    `caretaker_agent` stays None, and "state_ward" is appended to
    `Agent.conditions` -- the flag mechanism the design spec calls
    "flaggato" ahead of the treasury covering subsistence (Plan 4's
    per-tick job, not asserted here).
    """

    @pytest.mark.django_db
    def test_no_living_relative_returns_none_and_flags_state_ward(self, sim_with_zone):
        sim, zone = sim_with_zone
        mother = _make_agent(sim, zone, "Mother", is_alive=False, birth_tick=-60)
        father = _make_agent(sim, zone, "Father", is_alive=False, birth_tick=-60)
        minor = _make_agent(
            sim,
            zone,
            "Minor",
            parent_agent=mother,
            other_parent_agent=father,
            age=10,
            birth_tick=10,
        )

        caretaker = assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert caretaker is None
        assert minor.caretaker_agent is None
        assert "state_ward" in minor.conditions

    @pytest.mark.django_db
    def test_state_ward_flag_is_appended_not_overwriting_existing_conditions(self, sim_with_zone):
        sim, zone = sim_with_zone
        mother = _make_agent(sim, zone, "Mother", is_alive=False, birth_tick=-60)
        minor = _make_agent(
            sim,
            zone,
            "Minor",
            parent_agent=mother,
            age=10,
            birth_tick=10,
            conditions=["chronic_illness"],
        )

        assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert minor.conditions == ["chronic_illness", "state_ward"]


class TestAssignOrphanCaretakerDeterministicTiebreak:
    """Within a kinship rung, ties break by `birth_tick` ascending (oldest
    first), then `id` ascending -- the same convention as
    `_resolve_sibling_heirs` above.
    """

    @pytest.mark.django_db
    def test_lower_birth_tick_sibling_wins_regardless_of_creation_order(self, sim_with_zone):
        sim, zone = sim_with_zone
        mother = _make_agent(sim, zone, "Mother", is_alive=False, birth_tick=-60)
        # Created in reverse birth_tick order: the younger sibling gets the
        # LOWER id, so a naive "first created" or "lowest id" selection
        # would wrongly pick it instead of the older (lower birth_tick)
        # sibling.
        younger_sibling = _make_agent(
            sim, zone, "YoungerSibling", parent_agent=mother, birth_tick=20
        )
        older_sibling = _make_agent(sim, zone, "OlderSibling", parent_agent=mother, birth_tick=5)
        minor = _make_agent(sim, zone, "Minor", parent_agent=mother, age=10, birth_tick=10)

        caretaker = assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert caretaker == older_sibling
        # Self-check: id order is the opposite of birth_tick order, so this
        # result cannot be explained by an accidental id-only tiebreak.
        assert older_sibling.id > younger_sibling.id

    @pytest.mark.django_db
    def test_equal_birth_tick_lower_id_wins(self, sim_with_zone):
        sim, zone = sim_with_zone
        mother = _make_agent(sim, zone, "Mother", is_alive=False, birth_tick=-60)
        first_sibling = _make_agent(sim, zone, "FirstSibling", parent_agent=mother, birth_tick=5)
        second_sibling = _make_agent(sim, zone, "SecondSibling", parent_agent=mother, birth_tick=5)
        minor = _make_agent(sim, zone, "Minor", parent_agent=mother, age=10, birth_tick=10)

        caretaker = assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert caretaker == first_sibling
        assert first_sibling.id < second_sibling.id  # self-check


class TestAssignOrphanCaretakerDeadRelativesSkipped:
    """Dead relatives (`is_alive=False`) never qualify as a caretaker, at
    any kinship rung and in either stage of the ladder.
    """

    @pytest.mark.django_db
    def test_dead_same_zone_sibling_is_skipped_in_favor_of_same_zone_grandparent(
        self, sim_with_zone
    ):
        sim, zone = sim_with_zone
        grandparent = _make_agent(sim, zone, "Grandparent", birth_tick=-100)
        mother = _make_agent(
            sim, zone, "Mother", parent_agent=grandparent, is_alive=False, birth_tick=-60
        )
        _make_agent(sim, zone, "DeadSibling", parent_agent=mother, birth_tick=5, is_alive=False)
        minor = _make_agent(sim, zone, "Minor", parent_agent=mother, age=10, birth_tick=10)

        caretaker = assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert caretaker == grandparent

    @pytest.mark.django_db
    def test_only_relative_anywhere_is_dead_yields_none_and_flags_state_ward(self, sim_with_zone):
        sim, zone = sim_with_zone
        other_zone = _make_other_zone(zone.world)
        mother = _make_agent(sim, zone, "Mother", is_alive=False, birth_tick=-60)
        _make_agent(
            sim, other_zone, "DeadSibling", parent_agent=mother, birth_tick=5, is_alive=False
        )
        minor = _make_agent(sim, zone, "Minor", parent_agent=mother, age=10, birth_tick=10)

        caretaker = assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert caretaker is None
        assert "state_ward" in minor.conditions


class TestAssignOrphanCaretakerNoPersistence:
    """No-persistence contract (module-wide, settled): the function
    mutates the passed `minor` instance but NEVER calls `.save()` --
    consistent with `distribute_estate`'s own "WITHOUT persisting"
    contract (T021), leaving the write to the caller (the Plan 4
    orchestrator).
    """

    @pytest.mark.django_db
    def test_successful_assignment_is_not_persisted_to_database(self, sim_with_zone):
        sim, zone = sim_with_zone
        mother = _make_agent(sim, zone, "Mother", is_alive=False, birth_tick=-60)
        sibling = _make_agent(sim, zone, "Sibling", parent_agent=mother, birth_tick=5)
        minor = _make_agent(sim, zone, "Minor", parent_agent=mother, age=10, birth_tick=10)

        caretaker = assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert caretaker == sibling
        # The in-memory instance IS mutated by the call...
        assert minor.caretaker_agent_id == sibling.id

        # ...but nothing was ever written to the database.
        persisted = Agent.objects.get(id=minor.id)
        assert persisted.caretaker_agent_id is None


class TestAssignOrphanCaretakerOwnershipFixMiss1:
    """Fix MISS-1 (design spec Sezione 5, Gestione orfani): "L'orfano
    riceve comunque la sua eredità direttamente; il caretaker amministra
    ma non possiede gli asset." The caretaker assignment call must never
    move wealth between the orphan and the caretaker -- the orphan keeps
    direct ownership of whatever it inherited.
    """

    @pytest.mark.django_db
    def test_call_does_not_transfer_wealth_between_orphan_and_caretaker(self, sim_with_zone):
        sim, zone = sim_with_zone
        mother = _make_agent(sim, zone, "Mother", is_alive=False, birth_tick=-60)
        sibling = _make_agent(sim, zone, "Sibling", parent_agent=mother, birth_tick=5, wealth=100.0)
        minor = _make_agent(
            sim, zone, "Minor", parent_agent=mother, age=10, birth_tick=10, wealth=500.0
        )
        minor_wealth_before = minor.wealth
        sibling_wealth_before = sibling.wealth

        caretaker = assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert caretaker == sibling
        assert minor.wealth == minor_wealth_before
        assert sibling.wealth == sibling_wealth_before


class TestAssignOrphanCaretakerKinshipDefinitions:
    """Kinship definitions match this module's existing conventions: the
    sibling match is broadened to either parentage FK (same as
    `_resolve_sibling_heirs` above), and the grandparent lookup walks
    through EITHER of the minor's own two parentage FKs, not just
    `parent_agent`.
    """

    @pytest.mark.django_db
    def test_half_sibling_via_other_parent_agent_counts_as_sibling(self, sim_with_zone):
        sim, zone = sim_with_zone
        father = _make_agent(sim, zone, "Father", is_alive=False, birth_tick=-60)
        half_sibling = _make_agent(
            sim, zone, "HalfSibling", other_parent_agent=father, birth_tick=5
        )
        minor = _make_agent(sim, zone, "Minor", other_parent_agent=father, age=10, birth_tick=10)

        caretaker = assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert caretaker == half_sibling

    @pytest.mark.django_db
    def test_grandparent_via_minors_other_parent_agent_is_found(self, sim_with_zone):
        """The grandparent lookup must walk BOTH of the minor's own
        parentage FKs -- here the grandparent is reachable only through
        the minor's `other_parent_agent` (father) side, not `parent_agent`.
        """
        sim, zone = sim_with_zone
        grandparent = _make_agent(sim, zone, "Grandparent", birth_tick=-100)
        father = _make_agent(
            sim, zone, "Father", parent_agent=grandparent, is_alive=False, birth_tick=-60
        )
        minor = _make_agent(sim, zone, "Minor", other_parent_agent=father, age=10, birth_tick=10)

        caretaker = assign_orphan_caretaker(minor, tick=sim.current_tick)

        assert caretaker == grandparent


# ---------------------------------------------------------------------------
# generate_mourning_memories (Plan 3, T026/T027, user story 3 -- death
# leaves a mark). Design spec Sezione 5, "Cascata di memoria del lutto":
# the surviving spouse, surviving children, and every living agent tied to
# the deceased by a Relationship with strength > 0.6 (either direction)
# each receive one first-hand Memory of the death, deduplicated across
# categories. This function only creates the direct memories -- carrying
# them onward to socially-distant agents is the existing per-tick
# `propagate_information` system's job, called later, never from here.
#
# TRAP 2 (verbatim, load-bearing): the strong-tie filter is
# `Relationship.strength`, NOT `Agent.strength`. `Agent.strength` is an
# inherited PHYSICAL trait (h^2 = 0.55, Falconer & Mackay 1996 kernel --
# see `TestInheritTraitTwoParents` above) measuring how strong an agent's
# body is; `Relationship.strength` measures how strong a SOCIAL bond is.
# Filtering the grief cascade on the former would deliver memories to
# muscular strangers instead of close friends -- a category error the
# TestGenerateMourningMemoriesTrap2 class below is built to catch.
#
# `generate_mourning_memories` does not exist yet (implemented in T027);
# the import above therefore fails at collection time with "cannot import
# name 'generate_mourning_memories'", this file's established RED-first
# signal (see e.g. T016/T018/T020/T023/T024's own RED commits).


class TestGenerateMourningMemoriesSpouse:
    """The surviving partner of the deceased's active Couple receives one
    memory (design spec Sezione 5, heir-adjacent recipient list item 1).
    """

    @pytest.mark.django_db
    def test_surviving_spouse_receives_memory_with_the_module_row_shape(self, sim_with_zone):
        """Canonical row-shape check (asserted once here, not repeated per
        recipient category below): `agent`, `emotional_weight=0.9`,
        `source_type=DIRECT`, `reliability=1.0`, `tick_created=tick`,
        `origin_agent=deceased`, and a `content` sentence naming the
        deceased (wording itself is T027's freedom, not pinned here).
        """
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        partner = _make_agent(sim, zone, "Partner")
        form_couple(deceased, partner, formed_at_tick=1)

        generate_mourning_memories(deceased, tick=sim.current_tick)

        memory = Memory.objects.get(agent=partner, origin_agent=deceased)
        assert memory.emotional_weight == 0.9
        assert memory.source_type == Memory.SourceType.DIRECT
        assert memory.reliability == 1.0
        assert memory.tick_created == sim.current_tick
        assert deceased.name in memory.content

    @pytest.mark.django_db
    def test_dead_partner_in_active_couple_receives_nothing(self, sim_with_zone):
        """`active_couple_for` does not itself check the partner's own
        aliveness (see `_resolve_spouse_heirs`'s own documented edge case)
        -- this function must apply the "only if alive" qualifier itself.
        """
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        partner = _make_agent(sim, zone, "Partner", is_alive=False)
        form_couple(deceased, partner, formed_at_tick=1)

        generate_mourning_memories(deceased, tick=sim.current_tick)

        assert not Memory.objects.filter(agent=partner, origin_agent=deceased).exists()

    @pytest.mark.django_db
    def test_no_active_couple_yields_no_spousal_memory(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")

        generate_mourning_memories(deceased, tick=sim.current_tick)

        assert not Memory.objects.filter(origin_agent=deceased).exists()


class TestGenerateMourningMemoriesChildren:
    """Living children of the deceased (either parentage FK) each receive
    one memory (design spec Sezione 5, recipient list item 2).
    """

    @pytest.mark.django_db
    def test_surviving_children_via_both_parent_fks_receive_memory(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        child_via_mother_fk = _make_agent(
            sim, zone, "ChildViaMotherFk", parent_agent=deceased, birth_tick=5
        )
        child_via_father_fk = _make_agent(
            sim, zone, "ChildViaFatherFk", other_parent_agent=deceased, birth_tick=6
        )

        generate_mourning_memories(deceased, tick=sim.current_tick)

        assert Memory.objects.filter(agent=child_via_mother_fk, origin_agent=deceased).exists()
        assert Memory.objects.filter(agent=child_via_father_fk, origin_agent=deceased).exists()

    @pytest.mark.django_db
    def test_dead_child_receives_nothing(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        dead_child = _make_agent(
            sim, zone, "DeadChild", parent_agent=deceased, birth_tick=5, is_alive=False
        )

        generate_mourning_memories(deceased, tick=sim.current_tick)

        assert not Memory.objects.filter(agent=dead_child, origin_agent=deceased).exists()


class TestGenerateMourningMemoriesStrongTies:
    """Living agents linked to the deceased by a `Relationship` with
    `strength > 0.6`, in EITHER direction, each receive one memory (design
    spec Sezione 5, recipient list item 3).
    """

    @pytest.mark.django_db
    def test_strong_tie_with_deceased_as_agent_from_receives_memory(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        friend = _make_agent(sim, zone, "Friend")
        Relationship.objects.create(
            agent_from=deceased,
            agent_to=friend,
            relation_type=Relationship.RelationType.FRIENDSHIP,
            strength=0.8,
            since_tick=0,
        )

        generate_mourning_memories(deceased, tick=sim.current_tick)

        assert Memory.objects.filter(agent=friend, origin_agent=deceased).exists()

    @pytest.mark.django_db
    def test_strong_tie_with_deceased_as_agent_to_receives_memory(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        friend = _make_agent(sim, zone, "Friend")
        Relationship.objects.create(
            agent_from=friend,
            agent_to=deceased,
            relation_type=Relationship.RelationType.FRIENDSHIP,
            strength=0.8,
            since_tick=0,
        )

        generate_mourning_memories(deceased, tick=sim.current_tick)

        assert Memory.objects.filter(agent=friend, origin_agent=deceased).exists()

    @pytest.mark.django_db
    def test_boundary_strength_exactly_zero_point_six_receives_nothing(self, sim_with_zone):
        """Strict `>` boundary: `strength = 0.6` exactly does NOT qualify."""
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        acquaintance = _make_agent(sim, zone, "Acquaintance")
        Relationship.objects.create(
            agent_from=deceased,
            agent_to=acquaintance,
            relation_type=Relationship.RelationType.FRIENDSHIP,
            strength=0.6,
            since_tick=0,
        )

        generate_mourning_memories(deceased, tick=sim.current_tick)

        assert not Memory.objects.filter(agent=acquaintance, origin_agent=deceased).exists()

    @pytest.mark.django_db
    def test_dead_strong_tie_receives_nothing(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        dead_friend = _make_agent(sim, zone, "DeadFriend", is_alive=False)
        Relationship.objects.create(
            agent_from=deceased,
            agent_to=dead_friend,
            relation_type=Relationship.RelationType.FRIENDSHIP,
            strength=0.9,
            since_tick=0,
        )

        generate_mourning_memories(deceased, tick=sim.current_tick)

        assert not Memory.objects.filter(agent=dead_friend, origin_agent=deceased).exists()


class TestGenerateMourningMemoriesTrap2:
    """Trap 2 (mandatory, verbatim): the strong-tie filter MUST be
    `Relationship.strength`, never `Agent.strength`. Each test here is
    constructed so that filtering on the wrong field flips the assertion.
    """

    @pytest.mark.django_db
    def test_muscular_agent_with_no_relationship_receives_nothing(self, sim_with_zone):
        """High `Agent.strength` (physical trait) alone, with no
        `Relationship` row at all to the deceased, must not qualify.
        """
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        muscular_stranger = _make_agent(sim, zone, "MuscularStranger", strength=0.95)

        generate_mourning_memories(deceased, tick=sim.current_tick)

        assert not Memory.objects.filter(agent=muscular_stranger, origin_agent=deceased).exists()

    @pytest.mark.django_db
    def test_muscular_agent_with_weak_relationship_receives_nothing(self, sim_with_zone):
        """High `Agent.strength`, but the `Relationship.strength` to the
        deceased is at/under the 0.6 threshold -- still no memory.
        """
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        muscular_acquaintance = _make_agent(sim, zone, "MuscularAcquaintance", strength=0.95)
        Relationship.objects.create(
            agent_from=deceased,
            agent_to=muscular_acquaintance,
            relation_type=Relationship.RelationType.PROFESSIONAL,
            strength=0.5,
            since_tick=0,
        )

        generate_mourning_memories(deceased, tick=sim.current_tick)

        assert not Memory.objects.filter(
            agent=muscular_acquaintance, origin_agent=deceased
        ).exists()

    @pytest.mark.django_db
    def test_frail_agent_with_strong_relationship_receives_memory(self, sim_with_zone):
        """The discriminating case: LOW `Agent.strength` (0.1, frail) but
        a `Relationship.strength` of 0.8 to the deceased -- this is the
        close friend the cascade must reach. An implementation that
        mistakenly filters on `Agent.strength` instead of
        `Relationship.strength` fails this test.
        """
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        frail_close_friend = _make_agent(sim, zone, "FrailCloseFriend", strength=0.1)
        Relationship.objects.create(
            agent_from=deceased,
            agent_to=frail_close_friend,
            relation_type=Relationship.RelationType.FRIENDSHIP,
            strength=0.8,
            since_tick=0,
        )

        generate_mourning_memories(deceased, tick=sim.current_tick)

        assert Memory.objects.filter(agent=frail_close_friend, origin_agent=deceased).exists()


class TestGenerateMourningMemoriesDedup:
    """An agent qualifying under more than one recipient category gets
    exactly ONE memory, never one per category (design spec Sezione 5,
    "un ricordo per destinatario").
    """

    @pytest.mark.django_db
    def test_child_who_is_also_a_strong_tie_receives_exactly_one_memory(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        child = _make_agent(sim, zone, "Child", parent_agent=deceased, birth_tick=5)
        Relationship.objects.create(
            agent_from=deceased,
            agent_to=child,
            relation_type=Relationship.RelationType.FAMILY,
            strength=0.9,
            since_tick=0,
        )

        generate_mourning_memories(deceased, tick=sim.current_tick)

        assert Memory.objects.filter(agent=child, origin_agent=deceased).count() == 1


class TestGenerateMourningMemoriesNoPropagation:
    """This function only creates the direct, first-hand memories for its
    three recipient categories -- it does not itself carry the death to
    socially-distant agents (that is the existing per-tick
    `propagate_information` system's job, run later, not from here).
    """

    @pytest.mark.django_db
    def test_socially_distant_zone_mate_receives_nothing(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        zone_mate = _make_agent(sim, zone, "ZoneMateNoTie")

        generate_mourning_memories(deceased, tick=sim.current_tick)

        assert not Memory.objects.filter(agent=zone_mate, origin_agent=deceased).exists()


class TestGenerateMourningMemoriesNoSaveOnDeceased:
    """The function creates NEW `Memory` rows (persistence of new rows is
    this function's job -- precedent: `transfer_loans_as_lender` persists
    `Loan` updates), but it must never call `.save()` on the passed
    `deceased` instance itself.
    """

    @pytest.mark.django_db
    def test_never_saves_the_deceased_instance(self, sim_with_zone):
        sim, zone = sim_with_zone
        deceased = _make_agent(sim, zone, "Deceased")
        partner = _make_agent(sim, zone, "Partner")
        form_couple(deceased, partner, formed_at_tick=1)

        # Mutated only in memory -- if the function ever called
        # deceased.save(), this would leak into the database.
        deceased.name = "MutatedInMemoryOnly"

        generate_mourning_memories(deceased, tick=sim.current_tick)

        persisted = Agent.objects.get(id=deceased.id)
        assert persisted.name == "Deceased"


# ---------------------------------------------------------------------------
# process_inheritance_batch (Plan 3, T028/T029, user story 3 -- the
# death-path orchestrator). Design spec Sezione 5: per deceased, calls
# `dissolve_on_death` (D1), settles the estate through
# `resolve_heirs` -> `apply_estate_tax` -> `distribute_estate`, credits
# heirs' wealth and zeroes the deceased's, transfers active lender-side
# loans, assigns caretakers to now-orphaned minors, generates mourning
# memories, and emits one `DemographyEvent` (`INHERITANCE_TRANSFER`) per
# actual heir transfer.
#
# PRECONDITION, load-bearing for every test below: every agent in
# `deceased_agents` is passed in ALREADY `is_alive=False` (and, where
# relevant, `death_tick` already set) -- the caller (Plan 4's mortality
# step) sets this BEFORE calling `process_inheritance_batch`, never this
# function itself. This is the resolution of the apparent MISS-5 chaining
# puzzle: since `resolve_heirs`'s every category already filters
# `is_alive=True`, a same-tick-dead intermediate is mechanically excluded
# from being anyone's heir -- no suppression flag or special-cased
# recursion is needed, and none should be invented.
#
# FAMILY-TOPOLOGY NOTE (read before extending these tests): the coordinator
# brief's illustrative "grandfather / father / grandson" chain describes
# the OBSERVABLE arithmetic (two independent, separately-taxed transfers
# landing on one living heir) rather than a literal three-generation
# lineage `resolve_heirs` could actually traverse -- `resolve_heirs`'s own
# ladder (spouse, children, siblings, extended_family) never walks down
# to a deceased's grandchildren; "extended_family" reaches the deceased's
# OWN grandparents' descendants (aunts/uncles/cousins), never descendants
# of the deceased's own children. The tests below therefore build the
# "living heir inherits from two same-tick decedents" case as a shared
# living CHILD of two decedents (one on each parentage FK), and the
# "father already dead, estate falls to the next living category" case as
# ANOTHER living child of the same decedent (the same-generation fallback
# `resolve_heirs`'s own "children" category actually provides), not as a
# literal grandchild. Flagged explicitly rather than silently invented --
# see the T028 report's Doubts section for the full reasoning.
#
# `process_inheritance_batch` does not exist yet (implemented in T029);
# the import above therefore fails at collection time with "cannot import
# name 'process_inheritance_batch'", this file's established RED-first
# signal (see e.g. T016/T018/T020/T023/T024/T026's own RED commits).


def _set_demography_template(sim, template_name: str) -> None:
    """Point `sim.config["demography_template"]` at `template_name`.

    Mirrors `apply_inheritance_at_birth`'s own
    `simulation.config.get("demography_template", ...)` lookup -- the
    established convention this module uses to resolve which era template
    a Simulation-scoped call reads. Sets it both in memory (what a
    function reading `simulation.config` directly off the passed instance
    sees immediately, no extra query) and persisted (defensive, in case a
    future implementation re-fetches `simulation` from the database).
    """
    sim.config = {"demography_template": template_name}
    sim.save(update_fields=["config"])


class TestProcessInheritanceBatchNoIntraTickChaining:
    """Fix MISS-5, same-tick case (design spec Sezione 5): a deceased's own
    child who ALSO died in this same batch is never a bequest conduit --
    `resolve_heirs`'s `is_alive=True` filter excludes them exactly like it
    would exclude anyone else already dead. PRECONDITION: both agents
    below are constructed already `is_alive=False`, as `deceased_agents`
    always arrives.
    """

    @pytest.mark.django_db
    def test_dead_child_in_batch_receives_nothing_full_estate_goes_to_treasury(
        self, sim_with_government
    ):
        sim, zone, government = sim_with_government
        _set_demography_template(sim, "industrial")
        template = load_template("industrial")
        rate = template["economic_inheritance"]["estate_tax_rate"]

        grandfather = _make_agent(
            sim, zone, "Grandfather", is_alive=False, wealth=1000.0, age=90, birth_tick=-400
        )
        father = _make_agent(
            sim,
            zone,
            "Father",
            parent_agent=grandfather,
            is_alive=False,
            wealth=0.0,
            age=60,
            birth_tick=-300,
        )

        process_inheritance_batch(sim, tick=50, deceased_agents=[grandfather, father])

        father.refresh_from_db()
        grandfather.refresh_from_db()
        assert father.wealth == pytest.approx(0.0, abs=_CONSERVATION_TOLERANCE)
        assert grandfather.wealth == pytest.approx(0.0, abs=_CONSERVATION_TOLERANCE)

        assert not DemographyEvent.objects.filter(
            simulation=sim,
            event_type=DemographyEvent.EventType.INHERITANCE_TRANSFER,
            primary_agent=grandfather,
            secondary_agent=father,
        ).exists()

        # No living heir at all (father excluded, no siblings, no extended
        # family) -- distribute_estate's own documented "empty allocation
        # -> route the entire inheritable remainder to the treasury"
        # contract means BOTH the tax leg and the remainder land in the
        # treasury, summing to the full pre-tax estate. Currency-agnostic
        # on purpose: neither the settled contract nor the codebase
        # declares a canonical currency code for this orchestrator (every
        # existing apply_estate_tax test hardcodes an illustrative "USD"),
        # so summing every currency key sidesteps guessing T029's choice.
        government.refresh_from_db()
        assert sum(government.government_treasury.values()) == pytest.approx(
            1000.0, abs=_CONSERVATION_TOLERANCE
        )
        # Self-check that the rate is genuinely non-zero, or the test
        # would not distinguish "taxed once" from "never taxed".
        assert rate > 0.0


class TestProcessInheritanceBatchTwoIndependentTransfersToOneHeir:
    """The real chain case (design spec Sezione 5): a living heir who
    qualifies as a direct heir of TWO different same-tick decedents
    receives TWO separate transfers, each taxed once against its OWN
    source estate -- never a single combined transfer taxed once against
    the sum, and never taxed twice on either leg. See the FAMILY-TOPOLOGY
    NOTE above for why the shared heir is built as a common child (one
    parentage FK per decedent) rather than a literal grandchild.
    """

    @pytest.mark.django_db
    def test_heir_receives_two_separately_taxed_transfers_summing_correctly(
        self, sim_with_government
    ):
        sim, zone, government = sim_with_government
        _set_demography_template(sim, "industrial")
        template = load_template("industrial")
        rate = template["economic_inheritance"]["estate_tax_rate"]

        grandfather = _make_agent(
            sim, zone, "Grandfather", is_alive=False, wealth=1000.0, age=90, birth_tick=-400
        )
        father = _make_agent(
            sim, zone, "Father", is_alive=False, wealth=500.0, age=60, birth_tick=-300
        )
        grandson = _make_agent(
            sim,
            zone,
            "Grandson",
            parent_agent=grandfather,
            other_parent_agent=father,
            wealth=0.0,
            birth_tick=-30,
        )

        process_inheritance_batch(sim, tick=50, deceased_agents=[grandfather, father])

        grandson.refresh_from_db()
        grandfather.refresh_from_db()
        father.refresh_from_db()
        government.refresh_from_db()

        inheritable_from_grandfather = 1000.0 * (1 - rate)
        inheritable_from_father = 500.0 * (1 - rate)
        expected_total_tax = 1000.0 * rate + 500.0 * rate

        assert grandson.wealth == pytest.approx(
            inheritable_from_grandfather + inheritable_from_father, abs=_CONSERVATION_TOLERANCE
        )
        assert grandfather.wealth == pytest.approx(0.0, abs=_CONSERVATION_TOLERANCE)
        assert father.wealth == pytest.approx(0.0, abs=_CONSERVATION_TOLERANCE)
        assert sum(government.government_treasury.values()) == pytest.approx(
            expected_total_tax, abs=_CONSERVATION_TOLERANCE
        )

        transfer_events = DemographyEvent.objects.filter(
            simulation=sim,
            event_type=DemographyEvent.EventType.INHERITANCE_TRANSFER,
            secondary_agent=grandson,
        )
        assert transfer_events.count() == 2

        event_from_grandfather = transfer_events.get(primary_agent=grandfather)
        event_from_father = transfer_events.get(primary_agent=father)
        assert event_from_grandfather.payload["assets"]["cash"] == pytest.approx(
            inheritable_from_grandfather, abs=_CONSERVATION_TOLERANCE
        )
        assert event_from_father.payload["assets"]["cash"] == pytest.approx(
            inheritable_from_father, abs=_CONSERVATION_TOLERANCE
        )


class TestProcessInheritanceBatchCrossTickMiss5:
    """Fix MISS-5, cross-tick case: a father who died in an EARLIER tick
    (already `is_alive=False`, `death_tick` before the current tick, and
    NOT included in this batch's `deceased_agents`) is never a bequest
    conduit either -- the estate falls through to the next living
    category exactly as if he had never existed. See the FAMILY-TOPOLOGY
    NOTE above: the fallback recipient here is a second living child of
    the same decedent (the same-generation category `resolve_heirs`
    actually provides), not a literal grandchild.
    """

    @pytest.mark.django_db
    def test_earlier_tick_dead_child_excluded_falls_to_next_living_child(self, sim_with_government):
        sim, zone, government = sim_with_government
        _set_demography_template(sim, "industrial")
        template = load_template("industrial")
        rate = template["economic_inheritance"]["estate_tax_rate"]

        grandfather = _make_agent(
            sim, zone, "Grandfather", is_alive=False, wealth=1000.0, age=90, birth_tick=-400
        )
        father = _make_agent(
            sim,
            zone,
            "Father",
            parent_agent=grandfather,
            is_alive=False,
            death_tick=10,
            wealth=0.0,
            age=60,
            birth_tick=-300,
        )
        second_child = _make_agent(
            sim, zone, "SecondChild", parent_agent=grandfather, wealth=0.0, birth_tick=-250
        )

        # father died at tick 10 -- strictly before this batch's tick 50 --
        # and is deliberately NOT in deceased_agents.
        process_inheritance_batch(sim, tick=50, deceased_agents=[grandfather])

        father.refresh_from_db()
        second_child.refresh_from_db()
        government.refresh_from_db()

        assert father.wealth == pytest.approx(0.0, abs=_CONSERVATION_TOLERANCE)
        expected_inheritable = 1000.0 * (1 - rate)
        assert second_child.wealth == pytest.approx(
            expected_inheritable, abs=_CONSERVATION_TOLERANCE
        )
        assert not DemographyEvent.objects.filter(
            simulation=sim,
            event_type=DemographyEvent.EventType.INHERITANCE_TRANSFER,
            primary_agent=grandfather,
            secondary_agent=father,
        ).exists()
        # Taxed exactly once (the single actual transfer to second_child),
        # never re-applied on account of father's exclusion.
        assert sum(government.government_treasury.values()) == pytest.approx(
            1000.0 * rate, abs=_CONSERVATION_TOLERANCE
        )


class TestProcessInheritanceBatchEventPayload:
    """`DemographyEvent` shape for an actual heir transfer (design spec
    Sezione 5, DemographyEvent payload schemas, `inheritance_transfer`
    row): `event_type=INHERITANCE_TRANSFER`, `simulation`, `tick`,
    `primary_agent=deceased`, `secondary_agent=heir`, and a payload
    carrying `deceased_id`, `heir_id`, `assets: {cash, property_ids,
    loans_as_lender}`, `estate_tax_applied`, `rule_used`.

    `estate_tax_applied` and `rule_used`'s exact meaning is not specified
    anywhere upstream of this task (the design spec names the keys but not
    their semantics) -- this test PINS them explicitly: `estate_tax_applied`
    is the absolute tax AMOUNT (a float) subtracted from this transfer's
    own source estate, and `rule_used` is the era template's
    `economic_inheritance.rule` string. `property_ids` / `loans_as_lender`
    are asserted only to be lists, per the settled contract leaving their
    population to T029.
    """

    @pytest.mark.django_db
    def test_event_carries_the_full_payload_shape(self, sim_with_government):
        sim, zone, government = sim_with_government
        _set_demography_template(sim, "industrial")
        template = load_template("industrial")
        rate = template["economic_inheritance"]["estate_tax_rate"]
        rule = template["economic_inheritance"]["rule"]

        deceased = _make_agent(
            sim, zone, "Deceased", is_alive=False, wealth=1000.0, age=70, birth_tick=-300
        )
        heir = _make_agent(sim, zone, "Heir", parent_agent=deceased, wealth=0.0, birth_tick=-30)

        process_inheritance_batch(sim, tick=50, deceased_agents=[deceased])

        event = DemographyEvent.objects.get(
            simulation=sim,
            event_type=DemographyEvent.EventType.INHERITANCE_TRANSFER,
            primary_agent=deceased,
            secondary_agent=heir,
        )
        assert event.tick == 50

        payload = event.payload
        assert "deceased_id" in payload
        assert "heir_id" in payload
        assert "assets" in payload
        assert "estate_tax_applied" in payload
        assert "rule_used" in payload
        assert payload["deceased_id"] == deceased.id
        assert payload["heir_id"] == heir.id
        assert payload["rule_used"] == rule

        expected_tax = 1000.0 * rate
        expected_cash = 1000.0 - expected_tax
        assert payload["estate_tax_applied"] == pytest.approx(
            expected_tax, abs=_CONSERVATION_TOLERANCE
        )

        assets = payload["assets"]
        assert "cash" in assets
        assert "property_ids" in assets
        assert "loans_as_lender" in assets
        assert assets["cash"] == pytest.approx(expected_cash, abs=_CONSERVATION_TOLERANCE)
        assert isinstance(assets["property_ids"], list)
        assert isinstance(assets["loans_as_lender"], list)


class TestProcessInheritanceBatchEventPayloadReportsTheClampedTax:
    """Fix T046/C-3 (phase-6 audit round 1 -- prefixed to distinguish this
    finding from `process_inheritance_batch`'s unrelated, pre-existing
    design-spec fix also numbered "C-3", the Simultaneous Death Act
    processing-order convention): `estate_tax_applied` in the
    event payload must report the tax `apply_estate_tax` ACTUALLY applied
    (the rate clamped into [0, 1] internally), never the raw
    `economic_inheritance.estate_tax_rate` template value before clamping.
    Before this fix, `process_inheritance_batch` computed `tax_amount =
    total_estate_value * rate` using the RAW rate in a completely separate
    expression from `apply_estate_tax`'s own internal clamp -- a malformed
    template rate (the "40 instead of 0.40" authoring error the clamp
    exists to survive, per `apply_estate_tax`'s own docstring) credited
    the treasury correctly (clamped) while reporting a wildly wrong figure
    in every `inheritance_transfer` event for that estate.

    REPRODUCTION CHOICE, EXPLAINED: the audit's own illustrative example
    is a rate ABOVE 1 ("40 instead of 0.40"). A rate above 1 clamps to
    EXACTLY 1.0, meaning `apply_estate_tax` returns a remainder of EXACTLY
    0.0 for ANY estate value -- and `process_inheritance_batch`'s own
    documented ZERO-VALUE TRANSFERS rule skips a 0.0 allocation entry
    entirely (no wealth credit, no event). That case is therefore
    impossible to observe through the event payload at all, regardless of
    estate size or heir count -- there is no non-zero transfer to inspect.
    A rate BELOW 0 is the same underlying defect (raw unclamped rate used
    for the payload) in the one variant that IS observable this way: it
    clamps to 0.0 (a NON-zero remainder -- the full estate transfers, a
    real event is created), while the buggy code's raw-rate computation
    produces a nonsensical NEGATIVE "tax applied".
    """

    @pytest.mark.django_db
    def test_negative_template_rate_clamps_to_zero_tax_in_the_payload(
        self, sim_with_government, monkeypatch
    ):
        import copy

        import epocha.apps.demography.template_loader as template_loader_module

        sim, zone, government = sim_with_government
        _set_demography_template(sim, "industrial")

        malformed_template = copy.deepcopy(load_template("industrial"))
        malformed_template["economic_inheritance"]["estate_tax_rate"] = -0.5
        real_load_template = template_loader_module.load_template
        monkeypatch.setattr(
            template_loader_module,
            "load_template",
            lambda name: malformed_template if name == "industrial" else real_load_template(name),
        )

        deceased = _make_agent(
            sim, zone, "Deceased", is_alive=False, wealth=1000.0, age=70, birth_tick=-300
        )
        heir = _make_agent(sim, zone, "Heir", parent_agent=deceased, wealth=0.0, birth_tick=-30)

        process_inheritance_batch(sim, tick=50, deceased_agents=[deceased])

        event = DemographyEvent.objects.get(
            simulation=sim,
            event_type=DemographyEvent.EventType.INHERITANCE_TRANSFER,
            primary_agent=deceased,
            secondary_agent=heir,
        )
        # apply_estate_tax clamps rate=-0.5 into [0, 1] -> 0.0 internally,
        # so the ACTUALLY applied tax is 0.0 and the full 1000.0 transfers
        # as cash -- the payload must report that clamped 0.0, never
        # 1000.0 * -0.5 = -500.0 (the raw, unclamped, nonsensical figure).
        assert event.payload["estate_tax_applied"] == pytest.approx(
            0.0, abs=_CONSERVATION_TOLERANCE
        )
        assert event.payload["assets"]["cash"] == pytest.approx(1000.0, abs=_CONSERVATION_TOLERANCE)

        # Treasury received nothing under the clamped 0.0 rate.
        government.refresh_from_db()
        treasury = government.government_treasury or {}
        assert treasury.get("USD", 0.0) == pytest.approx(0.0, abs=_CONSERVATION_TOLERANCE)


class TestProcessInheritanceBatchResolvesTheSimulationsRealPrimaryCurrency:
    """Fix I-10 (phase-6 audit round 1, T046): estate tax and heirless-
    estate treasury credits must land under the simulation's REAL primary
    currency code when one exists, not an unconditional hardcoded "USD" no
    other treasury caller in the codebase uses. Every other `add_to_
    treasury` caller resolves it the same way: `economy/property_market.py`
    and `economy/credit.py` both query `Currency.objects.filter(simulation=
    simulation, is_primary=True).order_by("id").first()`, and `economy/
    context.py` inlines the identical filter -- this fix follows that same
    established, repeated pattern (there is no shared PUBLIC helper to
    import; every existing caller inlines its own copy, so inlining here
    too is the consistent choice, not a new one).

    Before this fix, in any simulation not literally denominated USD --
    the design's own example uses LVR -- estate tax and heirless estates
    piled into a treasury key no spending path reads: a permanently
    sequestered 40% of every estate under `modern_democracy`.

    The fallback (`ESTATE_TAX_CURRENCY_FALLBACK_CODE`, still "USD") is preserved
    for the "simplified" economy tier, where a simulation may have zero
    Currency rows at all (verified: `sim_with_government` -- reused by
    every other test in this class family -- creates no Currency row, and
    those tests already pass under exactly this fallback).
    """

    @pytest.mark.django_db
    def test_estate_tax_credits_the_simulations_own_primary_currency_not_usd(
        self, sim_with_government
    ):
        sim, zone, government = sim_with_government
        _set_demography_template(sim, "modern_democracy")
        Currency.objects.create(
            simulation=sim, code="LVR", name="Livre", symbol="L", is_primary=True, total_supply=0.0
        )

        deceased = _make_agent(
            sim, zone, "Deceased", is_alive=False, wealth=1000.0, age=70, birth_tick=-300
        )
        _make_agent(sim, zone, "Heir", parent_agent=deceased, wealth=0.0, birth_tick=-30)

        process_inheritance_batch(sim, tick=50, deceased_agents=[deceased])

        template = load_template("modern_democracy")
        rate = template["economic_inheritance"]["estate_tax_rate"]
        expected_tax = 1000.0 * rate

        government.refresh_from_db()
        treasury = government.government_treasury or {}
        assert treasury.get("LVR", 0.0) == pytest.approx(
            expected_tax, abs=_CONSERVATION_TOLERANCE
        ), (
            f"treasury={treasury} -- estate tax did not land under the simulation's "
            "own primary currency LVR"
        )
        assert "USD" not in treasury, (
            f"treasury={treasury} -- estate tax landed under the hardcoded USD "
            "fallback even though a real primary Currency (LVR) exists"
        )

    @pytest.mark.django_db
    def test_heirless_estate_credits_the_simulations_own_primary_currency_not_usd(
        self, sim_with_government
    ):
        """The SECOND treasury-crediting site (the empty-allocation
        fallback for a heirless or nationalized estate) must resolve the
        same real currency, not just apply_estate_tax's own call site.
        """
        sim, zone, government = sim_with_government
        _set_demography_template(sim, "modern_democracy")
        Currency.objects.create(
            simulation=sim, code="LVR", name="Livre", symbol="L", is_primary=True, total_supply=0.0
        )
        template = load_template("modern_democracy")
        rate = template["economic_inheritance"]["estate_tax_rate"]

        # No heirs at all: the entire post-tax remainder routes to treasury.
        deceased = _make_agent(
            sim, zone, "Deceased", is_alive=False, wealth=1000.0, age=70, birth_tick=-300
        )

        process_inheritance_batch(sim, tick=50, deceased_agents=[deceased])

        expected_total = 1000.0 * rate + 1000.0 * (1.0 - rate)  # tax + heirless remainder
        government.refresh_from_db()
        treasury = government.government_treasury or {}
        assert treasury.get("LVR", 0.0) == pytest.approx(
            expected_total, abs=_CONSERVATION_TOLERANCE
        )
        assert "USD" not in treasury


class TestProcessInheritanceBatchOrderingC3:
    """Fix C-3 (design spec's own numbering, NOT this file's separate
    audit-numbered `T046/C-3`, the event-payload tax figure): the batch
    processes deceased agents oldest (`age`
    descending) first, `id` ascending as the deterministic tiebreak for
    equal age -- the Simultaneous Death Act convention. Observed via the
    ORDER of the emitted `DemographyEvent` rows (queried by `id`, which
    reflects creation/processing order).
    """

    @pytest.mark.django_db
    def test_events_are_emitted_oldest_first_regardless_of_input_order(self, sim_with_government):
        sim, zone, government = sim_with_government
        _set_demography_template(sim, "industrial")

        older = _make_agent(
            sim, zone, "Older", is_alive=False, wealth=100.0, age=85, birth_tick=-500
        )
        _make_agent(sim, zone, "OlderHeir", parent_agent=older, wealth=0.0, birth_tick=-100)
        younger = _make_agent(
            sim, zone, "Younger", is_alive=False, wealth=100.0, age=40, birth_tick=-200
        )
        _make_agent(sim, zone, "YoungerHeir", parent_agent=younger, wealth=0.0, birth_tick=-50)

        # Deliberately passed younger-first -- the OPPOSITE of the required
        # processing order -- so this test cannot pass by accident of
        # input order matching the expected output order.
        process_inheritance_batch(sim, tick=50, deceased_agents=[younger, older])

        events = list(
            DemographyEvent.objects.filter(
                simulation=sim, event_type=DemographyEvent.EventType.INHERITANCE_TRANSFER
            ).order_by("id")
        )
        assert [event.primary_agent_id for event in events] == [older.id, younger.id]

    @pytest.mark.django_db
    def test_equal_age_tiebreak_is_id_ascending(self, sim_with_government):
        sim, zone, government = sim_with_government
        _set_demography_template(sim, "industrial")

        first_created = _make_agent(
            sim, zone, "FirstCreated", is_alive=False, wealth=100.0, age=50, birth_tick=-200
        )
        _make_agent(sim, zone, "FirstHeir", parent_agent=first_created, wealth=0.0, birth_tick=-50)
        second_created = _make_agent(
            sim, zone, "SecondCreated", is_alive=False, wealth=100.0, age=50, birth_tick=-200
        )
        _make_agent(
            sim, zone, "SecondHeir", parent_agent=second_created, wealth=0.0, birth_tick=-50
        )
        assert first_created.id < second_created.id  # self-check

        process_inheritance_batch(sim, tick=50, deceased_agents=[second_created, first_created])

        events = list(
            DemographyEvent.objects.filter(
                simulation=sim, event_type=DemographyEvent.EventType.INHERITANCE_TRANSFER
            ).order_by("id")
        )
        assert [event.primary_agent_id for event in events] == [
            first_created.id,
            second_created.id,
        ]


class TestProcessInheritanceBatchCoupleDissolution:
    """Composition (design spec Sezione 5): the batch calls
    `dissolve_on_death` per deceased (decision D1), observable as the
    `Couple` row's own state -- including fix MISS-4, both partners of one
    couple dying in the same batch.
    """

    @pytest.mark.django_db
    def test_single_partner_death_dissolves_couple_with_death_reason(self, sim_with_government):
        sim, zone, government = sim_with_government
        _set_demography_template(sim, "industrial")

        deceased = _make_agent(
            sim, zone, "Deceased", is_alive=False, wealth=0.0, age=70, birth_tick=-300
        )
        partner = _make_agent(sim, zone, "Partner", wealth=0.0, birth_tick=-290)
        form_couple(deceased, partner, formed_at_tick=1)

        process_inheritance_batch(sim, tick=50, deceased_agents=[deceased])

        couple = Couple.objects.get(simulation=sim)
        assert couple.dissolved_at_tick == 50
        assert couple.dissolution_reason == Couple.DissolutionReason.DEATH
        if deceased.id < partner.id:
            assert couple.agent_a_id is None
            assert couple.agent_a_name_snapshot == deceased.name
            assert couple.agent_b_id == partner.id
        else:
            assert couple.agent_b_id is None
            assert couple.agent_b_name_snapshot == deceased.name
            assert couple.agent_a_id == partner.id

    @pytest.mark.django_db
    def test_miss4_both_partners_die_in_same_batch_couple_dissolved_once(self, sim_with_government):
        sim, zone, government = sim_with_government
        _set_demography_template(sim, "industrial")

        partner_one = _make_agent(
            sim, zone, "PartnerOne", is_alive=False, wealth=0.0, age=70, birth_tick=-300
        )
        partner_two = _make_agent(
            sim, zone, "PartnerTwo", is_alive=False, wealth=0.0, age=68, birth_tick=-290
        )
        form_couple(partner_one, partner_two, formed_at_tick=1)

        process_inheritance_batch(sim, tick=50, deceased_agents=[partner_one, partner_two])

        assert Couple.objects.filter(simulation=sim).count() == 1
        couple = Couple.objects.get(simulation=sim)
        assert couple.agent_a_id is None
        assert couple.agent_b_id is None
        assert couple.dissolved_at_tick == 50
        assert couple.dissolution_reason == Couple.DissolutionReason.DEATH
        assert {couple.agent_a_name_snapshot, couple.agent_b_name_snapshot} == {
            partner_one.name,
            partner_two.name,
        }


class TestProcessInheritanceBatchMourningMemories:
    """Composition: the batch calls `generate_mourning_memories` per
    deceased, observable as `Memory` rows for survivors.
    """

    @pytest.mark.django_db
    def test_batch_generates_a_mourning_memory_for_the_surviving_partner(self, sim_with_government):
        sim, zone, government = sim_with_government
        _set_demography_template(sim, "industrial")

        deceased = _make_agent(
            sim, zone, "Deceased", is_alive=False, wealth=0.0, age=70, birth_tick=-300
        )
        partner = _make_agent(sim, zone, "Partner", wealth=0.0, birth_tick=-290)
        form_couple(deceased, partner, formed_at_tick=1)

        process_inheritance_batch(sim, tick=50, deceased_agents=[deceased])

        assert Memory.objects.filter(agent=partner, origin_agent=deceased).exists()


class TestProcessInheritanceBatchOrphanCaretaker:
    """Composition: the batch calls `assign_orphan_caretaker` for a minor
    newly orphaned by this same batch, observable as the minor's
    persisted `caretaker_agent`.
    """

    @pytest.mark.django_db
    def test_batch_assigns_a_caretaker_to_a_newly_orphaned_minor(self, sim_with_government):
        sim, zone, government = sim_with_government
        _set_demography_template(sim, "industrial")

        mother = _make_agent(
            sim, zone, "Mother", is_alive=False, wealth=0.0, age=40, birth_tick=-400
        )
        father = _make_agent(
            sim, zone, "Father", is_alive=False, wealth=0.0, age=42, birth_tick=-420
        )
        sibling = _make_agent(
            sim,
            zone,
            "Sibling",
            parent_agent=mother,
            other_parent_agent=father,
            wealth=0.0,
            birth_tick=-100,
        )
        minor = _make_agent(
            sim,
            zone,
            "Minor",
            parent_agent=mother,
            other_parent_agent=father,
            age=10,
            wealth=0.0,
            birth_tick=-10,
        )

        process_inheritance_batch(sim, tick=50, deceased_agents=[mother, father])

        persisted_minor = Agent.objects.get(id=minor.id)
        assert persisted_minor.caretaker_agent_id == sibling.id


class TestProcessInheritanceBatchLoanTransfer:
    """Composition: the batch calls `transfer_loans_as_lender` per
    deceased, observable as the reassigned `Loan.lender`.
    """

    @pytest.mark.django_db
    def test_batch_transfers_an_active_lender_side_loan_to_the_living_heir(
        self, sim_with_government
    ):
        sim, zone, government = sim_with_government
        _set_demography_template(sim, "industrial")

        deceased = _make_agent(
            sim, zone, "Deceased", is_alive=False, wealth=0.0, age=70, birth_tick=-300
        )
        heir = _make_agent(sim, zone, "Heir", parent_agent=deceased, wealth=0.0, birth_tick=-30)
        borrower = _make_agent(sim, zone, "Borrower", wealth=0.0, birth_tick=-30)
        loan = _make_loan(sim, borrower, lender=deceased)

        process_inheritance_batch(sim, tick=50, deceased_agents=[deceased])

        loan.refresh_from_db()
        assert loan.lender_id == heir.id

    @pytest.mark.django_db
    def test_matrilineal_loan_transfer_query_cost_does_not_scale_with_sister_count(
        self, monkeypatch
    ):
        """Fix NEW-7 (phase-6 audit round 4, T046): end-to-end proof, via
        the REAL `process_inheritance_batch` orchestrator (not
        `transfer_loans_as_lender` called in isolation), that threading
        `matrilineal_heirs` through both `distribute_estate` and
        `transfer_loans_as_lender` actually happens on the production
        path, not merely in a hand-assembled unit test. No era template
        selects `matrilineal` (verified elsewhere in this file), so the
        rule is forced via the same `load_template` monkeypatch pattern
        `TestProcessInheritanceBatchEventPayloadReportsTheClampedTax`
        already established.

        DELTA, not an exact total: the full batch's query count depends on
        many unrelated moving parts (`dissolve_on_death`, mourning
        memories, treasury resolution, wealth `bulk_update`, event
        `bulk_create`) that are not this fix's concern and would make an
        exact total fragile to pin. Comparing ONE sister against FOUR
        isolates exactly the sister-resolution cost fix NEW-7 addresses:
        if it still doubled (once inside `distribute_estate`, again inside
        `transfer_loans_as_lender`), three extra sisters would cost SIX
        extra queries; threaded correctly, they cost exactly THREE. Two
        INDEPENDENT simulations are built (not the shared `sim_with_
        government` fixture, which is not re-invocable mid-test) so
        neither scenario's rows leak into the other's query count.
        """
        import copy

        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        import epocha.apps.demography.template_loader as template_loader_module

        matrilineal_template = copy.deepcopy(load_template("industrial"))
        matrilineal_template["economic_inheritance"]["rule"] = "matrilineal"
        real_load_template = template_loader_module.load_template
        monkeypatch.setattr(
            template_loader_module,
            "load_template",
            lambda name: matrilineal_template if name == "industrial" else real_load_template(name),
        )

        def _build_sim_with_government(label: str):
            user = User.objects.create_user(
                email=f"{label}@epocha.dev", username=label, password="pass1234"
            )
            sim = Simulation.objects.create(name=label, seed=2026, owner=user, current_tick=10)
            world = World.objects.create(simulation=sim, stability_index=0.7)
            zone = Zone.objects.create(
                world=world,
                name=f"{label}Zone",
                zone_type="residential",
                boundary=Polygon.from_bbox((0, 0, 100, 100)),
                center=Point(50, 50),
            )
            government = Government.objects.create(simulation=sim)
            _set_demography_template(sim, "industrial")
            return sim, zone, government

        def _run_with_n_sisters(n: int, label: str) -> int:
            sim, zone, government = _build_sim_with_government(label)
            common_parent = _make_agent(sim, zone, "CommonParent")
            deceased = _make_agent(
                sim,
                zone,
                "Deceased",
                parent_agent=common_parent,
                is_alive=False,
                wealth=1000.0,
                age=70,
                birth_tick=-300,
            )
            for i in range(n):
                sister = _make_agent(
                    sim,
                    zone,
                    f"Sister{i}",
                    parent_agent=common_parent,
                    gender=Agent.Gender.FEMALE,
                    birth_tick=-250 + i,
                )
                _make_agent(sim, zone, f"Niece{i}", parent_agent=sister, birth_tick=-30 + i)
            borrower = _make_agent(sim, zone, "Borrower", wealth=0.0, birth_tick=-30)
            _make_loan(sim, borrower, lender=deceased)

            with CaptureQueriesContext(connection) as ctx:
                process_inheritance_batch(sim, tick=50, deceased_agents=[deceased])
            return len(ctx.captured_queries)

        queries_one_sister = _run_with_n_sisters(1, "matone")
        queries_four_sisters = _run_with_n_sisters(4, "matfour")

        delta = queries_four_sisters - queries_one_sister
        assert delta == 3, (
            f"1 sister cost {queries_one_sister} queries, 4 sisters cost "
            f"{queries_four_sisters} -- delta {delta}, expected exactly 3 "
            "(one query per extra sister, resolved once and shared between "
            "distribute_estate and transfer_loans_as_lender, not once per "
            "consumer)"
        )

    @pytest.mark.django_db
    def test_matrilineal_end_to_end_transfers_loan_to_a_niece_or_nephew(
        self, sim_with_government, monkeypatch
    ):
        """Functional companion to the query-cost test above: proves the
        THREADED matrilineal_heirs value is not just cheap but CORRECT --
        the loan actually reaches the niece/nephew `distribute_estate`
        paid cash to, through the real orchestrator, not a hand-assembled
        `heirs`/`cash_allocation` pair.
        """
        import copy

        import epocha.apps.demography.template_loader as template_loader_module

        sim, zone, government = sim_with_government
        _set_demography_template(sim, "industrial")

        matrilineal_template = copy.deepcopy(load_template("industrial"))
        matrilineal_template["economic_inheritance"]["rule"] = "matrilineal"
        real_load_template = template_loader_module.load_template
        monkeypatch.setattr(
            template_loader_module,
            "load_template",
            lambda name: matrilineal_template if name == "industrial" else real_load_template(name),
        )

        common_parent = _make_agent(sim, zone, "CommonParent")
        deceased = _make_agent(
            sim,
            zone,
            "Deceased",
            parent_agent=common_parent,
            is_alive=False,
            wealth=1000.0,
            age=70,
            birth_tick=-300,
        )
        sister = _make_agent(
            sim,
            zone,
            "Sister",
            parent_agent=common_parent,
            gender=Agent.Gender.FEMALE,
            birth_tick=-250,
        )
        niece = _make_agent(sim, zone, "Niece", parent_agent=sister, birth_tick=-30)
        borrower = _make_agent(sim, zone, "Borrower", wealth=0.0, birth_tick=-30)
        loan = _make_loan(sim, borrower, lender=deceased)

        process_inheritance_batch(sim, tick=50, deceased_agents=[deceased])

        loan.refresh_from_db()
        assert loan.lender_id == niece.id
        assert loan.lender_type == "agent"


class TestProcessInheritanceBatchPersistence:
    """Unlike this module's pure resolvers, `process_inheritance_batch` IS
    the orchestrated entry point and DOES persist: heir wealth credits and
    the deceased's zeroed wealth must survive a FRESH query (`Agent.
    objects.get`), not merely live on the in-memory instances the caller
    happens to still hold.
    """

    @pytest.mark.django_db
    def test_heir_and_deceased_wealth_are_persisted_not_only_in_memory(self, sim_with_government):
        sim, zone, government = sim_with_government
        _set_demography_template(sim, "industrial")
        template = load_template("industrial")
        rate = template["economic_inheritance"]["estate_tax_rate"]

        deceased = _make_agent(
            sim, zone, "Deceased", is_alive=False, wealth=1000.0, age=70, birth_tick=-300
        )
        heir = _make_agent(sim, zone, "Heir", parent_agent=deceased, wealth=0.0, birth_tick=-30)

        process_inheritance_batch(sim, tick=50, deceased_agents=[deceased])

        persisted_deceased = Agent.objects.get(id=deceased.id)
        persisted_heir = Agent.objects.get(id=heir.id)

        assert persisted_deceased.wealth == pytest.approx(0.0, abs=_CONSERVATION_TOLERANCE)
        assert persisted_heir.wealth == pytest.approx(
            1000.0 * (1 - rate), abs=_CONSERVATION_TOLERANCE
        )


class TestProcessInheritanceBatchEmptyBatch:
    """An empty batch is a no-op: no events, no exceptions."""

    @pytest.mark.django_db
    def test_empty_batch_creates_no_events_and_does_not_raise(self, sim_with_government):
        sim, zone, government = sim_with_government
        _set_demography_template(sim, "industrial")

        process_inheritance_batch(sim, tick=50, deceased_agents=[])

        assert not DemographyEvent.objects.filter(simulation=sim).exists()


# ---------------------------------------------------------------------------
# Birth-path determinism (Plan 3, T040, SC-003). Two INDEPENDENTLY
# constructed births -- fresh mother/father/child rows each time, so their
# ids genuinely differ (never the same object reused across "run A" and
# "run B", which would prove far less than it looks like it proves) --
# must produce byte-identical child state when driven through the SAME
# simulation, tick, and template. This is the module-wide guarantee
# `apply_trait_inheritance`'s own docstring already claims ("an unordered
# iteration would make the RNG draw sequence depend on the interpreter's
# per-process string hash seed, breaking the bit-for-bit reproducibility
# the demography subsystem requires") -- this test is the executable
# proof of that claim, comparing the FULL resulting state (every scalar
# trait, every personality entry, the derived trait `cunning`, gender,
# orientation, social class, education level, wealth, zone), not a
# sampled field or two.
# ---------------------------------------------------------------------------


class TestBirthPathDeterminismSC003:
    """SC-003: two independently constructed births at the same
    simulation/tick/template produce identical child state, compared by
    VALUE across every field the birth pipeline touches.

    SCOPE, STATED HONESTLY (phase-6 audit round 1, T046, M-1 test
    remediation): despite using two entirely separate database rows for
    mother/father/child (guarding against object-identity/creation-order
    shortcuts), both runs still execute in the SAME interpreter process
    and therefore share one `PYTHONHASHSEED` -- this test is presented
    elsewhere as executable proof that unordered `set` iteration would
    break reproducibility, but it would NOT catch `apply_trait_
    inheritance`'s `sorted(extra_names)` (inheritance.py) being deleted,
    since same-process replay cannot exercise hash-seed-dependent
    ordering at all. See `TestApplyTraitInheritanceDeterminismAcrossHash
    Seeds` below for the test that actually forces two different hash
    seeds via two subprocesses and would catch that deletion.
    """

    @pytest.mark.django_db
    def test_two_independent_births_produce_byte_identical_child_state(self, sim_with_zone):
        sim, zone = sim_with_zone
        template = load_template("pre_industrial_christian")

        mother_personality = {name: 0.65 for name in PERSONALITY_HERITABLE_TRAITS}
        father_personality = {name: 0.35 for name in PERSONALITY_HERITABLE_TRAITS}
        mother_scalars = {name: 0.65 for name in SCALAR_HERITABLE_TRAITS}
        father_scalars = {name: 0.35 for name in SCALAR_HERITABLE_TRAITS}

        # RUN A: its own mother/father/child rows.
        mother_a = _make_agent(
            sim,
            zone,
            "MotherA",
            social_class="wealthy",
            education_level=0.6,
            personality=dict(mother_personality),
            **mother_scalars,
        )
        father_a = _make_agent(
            sim,
            zone,
            "FatherA",
            social_class="middle",
            education_level=0.4,
            personality=dict(father_personality),
            **father_scalars,
        )
        child_a = _make_agent(sim, zone, "ChildA")

        # RUN B: an ENTIRELY SEPARATE set of mother/father/child rows,
        # created AFTER run A's, so their ids are strictly higher --
        # genuinely different database rows, not the same objects reused
        # (the "two calls in one process that happen to hit the same
        # objects prove less than you think" trap). Same trait VALUES as
        # run A, so any difference in the outcome can only come from a
        # hidden dependency on identity/id/creation-order, not from a
        # deliberate input difference.
        mother_b = _make_agent(
            sim,
            zone,
            "MotherB",
            social_class="wealthy",
            education_level=0.6,
            personality=dict(mother_personality),
            **mother_scalars,
        )
        father_b = _make_agent(
            sim,
            zone,
            "FatherB",
            social_class="middle",
            education_level=0.4,
            personality=dict(father_personality),
            **father_scalars,
        )
        child_b = _make_agent(sim, zone, "ChildB")

        assert mother_a.id != mother_b.id  # self-check: genuinely different rows
        assert father_a.id != father_b.id
        assert child_a.id != child_b.id

        rng_a = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")
        rng_b = get_seeded_rng(sim, tick=sim.current_tick, phase="inheritance")

        apply_trait_inheritance(child_a, mother_a, father_a, template, rng_a)
        gender_a, orientation_a = resolve_birth_attributes(template, rng_a)
        child_a.gender = gender_a
        child_a.sexual_orientation = orientation_a
        apply_social_inheritance(
            child_a, mother_a, father_a, template, zone_class_mean=2.0, rng=rng_a
        )
        child_a.wealth = 0.0
        child_a.zone = mother_a.zone

        apply_trait_inheritance(child_b, mother_b, father_b, template, rng_b)
        gender_b, orientation_b = resolve_birth_attributes(template, rng_b)
        child_b.gender = gender_b
        child_b.sexual_orientation = orientation_b
        apply_social_inheritance(
            child_b, mother_b, father_b, template, zone_class_mean=2.0, rng=rng_b
        )
        child_b.wealth = 0.0
        child_b.zone = mother_b.zone

        # Full state comparison -- every field the birth pipeline touches,
        # not a sampled subset.
        for name in SCALAR_HERITABLE_TRAITS:
            assert getattr(child_a, name) == getattr(child_b, name), name
        for name in PERSONALITY_HERITABLE_TRAITS:
            assert child_a.personality[name] == child_b.personality[name], name
        assert child_a.cunning == child_b.cunning  # the derived trait, NOT in either set above
        assert child_a.gender == child_b.gender
        assert child_a.sexual_orientation == child_b.sexual_orientation
        assert child_a.social_class == child_b.social_class
        assert child_a.education_level == child_b.education_level
        assert child_a.wealth == child_b.wealth == 0.0
        assert child_a.zone_id == child_b.zone_id == zone.id


# The subprocess payload below runs `apply_trait_inheritance` standalone --
# no database access anywhere (verified: the function only reads attributes
# already present on the passed mother/father/child instances and issues no
# ORM query; `django.setup()` is needed only so `Agent._meta.get_field`,
# used by `_agent_has_field`, has an app registry to introspect). This is
# what makes running it in a genuinely separate process, under a different
# PYTHONHASHSEED, both correct (no dependency on the parent test's own
# uncommitted transaction, which a subprocess could never see) and fast
# (no database connection ever opened).
_HASH_SEED_DETERMINISM_SUBPROCESS_SCRIPT = """
import json
from types import SimpleNamespace

import django

django.setup()

from epocha.apps.agents.models import Agent
from epocha.apps.demography.inheritance import apply_trait_inheritance
from epocha.apps.demography.rng import get_seeded_rng
from epocha.apps.demography.template_loader import load_template

template = load_template("pre_industrial_christian")

# Personality keys deliberately absent from any era template's heritability
# table -- design spec Sezione 4's own examples of unpublished-h2 traits.
# Five of them, so a bare `set`'s iteration order (hash-seed-dependent,
# unlike `sorted()`) has ample room to differ between two processes.
EXTRA_PERSONALITY_NAMES = [
    "humor_style", "attachment_style", "worldview", "risk_appetite", "loyalty_style",
]
SCALAR_NAMES = [
    "intelligence", "emotional_intelligence", "creativity",
    "strength", "stamina", "agility", "fertility", "mental_health",
]

mother = Agent(
    personality={name: 0.65 for name in EXTRA_PERSONALITY_NAMES},
    **{name: 0.65 for name in SCALAR_NAMES},
)
father = Agent(
    personality={name: 0.35 for name in EXTRA_PERSONALITY_NAMES},
    **{name: 0.35 for name in SCALAR_NAMES},
)
child = Agent()

simulation = SimpleNamespace(id=1, seed=2026)
rng = get_seeded_rng(simulation, tick=10, phase="inheritance")
apply_trait_inheritance(child, mother, father, template, rng)

result = {
    "scalars": {name: getattr(child, name) for name in SCALAR_NAMES},
    "personality": dict(child.personality),
    "cunning": child.cunning,
}
print(json.dumps(result))
"""


class TestApplyTraitInheritanceDeterminismAcrossHashSeeds:
    """Fix M-1 (phase-6 audit round 1, T046) -- TEST REMEDIATION: the
    genuine cross-process determinism proof neither
    `TestApplyInheritanceAtBirthDeterminism` nor `TestBirthPathDeterminism
    SC003` actually is (see their corrected docstrings) -- both run
    entirely within one interpreter process and therefore share one
    `PYTHONHASHSEED`, so neither can exercise hash-seed-dependent
    ordering at all.

    This test runs the SAME computation TWICE, as two separate
    subprocesses, each with an EXPLICIT, DIFFERENT `PYTHONHASHSEED`
    (verified beforehand: this container's own default leaves
    `PYTHONHASHSEED` unset, i.e. randomized per process -- `hash(
    "humor_style")` measured differently across two bare `python3 -c`
    invocations with no `PYTHONHASHSEED` set) and compares the resulting
    child state field-by-field. If `apply_trait_inheritance`'s
    `sorted(extra_names)` (inheritance.py) were deleted, the five
    EXTRA_PERSONALITY_NAMES in the subprocess script above -- present in
    both parents' `personality` dicts but absent from any era template's
    heritability table -- would be drawn from the RNG stream in whatever
    order a bare Python `set` happens to iterate them, which differs by
    `PYTHONHASHSEED`; the two subprocesses would then attribute different
    specific numeric draws to different specific trait names, and this
    test would fail.

    DISCRIMINATION VERIFIED BY MUTATION (per the audit's own required
    proof standard): `sorted(extra_names)` was temporarily changed to
    `list(extra_names)` (same trait names included, iteration order no
    longer forced) and this test was re-run. It failed -- the two
    subprocesses' `personality` dicts disagreed on which EXTRA_PERSONALITY_
    NAME got which numeric value, while every OTHER field (scalars,
    cunning, and the personality keys that ARE in the heritability table,
    whose order was never hash-dependent) still matched. The mutation was
    then reverted; `git diff` showed zero residual changes to
    `inheritance.py` afterward.

    No database access anywhere in the subprocess script (see the
    comment above it) -- this sidesteps the practical obstacle a
    DB-backed subprocess test would hit: `@pytest.mark.django_db` wraps
    each test in a transaction that pytest-django rolls back at the end,
    so rows created in THIS test's own transaction are invisible to any
    other process (a real, separate PostgreSQL connection) regardless of
    hash seed -- a subprocess querying for them would simply find
    nothing. Restricting this test to `apply_trait_inheritance` alone
    (rather than the full `apply_inheritance_at_birth`, which additionally
    queries the zone's population for `zone_class_mean`) avoids that
    obstacle entirely while still exercising the exact line the audit
    named.
    """

    def test_two_different_hash_seeds_produce_identical_trait_attribution(self):
        env_a = {**os.environ, "PYTHONHASHSEED": "0"}
        env_b = {**os.environ, "PYTHONHASHSEED": "4294967295"}

        result_a = subprocess.run(
            [sys.executable, "-c", _HASH_SEED_DETERMINISM_SUBPROCESS_SCRIPT],
            env=env_a,
            capture_output=True,
            text=True,
            timeout=30,
        )
        result_b = subprocess.run(
            [sys.executable, "-c", _HASH_SEED_DETERMINISM_SUBPROCESS_SCRIPT],
            env=env_b,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result_a.returncode == 0, (
            f"subprocess A failed (PYTHONHASHSEED=0): {result_a.stderr}"
        )
        assert result_b.returncode == 0, (
            f"subprocess B failed (PYTHONHASHSEED=4294967295): {result_b.stderr}"
        )

        state_a = json.loads(result_a.stdout)
        state_b = json.loads(result_b.stdout)

        assert state_a == state_b, (
            f"identical inputs under different PYTHONHASHSEED values produced "
            f"different child state -- state_a={state_a!r} state_b={state_b!r}"
        )


# ---------------------------------------------------------------------------
# GENUINE FINDING (T040, not a bug fix -- flagged for the phase-6 audit /
# the project's open determinism investigation, per CLAUDE.md's ABSOLUTE
# PRIORITY: Verify Before Asserting). Verified directly against
# epocha/apps/demography/rng.py: `get_seeded_rng`'s derived seed is
# `sha256(f"{simulation.id}:{simulation.seed}:{tick}:{phase}")`, NOT
# `sha256(f"{simulation.seed}:{tick}:{phase}")` as the module's own
# docstring states ("derived from a deterministic hash of
# (simulation.seed, tick, phase)" -- simulation.id is never named).
# CONSEQUENCE: two DIFFERENT Simulation rows sharing the SAME declared
# `.seed` value do NOT produce the same RNG stream, and therefore do NOT
# produce the same birth outcome, even with byte-identical mother/father
# input values -- verified below. This is DIFFERENT from the already-
# tracked "LLM world/agent generation has no seed" limitation (memory
# project_determinism_enumeration_pending.md): that one is about
# non-deterministic INPUTS (agents differ before inheritance even runs);
# this one is about the RNG STREAM ITSELF being tied to the database row's
# own primary key, so even IDENTICAL inputs on two DIFFERENT simulation
# rows diverge. Whether `simulation.id` in the hash is deliberate
# (isolating concurrent simulation runs from sharing RNG state) or an
# unintended docstring/implementation mismatch is a design question this
# task does NOT resolve -- flagged here, not silently patched, per the
# explicit instruction to stop and report rather than reseed or relax the
# assertion.
# ---------------------------------------------------------------------------


class TestGetSeededRngSimulationIdCoupling:
    """Documents (does not endorse or fix) a verified property of
    `get_seeded_rng`: reproducibility by `.seed` value alone does NOT hold
    across different `Simulation` rows, because the derived seed also
    incorporates `simulation.id`. See the module-level note above this
    class for the full account.
    """

    @pytest.mark.django_db
    def test_same_seed_value_on_different_simulation_rows_yields_different_streams(self):
        user_a = User.objects.create_user(
            email="rng-a@epocha.dev", username="rngusera", password="pass1234"
        )
        user_b = User.objects.create_user(
            email="rng-b@epocha.dev", username="rnguserb", password="pass1234"
        )
        sim_a = Simulation.objects.create(name="RngSimA", seed=2026, owner=user_a)
        sim_b = Simulation.objects.create(name="RngSimB", seed=2026, owner=user_b)

        assert sim_a.seed == sim_b.seed == 2026  # self-check: identical declared seed
        assert sim_a.id != sim_b.id  # self-check: genuinely different rows

        rng_a = get_seeded_rng(sim_a, tick=10, phase="inheritance")
        rng_b = get_seeded_rng(sim_b, tick=10, phase="inheritance")

        # VERIFIED FINDING: this is NOT the same draw, despite an
        # identical declared .seed, tick, and phase -- because
        # simulation.id differs and is folded into the hash. If a future
        # change to rng.py makes this assertion fail (i.e. the streams
        # become equal), that is progress on the finding above, not a
        # regression -- update this test's assertion deliberately in that
        # case, do not delete it silently.
        assert rng_a.random() != rng_b.random()


# ---------------------------------------------------------------------------
# Era coverage gate (Plan 3, T041, SC-004, Phase 8 closure). All five era
# templates must drive BOTH the inheritance path
# (`process_inheritance_batch`) and the migration path
# (`coordinate_family_migration`, `evaluate_emergency_flight`) without
# error, each producing era-appropriate outcomes -- not merely "does not
# raise", the weakest possible criterion and unfit for the last gate
# before the audit.
# ---------------------------------------------------------------------------


class TestEraCoverageSC004:
    """SC-004: all five era templates drive both the inheritance and the
    migration path, each exercising its OWN declared succession rule.

    RULE-PER-ERA MAPPING (verified directly against the five template
    JSON files under epocha/apps/demography/templates/, not assumed):
    only THREE of the five implemented succession rules are actually
    exercised by the five default era templates -- `primogeniture`
    (pre_industrial_christian only), `shari'a` (pre_industrial_islamic
    only), and `equal_split` (industrial, modern_democracy, AND sci_fi --
    three different eras share this one rule). `matrilineal` and
    `nationalized` are declared by NONE of the five default templates;
    both are only reachable through a scenario-authored template
    override, already exercised in isolation by
    `TestDistributeEstateMatrilineal`, `TestDistributeEstateNationalized`,
    and `TestFullEstateChainConservation` above -- not by any default
    era, and not by this test.

    Reuses, rather than duplicating, the per-rule fixture builders
    already established for T020-T022
    (`_build_deceased_for_primogeniture`, `_build_deceased_for_sharia`,
    `_build_deceased_for_equal_split`) and this file's own
    `sim_with_government` / `_make_agent` / `_set_demography_template`.
    """

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "era_name, rule, class_rule, estate_tax_rate, adulthood_age, "
        "flight_trigger_ticks, build_deceased",
        [
            (
                "pre_industrial_christian",
                "primogeniture",
                "patrilineal_rigid",
                0.0,
                16,
                30,
                _build_deceased_for_primogeniture,
            ),
            (
                "pre_industrial_islamic",
                "shari'a",
                "patrilineal_rigid",
                0.0,
                16,
                30,
                _build_deceased_for_sharia,
            ),
            (
                "industrial",
                "equal_split",
                "clark_regression",
                0.15,
                16,
                20,
                _build_deceased_for_equal_split,
            ),
            (
                "modern_democracy",
                "equal_split",
                "becker_tomes_elasticity_0.4",
                0.40,
                18,
                10,
                _build_deceased_for_equal_split,
            ),
            (
                "sci_fi",
                "equal_split",
                "meritocratic",
                0.0,
                18,
                5,
                _build_deceased_for_equal_split,
            ),
        ],
    )
    def test_era_drives_inheritance_and_migration_with_era_appropriate_outcomes(
        self,
        sim_with_government,
        era_name,
        rule,
        class_rule,
        estate_tax_rate,
        adulthood_age,
        flight_trigger_ticks,
        build_deceased,
    ):
        sim, zone, government = sim_with_government
        _set_demography_template(sim, era_name)
        template = load_template(era_name)

        # Self-check: the parametrize table states facts read directly
        # off the template JSON files (see the class docstring's RULE-PER-
        # ERA MAPPING) -- verify them here so a future template edit that
        # silently changes one of these values is caught by THIS test,
        # never merely assumed.
        assert template["economic_inheritance"]["rule"] == rule
        assert template["social_inheritance"]["class_rule"] == class_rule
        assert template["economic_inheritance"]["estate_tax_rate"] == pytest.approx(estate_tax_rate)
        assert template["migration"]["adulthood_age"] == adulthood_age
        assert template["migration"]["flight_trigger_ticks"] == flight_trigger_ticks

        # --- INHERITANCE PATH: process_inheritance_batch end to end,
        # asserting the era's OWN tax rate and the succession rule's
        # distinctive allocation signature -- not merely absence of error.
        deceased = build_deceased(sim, zone)
        deceased.wealth = 1000.0
        deceased.is_alive = False
        deceased.save(update_fields=["wealth", "is_alive"])

        process_inheritance_batch(sim, tick=50, deceased_agents=[deceased])

        government.refresh_from_db()
        expected_tax = 1000.0 * estate_tax_rate
        assert sum(government.government_treasury.values()) == pytest.approx(
            expected_tax, abs=_CONSERVATION_TOLERANCE
        )
        inheritable = 1000.0 - expected_tax

        # Every heir created by the builders above starts at
        # _make_agent's own default wealth (100.0) -- process_inheritance_
        # batch correctly credits ON TOP OF that pre-existing balance
        # (its own documented T029 contract: "a heir's final wealth is
        # their pre-batch database value plus every credit accumulated"),
        # so the rule-signature assertions below compare the CREDITED
        # DELTA (wealth minus the 100.0 baseline), not the raw post-batch
        # wealth -- comparing raw wealth against a bare `inheritable`
        # figure was this test's own first-draft bug, caught by running
        # it, not assumed away.
        _heir_baseline_wealth = 100.0

        if rule == "primogeniture":
            son = Agent.objects.get(simulation=sim, name="Son")
            assert son.wealth - _heir_baseline_wealth == pytest.approx(
                inheritable, abs=_CONSERVATION_TOLERANCE
            )
        elif rule == "shari'a":
            # spouse_fraction = 1/8 when children are present (verified
            # against _distribute_sharia's own docstring/body); residual
            # splits 2:1 son:daughter.
            partner = Agent.objects.get(simulation=sim, name="Partner")
            son = Agent.objects.get(simulation=sim, name="Son")
            daughter = Agent.objects.get(simulation=sim, name="Daughter")
            assert partner.wealth - _heir_baseline_wealth == pytest.approx(
                inheritable / 8, abs=_CONSERVATION_TOLERANCE
            )
            assert son.wealth - _heir_baseline_wealth == pytest.approx(
                2 * (daughter.wealth - _heir_baseline_wealth), abs=_CONSERVATION_TOLERANCE
            )
        elif rule == "equal_split":
            # Three equal shares (spouse counts as a child's share); the
            # two children never absorb the float remainder (spouse is
            # last in this rule's own deterministic order), so they must
            # be exactly equal.
            #
            # Fix M-1 (phase-6 audit round 1, T046) -- TEST REMEDIATION:
            # `partner.wealth > 0.0` was too loose -- every fixture agent
            # starts at the 100.0 baseline (`_heir_baseline_wealth`), so
            # this assertion passed even with the spouse dropped from
            # equal_split entirely (partner.wealth would simply stay at
            # its untouched 100.0 baseline, still > 0.0). Tightened to the
            # exact expected credited delta.
            partner = Agent.objects.get(simulation=sim, name="Partner")
            child_a = Agent.objects.get(simulation=sim, name="ChildA")
            child_b = Agent.objects.get(simulation=sim, name="ChildB")
            assert child_a.wealth == pytest.approx(child_b.wealth, abs=_CONSERVATION_TOLERANCE)
            assert partner.wealth - _heir_baseline_wealth == pytest.approx(
                inheritable / 3, abs=_CONSERVATION_TOLERANCE
            )

        # --- MIGRATION PATH, part 1: coordinate_family_migration reads
        # this era's adulthood_age (16 vs 18) -- a 17-year-old is an adult
        # under the 16-eras and a minor under the 18-eras, so the SAME
        # fixture discriminates every era's own declared value.
        target_zone = Zone.objects.create(
            world=zone.world,
            name=f"{era_name}Target",
            zone_type="residential",
            boundary=Polygon.from_bbox((200, 200, 300, 300)),
            center=Point(250, 250),
        )
        family_head = _make_agent(sim, zone, f"{era_name}FamilyHead")
        teenager = _make_agent(sim, zone, f"{era_name}Teenager", parent_agent=family_head, age=17)

        # Fix M-1 (phase-6 audit round 1, T046) -- TEST REMEDIATION: a
        # seeded rng is passed here (T038-added, KEYWORD-only-in-practice
        # `rng` parameter, still optional per `coordinate_family_
        # migration`'s own signature -- read fresh before writing this,
        # confirmed unchanged and still defaulted to None). Before this
        # fix, this was the only call to `coordinate_family_migration` in
        # this file and it never passed `rng` at all, so every household
        # move here exercised only the deterministic zone-centre fallback
        # `_scatter_location_in_zone` documents for `rng=None` -- the
        # scatter path added for I-12 in FIX BLOCK C (block "migration.py
        # half") had zero coverage from this file.
        rng = get_seeded_rng(sim, tick=50, phase="migration")
        household = coordinate_family_migration(
            family_head, target_zone, tick=50, template=template, rng=rng
        )

        teenager.refresh_from_db()
        if adulthood_age <= 17:
            # 16: a 17-year-old is already an adult under this era --
            # decides independently, never dragged along.
            assert teenager.id not in household
            assert teenager.zone_id == zone.id
        else:
            # 18: a 17-year-old is still a minor under this era -- moves
            # with the family. With a seeded rng supplied, the mover's
            # location must be the SCATTERED point _scatter_location_in_
            # zone draws (two rng.uniform() calls), not target_zone.center
            # exactly -- proving the scatter path itself ran, not merely
            # the zone FK reassignment.
            assert teenager.id in household
            assert teenager.zone_id == target_zone.id
            assert teenager.location.coords != target_zone.center.coords, (
                f"teenager.location={teenager.location.coords} exactly equals "
                f"target_zone.center={target_zone.center.coords} -- the scatter "
                "path (fix I-12) did not run; rng=None's deterministic fallback "
                "did instead"
            )

        # --- MIGRATION PATH, part 2: evaluate_emergency_flight reads this
        # era's flight_trigger_ticks (30/30/20/10/5) -- a fixed
        # consecutive_ticks_under_subsistence=15 clears the trigger for
        # sci_fi/modern_democracy but not for the other three, so the
        # SAME fixture discriminates every era's own declared value. A
        # hand-built zone_stats (own subsistence_threshold key, T039's
        # documented caching contract) avoids needing a Currency/
        # GoodCategory/ZoneEconomy economy scaffold just to prove this
        # one template value is actually read.
        starving_agent = _make_agent(sim, zone, f"{era_name}Starving", wealth=1.0)
        flight_zone_stats = {
            "world": zone.world,
            "government_stability": government.stability,
            "zones": {
                zone.id: {
                    "zone": zone,
                    "wage": 0.0,
                    "unemployment": 0.0,
                    "subsistence_threshold": 100.0,
                },
                target_zone.id: {
                    "zone": target_zone,
                    "wage": 200.0,
                    "unemployment": 0.0,
                    "subsistence_threshold": 0.0,
                },
            },
        }

        flight_target = evaluate_emergency_flight(
            starving_agent,
            sim,
            tick=50,
            template=template,
            zone_stats=flight_zone_stats,
            consecutive_ticks_under_subsistence=15,
        )

        if flight_trigger_ticks <= 15:
            assert flight_target == target_zone
        else:
            assert flight_target is None
