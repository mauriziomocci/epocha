"""Seeded RNG streams per demography subsystem for publication-grade reproducibility.

Each subsystem (mortality, fertility, couple, migration, inheritance,
initialization) gets an independent RNG stream derived from a
deterministic hash of (simulation.seed, tick, phase). Reordering or
suppressing one subsystem does not shift the RNG sequence of others,
which is essential for reproducibility across refactors.
"""
from __future__ import annotations

import hashlib
import random

ALLOWED_PHASES = {
    "mortality",
    "fertility",
    "couple",
    "migration",
    "inheritance",
    "initialization",
}


def get_seeded_rng(simulation, tick: int, phase: str) -> random.Random:
    """Return a per-simulation, per-tick, per-phase seeded RNG.

    Args:
        simulation: the Simulation instance (provides .seed and .id).
        tick: the current tick.
        phase: one of ALLOWED_PHASES.

    Raises:
        ValueError: when phase is not in ALLOWED_PHASES.
    """
    if phase not in ALLOWED_PHASES:
        raise ValueError(
            f"Unknown demography RNG phase {phase!r}; must be one of {sorted(ALLOWED_PHASES)}"
        )
    base_seed = simulation.seed or 0
    simulation_id = getattr(simulation, "id", 0) or 0
    key = f"{simulation_id}:{base_seed}:{tick}:{phase}".encode("utf-8")
    digest = hashlib.sha256(key).digest()
    derived_seed = int.from_bytes(digest[:8], "big")
    return random.Random(derived_seed)
