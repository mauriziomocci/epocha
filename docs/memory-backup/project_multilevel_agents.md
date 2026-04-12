---
name: multilevel-agents
description: Agenti multi-livello -- individui, organizzazioni, stati, coalizioni come agenti con meccanismi decisionali diversi
type: project
originSessionId: 0a27799c-3d4b-4995-b144-424ee45e5764
---
Decisione del 2026-04-12: gli attori a larga scala (NATO, USA, EU, Cina,
OPEC, BRICS, Hezbollah) devono essere modellati come agenti con
personalita', memoria, relazioni e decisioni, ma con meccanismi
decisionali specifici per il loro livello.

## Livelli di agente

| Livello | Esempi | Meccanismo decisionale |
|---------|--------|----------------------|
| Individuo | Trump, Macron, Khamenei | Big Five + LLM (esistente) |
| Organizzazione | NATO, Hezbollah, IAEA, Jacobin Club | Consenso/voto tra membri + leadership |
| Stato | USA, Iran, Israele, Francia | Tipo di governo + leader + interessi |
| Coalizione | BRICS, G7, OPEC, EU | Negoziazione tra stati membri |

## Architettura proposta

Modello OrganizationAgent separato (non polimorfo sull'Agent esistente)
con OneToOne ad Agent per ereditare personalita'/memoria/relazioni, piu':
- members: M2M ad altri agenti (individui o organizzazioni)
- decision_mechanism: "consensus", "majority", "leader_decides",
  "theocratic", "autocratic"
- institutional_inertia: float (resistenza al cambiamento)
- budget/resources: JSONField
- internal_cohesion: float (coesione interna, tipo fazioni)

## Feedback tra livelli

Trump (individuo) → influenza USA (stato) → influenza NATO (coalizione)
Ma NATO ha inerzia istituzionale che resiste ai singoli leader.
La "personalita'" dell'organizzazione emerge dai suoi membri + dalla
sua struttura, non e' imposta dall'esterno.

## Quando implementare

Prerequisito per Fase 5 (diplomazia/inter-civilta'). Va progettato
durante il brainstorming della Fase 5 con il ciclo completo three-step.

Fonte: March & Olsen (1989) "Rediscovering Institutions" per la teoria
delle decisioni organizzative. Cyert & March (1963) "A Behavioral Theory
of the Firm" per il decision-making organizzativo.

**Why:** Senza agenti multi-livello, non si possono modellare crisi
geopolitiche reali dove individui, organizzazioni, stati e coalizioni
interagiscono contemporaneamente.
