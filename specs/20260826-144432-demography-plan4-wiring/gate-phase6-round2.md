# Gate di fase 6 — Round 2 sul CODICE: criterio di convergenza

**Scritto prima del lancio del round, 2026-08-28.** Il round 1 è girato senza
che il criterio fosse fissato in anticipo su questo work item; qui lo è, e la
ragione è la stessa che il work item precedente ha pagato per undici round —
un criterio letto dopo aver visto il risultato è una trattativa, non un
criterio.

## Ambito: ristretto al diff della remediation

Il round giudica `git diff a9a7bb0..HEAD`, non l'intero branch. Il round 1 ha
già giudicato il diff completo `develop..a9a7bb0` e ha prodotto otto
bloccanti; ri-giudicare quel codice significherebbe rileggere duemila righe
già lette per trovare gli stessi rilievi. Sul work item precedente
restringere l'ambito al diff della remediation ha portato un round da
venticinque minuti a tre **senza perdere severità**: il round così ristretto
ha trovato il difetto più consequenziale dell'arco finale.

Il rischio del restringimento è dichiarato invece che taciuto: una
remediation può rompere codice che il round 1 aveva giudicato sano e che
questo round non rilegge. È mitigato dal fatto che la suite intera gira su
ogni commit, che le mutazioni sono eseguite contro la versione **precedente**
oltre che contro quella nuova, e che ogni file toccato dalla remediation
rientra comunque nell'ambito per intero, non solo nelle righe cambiate.

## I nove bloccanti del round 1, e che cosa si sostiene di aver chiuso

Il round deve **verificare ciascuna chiusura contro il codice**, non fidarsi
di questo elenco. Una chiusura dichiarata e non vera è il difetto peggiore
che questo round possa trovare, perché sposta un problema noto dentro la
categoria dei risolti.

1. **N+1 nel passo fertilità**, sette query per donna fertile viva.
   Sostenuto chiuso da `ae12137`: sei domande precaricate una volta per zona
   e per simulazione, la settima portata da `select_related`.
2. **Fixture della guardia di costo che non poteva fallire** (soli maschi
   contro un passo che filtra le femmine). Sostenuto chiuso già in `a9a7bb0`,
   e ri-verificato qui perché la guardia è stata riscritta due volte da
   allora.
3. **`_avg_household_size` senza soglia d'età**, contro la propria docstring.
   Sostenuto chiuso da `9a65ecb`, con la soglia presa dal template.
4. **Prove d'ordine SC-002 tautologiche** — asserzione sulla tupla permutata
   anziché sul comportamento. Sostenuto chiuso da `d773f7a`, che esegue
   l'ordine permutato.
5. **Nessun confine transazionale** nei passi scritti dall'orchestratore.
   Sostenuto chiuso da `45189e8` per mortalità e fertilità, con la
   dichiarazione esplicita che il passo contatore ha una sola scrittura e non
   ne ha bisogno.
6. **`load_template` nudo in `form_initial_couples`**, che abortiva la
   generazione del mondo. Sostenuto chiuso da `6ea106f`.
7. **`DemographyStep.rng_phase` senza consumatore e sbagliato per due passi**.
   Sostenuto chiuso da `6ea106f`, diventato `rng_phases` e tenuto al codice
   da un test che registra le derivazioni reali.
8. **Popolazione sterile su un mondo già generato, senza log**. Sostenuto
   chiuso da `bc93240`, con la riparazione del `birth_tick` per tick e
   l'avviso sull'assenza di coppie.
9. **Coda documentale**: §4.1.1–§4.1.3, l'ordine dichiarato in testa al §4.1,
   la mappa di default cancellata nel §4.1.5, la sezione `names` non
   documentata, la build map, `ruff format`. Sostenuta chiusa da `018d8ef`,
   `bc93240` e `1286458`.

## Che cosa il round deve cercare, in ordine di gravità

1. **Difetti di correttezza nel codice di produzione** introdotti dalla
   remediation stessa: è la classe che il work item precedente ha visto due
   volte di fila, dove una riparazione distrugge un testimone mentre ne
   aggiunge un altro.
2. **Criteri che non possono fallire** fra le guardie **nuove**. Su questo
   work item il conto sta a tredici; cinque delle ultime otto sono state
   trovate dentro guardie scritte per chiudere le prime.
3. **Chiusure dichiarate e non vere** fra le nove sopra.
4. **Doc-sync**: un modulo del §4.1 toccato dalla remediation senza il
   whitepaper aggiornato nello stesso commit.
5. **Prosa che descrive uno stato superato**, build map inclusa.

## Criterio di convergenza

Il gate dà **CONVERGED** quando il round non produce:

- alcun difetto di correttezza nel codice di produzione, **né**
- alcun criterio che non può fallire, **né**
- alcuna chiusura dichiarata e non vera fra le nove del round 1.

Cifre imprecise, riferimenti che puntano male, frasi da riformulare e
osservazioni sulla spec **non riaprono il gate**: si correggono nello stesso
commit e si registrano.

## Perché questo criterio può fallire

Il criterio è falsificabile e va detto in che modo, o è teatro. La
remediation aggiunge 2172 righe su 24 file, tocca due moduli auditati nelle
firme, cambia il costo per tick due volte, introduce una riparazione che gira
a ogni tick e riscrive undici file di test. Le mutazioni eseguite sono
ventisei e cinque sono sopravvissute al primo colpo, tutte chiuse. Se il
round non produce nulla delle tre classi bloccanti, la spiegazione ammessa è
che quelle mutazioni lo abbiano già colto — non che il round non abbia
guardato, e il verdetto deve dire quali percorsi ha verificato per
sostenerlo.

## Verdetto

*(da compilare a round concluso)*
