---
name: project_ruff_cleanup_pending
description: "CLOSED 2026-06-22. Ruff repo-wide cleanup completato e mergiato (PR#10, merge ed5e9e1). CI lint gate ora VERDE su develop (ruff check . e ruff format --check . exit 0)."
metadata: 
  node_type: memory
  type: project
  originSessionId: c0fe38ea-15e1-44b8-8624-3d4503b5a8f2
---

CHIUSO il 2026-06-22 via PR#10 (merge `ed5e9e1` in develop). Spec Kit: `specs/20260622-152915-ruff-repo-wide-cleanup/`.

Stato iniziale (scoperto 2026-06-13 a chiusura factions Branch 5): `ruff check .` exit 1 con 1183 errori / 150 file; `ruff format --check .` 212 file. Gate CI lint rosso da tempo.

Risultato: **`ruff check .` exit 0 e `ruff format --check .` exit 0 su develop**, pytest 809 invariato, zero cambi comportamentali.

Come risolto (7 commit, strategia ordinata):
- line-length 88->100 in pyproject.toml (E501 1056->489)
- `ruff format` repo-wide commit isolato (227 file, E501 489->52)
- auto-fix safe rules (I001, F401, F811, F541, UP035, UP012)
- E501 residui wrap/noqa; E402 import spostato
- naming N806/N803/N802: noqa-con-citazione per variabili-formula scientifiche (Heligman-Pollard 1980, Hadwiger 1940); costanti locali non-scientifiche hoistate a module-level
- F821 (4x `Couple` in demography/couple.py): NON era bug runtime, era igiene type-hint -> blocco `if TYPE_CHECKING:` + unquote annotation
- F841 dead-var rimossi (chiamate con side-effect DB mantenute, solo target assegnazione rimosso)

Config exclusions (giustificate in pyproject.toml):
- `**/migrations/*.py` E501 ignorato (generati Django, persi a rigenerazione)
- `epocha/apps/knowledge/prompts.py` E501 ignorato (literal prompt LLM multi-line, wrap rischia byte del prompt)

Lezioni:
- `ruff format` va eseguito DOPO aver settato line-length (usa quel limite).
- auto-fix F401 puo' rimuovere re-export legittimi: `EMBEDDING_DIM` in knowledge/embedding.py era re-export consumato da test -> ripristinato con `import ... as ...` esplicito. In futuro: dopo `ruff --fix F401` controllare collection pytest.
- Subagent puo' over-restructurare stringhe; per prompt LLM/JSON template preferire per-file-ignore a restructure (rischio byte-change). Verificare byte-identity via ast.literal_eval su HEAD vs working.

Vedi [[session-resume-2026-06-22]].
