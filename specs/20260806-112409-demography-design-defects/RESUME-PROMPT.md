# Prompt di ripresa — sessione nuova

Copia il blocco qui sotto come primo messaggio di una sessione nuova, lanciata da
`/Users/mauriziomocci/Documents/workspace/Opensource/epocha`. È scritto per contesto zero.

Aggiornato il 2026-08-12. Le versioni precedenti puntavano all'handoff del 6 agosto
e a una baseline di 1191 test: erano ferme a prima delle fasi 1-5 e del gate di
fase 6. Se questo file torna a divergere dallo stato, è lui a essere sbagliato.

---

```
Riprendi il work item "difetti di design della demografia" nel progetto Epocha.

PRIMA DI QUALSIASI ALTRA COSA, in quest'ordine:
1. Leggi per intero specs/20260806-112409-demography-design-defects/HANDOFF-2026-08-12.md
   È l'handoff valido per lo STATO. Quelli del 06 e dell'11 agosto restano solo
   come cronaca delle fasi 0-5 e sono espressamente superati sullo stato.
2. Leggi CLAUDE.md (GOLDEN RULE del metodo scientifico, regola della build map,
   doc-sync del whitepaper, Spec Kit obbligatorio, policy dei modelli, commit).
3. Leggi .specify/memory/constitution.md (i cinque principi, tutti non negoziabili).
4. Leggi specs/20260806-112409-demography-design-defects/tasks.md, che porta lo
   stato per fase e l'esito di ogni round d'audit, e plan.md per il perimetro.

VERIFICA LO STATO PRIMA DI TOCCARE QUALSIASI COSA (l'ambiente è condiviso):
   git branch --show-current                  # 20260806-112409-demography-design-defects
   git status --short                         # deve essere vuoto
   git log --oneline develop..HEAD | wc -l    # 68
   git log --oneline -1                       # 53463ea docs(config): hand off the phase-6 gate state
Se il container è giù:
   docker compose -f docker-compose.local.yml up -d
Baseline attesa: 1571 test verdi sull'intero progetto, ruff pulito, zero migrazioni
pendenti. Se uno di questi numeri non torna, FERMATI e dimmelo invece di procedere.

DOVE SIAMO. Le fasi 0-5 sono chiuse: tutti e dieci i difetti di design corretti
(kernel poligenico, parametri per era, innovazioni di istruzione e classe,
accoppiamento assortativo, quota coniugale shari'a, conservazione esatta
dell'imposta, coefficienti dell'istruzione, valore attuale della migrazione,
orizzonte di sussistenza, stabilità di zona), whitepaper allineati in entrambe le
lingue con la dichiarazione esplicita di non comparabilità fra risultati prodotti
prima e dopo.

RESTA APERTO SOLO IL GATE PESANTE DI FASE 6, l'audit avversariale sul CODICE.
Otto round, tutti NOT CONVERGED, 83 rilievi tutti chiusi. Il round 9 non è stato
lanciato. L'handoff del 12 agosto contiene l'ambito esatto da dare al round 9 e le
cinque domande utili: usalo, non improvvisare un audit a tutto campo, che costa
venti minuti e non trova nulla che i round 1-3 non abbiano già coperto.

IL MERGE NON È STATO FATTO, DELIBERATAMENTE. L'utente ha autorizzato merge e push
in autonomia, ma il gate è rosso e il piano colloca la ratifica esplicita al passo
5.4. Si merge quando un round chiude CONVERGED, e lo si annuncia.

LE DUE COSE DA PORTARSI DIETRO, che sono il vero prodotto di questo work item:

1. QUATTORDICI CRITERI CHE NON POTEVANO FALLIRE. Test verdi che non verificavano
   nulla: una conservazione che riderivava dentro il test la quantità da
   testimoniare; una conversione di unità eseguita dal test stesso; sonde che
   dichiaravano lo stesso valore del fallback; asserzioni che seguivano dalle due
   righe sopra; un test che legava la prosa al codice e passava verde sulla
   sopravvalutazione più estrema possibile. Ogni test va provato PER MUTAZIONE —
   iniettare il difetto, vederlo rosso, ripristinare — mai per ispezione.

2. LA REGOLA DI PROCESSO SULLA GUARDIA, scritta dentro
   epocha/apps/demography/tests/test_citation_hygiene.py: la guardia si estende
   SOLO per una violazione osservata nel repository, mai per una costruita da chi
   rivede. I round 6, 7 e 8 hanno girato lo stesso ciclo — chi rivede inventa una
   forma, chi corregge aggiunge un caso e una costante, il round dopo batte la
   costante — e quel ciclo non ha punto fisso.

VINCOLI IN VIGORE, non negoziabili:
- Nessuna formula senza fonte primaria verificata. Mai citare a memoria.
- Un seme non si cambia per far passare un test.
- Le domande che faresti all'utente vanno invece a un AGENTE AVVERSARIALE, la cui
  azione successiva va supervisionata in Matteo mode (verdetto netto, evidenza
  obbligatoria con file:riga o numero misurato).
- La build map docs/build-map/epocha-build-map.html va aggiornata a ogni
  checkpoint, verificata contro il CODICE e ripubblicata sullo STESSO url
  https://claude.ai/code/artifact/c81c0d24-313c-474b-8440-c22275e1cb15
- Commit via git-commit-assistant. Mai push automatico su develop o main.
- Se un task rivela un caso non previsto, FERMATI e portalo all'agente
  avversariale invece di inventare.

Comincia lanciando il round 9 con l'ambito che l'handoff del 12 agosto specifica.
```

---

## Perché questo file esiste

Una sessione compattata perde la conversazione, non il repository. Tutto ciò che
serve per riprendere sta in quattro file — questo, l'handoff del 12 agosto,
`tasks.md` e la build map — e ciascuno di essi è aggiornato al momento del commit
che descrive. La versione precedente di questo prompt era ferma a una baseline di
1191 test e a un handoff superato: chi l'avesse usata avrebbe verificato numeri
sbagliati e si sarebbe fermato, che è il comportamento voluto, ma avrebbe perso
tempo. Il modo di non ripetere l'omissione è aggiornarlo insieme all'handoff.
