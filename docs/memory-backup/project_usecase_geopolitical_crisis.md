---
name: usecase-geopolitical-crisis
description: Caso d'uso di riferimento -- simulare crisi geopolitiche reali come la crisi Iran-Israele-Libano 2026
type: project
originSessionId: 0a27799c-3d4b-4995-b144-424ee45e5764
---
L'utente ha proposto il 2026-04-12 un caso d'uso concreto per Epocha:
simulare la crisi geopolitica reale Iran-Israele-USA-Libano del 2026.

## Scenario

Attacco USA-Israele all'Iran, chiusura dello Stretto di Hormuz, attacchi
al Libano (Hezbollah). Attori multipli: Trump, Netanyahu, Khamenei,
leader europei, Xi, Putin, NATO, EU, BRICS, Hezbollah, UNIFIL.
Dichiarazioni polarizzate ("comizi deliranti di Trump"), mediatori,
neutrali, antagonisti.

## Perche' e' il caso d'uso perfetto

Richiede TUTTI i sottosistemi della roadmap:
- Knowledge Graph: estrarre entita' e relazioni dalle notizie
- Web scraping: acquisire dati in tempo reale
- Economia: petrolio, sanzioni, mercati finanziari, inflazione
- Militare: capacita', conflitto, deterrenza, proxy war
- Diplomazia: alleanze, mediazioni, sanzioni, veti ONU
- Inter-civilta': USA, Iran, Israele, Libano, EU, Cina, Russia
- Psicologia collettiva: opinione pubblica, panico, propaganda
- Energia: dipendenza dal petrolio, Hormuz come chokepoint
- Rotte commerciali: Hormuz = 20% del petrolio mondiale
- Media: propaganda, disinformazione, social media

## Come usarlo per guidare lo sviluppo

Ogni volta che progettiamo un nuovo sottosistema, chiedersi:
"questo modulo consentirebbe di modellare un aspetto della crisi
Iran-Israele-Libano?" Se no, manca qualcosa.

Il caso d'uso serve anche come test di integrazione finale: quando
tutti i sottosistemi saranno implementati, simulare questa crisi
e' il benchmark che dimostra che Epocha funziona su scenari reali.

## Valore di Epocha in questo contesto

Non prevedere IL futuro ma esplorare lo SPAZIO dei futuri possibili:
100 run con parametri diversi (Trump piu'/meno aggressivo, Cina che
media/si schiera, petrolio a 150/200/300$) per identificare pattern
statistici consistenti. Questa e' la psicostoriografia applicata.
