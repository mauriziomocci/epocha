"""Generate world from text input (Input Express)."""


def generate_world_from_prompt(prompt: str, simulation) -> dict:
    """Receives the user's free text, calls the LLM, and builds the world.

    1. Analyze the prompt to determine the type of world
    2. Generate zones, resources, agents via LLM
    3. Create World, Zone, Agent instances in the DB
    4. Return a summary of the generated world
    """
    raise NotImplementedError("To be implemented in MVP")
