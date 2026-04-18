---
name: bilingual-specs
description: REGOLA -- spec file in inglese (primaria) + companion italiano sincronizzato. Code, commit, plan files, docstring restano solo inglese
type: feedback
originSessionId: f9bc7a55-71c4-45ed-9602-f5e328a6175e
---
# Spec bilingue (inglese + italiano)

**Regola**: ogni spec file nel directory `docs/superpowers/specs/` esiste in due versioni sincronizzate:

- `YYYY-MM-DD-<nome>-design.md` — **versione primaria in inglese** (publication standard per citazioni internazionali, convention di repo, paper scientifico)
- `YYYY-MM-DD-<nome>-design-it.md` — **companion in italiano**, lingua preferita dell'utente per la lettura e revisione

Entrambe le versioni sono autorevoli e **devono stare in sync**. Ogni revisione applicata a una viene applicata all'altra nello stesso commit.

## Ambito della regola

**SI applica a**:
- Spec file in `docs/superpowers/specs/`
- Design decisions log, FAQ, audit resolution log, known limitations, bibliografia (resta con citazioni in lingua originale) — tutte le sezioni narrative

**NON si applica a** (restano inglese only):
- Codice sorgente
- Commenti e docstring nel codice
- Commit messages
- Log applicativi
- File di piano in `docs/superpowers/plans/` (per ora; rivalutabile in futuro)
- Test file
- README tecnici
- CLAUDE.md
- Memory files di progetto

## Why

L'utente ha dichiarato il 2026-04-18 che si trova "meglio leggendo in italiano". La spec file e' il documento di riferimento per ogni decisione di design — se l'utente la legge piu' fluidamente in italiano, la sua validazione umana e' piu' profonda e catch piu' errori. Pagare il costo della traduzione (e del sync) e' giustificato dal valore di una validazione umana di qualita' superiore.

Nel contempo, la versione inglese resta primaria perche':
1. Pubblicazione paper scientifico (standard internazionale)
2. Reviewer internazionali
3. Portabilita' del progetto
4. Regola CLAUDE.md preesistente "English only" applicata a tutto tranne le spec

## How to apply

1. **Scrittura iniziale**: si redige la versione inglese nel processo di brainstorming + three-step design + adversarial audit. Dopo la convergenza dell'audit, si produce la versione italiana.

2. **Sincronizzazione**: ad ogni revisione della spec (es. nuovi round audit, correzioni post-review), si applica la modifica a ENTRAMBE le versioni nello stesso commit. Il commit messaggio menziona esplicitamente la sync.

3. **Convenzione di naming**: il file italiano ha suffisso `-it.md` prima dell'estensione. Es.:
   - `2026-04-18-demography-design.md`
   - `2026-04-18-demography-design-it.md`

4. **Bibliografia e citazioni**: restano in lingua originale (inglese per paper inglesi, tedesco per Hadwiger 1940 originale se citato, ecc.). Non si traducono i titoli di paper.

5. **Nomi di modelli, formule, codice**: restano invariati nella versione italiana. Es. "Heligman-Pollard 8-parameter model", `compute_subsistence_threshold`, `Agent.birth_tick` — cosi' come sono.

6. **Retrofit**: le spec esistenti in inglese ricevono la versione italiana su richiesta dell'utente. Non sono obbligatorie per le spec chiuse di Economy Spec 1-2 a meno di richiesta esplicita.

## Disciplina di sync (non negoziabile)

**Divergenza tra versioni = bug di documentazione**. Se si trova una divergenza, si allineano entrambe al contenuto piu' aggiornato, si commita il fix, si continua. Non si procede mai con due versioni desincronizzate.

**Chi controlla il sync**: l'agente Opus che revisiona lo spec. La code review critica (Mandatory Code Review 8 punti) include, per le spec, un 9° punto virtuale: "verifica sync fra versione EN e IT".

## Cost impact

Token ~2x per spec iniziale e per ogni revisione. Accettabile perche' applicato solo a spec file (non a plan, code, docstring). Per sottosistema tipico Epocha con 1000-1500 righe di spec: ~2.500-4.000 token aggiuntivi per traduzione iniziale, ~200-500 token per ogni revisione successiva. Trascurabile rispetto al volume di implementazione.
