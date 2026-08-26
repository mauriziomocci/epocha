# -*- coding: utf-8 -*-
"""Chiava e traduce masthead, colonne, note, regole e substrato. Idempotente."""
from bs4 import BeautifulSoup
from pathlib import Path
import copy

MAP = Path("/app/docs/build-map/epocha-build-map.html")
soup = BeautifulSoup(MAP.read_text(encoding="utf-8"), "html.parser")

IT = {}
IT["mast.eyebrow"] = "Epocha · simulatore di civiltà · mappa di progetto"
IT["mast.h1"] = "La mappa di costruzione — 13 fasi, verificate contro il codice"
IT["mast.dek"] = ("La fonte di verità unica su che cosa è costruito e che cosa no — questa lavagna fa "
 "testo, e ogni sessione che cambia lo stato di una fase deve aggiornarla. Lo stato si verifica contro "
 "l'albero dei sorgenti e il whitepaper, mai ereditandolo da una nota di memoria. La dorsale a sinistra "
 "è l'arco di civiltà pianificato; il substrato a destra è ciò che è già costruito e auditato sotto di esso.")
IT["mast.branch"] = "<b>Ramo</b> develop"
IT["mast.tip"] = "<b>Punta</b> demografia Plan 3 mergiata · economia mergiata a 368e972"
IT["mast.suite"] = "<b>Suite</b> 1573 verdi · ruff pulito"
IT["mast.source"] = "<b>Sorgente</b> docs/build-map/epocha-build-map.html"

IT["col.spine"] = "Dorsale · ordine delle dipendenze"
IT["col.effort"] = "A che punto è il lavoro"
IT["col.substrate"] = "Il substrato sottostante"
IT["col.risks"] = "Rischi trasversali aperti"
IT["col.honest"] = "Tenere onesta questa lavagna"

IT["blk.1"] = "Fase 1 — Economia"
IT["blk.2"] = "Fase 2 — Demografia e generazioni"
IT["blk.3"] = "Fasi 3–12 — L'arco della civiltà"
IT["blk.4"] = "Fase 13 — Piattaforma e strumenti · corre in parallelo a tutte"

IT["note.count"] = ("Contate sulle 13 fasi della dorsale. I sottoblocchi 1a e 1b sono fatti, l'1c non è "
 "iniziato; il blocco pesa sull'economia perché è lì che si è concentrato il lavoro auditato.")
IT["note.substrate"] = ("Già costruiti e auditati — tutto ciò che sta sulla dorsale poggia su questi. Sono "
 "capitoli §4 Methods del whitepaper, non fasi della dorsale.")
IT["note.risks"] = ("Non sono fasi — tagliano la dorsale per traverso. Aperti il 2026-07-17, ciascuno "
 "verificato contro il codice. L'evidenza con file:riga vive nella memoria "
 "<code>project_determinism_enumeration_pending.md</code>.")
IT["note.honest"] = ("Questa pagina è la fonte di verità del progetto sullo stato di costruzione. "
 "Aggiornarla è obbligatorio — non è un'istantanea.")
IT["here.tag"] = "Sei qui"

IT["rule.paper.k"] = "Paper"
IT["rule.rng.k"] = "RNG"
IT["rule.pins.k"] = "Pin"
IT["rule.closed.k"] = "Chiuso"
IT["rule.source.k"] = "Sorgente"
IT["rule.update.k"] = "Aggiorna quando"
IT["rule.verify.k"] = "Verifica prima"

IT["rule.paper.v"] = ("<strong>Corretto il 2026-07-17.</strong> Entrambi i whitepaper affermavano che "
 "esecuzioni con lo stesso seme riproducono uno stato bit-identico e lo stesso registro di decisioni per "
 "agente. Enumerato in modo avversariale (5 FALSE, 7 ambigue, 3 ancore corrette) e riscritto in 13 punti "
 "per lingua: ogni affermazione di riproducibilità è ora circoscritta alla parte non-LLM, perché le "
 "decisioni degli agenti (LLM <code>temperature=0.7</code>) e la generazione del mondo (<code>0.8</code>, "
 "senza seme) non sono riproducibili dal seme — esattamente ciò che <code>models.py:35</code> chiama la "
 "«parte non-LLM». Il difetto non dichiarato dell'RNG dei colpi di stato "
 "(<code>government.py:618</code>) è ora esposto in §4.5.")
IT["rule.rng.v"] = ("L'RNG globale non è mai seminato in <code>agents/</code> e <code>world/</code>: "
 "successo del colpo di stato (<code>government.py:618</code>), dispersione all'arrivo, collocazione "
 "iniziale. <code>get_seeded_rng</code> esiste ed è ratificato in <code>economy/</code> e "
 "<code>demography/</code> — agenti e mondo non l'hanno mai adottato. Il whitepaper ora espone entrambi i "
 "difetti (§4.5 N-9 colpo di stato, §4.6 N-8 movimento) ma la correzione nel codice — adottare "
 "<code>get_seeded_rng</code> in agents e world — non è fatta.")
IT["rule.pins.v"] = ("Circa 23 selezioni sensibili all'ordine in <code>agents/world</code> scelgono una "
 "riga arbitraria quando due righe pareggiano, e la scelta persiste — classe sociale, appartenenza a una "
 "fazione, capo di stato, e quali ricordi arrivano all'LLM. L'enumerazione va rifatta in modo "
 "avversariale: tre grep successivi l'hanno sottostimata (3 → 13 → ~23 siti).")
IT["rule.closed.v"] = ("<strong>R12-DET-1 era un non-difetto</strong> (2026-07-17). "
 "<code>QuerySet.first()</code> applica <code>order_by(\"pk\")</code> ai queryset non ordinati, quindi i "
 "tre siti citati erano già deterministici e la correzione proposta emetteva SQL identico. Sei artefatti "
 "di memoria corretti. Va ricordata l'inversione: è l'<em>assenza</em> di <code>Meta.ordering</code> a "
 "proteggere; la sua <em>presenza</em> su una chiave non univoca è ciò che toglie il criterio di "
 "spareggio.")
IT["rule.source.v"] = ("<code>docs/build-map/epocha-build-map.html</code>, versionata nel repository. Si "
 "modifica lì, poi si ripubblica sullo stesso URL.")
IT["rule.update.v"] = ("una fase cambia stato, un audit converge, un modulo viene cablato nel tick loop, "
 "o un capitolo viene promosso.")
IT["rule.verify.v"] = ("verifica lo stato contro il codice e il whitepaper prima di colorare. Mai "
 "ereditare lo stato da una nota di memoria.")

IT["lab.done"] = '<span class="swatch" style="background:var(--done)"></span> Fatto'
IT["lab.prog"] = '<span class="swatch" style="background:var(--prog)"></span> In corso'
IT["lab.todo"] = '<span class="swatch" style="background:var(--hair-strong)"></span> Non iniziata'

IT["found.pipeline"] = "Pipeline decisionale degli agenti<small>Big Five + memoria + LLM</small>"
IT["found.reputation"] = "Reputazione<small>converso R2 · 2026-05-12</small>"
IT["found.rumor"] = "Propagazione delle voci<small>flusso · distorsione · credenza · affinità</small>"
IT["found.institutions"] = "Istituzioni politiche<small>governo · stratificazione · elezioni</small>"
IT["found.movement"] = "Movimento<small>spostamento fra zone per tick</small>"
IT["found.factions"] = "Fazioni<small>coesione · leadership</small>"
IT["found.kg"] = "Knowledge Graph<small>costruito · audit da fare — prossimo gate</small>"

def wrap(el, key):
    if el is None or el.get("data-k"):
        return 0
    en = copy.copy(el); en["data-k"] = key; en["data-lang"] = "en"
    it = copy.copy(el); it["data-k"] = key; it["data-lang"] = "it"
    tr = IT.get(key)
    if tr is not None:
        it.clear(); it.append(BeautifulSoup(tr, "html.parser"))
    el.replace_with(it); it.insert_after(en)
    return 1

n = 0
n += wrap(soup.select_one(".eyebrow"), "mast.eyebrow")
n += wrap(soup.select_one("h1"), "mast.h1")
n += wrap(soup.select_one(".dek"), "mast.dek")
for key, sp in zip(("mast.branch", "mast.tip", "mast.suite", "mast.source"),
                   [x for x in soup.select(".mast-meta span") if not x.select_one("button")]):
    n += wrap(sp, key)
for key, el in zip(("col.spine", "col.effort", "col.substrate", "col.risks", "col.honest"),
                   soup.select(".col-h")):
    n += wrap(el, key)
for i, el in enumerate(soup.select(".block-label"), 1):
    n += wrap(el, f"blk.{i}")
for key, el in zip(("note.count", "note.substrate", "note.risks", "note.honest"), soup.select(".note")):
    n += wrap(el, key)
n += wrap(soup.select_one(".here-tag"), "here.tag")
rk = ("paper", "rng", "pins", "closed", "source", "update", "verify")
for key, el in zip(rk, soup.select(".rule-k")):
    n += wrap(el, f"rule.{key}.k")
for key, el in zip(rk, soup.select(".rule-v")):
    n += wrap(el, f"rule.{key}.v")
for key, el in zip(("lab.done", "lab.prog", "lab.todo"), soup.select(".lab")):
    n += wrap(el, key)
for key, el in zip(("found.pipeline", "found.reputation", "found.rumor", "found.institutions",
                    "found.movement", "found.factions", "found.kg"), soup.select(".found-name")):
    n += wrap(el, key)

MAP.write_text(str(soup), encoding="utf-8")
print(f"{n} elementi chiavati in questa passata")
soup2 = BeautifulSoup(MAP.read_text(encoding="utf-8"), "html.parser")
print("mancanti:", [k for k in IT if not soup2.select(f'[data-k="{k}"]')] or "nessuna")
