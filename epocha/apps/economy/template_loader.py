"""Economy template loader with four pre-configured era templates.

Templates define the complete economic configuration for a simulation.
Each template is scientifically grounded for its era; see the inline
source citations for calibration notes.

The loader is idempotent: calling load_default_templates() multiple
times creates the templates once (via get_or_create).
"""

from __future__ import annotations

from .models import EconomyTemplate

TEMPLATE_NAMES = (
    "pre_industrial",
    "industrial",
    "modern",
    "sci_fi",
)

# Goods configuration shared across all templates (5 categories).
# Elasticities vary by era.
_GOODS_BASE = [
    {
        "code": "subsistence",
        "name": "Subsistence goods",
        "is_essential": True,
        # Houthakker & Taylor (1970); food elasticity ~0.2-0.5
        "price_elasticity": 0.3,
    },
    {
        "code": "materials",
        "name": "Raw materials",
        "is_essential": False,
        "price_elasticity": 0.7,
    },
    {
        "code": "manufacture",
        "name": "Manufactured goods",
        "is_essential": False,
        "price_elasticity": 1.2,
    },
    {
        "code": "luxury",
        "name": "Luxury goods",
        "is_essential": False,
        # Andreyeva et al. (2010); luxury elasticity ~1.5-2.5
        "price_elasticity": 2.0,
    },
    {
        "code": "services",
        "name": "Services",
        "is_essential": False,
        "price_elasticity": 0.9,
    },
]

_FACTORS_BASE = [
    {"code": "labor", "name": "Labor"},
    {"code": "capital", "name": "Capital"},
    {"code": "natural_resources", "name": "Natural Resources"},
    {"code": "knowledge", "name": "Knowledge"},
]

_PROPERTIES_BASE = [
    {
        "code": "land",
        "name": "Farmland",
        "base_value": 200,
        "production_bonus": {"subsistence": 1.5},
    },
    {
        "code": "workshop",
        "name": "Workshop",
        "base_value": 150,
        "production_bonus": {"manufacture": 1.3},
    },
    {
        "code": "shop",
        "name": "Shop",
        "base_value": 100,
        "production_bonus": {"services": 1.2},
    },
]

_ZONE_TYPE_RESOURCES = {
    "rural": {"natural_resources": 1.5, "labor": 0.8},
    "urban": {
        "natural_resources": 0.3,
        "capital": 1.5,
        "knowledge": 1.2,
    },
    "commercial": {"capital": 1.3, "knowledge": 1.0},
    "industrial": {"capital": 1.8, "natural_resources": 0.5},
    "wilderness": {"natural_resources": 2.0, "labor": 0.3},
}

_ROLE_PRODUCTION = {
    "farmer": {"good": "subsistence", "skill_weight": 1.2},
    "blacksmith": {"good": "materials", "skill_weight": 1.3},
    "craftsman": {"good": "manufacture", "skill_weight": 1.1},
    "merchant": {"good": "services", "skill_weight": 1.0},
    "priest": {"good": "services", "skill_weight": 0.8},
}

_FACTORY_PROPERTY = {
    "code": "factory",
    "name": "Factory",
    "base_value": 500,
    "production_bonus": {"manufacture": 2.0},
}

_OFFICE_PROPERTY = {
    "code": "office",
    "name": "Office",
    "base_value": 300,
    "production_bonus": {"services": 1.5},
}


# Expropriation policies by government type.
# Democracies and rule-of-law regimes: no expropriation.
# Autocratic/kleptocratic regimes: elite seizure (selective confiscation).
# Totalitarian regimes: nationalize all private property.
# Based on Acemoglu & Robinson (2012), Why Nations Fail, chapters 3-4:
# extractive institutions concentrate wealth through expropriation,
# inclusive institutions protect property rights.
_EXPROPRIATION_BY_GOVERNMENT = {
    "democracy": "none",
    "monarchy": "none",
    "federation": "none",
    "illiberal_democracy": "none",
    "oligarchy": "none",
    "theocracy": "none",
    "autocracy": "elite_seizure",
    "terrorist_regime": "elite_seizure",
    "kleptocracy": "elite_seizure",
    "junta": "elite_seizure",
    "totalitarian": "nationalize_all",
}


def _behavioral_config(
    loan_to_value: float,
    interest: float,
    deposits: float,
    reserve: float = 0.10,
) -> dict:
    """Return behavioral economy configuration for a template.

    Parameters are era-specific calibrations for the credit, banking,
    expectations, and expropriation subsystems introduced in Spec 2 Part 1.

    Args:
        loan_to_value: Maximum loan-to-value ratio for collateralized loans.
            Pre-industrial ~0.5 (limited credit markets), modern ~0.8
            (developed mortgage markets). Tunable design parameter.
        interest: Base interest rate per tick. Historical ranges: pre-modern
            5-10% (Homer & Sylla 2005, A History of Interest Rates), modern
            2-5%. Tunable design parameter.
        deposits: Initial banking system deposits in primary currency.
            Scaled to match the era's money supply. Tunable design parameter.
        reserve: Reserve ratio. Pre-modern banking ~10% (no formal
            regulation), modern regulated ~3-5% (Basel III). Tunable
            design parameter.
    """
    return {
        "credit_config": {
            "loan_to_value": loan_to_value,
            "max_rollover": 3,
            "default_loan_duration_ticks": 20,
        },
        "banking_config": {
            "initial_deposits": deposits,
            "base_interest_rate": interest,
            "reserve_ratio": reserve,
        },
        "expectations_config": {
            # Nerlove (1958) base lambda: 0.3 is a moderate adaptation
            # speed. Personality modulation (Costa & McCrae 1992) adjusts
            # this per-agent. Tunable design parameter.
            "lambda_base": 0.3,
            # Big Five modulation coefficients for lambda_rate.
            # Positive means trait increases adaptation speed.
            # Tunable design parameters -- directional effects from
            # Costa & McCrae (1992), magnitudes are calibrated for
            # the [0.05, 0.95] output range.
            "neuroticism_mod": 0.15,
            "openness_mod": 0.10,
            "conscientiousness_mod": 0.10,
            # Trend detection threshold: price must differ by more
            # than this fraction to be classified as rising/falling.
            # Tunable design parameter.
            "trend_threshold": 0.05,
        },
        "expropriation_policies": _EXPROPRIATION_BY_GOVERNMENT,
    }


def _pre_industrial_template() -> dict:
    """Pre-industrial: agricultural, artisanal, feudal property.

    CES sigma 0.5: low factor substitutability, consistent with
    Antras (2004) estimates for pre-modern economies.
    """
    # Pre-industrial credit: informal lending, high rates, low LTV.
    # Homer & Sylla (2005): pre-modern rates 5-10%.
    behavioral = _behavioral_config(
        loan_to_value=0.5,
        interest=0.08,
        deposits=5000.0,
    )
    return {
        "description": (
            "Agricultural economy with artisanal production,"
            " limited trade, feudal property."
        ),
        "era_label": "Pre-Industrial (1400-1800)",
        "goods_config": [
            {**g, "base_price": p}
            for g, p in zip(_GOODS_BASE, [3.0, 5.0, 12.0, 50.0, 8.0])
        ],
        "factors_config": _FACTORS_BASE,
        "currencies_config": [
            {
                "code": "LVR",
                "name": "Livre tournois",
                "symbol": "L",
                "initial_supply": 50000.0,
            },
        ],
        "production_config": {
            # CES sigma 0.5: low substitutability (Antras 2004)
            "default_sigma": 0.5,
            # default_scale: reduced from the implicit 5.0-10.0 range.
            # With scale=5.0 and typical factor inputs, a single farmer
            # produces ~5 units/tick -- enough to flood a 4-agent market.
            # Scale=2.0 yields ~2 units/tick, keeping supply/demand ratios
            # reasonable in small simulations. Tunable design parameter.
            "default_scale": 2.0,
            "role_production": _ROLE_PRODUCTION,
            "zone_type_resources": _ZONE_TYPE_RESOURCES,
        },
        "tax_config": {
            # Approximates the dime royale (~10-15%)
            "income_tax_rate": 0.15,
        },
        "properties_config": {"types": _PROPERTIES_BASE},
        "initial_distribution": {
            "wealth_range": {
                "elite": [300, 500],
                "middle": [50, 150],
                "poor": [5, 30],
            },
            "property_ownership": "class_based",
        },
        "config": behavioral,
    }


def _industrial_template() -> dict:
    """Industrial: factories, growing trade, emerging labor market.

    CES sigma 0.8: moderate factor substitutability, reflecting
    early mechanization where labor and capital are becoming more
    interchangeable but not yet fully so.
    """
    # Industrial credit: formalized banking, moderate rates.
    # Homer & Sylla (2005): 19th century rates 4-8%.
    behavioral = _behavioral_config(
        loan_to_value=0.6,
        interest=0.06,
        deposits=20000.0,
    )
    return {
        "description": (
            "Industrializing economy with factories,"
            " growing trade, emerging labor market."
        ),
        "era_label": "Industrial (1800-1950)",
        "goods_config": [
            {**g, "base_price": p}
            for g, p in zip(_GOODS_BASE, [2.0, 4.0, 8.0, 30.0, 6.0])
        ],
        "factors_config": _FACTORS_BASE,
        "currencies_config": [
            {
                "code": "GBP",
                "name": "Pound sterling",
                "symbol": "\u00a3",
                "initial_supply": 100000.0,
            },
        ],
        "production_config": {
            "default_sigma": 0.8,
            "role_production": _ROLE_PRODUCTION,
            "zone_type_resources": _ZONE_TYPE_RESOURCES,
        },
        "tax_config": {"income_tax_rate": 0.20},
        "properties_config": {
            "types": _PROPERTIES_BASE + [_FACTORY_PROPERTY],
        },
        "initial_distribution": {
            "wealth_range": {
                "elite": [500, 1000],
                "middle": [100, 300],
                "poor": [10, 50],
            },
            "property_ownership": "class_based",
        },
        "config": behavioral,
    }


def _modern_template() -> dict:
    """Modern: service-dominant, high tech, complex taxation.

    CES sigma 1.2: high factor substitutability, consistent with
    Karabarbounis & Neiman (2014) for the post-1950 period.
    """
    # Modern credit: developed financial markets, low rates, Basel III reserves.
    # Post-2008 central bank rates 1-3%.
    behavioral = _behavioral_config(
        loan_to_value=0.8,
        interest=0.03,
        deposits=100000.0,
        reserve=0.05,
    )
    return {
        "description": (
            "Service-dominant economy with high technology,"
            " global trade, complex taxation."
        ),
        "era_label": "Modern (1950-present)",
        "goods_config": [
            {**g, "base_price": p}
            for g, p in zip(_GOODS_BASE, [5.0, 10.0, 20.0, 100.0, 15.0])
        ],
        "factors_config": _FACTORS_BASE,
        "currencies_config": [
            {
                "code": "USD",
                "name": "US Dollar",
                "symbol": "$",
                "initial_supply": 500000.0,
            },
        ],
        "production_config": {
            # CES sigma 1.2: high substitutability
            # (Karabarbounis & Neiman 2014)
            "default_sigma": 1.2,
            "role_production": _ROLE_PRODUCTION,
            "zone_type_resources": _ZONE_TYPE_RESOURCES,
        },
        "tax_config": {"income_tax_rate": 0.30},
        "properties_config": {
            "types": _PROPERTIES_BASE
            + [
                _FACTORY_PROPERTY,
                _OFFICE_PROPERTY,
            ],
        },
        "initial_distribution": {
            "wealth_range": {
                "elite": [1000, 5000],
                "middle": [200, 800],
                "poor": [20, 100],
            },
            "property_ownership": "class_based",
        },
        "config": behavioral,
    }


def _sci_fi_template() -> dict:
    """Sci-fi: knowledge-dominant, advanced technology.

    CES sigma 1.5: speculative extrapolation of the historical
    trend toward higher substitutability. No empirical basis --
    this is a design parameter for gameplay purposes.
    """
    # Sci-fi credit: highly developed financial system, very low rates,
    # minimal reserves. Speculative extrapolation, no empirical basis.
    behavioral = _behavioral_config(
        loan_to_value=0.9,
        interest=0.02,
        deposits=500000.0,
        reserve=0.03,
    )
    return {
        "description": (
            "Knowledge-dominant economy with advanced"
            " technology, interstellar trade potential."
        ),
        "era_label": "Science Fiction / Future",
        "goods_config": [
            {**g, "base_price": p}
            for g, p in zip(_GOODS_BASE, [10.0, 20.0, 50.0, 200.0, 30.0])
        ],
        "factors_config": _FACTORS_BASE,
        "currencies_config": [
            {
                "code": "CRD",
                "name": "Galactic Credit",
                "symbol": "Cr",
                "initial_supply": 1000000.0,
            },
        ],
        "production_config": {
            # CES sigma 1.5: speculative extrapolation,
            # no empirical basis
            "default_sigma": 1.5,
            "role_production": _ROLE_PRODUCTION,
            "zone_type_resources": _ZONE_TYPE_RESOURCES,
        },
        "tax_config": {"income_tax_rate": 0.25},
        "properties_config": {
            "types": _PROPERTIES_BASE
            + [
                {
                    "code": "factory",
                    "name": "Automated Factory",
                    "base_value": 1000,
                    "production_bonus": {"manufacture": 3.0},
                },
                {
                    "code": "lab",
                    "name": "Research Lab",
                    "base_value": 800,
                    "production_bonus": {"services": 2.0},
                },
            ],
        },
        "initial_distribution": {
            "wealth_range": {
                "elite": [5000, 20000],
                "middle": [500, 2000],
                "poor": [50, 300],
            },
            "property_ownership": "class_based",
        },
        "config": behavioral,
    }


_TEMPLATE_BUILDERS = {
    "pre_industrial": _pre_industrial_template,
    "industrial": _industrial_template,
    "modern": _modern_template,
    "sci_fi": _sci_fi_template,
}


def load_default_templates() -> None:
    """Load the four default economy templates into the database.

    Idempotent: existing templates are not overwritten for their
    base fields. However, if an existing template lacks the
    behavioral config keys (credit_config, banking_config,
    expectations_config, expropriation_policies), the config
    field is updated to include them. This ensures backward
    compatibility with templates created before Spec 2 Part 1.
    """
    for name, builder in _TEMPLATE_BUILDERS.items():
        data = builder()
        behavioral_config = data.get("config", {})
        template, created = EconomyTemplate.objects.get_or_create(
            name=name,
            defaults={
                "description": data["description"],
                "era_label": data["era_label"],
                "goods_config": data["goods_config"],
                "factors_config": data["factors_config"],
                "currencies_config": data["currencies_config"],
                "production_config": data["production_config"],
                "tax_config": data["tax_config"],
                "properties_config": data["properties_config"],
                "initial_distribution": data["initial_distribution"],
                "config": behavioral_config,
            },
        )
        if not created and "credit_config" not in (template.config or {}):
            # Existing template missing behavioral config -- backfill it.
            existing_config = template.config or {}
            existing_config.update(behavioral_config)
            template.config = existing_config
            template.save(update_fields=["config"])


def get_template(name: str) -> EconomyTemplate:
    """Retrieve a template by name.

    Raises EconomyTemplate.DoesNotExist if not found.
    """
    return EconomyTemplate.objects.get(name=name)
