"""Tests for canonical name normalization."""
import pytest

from epocha.apps.knowledge.normalizer import (
    normalize_canonical_name,
    name_contained_in_passage,
)


class TestNormalize:
    def test_lowercase(self):
        assert normalize_canonical_name("Robespierre") == "robespierre"

    def test_strip_accents_french(self):
        assert normalize_canonical_name("Déclaration") == "declaration"

    def test_strip_accents_italian(self):
        assert normalize_canonical_name("Libertà") == "liberta"

    def test_strip_accents_german(self):
        assert normalize_canonical_name("Brüder") == "bruder"

    def test_strip_honorific_m(self):
        assert normalize_canonical_name("M. Robespierre") == "robespierre"

    def test_strip_honorific_dr(self):
        assert normalize_canonical_name("Dr. Marat") == "marat"

    def test_strip_honorific_mme(self):
        assert normalize_canonical_name("Mme. Roland") == "roland"

    def test_strip_honorific_citoyen(self):
        assert normalize_canonical_name("Citoyen Robespierre") == "robespierre"
        assert normalize_canonical_name("Citoyenne Roland") == "roland"

    def test_collapse_whitespace(self):
        assert normalize_canonical_name("Louis   XVI") == "louis xvi"

    def test_trim(self):
        assert normalize_canonical_name("  Danton  ") == "danton"

    def test_empty_string(self):
        assert normalize_canonical_name("") == ""

    def test_single_char(self):
        assert normalize_canonical_name("A") == "a"

    def test_all_caps(self):
        assert normalize_canonical_name("VERSAILLES") == "versailles"


class TestNameContained:
    def test_exact_match(self):
        assert name_contained_in_passage(
            "Robespierre", "Robespierre spoke to the assembly."
        ) is True

    def test_accent_insensitive(self):
        assert name_contained_in_passage(
            "Déclaration", "The declaration was read aloud."
        ) is True

    def test_case_insensitive(self):
        assert name_contained_in_passage(
            "ROBESPIERRE", "Robespierre spoke."
        ) is True

    def test_not_present(self):
        assert name_contained_in_passage(
            "Danton", "Robespierre spoke to the assembly."
        ) is False

    def test_partial_match_within_word(self):
        # "Paris" inside "Parisian" should still count as contained
        assert name_contained_in_passage(
            "Paris", "The Parisian crowds gathered."
        ) is True

    def test_empty_passage(self):
        assert name_contained_in_passage("Robespierre", "") is False

    def test_empty_name(self):
        assert name_contained_in_passage("", "some passage") is False
