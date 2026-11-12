# Specifica: rimuovere un'impostazione morta (provider LLM predefinito)

**Branch**: `20261112-210825-blank-llm-test-settings`
**Stato**: bozza
**Contratto API invariato.** Cambiano solo configurazione, esempi di ambiente e documentazione; nessun comportamento a runtime.

## Perche'

`config/settings/base.py` definiva `EPOCHA_DEFAULT_LLM_PROVIDER`, letto dalla variabile d'ambiente `EPOCHA_LLM_PROVIDER`. Nessun codice la legge: `get_llm_client` e `get_chat_llm_client` costruiscono sempre `OpenAIProvider` (verificato con grep, `getattr(settings, ...)` incluso). Un'impostazione morta e' peggio di una assente: i README e gli esempi di ambiente dicono di configurarla, e chi lo fa crede di scegliere un provider mentre non cambia nulla. La prima versione di questo branch la fissava nelle impostazioni di test; l'idea era sbagliata, perche' fissare un valore che nessuno legge non protegge niente (il test di guardia non puo' diventare rosso in CI e il blocco di `EPOCHA_LLM_MODEL` era un no-op, dato che `base.py` lo legge dall'ambiente solo se presente).

## Cambiamento

- Annullare il blocco aggiunto a `config/settings/test.py` e il test di guardia parametrizzato in `epocha/apps/llm_adapter/tests/test_client.py`; togliere dai test preesistenti le scritture inutili di `EPOCHA_DEFAULT_LLM_PROVIDER`, lasciando intatto il significato di ciascuno.
- Eliminare l'impostazione da `config/settings/base.py` e la riga `EPOCHA_LLM_PROVIDER` da `.env.example` e `.env.production.example`.
- Togliere la riga dai due README e il nome dai due whitepaper (§3.5, EN e IT).
- Azione in sospeso per il proprietario: `CLAUDE.md` (riga ~410, esempio `settings.EPOCHA_DEFAULT_LLM_PROVIDER`) nomina ancora l'impostazione; le istruzioni del progetto le modifica solo il proprietario.

## Criterio di successo

`grep -rn "DEFAULT_LLM_PROVIDER\|EPOCHA_LLM_PROVIDER"` non trova ne' lettori ne' citazioni fuori da `CLAUDE.md`, da questa specifica e dagli archivi storici sotto `docs/superpowers/`. I test di `epocha/apps/llm_adapter` e quelli di generatore e integrazione restano verdi, ruff pulito.

## FAQ

**Perche' eliminare e non fissare il valore nei test?** Perche' nessun codice legge l'impostazione: fissarla lascia in piedi una configurazione fantasma che i README continuano a promettere. Se un giorno servira' scegliere il provider, si reintrodurra' insieme al codice che la legge e al suo test.

**Perche' nessun nuovo test?** Eliminare configurazione morta e' un refactor senza comportamento nuovo: la prova e' il grep senza lettori piu' la suite verde. Un test che affermasse l'assenza di un nome sarebbe una guardia su una stringa, non su un invariante.

**Cambia qualcosa per chi ha `EPOCHA_LLM_PROVIDER` nel proprio `.env`?** No: la variabile non era letta da nulla, resta ignorata come prima.
