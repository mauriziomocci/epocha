# Feature Specification: la CI gira su ogni pull request

**Branch**: `20261112-191513-ci-on-pull-requests`
**Creata**: 2026-11-12
**Stato**: bozza, decisione della Trinità D-12-E-2 in una finestra di modalità totalmente autonoma
**Contratto API**: invariato (il lavoro tocca solo `.github/workflows/ci.yml`)

## Perché

Il workflow `.github/workflows/ci.yml` di GitHub Actions (la pipeline che esegue
lint e test su GitHub a ogni evento configurato) parte solo sui push a `main` e
sulle pull request verso `main`. Il lavoro di Epocha però si integra su
`develop`: le pull request verso `develop` non fanno partire nulla, e infatti
l'ultima esecuzione registrata è la 23448146550 del 23/03/2026, su `main`, fallita.
Da allora nessun controllo meccanico ha mai guardato il codice che entra in
`develop`. La regola globale dice che la pipeline di un progetto deve fallire sul
codice cambiato; una guardia meccanica che non parte equivale a una guardia
mancante, quindi è un difetto.

## Il cambiamento

1. Il trigger `pull_request` perde il filtro sui branch: la CI parte su ogni pull
   request, qualunque sia il branch di destinazione. Il trigger `push` su `main`
   resta com'è.
2. Nient'altro nel workflow, salvo ciò che la prima esecuzione su questa pull
   request dimostra necessario perché i job possano girare (sezione *Esito*).

## Criterio di successo

La CI parte sulla pull request di questo work item e i suoi job, `lint` e
`test`, finiscono verdi; oppure, se un job resta rosso, la causa è dichiarata
con la riga di log che la prova ed è preesistente (un segreto, una dipendenza o
un servizio che il runner non ha) e non introdotta da questo cambiamento.

## Esito

Da compilare dopo la prima esecuzione della CI su questa pull request.

## FAQ

**Perché togliere il filtro invece di aggiungere `develop` alla lista?**
Perché il filtro non protegge nulla: una pull request verso un branch di
feature (il caso dei work item grandi con sotto-task, previsto nella tabella
del Git Workflow di `CLAUDE.md`) merita gli stessi controlli di una verso
`develop`. Senza filtro non c'è una lista da tenere aggiornata.

**Perché lasciare `push` solo su `main`?**
Perché ogni commit che entra in `develop` passa da una pull request, che ora fa
girare la CI sul codice risultante dal merge; ripeterla sul push a `develop`
raddoppierebbe le esecuzioni senza trovare nulla di nuovo. Su `main` il push
resta il controllo del rilascio.

**Cosa succede se la CI è rossa per una causa che esisteva già?**
La causa viene letta dal log del job fallito e dichiarata nella sezione
*Esito*: se sta nel workflow o nel repository e si corregge in poco, la correggo
qui; se dipende dall'ambiente (un segreto mancante, la rete) la dichiaro e la
CI resta rossa finché non c'è una decisione.
