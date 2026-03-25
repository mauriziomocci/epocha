# Epocha MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a working civilization simulator where a user types a prompt, a world with 20-50 AI agents is generated, the simulation runs with tick-based time, and the user can chat with any agent.

**Architecture:** Django/DRF API backend with Celery for async agent processing, Django Channels for WebSocket real-time updates, and a single OpenAI-compatible LLM provider for agent decisions and world generation. Frontend is NOT part of this MVP plan — we build and validate the backend first via API and tests.

**Tech Stack:** Django 5.x, DRF, Django Channels, Celery + Redis, PostgreSQL, OpenAI-compatible API

**Spec:** `docs/superpowers/specs/2026-03-22-epocha-design.md` (MVP section)

---

## LLM Provider Setup

The MVP uses a single provider via the OpenAI SDK with configurable `base_url`, making it compatible with multiple providers without code changes.

### Recommended provider for development: Google Gemini (free)

All Gemini models have a free tier with 1000 requests/day — more than enough for MVP testing.

| Model | Input/1M tokens | Output/1M tokens | Best for |
|-------|----------------|------------------|----------|
| `gemini-2.5-flash-lite` | Free / $0.10 | Free / $0.40 | Agent decisions (fast, cheap) |
| `gemini-2.5-flash` | Free / $0.30 | Free / $2.50 | World generation (more capable) |
| `gemini-2.5-pro` | Free / $1.25 | Free / $10.00 | Complex reasoning (most powerful) |

**Free tier limits:** 30 req/min, 1000 req/day, 1M tokens/min.

**Setup:** Get a free API key from [Google AI Studio](https://aistudio.google.com/apikey) and configure `.envs/.local/.django`:

```
EPOCHA_LLM_PROVIDER=openai
EPOCHA_LLM_API_KEY=your-gemini-api-key
EPOCHA_LLM_MODEL=gemini-2.5-flash-lite
EPOCHA_LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
```

### Alternative providers (all OpenAI SDK compatible)

Switch provider by changing only `.env` variables — no code changes needed:

| Provider | `EPOCHA_LLM_BASE_URL` | Recommended model | Free tier |
|----------|----------------------|-------------------|-----------|
| Google Gemini | `https://generativelanguage.googleapis.com/v1beta/openai/` | `gemini-2.5-flash-lite` | 1000 req/day |
| Groq | `https://api.groq.com/openai/v1` | `llama-3.1-8b-instant` | Limited |
| OpenRouter | `https://openrouter.ai/api/v1` | Free models available | 200 req/day |
| OpenAI | *(leave empty)* | `gpt-4o-mini` | $5 initial credits |
| Together AI | `https://api.together.xyz/v1` | Various | Initial credits |
| Mistral | `https://api.mistral.ai/v1` | `mistral-small-latest` | No |

### Capacity estimate for MVP testing

With 20 agents and Gemini free tier (1000 req/day):
- World generation: ~1 request
- Per tick: ~20 requests (1 per agent)
- **~50 ticks per day** within free limits
- Chat with agents: additional requests (budget ~100/day for chat)

This is sufficient for development and testing. For longer simulations, upgrade to paid tier or switch to a provider with higher limits.

---

## Input Formats

The Express endpoint accepts multiple input formats. The system extracts text from any format and passes it to the LLM for world generation.

### Supported formats (MVP)

| Format | How it works | Example use case |
|--------|-------------|-----------------|
| **Text** (POST body) | Direct text in the API request | "A medieval village with 30 people" |
| **Markdown** (.md upload) | Parsed as-is, structure preserved | Worldbuilding document, scenario description |
| **PDF** (.pdf upload) | Text extracted via PyMuPDF | History book chapter, academic paper, news article |
| **Plain text** (.txt upload) | Read as-is | Notes, story outlines |
| **URL** (link in prompt) | Page content fetched and extracted | News article, Wikipedia page, report |

### API usage

```bash
# Text input (existing)
curl -X POST http://localhost:8000/api/v1/simulations/express/ \
  -H "Authorization: Bearer <token>" \
  -d '{"prompt": "A medieval village with 30 people"}'

# File upload (PDF, MD, TXT)
curl -X POST http://localhost:8000/api/v1/simulations/express/ \
  -H "Authorization: Bearer <token>" \
  -F "file=@chapter3-roman-empire.pdf" \
  -F "prompt=Simulate this historical period for 200 years"

# URL input
curl -X POST http://localhost:8000/api/v1/simulations/express/ \
  -H "Authorization: Bearer <token>" \
  -d '{"prompt": "Simulate the scenario described here", "url": "https://example.com/article"}'
```

The optional `prompt` field alongside a file/URL lets the user add instructions:
- "Focus on the economic aspects"
- "Simulate for 500 years"
- "Add a revolutionary leader after 50 years"

### Implementation requirements

**Additional dependency:** `PyMuPDF` (already in requirements/base.txt as `pymupdf`) for PDF parsing.

### Processing pipeline

```
Input (text / file / URL)
    ↓
Parser (format-specific)
    - PDF → PyMuPDF → extracted text
    - MD → read as-is
    - TXT → read as-is
    - URL → fetch page → extract text (BeautifulSoup or similar)
    ↓
Combined text (extracted content + user prompt)
    ↓
LLM analyzes and generates world JSON
    ↓
World, Zones, Agents created in DB
```

---

## File Map

### Files to implement (existing placeholders → real code)

| File | Responsibility |
|------|---------------|
| `epocha/apps/llm_adapter/providers/openai.py` | OpenAI API calls via SDK |
| `epocha/apps/llm_adapter/client.py` | Provider factory (already implemented, no changes needed) |
| `epocha/apps/llm_adapter/rate_limiter.py` | Redis-based rate limiting |
| `epocha/apps/llm_adapter/models.py` | LLMRequest log (already defined) |
| `epocha/apps/agents/personality.py` | Build personality prompt from traits |
| `epocha/apps/agents/memory.py` | Memory retrieval and decay |
| `epocha/apps/agents/decision.py` | Agent decision pipeline |
| `epocha/apps/agents/tasks.py` | Celery task for agent turn |
| `epocha/apps/world/generator.py` | World generation from prompt |
| `epocha/apps/world/economy.py` | Basic economy tick processing |
| `epocha/apps/simulation/engine.py` | Tick orchestrator |
| `epocha/apps/simulation/tasks.py` | Celery tasks for simulation loop |
| `epocha/apps/simulation/views.py` | Express endpoint (connect generator) |
| `epocha/apps/chat/consumers.py` | WebSocket chat with agents |
| `epocha/apps/chat/tasks.py` | Agent response generation |

### Test files to create

| File | Tests for |
|------|-----------|
| `epocha/apps/llm_adapter/tests/test_client.py` | Provider factory, mock LLM calls |
| `epocha/apps/llm_adapter/tests/test_rate_limiter.py` | Rate limiting logic |
| `epocha/apps/agents/tests/test_personality.py` | Personality prompt building |
| `epocha/apps/agents/tests/test_memory.py` | Memory retrieval and decay |
| `epocha/apps/agents/tests/test_decision.py` | Decision pipeline (mocked LLM) |
| `epocha/apps/world/tests/test_generator.py` | World generation (mocked LLM) |
| `epocha/apps/world/tests/test_economy.py` | Economy tick |
| `epocha/apps/simulation/tests/test_engine.py` | Tick orchestration |
| `epocha/apps/simulation/tests/test_api.py` | API endpoints |
| `epocha/apps/chat/tests/test_consumers.py` | WebSocket chat |

---

## Task 0: Database Migrations (prerequisite for all DB tests)

All subsequent tasks with `@pytest.mark.django_db` require tables to exist.

**Files:**
- Generate: all migration files in `*/migrations/`

- [ ] **Step 1: Generate all migrations**

```bash
python manage.py makemigrations users simulation agents world chat llm_adapter
```

- [ ] **Step 2: Verify migrations apply cleanly**

```bash
python manage.py migrate
```
Expected: All migrations applied without errors

- [ ] **Step 3: Commit**

```bash
git add */migrations/
git commit -m "feat: generate initial database migrations for all apps"
```

---

## Task 1: LLM Adapter — OpenAI Provider

The LLM adapter is the foundation. Everything else depends on it.

**Files:**
- Modify: `epocha/apps/llm_adapter/providers/openai.py`
- Modify: `epocha/apps/llm_adapter/client.py` (add base_url support)
- Modify: `config/settings/base.py` (add EPOCHA_LLM_BASE_URL setting)
- Modify: `.envs/.local/.django` (add EPOCHA_LLM_BASE_URL)
- Create: `epocha/apps/llm_adapter/tests/test_client.py`

- [ ] **Step 1: Write the failing test for OpenAI provider**

```python
# epocha/apps/llm_adapter/tests/test_client.py
from unittest.mock import MagicMock, patch

import pytest

from epocha.apps.llm_adapter.client import get_llm_client
from epocha.apps.llm_adapter.providers.openai import OpenAIProvider


class TestOpenAIProvider:
    def test_complete_returns_string(self):
        """Provider.complete() should return a string response."""
        provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")

        with patch.object(provider, "_call_api") as mock_api:
            mock_api.return_value = {
                "content": "Hello, I am an AI.",
                "input_tokens": 10,
                "output_tokens": 5,
            }
            result = provider.complete(
                prompt="Say hello",
                system_prompt="You are helpful",
            )

        assert isinstance(result, str)
        assert result == "Hello, I am an AI."

    def test_get_cost_calculates_correctly(self):
        """Cost should be calculated from token counts."""
        provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")
        cost = provider.get_cost(input_tokens=1000, output_tokens=500)
        assert cost > 0
        assert isinstance(cost, float)

    def test_get_model_name(self):
        provider = OpenAIProvider(api_key="test-key", model="gpt-4o-mini")
        assert provider.get_model_name() == "gpt-4o-mini"


class TestGetLLMClient:
    @pytest.mark.django_db
    def test_returns_openai_provider(self, settings):
        settings.EPOCHA_DEFAULT_LLM_PROVIDER = "openai"
        settings.EPOCHA_LLM_API_KEY = "test-key"
        settings.EPOCHA_LLM_MODEL = "gpt-4o-mini"

        client = get_llm_client()
        assert isinstance(client, OpenAIProvider)

    @pytest.mark.django_db
    def test_unknown_provider_raises(self, settings):
        settings.EPOCHA_DEFAULT_LLM_PROVIDER = "unknown"

        with pytest.raises(ValueError, match="Unknown LLM provider"):
            get_llm_client()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest epocha/apps/llm_adapter/tests/test_client.py -v`
Expected: FAIL — `_call_api` does not exist, `complete` raises NotImplementedError

- [ ] **Step 3: Implement OpenAI provider**

```python
# epocha/apps/llm_adapter/providers/openai.py
"""OpenAI provider — first provider for the MVP."""
import openai

from .base import BaseLLMProvider

# Pricing per 1M tokens (as of March 2026, update as needed)
MODEL_PRICING = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4.1": {"input": 2.00, "output": 8.00},
}


class OpenAIProvider(BaseLLMProvider):
    """OpenAI-compatible implementation via SDK.

    Supports any provider with OpenAI-compatible API by setting base_url:
    - OpenAI: no base_url needed
    - Google Gemini: base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    - Groq: base_url="https://api.groq.com/openai/v1"
    - OpenRouter: base_url="https://openrouter.ai/api/v1"
    - Together AI: base_url="https://api.together.xyz/v1"
    - Mistral: base_url="https://api.mistral.ai/v1"
    """

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: str | None = None):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self._client = openai.OpenAI(api_key=api_key, base_url=base_url)

    def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> str:
        result = self._call_api(prompt, system_prompt, temperature, max_tokens)
        return result["content"]

    def _call_api(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> dict:
        """Call OpenAI API and return content + token counts."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        choice = response.choices[0]
        return {
            "content": choice.message.content,
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
        }

    def get_cost(self, input_tokens: int, output_tokens: int) -> float:
        pricing = MODEL_PRICING.get(self.model, {"input": 1.0, "output": 5.0})
        return (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000

    def get_model_name(self) -> str:
        return self.model
```

- [ ] **Step 3b: Update client.py to pass base_url and add setting**

In `epocha/apps/llm_adapter/client.py`, update the factory:

```python
def get_llm_client() -> BaseLLMProvider:
    """Factory: returns the configured LLM provider."""
    provider_name = settings.EPOCHA_DEFAULT_LLM_PROVIDER

    if provider_name == "openai":
        return OpenAIProvider(
            api_key=settings.EPOCHA_LLM_API_KEY,
            model=settings.EPOCHA_LLM_MODEL,
            base_url=settings.EPOCHA_LLM_BASE_URL or None,
        )

    raise ValueError(f"Unknown LLM provider: {provider_name}")
```

In `config/settings/base.py`, add:

```python
EPOCHA_LLM_BASE_URL = env("EPOCHA_LLM_BASE_URL", default="")
```

In `.envs/.local/.django`, add:

```
# Leave empty for OpenAI default, or set for other providers:
# Google Gemini: https://generativelanguage.googleapis.com/v1beta/openai/
# Groq: https://api.groq.com/openai/v1
# OpenRouter: https://openrouter.ai/api/v1
# Together AI: https://api.together.xyz/v1
# Mistral: https://api.mistral.ai/v1
EPOCHA_LLM_BASE_URL=
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest epocha/apps/llm_adapter/tests/test_client.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add epocha/apps/llm_adapter/ config/settings/base.py .envs/.local/.django
git commit -m "feat(llm-adapter): implement OpenAI-compatible provider with configurable base_url"
```

---

## Task 2: LLM Adapter — Rate Limiter

**Files:**
- Modify: `epocha/apps/llm_adapter/rate_limiter.py`
- Create: `epocha/apps/llm_adapter/tests/test_rate_limiter.py`

- [ ] **Step 1: Write the failing test**

```python
# epocha/apps/llm_adapter/tests/test_rate_limiter.py
from unittest.mock import MagicMock

import pytest

from epocha.apps.llm_adapter.rate_limiter import RateLimiter


class TestRateLimiter:
    def setup_method(self):
        self.redis = MagicMock()
        self.limiter = RateLimiter(
            redis_client=self.redis,
            provider="openai",
            max_requests_per_minute=60,
        )

    def test_can_proceed_when_under_limit(self):
        self.redis.get.return_value = b"10"
        assert self.limiter.can_proceed() is True

    def test_cannot_proceed_when_at_limit(self):
        self.redis.get.return_value = b"60"
        assert self.limiter.can_proceed() is False

    def test_cannot_proceed_when_over_limit(self):
        self.redis.get.return_value = b"100"
        assert self.limiter.can_proceed() is False

    def test_can_proceed_when_no_key(self):
        self.redis.get.return_value = None
        assert self.limiter.can_proceed() is True

    def test_record_request_increments_counter(self):
        mock_pipe = MagicMock()
        self.redis.pipeline.return_value = mock_pipe
        self.limiter.record_request()
        mock_pipe.incr.assert_called_once()
        mock_pipe.execute.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest epocha/apps/llm_adapter/tests/test_rate_limiter.py -v`
Expected: FAIL — NotImplementedError

- [ ] **Step 3: Implement rate limiter**

```python
# epocha/apps/llm_adapter/rate_limiter.py
"""Rate limiting for LLM calls via Redis."""


class RateLimiter:
    """Redis-based rate limiter to respect provider limits."""

    KEY_PREFIX = "epocha:ratelimit"
    TTL_SECONDS = 60

    def __init__(self, redis_client, provider: str, max_requests_per_minute: int = 50):
        self.redis = redis_client
        self.provider = provider
        self.max_rpm = max_requests_per_minute
        self._key = f"{self.KEY_PREFIX}:{provider}"

    def can_proceed(self) -> bool:
        """Check if the request can proceed within rate limits."""
        current = self.redis.get(self._key)
        if current is None:
            return True
        return int(current) < self.max_rpm

    def record_request(self):
        """Record a completed request and set TTL if new key."""
        pipe = self.redis.pipeline()
        pipe.incr(self._key)
        pipe.expire(self._key, self.TTL_SECONDS)
        pipe.execute()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest epocha/apps/llm_adapter/tests/test_rate_limiter.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add epocha/apps/llm_adapter/rate_limiter.py epocha/apps/llm_adapter/tests/test_rate_limiter.py
git commit -m "feat(llm-adapter): add Redis-based rate limiter"
```

---

## Task 3: Agent Personality Builder

**Files:**
- Modify: `epocha/apps/agents/personality.py`
- Create: `epocha/apps/agents/tests/test_personality.py`

- [ ] **Step 1: Write the failing test**

```python
# epocha/apps/agents/tests/test_personality.py
import pytest

from epocha.apps.agents.personality import build_personality_prompt


class TestBuildPersonalityPrompt:
    def test_returns_non_empty_string(self):
        traits = {
            "openness": 0.8,
            "conscientiousness": 0.3,
            "extraversion": 0.6,
            "agreeableness": 0.4,
            "neuroticism": 0.7,
            "background": "A blacksmith in a medieval village",
            "ambitions": "Become the village leader",
            "weaknesses": "Quick temper, distrustful of strangers",
            "values": "Hard work, loyalty to family",
        }
        result = build_personality_prompt(traits)
        assert isinstance(result, str)
        assert len(result) > 100

    def test_includes_role_and_background(self):
        traits = {
            "openness": 0.5,
            "conscientiousness": 0.5,
            "extraversion": 0.5,
            "agreeableness": 0.5,
            "neuroticism": 0.5,
            "background": "A corrupt priest",
            "ambitions": "Accumulate wealth",
            "weaknesses": "Greed",
            "values": "Self-preservation",
        }
        result = build_personality_prompt(traits)
        assert "corrupt priest" in result.lower() or "priest" in result.lower()

    def test_handles_missing_optional_fields(self):
        traits = {
            "openness": 0.5,
            "conscientiousness": 0.5,
            "extraversion": 0.5,
            "agreeableness": 0.5,
            "neuroticism": 0.5,
        }
        result = build_personality_prompt(traits)
        assert isinstance(result, str)
        assert len(result) > 50
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest epocha/apps/agents/tests/test_personality.py -v`
Expected: FAIL — NotImplementedError

- [ ] **Step 3: Implement personality builder**

```python
# epocha/apps/agents/personality.py
"""Build personality profile from Big Five traits."""

BIG_FIVE_DESCRIPTIONS = {
    "openness": {
        "high": "curious, creative, open to new experiences",
        "low": "practical, conventional, prefers routine",
    },
    "conscientiousness": {
        "high": "organized, disciplined, reliable",
        "low": "spontaneous, flexible, sometimes careless",
    },
    "extraversion": {
        "high": "outgoing, energetic, talkative",
        "low": "reserved, introspective, prefers solitude",
    },
    "agreeableness": {
        "high": "cooperative, trusting, empathetic",
        "low": "competitive, skeptical, challenging",
    },
    "neuroticism": {
        "high": "anxious, emotionally reactive, prone to worry",
        "low": "calm, emotionally stable, resilient",
    },
}


def _describe_trait(trait_name: str, value: float) -> str:
    """Convert a 0-1 trait value to a natural language description."""
    descriptions = BIG_FIVE_DESCRIPTIONS.get(trait_name, {})
    if value >= 0.7:
        return f"You are {descriptions.get('high', 'notable in ' + trait_name)}"
    elif value <= 0.3:
        return f"You are {descriptions.get('low', 'low in ' + trait_name)}"
    return f"You are moderate in {trait_name}"


def build_personality_prompt(personality_data: dict) -> str:
    """Generate the personality prompt for the LLM from a traits dict."""
    parts = ["You are a person with the following personality:\n"]

    # Big Five traits
    for trait in ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]:
        value = personality_data.get(trait, 0.5)
        parts.append(f"- {_describe_trait(trait, value)}")

    # Background
    background = personality_data.get("background", "")
    if background:
        parts.append(f"\nYour background: {background}")

    # Ambitions
    ambitions = personality_data.get("ambitions", "")
    if ambitions:
        parts.append(f"Your ambitions: {ambitions}")

    # Weaknesses
    weaknesses = personality_data.get("weaknesses", "")
    if weaknesses:
        parts.append(f"Your weaknesses: {weaknesses}")

    # Values
    values = personality_data.get("values", "")
    if values:
        parts.append(f"Your core values: {values}")

    parts.append("\nAlways act consistently with your personality. Never break character.")

    return "\n".join(parts)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest epocha/apps/agents/tests/test_personality.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add epocha/apps/agents/personality.py epocha/apps/agents/tests/test_personality.py
git commit -m "feat(agents): implement personality prompt builder from Big Five traits"
```

---

## Task 4: Agent Memory System

**Files:**
- Modify: `epocha/apps/agents/memory.py`
- Create: `epocha/apps/agents/tests/test_memory.py`

- [ ] **Step 1: Write the failing test**

```python
# epocha/apps/agents/tests/test_memory.py
import pytest

from epocha.apps.agents.memory import decay_memories, get_relevant_memories
from epocha.apps.agents.models import Agent, Memory
from epocha.apps.simulation.models import Simulation


@pytest.mark.django_db
class TestGetRelevantMemories:
    @pytest.fixture
    def simulation(self, user):
        return Simulation.objects.create(name="Test", seed=42, owner=user)

    @pytest.fixture
    def agent(self, simulation):
        return Agent.objects.create(
            simulation=simulation,
            name="TestAgent",
            personality={"openness": 0.5},
        )

    def test_returns_most_relevant_memories(self, agent):
        Memory.objects.create(agent=agent, content="Saw a bird", emotional_weight=0.1, tick_created=1)
        Memory.objects.create(agent=agent, content="House burned down", emotional_weight=0.9, tick_created=2)
        Memory.objects.create(agent=agent, content="Had lunch", emotional_weight=0.2, tick_created=3)

        memories = get_relevant_memories(agent, current_tick=10, max_memories=2)
        assert len(memories) == 2
        assert memories[0].content == "House burned down"

    def test_excludes_inactive_memories(self, agent):
        Memory.objects.create(agent=agent, content="Old memory", emotional_weight=0.5, tick_created=1, is_active=False)
        Memory.objects.create(agent=agent, content="Active memory", emotional_weight=0.5, tick_created=2)

        memories = get_relevant_memories(agent, current_tick=10)
        assert all(m.is_active for m in memories)


@pytest.mark.django_db
class TestDecayMemories:
    @pytest.fixture
    def simulation(self, user):
        return Simulation.objects.create(name="Test", seed=42, owner=user)

    @pytest.fixture
    def agent(self, simulation):
        return Agent.objects.create(simulation=simulation, name="TestAgent", personality={})

    def test_old_low_weight_memories_decay(self, agent):
        Memory.objects.create(agent=agent, content="Trivial", emotional_weight=0.1, tick_created=1)
        decay_memories(agent, current_tick=100)

        memory = Memory.objects.get(content="Trivial")
        assert memory.is_active is False

    def test_high_weight_memories_persist(self, agent):
        Memory.objects.create(agent=agent, content="Trauma", emotional_weight=0.9, tick_created=1)
        decay_memories(agent, current_tick=100)

        memory = Memory.objects.get(content="Trauma")
        assert memory.is_active is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest epocha/apps/agents/tests/test_memory.py -v`
Expected: FAIL — NotImplementedError

- [ ] **Step 3: Implement memory system**

```python
# epocha/apps/agents/memory.py
"""Agent memory management — read, write, decay."""
from .models import Memory

# Memories older than this many ticks start decaying
DECAY_THRESHOLD_TICKS = 50

# Emotional weight above this value makes memories resistant to decay
EMOTIONAL_PERSISTENCE_THRESHOLD = 0.6


def get_relevant_memories(agent, current_tick, max_memories=10):
    """Retrieve the most relevant memories for the current context.

    Prioritizes: high emotional weight, then recency.
    """
    return list(
        Memory.objects.filter(agent=agent, is_active=True)
        .order_by("-emotional_weight", "-tick_created")[:max_memories]
    )


def decay_memories(agent, current_tick):
    """Apply decay to memories based on emotional weight and time.

    Memories with low emotional weight that are old enough get deactivated.
    High emotional weight memories persist much longer.
    """
    memories = Memory.objects.filter(agent=agent, is_active=True)

    for memory in memories:
        age = current_tick - memory.tick_created
        if age <= DECAY_THRESHOLD_TICKS:
            continue

        # High emotional weight = resistant to decay
        if memory.emotional_weight >= EMOTIONAL_PERSISTENCE_THRESHOLD:
            continue

        # Decay probability increases with age and decreases with emotional weight
        decay_factor = age / (DECAY_THRESHOLD_TICKS * (1 + memory.emotional_weight * 5))
        if decay_factor > 1.0:
            memory.is_active = False
            memory.save(update_fields=["is_active"])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest epocha/apps/agents/tests/test_memory.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add epocha/apps/agents/memory.py epocha/apps/agents/tests/test_memory.py
git commit -m "feat(agents): implement memory retrieval and decay system"
```

---

## Task 5: Agent Decision Pipeline

**Files:**
- Modify: `epocha/apps/agents/decision.py`
- Create: `epocha/apps/agents/tests/test_decision.py`

- [ ] **Step 1: Write the failing test**

```python
# epocha/apps/agents/tests/test_decision.py
from unittest.mock import MagicMock, patch

import pytest

from epocha.apps.agents.decision import process_agent_decision
from epocha.apps.agents.models import Agent, DecisionLog, Memory
from epocha.apps.simulation.models import Simulation
from epocha.apps.world.models import World


@pytest.mark.django_db
class TestProcessAgentDecision:
    @pytest.fixture
    def simulation(self, user):
        return Simulation.objects.create(name="Test", seed=42, owner=user)

    @pytest.fixture
    def world(self, simulation):
        return World.objects.create(simulation=simulation)

    @pytest.fixture
    def agent(self, simulation):
        return Agent.objects.create(
            simulation=simulation,
            name="Marco",
            role="blacksmith",
            personality={
                "openness": 0.8,
                "conscientiousness": 0.6,
                "extraversion": 0.4,
                "agreeableness": 0.3,
                "neuroticism": 0.5,
                "background": "A skilled blacksmith",
                "ambitions": "Become wealthy",
            },
        )

    @patch("epocha.apps.agents.decision.get_llm_client")
    def test_returns_action_dict(self, mock_get_client, agent, world):
        mock_client = MagicMock()
        mock_client.complete.return_value = '{"action": "work", "target": "forge", "reason": "Need to earn money"}'
        mock_client.get_model_name.return_value = "gpt-4o-mini"
        mock_get_client.return_value = mock_client

        result = process_agent_decision(agent, world, tick=1)  # world passed as world_state

        assert isinstance(result, dict)
        assert "action" in result

    @patch("epocha.apps.agents.decision.get_llm_client")
    def test_creates_decision_log(self, mock_get_client, agent, world):
        mock_client = MagicMock()
        mock_client.complete.return_value = '{"action": "rest", "reason": "Tired"}'
        mock_client.get_model_name.return_value = "gpt-4o-mini"
        mock_get_client.return_value = mock_client

        process_agent_decision(agent, world, tick=5)

        assert DecisionLog.objects.filter(agent=agent, tick=5).exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest epocha/apps/agents/tests/test_decision.py -v`
Expected: FAIL — NotImplementedError

- [ ] **Step 3: Implement decision pipeline**

```python
# epocha/apps/agents/decision.py
"""Decision pipeline: context -> prompt -> LLM -> action."""
import json
import logging

from epocha.apps.llm_adapter.client import get_llm_client

from .memory import get_relevant_memories
from .models import DecisionLog
from .personality import build_personality_prompt

logger = logging.getLogger(__name__)

DECISION_SYSTEM_PROMPT = """You are simulating a person in a world. Based on your personality,
memories, and current situation, decide what to do next.

Respond ONLY with a JSON object:
{
    "action": "work|rest|socialize|explore|trade|argue|help|avoid",
    "target": "who or what (optional)",
    "reason": "brief internal thought"
}
"""


def _build_context(agent, world, tick, memories):
    """Build the context string for the LLM prompt."""
    parts = [
        f"You are {agent.name}, a {agent.role}.",
        f"Current tick: {tick}. Your health: {agent.health:.1f}, wealth: {agent.wealth:.1f}, mood: {agent.mood:.1f}.",
        f"World stability: {world.stability_index:.1f}.",
    ]

    if memories:
        parts.append("\nYour recent memories:")
        for m in memories[:5]:
            source_label = f" ({m.source_type})" if m.source_type != "direct" else ""
            parts.append(f"- {m.content}{source_label}")

    return "\n".join(parts)


def process_agent_decision(agent, world_state, tick):
    """Complete pipeline for an agent decision.

    1. Gather context (world state, memories, relationships)
    2. Build prompt with the agent's personality
    3. Call LLM via llm_adapter
    4. Parse response into a concrete action
    5. Log the decision in DecisionLog
    """
    client = get_llm_client()

    # 1. Gather context
    memories = get_relevant_memories(agent, current_tick=tick, max_memories=5)
    context = _build_context(agent, world_state, tick, memories)

    # 2. Build personality prompt
    personality_prompt = build_personality_prompt(agent.personality)
    system_prompt = f"{personality_prompt}\n\n{DECISION_SYSTEM_PROMPT}"

    # 3. Call LLM
    raw_response = client.complete(
        prompt=context,
        system_prompt=system_prompt,
        temperature=0.7,
        max_tokens=200,
    )

    # 4. Parse response
    try:
        action = json.loads(raw_response)
    except json.JSONDecodeError:
        logger.warning(f"Agent {agent.name} returned non-JSON: {raw_response}")
        action = {"action": "rest", "reason": "confused", "raw": raw_response}

    # 5. Log decision
    DecisionLog.objects.create(
        simulation=agent.simulation,
        agent=agent,
        tick=tick,
        input_context=context,
        output_decision=json.dumps(action),
        llm_model=client.get_model_name(),
    )

    return action
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest epocha/apps/agents/tests/test_decision.py -v`
Expected: All 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add epocha/apps/agents/decision.py epocha/apps/agents/tests/test_decision.py
git commit -m "feat(agents): implement decision pipeline with LLM and logging"
```

---

## Task 6: World Generator (Input Express)

**Files:**
- Modify: `epocha/apps/world/generator.py`
- Create: `epocha/apps/world/tests/test_generator.py`

- [ ] **Step 1: Write the failing test**

```python
# epocha/apps/world/tests/test_generator.py
from unittest.mock import MagicMock, patch
import json

import pytest

from epocha.apps.agents.models import Agent
from epocha.apps.simulation.models import Simulation
from epocha.apps.world.generator import generate_world_from_prompt
from epocha.apps.world.models import World, Zone


MOCK_LLM_RESPONSE = json.dumps({
    "world": {
        "economy_level": "base",
        "stability_index": 0.6,
    },
    "zones": [
        {"name": "Village Center", "type": "urban", "x": 50, "y": 50, "resources": {"food": 100, "wood": 50}},
        {"name": "Farm Fields", "type": "rural", "x": 20, "y": 30, "resources": {"food": 300}},
        {"name": "Forest", "type": "wilderness", "x": 80, "y": 70, "resources": {"wood": 200, "game": 100}},
    ],
    "agents": [
        {"name": "Marco", "age": 35, "role": "blacksmith", "personality": {"openness": 0.8, "conscientiousness": 0.6, "extraversion": 0.4, "agreeableness": 0.3, "neuroticism": 0.5, "background": "A skilled blacksmith with ambitions"}},
        {"name": "Elena", "age": 28, "role": "farmer", "personality": {"openness": 0.4, "conscientiousness": 0.8, "extraversion": 0.6, "agreeableness": 0.7, "neuroticism": 0.3, "background": "A hardworking farmer"}},
        {"name": "Padre Luca", "age": 55, "role": "priest", "personality": {"openness": 0.3, "conscientiousness": 0.5, "extraversion": 0.7, "agreeableness": 0.6, "neuroticism": 0.4, "background": "A corrupt priest"}},
    ],
})


@pytest.mark.django_db
class TestGenerateWorldFromPrompt:
    @pytest.fixture
    def simulation(self, user):
        return Simulation.objects.create(name="Test", seed=42, owner=user)

    @patch("epocha.apps.world.generator.get_llm_client")
    def test_creates_world_zones_and_agents(self, mock_get_client, simulation):
        mock_client = MagicMock()
        mock_client.complete.return_value = MOCK_LLM_RESPONSE
        mock_get_client.return_value = mock_client

        result = generate_world_from_prompt(
            prompt="A medieval village with a blacksmith, a farmer, and a corrupt priest",
            simulation=simulation,
        )

        assert World.objects.filter(simulation=simulation).exists()
        assert Zone.objects.filter(world__simulation=simulation).count() == 3
        assert Agent.objects.filter(simulation=simulation).count() == 3
        assert "agents" in result
        assert result["agents"] == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest epocha/apps/world/tests/test_generator.py -v`
Expected: FAIL — NotImplementedError

- [ ] **Step 3: Implement world generator**

```python
# epocha/apps/world/generator.py
"""Generate world from text input (Input Express)."""
import json
import logging

from epocha.apps.agents.models import Agent
from epocha.apps.llm_adapter.client import get_llm_client

from .models import World, Zone

logger = logging.getLogger(__name__)

WORLD_GENERATION_PROMPT = """Based on the user's description, generate a world for a civilization simulation.

Respond ONLY with a JSON object with this exact structure:
{
    "world": {
        "economy_level": "simplified|base|full",
        "stability_index": 0.0-1.0
    },
    "zones": [
        {
            "name": "Zone Name",
            "type": "urban|rural|wilderness|commercial|industrial",
            "x": 0-100,
            "y": 0-100,
            "resources": {"food": N, "wood": N, "stone": N, "gold": N}
        }
    ],
    "agents": [
        {
            "name": "Full Name",
            "age": N,
            "role": "role in society",
            "personality": {
                "openness": 0.0-1.0,
                "conscientiousness": 0.0-1.0,
                "extraversion": 0.0-1.0,
                "agreeableness": 0.0-1.0,
                "neuroticism": 0.0-1.0,
                "background": "backstory",
                "ambitions": "what they want",
                "weaknesses": "flaws",
                "values": "core beliefs"
            }
        }
    ]
}

Generate 3-5 zones and 10-30 agents with diverse personalities, roles, and relationships.
Make the world interesting with potential for conflict and cooperation.
"""


def generate_world_from_prompt(prompt: str, simulation) -> dict:
    """Receives the user's free text, calls the LLM, and builds the world."""
    client = get_llm_client()

    raw = client.complete(
        prompt=f"Create a world based on this description:\n\n{prompt}",
        system_prompt=WORLD_GENERATION_PROMPT,
        temperature=0.8,
        max_tokens=4000,
    )

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error(f"World generation returned non-JSON: {raw[:200]}")
        raise ValueError("LLM returned invalid JSON for world generation")

    # Create World
    world_data = data.get("world", {})
    world = World.objects.create(
        simulation=simulation,
        economy_level=world_data.get("economy_level", "base"),
        stability_index=world_data.get("stability_index", 0.7),
        global_wealth=1000.0,
    )

    # Create Zones
    zones_created = 0
    for zone_data in data.get("zones", []):
        Zone.objects.create(
            world=world,
            name=zone_data["name"],
            zone_type=zone_data.get("type", "rural"),
            position_x=zone_data.get("x", 0),
            position_y=zone_data.get("y", 0),
            resources=zone_data.get("resources", {}),
        )
        zones_created += 1

    # Create Agents
    agents_created = 0
    for agent_data in data.get("agents", []):
        Agent.objects.create(
            simulation=simulation,
            name=agent_data["name"],
            age=agent_data.get("age", 25),
            role=agent_data.get("role", "villager"),
            personality=agent_data.get("personality", {}),
            position_x=agent_data.get("x", 50),
            position_y=agent_data.get("y", 50),
        )
        agents_created += 1

    return {
        "world_id": world.id,
        "zones": zones_created,
        "agents": agents_created,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest epocha/apps/world/tests/test_generator.py -v`
Expected: All 1 test PASS

- [ ] **Step 5: Commit**

```bash
git add epocha/apps/world/generator.py epocha/apps/world/tests/test_generator.py
git commit -m "feat(world): implement Express world generation from text prompt"
```

---

## Task 7: Economy Tick Processing

**Files:**
- Modify: `epocha/apps/world/economy.py`
- Create: `epocha/apps/world/tests/test_economy.py`

- [ ] **Step 1: Write the failing test**

```python
# epocha/apps/world/tests/test_economy.py
import pytest

from epocha.apps.agents.models import Agent
from epocha.apps.simulation.models import Simulation
from epocha.apps.world.economy import process_economy_tick
from epocha.apps.world.models import World, Zone


@pytest.mark.django_db
class TestProcessEconomyTick:
    @pytest.fixture
    def setup_world(self, user):
        sim = Simulation.objects.create(name="Test", seed=42, owner=user)
        world = World.objects.create(simulation=sim, economy_level="base", global_wealth=1000)
        zone = Zone.objects.create(world=world, name="Village", zone_type="urban", resources={"food": 100})
        agent = Agent.objects.create(simulation=sim, name="Worker", role="farmer", wealth=50)
        return world, zone, agent

    def test_working_agent_gains_wealth(self, setup_world):
        world, zone, agent = setup_world
        process_economy_tick(world, tick=1)

        agent.refresh_from_db()
        # Agent should have gained some wealth from working
        assert agent.wealth >= 50

    def test_world_stability_updates(self, setup_world):
        world, zone, agent = setup_world
        original_stability = world.stability_index
        process_economy_tick(world, tick=1)

        world.refresh_from_db()
        assert isinstance(world.stability_index, float)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest epocha/apps/world/tests/test_economy.py -v`
Expected: FAIL — NotImplementedError

- [ ] **Step 3: Implement economy tick**

```python
# epocha/apps/world/economy.py
"""Base economic logic — transactions, prices, markets."""
import logging

from epocha.apps.agents.models import Agent

from .models import EconomicTransaction

logger = logging.getLogger(__name__)

# Base income per tick by role
ROLE_INCOME = {
    "farmer": 5.0,
    "blacksmith": 8.0,
    "merchant": 10.0,
    "priest": 3.0,
    "soldier": 6.0,
}
DEFAULT_INCOME = 2.0

# Cost of living per tick
COST_OF_LIVING = 3.0


def process_economy_tick(world, tick):
    """Update the economic state for a tick.

    Simple MVP economy:
    1. Each agent earns income based on role
    2. Each agent pays cost of living
    3. Wealth affects mood
    4. World stability is average of agent moods
    """
    agents = Agent.objects.filter(simulation=world.simulation, is_alive=True)

    mood_sum = 0.0
    agent_count = 0

    for agent in agents:
        # Income
        income = ROLE_INCOME.get(agent.role, DEFAULT_INCOME)
        agent.wealth += income

        # Cost of living
        agent.wealth -= COST_OF_LIVING

        # Wealth affects mood
        if agent.wealth < 0:
            agent.mood = max(0.0, agent.mood - 0.1)
            agent.health = max(0.0, agent.health - 0.01)
        elif agent.wealth < 10:
            agent.mood = max(0.0, agent.mood - 0.05)
        elif agent.wealth > 100:
            agent.mood = min(1.0, agent.mood + 0.02)

        agent.save(update_fields=["wealth", "mood", "health"])

        mood_sum += agent.mood
        agent_count += 1

    # Update world stability based on average mood
    if agent_count > 0:
        avg_mood = mood_sum / agent_count
        world.stability_index = avg_mood
        world.save(update_fields=["stability_index"])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest epocha/apps/world/tests/test_economy.py -v`
Expected: All 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add epocha/apps/world/economy.py epocha/apps/world/tests/test_economy.py
git commit -m "feat(world): implement basic economy tick with income, cost of living, mood"
```

---

## Task 8: Simulation Engine — Tick Orchestrator

**Files:**
- Modify: `epocha/apps/simulation/engine.py`
- Create: `epocha/apps/simulation/tests/test_engine.py`

- [ ] **Step 1: Write the failing test**

```python
# epocha/apps/simulation/tests/test_engine.py
from unittest.mock import patch, MagicMock

import pytest

from epocha.apps.agents.models import Agent
from epocha.apps.simulation.engine import SimulationEngine
from epocha.apps.simulation.models import Simulation, Event
from epocha.apps.world.models import World, Zone


@pytest.mark.django_db
class TestSimulationEngine:
    @pytest.fixture
    def sim_with_world(self, user):
        sim = Simulation.objects.create(name="Test", seed=42, owner=user, status="running")
        world = World.objects.create(simulation=sim)
        Zone.objects.create(world=world, name="Village", zone_type="urban")
        Agent.objects.create(simulation=sim, name="Marco", role="blacksmith", personality={"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5, "agreeableness": 0.5, "neuroticism": 0.5})
        return sim

    @patch("epocha.apps.simulation.engine.process_agent_decision")
    @patch("epocha.apps.simulation.engine.process_economy_tick")
    def test_run_tick_advances_counter(self, mock_economy, mock_decision, sim_with_world):
        mock_decision.return_value = {"action": "work", "reason": "busy"}

        engine = SimulationEngine(sim_with_world)
        engine.run_tick()

        sim_with_world.refresh_from_db()
        assert sim_with_world.current_tick == 1

    @patch("epocha.apps.simulation.engine.process_agent_decision")
    @patch("epocha.apps.simulation.engine.process_economy_tick")
    def test_run_tick_processes_agents(self, mock_economy, mock_decision, sim_with_world):
        mock_decision.return_value = {"action": "rest"}

        engine = SimulationEngine(sim_with_world)
        engine.run_tick()

        mock_decision.assert_called_once()
        mock_economy.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest epocha/apps/simulation/tests/test_engine.py -v`
Expected: FAIL — NotImplementedError

- [ ] **Step 3: Implement simulation engine**

```python
# epocha/apps/simulation/engine.py
"""Tick logic: advance time, coordinate modules."""
import logging

from epocha.apps.agents.decision import process_agent_decision
from epocha.apps.agents.memory import decay_memories
from epocha.apps.agents.models import Agent, Memory
from epocha.apps.world.economy import process_economy_tick

logger = logging.getLogger(__name__)


class SimulationEngine:
    """Simulation cycle orchestrator.

    For each tick:
    1. Update world state (economy, resources)
    2. Process agent decisions
    3. Apply decision consequences
    4. Decay agent memories
    5. Advance tick counter
    """

    def __init__(self, simulation):
        self.simulation = simulation

    def run_tick(self):
        """Execute a single simulation tick."""
        tick = self.simulation.current_tick + 1
        world = self.simulation.world

        logger.info(f"Simulation {self.simulation.id}: running tick {tick}")

        # 1. Economy
        process_economy_tick(world, tick)

        # 2. Agent decisions (re-fetch after economy tick to get updated state)
        agents = list(Agent.objects.filter(simulation=self.simulation, is_alive=True))
        for agent in agents:
            agent.refresh_from_db()
            try:
                action = process_agent_decision(agent, world, tick)
                self._apply_action(agent, action, tick)
            except Exception as e:
                logger.error(f"Agent {agent.name} failed at tick {tick}: {e}")

        # 3. Memory decay (every 10 ticks to save processing)
        if tick % 10 == 0:
            for agent in agents:
                decay_memories(agent, tick)

        # 4. Advance tick
        self.simulation.current_tick = tick
        self.simulation.save(update_fields=["current_tick", "updated_at"])

        logger.info(f"Simulation {self.simulation.id}: tick {tick} complete")

    def _apply_action(self, agent, action, tick):
        """Apply the consequences of an agent's action."""
        action_type = action.get("action", "rest")

        if action_type == "work":
            agent.mood = min(1.0, agent.mood + 0.01)
        elif action_type == "rest":
            agent.health = min(1.0, agent.health + 0.02)
        elif action_type == "socialize":
            agent.mood = min(1.0, agent.mood + 0.03)
        elif action_type == "argue":
            agent.mood = max(0.0, agent.mood - 0.05)

        agent.save(update_fields=["mood", "health"])

        # Create memory of the action
        Memory.objects.create(
            agent=agent,
            content=f"I decided to {action_type}. {action.get('reason', '')}",
            emotional_weight=0.3 if action_type in ("argue", "help") else 0.1,
            source_type="direct",
            tick_created=tick,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest epocha/apps/simulation/tests/test_engine.py -v`
Expected: All 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add epocha/apps/simulation/engine.py epocha/apps/simulation/tests/test_engine.py
git commit -m "feat(simulation): implement tick orchestrator coordinating economy and agents"
```

---

## Task 9: Simulation Celery Tasks + API Wiring

**Files:**
- Modify: `epocha/apps/simulation/tasks.py`
- Modify: `epocha/apps/simulation/views.py`
- Create: `epocha/apps/simulation/tests/test_api.py`

- [ ] **Step 1: Write the failing test**

```python
# epocha/apps/simulation/tests/test_api.py
from unittest.mock import patch

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestSimulationAPI:
    def test_create_simulation(self, authenticated_client):
        response = authenticated_client.post("/api/v1/simulations/", {
            "name": "Test Sim",
            "seed": 42,
            "config": {},
        }, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Test Sim"

    @patch("epocha.apps.simulation.views.generate_world_from_prompt")
    def test_express_creates_simulation(self, mock_gen, authenticated_client):
        mock_gen.return_value = {"world_id": 1, "zones": 3, "agents": 10}

        response = authenticated_client.post("/api/v1/simulations/express/", {
            "prompt": "A medieval village with 20 people",
        }, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert "simulation_id" in response.data

    def test_list_simulations(self, authenticated_client):
        authenticated_client.post("/api/v1/simulations/", {"name": "Sim1", "seed": 1, "config": {}}, format="json")
        response = authenticated_client.get("/api/v1/simulations/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest epocha/apps/simulation/tests/test_api.py -v`
Expected: FAIL — express returns 501

- [ ] **Step 3: Implement Celery tasks and wire Express endpoint**

```python
# epocha/apps/simulation/tasks.py
"""Celery tasks for the simulation."""
import logging

from config.celery import app

logger = logging.getLogger(__name__)


@app.task(bind=True, acks_late=True)
def run_tick(self, simulation_id):
    """Execute a simulation tick in background.

    Uses acks_late=True so the task is only acknowledged after completion.
    If the worker shuts down mid-tick, the task will be re-delivered and
    re-executed from the start of that tick (the previous tick's state
    is already persisted in PostgreSQL).
    """
    from .engine import SimulationEngine
    from .models import Simulation

    simulation = Simulation.objects.get(id=simulation_id)
    if simulation.status != Simulation.Status.RUNNING:
        return

    engine = SimulationEngine(simulation)
    engine.run_tick()


@app.task
def run_simulation_loop(simulation_id):
    """Execute one tick and re-enqueue self if simulation is still running.

    Uses self-enqueue with countdown instead of blocking sleep to avoid
    holding a Celery worker indefinitely.
    """
    from django.conf import settings

    from .models import Simulation

    simulation = Simulation.objects.get(id=simulation_id)
    if simulation.status != Simulation.Status.RUNNING:
        logger.info(f"Simulation {simulation_id} no longer running, stopping loop")
        return

    # Execute tick synchronously
    from .engine import SimulationEngine
    engine = SimulationEngine(simulation)
    engine.run_tick()

    # Re-enqueue self with delay based on speed
    tick_interval = settings.EPOCHA_DEFAULT_TICK_INTERVAL_SECONDS
    countdown = tick_interval / simulation.speed
    run_simulation_loop.apply_async(args=[simulation_id], countdown=countdown)
```

Update the express view:

```python
# epocha/apps/simulation/views.py — replace the express action
    @action(detail=False, methods=["post"], serializer_class=SimulationCreateExpressSerializer)
    def express(self, request):
        """Create a simulation from text input (Express mode)."""
        import random

        from epocha.apps.world.generator import generate_world_from_prompt

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        simulation = Simulation.objects.create(
            name=f"Express Simulation",
            description=serializer.validated_data["prompt"],
            seed=random.randint(0, 2**32),
            status=Simulation.Status.INITIALIZING,
            owner=request.user,
        )

        try:
            result = generate_world_from_prompt(
                prompt=serializer.validated_data["prompt"],
                simulation=simulation,
            )
            simulation.status = Simulation.Status.PAUSED
            simulation.save(update_fields=["status"])

            return Response(
                {
                    "simulation_id": simulation.id,
                    "world": result,
                    "status": "ready",
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            simulation.status = Simulation.Status.ERROR
            simulation.save(update_fields=["status"])
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest epocha/apps/simulation/tests/test_api.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add epocha/apps/simulation/tasks.py epocha/apps/simulation/views.py epocha/apps/simulation/tests/test_api.py
git commit -m "feat(simulation): wire Express endpoint and Celery simulation loop"
```

---

## Task 10: Chat WebSocket — Agent Conversations

**Files:**
- Modify: `epocha/apps/chat/consumers.py`
- Modify: `epocha/apps/chat/tasks.py`
- Create: `epocha/apps/chat/tests/test_consumers.py`

- [ ] **Step 1: Write the failing test**

```python
# epocha/apps/chat/tests/test_consumers.py
from unittest.mock import patch, MagicMock

import pytest
from channels.testing import WebsocketCommunicator

from epocha.apps.agents.models import Agent
from epocha.apps.chat.consumers import ChatConsumer
from epocha.apps.simulation.models import Simulation


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestChatConsumer:
    @pytest.fixture
    def simulation(self, user):
        return Simulation.objects.create(name="Test", seed=42, owner=user)

    @pytest.fixture
    def agent(self, simulation):
        return Agent.objects.create(
            simulation=simulation,
            name="Marco",
            role="blacksmith",
            personality={"openness": 0.8, "background": "A blacksmith"},
        )

    @patch("epocha.apps.llm_adapter.client.get_llm_client")
    async def test_connect_and_send_message(self, mock_get_client, agent):
        mock_client = MagicMock()
        mock_client.complete.return_value = "Aye, I am Marco the blacksmith. What do you need?"
        mock_get_client.return_value = mock_client

        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f"/ws/chat/{agent.id}/",
        )
        connected, _ = await communicator.connect()
        assert connected

        await communicator.send_json_to({"message": "Hello blacksmith!"})
        response = await communicator.receive_json_from(timeout=5)

        assert response["role"] == "agent"
        assert len(response["content"]) > 0

        await communicator.disconnect()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest epocha/apps/chat/tests/test_consumers.py -v`
Expected: FAIL — returns placeholder TODO response

- [ ] **Step 3: Implement chat consumer with LLM**

```python
# epocha/apps/chat/consumers.py
"""WebSocket consumer for chatting with agents."""
import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    """Handles real-time chat between user and agent."""

    async def connect(self):
        self.agent_id = self.scope["url_route"]["kwargs"]["agent_id"]
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        """Receives message from user, generates agent response via LLM."""
        data = json.loads(text_data)
        user_message = data.get("message", "")

        response_content = await self._generate_response(user_message)

        await self.send(text_data=json.dumps({
            "role": "agent",
            "content": response_content,
        }))

    @database_sync_to_async
    def _generate_response(self, user_message):
        """Generate agent response synchronously (wrapped for async)."""
        from epocha.apps.agents.memory import get_relevant_memories
        from epocha.apps.agents.models import Agent
        from epocha.apps.agents.personality import build_personality_prompt
        from epocha.apps.llm_adapter.client import get_llm_client

        try:
            agent = Agent.objects.get(id=self.agent_id)
        except Agent.DoesNotExist:
            return "Agent not found."

        client = get_llm_client()
        personality_prompt = build_personality_prompt(agent.personality)
        memories = get_relevant_memories(agent, current_tick=agent.simulation.current_tick)

        memory_text = ""
        if memories:
            memory_text = "\n\nYour recent memories:\n" + "\n".join(f"- {m.content}" for m in memories[:5])

        system_prompt = (
            f"{personality_prompt}\n\n"
            f"You are {agent.name}, a {agent.role}. "
            f"Someone is talking to you. Respond in character, "
            f"consistently with your personality and memories."
            f"{memory_text}"
        )

        return client.complete(
            prompt=user_message,
            system_prompt=system_prompt,
            temperature=0.8,
            max_tokens=300,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest epocha/apps/chat/tests/test_consumers.py -v`
Expected: All 1 test PASS (with mocked LLM)

- [ ] **Step 5: Commit**

```bash
git add epocha/apps/chat/consumers.py epocha/apps/chat/tests/test_consumers.py
git commit -m "feat(chat): implement WebSocket chat with agents using LLM"
```

---

## Task 11: Play/Pause Wiring + Docker Verification

The Express endpoint creates a simulation in PAUSED state. We need play/pause to actually start the simulation loop.

**Files:**
- Modify: `epocha/apps/simulation/views.py` (wire play action to Celery)

- [ ] **Step 1: Wire play action to start simulation loop**

Update the `play` action in `SimulationViewSet`:

```python
    @action(detail=True, methods=["post"])
    def play(self, request, pk=None):
        """Start or resume the simulation."""
        from .tasks import run_simulation_loop

        simulation = self.get_object()
        simulation.status = Simulation.Status.RUNNING
        simulation.save(update_fields=["status"])

        # Start the self-enqueuing simulation loop
        run_simulation_loop.delay(simulation.id)

        return Response(SimulationSerializer(simulation).data)
```

- [ ] **Step 2: Verify Docker Compose starts**

```bash
docker compose -f docker-compose.local.yml up --build
```
Expected: All 5 services start (web, db, redis, celery-worker, celery-beat)

- [ ] **Step 3: Run full test suite**

```bash
pytest --cov=epocha -v
```
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add epocha/apps/simulation/views.py
git commit -m "feat(simulation): wire play/pause to Celery simulation loop"
```

---

## Task 12: Integration Test — Full MVP Flow

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write the integration test**

```python
# tests/test_integration.py
"""Integration test: full MVP flow from Express creation to running ticks."""
from unittest.mock import patch, MagicMock
import json

import pytest
from rest_framework import status

from epocha.apps.agents.models import Agent, DecisionLog, Memory
from epocha.apps.simulation.models import Simulation, Event
from epocha.apps.world.models import World, Zone


MOCK_WORLD_RESPONSE = json.dumps({
    "world": {"economy_level": "base", "stability_index": 0.7},
    "zones": [
        {"name": "Village", "type": "urban", "x": 50, "y": 50, "resources": {"food": 200}},
    ],
    "agents": [
        {"name": "Marco", "age": 30, "role": "blacksmith", "personality": {"openness": 0.8, "conscientiousness": 0.6, "extraversion": 0.4, "agreeableness": 0.3, "neuroticism": 0.5, "background": "A blacksmith"}},
        {"name": "Elena", "age": 25, "role": "farmer", "personality": {"openness": 0.4, "conscientiousness": 0.8, "extraversion": 0.6, "agreeableness": 0.7, "neuroticism": 0.3, "background": "A farmer"}},
    ],
})


@pytest.mark.django_db
class TestFullMVPFlow:
    @patch("epocha.apps.world.generator.get_llm_client")
    def test_express_create_and_run(self, mock_get_client, authenticated_client):
        """Full flow: Express create → world generated → run ticks → agents have memories."""
        # Mock LLM for world generation
        mock_client = MagicMock()
        mock_client.complete.return_value = MOCK_WORLD_RESPONSE
        mock_client.get_model_name.return_value = "gpt-4o-mini"
        mock_get_client.return_value = mock_client

        # 1. Create simulation via Express
        response = authenticated_client.post("/api/v1/simulations/express/", {
            "prompt": "A medieval village with a blacksmith and a farmer",
        }, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        sim_id = response.data["simulation_id"]

        # 2. Verify world was created
        sim = Simulation.objects.get(id=sim_id)
        assert World.objects.filter(simulation=sim).exists()
        assert Agent.objects.filter(simulation=sim).count() == 2
        assert Zone.objects.filter(world__simulation=sim).count() == 1

        # 3. Run a tick manually (mocking agent decisions)
        mock_client.complete.return_value = '{"action": "work", "target": "forge", "reason": "Need to earn money"}'

        from epocha.apps.simulation.engine import SimulationEngine
        engine = SimulationEngine(sim)

        with patch("epocha.apps.agents.decision.get_llm_client", return_value=mock_client):
            engine.run_tick()

        # 4. Verify tick advanced
        sim.refresh_from_db()
        assert sim.current_tick == 1

        # 5. Verify agents have decision logs and memories
        assert DecisionLog.objects.filter(simulation=sim).count() == 2
        assert Memory.objects.filter(agent__simulation=sim).count() == 2
```

- [ ] **Step 2: Run integration test**

Run: `pytest tests/test_integration.py -v`
Expected: PASS

- [ ] **Step 3: Run full test suite**

Run: `pytest --cov=epocha -v`
Expected: All tests PASS

- [ ] **Step 4: Final commit**

```bash
git add tests/test_integration.py
git commit -m "test: add full MVP integration test (Express → world → tick → memories)"
```

---

## Task 13: Production Docker Setup

Production-ready Docker configuration with multi-stage build, Nginx reverse proxy, health checks, and security hardening.

**Files:**
- Already created: `compose/django/Dockerfile.production`
- Already created: `compose/django/start.production.sh`
- Already created: `compose/nginx/nginx.conf`
- Already created: `docker-compose.production.yml`

- [ ] **Step 1: Verify production Dockerfile builds**

```bash
docker build -f compose/django/Dockerfile.production -t epocha:prod .
```
Expected: Multi-stage build completes, image size significantly smaller than local image

- [ ] **Step 2: Verify production image runs**

```bash
docker run --rm epocha:prod python -c "import django; print(django.get_version())"
```
Expected: Prints Django version without errors

- [ ] **Step 3: Verify production compose starts**

```bash
cp .env.production.example .envs/.production/.django
cp .env.postgres.example .envs/.production/.postgres
# Edit .envs/.production/.django with real values
docker compose -f docker-compose.production.yml up --build
```
Expected: All 6 services start (web, nginx, db, redis, celery-worker, celery-beat)

- [ ] **Step 4: Verify Nginx proxies correctly**

```bash
# HTTP API
curl http://localhost/api/v1/simulations/

# WebSocket (should upgrade)
curl -i -N \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  http://localhost/ws/simulation/1/
```
Expected: API returns JSON, WebSocket returns 101 Switching Protocols

- [ ] **Step 5: Verify health checks pass**

```bash
docker compose -f docker-compose.production.yml ps
```
Expected: All services show "healthy" status

- [ ] **Step 6: Commit**

```bash
git add compose/django/Dockerfile.production compose/django/start.production.sh \
  compose/nginx/nginx.conf docker-compose.production.yml
git commit -m "feat(infra): add production Docker setup with Nginx, multi-stage build, health checks"
```

### Key differences from local Docker setup

| Aspect | Local | Production |
|--------|-------|------------|
| Dockerfile | Single stage, includes dev tools | Multi-stage, minimal runtime image |
| Image size | ~800MB+ | ~300MB (no build tools, no dev deps) |
| User | root | Non-root `epocha` user |
| Nginx | Not used (Django serves directly) | Reverse proxy for HTTP + WebSocket |
| Static files | Not served | Nginx serves from shared volume |
| Volumes | Code mounted (hot reload) | No code mount (baked into image) |
| Ports | 8000 exposed directly | Only 80 (Nginx) exposed |
| Health checks | None | PostgreSQL + Redis health checks with conditions |
| Restart policy | None | `unless-stopped` on all services |
| Resource limits | None | Memory limit on Celery worker (1G) |
| Redis | Default config | AOF persistence + memory limit + eviction policy |
| Backups | No volume | Dedicated backup volume for PostgreSQL |

---

## Task 14: User Registration, Login, and Simulation Ownership

Basic multi-user support: registration, login, and simulation ownership. Each simulation belongs to a user. Sharing and collaboration are designed but deferred to post-MVP.

**Files:**
- Modify: `epocha/apps/users/views.py`
- Modify: `epocha/apps/users/serializers.py`
- Modify: `epocha/apps/users/urls.py`
- Modify: `epocha/apps/simulation/models.py` (add visibility field)
- Create: `epocha/apps/users/tests/test_api.py`

- [ ] **Step 1: Write the failing test for registration**

```python
# epocha/apps/users/tests/test_api.py
import pytest
from rest_framework import status


@pytest.mark.django_db
class TestUserRegistration:
    def test_register_new_user(self, api_client):
        response = api_client.post("/api/v1/users/register/", {
            "email": "newuser@epocha.dev",
            "username": "newuser",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        }, format="json")
        assert response.status_code == status.HTTP_201_CREATED
        assert "email" in response.data
        assert "password" not in response.data

    def test_register_duplicate_email_fails(self, api_client, user):
        response = api_client.post("/api/v1/users/register/", {
            "email": "test@epocha.dev",
            "username": "another",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        }, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_password_mismatch_fails(self, api_client):
        response = api_client.post("/api/v1/users/register/", {
            "email": "new@epocha.dev",
            "username": "newuser",
            "password": "StrongPass123!",
            "password_confirm": "DifferentPass!",
        }, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestUserLogin:
    def test_login_returns_tokens(self, api_client, user):
        response = api_client.post("/api/v1/users/token/", {
            "email": "test@epocha.dev",
            "password": "testpass123",
        }, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_login_wrong_password_fails(self, api_client, user):
        response = api_client.post("/api/v1/users/token/", {
            "email": "test@epocha.dev",
            "password": "wrongpassword",
        }, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestSimulationOwnership:
    def test_user_sees_only_own_simulations(self, authenticated_client, api_client):
        # Create simulation as authenticated user
        authenticated_client.post("/api/v1/simulations/", {
            "name": "My Sim", "seed": 42, "config": {},
        }, format="json")

        # Another user should see no simulations
        from epocha.apps.users.models import User
        other = User.objects.create_user(
            email="other@epocha.dev", username="other", password="pass123"
        )
        api_client.force_authenticate(user=other)
        response = api_client.get("/api/v1/simulations/")
        assert len(response.data["results"]) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest epocha/apps/users/tests/test_api.py -v`
Expected: FAIL — register endpoint does not exist

- [ ] **Step 3: Implement registration serializer and view**

```python
# epocha/apps/users/serializers.py
"""Serializers for the users app."""
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "username", "date_joined"]
        read_only_fields = ["id", "date_joined"]


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Registration with email, username, password + confirmation."""

    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "username", "password", "password_confirm"]
        read_only_fields = ["id"]

    def validate(self, data):
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return data

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        return User.objects.create_user(**validated_data)
```

```python
# epocha/apps/users/views.py
"""Views for the users app."""
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from .models import User
from .serializers import UserRegistrationSerializer, UserSerializer


class UserMeView(generics.RetrieveUpdateAPIView):
    """Authenticated user profile."""

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class UserRegistrationView(generics.CreateAPIView):
    """Register a new user account."""

    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
```

```python
# epocha/apps/users/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import views

urlpatterns = [
    path("register/", views.UserRegistrationView.as_view(), name="user-register"),
    path("me/", views.UserMeView.as_view(), name="user-me"),
    path("token/", TokenObtainPairView.as_view(), name="token-obtain"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
]
```

- [ ] **Step 4: Add visibility field to Simulation model**

Add to `epocha/apps/simulation/models.py` in the `Simulation` class:

```python
    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private"
        SHARED = "shared", "Shared"
        PUBLIC = "public", "Public"

    visibility = models.CharField(
        max_length=10,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
        help_text="Private: only owner. Shared: owner + collaborators. Public: everyone can view and fork.",
    )
```

- [ ] **Step 5: Generate migration for new field**

```bash
python manage.py makemigrations simulation
python manage.py migrate
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest epocha/apps/users/tests/test_api.py -v`
Expected: All 5 tests PASS

- [ ] **Step 7: Commit**

```bash
git add epocha/apps/users/ epocha/apps/simulation/models.py epocha/apps/simulation/migrations/
git commit -m "feat(users): add registration, login, and simulation visibility

CHANGE: User registration endpoint with email/password. JWT login
via simplejwt. Simulation model gains visibility field (private,
shared, public) for future collaboration features. Each user sees
only their own simulations."
```

### Post-MVP collaboration model (designed, not implemented yet)

The following features are designed and ready for implementation in v0.5+:

**Simulation versioning:**
- Once shared/public, the original simulation becomes immutable
- Owner can create new versions (v1, v2, v3...) with modifications
- Forks always reference a specific version
- Version history is visible to all viewers

**Collaboration roles:**

| Role | Permissions |
|------|------------|
| Owner | Full control: create, modify, delete, share, change visibility |
| Collaborator | Observe, chat with agents, fork, inject variables (if owner permits) |
| Viewer | Read-only: observe and chat |
| Staff/Admin | Promote simulations to "Featured", moderate content, manage users |

**Staff features (admin panel):**
- Curate "Featured" simulations for the community
- Moderate inappropriate content
- Manage user accounts (ban, role assignment)
- Create "official" template simulations

---

## Summary

| Task | Component | What it builds |
|------|-----------|---------------|
| 0 | Infra | Database migrations (prerequisite) |
| 1 | LLM Adapter | OpenAI provider with cost tracking |
| 2 | LLM Adapter | Redis rate limiter |
| 3 | Agents | Personality prompt builder |
| 4 | Agents | Memory retrieval and decay |
| 5 | Agents | Decision pipeline (context → LLM → action) |
| 6 | World | Express world generation from text |
| 7 | World | Basic economy tick |
| 8 | Simulation | Tick orchestrator |
| 9 | Simulation | Celery tasks + Express API wiring |
| 10 | Chat | WebSocket chat with agents |
| 11 | Simulation | Play/pause wiring + Docker verification |
| 12 | Integration | Full flow test |
| 13 | Infra | Production Docker setup (Nginx, multi-stage, health checks) |
| 14 | Users | Registration, login, simulation ownership and visibility |

**Estimated time:** 15 tasks, each 20-60 minutes = 8-15 hours of focused work.

**After completion, the MVP can:**
1. Accept a text prompt ("A medieval village...")
2. Generate a world with agents, zones, and economy
3. Run tick-based simulation where agents make LLM-driven decisions
4. Track agent memories with realistic decay
5. Let users chat with any agent via WebSocket
6. Log all decisions for replay and debugging
