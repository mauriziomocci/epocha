"""Tests for government type configuration data integrity."""
from epocha.apps.world.government_types import GOVERNMENT_TYPES


class TestGovernmentTypesConfig:
    def test_all_12_types_present(self):
        expected = {
            "democracy", "illiberal_democracy", "autocracy", "monarchy",
            "oligarchy", "theocracy", "totalitarian", "terrorist_regime",
            "anarchy", "federation", "kleptocracy", "junta",
        }
        assert set(GOVERNMENT_TYPES.keys()) == expected

    def test_all_types_have_required_fields(self):
        required_fields = {
            "label", "power_source", "legitimacy_base", "repression_tendency",
            "corruption_resistance", "election_enabled", "succession",
            "stability_weights", "institution_effects", "transitions",
        }
        for type_name, config in GOVERNMENT_TYPES.items():
            missing = required_fields - set(config.keys())
            assert not missing, f"{type_name} missing fields: {missing}"

    def test_stability_weights_sum_to_one(self):
        for type_name, config in GOVERNMENT_TYPES.items():
            weights = config["stability_weights"]
            total = weights["economy"] + weights["legitimacy"] + weights["military"]
            assert abs(total - 1.0) < 0.01, f"{type_name} stability weights sum to {total}"

    def test_institution_effects_have_all_7(self):
        institutions = {"justice", "education", "health", "military", "media", "religion", "bureaucracy"}
        for type_name, config in GOVERNMENT_TYPES.items():
            effects = set(config["institution_effects"].keys())
            assert effects == institutions, f"{type_name} missing: {institutions - effects}"

    def test_transitions_reference_valid_types(self):
        valid_types = set(GOVERNMENT_TYPES.keys())
        for type_name, config in GOVERNMENT_TYPES.items():
            for target in config["transitions"]:
                assert target in valid_types, f"{type_name} -> unknown '{target}'"

    def test_repression_tendency_in_range(self):
        for type_name, config in GOVERNMENT_TYPES.items():
            val = config["repression_tendency"]
            assert 0.0 <= val <= 1.0, f"{type_name}: {val}"

    def test_corruption_resistance_in_range(self):
        for type_name, config in GOVERNMENT_TYPES.items():
            val = config["corruption_resistance"]
            assert 0.0 <= val <= 1.0, f"{type_name}: {val}"
