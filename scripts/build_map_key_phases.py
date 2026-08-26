# -*- coding: utf-8 -*-
"""Chiava e traduce i quindici blocchi di fase. Idempotente."""
from bs4 import BeautifulSoup
from pathlib import Path
import copy

MAP = Path("/app/docs/build-map/epocha-build-map.html")

IT = {
"1a.title": "Economia, strato base",
"1a.pill": "Fatto · mergiato",
"1a.desc": "Produzione CES, <em>tâtonnement</em> walrasiano, multi-valuta, proprietà, imposta piatta, template d'era. Il nucleo di conservazione è stato riscritto e reso deterministico, verificato lungo dodici round d'audit.",
"1b.title": "Economia comportamentale",
"1b.pill": "Fatto",
"1b.needs": "richiede",
"1b.desc": "Aspettative adattive, credito e banche, mercato immobiliare — auditati e vivi. <span class=\"warn\">Le distorsioni della prospect theory e l'incontro sul mercato del lavoro, previsti dall'ambito originario, non sono costruiti.</span>",
"1c.title": "Mercati finanziari",
"1c.pill": "Non iniziata",
"1c.needs": "richiede",
"1c.desc": "Titoli (azioni, obbligazioni, derivati), una borsa, profondità a riserva frazionaria, bolle, panico, contagio. La Spec 3 non è ancora scritta.",
"2.title": "Demografia",
"2.pill": "In corso · prossima",
"2.needs": "richiede",
"3.title": "Tecnologia e progresso",
"3.pill": "Non iniziata",
"3.needs": "richiede",
"3.desc": "Albero tecnologico che rimodella le funzioni di produzione, la capacità militare, la velocità di trasporto e comunicazione. Nessun modello esiste ancora.",
"4.title": "Militare e conflitto",
"4.pill": "Non iniziata",
"4.needs": "richiede",
"4.desc": "Eserciti, attrito di Lanchester, conquista territoriale, impatto della guerra su demografia ed economia. Qualche impalcatura di governo in <code>world.government</code>; nessun modello di attrito.",
"5.title": "Diplomazia e rapporti fra civiltà",
"5.pill": "Non iniziata",
"5.needs": "richiede",
"5.desc": "Trattati, alleanze, sanzioni, tradimento; più civiltà indipendenti che commerciano e si combattono dentro una stessa esecuzione.",
"6.title": "Cultura · religione · istruzione",
"6.pill": "Non iniziata",
"6.needs": "richiede",
"6.desc": "Trasmissione culturale fra generazioni, evoluzione delle credenze, scuole come istituzioni attive. L'infrastruttura delle credenze esiste; le meccaniche sono passive.",
"7.title": "Ambiente · diritto · velocità delle comunicazioni",
"7.pill": "Non iniziata",
"7.needs": "richiede",
"7.desc": "Clima, risorse esauribili, disastri; un processo legislativo e una magistratura; velocità di propagazione dell'informazione legata al livello tecnologico.",
"8.title": "Epidemiologia e sanità pubblica",
"8.pill": "Non iniziata",
"8.needs": "richiede",
"8.desc": "Diffusione SIR/SEIR sulla rete sociale e spaziale; pandemie con ricadute demografiche, economiche e politiche.",
"9.title": "Energia · infrastrutture · città",
"9.pill": "Non iniziata",
"9.needs": "richiede",
"9.desc": "Transizioni energetiche che governano la scala della produzione, infrastrutture fisiche che si degradano senza manutenzione, urbanizzazione emergente. Esiste solo un campo <code>urbanization_index</code>.",
"10.title": "Psicologia delle folle · identità · media",
"10.pill": "Non iniziata",
"10.needs": "richiede",
"10.desc": "Contagio emotivo nelle folle, identità sociali sovrapposte, media e propaganda che amplificano lo strato delle voci. Visione documentata; nessuna meccanica di gioco.",
"11.title": "Rotte commerciali di lunga distanza",
"11.pill": "Non iniziata",
"11.needs": "richiede",
"11.desc": "Rotte spaziali (PostGIS) con costo di trasporto, rischio e capacità vincolata alla tecnologia — dalla via della seta ai container.",
"12.title": "Eredità · lignaggio · memoria",
"12.pill": "Non iniziata",
"12.needs": "richiede",
"12.desc": "Trasferimento intergenerazionale della ricchezza (Piketty r&gt;g), lignaggio familiare (la chiave esterna <code>parent_agent</code> esiste), memoria storica collettiva legata al Knowledge Graph. <b>Il substrato meccanico ora esiste</b> nell'<code>inheritance.py</code> della demografia (Plan 3): gli assi ereditari si liquidano secondo una scala di eredi specifica per era, tassati una volta per trasferimento, e i caratteri e la classe sociale passano alla nascita. Quello che questa fase deve ancora è lo strato dinamico che le sta sopra — la concentrazione della ricchezza misurata lungo le generazioni, i lignaggi come oggetti storici di prima classe, e una memoria che sopravviva agli agenti che l'hanno formata.",
"13.title": "Piattaforma e strumenti",
"13.pill": "In corso",
"13.needs": "richiede",
"13.desc": "Il cruscotto dell'operatore rende otto viste (stato, chat, grafo sociale, analitiche) e genera report a richiesta. <span class=\"warn\">Scraping web, ramificazione e scenari controfattuali, generatore narrativo, modalità intervista, mappa 2D (Pixi.js) e analitiche avanzate sono rinviati.</span>",
}

def key_of(phase):
    num = phase.select_one(".num")
    return num.get_text(strip=True) if num else None

def wrap(el, key, cls, soup):
    """Sostituisce `el` con la coppia it/en."""
    if el.get("data-k"):
        return 0
    en = copy.copy(el)
    en["data-k"] = f"{key}.{cls}"
    en["data-lang"] = "en"
    it = copy.copy(el)
    it["data-k"] = f"{key}.{cls}"
    it["data-lang"] = "it"
    tr = IT.get(f"{key}.{cls}")
    if tr is not None:
        it.clear()
        it.append(BeautifulSoup(tr, "html.parser"))
    el.replace_with(it)
    it.insert_after(en)
    return 1

soup = BeautifulSoup(MAP.read_text(encoding="utf-8"), "html.parser")
n = 0
for phase in soup.select(".phase"):
    k = key_of(phase)
    if not k:
        continue
    for cls in ("title", "desc", "pill", "needs"):
        el = phase.select_one("." + cls.split()[0])
        if el is not None:
            n += wrap(el, k, cls, soup)
MAP.write_text(str(soup), encoding="utf-8")
print(f"{n} elementi chiavati")
missing = [k for k in IT if not soup.select(f'[data-k="{k}"]')]
print("chiavi non applicate:", missing or "nessuna")
