# Feature Specification: R12-DET-1 è un non-difetto — chiusura del work item e correzione del registro

**Feature Branch**: `20260717-111300-agents-resolver-determinism`

**Created**: 2026-07-17 (quarta stesura: scope ristretto alla sola parte verificata, dopo tre round di audit)

**Status**: Draft (heavy gate fase 2 — in attesa dell'approvazione umana)

**Input**: il work item R12-DET-1 chiedeva di pinnare tre `.first()` su `name__icontains` in `simulation/engine.py` e `agents/factions.py`. Tre round di audit avversariale indipendenti hanno stabilito che quei siti **non sono difettosi** e che il fix proposto era un no-op semantico. Questo branch chiude R12-DET-1 con la prova e corregge i sei artefatti di registro che portano la diagnosi sbagliata. **Non pinna nulla**: i difetti di determinismo reali, che esistono e sono numerosi, sono deferiti a un work item dedicato per la ragione dichiarata sotto.

> **Nota sullo slug.** `agents-resolver-determinism` è ereditato dallo scope originale ed è impreciso: non esiste alcun resolver da correggere. Il branch è conservato per continuità; il nome non è autorevole, questo spec lo è.

## Che cosa questo branch consegna, e perché così poco

Consegna una sola cosa: **la verità su R12-DET-1, scritta dove il progetto la cercherà**. Nessun codice cambia comportamento.

La ragione della strettezza è un fallimento, e va scritta invece che nascosta. Questo spec è alla quarta stesura. Le prime tre hanno tentato di enumerare la popolazione dei difetti di determinismo del dominio agents/world, e tutte e tre hanno sbagliato — non ai margini, ma nel criterio:

- **Prima stesura**: assumeva che `.first()` su queryset non ordinato lasciasse la riga a Postgres. Falso. I tre siti del work item erano già deterministici e il fix emetteva SQL identico. Popolazione dichiarata: 3 siti, tutti inesistenti.
- **Seconda stesura**: cercava `.first()` con `order_by` **esplicito**, mentre dichiarava due righe più in là che `Meta.ordering` è ugualmente causale. L'omissione ha nascosto `factions.py:1247`, che vive dentro la funzione di un difetto enumerato. Non considerava affatto gli slice. Popolazione dichiarata: 3 siti; reale: molti di più.
- **Terza stesura**: definiva il troncamento come *"slice `[:N]`"* — la forma sintattica invece della sostanza — e mancava così `information_flow.py:247-249`, un `break` a `max_recipients` su queryset non ordinato che decide quali venti vicini ricevono ogni voce di ogni tick. Fondava inoltre la scelta della chiave di pin sulla seed-stabilità di `agent_id`, mai verificata e falsa. Popolazione dichiarata: 13 siti; il Round 3 ne ha trovati altri dieci.

Tre volte lo stesso errore: **il criterio che decide dove guardare era più stretto di quanto l'analisi stessa sapesse essere vero**. Ogni volta è stato l'audit avversariale a trovarlo, mai l'enumerazione. La popolazione è andata da 3 a 13 a circa 23, e non c'è ragione di credere che 23 sia il numero finale.

Una quarta enumerazione prodotta con lo stesso metodo — un grep, scritto da chi ha già scelto tre volte il predicato sbagliato — non merita fiducia, e un branch che pinnasse 23 siti su una lista inaffidabile darebbe al progetto la cosa peggiore possibile: la convinzione di aver chiuso una classe di difetti che resta aperta. **L'enumerazione va rifatta come lavoro proprio, con un'indagine avversariale multi-agente, non come premessa di un branch di fix** (decisione dell'utente, 2026-07-17).

Resta qui ciò che tre auditor indipendenti hanno verificato concorde, e che non richiede alcuna enumerazione: R12-DET-1 non esiste, e sei artefatti dicono il contrario.

## La prova che R12-DET-1 non esiste

Il work item, e la prima stesura, davano per assodato che un `.first()` su queryset non ordinato emetta `LIMIT 1` senza `ORDER BY`, lasciando a Postgres la scelta. È falso. Sorgente di `QuerySet.first()` in Django 5.1.15, la versione installata nel container, estratto e verificato da tre round:

```python
def first(self):
    """Return the first object of a query or None if no match is found."""
    if self.ordered:
        queryset = self
    else:
        self._check_ordering_first_last_queryset_aggregation(method="first")
        queryset = self.order_by("pk")      # <-- tiebreak automatico su pk
    for obj in queryset[:1]:
        return obj
```

`self.ordered` è vero per un `order_by()` esplicito **oppure** per un `Meta.ordering`. `Agent`, `Group` e `Zone` non dichiarano `Meta.ordering`, quindi i tre siti ricevono il tiebreak automatico. SQL realmente emesso, verificato sui modelli veri:

```
engine.py:149    Agent  .ordered = False -> ... ORDER BY "agents_agent"."id" ASC LIMIT 1
engine.py:168    Zone   .ordered = False -> ... ORDER BY "world_zone"."id" ASC LIMIT 1
factions.py:1208 Group  .ordered = False -> ... ORDER BY "agents_group"."id" ASC LIMIT 1
```

Il fix proposto (`.order_by("id").first()`) emette SQL **identico**, byte per byte.

Va registrata l'inversione logica, perché è la lezione: la prima stesura aveva verificato che i tre modelli non dichiarano `Meta.ordering` e ne aveva concluso che il difetto era reale. È l'esatto contrario — è **l'assenza** di `Meta.ordering` a far scattare il tiebreak protettivo, e la sua **presenza su chiave non unica** a sopprimerlo. Il dato era giusto, la conclusione rovesciata.

Nota di provenienza: la memoria ratificata e il session resume elencano solo `engine.py:148-171`. `factions.py:1208` non compare in nessuno dei due — era stato aggiunto allo scope in questa sessione. Non è load-bearing (è comunque un non-difetto), ma il registro va allineato.

## I sei artefatti da correggere

Tutti verificati riga per riga.

| # | Artefatto | Riga | Che cosa dice di sbagliato |
|---|---|---|---|
| 1 | `~/.claude/.../memory/project_economy_ratified_decisions.md` | 42 | *"R12-DET-1 FUORI SCOPE (ratificato): i resolver ... usano `.first()` non ordinato. **Difetto reale** ma di dominio demografia/agents"* |
| 2 | `docs/memory-backup/project_economy_ratified_decisions.md` | 42 | idem (copia versionata, imposta dalla regola di sync) |
| 3 | `~/.claude/.../memory/project_session_resume_2026_07_15.md` | 23 | idem, nella sintesi di sessione |
| 4 | `docs/memory-backup/project_session_resume_2026_07_15.md` | 23 | idem (copia versionata) |
| 5 | `~/.claude/.../memory/MEMORY.md` | 4 | porta il frammento `R12-DET-1 fuori scope` dentro l'indice, sotto un titolo `NON RILITIGARE` |
| 6 | `docs/memory-backup/MEMORY.md` | 4 | idem (copia versionata) |

Sui numeri 5 e 6 una precisazione dovuta al Round 3: `MEMORY.md` **non porta la diagnosi**. È una riga d'indice, non nomina file né righe, e l'unico contenuto è il frammento. Va corretta comunque — lasciare `R12-DET-1 fuori scope` dentro un elenco intitolato `NON RILITIGARE` conserverebbe il frame sbagliato, cioè che sia una decisione ratificata da non riaprire anziché un errore chiuso — ma non è "un artefatto che porta la diagnosi" al pari degli altri quattro.

Le tre copie in `docs/memory-backup/` non sono facoltative: la regola di sync del progetto le impone versionate, e correggere solo la memoria viva lascerebbe la diagnosi sbagliata nel repository, che è la copia che sopravvive a un cambio di macchina.

## I due commenti da rifondare

Nessuno dei due comporta un cambiamento di codice. Entrambi i fix che descrivono sono **corretti**; sbagliata è la motivazione, e una motivazione sbagliata in un commento è ciò che ha prodotto R12-DET-1.

**`engine.py:270-280` (R11-DET-1)** sostiene che un `.first()` non ordinato *"returned a DB-heap-order row -- an arbitrary good's trend set the persisted asking_price"*. Falso: avrebbe restituito la riga a pk minore, deterministicamente. Ma il fix resta pienamente valido, perché `order_by("good_code")` sceglie una riga **diversa** da `order_by("pk")` — l'ordine alfabetico dei codici bene non coincide con l'ordine di creazione — quindi il comportamento cambiò davvero e il suo test era genuinamente rosso. Va corretta la ragione, non il codice.

**`engine.py:247-251` (R6-PROP-1)** presenta `.order_by("id").first()` come pin di riproducibilità. È un no-op: l'ORM avrebbe ordinato per pk comunque, e l'SQL emesso è identico. Resta — è esplicito e innocuo, e rendere visibile un contratto implicito ha valore — ma il commento deve dire che **esplicita un contratto già garantito**, non che corregge un difetto.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: I sei artefatti della tabella DEVONO registrare R12-DET-1 come **non-difetto chiuso**, con la ragione (`QuerySet.first()` applica `order_by("pk")` sui queryset non ordinati) e con il dato che rende la ragione verificabile (i tre siti già emettono `ORDER BY id ASC LIMIT 1`). Le tre copie in `docs/memory-backup/` DEVONO restare identiche alle rispettive memorie vive.
- **FR-002**: Il commento R11-DET-1 (`engine.py:270-280`) DEVE essere corretto nella motivazione, dichiarando che il fix resta valido perché `good_code` seleziona una riga diversa da `pk`. Il codice NON DEVE cambiare.
- **FR-003**: Il commento R6-PROP-1 (`engine.py:247-251`) DEVE dichiarare che esplicita un contratto già garantito dall'ORM. Il codice NON DEVE cambiare.
- **FR-004**: Nessun comportamento DEVE cambiare. La suite completa DEVE passare senza che alcun test sia aggiunto, modificato o rimosso: se un test cambiasse esito, la premessa di questo branch — che i tre siti sono già deterministici — sarebbe falsa, e sarebbe motivo di escalation, non di adattamento.
- **FR-005**: La build map DEVE registrare R12-DET-1 come chiuso-non-difetto e aprire i work item deferiti di FR-006. Ripubblicata sull'artifact esistente.
- **FR-006**: I work item emersi dai tre round e non risolti qui DEVONO essere tracciati in una memoria dedicata, con l'evidenza già raccolta, perché il prossimo tentativo non riparta da zero:
  - **(a) Enumerazione del determinismo agents/world** — circa 23 siti noti su tre classi, da rifare con indagine avversariale multi-agente e predicati **semantici**: `.first()`/`.last()` con `self.ordered == True` e chiave finale non unica; **troncamento a N senza ordine totale** (slice, `break` a contatore, `islice` — non solo `[:N]`); iterazione order-sensitive su ordine parziale, incluse le iterazioni su `set`/`dict` di stringhe; riduzione float order-sensitive.
  - **(b) Riproducibilità: l'indagine architetturale.** Il RNG globale non è seminato in agents/world (`government.py:618` decide il successo di un colpo di stato, `movement.py:245-246` lo scatter, `generator.py:172`/`:391` il piazzamento); il chord Celery (`simulation/tasks.py:59-62`) crea `DecisionLog`, `Memory` e `Relationship` in parallelo, quindi le loro `id` non sono seed-stabili; e soprattutto **il mondo e gli agenti nascono da una chiamata LLM a temperatura 0.8 senza seme** (`generator.py:102-107`; `grep seed epocha/apps/llm_adapter/` non restituisce nulla). Il progetto lo dichiara nel proprio modello: `seed = models.BigIntegerField(help_text="Seed for reproducibility (non-LLM part)")` (`simulation/models.py:35`). Due run identicamente seminate non hanno gli stessi agenti.
  - **(c) L'affermazione di §4.8 sulla riproducibilità va riesaminata.** Il capitolo Methods dichiara che *"identically-seeded runs reproduce bit-identical state"*. Alla luce di (b) l'affermazione è al più scoped a "a parità di stato di partenza già nel database", e così com'è scritta un revisore la leggerebbe come riproducibilità end-to-end. È materia di integrità del paper, e ha precedenza sui pin.
  - **(d) Le memorie del ciclo politico non si propagano mai** (finding del Round 3): `stratification.py:186`/`:317` e `property_market.py:521` creano memorie dirette **dopo** `propagate_information` nello stesso tick, e al tick successivo la fase 1 filtra `tick_created=tick`. Difetto di modello, non di determinismo.
  - **(e)** `abs(sentiment)` contro `strength` in `election.py`: la docstring (`:222-223`) e il codice (`:245`) divergono **dal commit originale** `ead87fa`, quindi la divergenza è nativa e nessuno dei due criteri è scientificamente giustificato.
  - **(f)** Il gruppo a coesione nulla scartato dopo la selezione (`factions.py:1209`).
  - **(g)** L'invariante di non-sovrapposizione delle zone, né vincolata a DB né documentata (`generator.py:146-151`).

## Success Criteria *(mandatory)*

- **SC-001**: Il progetto non contiene più alcun artefatto che descriva R12-DET-1 come difetto reale. `grep -rn "R12-DET-1"` su repo e memorie restituisce solo occorrenze che lo dichiarano non-difetto chiuso.
- **SC-002**: La suite completa passa, con lo stesso numero di test di prima del branch e nessuna assertion modificata.
- **SC-003**: Il diff non contiene alcuna modifica a codice eseguibile: solo commenti, memorie, build map.
- **SC-004**: I sette work item deferiti sono tracciati con l'evidenza già raccolta (file:riga), non come titoli.
- **SC-005**: Un lettore che aprisse domani la memoria ratificata capirebbe in una riga che R12-DET-1 era un errore di diagnosi e perché, senza dover rileggere questa sessione.

## Assumptions

- Django resta alla `5.1.x` pinnata in `requirements/base.txt`. Se una major futura cambiasse il contratto di `first()`, la conclusione andrebbe rivista — ma il comportamento è stabile da anni e documentato.
- Il container è l'autorità per test e lint. In questo worktree la stack propria non si alza (quella del repo principale occupa 6379, 5432 e 8000), ma il worktree è montato dentro il container esistente: `docker exec -w /app/.claude/worktrees/trusting-wilbur-b337cf epocha-web-1 pytest -q`. Verificato: 13 test di `test_engine.py` verdi sul codice del branch.
- Nessun test-first: il branch non cambia comportamento. La regola test-first ha il suo escape hatch dichiarato per il lavoro di sola documentazione, ed è questo il caso. Un test che pinnasse "i tre siti sono deterministici" nascerebbe verde, e per la regola che le stesure precedenti si erano date un test che nasce verde è la prova che il difetto non esiste, non un pin da conservare.

## FAQ

**Un branch che non cambia codice vale un branch?**
Vale, e il costo di non farlo è misurato: la memoria ratificata ha prodotto questo work item, che ha consumato tre round di audit avversariale per scoprire che l'oggetto non esisteva. Lasciarla intatta significa che il prossimo che la legge — un agente, o l'utente fra sei mesi — riaprirà lo stesso lavoro. La correzione costa sei righe.

**Perché non pinnare almeno i difetti reali già trovati, visto che sono verificati?**
Perché "già trovati" è precisamente la categoria di cui non ci si può fidare qui. Ogni round ne ha trovati altri, due volte **dentro funzioni che il round precedente aveva enumerato**. Pinnare 23 siti e dichiarare chiusa la classe darebbe al progetto una falsa sicurezza, che è peggio dello stato attuale: oggi il difetto è ignoto, dopo sarebbe creduto risolto. L'enumerazione affidabile è lavoro proprio, non un sottoprodotto.

**I difetti reali restano quindi aperti in produzione?**
Sì, e restano aperti anche il RNG non seminato e la generazione LLM senza seme. Ma erano già aperti prima di questo branch e nessuno di essi è una regressione introdotta qui. La differenza è che ora sono **documentati con l'evidenza**, invece di essere ignoti. FR-006 esiste perché "aperto e tracciato" e "aperto e dimenticato" sono stati diversi.

**Perché lasciare in piedi il no-op R6-PROP-1 invece di rimuoverlo?**
Perché un `order_by("id")` esplicito su un `.first()` non è rumore: rende visibile nel codice un contratto che altrimenti vive solo dentro l'ORM, e questa intera vicenda dimostra che quel contratto non è di senso comune — tre stesure di spec e un work item ratificato hanno creduto il contrario. Il commento onesto vale più della riga rimossa.

**Che cosa impedisce alla quarta stesura di essere sbagliata come le prime tre?**
Il fatto che non enumera nulla. Ogni affermazione di questo spec è verificata direttamente e non dipende da un predicato di ricerca: il sorgente di `first()` è stato letto, l'SQL dei tre siti è stato stampato, le sei righe di registro sono state lette una per una. Non c'è una popolazione da delimitare, che è esattamente il passo in cui ho fallito tre volte.

**Perché il branch conserva uno slug che descrive un lavoro che non fa?**
Perché rinominarlo costerebbe più della confusione che risparmia, e nessun commit era stato prodotto sotto il vecchio scope. Lo slug è archeologia, non contratto — la nota in testa a questo spec basta a evitare l'equivoco.
