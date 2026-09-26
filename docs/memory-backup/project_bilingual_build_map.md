---
name: project_bilingual_build_map
description: La build map è bilingue dal 2026-08-26, italiano normativo, con una guardia strutturale che impedisce alle due lingue di divergere
metadata:
  type: project
---

# Build map bilingue — chiusa il 2026-08-26

`docs/build-map/epocha-build-map.html` porta **entrambe le lingue in un file
solo**. L'italiano è il testo **normativo**, l'inglese il mirror. Si apre in
italiano da sola, e il default vive nel CSS: senza JavaScript il lettore vede
l'italiano, non le due lingue impilate.

**Un secondo file è stato proposto e ucciso in revisione**: due file sono due
artifact URL, cioè il fork della fonte di verità che la regola CRITICAL vieta per
nome, con la sincronia affidata a una promessa. Non riproporlo.

## Come è fatta

Ogni blocco traducibile è una coppia di gemelli con la stessa `data-k`,
distinti da `data-lang`. Il mirror porta `data-fp`, l'impronta del testo
normativo; entrambi portano `data-fp-self`. Gli identificatori tecnici —
percorsi, SHA, riferimenti di capitolo, numeri di fase, nomi di ramo — **non
sono chiavati** e vivono verbatim dentro entrambi i gemelli, quindi non possono
divergere.

Il tooling è `scripts/build_map_i18n.py`: `fingerprint` ricalcola le impronte
dopo ogni modifica al testo, `extract` dà l'inventario. **Va lanciato ogni volta
che si tocca il testo della mappa**, altrimenti la guardia va rossa.

## La guardia

`epocha/apps/dashboard/tests/test_build_map_bilingual.py`, nove test, ciascuno
provato per mutazione. Sta in `dashboard` e non accanto alla guardia sulle
citazioni in `demography`, che vive lì per ragioni storiche che la spec dice
esplicitamente di non imitare.

**Il test che conta più di tutti** è `test_no_block_is_left_untranslated`, ed è
stato aggiunto DOPO l'audit sul codice: il blocco più grande della lavagna — la
descrizione della fase 2, la frontiera — era uscito in inglese verbatim nello
slot italiano, e tutti gli otto test di allora passavano. Chiavi presenti,
stati concordi, interi concordi (i testi erano identici), impronte fresche
(idem). Nessuno chiedeva se i due testi fossero **diversi**.

## I limiti, che stanno in FR-008 della spec e in nessun'altra sede

Numeri scritti a lettere non confrontati; una traduzione presente ma sbagliata
passa; ricalcolare l'impronta senza tradurre compra il verde; la lingua effettiva
del contenuto non è calcolabile; solo gli interi si confrontano. Il docstring
della guardia **rinvia** a FR-008 invece di ripeterli — una lista chiusa in due
sedi diverge, ed era già divergente.

## Cosa è costato, e le due lezioni

Gate di fase 2: **sette round, 64 rilievi, 17 bloccanti**. Almeno tre round li ha
generati la spec raccontando la propria storia dentro i requisiti: quando la
narrazione è stata separata nel registro, i bloccanti sono passati da tre a uno a
zero. **Scrivere i requisiti senza cronaca dentro, dal primo giorno.**

Audit sul codice: **quattro bloccanti**, tutti nel file pubblicato, e tre erano
test ciechi — la camminata saltava gli elementi con figli e non vedeva la
legenda; lo stato a riposo era verificato per *esistenza* delle regole CSS e non
per *vittoria*, mentre `.count-row .lab` a (0,2,0) batteva `[data-lang="en"]` a
(0,1,0) e mostrava tre etichette in entrambe le lingue.

La traduzione ha anche esposto due difetti che la precedevano: la pagina non
dichiarava il charset (in inglese non si notava, mancavano gli accenti), e
tradurre ha portato un riferimento di capitolo nella stessa regione che nomina
la fonte di genetica quantitativa — la co-locazione che la spec aveva previsto come edge case e che la
guardia sulle citazioni ha colto.

Vedi [[feedback_build_map_source_of_truth]] per la regola, e
[[project_session_resume_2026_07_15]] per lo stato.
