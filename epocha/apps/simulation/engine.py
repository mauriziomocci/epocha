"""Tick logic: advance time, coordinate modules."""


class SimulationEngine:
    """Simulation cycle orchestrator.

    For each tick:
    1. Update world state (economy, resources)
    2. Process agent decisions
    3. Propagate consequences
    4. Record events
    5. Advance tick counter
    """

    def __init__(self, simulation):
        self.simulation = simulation

    def run_tick(self):
        """Execute a single simulation tick."""
        raise NotImplementedError("To be implemented in MVP")
