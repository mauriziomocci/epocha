# Prompt di ripresa — sessione nuova

Copia il blocco qui sotto come primo messaggio di una sessione nuova, lanciata da
`/Users/mauriziomocci/Documents/workspace/Opensource/epocha`. È scritto per contesto zero.

---

```
Riprendi il work item "difetti di design della demografia" nel progetto Epocha.

PRIMA DI QUALSIASI ALTRA COSA, in quest'ordine:
1. Leggi per intero specs/20260806-112409-demography-design-defects/HANDOFF-2026-08-06.md
   È l'unico handoff valido: stato, decisioni già prese, trappole, questioni aperte.
2. Leggi CLAUDE.md (GOLDEN RULE del metodo scientifico, regola della build map,
   doc-sync del whitepaper, Spec Kit obbligatorio, policy dei modelli, commit).
3. Leggi .specify/memory/constitution.md (i cinque principi, tutti non negoziabili).
4. Leggi specs/20260806-112409-demography-design-defects/plan.md e spec.md.

VERIFICA LO STATO PRIMA DI TOCCARE QUALSIASI COSA (l'ambiente è condiviso):
   git branch --show-current                  # 20260806-112409-demography-design-defects
   git status --short                         # deve essere vuoto
   git log --oneline develop..HEAD | wc -l    # devono essere 7
   git log --oneline origin/develop -1        # d8b50a0
Se il container è giù:
   docker compose -f docker-compose.local.yml up -d
Baseline attesa: 372 test in epocha/apps/demography/, 1191 sull'intero progetto,
ruff pulito, zero migrazioni pendenti.
Se uno di questi numeri non torna, FERMATI e dimmelo invece di procedere.

IL DELIVERABLE PRIMARIO NON È CODICE: è un emendamento a
docs/superpowers/specs/2026-04-18-demography-design-it.md, una spec dichiarata
CONVERGED nell'aprile 2026. Il codice viene DOPO l'emendamento e dopo il suo gate.

=====================  SCALETTA COMPLETA  =====================

--- FASE 0 — L'EMENDAMENTO (nessun codice) — NON INIZIATA ---

0.1  Le tre deliberazioni scientifiche, ciascuna col processo in tre passi del
     principio IV (proposta -> prima autocritica -> seconda autocritica -> POI si
     scrive). Consolidare in research.md, che ancora non esiste:
     a) FAMIGLIA DISTRIBUZIONALE. LA RICERCA BIBLIOGRAFICA È GIÀ FATTA e sta in
        research/0.1a-distributional-family-INPUT.md — leggilo per intero. È INPUT,
        non decisione: il processo in tre passi va comunque svolto.
        Raccomanda la scala latente logit (fonte portante verificata: de Villemereuil
        et al. 2016, Genetics 204(3):1281-1294), con Beta e normale troncata respinte
        per ragioni argomentate. RIBALTA UNA PRIORITÀ: il troncamento oggi non costa
        nulla, perché nessun template dichiara era_noise e ogni tratto gira a media
        0,5; il costo vero è la scala del residuo, misurata al 21-51% della
        dispersione dichiarata. Restano da chiudere: la citazione verbatim di
        Falconer per il coefficiente h²/2 a genitore singolo. La citazione di
        capitolo è chiusa: intervallo 8-10, numeri verificati sull'indice, titoli
        omessi deliberatamente dopo tre round che ne hanno colto uno sbagliato.
     b) ORIZZONTE DI PIANIFICAZIONE della migrazione, che rende dimensionalmente
        coerente il guadagno atteso. Todaro (1969) è la fonte più vicina: il
        modello da riparare è il suo e porta già un orizzonte scontato. Sjaastad
        (1962) è la fondazione più generale. Decidere orizzonte E tasso di sconto,
        e dichiarare l'effetto sulla soglia migratoria.
     c) ORIZZONTE DI SUSSISTENZA: test di fame (un tick) o di risparmio
        precauzionale (N tick)? La riga 153 del design va riscritta COMUNQUE
        perché è internamente incoerente. Dichiarare l'interazione con
        flight_trigger_ticks (vale anch'esso 30) e applicare la scelta a
        migrazione E fertilità insieme.
0.2  Magnitudini dei parametri nuovi: ampiezza di innovazione dell'istruzione e
     di Clark. Prendere a modello _BECKER_TOMES_RANK_NOISE_SD, che ha già la
     propria giustificazione misurata.
0.3  Verificare l'attribuzione a Chetty et al. (2014) PRIMA di usare 0,35 come
     bersaglio: il design cita la stessa fonte a riga 709 e a riga 721 per due
     grandezze diverse (elasticità del reddito vs persistenza dell'istruzione).
0.4  Scrivere l'emendamento, con FAQ obbligatoria per ogni decisione non ovvia.
0.5  GATE PESANTE: audit avversariale (critical-analyzer, mandato ostile) sul
     l'emendamento, ciclo di convergenza fino a CONVERGED ESPLICITO.
     >>> NESSUN CODICE PRIMA DI QUESTO VERDETTO. <<<
     Salvare il report in audit/. Committare.

--- FASE 1 — LA GUARDIA STRUTTURALE, PER PRIMA ---

1.1  VALIDAZIONE DEI TEMPLATE (User Story 7, FR-014, SC-015).
     Va per prima e non è una scelta di calendario: è il meccanismo che ha
     lasciato entrare metà dei difetti che stiamo correggendo. Oggi il caricatore
     accetta senza protestare una chiave inventata, una sezione con refuso,
     estate_tax_rate=40, heritability=5.0 e rho negativo — tutte insieme.
     Deve respingere chiavi sconosciute, valori fuori intervallo e sezioni
     ANNIDATE obbligatorie mancanti (attenzione: le sezioni di PRIMO livello sono
     già respinte oggi, quindi un test che non nomina il livello non discrimina).
     Include la correzione del §6.2 del whitepaper, che oggi pubblica come vera
     una proprietà che il caricatore non ha.
     CHECKPOINT: commit + build map.

--- FASE 2 — IL NUCLEO DI TRASMISSIONE (ordine OBBLIGATO) ---

2.1  Famiglia distribuzionale + kernel poligenico (FR-002, FR-002a, FR-003;
     SC-002, SC-013). Residuo corretto in TUTTI E TRE i rami di parentela,
     coefficiente a genitore singolo dimezzato (h²/2, non h²).
     Oggi: 48,8% della dispersione dichiarata; obiettivo SC-002: almeno il 90%.
2.2  Parametri di rumore per era e per tratto (FR-004). DIPENDE da 2.1, perché
     la famiglia determina cosa significhi "ampiezza"; e risolvere le medie
     sposta il troncamento.
2.3  Innovazione dell'istruzione e di Clark (FR-002b; SC-011, SC-012).
     DIPENDE da 2.2, perché serve un parametro che oggi non esiste.
     Oggi: l'istruzione collassa a zero in 8 generazioni, Clark si congela a
     mobilità esattamente 0,0000 dalla 2a generazione.
     ESENTI e da NON toccare: la regola meritocratica (si risana da sé) e la
     successione patrilineare rigida (la rigidità È il modello che le fonti
     descrivono).
2.4  Accoppiamento assortativo (FR-013). PER ULTIMO, perché è 2.3 a risvegliarlo:
     restituire dispersione all'istruzione crea correlazione fra genitori su un
     carattere trasmesso in TUTTE E CINQUE le ere, non solo nella sci-fi.
     CHECKPOINT: commit + build map.

--- FASE 3 — SUCCESSIONE ED ECONOMIA (indipendenti fra loro) ---

3.1  Quota coniugale shari'a (FR-005, SC-004): vedovo 1/2 senza figli e 1/4 con,
     vedova 1/4 e 1/8. Fonte primaria = Corano 4:12; Powers (1986) resta apparato
     accademico, NON fonte della struttura. Definire il coniuge non binario
     coerentemente con quanto la spec già stabilisce per i figli.
3.2  Conservazione esatta dell'imposta (FR-007, SC-006) su TUTTO il dominio di
     aliquote che la funzione accetta, non sulle sole spedite. La costruzione
     "residuo poi imposta per differenza" è esatta solo fino a 0,5 (lemma di
     Sterbenz); quella che regge ovunque deriva per differenza sempre il termine
     MINORE. Il requisito enuncia la proprietà, NON prescrive la costruzione.
3.3  Valori di regressione dei template (FR-009, SC-007). DOPO 0.3.
     CHECKPOINT: commit + build map.

--- FASE 4 — MIGRAZIONE ---

4.1  Guadagno atteso (FR-006), con l'orizzonte deciso in 0.1b. ATTENZIONE
     all'interazione con la correzione del divisore del salario già atterrata
     nella Plan 3, che ha spostato quel valore del 20%.
4.2  Orizzonte di sussistenza (FR-008, SC-014), applicato a migrazione E
     fertilità (fertility.py fa lo stesso confronto stock-su-flusso).
4.3  Stabilità di zona (FR-015, SC-016): o un segnale reale per zona, o la
     dichiarazione esplicita che è un valore di simulazione.
     CHECKPOINT: commit + build map.

--- FASE 5 — CHIUSURA ---

5.1  Whitepaper §4.1.2, §4.1.4, §4.1.5, §6.2 e §11 in ENTRAMBE le lingue
     (FR-010, SC-008): sostituire la dichiarazione dei difetti con la descrizione
     dei modelli corretti, e DICHIARARE la non comparabilità fra risultati
     prodotti prima e dopo. Correggere anche i due rimedi errati che il §4.1.4
     oggi pubblica (la monetizzazione del costo distanza e il "4,9%").
5.2  Suite intera + ruff + makemigrations --check. Zero fallimenti, zero xfail.
5.3  GATE PESANTE: audit avversariale sul CODICE (critical-analyzer), ciclo di
     convergenza fino a CONVERGED ESPLICITO. Salvare il report in audit/.
5.4  >>> FERMARSI QUI. <<< Merge in develop, re-pin del frozen-at-commit al SHA
     del merge, sync memorie e push sono da fare SOLO con ratifica esplicita
     dell'utente. NON procedere in autonomia oltre questo punto.

=====================  FINE SCALETTA  =====================

REGOLE NON NEGOZIABILI:
- Nessuna formula senza fonte primaria citata e VERIFICATA (non a memoria).
  Se una deliberazione non è derivabile da una fonte, NON inventarla: documenta
  l'alternativa e fermati.
- Test-first, e ogni test va provato PER MUTAZIONE: inietta il difetto, guardalo
  fallire, ripristina. Mai per sola ispezione. In tutti e cinque i giri del gate
  di fase 2 il difetto decisivo è stato un criterio che non poteva fallire dove
  il requisito era falso — al terzo giro NESSUN requisito falliva contro il
  difetto per cui il work item esiste.
- Committa ogni blocco coerente appena è verde, via l'agente git-commit-assistant.
  Non accumulare lavoro non committato.
- MAI push automatico. MAI merge in develop senza ratifica esplicita dell'utente.
- L'implementazione va a subagent Sonnet; le decisioni scientifiche restano a
  Opus. Se un task rivela un caso non previsto, FERMATI ed escala invece di
  inventare.

TRE TRAPPOLE CHE TI COSTERANNO TEMPO SE NON LE SAI (dettaglio nell'handoff):
1. Aggiungere estrazioni casuali SPOSTA il flusso RNG condiviso: i test che
   fissano valori da un seme cambieranno risultato senza essere sbagliati.
   Distinguili dai fallimenti veri. Un seme non si cambia mai per far passare
   un test.
2. PYTHONHASHSEED randomizza solo str/bytes, mai int — un test di determinismo in
   sottoprocesso non cattura iterazioni su set di id interi. E id consecutivi in
   una fixture rendono list(set) e sorted(set) identici per costruzione.
3. Le cifre della spec sono la fotografia del punto di partenza, non un
   riferimento perenne: le correzioni interagiscono e invalidano le baseline a
   vicenda. Ri-misurare dopo ogni fase.

REGOLA DELLA BUILD MAP:
docs/build-map/epocha-build-map.html è la fonte di verità del progetto e va
aggiornata NELLA STESSA sessione a ogni checkpoint. Verifica prima contro il
CODICE, poi ripubblica sullo STESSO url artifact
(https://claude.ai/code/artifact/c81c0d24-313c-474b-8440-c22275e1cb15), poi
committa il file insieme al lavoro che descrive.

Parti verificando lo stato, poi dimmi cosa hai trovato e come intendi impostare
la deliberazione 0.1a prima di scrivere qualsiasi cosa.
```
