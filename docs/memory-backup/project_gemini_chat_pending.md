---
name: github-models-chat
description: Chat uses GPT-4o-mini via GitHub Models (150 req/day) with Groq fallback
type: project
---

Chat provider configured as GPT-4o-mini via GitHub Models (endpoint: models.inference.ai.azure.com).
FallbackProvider wraps it with Groq as fallback when GitHub quota is exhausted.

GitHub Models free tier limits:
- gpt-4o-mini: 150 req/day, 15 RPM (Low tier)
- gpt-4o: 50 req/day, 10 RPM (High tier) -- tested but returns None on some prompts
- Meta-Llama-3.1-8B-Instruct: 150 req/day (Low tier)

**How to apply:** Config is in `.envs/.local/.django` under CHAT PROVIDER section.
To switch to gpt-4o (better but fewer requests): change EPOCHA_CHAT_LLM_MODEL=gpt-4o
