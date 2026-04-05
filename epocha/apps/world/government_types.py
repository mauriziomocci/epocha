"""
Data-driven configuration for all government types in the Epocha simulator.

Each entry in GOVERNMENT_TYPES is a parametric dictionary consumed by the government
engine (Task 6), the institution engine (Task 3), and the election system (Task 5).
Adding a new government type requires only a new dictionary entry -- zero code changes.

Scientific grounding:
- Polity IV Project dataset (Marshall & Gurr, 2020): democratic vs autocratic scoring
  and regime transition probabilities. https://www.systemicpeace.org/polityproject.html
- Freedom House (2024) Freedom in the World: repression and civil liberties indicators.
  https://freedomhouse.org/report/freedom-in-the-world
- Acemoglu, D. & Robinson, J.A. (2006). Economic Origins of Dictatorship and Democracy.
  Cambridge University Press. Power concentration and redistribution models.
- Bueno de Mesquita et al. (2003). The Logic of Political Survival. MIT Press.
  Selectorate theory: winning coalition size and institutional incentives.

stability_weights: economy + legitimacy + military must sum to 1.0.
institution_effects: multipliers in (-1.0, 1.0) applied each tick to institution
    output. 0.0 = neutral, positive = boost, negative = suppression.
repression_tendency: 0.0 = no repression, 1.0 = maximum repression.
corruption_resistance: 0.0 = fully corrupt, 1.0 = fully resistant.
"""

GOVERNMENT_TYPES: dict[str, dict] = {
    "democracy": {
        # Polity IV score +10: full democracy. Freedom House: Free.
        "label": "Democracy",
        "power_source": "election",
        "legitimacy_base": "popular",
        "repression_tendency": 0.05,
        "corruption_resistance": 0.70,
        "election_enabled": True,
        "election_manipulated": False,
        "succession": "election",
        "stability_weights": {
            "economy": 0.40,
            "legitimacy": 0.40,
            "military": 0.20,
        },
        "institution_effects": {
            "justice": 0.30,
            "education": 0.25,
            "health": 0.20,
            "military": 0.05,
            "media": 0.35,
            "religion": 0.0,
            "bureaucracy": 0.15,
        },
        "transitions": {
            # Low public trust + high repression -> illiberal drift
            "illiberal_democracy": {"trigger": "low_trust_high_repression"},
            # Very low trust + low military loyalty -> strongman takeover
            "autocracy": {"trigger": "very_low_trust_low_military_loyalty"},
            # State collapse
            "anarchy": {"trigger": "very_low_stability"},
        },
    },

    "illiberal_democracy": {
        # Polity IV scores +1 to +5: semi-democracy with executive dominance.
        # Levitsky & Way (2010): competitive authoritarianism.
        "label": "Illiberal Democracy",
        "power_source": "manipulated_election",
        "legitimacy_base": "facade_popular",
        "repression_tendency": 0.30,
        "corruption_resistance": 0.30,
        "election_enabled": True,
        "election_manipulated": True,
        "succession": "manipulated_election",
        "stability_weights": {
            "economy": 0.30,
            "legitimacy": 0.30,
            "military": 0.40,
        },
        "institution_effects": {
            "justice": -0.25,
            "education": 0.05,
            "health": 0.05,
            "military": 0.15,
            "media": -0.40,
            "religion": 0.0,
            "bureaucracy": -0.10,
        },
        "transitions": {
            # Escalating repression erodes remaining legitimacy
            "autocracy": {"trigger": "high_repression_low_trust"},
            # Reform wave restores institutions
            "democracy": {"trigger": "high_legitimacy_low_corruption"},
            # Collapse
            "anarchy": {"trigger": "very_low_stability"},
        },
    },

    "autocracy": {
        # Polity IV scores -5 to -1: partial autocracy. Personalist rule.
        # Geddes (1999): regime survival through coercive apparatus.
        "label": "Autocracy",
        "power_source": "force",
        "legitimacy_base": "fear_and_loyalty",
        "repression_tendency": 0.60,
        "corruption_resistance": 0.20,
        "election_enabled": False,
        "election_manipulated": False,
        "succession": "strongest_faction",
        "stability_weights": {
            "economy": 0.20,
            "legitimacy": 0.20,
            "military": 0.60,
        },
        "institution_effects": {
            "justice": -0.35,
            "education": -0.20,
            "health": -0.10,
            "military": 0.35,
            "media": -0.45,
            "religion": 0.0,
            "bureaucracy": -0.15,
        },
        "transitions": {
            # Mass protest + military defection -> liberalisation
            "democracy": {"trigger": "high_legitimacy_low_military_loyalty"},
            # Full ideological control apparatus added
            "totalitarian": {"trigger": "very_high_repression"},
            # Military seizes power
            "junta": {"trigger": "very_high_military_loyalty"},
            # Regime collapses without successor
            "anarchy": {"trigger": "very_low_stability"},
        },
    },

    "monarchy": {
        # Traditional monarchies: Polity IV anocracy range.
        # Weber (1922): traditional legitimacy through dynastic continuity.
        "label": "Monarchy",
        "power_source": "inheritance",
        "legitimacy_base": "dynasty",
        "repression_tendency": 0.20,
        "corruption_resistance": 0.40,
        "election_enabled": False,
        "election_manipulated": False,
        "succession": "inheritance",
        "stability_weights": {
            "economy": 0.30,
            "legitimacy": 0.40,
            "military": 0.30,
        },
        "institution_effects": {
            "justice": 0.05,
            "education": 0.0,
            "health": 0.0,
            "military": 0.10,
            "media": 0.0,
            "religion": 0.15,
            "bureaucracy": 0.05,
        },
        "transitions": {
            # Dynasty loses popular standing -> strongman opportunism
            "autocracy": {"trigger": "low_legitimacy_high_repression"},
            # Constitutional reform: monarch grants popular sovereignty
            "democracy": {"trigger": "high_legitimacy_high_trust"},
            # Succession crisis with no heir
            "anarchy": {"trigger": "very_low_stability"},
        },
    },

    "oligarchy": {
        # Elite-capture states. Winters (2011): oligarchy and wealth defence.
        # Acemoglu & Robinson (2006): narrow winning coalition, high redistribution resistance.
        "label": "Oligarchy",
        "power_source": "wealth",
        "legitimacy_base": "wealth",
        "repression_tendency": 0.30,
        "corruption_resistance": 0.15,
        "election_enabled": False,
        "election_manipulated": False,
        "succession": "richest",
        "stability_weights": {
            "economy": 0.50,
            "legitimacy": 0.20,
            "military": 0.30,
        },
        "institution_effects": {
            "justice": -0.30,
            "education": -0.15,
            "health": -0.20,
            "military": 0.10,
            "media": -0.25,
            "religion": 0.0,
            "bureaucracy": -0.20,
        },
        "transitions": {
            # Broad coalition pressure forces elections
            "democracy": {"trigger": "high_legitimacy"},
            # Economic crisis + low military loyalty -> strongman
            "autocracy": {"trigger": "low_stability_low_military_loyalty"},
            # Wealth extraction becomes sole governing logic
            "kleptocracy": {"trigger": "very_high_corruption"},
            "anarchy": {"trigger": "very_low_stability"},
        },
    },

    "theocracy": {
        # Weber (1922): charismatic-rational legitimacy via religious mandate.
        # Fish (2002): Islam and authoritarianism (religion-state fusion patterns).
        "label": "Theocracy",
        "power_source": "religious_authority",
        "legitimacy_base": "divine",
        "repression_tendency": 0.40,
        "corruption_resistance": 0.40,
        "election_enabled": False,
        "election_manipulated": False,
        "succession": "religious_leader",
        "stability_weights": {
            "economy": 0.20,
            "legitimacy": 0.50,
            "military": 0.30,
        },
        "institution_effects": {
            "justice": -0.15,
            "education": -0.30,
            "health": -0.05,
            "military": 0.10,
            "media": -0.35,
            "religion": 0.60,
            "bureaucracy": -0.10,
        },
        "transitions": {
            # Modernisation wave + high civic trust -> secularisation
            "democracy": {"trigger": "high_legitimacy_high_trust"},
            # Legitimacy crisis without secular alternative
            "autocracy": {"trigger": "low_legitimacy"},
            "anarchy": {"trigger": "very_low_stability"},
        },
    },

    "totalitarian": {
        # Polity IV -10: full autocracy with ideological mass mobilisation.
        # Arendt (1951): The Origins of Totalitarianism. Terror as governing mechanism.
        # Linz (2000): distinction from authoritarianism: total penetration of society.
        "label": "Totalitarian",
        "power_source": "force",
        "legitimacy_base": "terror",
        "repression_tendency": 0.90,
        "corruption_resistance": 0.10,
        "election_enabled": False,
        "election_manipulated": False,
        "succession": "strongest_faction",
        "stability_weights": {
            "economy": 0.10,
            "legitimacy": 0.10,
            "military": 0.80,
        },
        "institution_effects": {
            "justice": -0.70,
            "education": -0.50,
            "health": -0.20,
            "military": 0.50,
            "media": -0.80,
            "religion": -0.60,
            "bureaucracy": -0.30,
        },
        "transitions": {
            # Repression apparatus relaxed: liberalisation
            "autocracy": {"trigger": "repression_drops"},
            # State machinery disintegrates under contradictions
            "anarchy": {"trigger": "low_stability_low_military_loyalty"},
        },
    },

    "terrorist_regime": {
        # Extreme case: governance via organised violence with no civic institutions.
        # Cronin (2009): How Terrorism Ends -- regime survival and collapse patterns.
        "label": "Terrorist Regime",
        "power_source": "force",
        "legitimacy_base": "terror",
        "repression_tendency": 0.95,
        "corruption_resistance": 0.05,
        "election_enabled": False,
        "election_manipulated": False,
        "succession": "strongest_faction",
        "stability_weights": {
            "economy": 0.10,
            "legitimacy": 0.10,
            "military": 0.80,
        },
        "institution_effects": {
            "justice": -0.90,
            "education": -0.80,
            "health": -0.70,
            "military": 0.30,
            "media": -0.95,
            "religion": -0.40,
            "bureaucracy": -0.90,
        },
        "transitions": {
            # External pressure or internal power consolidation -> stable autocracy
            "autocracy": {"trigger": "stability_rises"},
            # Complete disintegration of authority
            "anarchy": {"trigger": "stability_falls"},
        },
    },

    "anarchy": {
        # Absence of central authority. Hobbes (1651): war of all against all.
        # Kalyvas (2006): The Logic of Violence in Civil War -- power vacuum dynamics.
        "label": "Anarchy",
        "power_source": "none",
        "legitimacy_base": "none",
        "repression_tendency": 0.0,
        "corruption_resistance": 0.0,
        "election_enabled": False,
        "election_manipulated": False,
        "succession": "none",
        "stability_weights": {
            "economy": 0.50,
            "legitimacy": 0.30,
            "military": 0.20,
        },
        "institution_effects": {
            "justice": -0.80,
            "education": -0.70,
            "health": -0.60,
            "military": -0.50,
            "media": -0.60,
            "religion": -0.20,
            "bureaucracy": -0.90,
        },
        "transitions": {
            # Warlord consolidates enough territory to enforce order
            "autocracy": {"trigger": "stability_rises"},
            # Civic reconstruction with broad legitimacy
            "democracy": {"trigger": "high_trust_high_legitimacy"},
            # Military faction fills power vacuum
            "junta": {"trigger": "high_military_loyalty"},
        },
    },

    "federation": {
        # Multi-unit democratic federalism. Riker (1964): Federalism: Origin, Operation, Significance.
        # Stability derived from distributed power centres and inter-unit bargaining.
        "label": "Federation",
        "power_source": "election",
        "legitimacy_base": "mutual_benefit",
        "repression_tendency": 0.05,
        "corruption_resistance": 0.50,
        "election_enabled": True,
        "election_manipulated": False,
        "succession": "election",
        "stability_weights": {
            "economy": 0.40,
            "legitimacy": 0.40,
            "military": 0.20,
        },
        "institution_effects": {
            "justice": 0.20,
            "education": 0.20,
            "health": 0.15,
            "military": 0.05,
            "media": 0.15,
            "religion": 0.0,
            "bureaucracy": 0.30,
        },
        "transitions": {
            # Federal compact breaks under centrifugal forces
            "anarchy": {"trigger": "low_stability"},
            # Units consolidate into unitary democracy
            "democracy": {"trigger": "high_trust"},
            # Central authority captures federal apparatus
            "autocracy": {"trigger": "low_stability_low_military_loyalty"},
        },
    },

    "kleptocracy": {
        # Rose-Ackerman & Palifka (2016): Corruption and Government.
        # Theft-as-governance: ruling class extracts rents with minimal service provision.
        "label": "Kleptocracy",
        "power_source": "wealth",
        "legitimacy_base": "theft",
        "repression_tendency": 0.40,
        "corruption_resistance": 0.0,
        "election_enabled": False,
        "election_manipulated": False,
        "succession": "richest",
        "stability_weights": {
            "economy": 0.40,
            "legitimacy": 0.20,
            "military": 0.40,
        },
        "institution_effects": {
            "justice": -0.80,
            "education": -0.40,
            "health": -0.35,
            "military": 0.10,
            "media": -0.70,
            "religion": -0.10,
            "bureaucracy": -0.75,
        },
        "transitions": {
            # Complete economic collapse with no enforcement capacity
            "anarchy": {"trigger": "very_low_stability"},
            # Military fills void left by discredited civilian kleptocrats
            "autocracy": {"trigger": "high_military_loyalty"},
            # External pressure + internal reform coalition
            "democracy": {"trigger": "high_legitimacy_low_corruption"},
        },
    },

    "junta": {
        # Finer (1962): The Man on Horseback -- military intervention typology.
        # Geddes (1999): military regime survival: collegiate vs. personalist dynamics.
        "label": "Military Junta",
        "power_source": "military",
        "legitimacy_base": "military_force",
        "repression_tendency": 0.50,
        "corruption_resistance": 0.25,
        "election_enabled": False,
        "election_manipulated": False,
        "succession": "military_leader",
        "stability_weights": {
            "economy": 0.20,
            "legitimacy": 0.10,
            "military": 0.70,
        },
        "institution_effects": {
            "justice": -0.30,
            "education": -0.10,
            "health": -0.05,
            "military": 0.55,
            "media": -0.40,
            "religion": 0.0,
            "bureaucracy": -0.15,
        },
        "transitions": {
            # Military loses cohesion or splits along factional lines
            "autocracy": {"trigger": "military_loyalty_drops"},
            # Controlled transition: junta hands power to elected government
            "democracy": {"trigger": "high_legitimacy_high_trust"},
            # Institutional disintegration beyond military's ability to control
            "anarchy": {"trigger": "very_low_stability"},
        },
    },
}
