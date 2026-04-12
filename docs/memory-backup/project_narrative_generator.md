---
name: narrative-generator
description: Generatore di romanzo storico/geopolitico dalla simulazione, rigoroso e multilingue
type: project
originSessionId: 0a27799c-3d4b-4995-b144-424ee45e5764
---
L'utente ha richiesto il 2026-04-12 che Epocha produca come output una
narrazione in forma di romanzo storico, politico, geopolitico o altro a
seconda della simulazione. Il testo deve essere rigoroso (ogni evento
corrisponde a dati reali della simulazione) e nella lingua scelta
dall'utente.

## Cosa produce

Un documento narrativo che racconta la storia della simulazione come un
romanzo storico. Non un report analitico (quello e' il Report Agent), ma
prosa letteraria con:

- **Struttura narrativa**: archi narrativi con tensione, climax, risoluzione.
  Non cronologia piatta di eventi ma storia con ritmo.
- **Voci dei personaggi**: ogni agente chiave ha una voce narrativa
  distinta, coerente con la sua personalita' Big Five. Trump parla
  diversamente da Macron. Robespierre diversamente da Luigi XVI.
- **Prospettive multiple**: capitoli da punti di vista diversi (come un
  romanzo corale). Cap 1: il generale iraniano. Cap 2: il trader a Wall
  Street. Cap 3: il rifugiato libanese. Cap 4: l'analista al Pentagono.
- **Contesto e atmosfera**: descrizioni dei luoghi (dalle zone PostGIS),
  del clima economico (dai dati di mercato), della tensione sociale
  (dagli indicatori politici).
- **Rigore assoluto**: ogni evento narrato corrisponde a un evento
  reale della simulazione. Ogni decisione di un personaggio corrisponde
  a una decisione registrata nel DecisionLog. Ogni dato economico
  corrisponde a un PriceHistory o EconomicLedger. La narrazione e'
  fiction nella forma ma fatto nella sostanza.
- **Multilingue**: il testo viene generato nella lingua scelta dall'utente
  (italiano, inglese, francese, tedesco, spagnolo, o qualsiasi lingua
  supportata dall'LLM).

## Come funziona

1. **Seleziona i tick chiave**: il sistema identifica i momenti di svolta
   (Epochal Crisis, cambi di governo, battaglie, crash economici, scoperte)
   e li usa come punti cardine della narrazione.
2. **Per ogni capitolo**: seleziona un punto di vista (agente), raccoglie
   le sue memorie, decisioni, relazioni e il contesto economico/politico
   di quel momento, e genera il testo narrativo via LLM.
3. **Arco narrativo**: il sistema struttura i capitoli in atto I (setup),
   atto II (conflitto), atto III (risoluzione) seguendo la struttura
   in tre atti classica (Aristotele, Poetica; McKee 1997 "Story").
4. **Stile configurabile**: l'utente puo' scegliere lo stile (cronaca
   storica, romanzo letterario, reportage giornalistico, diario personale,
   epistolare).
5. **Verifica di rigore**: ogni affermazione nel testo viene cross-
   referenziata con i dati della simulazione. Se il narratore dice
   "il prezzo del pane raddoppio'", il sistema verifica che PriceHistory
   confermi il raddoppio. Discrepanze = warning.

## Fonti scientifiche

Per la struttura narrativa:
- Aristotele. "Poetica" -- struttura in tre atti
- McKee, R. (1997). "Story: Substance, Structure, Style" -- archi narrativi
- Bal, M. (2017). "Narratology: Introduction to the Theory of Narrative"

Per la narratologia computazionale:
- Riedl, M. & Young, R. (2010). "Narrative Planning: Balancing Plot and
  Character" -- Journal of Artificial Intelligence Research
- Gervás, P. (2009). "Computational Approaches to Storytelling and Creativity"
- Cavazza, M. & Charles, F. (2005). "Dialogue Generation in Character-based
  Interactive Storytelling" -- AIED

## Esempio di output

```
CAPITOLO 7: IL PREZZO DEL PANE

Parigi, 14 luglio 1789

Marie non aveva mai visto le strade cosi' silenziose. Non il silenzio
della notte, che conosceva bene dal suo appartamento sopra la panetteria
di Rue Saint-Antoine. Questo era il silenzio che precede la tempesta --
quel momento in cui l'aria si ferma e i cani smettono di abbaiare.

Il prezzo della farina era raddoppiato in tre settimane. [Dato reale:
PriceHistory tick 42-56, subsistence +98%]. Suo marito Jacques non
dormiva piu'. Ogni mattina calcolava: il costo della farina, il prezzo
a cui poteva vendere il pane, il margine che si assottigliava come la
luna calante. La settimana scorsa aveva dovuto licenziare il garzone.
[Dato reale: AgentInventory.cash tick 50 = 12 livres, sotto la soglia
di sussistenza].

Dal porto arrivavano voci -- distorte, amplificate, terrificanti come
sempre lo sono le voci. [Information flow: hearsay propagato con
distorsione Big Five, reliability 0.49 dopo 2 hop]. Si diceva che il
Re avesse ordinato di sparare sulla folla. Si diceva che Lafayette
avesse disertato. Si diceva che i granai di Versailles fossero pieni
mentre Parigi moriva di fame.

Marie non sapeva cosa fosse vero. Sapeva solo che il pane costava
troppo e che suo figlio aveva fame.
```

## Quando implementare

Fase 13 della roadmap (piattaforma e tooling), come estensione del
Report Agent. Richiede: tutti i dati della simulazione accessibili
(memorie, decisioni, economia, politica), un LLM capace di prosa
letteraria, e il sistema multilingue.

**Why:** Un romanzo generato dalla simulazione e' il modo piu' potente
per comunicare i risultati a un pubblico non tecnico. Un grafico del
Gini non emoziona. La storia di Marie che non puo' comprare il pane
perche' il Gini e' a 0.72 emoziona. E' lo stesso dato, presentato
come narrazione umana.
