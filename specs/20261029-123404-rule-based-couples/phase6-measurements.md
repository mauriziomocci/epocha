# Misure di fase 6 — coppie a regole (T086)

**Data e commit.** Ho eseguito le misure il 2026-11-06 fra le 00:41 e le
le 01:31, sul commit `7d3569b` del ramo `20261029-123404-rule-based-couples`
(gli script e il codice misurati sono quelli di quel commit; questo file
arriva nel commit successivo e non cambia codice). La macchina era quieta: il
coordinatore aveva fermato gli altri progetti di test, e ho eseguito un solo
comando pesante alla volta, nel progetto Docker isolato `epocha-couples`.

**Stato della mortalità del Plan 4 che queste misure riflettono.** La
correzione `0e83df4` della decisione di gate D-29-20 è nella storia del
commit misurato (verificato con `git merge-base --is-ancestor`): il ciclo dei
tick addebita la mortalità con `orchestrator.mortality_probability_for`, cioè
`tick_mortality_probability` valutata a `exposure_age`, l'età all'inizio
dell'intervallo del tick, e `mortality.py` legge q_x all'età compiuta senza il
vecchio limite `max(age, 0.01)`. Con questa mortalità la tavola per età intere
dà l(25) = 0,9297 e il ciclo dei tick a tick mensili la realizza esattamente
(l(12) della tavola 0,9480, l_tick(12) del ciclo 0,9480). I numeri di prima di
`0e83df4` non sono confrontabili con questi.

## Correzione dell'harness prima della misura (`7d3569b`)

Prima di misurare ho corretto un difetto della stessa classe di D-05-E-12.
Il docstring di `scripts/measure_nuptiality_fertility.py` dichiarava che
l'harness applicava la mortalità dopo il termine di fecondità, mentre
`orchestrator.DEMOGRAPHY_STEPS` esegue la formazione delle coppie (passo 2),
poi la mortalità (passo 3, con la coppia sciolta dalla successione al passo
4), poi la fecondità (passo 7), che legge solo le donne vive
(`is_alive=True`) e le coppie attive (`dissolved_at_tick` nullo). Quindi nel
motore una donna o un marito che muore a un tick non conta per le nascite di
quel tick, e nell'harness invece contava. Ora un tick dell'harness è
`replicate_tick` (mercato, mortalità, poi i conteggi che la fecondità legge),
e `test_measurement_harness_rules.py` ne fissa l'ordine: il test è andato
rosso sull'ordine vecchio (in coppia 1 invece di 0 quando muore la donna o il
marito al tick) ed è verde su quello nuovo. Con 2 repliche la configurazione
B passa da TFR 2,3600 a 2,3596 e il NRR dell'harness da [1,0035, 1,1235] a
[1,0033, 1,1232]: le estrazioni sono le stesse, si è spostato solo il punto in
cui si conta. La configurazione A non cambia (2,3833 contro il riferimento
2,3841).

## SC-005, costo del mercato (`scripts/measure_marriage_market_cost.py`)

Ho eseguito lo script tre volte di seguito con il seme di default 20261029,
per riportare il rumore accanto al numero come chiede D-05-E-11. Il criterio
di fallimento è un esponente stimato sopra 2,3 (la complessità dichiarata
N²·log N ha esponente locale 2,11 fra 10³ e 10⁵).

| Misura | Run 1 | Run 2 | Run 3 | Limite |
|---|---|---|---|---|
| Passo 2, secondi a N = 10³ / 10⁴ / 10⁵ | 0,0003 / 0,0103 / 1,2201 | 0,0004 / 0,0116 / 1,2297 | 0,0003 / 0,0097 / 1,2557 | |
| Passo 2, esponente ai minimi quadrati | 1,784 | 1,751 | 1,798 | 2,3 |
| Passo 2, pendenza fra 10⁴ e 10⁵ (non vincolata) | 2,074 | 2,024 | 2,113 | |
| Fondazione, secondi a N = 10³ / 10⁴ (mediana di 3) | 0,0640 / 7,5953 | 0,0584 / 6,9980 | 0,0579 / 7,2583 | |
| Fondazione, esponente del tempo (due punti) | 2,074 | 2,078 | 2,098 | 2,3 |
| Fondazione, memoria di picco a 10³ / 10⁴ | 4,4 / 380,4 MiB | 4,4 / 380,4 MiB | 4,4 / 380,4 MiB | |
| Fondazione, esponente della memoria | 1,933 | 1,933 | 1,933 | 2,3 |
| Estrapolazione a 10⁵ (non misurata) | 901 s, 31,9 GiB | 838 s, 31,9 GiB | 911 s, 31,9 GiB | |
| Esito | pass | pass | pass | |

Le popolazioni sintetiche sono le stesse nelle tre run (stesso seme): a
N = 10⁵ il passo 2 estrae 33 cercatrici contro 30.054 uomini e forma 33
coppie, la fondazione a 10⁴ dichiara sposate 1.856 donne contro 2.990 uomini.
Il rumore fra le run, a macchina quieta, è quindi solo di tempo: l'esponente
del passo 2 varia di 0,047 (da 1,751 a 1,798), quello del tempo di
fondazione di 0,024 (da 2,074 a 2,098), la memoria per niente. La run di
fase 11 (D-05-E-11), a macchina carica, aveva dato per la fondazione un
esponente fra 1,93 e 2,19: lo scarto di allora era quindi il carico e non il
codice. Il margine più stretto è quello del tempo di fondazione, 0,20 sotto
il limite nella run peggiore. Nessuna condizione di SC-005 scatta. Le cifre a
10⁵ della fondazione sono un'estrapolazione con l'esponente misurato, non una
misura, come la spec chiede.

## SC-007, nuzialità e fecondità (`scripts/measure_nuptiality_fertility.py --replicates 20`)

Venti repliche di 20.000 donne, 456 tick mensili, semi da 1 a 20, raggio
`world`, sul commit `7d3569b` (ordine del motore: mercato, mortalità,
fecondità). La configurazione A ha richiesto 302 s, la B 309 s.

| Configurazione | TFR, media ± semiampiezza t al 95% | Riferimento | Scarto | NRR dell'harness [t al 95%] | NRR analitico | l(25) |
|---|---|---|---|---|---|---|
| A, senza mortalità | 2,3866 ± 0,0060 | 2,3841 (propagazione) | +0,0024 | — | — | — |
| B, mortalità, vedovanza, lutto, r_f | 2,3688 ± 0,0056 | nessuno (senza soglia) | — | 1,0677 [1,0652, 1,0702] | 1,0700 (scarto −0,0023) | 0,9297 |

Nella configurazione A l'errore standard delle repliche è 0,0029, quindi lo
scarto di +0,0024 dalla propagazione deterministica vale 0,85 errori
standard, sotto il limite di 3. Il valore continuo dell'integrale è 2,3736 e
lo scarto di discretizzazione della propagazione mensile è +0,0105, riportato
e non vincolato. Il massimo di cercatrici in un tick è 172 (limite 500),
quindi l'ipotesi di uomini sempre disponibili regge. La condizione di
fallimento di A non scatta.

Nella configurazione B il TFR è calcolato con M(a) fra le donne vive
(SC-007, D-05-E-12) e non ha soglia, perché vedovanza e r_f sono euristiche.
Il NRR dell'harness è l_tick(12) per le nascite per donna iniziale divise per
1 + 1,05; il suo intervallo al 95% è [1,0652, 1,0702], con il limite
superiore sopra 1, quindi la condizione di fallimento di B non scatta. Il
valore analitico 1,0700 (u = 25,580, senza vedovanza) cade dentro
l'intervallo, 0,0002 sotto il bordo superiore: la vedovanza abbassa il NRR di 0,0023 rispetto al
calcolo analitico, al netto del rimatrimonio con r_f. La mortalità materna
del template (0,008 per nascita) non è modellata, né nell'harness né nel
valore analitico. Il massimo di cercatrici in un tick è 171 (limite 500).

Il margine del NRR sopra 1 resta del 6,8% (limite inferiore dell'intervallo
6,5%). Questo controllo va **rieseguito quando la mortalità del template
viene ricalibrata** (rinvii 2 e 9 della spec): il margine dipende da quella
mortalità, che D-29-18 giudica troppo leggera rispetto ai valori storici, e
una mortalità più pesante lo riduce. Né questo work item né quello della
fecondità coniugale si consegnano dopo quella ricalibrazione senza la nuova
esecuzione.

## Età maschile indicativa al primo matrimonio (test di T069)

Ho eseguito `epocha/apps/simulation/tests/test_rule_based_couples_integration.py`
da solo con `-o log_cli=true --log-cli-level=INFO`, in una sessione pytest
nuova (base di test creata e distrutta, quindi simulazione con pk 1), a
macchina quieta: il test passa, la chiamata del test dura **67,11 s** e la
sessione 70,69 s (73 s di orologio nel contenitore), sotto il limite di 120 s
del piano (Rinvii R7). La riga di log dice: età maschile media indicativa al
primo matrimonio **23,24 anni su n = 7 matrimoni**, e 0 delle 7 coppie formate
dopo l'inizializzazione vengono da intenti (K = 0, come atteso).

Il valore dipende dalla chiave primaria della simulazione, perché gli stream
casuali sono derivati da `(simulation, tick, phase)`. Per misurarne la
dispersione ho ripetuto il test in sessioni successive con `--reuse-db`: le
sequenze di PostgreSQL sopravvivono al rollback di ogni test, quindi ogni
sessione riceve la pk successiva. Il test non è stato modificato.

| pk della simulazione | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|
| Età maschile media (anni) | 23,24 | 20,18 | 18,20 | 20,16 | 27,36 | 29,97 | 27,41 | 28,61 | 23,75 |
| Matrimoni n | 7 | 5 | 6 | 3 | 9 | 6 | 10 | 2 | 10 |
| Coppie da intenti | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Durata della sessione (s) | 70,00 | 77,52 | 151,13 | 157,91 | 158,13 | 129,35 | 132,12 | 150,48 | 195,99 |

Sulle nove pk la media delle medie per run è **24,32 anni**, deviazione
standard 4,22, intervallo t al 95% con 8 gradi di libertà **[21,08, 27,56]**;
la media ponderata sui 58 matrimoni è 24,62 (calcolata dalle medie per run
arrotondate a due decimali). I riferimenti sono 27,02 anni, la media maschile
dei matrimoni fra celibi e nubili dei decenni 1700-1749 di Wrigley et al.
(1997, pp. 130-34) letta nella copia secondaria di Munro, e 27,1, la colonna
«National» di Newton per il 1701-50. Entrambi cadono dentro l'intervallo, ma
il confronto non è una validazione: ogni run poggia su 2-10 matrimoni di una
popolazione di 300 fondatori in tre anni, e l'intervallo misura la
dispersione fra le pk, non l'errore di un modello calibrato. Il valore passa
al work item di validazione come indicazione.

Il valore non dipende solo dalla pk della simulazione. La pk 1 ha dato 23,24
su 7 in sei sessioni diverse (determinismo a parità di stato della base),
mentre la pk 3 ha dato 18,20 su 6 nella serie e 18,70 su 6 in una run di
controllo in cui avevo portato la sequenza delle simulazioni a 3 su una base
che aveva ospitato una sola run invece di due. Quindi l'esito dipende anche
dalle altre chiavi primarie (agenti, zone, mondo), che cambiano con lo stato
della base; non ho isolato quale.

**Durata del test: correzione (D-05-E-14).** Il paragrafo di questa sezione
scritto in origine attribuiva la durata alla popolazione che le estrazioni
producono. Quell'affermazione è sbagliata. La diagnosi
(`phase6-t069-diagnosis.md`) mostra che la popolazione cambia il lavoro di
circa il 6-10%, mentre la durata raddoppia perché il test girava in una sola
transazione: due passi riscrivono ogni agente vivo a ogni tick, PostgreSQL non
può potare le versioni vecchie finché la transazione resta aperta, e le righe
morte lasciate dai test precedenti nella stessa base rendono ogni query più
lenta. La pk era solo un indicatore di quante run avevano preceduto il test.
Le durate della tabella qui sopra (129-196 s alle pk da 3 a 9) misurano
quindi quello stato della base, non la pk né la popolazione.

La decisione D-05-E-14 ha marcato il test con
`@pytest.mark.django_db(transaction=True)`, cioè con commit reali come fa il
motore in produzione (un commit per tick), lasciando invariato il limite di
120 s. Ho rimisurato il test così modificato (commit `6f0925d`), nel progetto
isolato `epocha-couples`, con il load average della macchina fra 5 e 8
(non quieta): da solo con `--create-db` la sessione dura 41,96 s (load 6,20
all'inizio, 5,21 alla fine); in una sola invocazione dopo
`test_demography_e2e.py` (due prove lunghe di demografia) la chiamata del test
dura 50,18 s (load 5,11 all'inizio, 5,30 alla fine) e, ripetuta subito dopo
sulla stessa base, 54,10 s (load 5,30 all'inizio, 8,56 alla fine). Tutte le
asserzioni passano. I tempi sono sotto il limite di 120 s anche con la
macchina carica e non dipendono più dai test eseguiti prima.

## Decisioni a cui queste misure si riferiscono

D-05-E-11 (provvisoria, Matteo, 06/11 00:10) ha fissato la convenzione
dell'età all'inizio del tick (`_effective_age_in_years`) per l'harness e ha
lasciato SC-005 com'è scritto, con la misura finale a macchina quieta e il
rumore riportato accanto al numero: è ciò che faccio nella sezione SC-005, e
la normalizzazione per valutazione di punteggio resta una proposta per
l'utente. D-05-E-12 (provvisoria, Matteo, 06/11 00:40) ha corretto D-05-E-11:
l'harness segue l'ordine dei passi del motore, con la formazione delle coppie
prima della fecondità, il riferimento di A è 2,384 e il TFR di B si calcola
fra le donne vive. La correzione di `7d3569b` estende la stessa regola alla
mortalità, che nel motore precede la fecondità.

## Condizioni di fallimento

SC-005 non fallisce in nessuna delle tre run, e SC-007 non fallisce in
nessuna delle due configurazioni. Il test di T069 con commit reali
(D-05-E-14) dura fra 42 e 54 s, sotto il limite di 120 s del piano
(Rinvii R7), anche dopo altre prove lunghe di demografia nella stessa
invocazione. La condizione di fallimento registrata in origine per T069 era
un artefatto della transazione unica del test, non una proprietà del modello
(si veda la correzione sopra e `phase6-t069-diagnosis.md`). Due difetti veri
trovati dalla diagnosi, fuori da questo work item, restano da aprire come work
item propri: la scrittura di `social_class` per ogni agente a ogni tick in
`update_social_classes` e le due letture di relazioni con OR su due chiavi
esterne.
