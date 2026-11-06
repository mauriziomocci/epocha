# Diagnosi della durata del test di T069 (decisione D-05-E-13)

**Data, commit e metodo.** Ho eseguito le misure il 2026-11-06 fra le 01:46 e
le 02:32, sul commit `725bb9f` del ramo `20261029-123404-rule-based-couples`,
nel progetto Docker isolato `epocha-couples`. La macchina era carica da
contenitori di altri progetti (load average fra 7 e 33), quindi i tempi di
orologio di questa notte non sono confrontabili con quelli di
`phase6-measurements.md`. Per questo misuro grandezze che il carico non
sposta: il numero di query SQL, il numero di versioni di riga scritte
(`pg_stat_xact_user_tables`), la dimensione delle tabelle, i buffer letti da
`EXPLAIN (ANALYZE, BUFFERS)` e il numero di chiamate di `cProfile`. Riporto
anche il tempo di database, cioè la somma dei tempi delle query, ma lo uso
solo per confrontare run della stessa sessione.

Lo strumento è una replica del test di T069 scritta nello scratchpad e mai
entrata nel repository: chiama la stessa fixture `_founded_simulation`, applica
le stesse patch e gira gli stessi 156 tick con `run_simulation_loop`. Avvolge
ogni passo del motore (`run_economy`, `run_demography_tick`,
`propagate_information`, `process_faction_dynamics`,
`process_political_cycle`, `evolve_relationships`, `run_memory_decay`,
`capture_and_detect`, `broadcast_tick`) e ogni passo di
`orchestrator.DEMOGRAPHY_STEPS`, e conta le query con
`connection.execute_wrapper`. Una prima versione usava `CaptureQueriesContext`
e contava zero dopo circa 60 tick, perché `connection.queries_log` è una coda
limitata a 9.000 voci: quando è piena la lunghezza prima e dopo un passo è la
stessa. Quei numeri li ho scartati. La pk della simulazione la fisso con
`setval` sulla sequenza di `simulation_simulation`. La replica riproduce i
valori di T086: alla pk 1 su base nuova l'età maschile media è 23,24 su
n = 7 matrimoni, alla pk 3 dopo una run sulla stessa base 18,20 su n = 6.

## Che cosa non spiega la durata: la popolazione

La popolazione della pk 3 è appena più grande di quella della pk 1, e il
lavoro per tick non cresce più della popolazione. Infatti, su base nuova, la
pk 1 fa 33 nascite, 6 morti, 7 coppie da 7 cercatrici e 48.524 agenti-tick
(la somma dei vivi su ogni tick), la pk 3 fa 63 nascite, 7 morti, 6 coppie da
6 cercatrici e 51.260 agenti-tick, cioè il 5,6% in più. Le query sono 24.724
contro 25.236 (+2,1%), e per tick restano piatte: alla pk 1 sono 148 nei primi dieci tick, 148 a
metà e 182 negli ultimi dieci, alla pk 3 149, 153 e 189. Nessun passo
fa una query per agente che cresce con la popolazione: le funzioni di tick
sono chiamate 156 volte in tutte le run, `decay_memories`
(`epocha/apps/agents/memory.py:49`) 4.669 volte alla pk 1 e 4.937 alla pk 3
(+5,7%, una chiamata per agente vivo ogni dieci tick), `compute_affinity`
(`epocha/apps/agents/affinity.py:118`) 178.784 contro 196.552 (+9,9%, lavoro
di CPU delle fazioni ogni cinque tick, senza query). Il passo 2, la formazione delle coppie con
il mercato a raggio `world`, costa 964 query in 156 tick alla pk 1, sei per
tick, e 1,59 s di tempo di database su 40,0. Quindi un 6-10% di differenza viene dalla popolazione,
e non può spiegare il raddoppio.

## Che cosa la spiega: le versioni di riga dentro una transazione sola

Il test gira dentro una sola transazione, perché `@pytest.mark.django_db`
senza `transaction=True` avvolge il test in un blocco atomico che alla fine
viene annullato. In ogni tick due passi riscrivono gli agenti vivi: l'economia
di riserva
(`epocha/apps/world/economy.py:126`, `bulk_update` di `wealth`, `mood`,
`health`; la fixture non crea valute, quindi `run_economy` sceglie questo
ramo) e `update_social_classes` (`epocha/apps/world/stratification.py:192`,
`bulk_update` di `social_class` per ogni agente vivo anche quando la classe
non cambia, chiamata ogni tick da `epocha/apps/world/government.py:795`). Alla pk 1 su base nuova le versioni di
riga scritte in `agents_agent` sono 98.135, di cui 48.497 dall'economia e
48.524 dalle classi sociali, cioè una per agente vivo per tick in entrambi i
passi (gli agenti-tick sono 48.524); alla pk 3 sono 103.611. Dentro una transazione
aperta PostgreSQL non può potare le versioni vecchie, quindi ogni lettura di
`agents_agent` le visita tutte: al tick 156 l'indice su `simulation_id`
restituisce 98.461 puntatori per 327 agenti vivi (`EXPLAIN` della lettura dei
vivi, 3.841 buffer). Il costo di una query cresce quindi con il tick, a
parità di numero di query: alla pk 1 il tempo medio per query passa da 0,56 ms
nei primi dieci tick a 1,62 a metà e a 2,66 negli ultimi dieci, mentre la
tabella `agents_agent` passa da 1,9 a 15,2 e a 29,3 MiB per 327 righe vive.
Con N agenti e T tick il costo totale va dunque come N per T al quadrato,
anche alla pk 1.

## Perché la pk 1 è veloce e la pk 3 no: lo stato lasciato dalle run precedenti

La pk non è la causa. Lo dimostrano due run in ordine invertito su basi nuove.
Se la pk 3 gira per prima su una base nuova, con gli agenti da 1 a 300, ha la
stessa popolazione della serie di T086 (63 nascite, 7 morti, 6 coppie) e
costa 43,0 s di tempo di database e 25.236 query; se la pk 1 gira subito dopo
sulla stessa base, con gli agenti da 364 a 663, costa 124,2 s e 24.709 query.
Nella sessione precedente, nell'ordine naturale, la pk 1 costava 40,0 s e la
pk 3 dopo di lei 119,5 s. La durata segue quindi la posizione nella base, non
la pk. Il motivo è che l'annullamento della transazione lascia in
`agents_agent` le righe morte della run precedente: all'inizio della seconda
run la tabella ha 103.974 righe morte (`n_dead_tup`) e pesa già 32,8 MiB, e
alla fine i suoi indici pesano 24,9 MiB invece degli 11,7 della stessa
popolazione su base nuova. Nella serie di
T086, con `--reuse-db`, la pk n era l'n-esima sessione sulla stessa base, e
nella suite completa il test di T069 parte dopo molti test che hanno scritto
agenti e annullato; la pk era solo un indicatore di quante run l'avevano
preceduto. La conclusione di `phase6-measurements.md` secondo cui la durata
«dipende dalla popolazione che le estrazioni producono» è quindi sbagliata.

In quello stato il costo si concentra sui tick con una morte. Nella seconda
run il tempo di database di un tick con un decesso sale fino a 26,86 s (pk 1, tick
142), mentre su base nuova i tick con una morte costano fra 0,14 e 0,43 s
alla pk 1 e fra 0,09 e 0,46 s alla pk 3, e lo spendono due
query che la morte fa partire. La prima è la lettura dei legami forti di
`generate_mourning_memories` (`epocha/apps/demography/inheritance.py:3155`),
nel passo di successione; la seconda è la lettura delle relazioni di
`_propagate_memory` (`epocha/apps/agents/information_flow.py:237`), che nei
tick con una morte propaga i ricordi diretti nuovi (quale ricordo la faccia
partire non l'ho verificato; i picchi coincidono con i tick di morte). Entrambe filtrano su
`agent_from` OR `agent_to` con `select_related` dei due agenti, e il
pianificatore le esegue come un ciclo annidato agenti per agenti sulla chiave
primaria di `agents_agent`: 363 per 363, cioè 131.769 giri, 38,1 milioni di
buffer letti e 12,3 s per una sola esecuzione che restituisce zero righe,
perché la tabella `agents_relationship` è vuota (pk 3, seconda run; 33,1
milioni di buffer e 10,8 s nella pk 1 in seconda posizione). Le due query
valgono 44,2 s su 119,5 nella pk 3 in seconda posizione (13 esecuzioni) e
47,5 s su 124,2 nella pk 1 in seconda posizione (12 esecuzioni); il resto è la crescita generale del
costo per query, che negli ultimi dieci tick arriva a 10,51 ms. Le statistiche
del pianificatore su `agents_agent` sono assenti in entrambi gli stati
(`reltuples = -1`, mai analizzata) e le stime sono di una riga; su base nuova
queste query non sono fra le più costose e non ne ho il piano, quindi non ho
verificato se il piano sia lo stesso su un indice più piccolo o un altro; i
buffer letti mostrano che nel caso lento il costo segue la dimensione
dell'indice, che contiene anche le righe morte.

## Verifica del rimedio sul test: transazioni vere come in produzione

In produzione ogni tick è un task Celery, e fuori dalle richieste HTTP Django
lavora in autocommit (`ATOMIC_REQUESTS` di `config/settings/base.py:26` vale
solo per le viste), quindi le versioni vecchie vengono potate dopo il commit.
Ho ripetuto la replica con `@pytest.mark.django_db(transaction=True)`, cioè con
commit reali e svuotamento delle tabelle alla fine del test, come fanno già
`epocha/apps/demography/tests/test_migration.py:3293` e i test di `chat` e
`knowledge`. Con la pk 3 su base nuova il tempo di database scende a 11,2 s, la
tabella resta a 2,2 MiB e il tempo per query resta fra 0,56 e 0,43 ms dal
primo all'ultimo tick; con la pk 1 subito dopo, 12,6 s. Il caso che conta per
la suite l'ho provato a parte: una run annullata della pk 3 (49,9 s di
database, 103.974 righe morte lasciate) seguita dalla pk 1 con
`transaction=True`, che parte da una tabella di 33,6 MiB e costa comunque
12,2 s, con il tempo per query fra 0,58 e 0,44 ms e nessun tick di morte sopra
0,11 s. Le query in modalità transazionale sono circa 23.000 invece di 25.000
perché i blocchi atomici diventano transazioni vere invece di coppie
`SAVEPOINT`/`RELEASE`; in quella modalità i contatori `pg_stat_xact` valgono
per singola transazione e non li uso. L'età maschile indicativa cambia con la
modalità e con le chiavi degli agenti (19,03 e 19,87 alla pk 3, 23,24, 24,67 e
24,95 alla pk 1), come `phase6-measurements.md` aveva già osservato: è un
valore di log, non un'asserzione. Le asserzioni del test passano in tutte le
run. Il test di T069 vero, senza strumenti e a macchina quieta, con
`transaction=True` non l'ho misurato.

## Rimedi e costi

**(a) Difetto di scala da correggere.** La crescita come T al quadrato esiste
solo dentro una transazione lunga, quindi nel motore di produzione non c'è
(verificato sulla replica transazionale, non in un ambiente reale). Restano
due difetti veri, fuori da questo work item. `update_social_classes` scrive
ogni agente a ogni tick anche quando la classe non cambia (51.260 delle
103.611 versioni alla pk 3); la correzione è scrivere solo gli agenti la cui
classe cambia, con un test che conta le righe aggiornate in un tick senza
cambi di ricchezza e si aspetta zero. Le due letture di relazioni con OR su
due chiavi esterne e doppio `select_related` hanno un piano fragile, agenti
per agenti, che in produzione comparirebbe con statistiche vecchie; la
correzione è leggere gli id con due filtri separati, o con `UNION`, e
caricare gli agenti a parte, con un test che fissa il numero di buffer o la
forma del piano. Entrambi toccano `world` e `agents`, non la demografia, e
vanno in work item propri.

**(b) Test indipendente dallo stato della base.** Fissare la pk o lo stream
non serve, perché la pk non è la causa: la pk 3 su base nuova è veloce.
Ridurre la popolazione abbassa il costo ma lascia la dipendenza dalle run
precedenti. Il rimedio che toglie la causa è segnare il test di T069 con
`@pytest.mark.django_db(transaction=True)`, una riga più una frase nel
docstring del modulo, che oggi spiega perché la simulazione è `running` e
dovrebbe dire anche perché le transazioni sono vere. Costa lo svuotamento
delle tabelle alla fine del test e allinea il test al motore di produzione,
che fa un commit per tick.

**(c) Limite giustificato.** Alzare il limite di 120 s non regge: con la
transazione unica il costo dipende da quante righe morte hanno lasciato i
test precedenti, che crescono con la suite senza un tetto, quindi nessun
valore è giustificabile.

**Raccomandazione.** Raccomando (b): `transaction=True` sul test di T069, con
una nuova misura del test vero a macchina quieta prima di chiudere il gate, e
i due difetti di (a) registrati come work item separati in build map.
Questa è una raccomandazione: la decisione resta a chi coordina, secondo
D-05-E-13, e in questo task non ho cambiato né il test, né il limite, né la
spec, né il codice di produzione.
