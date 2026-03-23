"""Decision pipeline: context -> prompt -> LLM -> action."""


def process_agent_decision(agent, world_state, tick):
    """Complete pipeline for an agent decision.

    1. Gather context (world state, memories, relationships)
    2. Build prompt with the agent's personality
    3. Call LLM via llm_adapter
    4. Parse response into a concrete action
    5. Log the decision in DecisionLog
    """
    raise NotImplementedError("To be implemented in MVP")
