"""Seeded RNG derivation for the economy app.

Mirrors the derivation scheme of epocha/apps/demography/rng.py (the
project's canonical per-simulation, per-tick, per-phase RNG helper):
sha256 over "{simulation_id}:{seed}:{tick}:{phase}", first 8 bytes as
the derived seed. Duplicated here rather than imported because the
economy app must not depend on the demography domain app for a generic
utility; consolidating both into epocha/common is a recorded future
refactor (R6-RNG-1, Round 6 re-audit).

Every stochastic decision in the economy app draws from an RNG
returned by this helper, never from the module-global random -- the
whitepaper 3.4 reproducibility contract requires identically-seeded
runs to produce identical state, and the global RNG's stream depends
on every prior consumer anywhere in the process.
"""

from __future__ import annotations

import hashlib
import random

# Phases with a reserved derivation label. Adding a phase is cheap;
# the guard exists so two call sites cannot silently share a stream.
ALLOWED_PHASES = {
    "initialization",
    "banking_concern",
}


def get_seeded_rng(simulation, tick: int, phase: str) -> random.Random:
    """Return a per-simulation, per-tick, per-phase seeded RNG.

    Args:
        simulation: the Simulation instance (provides .seed and .id).
        tick: the current tick (0 for initialization-time draws).
        phase: one of ALLOWED_PHASES.

    Raises:
        ValueError: when phase is not in ALLOWED_PHASES.
    """
    if phase not in ALLOWED_PHASES:
        raise ValueError(
            f"Unknown economy RNG phase {phase!r}; must be one of {sorted(ALLOWED_PHASES)}"
        )
    base_seed = simulation.seed or 0
    simulation_id = getattr(simulation, "id", 0) or 0
    key = f"{simulation_id}:{base_seed}:{tick}:{phase}".encode()
    digest = hashlib.sha256(key).digest()
    derived_seed = int.from_bytes(digest[:8], "big")
    return random.Random(derived_seed)
