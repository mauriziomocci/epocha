# Specifica: rimuovere un'impostazione morta (provider LLM predefinito)

**Branch**: `20261112-210825-blank-llm-test-settings`
**Stato**: bozza
**Contratto API invariato.** Cambiano solo configurazione, esempi di ambiente e documentazione; nessun comportamento a runtime.

## Perché

`config/settings/base.py` definiva `EPOCHA_DEFAULT_LLM_PROVIDER`, letto dalla variabile d'ambiente `EPOCHA_LLM_PROVIDER`. Nessun codice la legge: `get_llm_client` e `get_chat_llm_client` costruiscono sempre `OpenAIProvider` (verificato con grep, `getattr(settings, ...)` incluso). Un'impostazione morta è peggio di una assente: i README e gli esempi di ambiente dicono di configurarla, e chi lo fa crede di scegliere un provider mentre non cambia nulla.

Nessun pin di `EPOCHA_LLM_MODEL` o del provider nelle impostazioni di test: non serve, perché le chiavi LLM sono vuote in `config/settings/test.py` e ogni test che arriva a `get_model_name` lo sostituisce con un mock (per esempio `epocha/apps/agents/tests/test_decision.py`, riga 55 e seguenti).

## Cambiamento

- Togliere dai test di `epocha/apps/llm_adapter/tests/test_client.py` le scritture inutili di `EPOCHA_DEFAULT_LLM_PROVIDER`, lasciando intatto il significato di ciascuno.
- Eliminare l'impostazione da `config/settings/base.py` e la riga `EPOCHA_LLM_PROVIDER` da `.env.example` e `.env.production.example`.
- Togliere la riga dai due README e il nome dai due whitepaper (§3.5, EN e IT).
- Azione in sospeso per il proprietario: `CLAUDE.md` (riga ~410, esempio `settings.EPOCHA_DEFAULT_LLM_PROVIDER`) nomina ancora l'impostazione; le istruzioni del progetto le modifica solo il proprietario.

## Criterio di successo

`grep -rn "DEFAULT_LLM_PROVIDER\|EPOCHA_LLM_PROVIDER"` non trova nè lettori nè citazioni fuori da `CLAUDE.md`, da questa specifica e dagli archivi storici sotto `docs/superpowers/`. I test di `epocha/apps/llm_adapter` e quelli di generatore e integrazione restano verdi, ruff pulito.

## FAQ

**Perché eliminare e non fissare il valore nei test?** Perché nessun codice legge l'impostazione: fissarla lascia in piedi una configurazione fantasma che i README continuano a promettere. Se un giorno servirà scegliere il provider, si reintrodurra' insieme al codice che la legge e al suo test.

**Perché nessun nuovo test?** Eliminare configurazione morta è un refactor senza comportamento nuovo: la prova è il grep senza lettori più la suite verde. Un test che affermasse l'assenza di un nome sarebbe una guardia su una stringa, non su un invariante.

**Cambia qualcosa per chi ha `EPOCHA_LLM_PROVIDER` nel proprio `.env`?** No: la variabile non era letta da nulla, resta ignorata come prima.
