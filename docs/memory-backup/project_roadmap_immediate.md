---
name: immediate-roadmap
description: Roadmap operativa immediata -- Economia Spec 2 Part 3 chiusa, prossimo step Demografia
type: project
originSessionId: f9bc7a55-71c4-45ed-9602-f5e328a6175e
---
# Roadmap operativa immediata

Aggiornata il 2026-04-17.

## 1. Economy Spec 2 Part 3 -- COMPLETATA
Plan 3a + 3b + 3c implementati, mergiati in `develop` con `--no-ff`. 252 test economy passano. Tutto il workflow behavioral (aspettative, credito, banking, property market, espropriazione, hoard, borrow, buy/sell) e' ora integrato nel tick engine.

## 2. Demografia -- PROSSIMO STEP (Fase 2)
Primo step obbligato dopo economia. Collo di bottiglia per tutto il resto.

Ciclo completo: brainstorming -> three-step design -> spec con FAQ -> adversarial audit -> plan -> implementation -> re-audit -> CONVERGED.

Scope previsto:
- Nascita, morte, invecchiamento (Lotka 1925, Lee & Carter 1992)
- Eredita' di tratti (personalita', social_class) e proprieta'
- Migrazione tra zone (push-pull economico)
- Generazioni: il campo parent_agent esiste gia' nel modello Agent
- Fertility legata a economia (Becker 1991)
- Modelli ABM di demografia (Billari et al. 2006)

## 3. Dopo demografia

Si aprono rami paralleli (scegliere con l'utente):
- Tecnologia (3) -- albero tech, scoperte emergenti
- Cultura/Religione/Educazione (6) -- trasmissione culturale
- Ambiente/Legale/Comunicazione (7)
- Militare (4) -> Diplomazia (5) richiede tecnologia

## Decisioni prese

- Economy Spec 3 (finanziaria: borse, derivati) RIMANDATA. Non blocca nessuna fase, si fa dopo demografia o piu' avanti.
- Tooling (web scraping, report agent, narrative generator, mappa 2D) procede in parallelo se c'e' tempo, non ha priorita' sul percorso critico.
- Media layer (giornali, social feed dalla simulazione) e' una visione futura, non una priorita' immediata.

**Why:** Percorso critico concordato il 2026-04-15 ed aggiornato il 2026-04-17 dopo chiusura Spec 2 Part 3: economia -> demografia -> tecnologia. La demografia sblocca tutto il resto della roadmap.

**How to apply:** Partire con brainstorming Demografia al prossimo task, seguendo il ciclo di rigore scientifico standard (three-step design + adversarial audit + convergenza).
