---
name: post-mvp-roadmap
description: Roadmap completa per l'evoluzione sociale, economica, militare, culturale di Epocha -- ogni fase con massimo rigore scientifico. STATO per fase VERIFICATO contro codice/whitepaper il 2026-07-17.
type: project
originSessionId: 0a27799c-3d4b-4995-b144-424ee45e5764
---
Roadmap completa concordata il 2026-04-12. Ogni feature segue il ciclo:
brainstorming -> three-step design -> spec con FAQ -> adversarial audit ->
implementation -> re-audit fino a CONVERGED. Massimo rigore scientifico
su tutto, senza eccezioni.

## STATO VERIFICATO 2026-07-17 (fonte: codice + whitepaper, non memoria)

Verifica fatta contro `epocha/apps/` e `docs/whitepaper/epocha-whitepaper.md`.
I marcatori `STATO:` per fase qui sotto sono aggiornati a questa data. La
legenda dei simboli:

- [DONE] audited e cablato nel tick engine
- [PROG] parziale (modello esiste ma non cablato, oppure scope coperto solo in parte)
- [TODO] non iniziato (nessun modello)

Sintesi one-line:
- **Fase 1a economia base** [DONE] -- audit CONVERGED round 12 (2026-07-16),
  whitepaper §4.8, cablato via `process_economy_tick_new` (`simulation/engine.py:394,486`).
  In chiusura sul branch `20260715-132752-economy-base-layer-audit` (merge pendente).
- **Fase 1b economia comportamentale** [DONE] -- §4.2 (aspettative adattive,
  credito/banca, mercato immobiliare) audited e live. NON costruiti dallo scope
  originale: prospect theory, labor market matching.
- **Fase 1c economia finanziaria** [TODO] -- Spec 3 non ancora scritta.
- **Fase 2 demografia** [PROG] -- modelli mortality/fertility/couple auditati
  (§4.1, Plan 1+2 CONVERGED) e unit-tested MA **non cablati nel tick loop**
  (solo `set_avoid_conception_flag` viene chiamato da engine.py). Manca Plan 4
  (wiring engine + init + validation storica) e Plan 3 (eredita' + migrazione zona).
- **Fasi 3-12** [TODO] -- nessun modello. Infrastruttura parziale isolata:
  `world.government` (fase 4), campo `belief` (fase 6), `urbanization_index`
  (fase 9), FK `parent_agent` (fase 12). Nessuna meccanica.
- **Fase 13 piattaforma/tooling** [PROG] -- `dashboard/` renderizza 8 viste
  (stato, chat, grafo sociale, analytics) + report on-demand. Deferred: web
  scraping, branching/what-if, narrative generator, interview mode, mappa 2D
  Pixi.js, analytics avanzati.

**Substrato gia' costruito e auditato (capitoli §4, NON fasi forward)**, su cui
poggia tutta la spina: §3.2 agent decision pipeline (Big Five + memory + LLM),
§4.3 reputazione (R2, 2026-05-12), §4.4 rumor propagation (info flow/distortion/
belief/affinity, R2), §4.5 istituzioni politiche (R2), §4.6 movimento (R2),
§4.7 fazioni (R2). **§8.1 Knowledge Graph**: costruito (`epocha/apps/knowledge/`,
19 moduli) ma **zero chiamate dal tick engine** e audit PENDENTE -- e' il
prossimo gate dopo l'economia (unico residuo §8).

**Sei qui**: chiusura fase 1a economia base (§4.8). Frontiera successiva:
cablaggio demografia (Plan 4) + audit KG (§8.1). Mappa visuale one-page
pubblicata come artifact il 2026-07-17.

Note: quanto segue mantiene le fonti e la struttura originale del 2026-04-12;
gli STATO: inline erano stale (~94 giorni) e sono sostituiti dalla sintesi sopra.

## Fase 1 -- Economia (IN CORSO)

**1a. Economia base (neoclassica)** -- CES production, Walrasian tatonnement,
multi-currency, property, flat tax, template per era.
STATO (2026-07-17): [DONE] audit CONVERGED round 12, §4.8, cablato nel tick.
Merge pendente sul branch economy-base-layer-audit.
Fonti: Arrow (1961), Walras (1874), Fisher (1911), Ricardo (1817).

**1b. Economia comportamentale** -- property transfers, debito/credito,
labor market matching, prospect theory distortions, friction informativa,
aspettative.
STATO (2026-07-17): [DONE] core §4.2 (aspettative, credito/banca, mercato
immobiliare) audited e live. Prospect theory + labor matching NON costruiti.
Fonti: Minsky (1986), Kahneman & Tversky (1979), Stiglitz (2000),
Mortensen & Pissarides (2010), Krugman (1991).

**1c. Economia finanziaria** -- strumenti finanziari (azioni, obbligazioni,
derivati), borse, sistema bancario con riserva frazionaria, bolle, panico,
contagio.
STATO: da fare dopo 1b.
Fonti: LeBaron (2006), Shiller (2000), Diamond & Dybvig (1983),
Allen & Gale (2000), Arthur (1994).

## Fase 2 -- Demografia e generazioni

**2. Demografia** -- nascita, morte, invecchiamento, eredita' (proprieta'
e tratti), migrazione tra zone. Prerequisito per tutto il resto temporale:
senza generazioni non c'e' evoluzione sociale.
STATO (2026-07-17): [PROG] modelli mortality/fertility/couple auditati §4.1
(Plan 1+2 CONVERGED) e unit-tested ma NON cablati nel tick loop. Manca Plan 4
(wiring engine + init + validation) e Plan 3 (eredita' + migrazione).
Fonti: Lotka (1925) demographic models, Lee & Carter (1992) mortality
modeling, Becker (1991) fertility economics, modelli ABM di demografia
(Billari et al. 2006).

## Fase 3 -- Tecnologia e progresso

**3. Tecnologia** -- albero tecnologico che modifica funzioni di produzione,
capacita' militari, velocita' di comunicazione, efficienza dei trasporti,
organizzazione sociale. Scoperte/innovazioni come eventi emergenti dalla
simulazione (non predeterminate).
STATO: da fare dopo Fase 2.
Fonti: Romer (1990) crescita endogena, Nelson & Winter (1982) teoria
evoluzionaria dell'economia, modelli ABM di innovazione (Dosi et al. 2010).

## Fase 4 -- Sistema militare e conflitto

**4a. Forze armate** -- eserciti come entita' (unita', comandanti, soldati),
reclutamento, addestramento, equipaggiamento legato all'economia e alla
tecnologia, morale legato al sistema politico.
**4b. Guerra** -- conflitto tra fazioni/stati, modelli di attrito
(Lanchester 1916), tattiche, conquista territoriale via PostGIS, assedi,
battaglie con esito probabilistico.
**4c. Impatto** -- vittime (collegato a demografia), distruzione economica,
cambiamento dei confini, trauma (collegato a memoria agenti e mood).
STATO: da fare dopo Fase 3.
Fonti: Clausewitz (1832) "On War", Lanchester (1916) square/linear laws,
Dupuy (1987) TNDM (Tactical Numerical Deterministic Model), Richardson
(1960) arms race models, Axelrod (1984) cooperation/defection.

## Fase 5 -- Diplomazia e relazioni inter-civilta'

**5a. Diplomazia** -- trattati, alleanze, sanzioni economiche, embarghi,
negoziazione, tradimento di alleanze. I leader degli stati prendono
decisioni diplomatiche via LLM informate da personalita', economia,
forza militare.
**5b. Inter-civilta'** -- multiple civilta' indipendenti nella stessa
simulazione che interagiscono via commercio, diplomazia, guerra.
Commercio internazionale (multi-currency gia' predisposta), colonizzazione,
scontro di civilta'.
STATO: da fare dopo Fase 4.
Fonti: Schelling (1960) "Strategy of Conflict", Axelrod (1984),
modelli ABM di relazioni internazionali (Cederman 1997).

## Fase 6 -- Cultura, religione, educazione

**6a. Cultura** -- trasmissione culturale tra generazioni, evoluzione
delle credenze, movimenti artistici e intellettuali, lingua come
barriera/ponte, identita' culturale come fattore di coesione/conflitto.
**6b. Religione** -- sistemi religiosi come istituzioni con credenze
(collegati a ideology nel KG), conversione, riforme, conflitti religiosi,
influenza sulla politica e sulla legge.
**6c. Educazione** -- scuole come istituzioni attive, apprendimento
degli agenti nel tempo, mobilita' sociale intergenerazionale, impatto
sulla tecnologia e sulla produzione.
STATO: da fare dopo Fase 5.
Fonti: Boyd & Richerson (1985) "Culture and the Evolutionary Process",
Axelrod (1997) "Dissemination of Culture", Cavalli-Sforza & Feldman
(1981) cultural transmission, Durkheim (1912) per religione come fatto
sociale.

## Fase 7 -- Ambiente e sistema legale

**7a. Ambiente** -- clima, risorse naturali (esauribili), disastri
naturali, impatto ambientale della produzione, cambiamento climatico
come driver di migrazione e conflitto.
**7b. Sistema legale** -- processo legislativo (il governo emana leggi
durante la simulazione), sistema giudiziario, enforcement, evoluzione
delle norme, diritti civili.
**7c. Comunicazione tecnologica** -- velocita' di propagazione delle
informazioni legata al livello tecnologico (piccione -> telegrafo ->
telefono -> internet -> istantanea). Modifica il sistema di
information flow gia' implementato.
STATO: da fare dopo Fase 6.
Fonti: Ostrom (2009) gestione dei commons, modelli SES (social-ecological
systems), North (1990) "Institutions, Institutional Change and Economic
Performance" per il sistema legale.

## Fase 8 -- Epidemiologia e salute pubblica

**8a. Modello SIR/SEIR** -- propagazione di malattie via rete sociale e
spaziale (PostGIS). Suscettibili -> Esposti -> Infetti -> Recuperati/Morti.
Parametri dipendenti da: densita' di popolazione (zona), sanita'
(istituzione health), tecnologia medica (albero tech), nutrizione
(economia: accesso a beni di sussistenza).
**8b. Pandemie** -- epidemie che attraversano zone e civilta'. Impatto
demografico (mortalita'), economico (forza lavoro ridotta, commercio
interrotto), politico (crisi di legittimita' se il governo non risponde),
sociale (capri espiatori, superstizione vs scienza).
**8c. Salute pubblica** -- sanita' come istituzione attiva (gia' esiste
come tipo istituzionale), ospedali, quarantene, vaccinazioni (legate a
tecnologia).
STATO: da fare dopo Fase 7.
Fonti: Kermack & McKendrick (1927) modello SIR, Anderson & May (1991)
"Infectious Diseases of Humans", modelli ABM epidemiologici (Eubank et al.
2004). Per l'impatto storico: McNeill (1976) "Plagues and Peoples".

## Fase 9 -- Energia e infrastruttura fisica

**9a. Risorse energetiche** -- la transizione energetica come driver
fondamentale del progresso. Muscolo umano/animale -> legna -> carbone ->
petrolio -> gas -> nucleare -> rinnovabili. La fonte energetica disponibile
determina la scala della produzione, la capacita' militare, la velocita'
dei trasporti, e la struttura sociale.
**9b. Infrastruttura fisica** -- strade, ponti, acquedotti, porti, ferrovie,
aeroporti, reti di comunicazione. Costruite con risorse economiche e
lavoro, degradano senza manutenzione (entropia), determinano l'efficienza
del commercio e del movimento (gia' modellati via PostGIS).
**9c. Urbanizzazione** -- crescita delle citta' come fenomeno emergente
dalla concentrazione di commercio, infrastruttura e opportunita'. Le
zone urbane crescono, si espandono, attraggono migranti (collegato a
demografia), producono problemi (sovraffollamento, criminalita',
epidemie in spazi densi).
STATO: da fare dopo Fase 8.
Fonti: Smil (2017) "Energy and Civilization: A History", Braudel (1979)
per infrastruttura pre-industriale, Bettencourt et al. (2007) per le
scaling laws delle citta'.

## Fase 10 -- Psicologia collettiva e identita'

**10a. Psicologia delle folle** -- comportamenti di massa che emergono
quando gli agenti sono in gruppo: panico, euforia collettiva, linciaggi,
rivoluzioni spontanee. Non modellabile come somma di decisioni individuali
-- richiede un meccanismo di "contagio emotivo" separato dal decision
engine individuale.
**10b. Identita' sociale** -- gli agenti si identificano con gruppi
(nazione, religione, classe, etnia, professione) e questa identita'
influenza le decisioni, la coesione, il conflitto. L'appartenenza a
gruppi sovrapposti crea tensioni (un mercante ebreo nella Spagna
medievale: identita' religiosa vs identita' professionale vs identita'
nazionale).
**10c. Media e propaganda** -- chi controlla l'informazione controlla la
societa'. Giornali, radio, TV, social media come mezzi di persuasione
di massa. Il governo puo' usare i media per propaganda (collegato a
repression_level e institutional health di media). L'information flow
gia' modellato diventa il substrato; i media ne amplificano portata e
distorsione.
STATO: da fare dopo Fase 9.
Fonti: Le Bon (1895) "The Crowd", Moscovici (1981) "The Age of the
Crowd", Tajfel (1979) social identity theory, Tajfel & Turner (1986)
intergroup conflict, Herman & Chomsky (1988) "Manufacturing Consent".

## Fase 11 -- Commercio a lunga distanza e rotte

**11. Rotte commerciali** -- la Via della Seta, le rotte atlantiche, le
rotte interstellari. Il commercio a lunga distanza trasforma civilta':
porta ricchezza, idee, malattie, conflitti. Le rotte sono entita'
spaziali (PostGIS) con costi di trasporto, rischi (pirateria, guerre),
e capacita' che dipendono dalla tecnologia (vela -> vapore -> container
-> iperspazio).
STATO: da fare dopo Fase 5 (diplomazia) + Fase 9 (infrastruttura).
Fonti: Braudel (1979) "The Mediterranean", Abu-Lughod (1989) "Before
European Hegemony", Findlay & O'Rourke (2007) "Power and Plenty:
Trade, War, and the World Economy in the Second Millennium".

## Fase 12 -- Eredita', lignaggio e memoria storica

**12a. Eredita'** -- trasmissione intergenerazionale di ricchezza,
proprieta', status sociale, conoscenze. Meccanismo primario di
stratificazione persistente (Piketty 2013: r > g). I figli ereditano
dai genitori, con regole che dipendono dal sistema legale e culturale
(primogenitura, divisione egualitaria, dote).
**12b. Lignaggio e famiglie** -- albero genealogico degli agenti (il campo
parent_agent esiste gia' nel modello Agent). Le famiglie come unita'
sociale con reputazione collettiva (i Borgia, i Medici). Il lignaggio
influenza la legittimita' politica (diritto divino, aristocrazia).
**12c. Memoria storica collettiva** -- la civilta' "ricorda" i suoi
eventi fondativi (la presa della Bastiglia, la fondazione di Roma).
Questi eventi influenzano l'identita' collettiva e le decisioni
future. Collegato al Knowledge Graph: gli eventi storici diventano
parte della memoria culturale, non solo dei singoli agenti.
STATO: da fare dopo Fase 2 (demografia) + Fase 6 (cultura).
Fonti: Piketty (2013) "Le Capital au XXIe siecle", Halbwachs (1950)
"La Memoire Collective", Assmann (2011) "Cultural Memory".

## Fase 13 -- Piattaforma e tooling

**13a. Web scraping** -- acquisizione automatica dati per scenari reali.
**13b. Branching/what-if** -- checkpoint + fork della simulazione.
**13c. Report Agent** -- agente con toolset per report stile enciclopedia.
**13d. Narrative Generator** -- genera un romanzo storico/geopolitico dalla
simulazione. Prosa letteraria rigorosa (ogni evento verificato contro i
dati della simulazione), multilingue, con struttura narrativa in tre atti
(Aristotele), voci distinte per personaggio (Big Five), prospettive
multiple (romanzo corale), stile configurabile (cronaca, romanzo,
reportage, diario, epistolare). Fonti: Riedl & Young (2010), Gervas
(2009), McKee (1997).
**13e. Interview mode** -- interviste post-simulazione agli agenti.
**13e. Mappa 2D** -- Pixi.js per zone e posizioni agenti.
**13f. Miglioramento grafo** -- multi-tipo, tab, sfondo chiaro, densita'.
**13g. Analytics avanzati** -- confronto branch, pattern detection, export.
**13h. Documentazione scientifica pubblica** -- il "paper" di Epocha.

## Principi trasversali

- **Ogni fase segue il ciclo completo**: brainstorming -> three-step
  design -> spec con FAQ -> adversarial scientific audit -> plan ->
  implementation -> re-audit -> CONVERGED
- **Massimo rigore scientifico**: ogni formula citata, ogni parametro
  giustificato, nessun magic number
- **Architettura estensibile**: ogni nuovo sistema si inserisce nel
  tick engine come modulo indipendente con interfacce definite
- **Feedback tra sistemi**: ogni nuovo modulo deve dichiarare
  esplicitamente come interagisce con tutti i moduli esistenti
- **Template configurabili**: ogni era/scenario ha la sua configurazione,
  nessun parametro hardcoded
- **Backward compatible**: simulazioni esistenti non vengono rotte da
  nuovi moduli

## Ordine delle dipendenze

```
Economia base (1a) ← nessuna dipendenza
    ↓
Economia comportamentale (1b) ← 1a
    ↓
Economia finanziaria (1c) ← 1b
    ↓
Demografia (2) ← 1a
    ↓
Tecnologia (3) ← 1a + 2
    ↓
Militare (4) ← 1a + 2 + 3
    ↓
Diplomazia (5) ← 4
    ↓
Cultura/Religione/Educazione (6) ← 2 + 3
    ↓
Ambiente/Legale/Comunicazione (7) ← 1a + 2 + 3
    ↓
Epidemiologia (8) ← 2 + 7 (demografia + ambiente)
    ↓
Energia/Infrastruttura/Urbanizzazione (9) ← 1a + 2 + 3
    ↓
Psicologia collettiva/Identita'/Media (10) ← 6 + information_flow esistente
    ↓
Rotte commerciali (11) ← 5 + 9 (diplomazia + infrastruttura)
    ↓
Eredita'/Lignaggio/Memoria storica (12) ← 2 + 6 (demografia + cultura)
```

Fase 13 (piattaforma/tooling) procede in parallelo a qualsiasi fase.

Note sulle dipendenze:
- Le fasi 8-12 hanno dipendenze parziali, non totali: possono
  iniziare non appena le loro dipendenze dirette sono complete,
  senza aspettare che TUTTE le fasi precedenti siano finite.
- Energia (9) puo' procedere in parallelo a Epidemiologia (8).
- Psicologia collettiva (10) puo' procedere in parallelo a Rotte (11).
- Eredita' (12) richiede demografia (2) e cultura (6) ma non
  necessariamente militare (4) o diplomazia (5).
