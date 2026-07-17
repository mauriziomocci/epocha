---
name: ruff-lint-practice
description: "Lezioni operative sul lint ruff in Epocha, pagate durante il cleanup repo-wide del 2026-06-22. Applicarle PRIMA di rilanciare ruff --fix o ruff format su larga scala, o si rompono re-export e prompt LLM."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 04c1bad8-c5e3-4aa6-a6fc-12ef535f744c
---

Lezioni dal cleanup ruff repo-wide (2026-06-22, PR#10, merge `ed5e9e1`, spec `specs/20260622-152915-ruff-repo-wide-cleanup/`). Il cleanup e' CHIUSO -- la cronaca la registra git. Qui resta solo cio' che serve la PROSSIMA volta.

**Why**: partiti da `ruff check .` exit 1 con 1183 errori su 150 file e `ruff format --check .` su 212 file, il cleanup ha portato entrambi a exit 0 con pytest invariato e zero cambi comportamentali. Tre trappole hanno morso durante il percorso, e nessuna e' deducibile dal codice.

**How to apply** -- prima di rilanciare ruff su larga scala:

1. **`ruff format` DOPO aver settato `line-length`, mai prima**: usa quel limite. In Epocha line-length e' 100 (alzato da 88 in `pyproject.toml`, che da solo porto' E501 da 1056 a 489). Formattare prima significa riformattare due volte.
2. **`ruff --fix F401` puo' rimuovere re-export legittimi**: `EMBEDDING_DIM` in `epocha/apps/knowledge/embedding.py` era un re-export consumato dai test, e l'auto-fix lo tolse. Ripristinato con `import ... as ...` esplicito. **Dopo ogni `ruff --fix F401`, verificare la collection di pytest**, non solo che i test passino.
3. **I subagent over-restructurano le stringhe**: per i literal di prompt LLM e i template JSON preferire un `per-file-ignore` al restructure -- il rischio e' cambiare i byte del prompt. Verificare byte-identity con `ast.literal_eval` confrontando HEAD e working tree.

**Variabili-formula scientifiche**: i nomi che violano N806/N803/N802 ma vengono dalla notazione di un paper (Heligman-Pollard 1980, Hadwiger 1940) si tengono con `noqa` **corredato dalla citazione**, non si rinominano -- la fedelta' alla fonte prevale sulla convenzione. Le costanti locali NON scientifiche invece si hoistano a module-level.

**Exclusion attive** (gia' giustificate in `pyproject.toml`, non re-litigare): E501 ignorato su `**/migrations/*.py` (generati da Django, persi a rigenerazione) e su `epocha/apps/knowledge/prompts.py` (literal di prompt LLM multi-line, il wrap rischia i byte del prompt).

Il container e' l'autorita' per il lint: `docker compose -f docker-compose.local.yml exec -T web ruff check .` e `... ruff format --check .`.
