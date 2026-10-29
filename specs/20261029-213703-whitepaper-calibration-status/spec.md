# Specifica: stato reale delle calibrazioni nei whitepaper

**Branch**: `20261029-213703-whitepaper-calibration-status`
**Creata**: 2026-10-29
**Stato**: BOZZA, in attesa del responsabile del progetto. È una proposta
(decisione della Trinità D-29-36), non una modifica del Plan 4: rovescia un
requisito approvato, FR-017 della spec del Plan 4, e quindi entra solo con la
sua approvazione esplicita.
**Contratto API invariato**: il work item tocca solo documentazione, due
docstring e un test; nessuna rotta, campo o codice d'errore cambia.

## Perché

Il Plan 4 della demografia ha cablato i moduli demografici nel ciclo di tick e
non ha calibrato nulla. È chiuso in attesa del merge. I due whitepaper
(`docs/whitepaper/epocha-whitepaper.md` e `.it.md`) però continuavano a dire
che una serie di calibrazioni era «rinviata al Plan 4»: la mortalità di
Heligman-Pollard, i coefficienti di Becker (debito B2-07), la scheda di
Hadwiger, i parametri di aspettative, credito e mercato immobiliare, il debito
A-5. Prima della chiusura quella formula descriveva un piano; dopo la chiusura
si legge come una promessa mantenuta o in corso, e non lo è.

Il caso più grave è il §4.1.1. Diceva che i valori di Heligman-Pollard dei
template erano «nell'ordine di grandezza dei loro target», ma non sono mai
stati stimati. Calcolata dai parametri spediti, la speranza di vita completa
alla nascita (`e0`) dei due template pre-industriali è 70,7 anni, contro i
38,47 dell'Inghilterra nel 1701. La mortalità infantile del template è 29 per
mille, contro 190,7 per mille nel 1700-1724 e 190,8 nel 1725-1749: un fattore
di circa 6,6 (191 / 29,11 = 6,56). Un lettore che si fida del paragrafo crede
calibrata una mortalità che è fuori di un fattore sei sul primo anno di vita.

## Deviazione esplicita da FR-017

FR-017 della spec del Plan 4 (`specs/20260826-144432-demography-plan4-wiring/spec.md`,
righe 282-286) dice che le occorrenze di «Plan 4» che rinviano calibrazioni
«restano vere e non si toccano», perché cancellarle «sarebbe un difetto opposto
e uguale»: il lettore perderebbe l'informazione che la calibrazione manca.

La posizione di FR-017 era giusta quando il Plan 4 era aperto: il rinvio era un
fatto e toglierlo avrebbe fatto sembrare calibrato ciò che non lo è.

La posizione di questa proposta è che, a Plan 4 chiuso, «rinviata al Plan 4» è
diventata falsa nell'altra direzione, perché promette una consegna che non
arriverà da lì. La proposta non cancella i rinvii: sostituisce ciascuno con lo
stato vero, cioè «non calibrato, calibrazione non ancora programmata» oppure,
dove il work item esiste nella build map, «registrato nella build map e non
ancora aperto». Dove serve a capire la storia, il testo dice anche che il
compito era assegnato al Plan 4 e che il Plan 4 non l'ha eseguito. Quindi la
calibrazione continua a leggersi come pendente, che è la proprietà che FR-017
voleva proteggere.

Se il responsabile del progetto rifiuta la deviazione, il branch non va
mergiato e FR-017 resta com'è; le correzioni numeriche (Appendice A.4, §4.1.1)
andrebbero allora portate in un commit separato, perché sono errori a
prescindere da FR-017.

## Cosa cambia

1. **Rinvii al Plan 4** in entrambi i whitepaper: ogni passo che prometteva una
   calibrazione «in Plan 4» dichiara lo stato vero (commit `baafab4`). Le
   occorrenze della stringa `Plan 4` scendono da 83 a 55 nel file inglese e da
   85 a 52 in quello italiano; quelle rimaste raccontano ciò che il Plan 4 ha
   consegnato o non ha consegnato, con la formula «chiuso in attesa del merge».
2. **§4.1.1**: i valori di Heligman-Pollard dichiarati mai stimati, la colonna
   della Tabella 4.2 rinominata in target previsto, le `e0` misurate (70,7;
   78,1; 86,8; circa 120 per `sci_fi`) con la convenzione dichiarata (speranza
   di vita completa, forza di mortalità costante entro ogni anno di età; la
   versione per anni compiuti varrebbe 70,24), il confronto con l'Inghilterra
   e le sue fonti, il tasso netto di riproduzione di circa 1,9 con le sue
   condizioni.
3. **Appendice A.4**: `maternal_mortality_rate_per_birth` e
   `neonatal_survival_when_mother_dies` allineati ai file JSON dei template
   (0,008 / 0,003 / 0,0001 / 0,00001 e 0,30 / 0,50 / 0,90 / 0,99 per
   pre-industriale, industriale, democrazia moderna, sci-fi); la tabella
   riportava 0,012, 0,005 e 0,95.
4. **Bibliografia del §13**: Galley (2023) con tabella e pagina, Munro (s.d.)
   come fonte secondaria dichiarata, Wrigley et al. (1997) citato solo
   attraverso quelle due.
5. **Docstring** di `fertility.py` e `mortality.py` che promettevano una
   calibrazione nel Plan 4 (commit `4a1eb6a`).
6. **Test** `epocha/apps/demography/tests/test_template_life_expectancy.py`,
   che calcola la `e0` completa di ogni template con le funzioni di
   `mortality.py` e fissa i valori pubblicati.

## Criteri di successo

- **Inventario prima e dopo.** Un grep sui pattern di promessa al Plan 4
  («deferred to Plan 4», «in Plan 4», «rinviata al Plan 4» e simili) trova 23
  righe nel file inglese e 3 in quello italiano al commit base `3c1e2c0`, e 0
  in entrambi dopo. Il grep è un innesco di revisione, come dice FR-017a, non
  un cancello: la chiusura si dichiara rileggendo ogni passo toccato.
- **Parità bilingue.** Ogni modifica compare in entrambi i file con lo stesso
  contenuto: stessi numeri, stesse fonti, stesse condizioni. L'unica modifica
  presente in un solo file è la virgola mancante nel paragrafo della roadmap
  del file italiano, che allinea l'italiano all'inglese.
- **Nessuna numerazione cambiata.** Titoli, numeri di equazione e numeri di
  tabella restano quelli del commit base.
- **Pin intatto.** Il valore `frozen-at-commit` in testa ai whitepaper non
  cambia; lo aggiorna la chiusura del work item, non questo branch.
- **Test della `e0`.** Il test passa sui template spediti ed è stato visto
  fallire cambiando un valore atteso.

## Limiti noti

- Le fonti inglesi sono lette di seconda mano. `e0` = 38,47 viene dalla
  trascrizione dell'appendice 9 di Wrigley et al. (1997) fatta da Munro in una
  dispensa dell'Università di Toronto. La mortalità infantile viene dalla
  Tabella 2.15 di Galley (2023, p. 92), che ho letto nell'edizione online il
  2026-10-29 e che riporta Wrigley et al. (1997, p. 226). Né il libro del 1997
  né quello di Wrigley e Schofield (1981) sono stati aperti.
- Il tasso netto di riproduzione di circa 1,9 è un limite superiore analitico,
  senza vedovanza e senza mortalità materna, e dipende da due branch non
  mergiati: la fertilità coniugale (`20261029-185654-marital-fertility`,
  approvata in via provvisoria dalla Trinità con D-29-31, in attesa della
  conferma di fase 2 del responsabile del progetto) e la nuzialità delle
  coppie (`20261029-123404-rule-based-couples`).
- Il test fissa i valori, non li giudica: dice che whitepaper e template sono
  coerenti fra loro, non che i template sono giusti. La ricalibrazione resta un
  work item della build map (`spine2.n9`), non ancora aperto.

## FAQ

**Perché non lasciare «rinviata al Plan 4» e aggiungere una nota?** Perché il
lettore incontra la formula in ventitré righe del file inglese e la nota in
una sola. Un
whitepaper che si contraddice tra un paragrafo e l'altro viene letto nel
paragrafo che dà la risposta più comoda.

**Perché la speranza di vita completa e non quella per anni compiuti?** È la
`e0` che riportano le tavole di vita pubblicate, compreso il 38,47 di Wrigley
et al. (1997), quindi il confronto ha senso solo con la stessa convenzione. La
versione per anni compiuti (70,24) è dichiarata accanto per evitare che
qualcuno la ricalcoli e creda di aver trovato un errore.

**Perché il confronto usa il libro del 1997 se la Tabella 4.2 nomina quello del
1981?** Perché i valori che ho trovato vengono dalla ricostruzione delle
famiglie del 1997, attraverso Munro e Galley; le tavole del 1981 non sono state
lette. Il testo lo dice in chiaro invece di attribuire al 1981 un numero preso
dal 1997.

**Il test introduce un helper nuovo nel codice di produzione?** No. La funzione
che calcola la `e0` vive nel file di test e usa solo
`annual_mortality_probability` e `load_template`, cioè le funzioni che il ciclo
di tick usa davvero.

**Che cosa succede se qualcuno ricalibra i template?** Il test diventa rosso, ed
è il comportamento voluto: chi cambia i parametri deve aggiornare insieme i
numeri del §4.1.1 nelle due lingue e i valori attesi del test.

**Ci sono rischi di sicurezza o di licenza?** Nessun dato di Wrigley e
Schofield, del UK Data Service o della dispensa di Munro entra nel repository:
il whitepaper cita solo pochi valori pubblicati, ciascuno con la sua fonte, e il
test contiene solo valori calcolati dai template del progetto.
