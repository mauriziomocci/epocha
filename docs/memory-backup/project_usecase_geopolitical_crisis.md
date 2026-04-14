---
name: usecase-geopolitical-crisis
description: Caso d'uso di riferimento -- crisi Iran-Israele-Libano 2026 con validazione empirica parziale dei pattern previsti
type: project
originSessionId: 0a27799c-3d4b-4995-b144-424ee45e5764
---
## Scenario

Crisi geopolitica reale Iran-Israele-USA-Libano del 2026. L'utente ha
proposto questo scenario il 2026-04-12 come benchmark per lo sviluppo
di Epocha. Il 2026-04-13 si e' verificato che i pattern descritti dalla
logica di Epocha corrispondono agli eventi reali.

## Esplorazione di scenario originale (2026-04-12)

Basandosi sui modelli scientifici della roadmap (Minsky per la fragilita'
finanziaria, Kindleberger/Arrighi/Kennedy per la cascata egemonica,
Schelling per la strategia del conflitto), avevamo descritto:

**Tick 1-10**: Trump attacca, Israele attacca il Libano, petrolio +40%,
mercati in panico, NATO consulta, Cina media ma accumula riserve,
Russia supporta Iran retoricamente.

**Tre fork possibili**:
- A: Iran risponde militarmente, conflitto regionale
- B: mediazione cinese/europea, cessate il fuoco
- C: EU si spacca, NATO in crisi

**Cascata egemonica**: perdita rotte → shock economico → fiducia
alleanze crolla → capital flight → spirale discendente.

## Validazione empirica (2026-04-14)

L'utente ha confermato che gli eventi reali seguono la sequenza
descritta:

| Pattern previsto | Evento reale |
|-----------------|-------------|
| Trump attacca | Confermato |
| Israele attacca Libano | Confermato |
| Iran risponde militarmente (Scenario A) | Iran attacca basi USA + pozzi petroliferi |
| Chiusura Hormuz | Iran chiude stretto e chiede pedaggi |
| Doppia leva militare + energetica | Confermato (basi + pozzi simultaneamente) |
| Escalation seguita da tentativo di mediazione | Trump cerca mediazione |
| Tregua fragile | "La tregua regge timidamente" |
| Risposta USA economica | Trump chiude porti iraniani |

## Analisi del match

La sequenza attacco → risposta → escalation → mediazione forzata →
tregua fragile e' un pattern classico della teoria dei giochi (Schelling
1960) quando:
- L'attaccante ha superiorita' militare ma dipendenza energetica (USA)
- Il difensore ha inferiorita' militare ma leva geografica (Iran + Hormuz)
- Nessuno vuole la distruzione totale (MAD convenzionale)
- Entrambi cercano un equilibrio di Nash

L'Iran ha colpito simultaneamente basi militari E pozzi petroliferi =
leva militare + energetica. Questo e' il pattern della cascata egemonica:
chi controlla rotte e energia ha il potere negoziale reale.

## Cosa questo implica per Epocha

1. I modelli scientifici nella roadmap (Kindleberger, Arrighi, Schelling,
   Minsky) producono pattern che CORRISPONDONO alla realta' quando i
   parametri sono quelli giusti. La psicostoriografia funziona.

2. Il valore NON e' nella previsione del singolo evento ma
   nell'esplorazione dello spazio dei futuri: avevamo descritto 3 fork,
   la realta' ha seguito principalmente il fork A (risposta militare)
   con elementi di B (mediazione). Un simulatore che esplora tutti e 3
   e li quantifica avrebbe avuto valore analitico reale.

3. La doppia leva Iran (militare + energetica) conferma che i sistemi
   devono essere interconnessi: il modulo militare DEVE comunicare col
   modulo energetico e col modulo economico. Sistemi isolati non
   catturano questa dinamica.

4. La tregua fragile e' il punto dove Epocha potrebbe dare il valore
   massimo: prevedere sotto quali condizioni la tregua regge o crolla
   (variando parametri: coesione interna USA, scorte petrolifere EU,
   mediazione cinese, pressione economica reciproca).

## Domande aperte per simulazione futura

- La tregua regge? Dipende da pressione economica interna (inflazione),
  coesione interna (Turchin asabiya), e se i pedaggi Hormuz diventano
  permanenti (cambio strutturale ordine mondiale, Arrighi).
- Chi cede per primo? USA (polarizzazione alta) vs Iran (regime
  compattato dalla guerra).
- La Cina ne approfitta? Quasi certamente come mediatore (soft power)
  e acquirente di petrolio iraniano scontato.
- I pedaggi permanenti su Hormuz = transizione egemonica in corso?

## Caveat scientifico

La corrispondenza tra pattern previsti e eventi reali NON prova che i
modelli siano "corretti" in senso forte. Potrebbe essere:
- Conferma genuina dei modelli (i pattern sono universali)
- Bias di conferma (abbiamo descritto scenari abbastanza generali da
  matchare molti esiti possibili)
- Coincidenza

La vera validazione richiede simulazioni ripetute con parametri variati
e confronto statistico con esiti storici. Questo e' il lavoro della
psicostoriografia computazionale che Epocha abilitera'.
