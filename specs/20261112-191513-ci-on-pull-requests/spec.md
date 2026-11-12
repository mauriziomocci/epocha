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

Il lavoro tocca cinque file: `.github/workflows/ci.yml`, `requirements/local.txt`,
`.pre-commit-config.yaml`, `compose/postgres/Dockerfile` e
`.specify/feature.json` (il puntatore di Spec Kit alla feature corrente).
Il criterio di successo ha richiesto più esecuzioni, perché ogni giro ha
mostrato una causa nuova e preesistente.

**Esecuzione 43278450837.** Prima esecuzione sulla pull request #20, rossa in
entrambi i job. Il job `lint` installava `ruff` senza versione e ha preso la
0.17.5, che riformatta anche i blocchi Python dentro i file Markdown
(`CLAUDE.md`, i piani e le spec in `docs/superpowers/`): `ruff format --check .`
è fallito su file che la 0.15.11 dell'immagine di sviluppo accetta («All checks
passed!», «324 files already formatted»). Il job `test` si è fermato prima di
raccogliere i test con `ImproperlyConfigured: Could not find the GDAL library`:
il progetto usa GeoDjango (la parte di Django per i dati geografici), che
richiede sul runner le librerie GDAL, GEOS e PROJ.

**Esecuzione 43279153319.** Dopo aver fissato `ruff==0.15.11` in
`requirements/local.txt` (il workflow ne installa esattamente quella riga) e aver
aggiunto al job `test` i pacchetti di sistema di `compose/django/Dockerfile`, lo
schema `postgis://` e la costruzione di `compose/postgres/Dockerfile` al posto
dell'immagine `postgres:16-alpine` (che non ha né PostGIS né pgvector, l'estensione
per i vettori creata dalla migrazione `knowledge.0001_initial`), `lint` è
diventato verde. `test` è rimasto rosso perché `apt-get update` dell'immagine del
database non trova più il repository `apt.postgresql.org` per Debian bullseye,
la base di `postgis/postgis:16-3.4`.

**Correzioni successive.** `compose/postgres/Dockerfile` legge ora i pacchetti
dall'archivio congelato `apt-archive.postgresql.org`, che serve ancora
`bullseye-pgdg` con `postgresql-16-pgvector`; base e versioni sono invariate.
Passare a una base più recente è una decisione del proprietario, perché cambia
l'immagine con cui è stato creato il volume del database di sviluppo.
`.pre-commit-config.yaml` fissa ruff alla 0.15.11, così nel repository c'è una
sola versione. Il workflow dichiara `permissions: contents: read`.

**Esecuzione sull'ultimo push.** La 43282461996, sul commit 297c3ea: `lint` verde in 9 secondi, `test` rosso
dopo 11 minuti e 48 secondi, con 1574 test passati e 8 falliti. Il database
(PostGIS con pgvector) e le librerie geografiche ora funzionano, e la
suite gira fino in fondo. Dei 8 fallimenti, 7 sono quelli noti del residuo
sotto: 5 in `TestGenerateWorldFromPrompt` (`IndexError: list index out of
range`) e 2 in `tests/test_integration.py` (HTTP 500 e `KeyError:
'simulation_id'`). L'ottavo è nuovo e dipende dall'ambiente:
`TestFlightPathDeterminismAcrossHashSeeds` in
`epocha/apps/demography/tests/test_migration.py` lancia un sottoprocesso con
`cwd="/app"` (riga 2992), il percorso dell'immagine Docker, che sul runner non
esiste (`FileNotFoundError: '/app'`). Va corretto in un lavoro a parte, con il
percorso ricavato dal file del test; qui resta dichiarato. Il criterio di
successo è quindi soddisfatto nella forma alternativa: la CI parte, `lint` è
verde e `test` è rosso solo per cause preesistenti nel codice di `develop`,
non nella CI.

**Residuo noto.** Su `develop` sette test hanno bisogno del merge del Plan 4
(PR #18): cinque in `TestGenerateWorldFromPrompt` e due in
`tests/test_integration.py`. Il Plan 4 svuota le chiavi LLM nelle impostazioni di
test e simula l'arricchimento; senza quel merge il job `test` di questa pull
request può restare rosso su quei sette, per una causa che sta nel codice di
`develop` e non nella CI. Consiglio di fondere la #18 prima della #20, oppure di
rilanciare la CI della #20 dopo la #18. Resta comunque rosso l'ottavo test,
quello con `cwd="/app"`, finché non viene corretto.

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
