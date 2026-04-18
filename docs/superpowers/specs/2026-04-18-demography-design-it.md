# Progetto del sottosistema Demografia

**Data**: 2026-04-18
**Stato**: approvata per implementazione
**Paradigma**: ciclo biologico completo (nascita, invecchiamento, riproduzione, ereditarietà, migrazione, morte) come processo emergente a livello di agente, calibrato su dati demografici storici.
**Dipende da**: Economy Spec 1 (neoclassica, completata), Economy Spec 2 Parts 1-3 (comportamentale, completata). Non richiede dati esterni all'inizializzazione.
**Audit**: critical self-review a due passi completato (vedi Audit Resolution Log).

> **Nota bilingue**: questa è la versione italiana della spec. La versione primaria in inglese è `2026-04-18-demography-design.md` nella stessa directory. Le due versioni sono tenute sincronizzate ad ogni revisione. Citazioni bibliografiche, formule, nomi di codice, nomi di modelli scientifici restano nelle lingue originali senza traduzione.

## Scopo e ambito

Epocha necessita di un layer di dinamica della popolazione rigoroso. Senza demografia le civiltà non possono avere dinastie, ricambio generazionale, variazione dell'offerta di lavoro, flussi migratori, accumulazione ereditaria della ricchezza. Lo scenario "Rivoluzione Francese", già in uso, non può credibilmente simulare ciò che annuncia senza nascite, morti e famiglie.

Questo design consegna un sottosistema demografico auto-contenuto che:

1. Simula la mortalità individuale tramite curve di rischio analitiche calibrate per era storica (Heligman & Pollard 1980);
2. Simula la fertilità combinando tassi biologici età-specifici (Hadwiger 1940) con modulazione economica (Becker 1991);
3. Modella la formazione di coppie tramite un mercato del matrimonio a stable matching (Gale & Shapley 1962) con scelta LLM, includendo il matrimonio combinato come opzione d'era (Goode 1963);
4. Eredita tratti biologici tramite genetica polygenic additive con coefficienti di heritability dalla meta-analisi Polderman et al. (2015);
5. Trasferisce la ricchezza alla morte tramite regole per-era (primogenitura, divisione equa, shari'a, matrilineare, nazionalizzazione) con estate tax opzionale, seguendo il framework di Piketty (2014) per la trasmissione intergenerazionale del capitale;
6. Arricchisce le decisioni di migrazione con differenziali di salario attesi Harris-Todaro (1970), coordinamento familiare Mincer (1978), e flight migration sotto starvation (O'Rourke 1994);
7. Applica un soft cap malthusiano sui tassi di nascita (Malthus 1798; Ricardo 1817; Ashraf & Galor 2011) con duplice funzione di realismo scientifico e protezione del budget computazionale;
8. Si valida automaticamente contro il baseline pre-industriale di Wrigley-Schofield (1981) e contro pattern di risposta a carestia (O'Rourke 1994), producendo output benchmarkabile per pubblicazione.

**Cosa questa spec NON consegna** (deferred):
- Mortalità da malattia (epidemie SIR/SEIR) — pianificato come sottosistema epidemiologia separato
- Template d'era di transizione con parametri time-varying (mortality transition 1750-1900, fertility transition 1870-1960)
- Adozione, step-parenting, concepimento da donor
- Meccanica del marriage market poliandrico oltre la dichiarazione di tipo
- Migrazione di ritorno come flusso esplicito
- Trasmissione intergenerazionale culturale/linguistica/religiosa oltre i tratti di personalità
- Decisioni di carriera e istruzione del ciclo di vita
- Ereditarietà di famiglia estesa oltre 2 generazioni

## Fondamenti scientifici

**Mortalità**
- Heligman, L. & Pollard, J.H. (1980). The age pattern of mortality. *Journal of the Institute of Actuaries* 107(1), 49-80.
- Gompertz, B. (1825). On the nature of the function expressive of the law of human mortality. *Philosophical Transactions of the Royal Society* 115, 513-583.
- Makeham, W.M. (1860). On the law of mortality and the construction of annuity tables. *Journal of the Institute of Actuaries* 8, 301-310.

**Fertilità**
- Hadwiger, H. (1940). Eine analytische Reproduktionsfunktion für biologische Gesamtheiten. *Skandinavisk Aktuarietidskrift* 23, 101-113.
- Chandola, T., Coleman, D.A. & Hiorns, R.W. (1999). Recent European fertility patterns: fitting curves to 'distorted' distributions. *Population Studies* 53(3), 317-329.
- Schmertmann, C.P. (2003). A system of model fertility schedules with graphically intuitive parameters. *Demographic Research* 9, 81-110.
- Becker, G.S. (1991). *A Treatise on the Family*, enlarged edition. Harvard University Press.
- Coale, A.J. & Watkins, S.C. (eds.) (1986). *The Decline of Fertility in Europe*. Princeton University Press.
- Jones, L.E. & Tertilt, M. (2008). An economic history of fertility in the U.S., 1826-1960. In Rupert, P. (ed.), *Frontiers of Family Economics* 1, 165-230.
- Bongaarts, J. & Bruce, J. (1995). The causes of unmet need for contraception and the social content of services. *Studies in Family Planning* 26(2), 57-75.
- Lee, R.D. (1987). Population dynamics of humans and other animals. *Demography* 24(4), 443-465.

**Formazione di coppia e matrimonio**
- Gale, D. & Shapley, L.S. (1962). College admissions and the stability of marriage. *American Mathematical Monthly* 69(1), 9-15.
- Becker, G.S. (1973). A theory of marriage: Part I. *Journal of Political Economy* 81(4), 813-846.
- Goode, W.J. (1963). *World Revolution and Family Patterns*. Free Press.
- Hajnal, J. (1965). European marriage patterns in perspective. In Glass, D.V. & Eversley, D.E.C. (eds.), *Population in History*, 101-143. Arnold.
- Kalmijn, M. (1998). Intermarriage and homogamy: causes, patterns, trends. *Annual Review of Sociology* 24, 395-421.
- Oppenheimer, V.K. (1988). A theory of marriage timing. *American Journal of Sociology* 94(3), 563-591.
- Holmes, T.H. & Rahe, R.H. (1967). The Social Readjustment Rating Scale. *Journal of Psychosomatic Research* 11(2), 213-218.
- Weiss, R.S. (1975). *Marital Separation*. Basic Books.
- Parkes, C.M. (1972). *Bereavement: Studies of Grief in Adult Life*. International Universities Press.

**Ereditarietà biologica dei tratti**
- Polderman, T.J.C. et al. (2015). Meta-analysis of the heritability of human traits based on fifty years of twin studies. *Nature Genetics* 47(7), 702-709.
- Bouchard, T.J. & McGue, M. (1981). Familial studies of intelligence: a review. *Science* 212(4498), 1055-1059.
- Falconer, D.S. & Mackay, T.F.C. (1996). *Introduction to Quantitative Genetics*, 4th ed. Longman.
- Plomin, R. & Deary, I.J. (2015). Genetics and intelligence differences: five special findings. *Molecular Psychiatry* 20, 98-108.
- Jang, K.L., Livesley, W.J. & Vernon, P.A. (1996). Heritability of the Big Five personality dimensions and their facets: a twin study. *Journal of Personality* 64(3), 577-591.
- Vernon, P.A. et al. (2008). Genetic and environmental influences on individual differences in emotional intelligence. *Emotion* 8(5), 635-642.
- Nichols, R.C. (1978). Twin studies of ability, personality, and interests. *Homo* 29, 158-173.
- Zempo, H. et al. (2017). Heritability estimates of muscle strength-related phenotypes. *Scandinavian Journal of Medicine & Science in Sports* 27(12), 1537-1546.
- Miyamoto-Mikami, E. et al. (2018). Heritability estimates of endurance-related phenotypes. *Scandinavian Journal of Medicine & Science in Sports* 28(3), 834-845.
- Thomis, M.A. et al. (1998). Heritability estimates of strength, motor performance, and cardiorespiratory performance. *American Journal of Human Biology* 10(6), 687-698.
- Zietsch, B.P. et al. (2014). Genetic analysis of human fertility reveals substantial heritability. *Population Studies* 68(3), 251-267.

**Ereditarietà sociale ed economica**
- Becker, G.S. & Tomes, N. (1979). An equilibrium theory of the distribution of income and intergenerational mobility. *Journal of Political Economy* 87(6), 1153-1189.
- Solon, G. (1999). Intergenerational mobility in the labor market. In Ashenfelter, O. & Card, D. (eds.), *Handbook of Labor Economics* Vol. 3A, Ch. 29, 1761-1800. Elsevier.
- Goldin, C. (1995). The U-shaped female labor force function in economic development and economic history. In Schultz, T.P. (ed.), *Investment in Women's Human Capital*, 61-90. University of Chicago Press.
- Piketty, T. (2014). *Capital in the Twenty-First Century*. Harvard University Press.
- Kotlikoff, L.J. & Summers, L.H. (1981). The role of intergenerational transfers in aggregate capital accumulation. *Journal of Political Economy* 89(4), 706-732.
- Clark, G. (2014). *The Son Also Rises: Surnames and the History of Social Mobility*. Princeton University Press.
- Chetty, R. et al. (2014). Where is the land of opportunity? The geography of intergenerational mobility in the United States. *Quarterly Journal of Economics* 129(4), 1553-1623.
- Goody, J., Thirsk, J. & Thompson, E.P. (eds.) (1976). *Family and Inheritance: Rural Society in Western Europe 1200-1800*. Cambridge University Press.
- Thirsk, J. (1976). The European debate on customs of inheritance, 1500-1700. In Goody et al., 177-191.
- Blackstone, W. (1765). *Commentaries on the Laws of England*, Book II. Clarendon.
- Powers, D.S. (1986). *Studies in Qur'an and Hadith: The Formation of the Islamic Law of Inheritance*. University of California Press.
- Schneider, D.M. & Gough, K. (eds.) (1961). *Matrilineal Kinship*. University of California Press.
- Nove, A. (1969). *An Economic History of the USSR*. Allen Lane.

**Migrazione**
- Lee, E.S. (1966). A theory of migration. *Demography* 3(1), 47-57.
- Harris, J.R. & Todaro, M.P. (1970). Migration, unemployment and development: a two-sector analysis. *American Economic Review* 60(1), 126-142.
- Mincer, J. (1978). Family migration decisions. *Journal of Political Economy* 86(5), 749-773.
- O'Rourke, K.H. (1994). The economic impact of the Famine in the short and long run. *European Review of Economic History* 1(1), 3-22.
- Ravenstein, E.G. (1885). The laws of migration. *Journal of the Statistical Society of London* 48(2), 167-235.
- Hatton, T.J. & Williamson, J.G. (2005). *Global Migration and the World Economy*. MIT Press.
- McFadden, D. (1973). Conditional logit analysis of qualitative choice behavior. In Zarembka, P. (ed.), *Frontiers in Econometrics*, 105-142. Academic Press.

**Dinamiche di popolazione e vincoli malthusiani**
- Malthus, T.R. (1798). *An Essay on the Principle of Population*. J. Johnson.
- Ricardo, D. (1817). *On the Principles of Political Economy and Taxation*, ch. 5. John Murray.
- Ashraf, Q. & Galor, O. (2011). Dynamics and stagnation in the Malthusian epoch. *American Economic Review* 101(5), 2003-2041.
- Lotka, A.J. (1925). *Elements of Physical Biology*. Williams & Wilkins.
- Wolowyna, O. (1997). The 1946-47 famine in Ukraine: short- and long-term consequences. *Journal of Ukrainian Studies* 22(1-2), 153-170.

**Dataset di validazione storica**
- Wrigley, E.A. & Schofield, R.S. (1981). *The Population History of England 1541-1871*. Cambridge University Press.
- Mitchell, B.R. (1988). *British Historical Statistics*. Cambridge University Press.
- Bairoch, P. (1988). *Cities and Economic Development*. University of Chicago Press.
- Larmuseau, M.H.D. et al. (2016). Cuckolded fathers rare in human populations. *Trends in Ecology & Evolution* 31(5), 327-329.
- Loudon, I. (1992). *Death in Childbirth: An International Study of Maternal Care and Maternal Mortality 1800-1950*. Clarendon Press.
- Yang, J. (2012). *Tombstone: The Great Chinese Famine 1958-1962*. Farrar, Straus and Giroux.
- Chesnais, J-C. (1992). *The Demographic Transition*. Clarendon Press.
- HMD — Human Mortality Database. University of California Berkeley e Max Planck Institute. mortality.org
- HFD — Human Fertility Database. Max Planck Institute for Demographic Research. humanfertility.org
- UN WPP — World Population Prospects 2022. UN Department of Economic and Social Affairs. population.un.org

**Razionalità limitata e teoria della decisione**
- Simon, H.A. (1955). A behavioral model of rational choice. *Quarterly Journal of Economics* 69(1), 99-118.
- Miller, G.A. (1956). The magical number seven, plus or minus two. *Psychological Review* 63(2), 81-97.

## Integration contracts con i sistemi esistenti

Prima di specificare il sottosistema demografia, definiamo la superficie di integrazione con il sottosistema economia già implementato (Spec 2 Parts 1-3). Queste definizioni sono contratti che questa spec è responsabile di implementare o derivare; non assumono variabili pre-esistenti che in realtà non esistono.

### Subsistence threshold (derivazione)

La demografia necessita di una soglia di sussistenza per la modulazione Becker e per i trigger di flight migration. Il sottosistema economia NON espone attualmente una costante denominata `subsistence_threshold`. La deriviamo dai dati esistenti:

```python
def compute_subsistence_threshold(simulation, zone) -> float:
    """Deriva il costo di sussistenza per agente per tick nella valuta primaria.

    Usa il flag GoodCategory.is_essential esistente, il fabbisogno di sussistenza
    per-bene dal modulo market (default 1.0 unità per agente per tick), e i
    prezzi di mercato correnti nella zona. Il risultato è il flusso minimo di
    ricchezza richiesto per consumare i beni essenziali in quantità di sussistenza.
    """
    from epocha.apps.economy.models import GoodCategory, ZoneEconomy
    SUBSISTENCE_NEED_PER_AGENT = 1.0  # per-bene per-tick, corrisponde alla variabile
                                      # locale `subsistence_need` in economy/market.py:172
    ze = ZoneEconomy.objects.get(zone=zone, simulation=simulation)
    essentials = GoodCategory.objects.filter(simulation=simulation, is_essential=True)
    total = 0.0
    for good in essentials:
        price = ze.market_prices.get(good.code, good.base_price)
        total += price * SUBSISTENCE_NEED_PER_AGENT
    return total
```

Come parte dell'implementazione di QUESTA spec, la variabile locale `subsistence_need = 1.0` in `epocha/apps/economy/market.py` viene estratta come costante a livello di modulo `SUBSISTENCE_NEED_PER_AGENT` per poter essere condivisa. Questa derivazione produce un valore zone-dipendente ed era-dipendente computato on-demand. I confronti di ricchezza usano `agent.wealth < N * subsistence_threshold` dove `N` è il numero di tick di sussistenza che l'agente può sopravvivere con i risparmi attuali (parametro di design tunable, default 30 tick ≈ 1 mese con cadenza tick giornaliera).

### Aggregate economic outlook (derivazione)

La modulazione Becker necessita di uno scalare `[-1, 1]` che riassuma la percezione dell'agente delle condizioni economiche. Nessun attributo del genere esiste su `AgentExpectation`. Lo deriviamo:

```python
def compute_aggregate_outlook(agent) -> float:
    """Produce outlook scalare in [-1, 1] dallo stato esistente.

    Combina:
    - mood dell'agente (0.0-1.0 mappato a -1..1)
    - banking confidence (0.0-1.0 da BankingState.confidence_index mappato a -1..1)
    - zone stability (0.0-1.0 da Government.stability mappato a -1..1)
    Pesi equali; tunable.
    """
    from epocha.apps.economy.models import BankingState
    from epocha.apps.world.models import Government
    mood_norm = 2.0 * agent.mood - 1.0
    try:
        conf_norm = 2.0 * BankingState.objects.get(
            simulation=agent.simulation).confidence_index - 1.0
    except BankingState.DoesNotExist:
        conf_norm = 0.0
    stability_norm = 0.0
    try:
        gov = Government.objects.get(simulation=agent.simulation)
        stability_norm = 2.0 * gov.stability - 1.0
    except Government.DoesNotExist:
        pass
    return (mood_norm + conf_norm + stability_norm) / 3.0
```

Questa è una euristica di design, NON derivata da Jones & Tertilt (2008). Marcata come parametro di design tunable.

### Segnali di salario senza segmentazione di genere

Il sottosistema economia registra i salari in `EconomicLedger.transaction_type="wage"` senza segmentazione di genere. Il framework originale di Becker (1991) usa il *costo opportunità del tempo delle donne* come depressore di fertilità. Nell'MVP non possiamo computarlo direttamente. Sostituiamo con due segnali alternativi entrambi disponibili dai dati esistenti:

1. **Livello medio di salario zonale** (`zone_wage_mean`): media delle transazioni wage in `EconomicLedger` nella zona negli ultimi 5 tick. Salari zonali più alti correlano storicamente con partecipazione femminile più alta alla forza lavoro (Goldin 1995 *The U-Shaped Female Labor Force Function*), che è il meccanismo che Becker identifica.
2. **Frazione di occupazione femminile in ruoli lavorativi** (`female_role_employment_fraction`): `count(agenti con gender=female AND role IN {merchant, craftsman, ...} AND wage>0 ultimo tick) / count(femmine adulte)`. Proxy diretta di partecipazione femminile al lavoro senza richiedere un campo salario gendered.

Usati congiuntamente nella modulazione Becker come alternativa al rapporto di salario gendered. Documentato come adattamento alla disponibilità dati di Spec 2.

### Addizione al treasury del governo (pattern helper)

L'economia di Spec 2 usa mutazione diretta di JSON dict su `Government.government_treasury`. Proponiamo l'estrazione di un helper `add_to_treasury(government, currency_code, amount)` come parte dello scope di QUESTA spec, collocato in `epocha/apps/world/government.py` per essere condiviso con la demografia. Implementazione:

```python
def add_to_treasury(government, currency_code: str, amount: float) -> None:
    """Aggiunge un amount nella valuta data al treasury del governo.

    Estratto nella demography spec del 2026-04-18; i callers precedentemente
    usavano mutazione inline di JSON dict (vedi economy/engine.py:433).
    Centralizzare garantisce accounting consistente attraverso tax,
    estate tax, espropriazione, e multe.
    """
    treasury = government.government_treasury or {}
    treasury[currency_code] = treasury.get(currency_code, 0.0) + amount
    government.government_treasury = treasury
    government.save(update_fields=["government_treasury"])
```

Le chiamate dalla demografia (estate tax routing in `inheritance.py`) usano questo helper. `economy/engine.py:433-436` viene refattorizzato allo stesso helper nel task 1 di Plan 1 della demografia.

### Riferimento velocità di camminata

Il claim "25 km/giorno velocità di camminata" ha origine dal dict `TRAVEL_SPEEDS` in `epocha/apps/agents/movement.py:37`, verificato presente. Il valore 25 km/giorno è documentato con le fonti Chandler (1966) *The Art of Warfare in the Age of Marlborough* e Braudel (1979) *Civilization and Capitalism 15th-18th Century Vol 1*. Il computo del costo di distanza migratoria riusa `movement.compute_travel_ticks()` (funzione esistente) invece di introdurre una nuova costante.

---

## Panoramica di architettura

La demografia vive in una nuova app Django `epocha.apps.demography`, strutturata in parallelo all'app `epocha.apps.economy` esistente. La superficie di integrazione con il resto del sistema è minimale: una funzione orchestrator chiamata dal simulation tick, un blocco di context enrichment per le decisioni degli agenti, e una manciata di nuove azioni LLM. Tutto lo stato interno, gli algoritmi e la calibrazione sono dietro questo boundary.

```
epocha/apps/demography/
├── models.py            # Couple, DemographyEvent, PopulationSnapshot, AgentFertilityState
├── mortality.py         # hazard a 8 parametri Heligman-Pollard
├── fertility.py         # Hadwiger ASFR × modulazione Becker + Malthusian ceiling
├── couple.py            # pair bonding, separation, omogamia Gale-Shapley
├── inheritance.py       # ereditarietà tratti biologici + ereditarietà economica per-era
├── migration.py         # context enrichment + coordinamento familiare + emergency flight
├── initialization.py    # demographic initializer (piramide d'età + coppie + genealogie)
├── rng.py               # RNG seeded per riproducibilità
├── engine.py            # orchestrator process_demography_tick
├── template_loader.py   # parameter set per-era (pre_industrial, industrial, modern, sci_fi)
├── context.py           # build_demographic_context per il decision prompt
├── tests/
└── migrations/
```

### Integrazione con la pipeline di simulazione

```
tick N:
  0. process_economy_tick_new       (esistente)
  1. process_demography_tick        (NUOVO)
  2. process_agent_decisions        (esistente; ora vede lo stato demografico aggiornato)
  3. propagate_information          (esistente; eventi di nascita/morte/coppia si propagano)
  4. process_faction_dynamics       (esistente)
  5. process_political_cycle        (esistente)
  6. capture_and_detect             (esistente)
```

La demografia gira prima delle decisioni degli agenti cosicché i neonati non decidono mai nel loro primo tick, i morti non decidono mai nel loro ultimo tick, e il coniuge sopravvissuto di un partner deceduto vede la perdita riflessa nel decision context dello stesso tick.

### Nuovi modelli

**Couple** — una riga per ogni evento di coppia in una simulazione.

- `agent_a` (FK Agent, null alla morte del coniuge per preservare la genealogia)
- `agent_b` (FK Agent, null alla morte del coniuge per preservare la genealogia)
- `agent_a_name_snapshot` (CharField, blank) — catturato alla dissolution quando agent_a FK viene nullato
- `agent_b_name_snapshot` (CharField, blank) — catturato alla dissolution quando agent_b FK viene nullato
- `formed_at_tick` (PositiveIntegerField)
- `dissolved_at_tick` (PositiveIntegerField, null)
- `dissolution_reason` (CharField, choices: `death`, `separate`, `annulment`)
- `couple_type` (CharField, choices: `monogamous`, `arranged`) — polygynous e polyandrous rinviati a spec futura (vedi fix MISS-8)
- `simulation` (FK Simulation, indicizzato con formed_at_tick)
- Indici: `(simulation, dissolved_at_tick)`, `(agent_a, dissolved_at_tick)`, `(agent_b, dissolved_at_tick)`

**DemographyEvent** — ledger di eventi demografici per analytics, audit trail, riproducibilità paper.

- `simulation` (FK, indicizzato con tick)
- `tick` (PositiveIntegerField)
- `event_type` (CharField, choices: `birth`, `death`, `pair_bond`, `separate`, `migration`, `inheritance_transfer`, `mass_flight`, `trapped_crisis`, `demographic_initializer`)
- `primary_agent` (FK Agent, null per eventi aggregati)
- `secondary_agent` (FK Agent, null)
- `payload` (JSONField, strutturato per event_type — vedi §"Schemi di payload di DemographyEvent")

**PopulationSnapshot** — una riga per simulazione-tick, aggregati per dashboard e validazione.

- `simulation`, `tick`
- `total_alive` (int)
- `age_pyramid` (JSONB: lista di (age_bucket_low, age_bucket_high, count_male, count_female))
- `sex_ratio` (float, M/F)
- `avg_age` (float)
- `crude_birth_rate` (float, per 1000 per equivalente annuale)
- `crude_death_rate` (float, per 1000 per equivalente annuale)
- `tfr_instant` (float, stima total fertility rate dal tick ASFR)
- `net_migration_by_zone` (JSONB: zone_id -> net inflow)
- `couples_active` (int)
- `avg_household_size` (float)
- Unique together: `(simulation, tick)`

**AgentFertilityState** — stato leggero per-agente per il flag di family planning (popolato solo quando il template abilita planned fertility).

- `agent` (OneToOne Agent)
- `avoid_conception_flag_tick` (PositiveIntegerField, null) — ultimo tick in cui l'agente ha dichiarato intento di evitare concepimento; fertility lo legge quando `current_tick == flag_tick + 1`

### Estensioni ad `Agent`

- `birth_tick` (PositiveIntegerField, indicizzato) — fonte canonica dell'età, `age = (current_tick - birth_tick) / ticks_per_year`
- `death_tick` (PositiveIntegerField, null=True)
- `death_cause` (CharField, choices: `natural_senescence`, `early_life_mortality`, `external_cause`, `childbirth`, `starvation`, `expropriation`, `executed`, `unknown`). Le tre label HP-derivate (`natural_senescence`, `early_life_mortality`, `external_cause`) catturano tutte le morti naturali dal modello HP. Le morti event-driven (childbirth, starvation, expropriation, execution) sono etichettate direttamente dall'evento scatenante.
- `other_parent_agent` (FK self, null, on_delete=SET_NULL, related_name=`other_parent_children`) — il secondo genitore biologico.
- `caretaker_agent` (FK self, null, on_delete=SET_NULL, related_name=`dependents`) — caretaker attivo per figli minori i cui genitori sono non disponibili (entrambi morti, o migrati via). Risolve l'edge case MISS-1 dell'orfano: quando un bambino è orfano, caretaker viene impostato al parente vivente più vicino nella zona; se nessuno, impostato a `None` e il bambino viene flaggato come pupillo dello stato (il governo diventa caretaker implicito). Vedi §5 orphan handling.

**Fonte autoritativa per la genitorialità** (risolve INC-I4): `parent_agent` è la madre biologica per convenzione Epocha (perché ASFR è indicizzato femminile e gli eventi di nascita originano dalla madre). `other_parent_agent` è il padre biologico quando noto (dalla Couple attiva al momento della nascita). `Couple` registra la relazione di matrimonio sociale e NON è fonte di verità per la genitorialità biologica — un bambino può nascere al di fuori di una Couple (se il template ha `require_couple_for_birth: false`) con `other_parent_agent` risolto dal contesto sociale o lasciato null. Iterando genealogie (ereditarietà, tratti), i FK parent su Agent sono autoritativi; Couple è usato per query di marriage market e di relazione.

## Sezione 1: Mortalità — Heligman-Pollard per-era

Il rischio istantaneo di morte all'età `x` è decomposto in tre componenti:

```
q(x) / p(x) = A^((x + B)^C)                      # Componente 1: mortalità infantile
            + D · exp(-E · (ln(x) - ln(F))^2)    # Componente 2: hump di giovane età adulta
            + G · H^x                            # Componente 3: senescenza
```

dove `q(x) = 1 - p(x)` è la probabilità annuale di morte all'età `x`. Gli otto parametri {A, B, C, D, E, F, G, H} sono calibrati per era. Fonte: Heligman & Pollard (1980), formula (5).

### Parameter set per-era

Le tabelle di parametri sono fornite in `template_loader.py`. I valori sotto sono **valori provvisori di seed** in range plausibili per ciascuna era; NON sono ancora fittati dalle fonti nominate. Il task "HP calibration" di Plan 1 esegue il fitting numerico degli 8 parametri HP contro dati di life-table dalle fonti citate tramite minimizzazione ai minimi quadrati non-lineari sui residui di `q(x)`:

```python
HELIGMAN_POLLARD_PARAMS = {
    "pre_industrial": {
        "A": 0.00491, "B": 0.017, "C": 0.102,
        "D": 0.00080, "E": 9.9, "F": 22.4,
        "G": 0.0000383, "H": 1.101,
        "calibration_target": "Wrigley & Schofield (1981) tables A3.1-A3.3, England 1700-1749",
        "calibration_status": "provisional seed values; fit deferred to Plan 1",
        "notes": "Regime demografico pre-industriale, mortalità infantile alta",
    },
    "industrial": {
        "A": 0.00223, "B": 0.022, "C": 0.115,
        "D": 0.00057, "E": 10.8, "F": 25.1,
        "G": 0.0000198, "H": 1.104,
        "calibration_target": "HMD England & Wales life tables, pooled 1841-1900",
        "calibration_status": "provisional seed values; fit deferred to Plan 1",
    },
    "modern": {
        "A": 0.00054, "B": 0.017, "C": 0.125,
        "D": 0.00013, "E": 18.3, "F": 19.6,
        "G": 0.0000123, "H": 1.101,
        "calibration_target": "HMD USA life table 2019 (pre-COVID baseline)",
        "calibration_status": "provisional seed values; fit deferred to Plan 1",
    },
    "sci_fi": {
        "A": 0.00002, "B": 0.017, "C": 0.125,
        "D": 0.00001, "E": 18.3, "F": 19.6,
        "G": 0.0000018, "H": 1.089,
        "calibration_target": "extrapolazione speculativa dal modern, nessuna base empirica",
        "calibration_status": "tunable design parameter set for long-horizon scenarios",
    },
}
```

Procedura di fitting (documentata in Plan 1): carica la colonna q(x) dalla life table dell'era citata; usa `scipy.optimize.curve_fit` sulla forma funzionale HP; memorizza gli 8 parametri fittati; valida i residui. I valori seed attuali sono nell'ordine di grandezza giusto ma NON sono il risultato del fit.

### Applicazione per-tick

Il rischio Heligman-Pollard è annuale. Per un tick di durata `h` ore e con fattore di scala `demography_acceleration`:

```python
def annual_mortality_probability(age: float, params: dict) -> float:
    """Restituisce la probabilità annuale di morte all'età x usando le componenti HP (1980)."""
    A, B, C, D, E, F, G, H = (params[k] for k in "ABCDEFGH")
    x = max(age, 0.01)
    c1 = A ** ((x + B) ** C)
    c2 = D * math.exp(-E * (math.log(x) - math.log(F))**2) if x > 0 else 0.0
    c3 = G * (H ** x)
    q_over_p = c1 + c2 + c3
    q = q_over_p / (1.0 + q_over_p)  # converte hazard a probabilità
    return min(q, 0.999)

def tick_mortality_probability(age: float, params: dict,
                                tick_duration_hours: float,
                                demography_acceleration: float) -> float:
    """Tick-scaling con approssimazione lineare per q < 0.1.
    
    Per q grandi (mortalità infantile pre-industriale), usa conversione geometrica.
    """
    annual_q = annual_mortality_probability(age, params)
    dt = (tick_duration_hours / 8760.0) * demography_acceleration
    if annual_q < 0.1:
        return annual_q * dt
    # Conversione geometrica esatta per q grandi
    return 1.0 - (1.0 - annual_q) ** dt
```

Realizzazione stocastica: `dies_this_tick = rng.random() < tick_q`.

### Attribuzione della causa di morte

Quando la mortalità si attiva, la causa è campionata dalle tre componenti HP all'età `x`. Ogni componente è mappata a una singola label analitica; nessuna soglia d'età all'interno di una componente:

```python
def sample_death_cause(age: float, params: dict, rng: random.Random) -> str:
    """Attribuisce la causa alla componente HP dominante all'età di morte.

    Convention di mapping (analitica, non eziologica):
    - Componente 1 (A^(...)): `early_life_mortality` — infantile + malattie infanzia
    - Componente 2 (accident hump, termine D): `external_cause` — incidenti, omicidio,
      violenza, guerra. Per HP (1980) p.54, cattura mortalità "che si applica
      principalmente ai maschi fra 20 e 40 anni"; non suddividiamo per età entro.
    - Componente 3 (senescenza Gompertz): `natural_senescence`

    Le label sono convention analitiche per reporting dashboard, non classificazione
    medica. Il template può sovrascrivere il mapping con label era-specifiche
    (es. pre_industrial può mappare componente 2 a "war_or_accident").
    """
    A, B, C, D, E, F, G, H = (params[k] for k in "ABCDEFGH")
    x = max(age, 0.01)
    c1 = A ** ((x + B) ** C)
    c2 = D * math.exp(-E * (math.log(x) - math.log(F))**2) if x > 0 else 0.0
    c3 = G * (H ** x)
    total = c1 + c2 + c3
    r = rng.random() * total
    if r < c1:
        return "early_life_mortality"
    if r < c1 + c2:
        return "external_cause"
    return "natural_senescence"
```

Il mapping HP-componente a label `death_cause` è una convention per chiarezza analytics, NON un claim sull'eziologia medica. Le tre label si allineano con la decomposizione HP (1980) senza inventare sub-split età-specifiche.

### Mortalità materna al parto — risoluzione congiunta (fix C-1)

Quando la fertilità (§2) attiva una nascita per un'agente incinta allo stesso tick in cui la mortalità agisce su di lei, i due eventi sono risolti congiuntamente:

1. Prima del draw di mortalità ordinario, controlla se l'agente sta per partorire in questo tick (fertility marker).
2. Se sì, applica la probabilità di mortalità da parto `P_childbirth_death = maternal_mortality_rate_per_birth` dal template. Loudon (1992) riporta tassi di mortalità materna in Inghilterra pre-industriale di ~5-10 per 1000 nascite (0.005-0.010) con variazione regionale (più alti nelle terre germanofone ~0.015-0.020). Valore seed 0.008 per pre_industrial (stima centrale Loudon); 0.0001 per modern (mortalità materna HMD moderna).
3. Se la morte materna si attiva, `death_cause = "childbirth"` e il neonato ha una probabilità ridotta di sopravvivenza `neonatal_survival_when_mother_dies` (parametro template, es. 0.3 pre-industriale).
4. Se la morte materna non si attiva da parto, il draw di mortalità ordinario procede.

Questo cattura la forte correlazione storica tra parto e mortalità femminile senza duplicare eventi di morte o perdere gravidanze silenziosamente.

## Sezione 2: Fertilità — Hadwiger ASFR × Becker × Malthusian ceiling

### ASFR baseline (Hadwiger 1940)

Age-specific fertility rate all'età `a` usando la funzione Hadwiger canonicamente normalizzata:

```
f(a) = (H · T / (R · sqrt(π))) · (R / a)^(3/2) · exp(-T^2 · (R/a + a/R - 2))
```

dove:
- `H` è il total fertility rate (l'integrale di `f` su tutte le età è asintoticamente `H`)
- `R` è un parametro di forma correlato a (ma non esattamente uguale a) l'età modale di fertilità
- `T` è un parametro di forma che controlla lo spread della distribuzione
- Il fattore `1/sqrt(π)` è la normalizzazione che garantisce la consistency di integrazione

L'età modale a cui `f(a)` raggiunge il picco è approssimativamente `R` solo nel limite di `T` piccolo; in generale la moda è leggermente shifted e deve essere computata numericamente.

Fonte: Hadwiger, H. (1940). Eine analytische Reproduktionsfunktion für biologische Gesamtheiten. *Skandinavisk Aktuarietidskrift* 23, 101-113. Convention di normalizzazione segue Chandola, Coleman & Hiorns (1999) "Recent European fertility patterns: fitting curves to 'distorted' distributions", *Population Studies* 53(3), 317-329; e Schmertmann (2003) "A system of model fertility schedules with graphically intuitive parameters", *Demographic Research* 9, 81-110.

Parametri per-era (**valori provvisori di seed** — la calibrazione effettiva sulle fonti storiche citate è rinviata all'implementazione di Plan 1 tramite fit numerico contro le life table originali):

| Era | H (target TFR approx) | R | T | Fonte contro cui calibrare |
|-----|----------------------|----|----|------------------------------|
| pre_industrial | 5.0 | 26 | 0.35 | Wrigley & Schofield (1981) — England TFR range 4.0-5.8 attraverso 1541-1871; valore seed in quel range |
| industrial | 4.0 | 27 | 0.38 | Mitchell (1988), HMD; England 1830-1900 TFR range 3.5-4.5 |
| modern | 1.8 | 30 | 0.42 | HFD (2020) — US, Europa Occidentale sotto replacement |
| sci_fi | 2.1 | 32 | 0.40 | speculativo (parametro di design tunable) |

I valori sono attualmente parametri di seed. La calibrazione TFR reale richiede fitting di `f(a)` a curve ASFR pubblicate e targeting del TFR empirico dell'era. Questo fitting è un task in Plan 1.

### Modulazione Becker

Seguendo lo spirito di Becker (1991) e le regressioni empiriche in Jones & Tertilt (2008), la domanda di fertilità risponde alle condizioni economiche tramite un fattore moltiplicativo. Poiché Spec 2 non espone salari gendered né uno scalare aggregato di outlook economico, usiamo i segnali adattati definiti in Integration Contracts:

```python
def becker_modulation(agent: Agent, coeffs: dict) -> float:
    """Scala l'ASFR baseline con segnali economici derivati dallo stato esistente.
    
    Design ispirato a Becker (1991) e Jones & Tertilt (2008).
    Tutti i coefficienti sono valori provvisori di seed; la calibrazione
    effettiva è rinviata a Plan 1 usando test di shock sintetici che
    mirano alle elasticità US 1826-1960 di Jones-Tertilt come benchmark.
    """
    subsistence = compute_subsistence_threshold(agent.simulation, agent.zone)
    wealth_signal = math.log(max(agent.wealth / max(subsistence, 1e-6), 0.1))
    # Proxy di female labor participation (sostituisce il costo opportunità)
    zone_flp = female_role_employment_fraction(agent.zone, agent.simulation)
    zone_wage = zone_mean_wage(agent.zone, agent.simulation)
    outlook = compute_aggregate_outlook(agent)
    
    raw = (coeffs["beta_0"] 
           + coeffs["beta_1"] * wealth_signal 
           + coeffs["beta_2"] * agent.education_level 
           + coeffs["beta_3"] * zone_flp
           + coeffs["beta_4"] * outlook)
    return max(0.05, min(3.0, math.exp(raw)))
```

Dove `female_role_employment_fraction` e `zone_mean_wage` sono helper query sui record `EconomicLedger` esistenti, definiti in `demography/fertility.py`.

Coefficienti per-era (**valori provvisori di seed** — i segni seguono le predizioni qualitative di Becker 1991 e Jones & Tertilt 2008; le magnitudo da calibrare contro Jones & Tertilt tabelle 3-4 durante la validation di Plan 1):

| Era | β₀ | β₁ (wealth) | β₂ (education) | β₃ (female_flp) | β₄ (outlook) |
|-----|-----|------------|----------------|-----------------|--------------|
| pre_industrial | 0 | +0.1 | -0.05 | -0.1 | +0.2 |
| industrial | 0 | +0.2 | -0.3 | -0.4 | +0.3 |
| modern | 0 | +0.15 | -0.6 | -0.5 | +0.4 |

Tutte le magnitudo dei coefficienti sono parametri di design tunable. Il validation test 2 in §12 misura la risposta agli shock economici e aggiusta i coefficienti per matchare i pattern qualitativi di Jones & Tertilt.

### Soft-cap heuristic malthusiana (fix I-4)

Soft cap operativo che previene esplosione della popolazione. È una funzione piecewise ingegnerizzata **ispirata dal** preventive check malthusiano (Malthus 1798) e dai modelli di carrying-capacity formalizzati in Ashraf & Galor (2011), ma NON è essa stessa la formalizzazione che loro propongono. Il loro paper AER 2011 usa dinamiche differenziali in continuous-time sul reddito pro-capite; questa euristica è uno scaling multiplicativo tick-based sulla fertilità:

```python
def malthusian_soft_ceiling(prob: float, current_pop: int, max_pop: int,
                             floor_ratio: float = 0.1) -> float:
    """Soft-cap euristico sulla fertilità. Non è una derivazione di una formula pubblicata.

    Obiettivi di design:
    - Fertilità libera sotto l'80% del cap (nessuna distorsione)
    - Rampa discendente lineare tra 80% e 100% del cap (preventive check)
    - Floor a floor_ratio * baseline sopra il cap (popolazioni non smettono mai
      di riprodursi completamente, per l'osservazione di Lee 1987 su popolazioni intrappolate)

    Riferimenti (ispirazionali, non formulazioni):
    - Malthus (1798) — concetto di preventive check
    - Ricardo (1817) — carrying capacity
    - Ashraf & Galor (2011) — formalizzazione moderna delle dinamiche malthusiane
    - Lee (1987) — floor empirico sulla fertilità sotto stress
    """
    if current_pop < 0.8 * max_pop:
        return prob
    if current_pop < max_pop:
        saturation = (current_pop - 0.8 * max_pop) / (0.2 * max_pop)
        ceiling_factor = max(0.0, 1.0 - saturation)
        return prob * ceiling_factor
    return prob * floor_ratio
```

La soglia di attivazione 0.8 e il floor 0.1 sono parametri di design tunable. Formulazioni alternative (es. declino logistico) sono sostituzioni accettabili se i test di validation mostrano miglior fit con dinamiche malthusiane osservate.

### LLM gating — avoid_conception (fix C-2)

Template `fertility_agency`:
- `biological` (default pre_industrial): no gating, le nascite si attivano stocasticamente da ASFR × Becker × Malthusian.
- `planned` (default modern): gate tramite `AgentFertilityState.avoid_conception_flag_tick`. Un agente (femmina o maschio in coppia attiva) invoca `avoid_conception` al tick T; il flag viene impostato. Al tick T+1, fertility controlla `flag_tick == current_tick - 1`; se sì, il birth draw viene saltato indipendentemente dall'outcome stocastico. Il settlement di 1 tick corrisponde al pattern property market di Spec 2.

Questo cattura la fertility transition (Coale & Watkins 1986) come proprietà emergente configurabile dal template invece di comportamento hardcoded.

### Formula combinata di fertilità

```python
def tick_birth_probability(mother: Agent, params_era: dict,
                            coeffs_era: dict, current_pop: int, max_pop: int,
                            tick_duration_hours: float,
                            demography_acceleration: float) -> float:
    if params_era.get("require_couple_for_birth", True) and not is_in_active_couple(mother):
        return 0.0
    if avoid_conception_active_this_tick(mother):
        return 0.0
    
    annual_asfr = hadwiger_asfr(mother.age, params_era)
    becker_factor = becker_modulation(mother, coeffs_era)
    effective = annual_asfr * becker_factor
    effective = malthusian_soft_ceiling(effective, current_pop, max_pop,
                                         params_era.get("malthusian_floor_ratio", 0.1))
    
    # Approssimazione lineare della discretizzazione Poisson continuous-time.
    # Per annual rate q < 0.1 (tipico per fertilità), errore del linear scaling
    # vs. conversione geometrica esatta è <0.5%. Per q grandi (mortalità
    # infantile q~0.25), usa invece geometric_tick_probability.
    return effective * (tick_duration_hours / 8760.0) * demography_acceleration
```

## Sezione 3: Formazione di coppia — Gale-Shapley + azioni LLM

### Context enrichment

Quando un agente single di età idonea non ha una coppia attiva, il decision context riceve un blocco `match_pool`:

```
Match potenziali (ordinati per compatibility score, tua zona):
- Marie Dupont, età 24, tessitrice, classe middle (compat 0.82)
- Antoinette Giraud, età 22, domestica, classe working (compat 0.67)
- Louise Moreau, età 28, figlia del mercante, classe middle (compat 0.61)
```

Il compatibility score usa pesi di omogamia Kalmijn (1998):

```
compat(i, j) = w_class · same_class_binary 
             + w_edu · exp(-|edu_i - edu_j|)
             + w_age · exp(-|age_i - age_j| / age_tolerance)
             + w_relationship · existing_sentiment(i, j)
```

Pesi di default (euristica di design, tutti tunable): `w_class = 0.4, w_edu = 0.25, w_age = 0.20, w_relationship = 0.15`. Kalmijn (1998) identifica classe ed istruzione come i due driver più forti di omogamia nelle società occidentali; i pesi numerici specifici sono euristica di design che matcha quel ranking qualitativo, NON una derivazione diretta dal paper. La validation di Plan 1 aggiusterà i pesi affinché la correlazione di classe intra-coppia osservata matchi benchmark empirici.

### Marriage market radius (fix I-2)

Il template dichiara `marriage_market_radius ∈ {same_zone, adjacent_zones, world}`.

- `same_zone` (default pre_industrial) — >90% matrimoni intra-parrocchia in Wrigley-Schofield England
- `adjacent_zones` (default industrial) — cerchia più ampia con trasporti migliorati
- `world` (default modern, sci_fi) — nessun vincolo geografico (era online dating)

### Azione LLM: pair_bond

- Target: nome di un candidato dal match_pool
- Handler:
  1. Valida che il candidato sia nel match_pool e ancora disponibile (non sposato, non morto)
  2. Registra l'intento pair_bond in DecisionLog
  3. Nel demography step del tick successivo, controlla se il target ha ricambiato (anch'esso ha scelto pair_bond verso questo agente) OPPURE se applica il consenso implicito (template con `implicit_mutual_consent: true` — pre_industrial default yes, modern default no richiede reciprocità esplicita entro N tick)
  4. Se reciproco, crea `Couple(agent_a=proposer, agent_b=target, formed_at_tick=current_tick + 1, couple_type=template_default)`

### Matrimonio combinato (Goode 1963)

Se `marriage_market_type == "arranged"`, il decision-maker è il genitore, non il figlio. Il decision context dell'agente genitore include il match_pool dei suoi figli adulti non sposati. Il genitore invoca la standard azione `pair_bond` con un payload target esteso: `{"for_child": "<nome_figlio>", "match": "<nome_altro>"}`. Il figlio ha una finestra di 1 tick in cui ricambiare invocando `pair_bond target=<nome_match>` (accetta) o NON invocandolo (rifiuta). Un rifiuto genera memoria negativa per figlio e genitore con `emotional_weight = 0.5` (conflitto sociale). **Nessun nuovo nome di azione viene aggiunto** — il riuso di `pair_bond` con payload esteso evita l'espansione della lista azioni (fix MISS-10). Lo scenario template `pre_industrial_feudal` abilita questo; `modern` lo disabilita impostando `marriage_market_type: "autonomous"`.

### Azione LLM: separate

- Disponibile solo quando `divorce_enabled: true` nel template (fix N-4: azioni filtrate al prompt level per azioni indisponibili nell'era).
- Handler: marca Couple.dissolved_at_tick = current_tick + 1, dissolution_reason="separate". Entrambi i partner ricevono memoria mood negativa.

### Dissoluzione automatica alla morte

Quando un partner muore (rilevato nello step §1 mortality), qualsiasi Couple attiva cui appartiene è automaticamente marcata dissolta con reason="death". Il nome del partner deceduto viene catturato nel corrispondente campo `agent_a_name_snapshot` o `agent_b_name_snapshot` PRIMA che il FK venga nullato, preservando il record storico indipendentemente da quale partner è morto. Il partner sopravvissuto riceve una memoria di bereavement con `emotional_weight = 0.9` (Parkes 1972). Dopo `mourning_ticks` (parametro template; default 365 tick-equivalent per pre_industrial, 180 per modern), il partner sopravvissuto rientra nel marriage market.

### Stable matching in inizializzazione

Nell'initializer demografico (§10), la formazione retrospettiva di coppie usa stable matching Gale-Shapley su tutti gli agenti adulti eleggibili globalmente. L'algoritmo:

1. Ordina i proposers per età decrescente (anziani propongono per primi, matcha pattern di timing del matrimonio pre-industriale)
2. Ogni proposer ha una lista di preferenze ordinata per compatibility score
3. I respondents tengono l'engagement con il loro proposer più alto in ranking visto finora, jiltano proposers più bassi
4. Convergence: ogni proposer fa al massimo `n` proposte, portando a O(n²) proposte totali complessive. Gale & Shapley (1962) hanno dimostrato sia l'esistenza che la stability del matching risultante.

## Sezione 4: Ereditarietà dei tratti biologici — polygenic additive

### Formula (Falconer & Mackay 1996)

Per ogni tratto ereditabile T con heritability h²:

```
child_T = h²_T · (mother_T + father_T) / 2 + (1 - h²_T) · ε_T
ε_T ~ N(era_mean_T, era_sd_T)
```

Il rumore ambientale `ε` è campionato da una distribuzione Normale la cui media e SD sono stimate dalla popolazione iniziale (tick 0) della simulazione (congelate dopo il tick 0). Questo modella l'ambiente come deviazione dal background genetico a livello di popolazione, un approccio metodologicamente standard (Falconer 1996 cap. 8).

### Tabella di heritability

Ereditate tramite il meccanismo polygenic additive. I valori di heritability provengono dagli studi primari trait-specifici citati sotto. La meta-analisi Polderman et al. (2015) è citata come backbone metodologico (integra 50 anni di twin studies con h² medio ≈ 0.49 su 17.804 tratti) ma NON come fonte dei valori individuali di h²:

| Tratto Agent | h² | Fonte |
|--------------|-----|--------|
| openness (Big Five) | 0.41 | Jang, Livesley & Vernon (1996) |
| conscientiousness | 0.44 | Jang, Livesley & Vernon (1996) |
| extraversion | 0.54 | Jang, Livesley & Vernon (1996) |
| agreeableness | 0.42 | Jang, Livesley & Vernon (1996) |
| neuroticism | 0.48 | Jang, Livesley & Vernon (1996) |
| intelligence | 0.55 | Plomin & Deary (2015) review |
| emotional_intelligence | 0.40 | Vernon et al. (2008) |
| creativity | 0.22 | Nichols (1978) |
| strength | 0.55 | Zempo et al. (2017) |
| stamina | 0.52 | Miyamoto-Mikami et al. (2018) |
| agility | 0.45 | Thomis et al. (1998) |
| fertility (fecondità biologica) | 0.50 | Zietsch et al. (2014) |
| mental_health baseline | 0.40 | euristica di design seeded da aggregato Polderman 0.49, aggiustato in basso |

Il tratto `cunning` (da `Agent.cunning`) NON è ereditato tramite il meccanismo biologico perché non è un costrutto psicometrico standard con heritability pubblicata. È invece computato at-birth come valore derivato da altri tratti ereditati seguendo una proxy Machiavellism standard (agreeableness bassa + neuroticism alto + intelligence sopra-media), specificamente: `cunning = 0.4·(1-agreeableness) + 0.3·neuroticism + 0.3·intelligence`, clampato a [0,1]. Questa è una proxy euristica di design piuttosto che un tratto ereditato di per sé.

**Responsibility contract**: `inheritance.py` legge la sezione `trait_inheritance.derived_trait_formulas` dal template demografico della simulazione *dopo* aver applicato il polygenic additive inheritance a tutti i tratti ereditabili. Per ciascuna entry in `derived_trait_formulas` (attualmente solo `cunning`), valuta la formula contro i tratti ereditabili appena computati del neonato e imposta il corrispondente campo `Agent`. La stringa della formula è parsata tramite un piccolo expression evaluator ristretto a aritmetica e riferimenti a tratti (no arbitrary code execution); l'insieme di tratti referenziabili corrisponde alle keys del dict `heritability`. Questo contract rende il computo dei derived trait una responsabilità di prima classe di `inheritance.py`, non un'attività side implicita.

I tratti memorizzati dentro `Agent.personality` JSONB che non hanno un h² pubblicato (es. `humor_style`, `attachment_style`) sono ereditati tramite default h² = 0.30, marcato come parametro di design tunable.

Il genere è risolto alla nascita tramite draw dall'era `sex_ratio_at_birth` (default 1.05 M/F biologicamente universale). L'orientamento sessuale è tratto dalla distribuzione d'era; il default per scenari moderni approssima Chandra et al. (2011) *National Health Statistics Reports* 36 (U.S. National Survey of Family Growth 2006-2008): heterosexual 0.955, bisexual 0.030, homosexual 0.015. Questi valori sono self-report US moderno e sono marcati come parametri di design tunable per ere non-moderne dove dati comparabili non sono disponibili.

### Applicazione alla nascita

```python
def inherit_trait(mother_val: float, father_val: float, h2: float,
                   era_mean: float, era_sd: float, rng: random.Random) -> float:
    midparent = (mother_val + father_val) / 2
    noise = rng.gauss(era_mean, era_sd)
    return h2 * midparent + (1 - h2) * noise
```

Applicato per tratto, risultato clampato al range del tratto (es. `[0, 1]` per scalari di personalità).

### Edge case: singolo genitore noto (fix I-1)

Neonato da una coppia dove solo un genitore è risolto (raro: scenario adozione deferred; più comune: fase di inizializzazione dove alcuni agenti hanno genealogia sintetica senza entrambi i genitori). Fallback a `child_T = h² · parent_T + (1-h²) · ε` (metà del signal genetico). Documentato come semplificazione — matcha il flusso genetico single-parent reale.

## Sezione 5: Ereditarietà sociale ed economica

### Classe sociale per-era

| Template | Regola |
|----------|--------|
| pre_industrial | `child.social_class = father.social_class` (patrilineale rigido; Goody 1976; Wrigley 1981) |
| industrial | 70% ereditato dal padre; 30% regressione verso la media di classe della zona (Clark 2014, *The Son Also Rises*) |
| modern | Elasticità intergenerazionale del reddito 0.4: campiona la classe del figlio da distribuzione shiftata verso la classe del genitore. Il valore 0.4 è il valore approssimato US moderno da Solon (1999) *Intergenerational Mobility in the Labor Market*, Handbook of Labor Economics 3A, e Chetty et al. (2014) che danno range 0.3-0.5. Becker & Tomes (1979) è il framework teorico fondativo ma non pubblicò questo specifico valore di elasticità. |
| sci_fi | 20% ereditato, 80% riassegnazione meritocratica basata su intelligence + education (scelta di design speculativa) |

### Regressione intergenerazionale del livello educativo

```
child.education = ρ · (mother.edu + father.edu) / 2 + (1 - ρ) · era_mean_edu
```

`ρ` per-era:
- pre_industrial: 0.5 (persistenza forte, mobilità limitata)
- industrial: 0.42
- modern: 0.35 (Chetty et al. 2014)
- sci_fi: 0.25

### Ricchezza di partenza e zona

- `wealth` di partenza = 0. Il figlio eredita solo alla morte del genitore.
- `zone = mother.zone` al tick di nascita (denormalizzato per performance, consistente con il modello esistente).

### Ereditarietà economica alla morte — regola per-era + estate tax

Priorità degli eredi (default, configurabile nel template):

1. Coniuge sopravvissuto (tramite Couple attiva)
2. Figli (tramite parent_agent + other_parent_agent)
3. Fratelli (parent_agent condiviso)
4. Famiglia estesa (lineage di nonno, fino a 2 generazioni)
5. Government treasury (nessun erede → proprietà + cash al governo)

Regole di ereditarietà:

| Regola | Distribuzione | Gestione non-binary |
|--------|---------------|---------------------|
| `primogeniture` | 100% di proprietà e cash al figlio maschio maggiore sopravvissuto; se nessuno, alla femmina maggiore; se nessuno, cascade al coniuge poi fratelli (Blackstone 1765). | Gli eredi non-binary sono processati insieme agli eredi femmine nell'ordering (contesto storico: la legge ereditaria pre-moderna non aveva categoria per identità non-binary; trattare non-binary come femmina è una semplificazione pragmatica documentata qui). |
| `equal_split` | Cash e proprietà divisi equamente tra figli sopravvissuti; il coniuge riceve quota uguale a quella di un figlio (Napoleonic Code 1804). | Eredi non-binary ricevono quota equa (nessuna distinzione di genere). |
| `shari'a` | Coniuge 1/8 se figli esistono altrimenti 1/4; figli maschi 2× quota figlia; il resto cascade per regole coraniche (Powers 1986). | Eredi non-binary ricevono quota figlia (1× unit). Semplificazione; la giurisprudenza islamica classica non riconosceva status non-binary. |
| `matrilineal` | Beni passano ai figli della sorella del defunto (schematico, Schneider & Gough 1961). | Non-binary trattato per parentela biologica (linea materna); nessuna distinzione di ruolo di genere necessaria. |
| `nationalized` | 100% al government treasury (Nove 1969, espropriazione sovietica). | Nessun erede, quindi genere irrilevante. |

### Estate tax

Usa l'helper `add_to_treasury` definito in §Integration Contracts (estratto come parte dello scope di questa spec dal pattern esistente di JSON-dict mutation in economy/engine.py:433):

```python
def apply_estate_tax(total_estate_value: float, rate: float,
                     government, primary_currency_code: str) -> float:
    """Restituisce l'amount ereditabile dopo tax. Routa la tax al treasury."""
    from epocha.apps.world.government import add_to_treasury
    tax_revenue = total_estate_value * rate
    add_to_treasury(government, primary_currency_code, tax_revenue)
    return total_estate_value * (1.0 - rate)
```

Tassi di estate tax di default per era:
- pre_industrial: 0.0 (dovizi feudali modellati separatamente in economia, non come estate tax)
- industrial: 0.15
- modern_democracy: 0.40 (Piketty 2014 tabelle 14.1-14.2)
- sci_fi: template-dependent

### Ordering di morti simultanee (fix C-3)

Quando più agenti muoiono nello stesso tick, l'ereditarietà processa in batch ordinato per età decrescente. Questo è un tiebreak deterministico per riproducibilità; matcha la convention del Simultaneous Death Act nella common law anglo-americana. L'estate tax è applicata una volta per trasferimento (non cumulativamente) anche se gli asset si concatenano attraverso multipli agenti morenti in un singolo tick.

### Ereditarietà multi-generazionale attraverso tick (fix MISS-5)

Quando un erede è morto per molteplici tick, il loro estate era già stato settled ai loro stessi eredi al loro tick di morte. Il nonno deceduto non può lasciare in eredità a un padre deceduto; l'estate passa attraverso la catena seguendo la lista di eredi di ciascun deceduto al loro tempo di morte. L'estate tax si applica a ciascun evento di trasferimento effettivo e NON viene ri-applicata quando gli asset successivamente si muovono attraverso ulteriori eventi di ereditarietà in tick successivi.

### Gestione orfani (fix MISS-1)

Quando entrambi i genitori biologici di un minorenne (`age < adulthood_age`) sono morti, il minore viene assegnato un `caretaker_agent` secondo la priorità seguente: parente vivente più vicino nella stessa zona (fratello, nonno, zio/zia), poi qualsiasi parente vivente ovunque, poi None (pupillo dello stato). Un orfano con `caretaker_agent = None` viene flaggato e `Government.government_treasury` copre la sua sussistenza (modellando il wardship statale). L'orfano riceve comunque la sua eredità direttamente; il caretaker amministra ma non possiede gli asset.

### Couple con entrambi i partner morti nello stesso tick (fix MISS-4)

Quando sia `agent_a` che `agent_b` muoiono nello stesso tick, il record Couple è marcato `dissolved_at_tick = tick, dissolution_reason = "death"`. Entrambi i FK diventano null, ma couple_type e formed_at_tick rimangono per audit di genealogia. Per preservare il linkage di audit, due campi aggiuntivi sono aggiunti a Couple: `agent_a_name_snapshot` (CharField, popolato alla dissolution) e `agent_b_name_snapshot` (CharField) che catturano i nomi dei partner deceduti per query storiche anche dopo il nulling dei FK.

### Loans ereditati (come lender)

I loans attivi dove il deceduto era lender vengono trasferiti agli eredi usando la stessa regola di distribuzione. Se la regola non produce eredi umani (es. nationalized o nessuna famiglia), il loan trasferisce al banking system (`lender=None, lender_type="banking"`) e continua a essere servito. Loans agent-to-agent senza eredi vengono silenziosamente cancellati a MVP — limitazione documentata.

### Cascata di memoria del lutto

La morte genera memorie con `emotional_weight = 0.9` per:
- Coniuge sopravvissuto (se esiste)
- Figli sopravvissuti
- Relazioni strette (`Relationship.strength > 0.6` esistenti)

Queste memorie si propagano tramite il sistema information_flow esistente (Spec 1 app agents), raggiungendo la società più ampia come memorie tipo-rumor con peso decadato.

## Sezione 6: Migrazione — LLM-driven + context Harris-Todaro + coordinamento familiare + emergency flight

### Context enrichment per le decisioni

Quando un agente ha `move_to` disponibile, il prompt riceve un blocco `migration_outlook`:

```
Migration outlook (la tua zona: Capital):
- Wage differential (media 5-tick):
  - Paris: +12 LVR/tick (destinazione)
  - Lyon: +3 LVR/tick
  - Countryside: -5 LVR/tick
- Unemployment: Paris 8%, qui 15%, Lyon 12%
- Costo distanza in tick: Paris 0, Lyon 3, Countryside 5
- Zone stability: Paris crisi (0.3), qui stabile (0.7), Countryside stabile (0.6)
- Expected gain Harris-Todaro se ti muovi a Paris: +4.8 LVR/tick

Il tuo household (se ti muovi, questi ti seguono automaticamente):
- Coniuge: Marie
- Figli minori: Pierre (4), Anne (1)
```

Computazioni:

- **Wage differential**: media delle transazioni `EconomicLedger.transaction_type="wage"` per zona negli ultimi 5 tick, normalizzata per-capita.
- **Unemployment**: frazione di agenti nella zona con `role` impostato ma wage zero negli ultimi 3 tick.
- **Costo distanza**: `ceil(distance_km / (walking_speed_km_per_day · tick_duration_days))`, usando `World.distance_scale` esistente e walking_speed_km_per_day = 25 (verificato audit 2026-04-12).
- **Zone stability**: campo Government.stability esistente.
- **Expected gain Harris-Todaro** — variante operativa di Harris & Todaro (1970). La forma canonica confronta reddito urbano atteso `p · w_urban + (1-p) · w_informal` contro reddito rurale. Usiamo una variante operativa semplificata: `E[gain_j] = (1 - unemployment_j) · wage_j - wage_current - distance_cost_j`, settando salario informale-sector a 0 e aggiungendo costo di distanza esplicito. Questa semplificazione è documentata e tunable (salario informale può essere aggiunto in futuro come parametro di zona).

### Coordinamento familiare (Mincer 1978)

Quando un agente in Couple attiva con figli minorenni decide `move_to target=<zone>`:

1. Partner e tutti i figli con `age < adulthood_age` (template-specific; 16 pre_industrial, 18 modern) migrano con lui nello stesso tick.
2. Singolo `DemographyEvent(event_type="migration", primary_agent=deciding_agent, payload={"household_members": [partner_id, child_ids], "from_zone": X, "to_zone": Y, "reason": "voluntary"})`.
3. I figli minori non vengono chiamati al decision loop per questa migrazione al tick.
4. I figli adulti decidono indipendentemente.

### Emergency flight (O'Rourke 1994, Simon 1955 bounded rationality)

Condizioni trigger (tutte e tre simultaneamente):

- `agent.wealth < compute_subsistence_threshold(agent.simulation, agent.zone)` (helper definito in §Integration Contracts)
- `consecutive_ticks_under_subsistence >= flight_trigger_ticks` (tunable, default 30)
- `max(expected_harris_todaro_gain su altre zone) > 0` (almeno una zona offre miglioramento; fix I-5)

Se triggered:

1. Migrazione automatica alla zona con expected gain più alto; bypassa LLM (istinto di sopravvivenza, Simon 1955 bounded rationality sotto soglia di sopravvivenza).
2. Coordinamento familiare si applica.
3. Memoria: `emotional_weight = 0.85`, contenuto "Ho dovuto lasciare <zone> per fame. Non c'era scelta."
4. `DemographyEvent(event_type="migration", payload={"reason": "emergency_flight", ...})`.

Se nessuna zona offre gain positivo ma le condizioni trigger sono altrimenti soddisfatte, l'agente rimane intrappolato e può morire di fame. Un `DemographyEvent(event_type="trapped_crisis", primary_agent=agent)` viene generato. **Politica di propagazione (fix MISS-3)**: l'evento trapped_crisis viene scritto sia nel ledger di analytics CHE propagato come memoria agent-visible con `emotional_weight = 0.95, source_type = "public"` a tutti gli agenti co-zone. Questo cattura la realtà osservabile della starvation di massa che si blocca su una popolazione. Altri agenti testimoni di trapped_crisis formano memorie di grief/paura che alimentano decisioni successive (fazioni, migrazione, protesta).

### Broadcast di mass flight

Se >30% della popolazione vivente di una zona fugge entro `flight_trigger_ticks`, un `DemographyEvent(event_type="mass_flight", payload={"from_zone": X, "agents": [...]})` viene generato. Questo si integra con i sistemi esistenti di information_flow e political cycle come evento di crisi (analogo a `broadcast_banking_concern` di Spec 2).

## Sezione 7: Invecchiamento (implicito tramite birth_tick)

L'età è computata dinamicamente come `(current_tick - birth_tick) / ticks_per_year` piuttosto che memorizzata e aggiornata. Questo evita scrittura O(N) per tick ed elimina race condition tra demografia e altri sistemi che leggono `age`.

`ticks_per_year = 8760.0 / tick_duration_hours` con `demography_acceleration` come moltiplicatore: `effective_age_in_years = (current_tick - birth_tick) · tick_duration_hours / 8760.0 · demography_acceleration`.

Il campo `Agent.age` esistente viene mantenuto come cache denormalizzata per il codice legacy; rinfrescato da signal su tick-advance.

## Sezione 8: Azioni LLM e decision context

### Nuove azioni

Tre nuove azioni aggiunte a `_DECISION_SYSTEM_PROMPT`:

- `pair_bond` — formare una coppia con un candidato
- `separate` — dissolvere una coppia (disponibile solo quando il template abilita divorzio)
- `avoid_conception` — bloccare il concepimento questo tick (disponibile solo quando il template supporta family planning)

Il system prompt diventa:

```
"action": "work|rest|socialize|explore|trade|argue|help|avoid|form_group|
          join_group|crime|protest|campaign|move_to|hoard|borrow|
          sell_property|buy_property|pair_bond|separate|avoid_conception"
```

**Filtro dinamico (fix N-4)**: le azioni non disponibili nel template corrente sono filtrate dal system prompt al momento della build. `separate` è assente per pre_industrial_christian; `avoid_conception` è assente per pre_industrial. Questo riduce il costo token del prompt e previene che l'LLM tenti azioni non disponibili.

### Mood delta e emotional weight

| Azione | Mood delta | Emotional weight | Razionale |
|--------|-----------|-----------------|-----------|
| pair_bond | +0.10 | 0.7 | Grande evento positivo di vita (Holmes & Rahe 1967 marriage score 50) |
| separate | -0.15 | 0.8 | Grande evento negativo di vita (Holmes & Rahe 1967 divorce score 73) |
| avoid_conception | -0.01 | 0.2 | Atto pianificatorio minore, valenza emotiva neutrale |

Tutti sono parametri di design tunable consistenti con la calibrazione esistente in simulation/engine.py.

### Verbi dashboard

```python
_ACTION_VERBS.update({
    "pair_bond": "formed a couple with",
    "separate": "separated from",
    "avoid_conception": "chose to delay having children",
})
```

### Eventi demografici automatici nell'activity feed

Eventi non-LLM generano entry nel feed:

- Nascita: "<mother name> gave birth to <child name>"
- Morte: "<agent name> died (<cause>)"
- Emergency flight: "<agent name> fled <from_zone> for <to_zone> due to starvation"
- Mass flight: "<N> agents fled <from_zone>"
- Trapped crisis: "<agent name> is trapped in <zone> with no viable escape"

### Blocco demographic context nel decision prompt

Da `demography/context.py`:

```
La tua situazione di vita:
- Età: 34 (peak adult)
- Life stage: anni di costruzione familiare
- Life expectancy outlook: ~25 anni residui basati sull'era corrente
- Relazione: sposato con Marie (3 anni), 2 figli (Pierre età 4, Anne età 1)
- Eventi familiari recenti: la madre di Marie è morta 2 tick fa (ancora in lutto)

Match potenziali (se single): [omesso quando in coppia]

Considerazione di migrazione familiare: [mostrato quando move_to viable]
- Il tuo household: 2 adulti, 2 figli (tutti si muoverebbero con te)
- I tuoi genitori in zona Countryside: NON si muoverebbero (figli adulti)
```

Le etichette di life stage (convention UN WPP age-group):
- 0-12: child
- 13-17: adolescent
- 18-25: young adult
- 26-45: peak adult
- 46-65: mature
- 66+: elder

Query: tutte indicizzate, no N+1. Overhead totale <5ms per agente per tick.

## Sezione 9: Integrazione della pipeline — process_demography_tick

```python
def process_demography_tick(simulation, tick: int) -> None:
    """Esegue un tick demografico completo: aging, mortality, fertility,
    couple market, migration, inheritance, snapshot.
    
    Chiamato dopo economy, prima delle decisioni dell'agente.
    """
    # Guard: early-return per popolazione zero (MISS-2)
    if not Agent.objects.filter(simulation=simulation, is_alive=True).exists():
        logger.info("Simulation %d has no living agents; demography tick skipped", simulation.id)
        return
    
    # Guard: economy non inizializzata -> Becker fallback neutrale, emergency flight disabilitato (MISS-6)
    economy_initialized = Currency.objects.filter(simulation=simulation).exists()
    
    rng = get_seeded_rng(simulation, tick, phase="mortality")
    template = load_demography_template(simulation)
    
    # STEP 1: AGING è implicito tramite birth_tick, no state change necessario
    # (cache denormalizzata Agent.age rinfrescata qui se necessario)
    
    # STEP 2+2.5+3: RISOLUZIONE CONGIUNTA MORTALITY-FERTILITY (fix C-1)
    pending_births = identify_pending_births(simulation, tick, rng, template)
    for agent in living_agents(simulation):
        # Controlla prima morte materna childbirth-linked
        if agent in {b.mother for b in pending_births}:
            resolve_childbirth_event(agent, pending_births, tick, rng, template)
        else:
            # Draw di mortalità ordinario
            if mortality_fires(agent, tick, rng, template):
                process_death(agent, tick, rng, template)

    # STEP 3.5: ASSEGNAZIONE CARETAKER ORFANI (fix MISS-1)
    # Dopo tutte le morti in STEP 2-3, assegna caretaker_agent per agenti
    # minorenni i cui entrambi i genitori biologici sono ora morti.
    assign_caretakers_for_orphans(simulation, tick)

    # STEP 4: COUPLE MARKET (risolvi intenti pair_bond/separate del tick precedente)
    process_pair_bond_intents(simulation, tick, rng, template)
    process_separate_intents(simulation, tick, template)
    refresh_match_pools_for_context(simulation)
    
    # STEP 5: MIGRAZIONE (emergency flight auto; voluntary tramite context enrichment solo)
    process_emergency_flights(simulation, tick, template)
    
    # STEP 6: POPULATION SNAPSHOT
    capture_population_snapshot(simulation, tick)
```

Razionale del timing:

- Mortality e fertility prima di ogni decision step così nascite/morti nuove sono visibili nel decision context di questo tick per altri agenti (es. coniuge in lutto).
- Couple market processa intenti dal DecisionLog del tick *precedente* (settlement a tick+1, consistente con property market e hoard in Spec 2).
- Emergency flight bypassa LLM (Simon 1955 bounded rationality sotto soglia di sopravvivenza).
- La migrazione volontaria non si innesca qui; accade tramite la normale azione LLM `move_to` nella phase decision.
- Snapshot è l'ultimo step, cattura lo stato finale.

### Hook in `simulation/engine.py`

Aggiunta di due linee:

```python
from epocha.apps.demography.engine import process_demography_tick

# ... dentro run_tick, dopo process_economy_tick_new(...) ...
process_demography_tick(self.simulation, tick)
```

## Sezione 10: Inizializzazione demografica

`demography/initialization.py:initialize_demography(simulation, template_name)` gira dopo `generate_world_from_prompt` e prima del primo tick.

Quattro fasi:

### Fase 1: Redistribuzione piramide d'età

Il template dichiara la piramide d'età come PDF su bucket di 5 anni. Per pre_industrial:

```python
AGE_PYRAMID_PRE_INDUSTRIAL = [
    (0, 5, 0.15), (5, 10, 0.12), (10, 15, 0.11),
    (15, 20, 0.10), (20, 25, 0.09), (25, 30, 0.08),
    (30, 35, 0.07), (35, 40, 0.06), (40, 45, 0.05),
    (45, 50, 0.05), (50, 55, 0.04), (55, 60, 0.03),
    (60, 65, 0.02), (65, 70, 0.015), (70, 75, 0.01),
    (75, 80, 0.005),
]
```

Fonte: Wrigley & Schofield (1981) tables A3.1-A3.3, England 1700.

L'età di ogni agente esistente viene ricampionata da questa distribuzione; `birth_tick = -int(age * ticks_per_year)` è computato. Distribuzione del sesso da `sex_ratio_at_birth` d'era aggiustato per sopravvivenza età-specifica.

### Fase 2: Formazione di coppie via Gale-Shapley

Stable matching applicato a tutti gli agenti adulti (età >= `min_marriage_age`) attraverso le zone entro `marriage_market_radius`. I compatibility score usano i pesi Kalmijn (1998) come in §3. Ogni coppia matched ottiene `Couple(formed_at_tick=-rng.randint(...), couple_type=template_default)` con timing retrospettivo.

### Fase 3: Genealogie sintetiche

Per ogni coppia formata con entrambi i partner adulti:

1. Computa la fertility attesa sui years-of-couple passati usando era ASFR × Becker.
2. Con probabilità matching la fertility attesa, aggiungi parent_agent link a agenti adulti esistenti la cui età è compatibile (age_child < age_parent - min_reproductive_age), fino a `initial_population_target`.
3. Genera nuovi agenti figli minorenni dove esistono agenti parent-aged ma nessun figlio esistente matcha, rispettando la piramide d'età.

**Gestione side-effect (fix MISS-7)**: la Fase 3 modifica agenti originariamente creati dal world generator. Per evitare cascading in sistemi reputation, information_flow e factions durante l'inizializzazione:
- I signal Django sono soppressi tramite un `disable_signals_context_manager` wrapper per la durata dell'inizializzazione.
- I nuovi agenti creati in Fase 3 sono popolati con personalità di default (campionata dalla distribuzione d'era), ruolo di default (ereditato dalla social_class del parent con mapping era-specifico), e nome generato tramite l'helper di naming del world generator esistente.
- La Fase 3 gira DOPO la Fase 1 (piramide d'età) così i nuovi figli minorenni sono aggiunti alla popolazione già-redistribuita senza rebalance ricorsivo.

Risultato: struttura multi-generazionale realistica al tick 0 senza side effect ad altri sottosistemi.

### Fase 4: Check di consistency

Check automatici:

- TFR retrospettivo ≈ TFR d'era entro tolleranza ±20%
- Sex ratio ≈ valore d'era ±0.05
- Life expectancy dalla piramide consistente con era
- Nessun figlio più vecchio del genitore
- Nessun genitore sotto min_reproductive_age al concepimento
- Ogni coppia: entrambi partner vivi, compatibili per età, compatibili per genere secondo couple_type

Fallimenti loggano WARNING ma non bloccano (permette scenari sperimentali).

Risultato loggato come `DemographyEvent(event_type="demographic_initializer", payload={phase_1_resampled: N, phase_2_couples_formed: N, phase_3_genealogies_created: N, phase_4_issues: [...], rng_seed: sim.seed, template_hash: sha256(template_json), duration_ms: elapsed})`. Il template hash permette il rilevamento di modifiche post-hoc al template; rng_seed e durata supportano claim di riproducibilità publication-grade.

## Sezione 11: Malthusian ceiling (vincolo dual-role)

Integrato nella formula fertility di §2. Documentato sia come scientifico (Ashraf & Galor 2011 formalizzazione del preventive check Malthus-Ricardo) sia operativo (limita costo LLM e crescita DB). Questo dual role è dichiarato esplicitamente nelle Known Limitations.

## Sezione 12: Strategia di testing e validazione storica

### Unit test (PostgreSQL; no SQLite)

Per modulo, un test file dedicato:

- `test_mortality.py` — HP a età di test, parametri d'era, decomposizione infantile/giovane-adult/senescenza, tick scaling, attribuzione death cause, risoluzione congiunta mortalità childbirth
- `test_fertility.py` — peak ASFR Hadwiger a R d'era, scaling modulazione Becker, gating avoid_conception, Malthusian ceiling, floor behavior
- `test_couple.py` — stability Gale-Shapley, pair_bond mutual consent, separate rispetta flag d'era, auto-dissoluzione su morte coniuge, mourning ticks
- `test_inheritance.py` — formula polygenic additive, heritability per-tratto, regole social class per-era (primogenitura, Becker-Tomes, shari'a), routing estate tax, trasferimento loans-as-lender, ordering morti simultanee
- `test_migration.py` — field context enrichment, formula Harris-Todaro expected gain, family coordination sposta tutti i dependent, emergency flight trigger solo dopo N tick di starvation, trapped_crisis event
- `test_initialization.py` — distribuzione piramide d'età, formazione coppie, genealogie, check di consistency
- `test_rng.py` — riproducibilità seeded attraverso run

### Integration test (end-to-end)

`test_integration_demography.py` — simulazione full per 100 tick:

- Inizializza world + demografia
- Gira 100 tick di economia + demografia
- Asserisce CBR > 0, CDR > 0, coppie formate, nascite/morti registrate, eredità eseguite, snapshot popolati
- Asserisce nessuna inconsistenza (link parent orfani, agenti età-negativa, etc.)

### Validazione storica (publication-grade, non-blocking)

Due suite di benchmark documentate nel paper:

**Validation 1 — Convergenza statistica su baseline pre_industrial** (1000 tick, 500 agenti, template pre_industrial):

- Life expectancy at birth entro ±10% di Wrigley-Schofield UK 1700 (32-38 anni)
- CBR entro ±15% (30-45/1000/year)
- CDR entro ±15% (25-40/1000/year)
- TFR entro ±10% (4.5-6.5)
- Sex ratio at birth: 1.05 ± 0.03
- Mean age al primo matrimonio: uomini 24-28, donne 22-26 (Hajnal 1965)

**Validation 2 — Risposta a shock** (analogo Irish Famine, 500 agenti, food supply -50% per 365 tick):

- Picco di mortalità: CDR almeno +50% durante lo shock
- Drop di fertility: CBR -30% entro 40 tick (modulazione Becker)
- Emergency flight: >20% della popolazione migra dalle zone affette
- Recovery post-shock: CBR rimbalza sopra baseline entro 2-3 anni (catch-up post-carestia, Wolowyna 1997)

Entrambe le suite producono report committati in `docs/validation/` per citazione del paper.

## Schema del template Demografia

Schema JSON per la porzione demografica del template di simulazione:

```json
{
  "demography": {
    "acceleration": 1.0,
    "max_population": 500,
    "fertility_agency": "biological",
    "mortality": {
      "heligman_pollard": {
        "A": 0.00491, "B": 0.017, "C": 0.102,
        "D": 0.00080, "E": 9.9, "F": 22.4,
        "G": 0.0000383, "H": 1.101,
        "source": "..."
      },
      "maternal_mortality_rate_per_birth": 0.008,
      "neonatal_survival_when_mother_dies": 0.3
    },
    "fertility": {
      "hadwiger": {"H": 5.5, "R": 26, "T": 0.35},
      "becker_coefficients": {
        "beta_0": 0.0, "beta_1": 0.1, "beta_2": -0.05,
        "beta_3": -0.1, "beta_4": 0.2
      },
      "require_couple_for_birth": true,
      "malthusian_floor_ratio": 0.1
    },
    "age_pyramid": [
      [0, 5, 0.15], [5, 10, 0.12]
    ],
    "sex_ratio_at_birth": 1.05,
    "sexual_orientation_distribution": {"heterosexual": 0.92, "bisexual": 0.04, "homosexual": 0.04},
    "couple": {
      "min_marriage_age_male": 16,
      "min_marriage_age_female": 14,
      "allowed_types": ["monogamous", "arranged"],
      "default_type": "monogamous",
      "divorce_enabled": false,
      "marriage_market_type": "autonomous",
      "marriage_market_radius": "same_zone",
      "implicit_mutual_consent": true,
      "mourning_ticks": 365,
      "homogamy_weights": {
        "w_class": 0.4, "w_edu": 0.25, "w_age": 0.20, "w_relationship": 0.15
      }
    },
    "trait_inheritance": {
      "heritability": {
        "openness": 0.41, "conscientiousness": 0.44, "extraversion": 0.54,
        "agreeableness": 0.42, "neuroticism": 0.48,
        "intelligence": 0.55, "emotional_intelligence": 0.40,
        "creativity": 0.22,
        "strength": 0.55, "stamina": 0.52, "agility": 0.45,
        "fertility": 0.50, "mental_health_baseline": 0.40,
        "default": 0.30
      },
      "derived_trait_formulas": {
        "cunning": {
          "description": "Computed at birth from inherited traits (not heritable itself).",
          "formula": "0.4*(1-agreeableness) + 0.3*neuroticism + 0.3*intelligence",
          "range": [0.0, 1.0]
        }
      }
    },
    "social_inheritance": {
      "class_rule": "patrilineal_rigid",
      "education_regression_rho": 0.5
    },
    "economic_inheritance": {
      "rule": "primogeniture",
      "heir_priority": ["spouse", "children", "siblings", "extended_family", "government"],
      "estate_tax_rate": 0.0
    },
    "migration": {
      "flight_trigger_ticks": 30,
      "adulthood_age": 16
    }
  }
}
```

Quattro template di default (mirror del pattern template di Economia): `pre_industrial_christian`, `pre_industrial_islamic`, `industrial`, `modern_democracy`, `sci_fi`. Gli scenari possono sovrascrivere ogni campo.

## Schemi di payload di DemographyEvent

Struttura canonica di `payload` per `event_type`:

| event_type | keys del payload |
|------------|------------------|
| `birth` | `{mother_id, father_id, newborn_id, zone_id, couple_id}` |
| `death` | `{cause, age_at_death, years_lived, zone_id}` |
| `pair_bond` | `{couple_id, couple_type, marriage_market_type}` |
| `separate` | `{couple_id, years_together}` |
| `migration` | `{from_zone, to_zone, reason, household_members}` dove reason ∈ {voluntary, emergency_flight} |
| `mass_flight` | `{from_zone, agents: [agent_ids], trigger_ticks}` |
| `trapped_crisis` | `{zone, consecutive_under_subsistence}` |
| `inheritance_transfer` | `{deceased_id, heir_id, assets: {cash, property_ids, loans_as_lender}, estate_tax_applied, rule_used}` |
| `demographic_initializer` | `{phase_1_resampled, phase_2_couples_formed, phase_3_genealogies, phase_4_issues, rng_seed, template_hash, duration_ms}` |

## File Changes Summary

| File | Operazione | Responsabilità |
|------|-----------|----------------|
| `epocha/apps/demography/` | Nuova app | Tutta la demografia |
| `epocha/apps/demography/models.py` | Nuovo | Couple, DemographyEvent, PopulationSnapshot, AgentFertilityState |
| `epocha/apps/demography/mortality.py` | Nuovo | Heligman-Pollard |
| `epocha/apps/demography/fertility.py` | Nuovo | Hadwiger × Becker × Malthusian |
| `epocha/apps/demography/couple.py` | Nuovo | Gale-Shapley, handler pair_bond/separate |
| `epocha/apps/demography/inheritance.py` | Nuovo | Polygenic additive biologico + derived trait formulas (es. cunning) + ereditarietà economica per-era |
| `epocha/apps/demography/migration.py` | Nuovo | Context enrichment + family coordination + flight |
| `epocha/apps/demography/initialization.py` | Nuovo | Piramide d'età + coppie + genealogie |
| `epocha/apps/demography/engine.py` | Nuovo | Orchestrator process_demography_tick |
| `epocha/apps/demography/template_loader.py` | Nuovo | Parametri per-era |
| `epocha/apps/demography/context.py` | Nuovo | Blocco demografico per decision prompt |
| `epocha/apps/demography/rng.py` | Nuovo | Riproducibilità seeded |
| `epocha/apps/agents/models.py` | Modifica | Aggiungi birth_tick, death_tick, death_cause, other_parent_agent |
| `epocha/apps/agents/decision.py` | Modifica | Aggiungi pair_bond, separate, avoid_conception; filtro dinamico |
| `epocha/apps/simulation/engine.py` | Modifica | Hook process_demography_tick; handler per nuove azioni |
| `epocha/apps/dashboard/formatters.py` | Modifica | Entry di verbi per nuove azioni |
| `config/settings/base.py` | Modifica | Aggiungi `epocha.apps.demography` a INSTALLED_APPS |

## Known Limitations

1. **Parametri per-era fissi**: i parametri Heligman-Pollard e Hadwiger sono costanti entro un template per tutta la simulazione. Le transizioni reali di mortalità e fertilità (mortality transition 1750-1900; fertility transition 1870-1960) non sono modellate. L'MVP valida singole ere statiche. Template di transizione con parametri time-varying rinviati.

2. **Migrazione zona discreta**: le zone sono unità discrete (~10 per world). Nessun gradiente urbano-rurale intra-zona. L'urbanizzazione è dicotomica per zona piuttosto che continua (limite Bairoch 1988).

3. **Heritability costanti attraverso ere**: i valori Polderman (2015) sono stime moderne. La heritability storica differiva (meno varianza ambientale in popolazioni ancestrali omogenee). L'MVP usa costanti moderne; override del template rinviato.

4. **Approssimazione formazione coppia**: lo stable matching Gale-Shapley è un'astrazione razionale. I marriage market reali hanno scelte irrazionali, pressione familiare, meccanica di dote. Semplificazione documentata.

5. **No trasmissione di malattia**: la mortalità è individuale, nessuna dinamica epidemica. Peste, shock pandemici devono essere modellati come eventi template esterni, non emergenti. SIR/SEIR rinviato a sottosistema epidemiologia.

6. **Certezza di paternità 100%**: no infedeltà, no adozione, no concepimento donor modellato. Larmuseau et al. (2016) *Cuckolded fathers rare in human populations* stima non-paternità <1% storicamente in Europa Occidentale, revisionando stime folk-belief precedenti in basso. Questo è sotto la soglia di rumore per gli agent count MVP.

7. **Starting wealth dei figli = 0**: semplificazione. I figli reali consumano risorse familiari durante la crescita. Il modulo consumo di Economy Spec 2 non distingue dipendenti minorenni; estensione rinviata.

8. **Malthusian ceiling dual role**: il soft cap serve simultaneamente modeling ricardiano (1817) scientifico e vincoli operativi di budget LLM. Il dual role è esplicito ma introduce un parametro con due giustificazioni invece di una. Documentato qui per onestà paper.

9. **Loans agent-to-agent senza eredi cancellati**: storicamente i creditori recuperavano dal debitore anche quando il lender moriva. L'MVP semplifica. Estensione rinviata.

10. **Couple type statico**: una volta formata, la couple type non evolve (es. arranged → loving). I matrimoni reali possono shiftare. Rinviato.

11. **Tipi di coppia poligami rinviati** (fix MISS-8): solo `monogamous` e `arranged` couple type sono supportati nell'MVP. `polygynous` e `polyandrous` sono rimossi dall'enum perché richiederebbero relazioni one-to-many che il modello `Couple` attuale (due FK) non può rappresentare. Scenari multi-partner possono essere implementati in futuro rilassando il vincolo di unicità Couple; dichiarli senza meccanismo sarebbe un footgun.

12. **Outlook economico aggregato è euristica di design**: la funzione `compute_aggregate_outlook` combina mood, banking confidence, e zone stability con pesi equali. NON è derivato da Jones & Tertilt (2008); è una proxy pragmatica per "percezione agenti delle condizioni economiche" costruita dallo stato Spec 2 disponibile. La validation di Plan 1 può aggiustare pesi o aggiungere fattori (es. inflazione recente, trend di disoccupazione).

13. **Modulazione Becker usa proxy di female labor participation**: il sottosistema economia non traccia salari gendered, quindi il termine Becker opportunity-cost usa la frazione di femmine adulte in ruoli wage-earning come proxy. Questa è una deviazione nota dalla formulazione originale di Becker (che usa direttamente il tasso di salario femminile).

14. **Fitting parametri Hadwiger rinviato a Plan 1**: i valori R/T/H Hadwiger per-era nelle tabelle della spec sono valori provvisori di seed in range plausibili. Il fit numerico effettivo alle life table delle fonti citate (Wrigley-Schofield, HMD, HFD) è un task di calibrazione in Plan 1, non un artefatto consegnato di questa spec.

15. **Fitting parametri Heligman-Pollard rinviato a Plan 1**: stesso come sopra — gli 8 parametri HP sono provvisori; Plan 1 include un task di calibrazione usando `scipy.optimize.curve_fit` contro le life table citate.

16. **Magnitudo coefficienti Becker provvisorie**: le tabelle di coefficienti β₀-β₄ sono valori di seed. I segni qualitativi seguono predizioni Becker/Jones-Tertilt; le magnitudo verranno calibrate tramite iterazione validation-driven in Plan 1.

## Out of Scope

- Mortalità da malattia (epidemie SIR/SEIR) — sottosistema epidemiologia separato
- Template d'era di transizione (parametri time-varying)
- Adozione, step-parenting, concepimento donor, surrogacy
- Strutture di matrimonio multi-partner (polygynous / polyandrous) — richiede un future redesign del modello Couple
- Migrazione di ritorno come flusso esplicito
- Trasmissione intergenerazionale culturale/linguistica/religiosa (sottosistema cultura)
- Decisioni di carriera e istruzione del ciclo di vita oltre semplice regressione
- Ereditarietà di famiglia estesa oltre 2 generazioni
- Scenari di shock carestia/malattia dichiarati a livello template (richiederebbe layer di event-scripting)

## Design Decisions Log

Audit trail completo delle scelte di design fatte durante brainstorming (2026-04-18), con alternative considerate e razionale. Questa tabella è la giustificazione architetturale per ogni decisione e serve come evidenza citabile per il paper di pubblicazione finale.

| # | Decisione | Scelta | Alternative scartate | Razionale | Fonte chiave |
|---|-----------|--------|----------------------|-----------|--------------|
| 1 | Decomposizione strutturale | Spec unificata + piani di implementazione multi-parte | Quattro spec separate; singolo piano monolitico | La demografia è un ciclo biologico irriducibile. Dividere in spec indipendenti rischia incoerenza di parametri (es. Lee-Carter e Becker devono essere calibrati congiuntamente). Una singola spec con piani sequenziali preserva coerenza e gestisce la complessità di implementazione. | Metodologica (analoga alla struttura di Economy Spec 2) |
| 2 | Scala temporale | Scaling stocastico per-tick con `demography_acceleration` per template d'era | Demography tick separato; scala template-level da sola | Rigore matematico (proprietà ergodica di Lotka 1925 richiede scaling continuo). Acceleration configurabile da template preserva flessibilità scenario senza sacrificare correttezza formale. | Lotka (1925) |
| 3 | Modello di mortalità | Heligman-Pollard con parameter set per-era | Gompertz-Makeham (no hump); Brass logit (richiede standard); Lee-Carter (richiede dati moderni) | HP copre tre regioni empiriche della curva di mortalità umana (infantile, accident hump, senescenza). Calibrazione per-era da fonti storiche indipendenti (Wrigley-Schofield 1981, HMD). Funziona dal Neolitico a futuri speculativi. | Heligman & Pollard (1980) |
| 4 | Modello di fertilità | Hadwiger ASFR × modulazione Becker | ASFR da solo (no risposta economica); Becker puro (no distribuzione d'età); Bongaarts proximate | Hadwiger fornisce rigorosa distribuzione per-età; Becker fornisce aggancio economico diretto. Combinazione standard in economia demografica moderna. | Jones & Tertilt (2008) |
| 5 | Formazione coppia | Modello Couple + azioni LLM pair_bond/separate | Nessuna coppia (solo madre); campo partner semplice; matching automatico | Storia completa di coppia supporta dinastie, divorzio, matrimonio combinato. Agency LLM matcha il principio core di Epocha di decisione strategica emergente. | Gale & Shapley (1962) backend; filosofia Epocha LLM-first |
| 6 | Ereditarietà di tratti | Heritability Polderman per biologico + regole per-era per social/economic | Media genitoriale semplice; polygenic puro senza regole sociali; correzione assortative mating | Genetica quantitativa per biologia (50 anni di twin studies), sociologia/legge per cultura. Matcha modeling demografico-economico contemporaneo (Jones & Tertilt 2008; Chetty et al. 2014). | Polderman et al. (2015); Becker & Tomes (1979) |
| 7 | Migrazione | LLM `move_to` con context arricchito + family coordination + emergency flight | LLM puro senza override crisi; sostituzione probabilistica Harris-Todaro | Bilancia architettura LLM-first con realismo di flight migration sotto pressione di sopravvivenza (Simon 1955 bounded rationality). | Lee (1966); Harris & Todaro (1970); Mincer (1978); O'Rourke (1994) |
| 8 | Ereditarietà economica alla morte | Regola per-era + estate tax configurabile | Divisione universale singola; testamento LLM-driven | Accuratezza storica cross-culturale. Si integra pulitamente con Spec 2 TaxPolicy/government.treasury. Cattura declaratively la leva più consequenziale della concentrazione di ricchezza (Piketty 2014). | Piketty (2014); Goody et al. (1976) |
| 9 | Architettura + gating LLM fertilità | Nuova app `epocha.apps.demography` + `fertility_agency` era-dependent (`biological` vs `planned`) | Parti di app agents o simulation; stocastico puro o LLM-gated puro | Rispecchia il pattern app Economy (validato). Gating era-dependent cattura fertility transition (Coale & Watkins 1986) come proprietà emergente. | Coale & Watkins (1986) |
| 10 | Meccanismo di invecchiamento | Campo `birth_tick` + computo dinamico dell'età | Aggiornamento per-tick dell'età | Elimina scrittura O(N) per tick; no race condition; età sempre consistente. | Best practice ingegneristica |
| 11 | Popolazione iniziale | Demographic initializer con piramide d'età + coppie + genealogie sintetiche | Lasciare output world generator così com'è | Accuratezza storica dal tick 0. Piramide + coppie + genealogie richieste per credibilità scenario pubblicabile. | Wrigley & Schofield (1981) |
| 12 | Population cap | Soft cap malthusiano con floor 0.1 | No cap; hard cap con nascite in coda | Scientificamente fondato (formalizzazione Ashraf & Galor 2011) e operativamente sicuro. Trasparenza dual-role documentata. | Malthus (1798); Ricardo (1817); Ashraf & Galor (2011) |

## FAQ

### Scaling temporale e dinamiche di tick

**D: Perché scalare mortalità e fertilità stocasticamente per tick invece di accumulare eventi attraverso tick?**
R: Lo scaling stocastico per-tick è la **approssimazione lineare** standard di un processo Poisson continuous-time con rate `λ_annual`. Per probabilità annuali piccole (q < 0.1, tipico per fertilità e la maggior parte delle età di mortalità), l'errore dell'approssimazione lineare vs. la conversione geometrica esatta `tick_q = 1 - (1-q_annual)^(tick_years)` è sotto 0.5%. Per q grandi (notabilmente mortalità infantile q ~ 0.20-0.30 in contesti pre-industriali), la forma lineare sotto-stima la probabilità per-tick di ~5-15%. Il motore usa la conversione geometrica per q > 0.1 (helper `geometric_tick_probability`). Accumulare eventi attraverso tick richiederebbe una distribuzione di tempo di attesa e non è necessario alla nostra scala. Il parametro `demography_acceleration` permette compressione temporale scenario-specifica.

**D: Cosa succede se una simulazione gira con `tick_duration_hours = 168` (settimanale)?**
R: Il fattore di scaling `(tick_duration_hours / 8760.0)` gestisce questo automaticamente. Un tick settimanale vede ~7x la mortalità di un tick giornaliero, consistente con l'hazard annuale sottostante.

**D: Perché `demography_acceleration` è per-era piuttosto che per-simulazione?**
R: Ere diverse simulano a scale temporali diverse. Uno scenario Rivoluzione Francese (arco 1-2 anni) può usare acceleration 1.0 (tempo standard). Uno scenario "ascesa di Roma" (500 anni) può usare acceleration 10.0 per comprimere i cicli demografici in tick count fattibili. Il template cattura questo intento narrativo.

### Modello di mortalità

**D: Perché Heligman-Pollard e non Lee-Carter (nominato nella project memory)?**
R: Lee-Carter (1992) richiede dati di mortalità empirici per ogni combinazione popolazione-anno. Epocha simula Inghilterra pre-industriale, Giappone medievale, e sci-fi ipotetica — per la maggior parte di questi, Lee-Carter non ha dati. HP è parametrico con otto parametri che possono essere calibrati a qualsiasi era con life table pubblicate. Lee-Carter resta un'estensione opzionale per scenari moderni dove dati reali sono disponibili.

**D: Perché attribuire causa di morte tramite pesi di componente HP piuttosto che modeling indipendente?**
R: La causa di morte è usata per differenziazione analytics, non realismo biologico. Separare cause esplicitamente (una RV per causa) richiederebbe calibrazione di hazard indipendenti e moltiplicherebbe parametri tunable. Attribuire causalmente alla componente dominante all'età di morte è un'abbreviazione difendibile con assunzioni documentate.

**D: Come è riconciliata la mortalità da parto con la mortalità HP ordinaria?**
R: La mortalità da parto è applicata prima del draw HP ordinario per madri che stanno per partorire nello stesso tick. Questo rispecchia la correlazione reale: eventi di mortalità materna occorrono *durante* il parto, non come draw di senescenza indipendente. Il parametro template `maternal_mortality_rate_per_birth` è calibrato separatamente (Loudon 1992 riporta l'Inghilterra pre-industriale a 5-10 per 1000 nascite; il default template è 0.008 come stima centrale).

### Fertilità

**D: Come i coefficienti Becker riproducono il cambio storico di TFR?**
R: Calibrazione nell'implementazione di Plan 1 contro le tabelle TFR di Jones & Tertilt (2008). Il test di validation 1 richiede che il TFR simulato sotto il template pre-industriale matchi Wrigley-Schofield entro 10%; se no, i coefficienti Becker vengono aggiustati.

**D: Perché avoid_conception usa settlement a tick+1?**
R: Le decisioni dell'agente accadono *dopo* lo step demografico nella pipeline del tick, quindi un'azione al tick T non può influenzare la fertilità al tick T. Il settlement a tick+1 matcha il pattern esistente dal property market di Spec 2. Realisticamente, l'intento di evitare concepimento precede il tick in cui il concepimento occorrerebbe.

**D: Perché non modellare stock contracettivo invece di flag avoid per-tick?**
R: Il flag astrae il comportamento di blocking della fertilità senza modellare metodi specifici. Questo è sufficiente per outcome demografici (l'obiettivo è riprodurre la fertility transition, non classificare metodi contraccettivi). Un modello stock-based può estendere questo in futuro se necessario.

### Formazione coppia

**D: Perché Gale-Shapley per inizializzazione e LLM per pair_bond runtime?**
R: L'inizializzazione richiede un matching globalmente stabile e riproducibile su molti agenti simultaneamente. LLM per-coppia per inizializzazione sarebbe costoso e non-deterministico. Runtime pair_bond è bilaterale e context-dependent — esattamente il tipo di decisione che gli LLM fanno bene. L'inizializzazione dà uno starting state credibile; LLM mantiene decisioni evolutive.

**D: E se un agente ricambia pair_bond dopo la finestra di 1 tick?**
R: La finestra è di default 1 tick ma configurabile. Dopo scadenza, l'intento del proposer originale è stale; la coppia non è formata. Il respondent ipotetico può iniziare una nuova proposta se desiderato.

**D: Come funzionano i matrimoni combinati per decisioni LLM?**
R: Quando `marriage_market_type: "arranged"` è settato nel template, l'agente genitore vede il match pool per i suoi figli adulti non sposati nel suo decision context. Il genitore invoca la standard azione `pair_bond` con un target payload esteso `{"for_child": "<nome_figlio>", "match": "<nome_altro>"}`. Il figlio ha una finestra di 1 tick in cui ricambiare invocando `pair_bond target=<nome_match>` (accetta) o non invocando `pair_bond` (rifiuta). Un rifiuto genera memoria negativa per figlio e genitore. Nessun nuovo nome azione viene introdotto — l'azione esistente `pair_bond` è riutilizzata.

### Ereditarietà di tratti

**D: Perché Polderman (2015) e non twin study trait-specifici?**
R: Polderman integra 50 anni di twin study e dà stime h² consistenti attraverso tratti in una singola metodologia. Gli studi trait-specifici sono citati accanto (Jang 1996, Zietsch 2014, etc.) dove rifiniscono l'aggregato Polderman. Usare un singolo backbone metodologico rende difendibili i confronti cross-trait.

**D: I valori di heritability sono era-specifici?**
R: I valori Polderman sono moderni. La heritability storica può differire perché la varianza ambientale cambia nel tempo. L'MVP usa costanti moderne con il template che fornisce meccanismo di override per future calibrazioni. Questa è una limitazione documentata.

**D: Come viene tratto il rumore ambientale `ε`?**
R: Da una distribuzione Normale la cui media e SD sono uguali alla media e SD del tratto della popolazione al tick 0 della simulazione (congelate). Questo modella l'ambiente come deviazione dal background genetico della popolazione simulata, un approccio standard in genetica quantitativa (Falconer 1996 cap. 8).

### Ereditarietà economica

**D: Perché multiple regole di ereditarietà per era piuttosto che una singola regola?**
R: Accuratezza storica. L'Europa pre-industriale include primogenitura (Inghilterra dopo 1066) e ereditarietà divisibile (Francia prima di Napoleone; tribù germaniche). La civiltà islamica usa shari'a. Società matrilineari esistono attraverso Africa, Sud-est Asiatico. Una singola regola è una misrappresentazione seria. Il template dichiara quale regola si applica; gli utenti possono costruire scenari con customi ereditari diversi.

**D: Cosa succede ai loans dove il deceduto era il lender?**
R: Passano agli stessi eredi sotto la regola di ereditarietà attiva. Se nessun erede (nazionalizzato o senza figli), il loan trasferisce al sistema bancario (lender=None, lender_type="banking") e continua a essere servito. Loans agent-to-agent senza eredi sono semplicemente cancellati all'MVP — questa è una semplificazione documentata.

**D: Come interagisce l'estate tax con government.treasury?**
R: L'estate tax computato è instradato tramite il nuovo helper `add_to_treasury(government, primary_currency_code, tax_revenue)` definito in §Integration Contracts. Questo helper centralizza l'accumulo al treasury, sostituendo la mutazione inline di JSON-dict attualmente usata in economy/engine.py (che questa spec refattorizza all'helper come parte del suo scope).

### Migrazione

**D: E se una famiglia è separata attraverso zone al momento di una decisione move_to?**
R: Solo i membri fisicamente nella zona attuale del decision-maker si muovono con lui tramite coordinamento familiare. Figli adulti o coniugi che vivono in altre zone decidono indipendentemente. Questo cattura la realtà storica di famiglie migranti separate dalla distanza (migrazione interna US 1916-1970, Great Migration).

**D: Come viene computato l'`expected_gain` Harris-Todaro quando la zona destinazione ha un salario sconosciuto?**
R: I salari sono smussati sugli ultimi 5 tick di dati `EconomicLedger` wage. Se una zona non ha storia salariale (neonata), il salario atteso della zona ha default alla media simulation-wide; questa è un'approssimazione esplicita per condizioni iniziali.

**D: Cosa previene runaway emergency flight che migra tutti a una singola zona?**
R: La selezione target usa `max(expected_harris_todaro_gain)`, che tiene conto di salario, disoccupazione, e distanza. Man mano che i rifugiati arrivano in una zona, la disoccupazione sale, riducendo il gain atteso per migranti successivi — un dampening built-in. Questo riproduce il concetto di "migration equilibrium" (Harris & Todaro 1970).

### Dinamiche di popolazione

**D: Perché Malthusian ceiling piuttosto che hard cap sulle nascite?**
R: Il preventive check di Malthus è una riduzione continua nel birth rate man mano che le risorse si restringono, non un halt brusco. Ashraf & Galor (2011) formalizzano questo come funzione smooth. Un hard cap crea comportamento di queue irrealistico e discontinuità.

**D: E se la popolazione cade a quasi zero?**
R: La fertilità riprende al baseline rate pieno (saturation = 0 nella formula del ceiling). Non c'è effetto Allee opposto. Se sono necessarie dinamiche di quasi-estinzione (popolazioni molto piccole faticano a riprodursi per scarsità di partner), questo richiederebbe modeling separato.

**D: Il cap Malthusian può essere disabilitato per scenari specifici?**
R: Sì — imposta `max_population` a valore molto grande (es. 10000) nel template. Lo scaling si attiva solo all'80% del cap, quindi un cap effettivamente illimitato lascia la fertilità pienamente non-vincolata.

### Architettura e riproducibilità

**D: Perché una nuova app piuttosto che estendere agents?**
R: L'app `agents` è già grande (decision, memory, relationships, reputation, information_flow, beliefs, distortion, movement). La demografia la gonfierebbe ulteriormente e mischierebbe concerni biologici con cognitivi. Seguendo il precedente di Economy, la demografia ha la sua app con un boundary pulito.

**D: Come è garantita la riproducibilità?**
R: Tutta la demografia stocastica usa stream RNG seeded per-sottosistema per-tick: `get_seeded_rng(simulation, tick, phase)` dove `phase ∈ {"mortality", "fertility", "couple", "migration", "inheritance", "initialization"}`. Il seed è computato come hash deterministico di `(simulation.seed, tick, phase)`, producendo stream indipendenti per sottosistema così che il riordino di sottosistemi o la soppressione di uno non shifta la sequenza RNG degli altri. Questo abilita riproducibilità anche sotto refattorizzazioni future.

**D: Cosa succede quando la demografia gira senza economia?**
R: La demografia dipende dal context economico (modulazione Becker usa ricchezza, salari, aspettative). Se l'economia non è inizializzata, la modulazione Becker fallback a fattore neutrale (1.0), disabilitando effettivamente l'aggancio economico. Mortalità, aging, formazione coppia, ed ereditarietà girano ancora. Questo permette test demografia standalone.

### Pubblicazione e validazione

**D: Quali sono i target quantitativi per validazione contro dati storici?**
R: Le due suite di validation (§12.3) mirano a specifiche soglie numeriche (±10% per life expectancy, ±15% per CBR/CDR, ±10% per TFR, etc.) contro baseline Wrigley-Schofield e HMD. Fallire queste soglie non è un fallimento CI blocking ma è un flag per review di calibrazione; il paper riporta le tolerance raggiunte.

**D: Cosa dichiara il paper sulla validità demografica?**
R: Modesto ma concreto: "Il sottosistema demografia di Epocha riproduce il baseline pre-industriale Inghilterra di Wrigley-Schofield (1981) entro tolleranza ±15% attraverso cinque indicatori core, e riproduce il pattern qualitativo Irish Famine (O'Rourke 1994) in emergency flight e risposta di fertilità". Non un endorsement di potere predittivo, solo di fedeltà di calibrazione.

### Scalabilità

**D: Qual è l'overhead per-tick atteso rispetto a Spec 2 economia da sola?**
R: Stimato +3-5% wall-clock basato su O(N) mortalità, O(F) fertilità, O(S²) couple market all'inizializzazione-solo, O(E) ereditarietà per morte. Con N=500 e tick-giornaliero: ~1000 operazioni DB aggiuntive per tick, trascurabile rispetto alla pipeline economia esistente. Il costo LLM cresce solo quando nuove azioni (pair_bond, separate, avoid_conception) sono usate, tipicamente <5% di agenti per tick.

**D: Qual è la popolazione massima supportabile?**
R: Il target MVP è 500 agenti con performance accettabile (1000 tick < 30 minuti wall time su laptop di sviluppo). Scalare oltre 500 richiede profiling e probabilmente batching. Il parametro template `max_population` può essere settato più alto se la performance lo permette in deployment specifici.

## Audit Resolution Log

Critical self-review a due step condotto 2026-04-18 prima di scrivere questa spec. Findings e risoluzioni.

(Vedi sezione equivalente nella versione inglese primaria per il log completo di Round 1-4. Questa versione italiana mantiene il solo verdetto finale sotto.)

### Verdetto di convergenza (Round 4, 2026-04-18)

Quattro round di audit avversariale confermano:
- Tutti i findings INCORRECT (10) risolti
- Tutti i UNJUSTIFIED (10) citati esplicitamente o marcati come tunable design parameters (1 challenged come falso positivo aritmetico dell'auditor, verificato indipendentemente)
- Tutti gli INCONSISTENT (5 sostanziali) riconciliati
- Tutti i MISSING (12 edge case) documentati o risolti
- Nessun nuovo BLOCKER o MAJOR introdotto dai fix

**VERDETTO: CONVERGED**

Lo spec soddisfa il criterio di convergenza obbligatoria di CLAUDE.md ed è pronto per validazione umana e implementation planning.
