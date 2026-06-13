---
name: project_ruff_cleanup_pending
description: "NUOVO work item (scoperto 2026-06-13). ruff check . esce 1 su develop, 1185 errori / 150 file, CI lint gate gia' rosso. Aprire spec Spec Kit dedicato per ripristinare gate verde."
metadata: 
  node_type: memory
  type: project
  originSessionId: c0fe38ea-15e1-44b8-8624-3d4503b5a8f2
---

Scoperto durante la chiusura di Branch 5 factions (2026-06-13): `ruff check .` sul repo esce con exit 1.

**Entita' del debito**: 1185 errori su 150 file. Breakdown: 1058 E501 (line-length 88), 32 I001 (import sorting), 30 F401 (unused import), 26 N806 (variable naming), 9 F841 (unused local), 8 N803, 5 UP037, 4 F821, 4 F811, 3 UP035, 2 N802, 2 F541, 1 UP012, 1 E402.

**Config**: `pyproject.toml` `[tool.ruff] line-length=88`, `[tool.ruff.lint] select=["E","F","I","N","W","UP"]`. CI `.github/workflows/ci.yml:18-19` gira `ruff check .` e `ruff format --check .` come step.

**Perche' conta** (il punto vero, non i 1058 E501): il gate CI lint e' **gia' rosso da tempo** su develop. Un gate permanentemente rosso addestra il team a ignorare la CI rossa, e cosi un fallimento reale (test che si rompe, format drift) passa inosservato. Il rischio e' la perdita di affidabilita' del segnale CI, non lo stile.

**Cosa fare**: aprire spec dedicato via Spec Kit `specs/<timestamp>-ruff-repo-wide-cleanup/`. 77 errori auto-fixable con `ruff check --fix` + `ruff format` (9 hidden con `--unsafe-fixes` da valutare). Il resto E501 a mano o spezzando, caso per caso. Obiettivo: `ruff check .` e `ruff format --check .` di nuovo verdi, gate CI affidabile.

**Nota**: Branch 5 factions NON ha aggiunto violazioni (le 2 regressioni E501 sue corrette in commit 1c24c83). Il debito e' pre-esistente, fuori scope dei branch audit scientifici.

Tracciato in [[session-resume-2026-06-13]].
