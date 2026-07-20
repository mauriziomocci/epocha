# Prompt per riprendere la lavorazione in una sessione nuova

Copia il blocco qui sotto e incollalo come primo messaggio della nuova sessione, lanciata dalla directory `/Users/mauriziomocci/Documents/workspace/Opensource/epocha`. È scritto per una sessione a **contesto zero**: non assume nulla di questa conversazione.

---

```
Riprendi l'implementazione della Demografia Plan 3 (Ereditarietà e Migrazione) nel progetto Epocha.

PRIMA DI QUALSIASI ALTRA COSA, in quest'ordine:

1. Leggi specs/20260717-120706-demography-inheritance-migration/HANDOFF-2026-07-20.md per intero.
   È l'unico handoff valido e contiene stato, decisioni gia' prese, trappole e questioni aperte.
2. Leggi CLAUDE.md (regole di progetto: GOLDEN RULE del metodo scientifico, regola della build map,
   doc-sync del whitepaper, Spec Kit obbligatorio, policy dei modelli, convenzioni di commit).
3. Leggi specs/20260717-120706-demography-inheritance-migration/tasks.md e riprendi da T024.
   Quel file e' la fonte di verita' su cosa e' fatto e cosa no.

VERIFICA LO STATO PRIMA DI TOCCARE QUALSIASI COSA (l'ambiente e' condiviso con altri attori
che lavorano sullo stesso repository in parallelo):

   git branch --show-current     # deve essere 20260717-120706-demography-inheritance-migration
   git status --short            # deve essere vuoto
   git log --oneline develop..HEAD | wc -l    # devono essere 15 commit
   grep -c '^- \[x\] T' specs/20260717-120706-demography-inheritance-migration/tasks.md   # devono essere 23

Se uno di questi numeri non torna, FERMATI e dimmelo invece di procedere: significa che qualcosa
e' cambiato sotto di noi. Se il container e' giu':
   docker compose -f docker-compose.local.yml up -d
Baseline attesa: 183 test verdi in epocha/apps/demography/, zero migrazioni pendenti.

COSA FARE:

Prosegui la fase 5 dal task T024, un task atomico alla volta, con questo protocollo non negoziabile:
- TEST-FIRST: scrivi il test rosso, ESEGUILO, e conferma che fallisce per la ragione giusta
  leggendo davvero l'output (non darlo per scontato). Solo dopo implementa.
- Verifica ogni task nel container (e' l'autorita' per test e lint), poi spunta la checkbox in tasks.md.
- Committa ogni blocco coerente appena e' verde, tramite l'agente git-commit-assistant. Non accumulare
  lavoro non committato: in questo repo e' gia' successo che un altro processo facesse stash del lavoro.
- Mai push automatico.
- L'implementazione va a un subagent Sonnet (policy dei modelli); qualunque decisione strategica
  torna a Opus. Se un task rivela un caso non previsto dal design, FERMATI ed escala invece di inventare.

BLOCCHI RESIDUI, in ordine: US3 (T024-T029, chiude inheritance.py con orfani, cascata del lutto e
batch delle morti simultanee), US4 (T030-T035, crea migration.py da zero), US5 (T036-T040, fuga
d'emergenza e crisi), chiusura (T041-T047: whitepaper §4.1 bilingue con il re-pin frozen-at-commit,
tabella doc-sync nelle sue quattro copie, suite completa, e il gate pesante di fase 6 con
critical-analyzer fino a un verdetto CONVERGED esplicito).

TRE COSE CHE TI COSTERANNO TEMPO SE NON LE SAI (dettaglio nell'handoff):

1. Il campo dell'istruzione e' Agent.education_level, NON education. La spec di design scrive
   "child.education" come abbreviazione. Inventare un campo education produce una migrazione,
   e questo piano ne produce ZERO per contratto.
2. "strength" sono due cose diverse: Agent.strength e' un tratto fisico ereditabile, mentre
   Relationship.strength e' la forza del legame ed e' quella su cui filtra la cascata del lutto (> 0.6).
   Questa trappola e' viva proprio in US3, il blocco che stai per fare.
3. Il design e' gia' CONVERGED dopo quattro round di audit: NON si riapre. Si esegue.

REGOLA ASSOLUTA SULLA BUILD MAP:
docs/build-map/epocha-build-map.html e' la fonte di verita' del progetto e va aggiornata NELLA STESSA
sessione a ogni checkpoint in cui committi un blocco coerente, ogni volta che il lavoro committato rende
falso qualcosa che la mappa afferma. Verifica prima contro il codice (mai contro memorie o handoff),
poi ripubblica sullo STESSO url artifact
(https://claude.ai/code/artifact/c81c0d24-313c-474b-8440-c22275e1cb15), poi committa il file insieme al
lavoro. Attenzione: la mappa e' stata modificata sia su questo branch sia su develop, quindi al merge
ci sara' un conflitto su quel file da risolvere tenendo ENTRAMBE le informazioni.

Parti verificando lo stato, poi dimmi cosa hai trovato e come intendi procedere su T024 prima di
scrivere codice.
```

---

## Perché il prompt è fatto così

Non duplica il contenuto dell'handoff: lo indirizza. L'unica ridondanza deliberata sono le tre trappole e la regola della build map, perché sono le cose il cui costo, se ignorate, si paga prima ancora di aprire l'handoff — e la trappola su `Relationship.strength` è viva esattamente nel primo blocco che la nuova sessione affronterà.

I quattro comandi di verifica servono come test di integrità: se uno dei numeri non torna, l'ambiente è cambiato e la sessione deve fermarsi invece di costruire su uno stato che non è quello descritto.

L'ultima riga chiede alla nuova sessione di riferire prima di scrivere codice, così hai un punto di controllo prima che parta da sola.
