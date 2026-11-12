# Specifica: neutralizzare ogni impostazione LLM nei test

**Branch**: `20261112-210825-blank-llm-test-settings`
**Stato**: bozza
**Contratto API invariato.** Cambia solo `config/settings/test.py` e il suo test di guardia.

## Perche'

`config/settings/test.py` svuota `EPOCHA_LLM_API_KEY`, `EPOCHA_LLM_BASE_URL` e le tre `EPOCHA_CHAT_LLM_*`, ma lascia ereditare dall'ambiente `EPOCHA_LLM_MODEL` e `EPOCHA_DEFAULT_LLM_PROVIDER` (letti in `config/settings/base.py`). La suite gira nei container della dashboard, che portano l'ambiente reale: i test dipendono quindi da valori che non controllano. Oggi il rischio e' latente e non raggiunge la rete: `get_llm_client` costruisce sempre `OpenAIProvider` e non legge mai il provider, e con la chiave vuota la costruzione fallisce. Ma un provider o un modello non predefiniti nell'ambiente cambiano la configurazione sotto cui la suite gira, e il giorno in cui il provider verra' letto la guardia non lo coprira'.

## Cambiamento

In `config/settings/test.py` fissare `EPOCHA_DEFAULT_LLM_PROVIDER` e `EPOCHA_LLM_MODEL` ai valori predefiniti di `base.py` ("openai", "gpt-4o-mini"), qualunque sia l'ambiente. Estendere il test di guardia in `epocha/apps/llm_adapter/tests/test_client.py` perche' li verifichi.

## Criterio di successo

Con `EPOCHA_LLM_PROVIDER` e `EPOCHA_LLM_MODEL` non predefiniti nell'ambiente, il test di guardia passa; senza il fix fallisce. Test di `llm_adapter` e i test di generatore/integrazione restano verdi, ruff pulito.
