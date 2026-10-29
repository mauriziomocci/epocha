# Handoff: demografia Plan 4 — gate di fase 6 dopo il round 11 (2026-09-26, sera)

Sostituisce `HANDOFF-2026-09-26.md`, scritto la mattina dello stesso giorno
al round 10 e ormai superato. Il documento autoritativo sulla storia del gate
resta `gate-phase6-round2.md`: criteri e verdetti dei round 2-11, la review
di chiusura, le decisioni prese su delega dell'utente. Va letto per intero
prima di qualsiasi azione, e in particolare le sezioni dal «Round 10:
emendamento» in poi.

## Obiettivo

Portare il work item Plan 4 a gate di fase 6 CONVERGED, poi chiusura e
verdetto di mergiabilità. **Il merge è dell'utente**: a CONVERGED ci si ferma
al verdetto e si chiede. Push del branch e PR sono autorizzati con la skill
`autonomous-execution` invocata per nome; la PR esiste già in stato Draft
(vedi sotto).

## Stato attuale

**VERIFICATO la sera del 2026-09-26** (misurato, non ricordato):

- Branch `20260826-144432-demography-plan4-wiring`. HEAD è il commit che
  registra l'URL della PR, figlio di `91b9599`; `git rev-list --count
  develop..HEAD` dà **73**.
- `develop` e `origin/develop` fermi su `2223968`: il merge resta un
  fast-forward.
- Suite **1765 verdi** a `b1b7c0d` e rimisurata dal revisore del round 11 a
  `7a24c7a`; `ruff check` e `ruff format --check` puliti su **340 file**;
  guardia bilingue della build map 9 su 9.
- Il round 11 ha dato **NOT CONVERGED** con quattro bloccanti (R1-R4) e
  alcuni non bloccanti, **nessuno ancora corretto**: la sessione si è fermata
  al verdetto su richiesta dell'utente.
- `tasks.md`: T038 aperto (validazione finale).

- **Push e PR verificati.** Il branch è su GitHub a `91b9599` (remoto e
  locale coincidevano dopo il push, in fast-forward da `04129ed`). La PR è
  https://github.com/mauriziomocci/epocha/pull/18, **Draft**, verso
  `develop`, `MERGEABLE` e `CLEAN`. **Nessuna CI la verifica**:
  `.github/workflows/ci.yml` parte solo per `main`, quindi la verifica è la
  suite locale. La descrizione della PR va aggiornata quando il gate
  converge, e lo stato Draft tolto solo allora.

**ASSUNTO, non verificato**:

- Che l'artifact della build map sia alla versione 21, con la voce `13.desc`
  del sito pubblico aggiunta da un'altra sessione: lo ha riferito quella
  sessione, non l'ho letto.

## Il primo passo di domani

Remediation del round 11, **test rosso prima** per ciascun rilievo,
mutazioni misurate una per una contro un backup e anche contro la versione
precedente:

1. **R1** — ogni persona in fuga attribuita alla propria zona di partenza,
   catturata prima dello spostamento: numeratore corrente della fuga di
   massa, payload (serve al numeratore storico) e migrazione netta dello
   snapshot. Il testimone è il caso del revisore: decisore in A con nove
   vicini, moglie e due figli in «Casa» con due vicini.
2. **R2** — `mortality.py`, sempre la forma geometrica `1-(1-q)^dt`;
   correggere nel §4.1.1 l'errore dichiarato («below 0.5%») e la frase
   falsa sui neonati pre-industriali (`q(0)` = 0,0247).
3. **R3** — §4.1.5, in entrambe le lingue, togliere la «divergenza
   deliberata» della condizione (1).
4. **R4** — il pupillo dello Stato: o l'orchestratore copre la sua
   sussistenza, o la spec dichiara che il Plan 4 non lo fa e il docstring di
   `inheritance.py` smette di affermarlo. **È una decisione di perimetro:
   portarla all'utente prima di scrivere codice.**
5. Non bloccanti: una regola di nucleo per la condizione 2 (N1); testimoni
   per il decisore «mai un dipendente» (M7) e per l'ordine dei dipendenti
   (M10); le quattro uguaglianze di `test_demography_cost.py` che non
   forzano gli stream vitali; la prosa superata (N8). La memoria di fuga del
   solo decisore è una **decisione dell'utente**: chiederla.

Poi criterio del round 12 scritto e committato prima del lancio, round 12
sull'intero `develop..HEAD` con `critical-analyzer` in background.

## Decisioni dell'utente, da non rilitigare

B1 contatore di fame sul nucleo; B3 neonati creati prima della liquidazione;
C3 nomi ambigui rifiutati; la soglia d'età al matrimonio dell'era applicata
anche agli intenti, con un predicato unico (su delega); la fuga d'emergenza
decisa per nucleo (confermata il 2026-09-26). **Rinviati a work item
separati, con autorizzazione**: risoluzione degli intenti per identificatore;
le quattro chiavi `couple` dei template mai lette (`mourning_ticks`,
`marriage_market_radius`, `marriage_market_type`, `allowed_types`); il sito
pubblico, in corso in un'altra sessione sul branch
`20260926-175930-public-website`.

## Trappole pagate in questa sessione

- **Docker è condiviso fra sessioni.** Il container `web` monta il checkout
  principale, cioè questo branch, e il database di test `test_epocha` è uno
  solo. Un'altra sessione che esegue pytest o il fingerprint della build map
  nel container collide con i test o scrive nel file sbagliato. La sessione
  del sito è stata avvisata e ha smesso.
- **Test che dipendono dall'id della simulazione.** `get_seeded_rng` mescola
  la chiave primaria nel seme: un test con uguaglianze esatte su nascite,
  morti o query può passare da solo e cadere nella suite intera. Due chiusi
  (guardia per intento, identità contabile end-to-end), altri quattro
  segnalati dal round 11.
- **La guardia bilingue non vede una traduzione mancata** se si ricalcolano
  le impronte dopo aver cambiato solo l'italiano. Dopo ogni modifica della
  mappa, confrontare a occhio le due lingue del paragrafo toccato.
- **L'artifact della build map ha una voce che il file del repo non ha**
  (`13.desc`, il sito). Alla ripubblicazione leggere la versione live e
  integrarla, non sovrascriverla.
- Restano valide le trappole dell'handoff precedente: un solo pytest per
  volta; mai `git checkout` su lavoro non committato, muta solo contro un
  backup; `ps` non esiste nel container; il codice di uscita dietro una pipe
  mente; `git-commit-assistant` va verificato con `git log` e `git status`.

## Come verificare lo stato

```bash
git branch --show-current            # 20260826-144432-demography-plan4-wiring
git status --short                   # vuoto
git rev-list --count develop..HEAD   # 73
git rev-list --count HEAD..develop   # 0
docker compose -f docker-compose.local.yml exec -T web pytest -q        # 1765 passed
docker compose -f docker-compose.local.yml exec -T web ruff check .
docker compose -f docker-compose.local.yml exec -T web ruff format --check .   # 340 files
```

Se un numero non torna, fermarsi e dirlo invece di procedere.
