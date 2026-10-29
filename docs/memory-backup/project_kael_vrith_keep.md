---
name: project-kael-vrith-keep
description: "The user loves the character Kael Vrith (Alien Scientist, agent 28, simulation 4 «Express Simulation», year 2500, alien first contact) and wants to chat with him always: never delete or reset simulation 4, back it up before risky DB operations."
metadata:
  node_type: memory
  type: project
  originSessionId: f3c14087-5073-413f-8363-93f01142295b
  modified: 2026-10-29T15:18:15.077Z
---

User request 2026-10-29: «il personaggio Kael Vrith (Alien Scientist) è
fantastico, vorrei che lo memorizzassi in qualche modo, vorrei poterci
chiacchierare sempre».

Where he lives: local Docker database of the `epocha` compose project (volume
`epocha_postgres_data`), simulation 4, agent id 28, role "Alien Scientist", age
350, no `birth_tick`. Simulation 4 has no demography opt-in, and no celery
worker runs in the session stack, so no tick can kill him today.

Backups made 2026-10-29 16:17, outside the public repo, mode 600:
`~/Documents/workspace/Epocha-personaggi/kael-vrith-2026-10-29.json` (agent
fields, personality, 3 memories, 48 chat messages) and
`~/Documents/workspace/Epocha-personaggi/epocha-db-2026-10-29.dump` (pg_dump
-Fc of the whole local database, 69 tables of data, verified with
pg_restore --list).

**Why:** the local DB is the only copy; `docker compose down -v`, a volume
reset, a test run pointed at the dev DB, or running simulation 4 with
demography on (mortality) would lose him.

**How to apply:** never run `down -v` or drop/reset the `epocha` database;
before any migration or risky DB operation, take a fresh dump into that
folder; do not run ticks on simulation 4 with demography enabled without
asking. When the agent-context work item lands, Kael is a good first test of
the chat. Restore: `pg_restore -U <user> -d <db> --clean` into the epocha db
service. Related: [[project-chat-coherence]], [[project-world-setting-lost]].

What the user likes in him (2026-10-29): «il carattere, il modo di rispondere,
la calma, la logica e la comprensione». It comes from two sources, and both
must be kept to keep his voice:
1. His personality fields: openness 0.95, conscientiousness 0.85, extraversion
   0.4, agreeableness 0.6, neuroticism 0.15; background "Geneticist from the
   Virel-9 research colony"; values "Discovery, logic, curiosity"; ambitions
   "Study human biology and evolution"; weakness "Obsessive focus on research".
2. The model that speaks for him: google/gemma-4-12b in LM Studio with
   reasoning OFF (switched from qwen/qwen3-8b on 2026-10-29). A different
   model will change his voice even with the same fields.
His three memories are the same injected "meteorite" event stored three times
(non-idempotent event injection, see [[project-chat-coherence]]).

Resume point (user request 2026-10-29): a copy of the transcript and the JSON,
plus `COME-RIPRENDERE.md`, is in the user's private diary repo at
`~/Documents/workspace/Diario/2026/10/2026-10-29/epocha-kael-vrith/`. When the
user asks to "load Kael and continue", follow that file: (1) simulation 4 still
in the DB -> open the 1:1 chat; (2) DB lost -> restore the dump per
`~/Documents/workspace/Epocha-personaggi/LEGGIMI.md`; (3) no dump -> write a
small import from the JSON (agent fields + chat messages) into a new
simulation. The DB dump is deliberately NOT in the diary repo (it holds the
whole dev DB, test-user password hash included).

Living sheet (user request 2026-10-29, «aggiornandola anche»):
`Diario/2026/10/2026-10-29/epocha-kael-vrith/kael-vrith.md` (the user confirmed the subfolder is right), regenerated from
the live DB by `~/Documents/workspace/Epocha-personaggi/aggiorna_scheda_personaggio.py`
(run with `docker compose -p epocha -f docker-compose.local.yml exec -T web
python manage.py shell < <script>`, prepend the header line with the date).
Refresh it whenever the user chats with Kael and asks, and at the end of any
day the user chatted with him; take a fresh DB dump at the same time.

Gender: `non_binary`, and the user wants it kept that way (2026-10-29: «lascialo non binario, va bene così»). The model sometimes uses feminine agreement («incaricata»); that is fine, do not fix the data.
