---
name: post-mvp-roadmap
description: Roadmap completa per l'evoluzione sociale, economica, militare, culturale di Epocha -- ogni fase con massimo rigore scientifico
type: project
originSessionId: 0a27799c-3d4b-4995-b144-424ee45e5764
---
Roadmap completa concordata il 2026-04-12. Ogni feature segue il ciclo:
brainstorming -> three-step design -> spec con FAQ -> adversarial audit ->
implementation -> re-audit fino a CONVERGED. Massimo rigore scientifico
su tutto, senza eccezioni.

## Fase 1 -- Economia (IN CORSO)

**1a. Economia base (neoclassica)** -- CES production, Walrasian tatonnement,
multi-currency, property, flat tax, template per era.
STATO: Part 1 data layer DONE, Part 2 engine DONE, Part 3 integration DA FARE.
Fonti: Arrow (1961), Walras (1874), Fisher (1911), Ricardo (1817).

**1b. Economia comportamentale** -- property transfers, debito/credito,
labor market matching, prospect theory distortions, friction informativa,
aspettative.
STATO: da fare dopo 1a.
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
STATO: da fare dopo Fase 1.
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

## Fase 8 -- Piattaforma e infrastruttura

**8a. Web scraping** -- acquisizione automatica dati per scenari reali.
**8b. Branching/what-if** -- checkpoint + fork della simulazione.
**8c. Report Agent** -- agente con toolset per report stile enciclopedia.
**8d. Interview mode** -- interviste post-simulazione agli agenti.
**8e. Mappa 2D** -- Pixi.js per zone e posizioni agenti.
**8f. Miglioramento grafo** -- multi-tipo, tab, sfondo chiaro, densita'.
**8g. Analytics avanzati** -- confronto branch, pattern detection, export.

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
Demografia (2) ← 1a (per eredita' e pressione economica)
    ↓
Tecnologia (3) ← 1a + 2 (modifica produzione + generazioni)
    ↓
Militare (4) ← 1a + 2 + 3 (risorse + soldati + armi)
    ↓
Diplomazia (5) ← 4 (equilibrio di forze)
    ↓
Cultura/Religione/Educazione (6) ← 2 + 3 (trasmissione intergenerazionale)
    ↓
Ambiente/Legale/Comunicazione (7) ← tutti i precedenti
```

Fase 8 (piattaforma) puo' procedere in parallelo a qualsiasi fase.
