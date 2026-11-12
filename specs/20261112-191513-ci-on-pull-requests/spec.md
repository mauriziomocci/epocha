# Feature Specification: la CI gira su ogni pull request

**Branch**: `20261112-191513-ci-on-pull-requests`
**Creata**: 2026-11-12
**Stato**: bozza, decisione della Trinità D-12-E-2 in una finestra di modalità totalmente autonoma
**Contratto API**: invariato (il lavoro tocca la CI, le sue dipendenze di sviluppo, un test e il puntatore di Spec Kit; nessun codice di produzione né API)

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

Stato al commit 3909c3a. Il lavoro tocca sette file: `.github/workflows/ci.yml`,
`requirements/local.txt`, `.pre-commit-config.yaml`, `compose/postgres/Dockerfile`,
`.specify/feature.json` (il puntatore di Spec Kit alla feature corrente),
`epocha/apps/demography/tests/test_migration.py` e questa spec.

**Cosa ho cambiato.** Il trigger `pull_request` non ha più il filtro sui branch.
Ruff è fissato alla 0.15.11 in `requirements/local.txt` (il workflow installa
esattamente quella riga) e in `.pre-commit-config.yaml`: senza versione il job
`lint` prendeva la 0.17.5, che riformatta anche i blocchi Python dentro i file
Markdown e falliva su file che la 0.15.11 dell'immagine di sviluppo accetta. Il
job `test` installa i pacchetti di sistema di `compose/django/Dockerfile` (GDAL,
GEOS e PROJ, le librerie che GeoDjango, la parte di Django per i dati geografici,
richiede sul runner), usa lo schema `postgis://` e costruisce
`compose/postgres/Dockerfile` al posto di `postgres:16-alpine`, che non ha né
PostGIS né pgvector (l'estensione per i vettori creata dalla migrazione
`knowledge.0001_initial`). Quel Dockerfile legge ora i pacchetti dall'archivio
congelato `apt-archive.postgresql.org`, perché `apt.postgresql.org` non serve più
Debian bullseye, la base di `postgis/postgis:16-3.4`; base e versioni sono
invariate, e passare a una base più recente è una decisione del proprietario,
perché cambia l'immagine con cui è stato creato il volume del database di
sviluppo. Il workflow dichiara `permissions: contents: read`. Il test
`TestFlightPathDeterminismAcrossHashSeeds` lanciava un sottoprocesso con
`cwd="/app"`, il percorso che esiste solo nell'immagine Docker
(`FileNotFoundError: '/app'` sul runner): ora usa `settings.ROOT_DIR`, la radice
del repository.

**Stato attuale, esecuzione 43284913652 su 3909c3a.** `lint` è verde in 6 secondi.
`test` è rosso: 1575 test passati e 7 falliti in 9 minuti e 42 secondi. I 7
fallimenti sono esattamente quelli noti: 5 in `TestGenerateWorldFromPrompt`
(`IndexError: list index out of range`) e 2 in
`tests/test_integration.py::TestFullMVPFlow` (HTTP 500 e `KeyError:
'simulation_id'`). Hanno bisogno del merge del Plan 4 (PR #18), che svuota le
chiavi LLM nelle impostazioni di test e simula l'arricchimento: l'ho verificato su
un albero con tutti e cinque i branch in attesa fusi. Il test con `cwd="/app"`,
corretto in 3909c3a, è passato.

**Storia delle esecuzioni precedenti.** La 43278450837 era rossa in entrambi i job
(ruff 0.17.5 senza versione e GDAL mancante); la 43279153319 aveva `lint` verde e
`test` rosso perché `apt-get update` dell'immagine del database non trovava più
il repository per bullseye; la 43282461996, sul commit 297c3ea, aveva `lint`
verde in 9 secondi e `test` rosso con 1574 passati e 8 falliti (i 7 sopra più il
test con `cwd="/app"`).

**Verdetto.** CI rossa per causa preesistente, che si chiude con il merge del
Plan 4. Il criterio di successo è soddisfatto nella forma alternativa: la CI
parte, `lint` è verde e `test` è rosso solo per cause che stanno nel codice di
`develop`, non nella CI. Ordine di merge consigliato: la #18 prima della #20,
oppure rilanciare la CI della #20 dopo la #18.

## Limiti noti

- Ruff è fissato in due posti (`requirements/local.txt` e
  `.pre-commit-config.yaml`) e nessun controllo verifica che restino uguali.
- L'elenco dei pacchetti GDAL in `ci.yml` copia quello di
  `compose/django/Dockerfile`: se uno cambia, l'altro va aggiornato a mano.
- `.specify/feature.json` viene riscritto da ogni branch in attesa, quindi darà
  conflitto nei merge.
- L'archivio apt congelato non riceve aggiornamenti di sicurezza: l'immagine del
  database di sviluppo non ne avrà più.

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
