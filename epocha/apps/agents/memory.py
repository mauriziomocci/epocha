"""Agent memory management — read, write, decay."""


def get_relevant_memories(agent, current_tick, max_memories=10):
    """Retrieve the most relevant memories for the current context."""
    raise NotImplementedError("To be implemented in MVP")


def decay_memories(agent, current_tick):
    """Apply decay to memories based on emotional weight and time."""
    raise NotImplementedError("To be implemented in MVP")
