---
name: groq-failover
description: User has two Groq accounts for token quota failover - implement automatic key rotation on 429 errors
type: feedback
---

User has two separate Groq accounts (two API keys) to double the daily token quota (100k TPD each). When one account exhausts its quota, the system should automatically switch to the other.

**Why:** Groq free tier has a hard 100k token/day limit per account. With 15-20 agents, world generation + enrichment + simulation ticks + chat can burn through this in a single session.

**How to apply:** The provider should support multiple API keys with automatic failover on rate limit errors. Keys are configured in .env as comma-separated values.
