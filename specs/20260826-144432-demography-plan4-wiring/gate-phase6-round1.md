# Gate di fase 6 — Round 1 sul CODICE: criterio di convergenza

**Scritto prima del lancio del round, 2026-08-27.**

## Ambito

L'intero diff del branch: `git diff develop..HEAD`. È codice, non spec: il
gate di fase 2 ha già giudicato i requisiti e non si riapre qui. Un rilievo
che contesta una decisione della spec non è un difetto del codice — va
registrato fra le osservazioni sulla spec e non ostacola la chiusura.

## Che cosa il round deve cercare, in ordine di gravità

1. **Difetti di correttezza nel codice di produzione**: formule sbagliate,
   stato non persistito, ordine violato, query per agente vivo, transazioni
   mancanti dove servono, eccezioni ingoiate.
2. **Criteri che non possono fallire**: test verdi che resterebbero verdi
   davanti a un'implementazione sbagliata. È la classe che questo progetto ha
   pagato sedici volte nel work item precedente e cinque in questo; ogni
   verifica deve dimostrare di poter fallire.
3. **Deviazioni dalla spec approvata** non dichiarate.
4. **Doc-sync**: un modulo del §4.1 modificato senza il whitepaper aggiornato
   nello stesso commit.
5. **Prosa che descrive uno stato superato**: docstring, commenti, whitepaper
   e build map che il branch stesso rende falsi.

## Criterio di convergenza

Il gate dà **CONVERGED** quando il round non produce:

- alcun difetto di correttezza nel codice di produzione, **né**
- alcun criterio che non può fallire.

Cifre imprecise, riferimenti che puntano male, frasi da riformulare e
osservazioni sulla spec **non riaprono il gate**: si correggono nello stesso
commit e si registrano. La seconda classe resta bloccante di proposito:
declassarla butterebbe via l'unica lezione che questo progetto ha pagato più
volte di ogni altra.

Il criterio può fallire, ed è il punto: il branch introduce sei moduli nuovi,
una migrazione, una modifica di firma in codice auditato e un cablaggio nel
tick loop. Se nulla di tutto questo produce un rilievo delle due classi
bloccanti, è perché le mutazioni lo hanno già colto — sono state ventisette,
di cui sette sopravvissute e chiuse — non perché il round non ha guardato.

## Verdetto

*(da compilare a round concluso)*
