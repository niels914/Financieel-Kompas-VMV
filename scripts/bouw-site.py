#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bouwt de website van het Financieel Vastgoedkompas uit het datamodel.

  python3 scripts/bouw-site.py                bouw site/
  python3 scripts/bouw-site.py --controleer   alleen de data nakijken
  python3 scripts/bouw-site.py --links        interne links nakijken na de bouw
  python3 scripts/bouw-site.py --schoon       gegenereerde pagina's eerst weg

Alles is pure Python zonder afhankelijkheden: templates zijn functies die
HTML-tekst teruggeven. De stijl en de gedeelde JavaScript staan in
site/assets/ en worden niet door dit script aangeraakt.

De site moet vanaf schijf werken. Dat sluit twee gebruikelijke oplossingen
uit: vanaf file:// weigert de browser fetch() en ES-modules op CORS, en een
externe SVG-sprite via <use href="sprite.svg#id"> wordt ook geweigerd. Data
komt dus binnen als klassiek <script src> dat een globale zet, en de sprite
wordt in elke pagina ingevoegd.
"""

import html
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kompasdata as K  # noqa: E402

UIT = os.path.join(K.WORTEL, "site")
ASSETS = os.path.join(UIT, "assets")

# Mappen die dit script zelf vult. --schoon leegt alleen deze.
GEGENEREERD = ["instrument", "beslismoment", "vraag"]

SITENAV = [
    ("", "index.html", "Home"),
    ("instrumenten", "instrumenten.html", "Instrumenten"),
    ("beslismomenten", "beslismomenten.html", "Beslismomenten"),
    ("vragen", "vragen.html", "Financiële vragen"),
    ("routeplanner", "routeplanner.html", "Routeplanner"),
    ("adviseur", "adviseur.html", "Adviseur"),
    ("verantwoording", "verantwoording.html", "Verantwoording"),
]

CONCEPTTEKST = ("Conceptprototype – bedoeld voor dialoog, niet voor besluitvorming. "
                "Het datamodel is concept v0.1 en niet vastgesteld.")

HERKOMSTTEKST = (
    "Instrumentnamen, omschrijvingen, bronnen en beheerders komen uit catalogus v0.1. "
    "Alle koppelingen en classificaties — met rollen, fasen, beslismomenten, opgaven, "
    "vragen, effecten en voorwaarden — zijn dummy en alleen bedoeld om de navigatie te tonen.")


def esc(v):
    return html.escape("" if v is None else str(v), quote=True)


def icon(naam, maat=16, dikte=1.7):
    return ('<svg width="%d" height="%d" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="%s" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            '<use href="#%s"/></svg>' % (maat, maat, dikte, naam))


def chip(tekst, soort=None, extra=""):
    kl = "chip" + (" chip--" + soort if soort else "")
    return '<span class="%s"%s>%s</span>' % (kl, extra, esc(tekst))


def js_globaal(naam, data):
    """Een klassiek script dat een globale zet; werkt wel vanaf file://."""
    ruw = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return "window.%s=%s;\n" % (naam, ruw)


def slug(code):
    """Codes uit het model zijn al bestandsveilig, maar we nemen geen risico."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", str(code))


class Bouwer:
    def __init__(self, model, meta, domein=None, aantal_verwijzingen=0):
        self.m = model
        self.meta = meta
        self.domein = domein or {}
        self.aantal_verwijzingen = aantal_verwijzingen
        with open(os.path.join(ASSETS, "sprite.html"), encoding="utf-8") as fh:
            self.sprite = fh.read().strip()
        self.geschreven = []

    # ----------------------------------------------------------------
    # Schil
    # ----------------------------------------------------------------
    def schrijf(self, pad, inhoud):
        vol = os.path.join(UIT, pad)
        os.makedirs(os.path.dirname(vol), exist_ok=True)
        with open(vol, "w", encoding="utf-8") as fh:
            fh.write(inhoud)
        self.geschreven.append(pad)

    def pagina(self, pad, titel, beschrijving, hoofd, nav="", kruimels=None,
               subnav=None, hero=None, contextstrip=False, scripts=None,
               databloks=None, bodyattr=""):
        diepte = pad.count("/")
        b = "../" * diepte

        navlinks = "".join(
            '<a class="sitenav__link" href="%s%s"%s>%s</a>'
            % (b, doel, ' aria-current="page"' if sleutel == nav else "", esc(label))
            for sleutel, doel, label in SITENAV)

        return self._schrijf_pagina(pad, titel, beschrijving, hoofd, b, navlinks,
                                    kruimels or [], subnav, hero, contextstrip,
                                    scripts or [], databloks or [], bodyattr)

    def _schrijf_pagina(self, pad, titel, beschrijving, hoofd, b, navlinks,
                        kruimels, subnav, hero, contextstrip, scripts, databloks,
                        bodyattr=""):
        kruimelhtml = ""
        if kruimels:
            delen = ['<a href="%sindex.html">%s Kompas</a>' % (b, icon("i-home", 13, 1.9))]
            for i, (label, doel) in enumerate(kruimels):
                laatste = i == len(kruimels) - 1
                if laatste:
                    delen.append('<span aria-current="page">%s</span>' % esc(label))
                elif doel:
                    delen.append('<a href="%s%s">%s</a>' % (b, doel, esc(label)))
                else:
                    delen.append('<span>%s</span>' % esc(label))
            kruimelhtml = (
                '<nav class="kruimel" aria-label="Kruimelspoor"><div class="kruimel__inner">'
                + '<span class="kruimel__scheiding" aria-hidden="true">›</span>'.join(delen)
                + "</div></nav>")

        contexthtml = ""
        if contextstrip:
            contexthtml = (
                '<div class="contextstrip" id="contextstrip" hidden>'
                '<div class="contextstrip__inner">'
                '<span class="contextstrip__label">Je zocht voor:</span>'
                '<span class="chip-row" id="contextstrip-labels"></span>'
                '<a class="contextstrip__terug" id="contextstrip-terug" href="%sinstrumenten.html">'
                '%s Terug naar je selectie</a>'
                "</div></div>" % (b, icon("i-arrow-left", 15, 1.9)))

        subnavhtml = ""
        if subnav:
            subnavhtml = ('<nav class="subnav" id="subnav" aria-label="Op deze pagina">'
                          '<div class="subnav__inner">'
                          + "".join('<a class="subnav__link" href="#%s">%s</a>' % (anker, esc(label))
                                    for anker, label in subnav)
                          + "</div></nav>")

        scripthtml = "".join('<script src="%s%s"></script>' % (b, s) for s in scripts)
        datahtml = "".join(
            '<script id="%s" type="application/json">%s</script>'
            % (naam, json.dumps(data, ensure_ascii=False, separators=(",", ":"))
               .replace("\\", "\\\\").replace("</", "<\\/"))
            for naam, data in databloks)

        return self.schrijf(pad, PAGINA % {
            "titel": esc(titel),
            "bodyattr": bodyattr,
            "beschrijving": esc(beschrijving),
            "b": b,
            "sprite": self.sprite,
            "navlinks": navlinks,
            "kruimel": kruimelhtml,
            "context": contexthtml,
            "subnav": subnavhtml,
            "hero": hero or "",
            "hoofd": hoofd,
            "hoofd_klasse": "shell",
            "concept": esc(CONCEPTTEKST),
            "icoon_info": icon("i-info", 15),
            "icoon_zoek": icon("i-search", 15),
            "icoon_bookmark": icon("i-bookmark", 15, 1.9),
            "icoon_close": icon("i-close", 17, 1.8),
            "icoon_copy": icon("i-copy", 15, 1.8),
            "icoon_trash": icon("i-trash", 15, 1.8),
            "icoon_compass": icon("i-compass", 26, 1.6),
            "versie": esc(self.meta["versie"]),
            "datum": esc(self.meta["datum"]),
            "data": datahtml,
            "scripts": scripthtml,
        })


    # ----------------------------------------------------------------
    # Afgeleide gegevens, één keer berekend
    # ----------------------------------------------------------------
    def bereken(self):
        self.fasen = self.m.fasen_op_rij()

        # Kenmerksets per instrument: waarop het filtert en waarop het lijkt.
        self.kenmerk = {}
        for i in self.m.tab("instrument"):
            c = i["instrument_code"]
            kn = {
                "type": [i["primaire_instrumenttype_id"]] if i.get("primaire_instrumenttype_id") else [],
                "complexiteit": [i["complexiteitsniveau"]] if i.get("complexiteitsniveau") else [],
                "doorlooptijd": [i["doorlooptijd_categorie"]] if i.get("doorlooptijd_categorie") else [],
                "openstelling": [],
            }
            for naam, _, _ in KOPPELING:
                kn[naam] = []
            self.kenmerk[c] = kn
        for naam, tabel, veld in KOPPELING:
            for r in self.m.tab(tabel):
                kn = self.kenmerk.get(r.get("instrument_id"))
                if kn is not None and r.get(veld) is not None:
                    kn[naam].append(str(r[veld]))
        for r in self.m.tab("openstelling"):
            kn = self.kenmerk.get(r.get("instrument_id"))
            if kn is not None and r.get("openstelling_status"):
                kn["openstelling"].append(r["openstelling_status"])

        # Vastgelegde relaties, beide kanten op.
        self.relaties = {}
        for r in self.m.tab("instrument_relatie"):
            van, naar = r.get("van_instrument_id"), r.get("naar_instrument_id")
            if not van or not naar:
                continue
            rtype = self.m.naam("instrument_relatietype", r.get("relatietype_id"))
            for a, b in ((van, naar), (naar, van)):
                self.relaties.setdefault(a, []).append(
                    (b, rtype, r.get("relatiesterkte"), r.get("is_validated"),
                     r.get("toelichting")))

        self.aantal_instrumenten = len(self.m.tab("instrument"))
        met_vw = {r.get("instrument_id") for r in self.m.tab("instrument_voorwaarde")}
        self.zonder_voorwaarden = self.aantal_instrumenten - len(met_vw)
        self.zonder_relatie = self.aantal_instrumenten - len(self.relaties)
        self.aantal_relaties = len(self.m.tab("instrument_relatie"))

        # Een meter die op elke pagina hetzelfde aanwijst, liegt over de
        # data. Alleen tonen als de sterkte daadwerkelijk varieert.
        sterktes = {r.get("effectsterkte") for r in self.m.tab("instrument_effect")}
        self.sterkte_varieert = len({s for s in sterktes if s}) > 1

        # Bron-URL per instrument, voor de knop in de hero.
        self._bronurl = {}
        for r in self.m.tab("instrument_bron"):
            code = r.get("instrument_id")
            if code in self._bronurl and r.get("is_primary") != "ja":
                continue
            url = self.url_van_bron(r.get("bron_id"))
            if url:
                self._bronurl[code] = url

    # Bron-titels zijn een mengsel: soms een kale URL, soms een
    # literatuurverwijzing. Alleen het eerste maken we klikbaar.
    DOMEIN = re.compile(r"^([a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)+(?:/[^\s;,()]*)?)")

    def url_van_bron(self, titel):
        t = str(titel or "").strip()
        if t.startswith("http://") or t.startswith("https://"):
            return t
        m = self.DOMEIN.match(t)
        return "https://" + m.group(1) if m else None

    def bronurl(self, instrumentcode):
        return self._bronurl.get(instrumentcode)

    def bronlink(self, titel):
        url = self.url_van_bron(titel)
        if not url:
            return esc(titel)
        return ('<a href="%s" target="_blank" rel="noopener">%s %s</a>'
                % (esc(url), esc(titel), icon("i-external", 12, 2)))

    def clusterkleur(self, code):
        return CLUSTERKLEUR.get(code, "var(--vmv-grey-400)")

    def verwant_berekend(self, code, n=5):
        """Instrumenten die de meeste kenmerken delen.

        Het model legt maar 17 relaties expliciet vast; zonder deze
        aanvulling blijft het blok op 53 van de 77 pagina's leeg.
        """
        eigen = self.kenmerk[code]
        al_vast = {r[0] for r in self.relaties.get(code, [])}
        dims = [("opgave", "opgave", 3), ("rol", "rol", 2), ("fase", "fase", 3),
                ("vraag", "financiële vraag", 2), ("type", "type", 1),
                ("moment", "beslismoment", 3)]
        scores = []
        for ander, kn in self.kenmerk.items():
            if ander == code or ander in al_vast:
                continue
            punten, labels = 0, []
            for sleutel, label, gewicht in dims:
                gedeeld = set(eigen[sleutel]) & set(kn[sleutel])
                if gedeeld:
                    punten += gewicht * len(gedeeld)
                    labels.append(label)
            if punten >= 5 and len(labels) >= 2:
                scores.append((punten, ander, labels))
        scores.sort(key=lambda x: (-x[0], x[1]))
        return [(ander, labels) for _, ander, labels in scores[:n]]

PAGINA = """<!doctype html>
<html lang="nl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(titel)s · Financieel Vastgoedkompas</title>
<meta name="description" content="%(beschrijving)s">
<meta name="robots" content="noindex, nofollow">
<link rel="stylesheet" href="%(b)sassets/kompas.css">
</head>
<body%(bodyattr)s>
<a class="skiplink" href="#hoofdinhoud">Naar de inhoud</a>

%(sprite)s

<header class="topbar">
  <div class="topbar__inner">
    <a class="brand" href="%(b)sindex.html">
      <span class="brand__mark">%(icoon_compass)s</span>
      <span class="brand__name">Financieel Vastgoedkompas<span>Verduurzaming Maatschappelijk Vastgoed</span></span>
    </a>
    <div class="zoekveld">
      <span class="zoekveld__icoon">%(icoon_zoek)s</span>
      <label class="visually-hidden" for="topzoek">Zoek in de instrumenten</label>
      <input type="search" id="topzoek" placeholder="Zoek een instrument…">
    </div>
    <div class="topbar__actions">
      <button type="button" class="btn btn--small" data-action="open-selectie" aria-haspopup="dialog">
        %(icoon_bookmark)s Mijn selectie <span class="mijnlijst__telling" id="selectie-telling" data-leeg="ja"></span>
      </button>
      <button type="button" class="btn btn--small" data-action="open-reflection" aria-expanded="false" aria-controls="reflectiepaneel">
        Reflectie
      </button>
    </div>
  </div>
</header>

<div class="conceptbar"><div class="conceptbar__inner">%(icoon_info)s<span>%(concept)s</span></div></div>

<nav class="sitenav" aria-label="Hoofdnavigatie"><div class="sitenav__inner">%(navlinks)s</div></nav>

%(kruimel)s
%(context)s
%(hero)s
%(subnav)s

<main class="%(hoofd_klasse)s" id="hoofdinhoud" tabindex="-1">
%(hoofd)s
</main>

<footer class="sitefoot">
  <div class="sitefoot__inner">
    <div>
      <p class="small muted" style="margin-bottom:8px"><strong>Financieel Vastgoedkompas</strong> ·
        conceptprototype op datamodel %(versie)s (%(datum)s) · gebouwd binnen het programma
        Verduurzaming Maatschappelijk Vastgoed.</p>
      <p class="tiny muted">De inhoud is deels dummy en niet vastgesteld door het kernteam.
        Gebruik deze site om de navigatie te beoordelen, niet om beslissingen op te baseren.</p>
    </div>
    <div class="sitefoot__links">
      <a href="%(b)sverantwoording.html">Verantwoording en herkomst</a>
      <a href="%(b)sinstrumenten.html">Instrumenten</a>
      <a href="%(b)sindex.html">Home</a>
    </div>
  </div>
</footer>

<div class="modal-backdrop" id="modal-backdrop" hidden>
  <div class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-titel" id="modal" tabindex="-1">
    <div class="modal__head">
      <div>
        <span class="viewhead__eyebrow" id="modal-eyebrow"></span>
        <h2 id="modal-titel"></h2>
      </div>
      <button type="button" class="iconbtn" data-action="close-modal" aria-label="Sluit venster">%(icoon_close)s</button>
    </div>
    <div class="modal__body" id="modal-body"></div>
    <div class="modal__foot" id="modal-foot"></div>
  </div>
</div>

<aside class="drawer" id="reflectiepaneel" role="dialog" aria-modal="false" aria-labelledby="reflectie-titel" hidden>
  <div class="drawer__head">
    <div>
      <span class="viewhead__eyebrow">Dialoog</span>
      <h2 id="reflectie-titel">Reflectievragen</h2>
    </div>
    <button type="button" class="iconbtn" data-action="close-reflection" aria-label="Sluit reflectiepaneel">%(icoon_close)s</button>
  </div>
  <div class="drawer__body">
    <p class="notice notice--neutral small" style="margin-bottom:16px">%(icoon_info)s
      <span>Je aantekeningen blijven alleen in deze browser bewaard. Dit is geen formele
      onderzoeksregistratie; kopieer je tekst als je die wilt delen.</span></p>
    <div class="stack stack--tight" id="reflectie-velden"></div>
  </div>
  <div class="drawer__foot">
    <button type="button" class="btn btn--primary" data-action="reflectie-kopieer">%(icoon_copy)s Kopieer reflecties</button>
    <button type="button" class="btn" data-action="reflectie-wis">%(icoon_trash)s Wis reflecties</button>
    <span class="tiny muted" id="reflectie-status" aria-live="polite" style="flex-basis:100%%"></span>
  </div>
</aside>

<div class="toasts" id="toasts" role="status" aria-live="polite" aria-atomic="false"></div>

%(data)s
<script>window.KOMPAS={basis:"%(b)s"};</script>
<script src="%(b)sassets/kompas-namen.js"></script>
<script src="%(b)sassets/kompas.js"></script>
%(scripts)s
</body>
</html>
"""

# ====================================================================
# Kenmerken per instrument
# ====================================================================
KOPPELING = [
    ("rol", "instrument_rol", "rol_id"),
    ("fase", "instrument_procesfase", "procesfase_id"),
    ("moment", "instrument_beslismoment", "beslismoment_id"),
    ("opgave", "instrument_opgave", "opgave_id"),
    ("vraag", "instrument_financiele_vraag", "financiele_vraag_id"),
    ("objecttype", "instrument_objecttype", "objecttype_id"),
    ("eigenaar", "instrument_eigenaartype", "eigenaartype_id"),
    ("route", "instrument_financiele_route", "financiele_route_id"),
    ("gebied", "instrument_werkingsgebied", "werkingsgebied_id"),
]

# Vaste kleur per rolcluster, gelijk aan de JavaScript in de browser.
CLUSTERKLEUR = {
    "RC-01": "#1f6fb2", "RC-02": "#3e9b62", "RC-03": "#12a3a0", "RC-04": "#b0566a",
    "RC-05": "#d98f2f", "RC-06": "#5a6fb8", "RC-07": "#9462a6", "RC-08": "#e2833c",
    "RC-09": "#57b6a4",
}

STATUSKLEUR = {
    "open": "success", "doorlopend": "teal", "verwacht": "blue",
    "gesloten": "critical", "onbekend": "",
}

# Richting uit het model -> pictogram en klasse.
RICHTING = {
    "verlaagt": ("i-arrow-down", "verlaagt"),
    "verhoogt": ("i-arrow-up", "verhoogt"),
    "vergroot": ("i-arrow-up", "vergroot"),
    "verschuift": ("i-swap", "verschuift"),
    "neutraal": ("i-minus", "neutraal"),
}

MAANDEN = ["januari", "februari", "maart", "april", "mei", "juni", "juli",
           "augustus", "september", "oktober", "november", "december"]


def datum_nl(iso):
    """2026-10-16 -> 16 oktober 2026. Onbekende vorm gaat ongewijzigd terug."""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", str(iso or ""))
    if not m:
        return str(iso or "")
    return "%d %s %s" % (int(m.group(3)), MAANDEN[int(m.group(2)) - 1], m.group(1))


class Instrumentpagina:
    """Alles wat één instrumentpagina nodig heeft, bij elkaar."""

    SUBNAV = [
        ("past", "Past dit bij mij"),
        ("effect", "Effect"),
        ("voorwaarden", "Voorwaarden"),
        ("gebruik", "Gebruik"),
        ("proces", "Proces"),
        ("rollen", "Rollen"),
        ("vragen", "Vragen"),
        ("verwant", "Verwant"),
        ("herkomst", "Herkomst"),
    ]

    def __init__(self, bouwer, code):
        self.b = bouwer
        self.m = bouwer.m
        self.code = code
        self.i = self.m.rec("instrument", code)
        self.kn = bouwer.kenmerk[code]

    # -- kleine bouwstenen ------------------------------------------
    def leeg(self, tekst):
        return '<p class="leeg">%s<span>%s</span></p>' % (icon("i-info", 15), esc(tekst))

    def mchip(self, label, href, groep=None, code=None, primair=False,
              relevantie=None, titel=None):
        klassen = "mchip" + (" mchip--primair" if primair else "")
        ctx = ' data-ctx="%s:%s"' % (esc(groep), esc(code)) if groep and code else ""
        stip = ""
        if relevantie:
            stip = ('<span class="mchip__stip mchip__stip--%s" aria-hidden="true"></span>'
                    % esc(relevantie))
        extra = ' title="%s"' % esc(titel) if titel else ""
        return ('<a class="%s" href="%s"%s%s>%s%s</a>'
                % (klassen, esc(href), ctx, extra, stip, esc(label)))

    def rij(self, label, sub, waarden):
        return ('<div class="matchrij"><div class="matchrij__label">%s<span>%s</span></div>'
                '<div class="matchrij__waarden">%s</div></div>'
                % (esc(label), esc(sub), waarden or
                   '<span class="muted small">niet vastgelegd</span>'))

    def filterlink(self, groep, code):
        return "../instrumenten.html?%s=%s" % (groep, code)

    # -- blok 1: past dit bij jouw situatie -------------------------
    def blok_past(self):
        rijen = []

        # Opgave
        bronnen = self.m.bij("instrument_opgave", "instrument_id", self.code)
        chips = "".join(self.mchip(self.m.naam("opgave", r["opgave_id"]),
                                   self.filterlink("opgave", r["opgave_id"]),
                                   "opgave", r["opgave_id"],
                                   primair=r.get("relevantie") == "hoog",
                                   relevantie=r.get("relevantie"),
                                   titel="relevantie: %s" % r.get("relevantie", "onbekend"))
                        for r in bronnen)
        rijen.append(self.rij("Opgave", "waar je aan werkt", chips))

        # Rol
        rollen = self.m.bij("instrument_rol", "instrument_id", self.code)
        chips = "".join(self.mchip(self.m.naam("rol", r["rol_id"]),
                                   self.filterlink("rol", r["rol_id"]),
                                   "rol", r["rol_id"],
                                   primair=r.get("is_primary") == "ja",
                                   relevantie=r.get("relevantie"),
                                   titel="%s · relevantie: %s"
                                         % (r.get("rol_bij_gebruik", "betrokken"),
                                            r.get("relevantie", "onbekend")))
                        for r in rollen)
        rijen.append(self.rij("Rol", "wie je bent", chips))

        # Procesfase
        fasen = self.m.bij("instrument_procesfase", "instrument_id", self.code)
        chips = "".join(self.mchip("%s · %s" % (r["procesfase_id"],
                                                self.m.naam("procesfase", r["procesfase_id"])),
                                   self.filterlink("fase", r["procesfase_id"]),
                                   "fase", r["procesfase_id"],
                                   primair=r.get("is_primary") == "ja",
                                   relevantie=r.get("relevantie"))
                        for r in fasen)
        rijen.append(self.rij("Procesfase", "waar je nu staat", chips))

        # Beslismoment
        momenten = self.m.bij("instrument_beslismoment", "instrument_id", self.code)
        chips = "".join(self.mchip(self.m.naam("beslismoment", r["beslismoment_id"]),
                                   "../beslismoment/%s.html" % slug(r["beslismoment_id"]),
                                   "moment", r["beslismoment_id"],
                                   primair=r.get("is_primary") == "ja",
                                   relevantie=r.get("relevantie"),
                                   titel="ondersteunt bij: %s"
                                         % r.get("ondersteuningsfunctie", "onbekend"))
                        for r in momenten)
        rijen.append(self.rij("Beslismoment", "welk besluit voorligt", chips))

        # Objecttype en eigenaartype
        obj = self.m.bij("instrument_objecttype", "instrument_id", self.code)
        chips = "".join(self.mchip(self.m.naam("objecttype", r["objecttype_id"]),
                                   self.filterlink("objecttype", r["objecttype_id"]),
                                   "objecttype", r["objecttype_id"],
                                   primair=r.get("is_primary") == "ja")
                        for r in obj)
        rijen.append(self.rij("Vastgoed", "om welk type gebouw het gaat", chips))

        eig = self.m.bij("instrument_eigenaartype", "instrument_id", self.code)
        chips = "".join(self.mchip(self.m.naam("eigenaartype", r["eigenaartype_id"]),
                                   self.filterlink("eigenaar", r["eigenaartype_id"]),
                                   "eigenaar", r["eigenaartype_id"],
                                   primair=r.get("is_primary") == "ja")
                        for r in eig)
        rijen.append(self.rij("Eigenaar", "wie het vastgoed bezit", chips))

        # Werkingsgebied en financiële route
        geb = self.m.bij("instrument_werkingsgebied", "instrument_id", self.code)
        chips = "".join(self.mchip(r["werkingsgebied_id"],
                                   self.filterlink("gebied", r["werkingsgebied_id"]),
                                   "gebied", r["werkingsgebied_id"],
                                   primair=r.get("is_primary") == "ja")
                        for r in geb)
        rijen.append(self.rij("Werkingsgebied", "waar het geldt", chips))

        return ('<section class="blok" id="past" aria-labelledby="past-kop">'
                '<div class="blok__kop"><h2 id="past-kop">Past dit bij jouw situatie?</h2></div>'
                '<p class="blok__uitleg">De kenmerken waarop dit instrument in het model is '
                'vastgelegd. Een omlijnde kenmerk is van toepassing, een gevulde is primair. '
                'Klik door om alle instrumenten met dat kenmerk te zien.</p>'
                '<p class="blok__uitleg" id="contextnoot" hidden></p>'
                '<div class="card"><div class="card__body">%s</div></div>'
                "</section>" % "".join(rijen))

    # -- blok 2: effect op de businesscase --------------------------
    def blok_effect(self):
        effecten = self.m.bij("instrument_effect", "instrument_id", self.code)
        if not effecten:
            inhoud = self.leeg("Het effect van dit instrument is nog niet in het model vastgelegd.")
        else:
            per_cat = {}
            for e in effecten:
                ty = self.m.rec("effecttype", e.get("effecttype_id")) or {}
                per_cat.setdefault(ty.get("effectcategorie", "overig"), []).append((e, ty))
            delen = []
            for cat in sorted(per_cat):
                delen.append('<p class="effect__categorie">%s</p>' % esc(cat))
                for e, ty in per_cat[cat]:
                    ico, kl = RICHTING.get(e.get("effectrichting"), ("i-minus", "neutraal"))
                    sterkte = ""
                    if self.b.sterkte_varieert:
                        vol = {"laag": 1, "middel": 2, "sterk": 3}.get(e.get("effectsterkte"), 0)
                        sterkte = ('<div class="effect__sterkte">'
                                   + "".join('<span class="effect__pip%s"></span>'
                                             % (" is-vol" if n < vol else "") for n in range(3))
                                   + '<span class="effect__sterktelabel">%s</span></div>'
                                   % esc(e.get("effectsterkte", "")))
                    toel = []
                    if e.get("effect_toelichting"):
                        toel.append(e["effect_toelichting"])
                    if not self.b.sterkte_varieert and e.get("effectsterkte"):
                        toel.append("sterkte: %s" % e["effectsterkte"])
                    # "verlaagt" + "verlaagt initiële investering" stottert; de naam
                    # van het effecttype bevat de richting meestal al.
                    richting = e.get("effectrichting", "")
                    typenaam = ty.get("naam", "")
                    voorvoegsel = "" if typenaam.lower().startswith(richting.lower()) \
                        else (richting + " ")
                    delen.append(
                        '<div class="effect effect--%s">'
                        '<span class="effect__richting" title="%s">%s</span>'
                        '<div><div class="effect__naam">%s%s</div>%s</div>%s</div>'
                        % (kl, esc(richting), icon(ico, 16, 2),
                           esc(voorvoegsel), esc(typenaam),
                           '<div class="effect__toelichting">%s</div>' % esc(" · ".join(toel))
                           if toel else "",
                           sterkte))
            inhoud = "".join(delen)

        routes = self.m.bij("instrument_financiele_route", "instrument_id", self.code)
        routehtml = ""
        if routes:
            regels = []
            for r in routes:
                ro = self.m.rec("financiele_route", r["financiele_route_id"]) or {}
                regels.append('<a class="mchip%s" href="%s">%s</a>'
                              % (" mchip--primair" if r.get("is_primary") == "ja" else "",
                                 esc(self.filterlink("route", r["financiele_route_id"])),
                                 esc(ro.get("naam", r["financiele_route_id"]))))
            routehtml = ('<hr class="divider"><span class="label">Oplossingsrichting</span>'
                         '<div class="matchrij__waarden">%s</div>'
                         '<p class="tiny muted" style="margin-top:8px">De financiële route '
                         'plaatst dit instrument in een oplossingsrichting: waar in de '
                         'bekostiging het zijn werk doet.</p>' % "".join(regels))

        return ('<section class="blok" id="effect" aria-labelledby="effect-kop">'
                '<div class="blok__kop"><h2 id="effect-kop">Wat doet het met je businesscase?</h2></div>'
                '<p class="blok__uitleg">Niet wat het instrument ís, maar wat het met je '
                'cijfers doet: verlaagt het de investering, verschuift het lasten, of geeft '
                'het alleen inzicht?</p>'
                '<div class="card"><div class="card__body">%s%s</div></div>'
                "</section>" % (inhoud, routehtml))

    # -- blok 3: voorwaarden en uitsluitingen -----------------------
    def blok_voorwaarden(self):
        vw = self.m.bij("instrument_voorwaarde", "instrument_id", self.code)
        hard = [v for v in vw if v.get("is_harde_voorwaarde") == "ja" and v.get("is_uitsluiting") != "ja"]
        zacht = [v for v in vw if v.get("is_harde_voorwaarde") != "ja" and v.get("is_uitsluiting") != "ja"]
        uit = [v for v in vw if v.get("is_uitsluiting") == "ja"]

        def regel(v, soort):
            ico = {"hard": "i-lock", "zacht": "i-check", "uitsluiting": "i-alert"}[soort]
            return ('<div class="vw__regel vw__regel--%s">'
                    '<span class="vw__teken">%s</span>'
                    '<div><span class="vw__type">%s</span> '
                    '<span class="muted">%s</span> <span class="vw__waarde">%s</span></div></div>'
                    % (soort, icon(ico, 15, 1.9),
                       esc(self.m.naam("voorwaardetype", v.get("voorwaardetype_id"))),
                       esc(v.get("operator", "")),
                       esc(v["waarde_tekst"]) if v.get("waarde_tekst")
                       else '<span class="muted">— waarde nog niet vastgelegd</span>'))

        delen = []
        if hard:
            delen.append('<span class="label">Harde voorwaarden – hier valt niet aan te '
                         'ontkomen</span><div class="vw">%s</div>'
                         % "".join(regel(v, "hard") for v in hard))
        if zacht:
            delen.append('<span class="label" style="margin-top:14px">Overige voorwaarden'
                         '</span><div class="vw">%s</div>'
                         % "".join(regel(v, "zacht") for v in zacht))
        if uit:
            delen.append('<span class="label" style="margin-top:14px">Let op: hier geldt het '
                         'níet</span><div class="vw">%s</div>'
                         % "".join(regel(v, "uitsluiting") for v in uit))
        if not delen:
            delen.append(self.leeg(
                "Voor dit instrument zijn nog geen voorwaarden in het model vastgelegd. "
                "Dat geldt in v0.1 voor %d van de %d instrumenten; de bron is voorlopig "
                "de plek om de actuele voorwaarden te lezen."
                % (self.b.zonder_voorwaarden, self.b.aantal_instrumenten)))

        return ('<section class="blok" id="voorwaarden" aria-labelledby="vw-kop">'
                '<div class="blok__kop"><h2 id="vw-kop">Voorwaarden en uitsluitingen</h2></div>'
                '<div class="card"><div class="card__body">%s</div></div>'
                "</section>" % "".join(delen))

    # -- blok 4: zo gebruik je het ----------------------------------
    def blok_gebruik(self):
        i = self.i
        stappen = [
            ("Waarvoor", i.get("doel")),
            ("Wat je aanlevert", i.get("benodigde_input")),
            ("Wat het oplevert", i.get("beoogde_output")),
        ]
        if not any(w for _, w in stappen):
            kern = self.leeg("Het gebruik van dit instrument is nog niet uitgewerkt in het model.")
        else:
            cellen = []
            for n, (label, waarde) in enumerate(stappen):
                if n:
                    cellen.append('<div class="flow__pijl">%s</div>' % icon("i-arrow-right", 18, 2))
                cellen.append('<div class="flow__stap"><span class="label">%s</span><p>%s</p></div>'
                              % (esc(label), esc(waarde or "niet vastgelegd")))
            kern = '<div class="flow">%s</div>' % "".join(cellen)

        noot = ('<p class="bron-noot" style="margin-top:14px">%s<span>%s</span></p>'
                % (icon("i-bulb", 15), esc(i["gebruikstoelichting"]))
                if i.get("gebruikstoelichting") else "")

        dv = self.m.naam("digitale_vorm", i.get("digitale_vorm_id")) if i.get("digitale_vorm_id") else None
        feiten = [
            ("Complexiteit", i.get("complexiteitsniveau")),
            ("Doorlooptijd", i.get("doorlooptijd_categorie")),
            ("Digitale vorm", dv),
            ("Zelfstandig te gebruiken", i.get("zelfstandig_bruikbaar")),
        ]
        feitenhtml = ('<hr class="divider"><dl class="deflist">%s</dl>'
                      % "".join('<div><dt>%s</dt><dd>%s</dd></div>' % (esc(k), esc(v))
                                for k, v in feiten if v))

        return ('<section class="blok" id="gebruik" aria-labelledby="gebruik-kop">'
                '<div class="blok__kop"><h2 id="gebruik-kop">Zo gebruik je het</h2></div>'
                '<div class="card"><div class="card__body">%s%s%s</div></div>'
                "</section>" % (kern, noot, feitenhtml))

    # -- blok 5: waar in het proces ---------------------------------
    def blok_proces(self):
        eigen = {r["procesfase_id"]: r for r in
                 self.m.bij("instrument_procesfase", "instrument_id", self.code)}
        cellen = []
        for f in self.b.fasen:
            code = f["fase_code"]
            r = eigen.get(code)
            klassen = "fasestrip__cel"
            if r:
                klassen += " is-actief"
                if r.get("is_primary") == "ja":
                    klassen += " is-primair"
            cellen.append(
                '<a class="%s" href="%s" title="%s">'
                '<span class="fasestrip__code">%s</span>'
                '<span class="fasestrip__naam">%s</span></a>'
                % (klassen, esc(self.filterlink("fase", code)),
                   esc("%s · %s — %s" % (code, f.get("naam", ""),
                                         "dit instrument hoort hier" if r
                                         else "geen rol voor dit instrument")),
                   esc(code), esc(f.get("naam", ""))))

        legenda = ('<div class="fasestrip__legenda">'
                   '<span>Gekleurd: hier speelt dit instrument een rol.</span>'
                   '<span>Paarse rand: de primaire fase.</span>'
                   '<span>P1–P5 is portefeuille, O1–O7 is één object.</span></div>')

        momenten = self.m.bij("instrument_beslismoment", "instrument_id", self.code)
        if momenten:
            items = []
            for r in momenten:
                bm = self.m.rec("beslismoment", r["beslismoment_id"]) or {}
                meta = " · ".join(x for x in [
                    r.get("ondersteuningsfunctie"),
                    ("te gebruiken %s het besluit" % r["gebruik_voor_of_na_besluit"])
                    if r.get("gebruik_voor_of_na_besluit") else None,
                    bm.get("formaliteitsniveau"),
                ] if x)
                items.append(
                    '<li><a class="linklist__btn" href="../beslismoment/%s.html">%s'
                    '<span class="linklist__meta">%s</span>'
                    '<span class="arrow">%s</span></a></li>'
                    % (slug(r["beslismoment_id"]), esc(bm.get("naam", r["beslismoment_id"])),
                       esc(meta), icon("i-arrow-right", 16, 1.8)))
            momenthtml = ('<hr class="divider"><span class="label">Bij welk besluit het op '
                          'tafel komt</span><ul class="linklist">%s</ul>' % "".join(items))
        else:
            momenthtml = ('<hr class="divider">'
                          + self.leeg("Er is nog geen beslismoment aan dit instrument gekoppeld."))

        return ('<section class="blok" id="proces" aria-labelledby="proces-kop">'
                '<div class="blok__kop"><h2 id="proces-kop">Waar in het proces</h2></div>'
                '<p class="blok__uitleg">De twaalf fasen van het model staan er altijd alle '
                'twaalf. Dat één cel oplicht is het punt: dit instrument hoort op één plek '
                'in de cyclus, niet overal.</p>'
                '<div class="card"><div class="card__body">'
                '<div class="fasestrip">%s</div>%s%s</div></div>'
                "</section>" % ("".join(cellen), legenda, momenthtml))

    # -- blok 6: wie gebruikt het en hoe ----------------------------
    def blok_rollen(self):
        rollen = self.m.bij("instrument_rol", "instrument_id", self.code)
        if not rollen:
            inhoud = self.leeg("Er zijn nog geen rollen aan dit instrument gekoppeld.")
        else:
            per_cluster = {}
            for r in rollen:
                rol = self.m.rec("rol", r["rol_id"]) or {}
                per_cluster.setdefault(rol.get("rolcluster_id", "RC-00"), []).append((r, rol))
            delen = []
            for cl in sorted(per_cluster, key=lambda c: (self.m.rec("rolcluster", c) or {}).get("sort_order", 99)):
                clusternaam = self.m.naam("rolcluster", cl)
                delen.append('<div class="rolgroep"><p class="rolgroep__kop">'
                             '<span class="rolgroep__spoor" style="background:%s"></span>%s</p>'
                             % (esc(self.b.clusterkleur(cl)), esc(clusternaam)))
                for r, rol in per_cluster[cl]:
                    sub = " · ".join(x for x in [
                        r.get("rol_bij_gebruik"),
                        rol.get("informatie_detailniveau") and
                        ("informatie op %s niveau" % rol["informatie_detailniveau"]),
                        "primaire gebruiker in v1" if rol.get("primaire_gebruiker_v1") == "ja" else None,
                        "externe partij" if rol.get("externe_rol") == "ja" else None,
                    ] if x)
                    delen.append(
                        '<a class="rolkaart" href="%s" data-ctx="rol:%s">'
                        '<span><span class="rolkaart__naam">%s</span>'
                        '<span class="rolkaart__sub">%s</span></span>'
                        '<span class="arrow" style="color:var(--vmv-grey-400)">%s</span></a>'
                        % (esc(self.filterlink("rol", r["rol_id"])), esc(r["rol_id"]),
                           esc(rol.get("naam", r["rol_id"])), esc(sub),
                           icon("i-arrow-right", 16, 1.8)))
                delen.append("</div>")
            inhoud = "".join(delen)

        return ('<section class="blok" id="rollen" aria-labelledby="rollen-kop">'
                '<div class="blok__kop"><h2 id="rollen-kop">Wie gebruikt het, en hoe</h2></div>'
                '<p class="blok__uitleg">Hierboven stond óf je rol past. Hier staat wat je '
                'rol dan is: gebruiker, adviseur of beslisser — en op welk detailniveau je '
                'de informatie nodig hebt.</p>'
                '<div class="card"><div class="card__body">%s</div></div>'
                "</section>" % inhoud)

    # -- blok 7: financiële vragen ----------------------------------
    def blok_vragen(self):
        vragen = self.m.bij("instrument_financiele_vraag", "instrument_id", self.code)
        if not vragen:
            inhoud = self.leeg("Er is nog geen financiële vraag aan dit instrument gekoppeld.")
        else:
            per_thema = {}
            for r in vragen:
                v = self.m.rec("financiele_vraag", r["financiele_vraag_id"]) or {}
                per_thema.setdefault(v.get("financieel_thema_id", "TH-00"), []).append((r, v))
            delen = []
            for th in sorted(per_thema, key=lambda t: (self.m.rec("financieel_thema", t) or {}).get("sort_order", 99)):
                delen.append('<p class="effect__categorie">%s</p>' % esc(self.m.naam("financieel_thema", th)))
                items = []
                for r, v in per_thema[th]:
                    items.append(
                        '<li><a class="linklist__btn" href="../vraag/%s.html">%s'
                        '<span class="linklist__meta">%s</span>'
                        '<span class="arrow">%s</span></a></li>'
                        % (slug(r["financiele_vraag_id"]),
                           esc(v.get("vraagtekst", r["financiele_vraag_id"])),
                           esc(" · ".join(x for x in [r.get("antwoordniveau"),
                                                      r.get("relevantie") and
                                                      "relevantie %s" % r["relevantie"]] if x)),
                           icon("i-arrow-right", 16, 1.8)))
                delen.append('<ul class="linklist">%s</ul>' % "".join(items))
            inhoud = "".join(delen)

        return ('<section class="blok" id="vragen" aria-labelledby="vragen-kop">'
                '<div class="blok__kop"><h2 id="vragen-kop">Welke financiële vragen het '
                'beantwoordt</h2></div>'
                '<p class="blok__uitleg">En hoe diep: indicatief inzicht is genoeg om een '
                'richting te kiezen, een specialistische onderbouwing heb je nodig voor een '
                'investeringsbesluit.</p>'
                '<div class="card"><div class="card__body">%s</div></div>'
                "</section>" % inhoud)

    # -- blok 8: verwante instrumenten ------------------------------
    def blok_verwant(self):
        delen = []
        vast = self.b.relaties.get(self.code, [])
        if vast:
            items = []
            for ander, rtype, sterkte, gevalideerd, toel in vast:
                meta = " · ".join(x for x in [
                    rtype, sterkte and "verband %s" % sterkte,
                    "nog niet gevalideerd" if gevalideerd != "ja" else None] if x)
                items.append(
                    '<li><a class="linklist__btn" href="%s.html">%s'
                    '<span class="linklist__meta">%s</span>'
                    '<span class="arrow">%s</span></a></li>'
                    % (slug(ander), esc(self.m.naam("instrument", ander)), esc(meta),
                       icon("i-arrow-right", 16, 1.8)))
            delen.append('<span class="label">Vastgelegd in het model</span>'
                         '<ul class="linklist">%s</ul>' % "".join(items))
        else:
            delen.append(self.leeg(
                "Voor dit instrument is nog geen relatie met een ander instrument vastgelegd. "
                "Dat geldt in v0.1 voor %d van de %d instrumenten."
                % (self.b.zonder_relatie, self.b.aantal_instrumenten)))

        berekend = self.b.verwant_berekend(self.code)
        if berekend:
            items = []
            for ander, overeenkomsten in berekend:
                items.append(
                    '<li><a class="linklist__btn" href="%s.html">%s'
                    '<span class="linklist__meta">deelt %s</span>'
                    '<span class="arrow">%s</span></a></li>'
                    % (slug(ander), esc(self.m.naam("instrument", ander)),
                       esc(" en ".join(overeenkomsten)), icon("i-arrow-right", 16, 1.8)))
            delen.append('<hr class="divider">'
                         '<span class="label">Vaak in hetzelfde gesprek — berekend, niet '
                         'vastgelegd</span><ul class="linklist">%s</ul>'
                         '<p class="tiny muted" style="margin-top:8px">Deze lijst is '
                         'afgeleid uit gedeelde kenmerken, niet uit een inhoudelijk oordeel. '
                         'Het model legt er nog maar %d expliciet vast.</p>'
                         % ("".join(items), self.b.aantal_relaties))

        return ('<section class="blok" id="verwant" aria-labelledby="verwant-kop">'
                '<div class="blok__kop"><h2 id="verwant-kop">Verwante instrumenten</h2></div>'
                '<div class="card"><div class="card__body">%s</div></div>'
                "</section>" % "".join(delen))

    # -- blok 9: herkomst en actualiteit ----------------------------
    def blok_herkomst(self):
        i = self.i
        bronnen = self.m.bij("instrument_bron", "instrument_id", self.code)
        beheer = self.m.bij("instrument_organisatie", "instrument_id", self.code)

        bronhtml = ""
        if bronnen:
            regels = []
            for b in bronnen:
                br = self.m.rec("bron", b["bron_id"]) or {}
                meta = " · ".join(x for x in [
                    self.m.naam("brontype", br.get("brontype_id")) if br.get("brontype_id") else None,
                    br.get("bronstatus"),
                    "juridisch bindend" if br.get("juridisch_bindend") == "ja" else None,
                    "geraadpleegd %s" % datum_nl(br["geraadpleegd_op"]) if br.get("geraadpleegd_op") else None,
                ] if x)
                regels.append('<div><dt>%s</dt><dd class="printbron">%s<br>'
                              '<span class="tiny muted">%s</span></dd></div>'
                              % ("Bron" if b.get("is_primary") == "ja" else "Ook",
                                 self.b.bronlink(b["bron_id"]), esc(meta)))
            bronhtml = '<dl class="deflist">%s</dl>' % "".join(regels)
        else:
            bronhtml = self.leeg("Er is geen bron vastgelegd.")

        feiten = []
        if beheer:
            feiten.append(("Beheer", ", ".join(
                "%s (%s)" % (b["organisatie_id"], b.get("relatierol", "betrokken")) for b in beheer)))
        if i.get("inhoudelijke_status_id"):
            feiten.append(("Inhoudelijke status", self.m.naam("inhoudelijke_status", i["inhoudelijke_status_id"])))
        if i.get("publicatiestatus_id"):
            feiten.append(("Publicatiestatus", self.m.naam("publicatiestatus", i["publicatiestatus_id"])))
        if i.get("relevantie_v1"):
            feiten.append(("Relevantie voor v1", i["relevantie_v1"]))
        os_rec = self.m.bij("openstelling", "instrument_id", self.code)
        if os_rec and os_rec[0].get("laatst_gecontroleerd_op"):
            feiten.append(("Laatst gecontroleerd", datum_nl(os_rec[0]["laatst_gecontroleerd_op"])))
        feitenhtml = ('<hr class="divider"><dl class="deflist">%s</dl>'
                      % "".join('<div><dt>%s</dt><dd>%s</dd></div>' % (esc(k), esc(v))
                                for k, v in feiten)) if feiten else ""

        return ('<section class="blok" id="herkomst" aria-labelledby="herkomst-kop">'
                '<div class="blok__kop"><h2 id="herkomst-kop">Herkomst en actualiteit</h2></div>'
                '<div class="card"><div class="card__body">%s%s'
                '<div class="bron-noot" style="margin-top:16px">%s<span>%s</span></div>'
                "</div></div></section>"
                % (bronhtml, feitenhtml, icon("i-info", 15), esc(HERKOMSTTEKST)))

    # -- blok 10: feedback ------------------------------------------
    def blok_feedback(self):
        return ('<section class="blok" aria-labelledby="fb-kop">'
                '<div class="feedback">'
                '<p class="feedback__vraag" id="fb-kop">Klopt deze pagina nog, en vond je '
                'wat je zocht?</p>'
                '<div class="feedback__keuzes" id="feedback-keuzes">'
                '<button type="button" class="btn btn--small" data-feedback="gevonden">%s Ja, dit zocht ik</button>'
                '<button type="button" class="btn btn--small" data-feedback="deels">Deels</button>'
                '<button type="button" class="btn btn--small" data-feedback="verouderd">%s Informatie is verouderd</button>'
                '<button type="button" class="btn btn--small" data-feedback="onvindbaar">Ik zocht iets anders</button>'
                "</div>"
                '<p class="small muted" style="margin-top:12px" id="feedback-dank" hidden></p>'
                '<p class="tiny muted" style="margin-top:10px">In dit prototype blijft je '
                'antwoord in je eigen browser. Het datamodel heeft er een tabel voor '
                '(gebruikersfeedback, met bruikbaarheidsscore en of je vond wat je zocht); '
                'een echte site stuurt het daarheen.</p>'
                "</div></section>"
                % (icon("i-check", 15, 2.2), icon("i-alert", 15, 1.9)))

    # -- hero -------------------------------------------------------
    def status_chip(self):
        os_rec = self.m.bij("openstelling", "instrument_id", self.code)
        if not os_rec:
            return "", None
        o = os_rec[0]
        st = o.get("openstelling_status", "onbekend")
        tekst = st
        if st in ("open", "verwacht") and o.get("einddatum"):
            tekst = "%s t/m %s" % (st, datum_nl(o["einddatum"]))
        elif st == "gesloten" and o.get("einddatum"):
            tekst = "gesloten sinds %s" % datum_nl(o["einddatum"])
        elif o.get("einddatum"):
            # Status onbekend, maar er staat wel een ronde in het model.
            tekst = "%s · ronde t/m %s" % (st, datum_nl(o["einddatum"]))
        soort = STATUSKLEUR.get(st, "")
        return ('<span class="chip%s">%s %s</span>'
                % (" chip--" + soort if soort else "",
                   icon("i-clock", 13, 2), esc(tekst))), o

    def hero(self):
        i = self.i
        ty = self.m.rec("instrumenttype", i.get("primaire_instrumenttype_id")) or {}
        statushtml, _ = self.status_chip()

        eyebrow = [esc(self.code)]
        if ty.get("naam"):
            eyebrow.append('<a href="%s">%s</a>'
                           % (esc(self.filterlink("type", ty["code"])), esc(ty["naam"])))
        if ty.get("hoofdgroep"):
            eyebrow.append(esc(ty["hoofdgroep"]))

        chips = [statushtml]
        if i.get("complexiteitsniveau"):
            chips.append(chip("complexiteit: " + i["complexiteitsniveau"]))
        if i.get("doorlooptijd_categorie"):
            chips.append(chip("doorlooptijd: " + i["doorlooptijd_categorie"]))
        if i.get("zelfstandig_bruikbaar") == "ja":
            chips.append(chip("zelfstandig bruikbaar", "success"))
        elif i.get("zelfstandig_bruikbaar") == "nee":
            chips.append(chip("hoort bij een ander instrument", "warning"))
        geb = self.m.bij("instrument_werkingsgebied", "instrument_id", self.code)
        for g in geb[:2]:
            chips.append(chip(g["werkingsgebied_id"]))

        url = self.b.bronurl(self.code)
        acties = []
        if url:
            acties.append('<a class="btn btn--teal" href="%s" target="_blank" rel="noopener">'
                          "%s Naar de bron</a>" % (esc(url), icon("i-external", 15, 1.9)))
        acties.append('<button type="button" class="btn" data-selectie="%s" '
                      'data-selectienaam="%s" aria-pressed="false">%s '
                      '<span class="selectie-label">Zet in mijn selectie</span></button>'
                      % (esc(self.code), esc(i.get("naam_officieel") or self.code),
                         icon("i-bookmark", 15, 1.9)))
        acties.append('<button type="button" class="btn" data-action="print">%s Printen</button>'
                      % icon("i-printer", 15, 1.8))

        naam = i.get("naam_officieel") or i.get("naam_kort") or self.code
        kort = i.get("naam_kort")
        titel = esc(naam)
        if kort and kort != naam:
            titel += ' <span class="muted" style="font-size:.6em;font-weight:400">%s</span>' % esc(kort)

        return ('<div class="hero"><div class="hero__inner">'
                '<p class="hero__eyebrow">%s</p>'
                '<h1 class="hero__titel">%s</h1>'
                "%s"
                '<p class="hero__lead">%s</p>'
                '<div class="hero__status">%s</div>'
                '<div class="hero__acties">%s</div>'
                "</div></div>"
                % ('<span class="kruimel__scheiding">·</span>'.join(eyebrow),
                   titel,
                   '<p class="hero__belofte">%s</p>' % esc(i["centrale_gebruikersvraag"])
                   if i.get("centrale_gebruikersvraag") else "",
                   esc(i.get("korte_omschrijving", "")),
                   "".join(c for c in chips if c),
                   "".join(acties)))

    # -- zijkolom ---------------------------------------------------
    def zijkolom(self):
        i = self.i
        ty = self.m.rec("instrumenttype", i.get("primaire_instrumenttype_id")) or {}
        beheer = self.m.bij("instrument_organisatie", "instrument_id", self.code)
        _, os_rec = self.status_chip()

        feiten = [
            ("Type", ty.get("naam")),
            ("Hoofdgroep", ty.get("hoofdgroep")),
            ("Beheerder", ", ".join(b["organisatie_id"] for b in beheer) or None),
            ("Vorm", self.m.naam("digitale_vorm", i["digitale_vorm_id"]) if i.get("digitale_vorm_id") else None),
            ("Complexiteit", i.get("complexiteitsniveau")),
            ("Doorlooptijd", i.get("doorlooptijd_categorie")),
            ("Status", (os_rec or {}).get("openstelling_status")),
            ("Gecontroleerd", datum_nl((os_rec or {}).get("laatst_gecontroleerd_op"))
             if (os_rec or {}).get("laatst_gecontroleerd_op") else None),
        ]
        kaarten = ['<section class="card" aria-labelledby="oog-kop">'
                   '<div class="card__head"><h2 id="oog-kop">In één oogopslag</h2></div>'
                   '<div class="card__body"><dl class="deflist">%s</dl></div></section>'
                   % "".join('<div><dt>%s</dt><dd>%s</dd></div>' % (esc(k), esc(v))
                             for k, v in feiten if v)]

        # Openstelling met data, als het model die heeft
        if os_rec and (os_rec.get("startdatum") or os_rec.get("toelichting")):
            regels = []
            if os_rec.get("startdatum") or os_rec.get("einddatum"):
                regels.append('<div><dt>Periode</dt><dd>%s t/m %s</dd></div>'
                              % (esc(datum_nl(os_rec.get("startdatum")) or "onbekend"),
                                 esc(datum_nl(os_rec.get("einddatum")) or "onbekend")))
            if os_rec.get("toelichting"):
                regels.append('<div><dt>Toelichting</dt><dd>%s</dd></div>'
                              % esc(os_rec["toelichting"]))
            kaarten.append('<section class="card" aria-labelledby="open-kop">'
                           '<div class="card__head">%s<h2 id="open-kop">Kan je er nu bij?</h2></div>'
                           '<div class="card__body"><dl class="deflist">%s</dl></div></section>'
                           % (icon("i-calendar", 16, 1.8), "".join(regels)))

        # Volgende stap: het beslismoment dat dit instrument primair steunt
        momenten = self.m.bij("instrument_beslismoment", "instrument_id", self.code)
        primair = next((r for r in momenten if r.get("is_primary") == "ja"), momenten[0] if momenten else None)
        if primair:
            bm = self.m.rec("beslismoment", primair["beslismoment_id"]) or {}
            kaarten.append(
                '<section class="card" aria-labelledby="stap-kop">'
                '<div class="card__head">%s<h2 id="stap-kop">Volgende stap</h2></div>'
                '<div class="card__body">'
                '<p class="small" style="margin-bottom:10px">Dit instrument komt op tafel bij '
                '<strong>%s</strong>.</p>%s'
                '<a class="btn btn--block btn--primary" href="../beslismoment/%s.html">'
                "Naar dat beslismoment %s</a></div></section>"
                % (icon("i-flag", 16, 1.8), esc(bm.get("naam", "")),
                   '<p class="small muted" style="margin-bottom:10px">Daarna: %s</p>'
                   % esc(bm["volgende_stap"]) if bm.get("volgende_stap") else "",
                   slug(primair["beslismoment_id"]), icon("i-arrow-right", 15, 1.9)))

        # Kennisproducten
        kps = [r for r in self.m.tab("kennisproduct_instrument") if r.get("instrument_id") == self.code]
        if kps:
            items = []
            for r in kps:
                kp = self.m.rec("kennisproduct", r["kennisproduct_id"]) or {}
                items.append('<li><strong>%s</strong><br><span class="tiny muted">%s</span></li>'
                             % (esc(kp.get("naam", r["kennisproduct_id"])),
                                esc(" · ".join(x for x in [r.get("relatietype"),
                                                           kp.get("producttype"),
                                                           kp.get("status")] if x))))
            kaarten.append('<section class="card" aria-labelledby="kp-kop">'
                           '<div class="card__head">%s<h2 id="kp-kop">Meer lezen</h2></div>'
                           '<div class="card__body"><ul class="small" style="display:grid;gap:9px">%s</ul>'
                           '<p class="tiny muted" style="margin-top:10px">Kennisproducten uit het '
                           "VMV-programma. In v0.1 zijn dit dummy-titels.</p></div></section>"
                           % (icon("i-book", 16, 1.8), "".join(items)))

        return '<aside class="zijkolom">%s</aside>' % "".join(kaarten)

    # -- de hele pagina ---------------------------------------------
    def bouw(self):
        i = self.i
        ty = self.m.rec("instrumenttype", i.get("primaire_instrumenttype_id")) or {}
        naam = i.get("naam_officieel") or i.get("naam_kort") or self.code

        hoofd = ('<div class="paginalayout"><div>%s%s%s%s%s%s%s%s%s%s</div>%s</div>'
                 % (self.blok_past(), self.blok_effect(), self.blok_voorwaarden(),
                    self.blok_gebruik(), self.blok_proces(), self.blok_rollen(),
                    self.blok_vragen(), self.blok_verwant(), self.blok_herkomst(),
                    self.blok_feedback(), self.zijkolom()))

        beschrijving = (i.get("korte_omschrijving") or "")[:180]
        self.b.pagina(
            "instrument/%s.html" % slug(self.code),
            naam,
            beschrijving,
            hoofd,
            nav="instrumenten",
            kruimels=[("Instrumenten", "instrumenten.html"),
                      (ty.get("hoofdgroep") or "Instrument", None),
                      (naam, None)],
            subnav=self.SUBNAV,
            hero=self.hero(),
            contextstrip=True,
            scripts=["assets/instrument.js"],
            bodyattr=' data-instrument="%s"' % esc(self.code),
        )


# ====================================================================
# Gedeelde data-assets
# ====================================================================
def bouw_namen_js(bouwer):
    """Instrumentnamen voor het selectievenster, op elke pagina nodig."""
    namen = {i["instrument_code"]: (i.get("naam_officieel") or i.get("naam_kort") or i["instrument_code"])
             for i in bouwer.m.tab("instrument")}
    return js_globaal("KOMPAS_NAMEN", namen)


def bouw_index_js(bouwer):
    """Alles wat instrumenten.html nodig heeft om te filteren en zoeken.

    Niet het hele model: de detailpagina's hebben hun inhoud al ingebakken,
    dus deze bundel bevat alleen de filterkenmerken en de zoekvelden.
    """
    m = bouwer.m

    instrumenten = []
    for i in m.sorteer(m.tab("instrument")):
        code = i["instrument_code"]
        kn = bouwer.kenmerk[code]
        ty = m.rec("instrumenttype", i.get("primaire_instrumenttype_id")) or {}
        hooi = " ".join(str(x) for x in [
            i.get("naam_officieel"), i.get("naam_kort"), i.get("korte_omschrijving"),
            i.get("centrale_gebruikersvraag"), i.get("doel"), i.get("beoogde_output"),
            ty.get("naam"), ty.get("hoofdgroep"),
        ] if x).lower()
        instrumenten.append({
            "code": code,
            "naam": i.get("naam_officieel") or i.get("naam_kort") or code,
            "kort": i.get("naam_kort") or "",
            "omschrijving": i.get("korte_omschrijving") or "",
            "vraag": i.get("centrale_gebruikersvraag") or "",
            "type": ty.get("naam") or "",
            "hoofdgroep": ty.get("hoofdgroep") or "",
            "status": (kn["openstelling"] or [""])[0],
            "complexiteit": i.get("complexiteitsniveau") or "",
            "doorlooptijd": i.get("doorlooptijd_categorie") or "",
            "v1": i.get("tonen_in_v1") or "",
            "relevantie": i.get("relevantie_v1") or "",
            "hooi": hooi,
            "kn": {k: v for k, v in kn.items() if v},
        })

    # Filtergroepen, met dezelfde id's als de querystring gebruikt.
    def uit(tabel, labelveld):
        sl = K.SLEUTEL[tabel]
        return [{"code": str(r[sl]), "label": r.get(labelveld) or str(r[sl])}
                for r in m.sorteer(m.tab(tabel))]

    rollen = []
    for c in m.sorteer(m.tab("rolcluster")):
        for r in m.tab("rol"):
            if r.get("rolcluster_id") == c["code"]:
                rollen.append({"code": r["rol_code"], "label": r.get("naam", r["rol_code"]),
                               "sub": c.get("naam", "")})

    fasen = [{"code": f["fase_code"], "label": "%s · %s" % (f["fase_code"], f.get("naam", "")),
              "sub": m.naam("procesniveau", f.get("procesniveau_id"))}
             for f in bouwer.fasen]

    typen = []
    for hg in ["Financiële regeling", "Financiële en organisatorische constructie",
               "Analyse en besluitvorming", "Ondersteunend product"]:
        for ty in m.sorteer(m.tab("instrumenttype")):
            if ty.get("hoofdgroep") == hg:
                typen.append({"code": ty["code"], "label": ty.get("naam", ty["code"]), "sub": hg})

    objecten = []

    def objloop(ouder, diepte):
        for o in m.sorteer(m.tab("objecttype")):
            if (o.get("parent_objecttype_id") or None) == ouder:
                objecten.append({"code": o["objecttype_code"], "label": o.get("naam", ""),
                                 "diepte": diepte})
                objloop(o["objecttype_code"], diepte + 1)
    objloop(None, 0)

    momenten = [{"code": b["beslismoment_code"], "label": b.get("naam", ""),
                 "sub": m.naam("procesfase", b.get("procesfase_id"))}
                for b in m.tab("beslismoment")]

    groepen = [
        {"id": "rol", "titel": "Rol", "open": True, "opties": rollen},
        {"id": "fase", "titel": "Procesfase", "open": True, "opties": fasen},
        {"id": "opgave", "titel": "Opgave", "open": True, "opties": uit("opgave", "naam")},
        {"id": "type", "titel": "Type instrument", "open": True, "opties": typen},
        {"id": "moment", "titel": "Beslismoment", "open": False, "opties": momenten},
        {"id": "vraag", "titel": "Financiële vraag", "open": False,
         "opties": [{"code": v["vraag_code"], "label": v.get("korte_naam") or v.get("vraagtekst", "")}
                    for v in m.sorteer(m.tab("financiele_vraag"))]},
        {"id": "objecttype", "titel": "Objecttype", "open": False, "opties": objecten},
        {"id": "eigenaar", "titel": "Eigenaartype", "open": False, "opties": uit("eigenaartype", "naam")},
        {"id": "route", "titel": "Financiële route", "open": False, "opties": uit("financiele_route", "naam")},
        {"id": "gebied", "titel": "Werkingsgebied", "open": False, "opties": uit("werkingsgebied", "naam")},
        {"id": "openstelling", "titel": "Openstelling", "open": False,
         "opties": [{"code": s, "label": s} for s in
                    ["open", "doorlopend", "verwacht", "gesloten", "onbekend"]]},
        {"id": "complexiteit", "titel": "Complexiteit", "open": False,
         "opties": [{"code": s, "label": s} for s in ["basis", "gemiddeld", "specialistisch"]]},
        {"id": "doorlooptijd", "titel": "Doorlooptijd", "open": False,
         "opties": [{"code": s, "label": s} for s in ["direct", "dagen", "weken", "maanden"]]},
    ]

    # Functietitels uit de praktijk, zodat iemand op zijn eigen titel zijn rol vindt.
    aliassen = [{"titel": a["functietitel"], "rol": a["rol_id"],
                 "rolnaam": m.naam("rol", a["rol_id"])}
                for a in m.tab("functie_alias") if a.get("functietitel")]

    themas = []
    for t in m.sorteer(m.tab("financieel_thema")):
        vragen = [v for v in m.tab("financiele_vraag")
                  if v.get("financieel_thema_id") == t["thema_code"]]
        if vragen:
            themas.append({"code": t["thema_code"], "label": t.get("naam", ""),
                           "vragen": [v["vraag_code"] for v in vragen]})

    beheerders = {}
    for r in m.tab("instrument_organisatie"):
        if r.get("relatierol") == "beheerder":
            beheerders.setdefault(r["organisatie_id"], []).append(r["instrument_id"])

    return js_globaal("KOMPAS_INDEX", {
        "instrumenten": instrumenten,
        "groepen": groepen,
        "aliassen": aliassen,
        "themas": themas,
        "beheerders": beheerders,
    })


def bouw_model_js(bouwer):
    """De navigatietabellen die de routeplanner en de adviseur nodig hebben."""
    m = bouwer.m
    nodig = [
        "procesniveau", "procesfase", "beslismoment", "besluittype",
        "rol", "rolcluster", "opgave", "objecttype", "eigenaartype",
        "financiele_vraag", "financieel_thema", "informatiebehoefte",
        "handelingsperspectief", "knelpunt", "beslisproduct",
        "beslismoment_rol", "beslismoment_informatiebehoefte",
        "beslismoment_financiele_vraag", "beslismoment_beslisproduct",
        "beslismoment_handelingsperspectief", "beslismoment_knelpunt",
        "informatieoverdracht", "instrument", "instrumenttype",
        "instrument_rol", "instrument_procesfase", "instrument_beslismoment",
        "instrument_opgave", "instrument_objecttype", "instrument_eigenaartype",
        "pc_moment",
    ]
    return js_globaal("KOMPAS_MODEL", {t: m.tab(t) for t in nodig})


# ====================================================================
# Instrumentenbibliotheek (de index)
# ====================================================================
def bouw_instrumenten_index(b):
    m = b.m
    totaal = len(m.tab("instrument"))
    v1 = len([i for i in m.tab("instrument") if i.get("tonen_in_v1") != "nee"])

    hoofd = """
<div class="viewhead">
  <div class="viewhead__row">
    <div>
      <span class="viewhead__eyebrow">Instrumentenbibliotheek</span>
      <h1 class="viewhead__title">Welk instrument helpt je verder?</h1>
      <p class="viewhead__sub">%(v1)d instrumenten uit catalogus v0.1, te filteren op je
        opgave, je rol, je fase en het besluit dat voorligt. Filter je iets weg, dan zie je
        dat meteen in de aantallen: zo wordt ook zichtbaar waar het model nog leeg is.</p>
    </div>
  </div>
</div>

<div class="layout layout--3">
  <section class="card" aria-labelledby="b-filters-titel">
    <div class="card__head">%(icoon_filter)s<h2 id="b-filters-titel">Filters</h2>
      <button type="button" class="btn btn--ghost btn--small" data-wis="1" style="margin-left:auto">Wis alles</button>
    </div>
    <div class="card__body" style="padding:6px 10px 10px" id="b-filters"></div>
  </section>

  <div class="stack">
    <div class="searchbar">
      <div class="searchbar__field">
        <label class="visually-hidden" for="b-zoek">Zoek in de instrumenten</label>
        <input type="search" id="b-zoek" placeholder="Zoek op naam, doel of vraag…">
      </div>
      <button type="button" class="btn btn--primary" id="b-zoek-knop">%(icoon_zoek)s Zoek</button>
    </div>
    <div id="b-aliasnoot"></div>
    <div class="filterchips" id="b-chips"></div>
    <div class="results-head">
      <strong id="b-telling" aria-live="polite">—</strong>
      <label class="check" style="margin-left:auto">
        <input type="checkbox" id="b-toon-alles">
        <span>Toon ook de %(buiten)d instrumenten die buiten v1 vallen</span>
      </label>
    </div>
    <div class="inst-grid" id="b-resultaten"></div>
  </div>

  <div class="stack">
    <section class="card" aria-labelledby="b-themas-titel">
      <div class="card__head">%(icoon_euro)s<h2 id="b-themas-titel">Financiële thema's</h2></div>
      <div class="card__body">
        <div class="chip-row" id="b-themachips"></div>
        <p class="tiny muted" style="margin-top:10px">De %(themas)d thema's groeperen de
          %(vragen)d financiële vragen uit het model. Het getal is het aantal vragen.</p>
      </div>
    </section>
    <section class="card" aria-labelledby="b-typen-titel">
      <div class="card__head">%(icoon_layers)s<h2 id="b-typen-titel">Verdeling over hoofdgroepen</h2></div>
      <div class="card__body" id="b-verdeling"></div>
    </section>
    <section class="card" aria-labelledby="b-beheer-titel">
      <div class="card__head">%(icoon_users)s<h2 id="b-beheer-titel">Wie beheert wat</h2></div>
      <div class="card__body"><ul class="linklist" id="b-beheerders"></ul></div>
    </section>
  </div>
</div>
""" % {
        "v1": v1,
        "buiten": totaal - v1,
        "themas": len([t for t in m.tab("financieel_thema")
                       if any(v.get("financieel_thema_id") == t["thema_code"]
                              for v in m.tab("financiele_vraag"))]),
        "vragen": len(m.tab("financiele_vraag")),
        "icoon_filter": icon("i-filter", 17, 1.8),
        "icoon_zoek": icon("i-search", 15, 1.9),
        "icoon_euro": icon("i-euro", 17, 1.7),
        "icoon_layers": icon("i-layers", 17, 1.7),
        "icoon_users": icon("i-users", 17, 1.7),
    }

    b.pagina("instrumenten.html", "Instrumenten",
             "Doorzoek %d financiële instrumenten op opgave, rol, fase en beslismoment." % v1,
             hoofd, nav="instrumenten",
             kruimels=[("Instrumenten", None)],
             scripts=["assets/kompas-index.js", "assets/instrumenten.js"])


# ====================================================================
# Beslismomentpagina
# ====================================================================
class Beslismomentpagina:

    SUBNAV = [
        ("besluit", "Het besluit"),
        ("wie", "Wie aan tafel"),
        ("informatie", "Welke informatie"),
        ("vragen", "Financiële vragen"),
        ("overdracht", "Overdracht"),
        ("knelpunten", "Knelpunten"),
        ("handelen", "Wat je kunt doen"),
        ("producten", "Producten"),
        ("instrumenten", "Instrumenten"),
    ]

    def __init__(self, bouwer, code):
        self.b = bouwer
        self.m = bouwer.m
        self.code = code
        self.bm = self.m.rec("beslismoment", code)

    def leeg(self, tekst):
        return '<p class="leeg">%s<span>%s</span></p>' % (icon("i-info", 15), esc(tekst))

    def blok(self, anker, titel, uitleg, inhoud):
        return ('<section class="blok" id="%s" aria-labelledby="%s-kop">'
                '<div class="blok__kop"><h2 id="%s-kop">%s</h2></div>'
                "%s"
                '<div class="card"><div class="card__body">%s</div></div></section>'
                % (anker, anker, anker, esc(titel),
                   '<p class="blok__uitleg">%s</p>' % esc(uitleg) if uitleg else "",
                   inhoud))

    # -- hero -------------------------------------------------------
    def hero(self):
        bm = self.bm
        fase = self.m.rec("procesfase", bm.get("procesfase_id")) or {}
        niveau = self.m.naam("procesniveau", fase.get("procesniveau_id"))

        eyebrow = [esc(self.code),
                   '<a href="../instrumenten.html?fase=%s">%s · %s</a>'
                   % (esc(bm.get("procesfase_id", "")), esc(bm.get("procesfase_id", "")),
                      esc(fase.get("naam", ""))),
                   esc(niveau)]

        chips = []
        if bm.get("besluittype_id"):
            chips.append(chip("besluittype: " + self.m.naam("besluittype", bm["besluittype_id"]), "purple"))
        if bm.get("formaliteitsniveau"):
            chips.append(chip(bm["formaliteitsniveau"],
                              "critical" if bm["formaliteitsniveau"] == "bestuurlijk" else "blue"))
        if bm.get("voorbereidend_of_definitief"):
            chips.append(chip(bm["voorbereidend_of_definitief"]))
        if bm.get("pc_moment_id"):
            pc = self.m.rec("pc_moment", bm["pc_moment_id"]) or {}
            chips.append(chip("P&C: %s (%s)" % (pc.get("naam", ""), pc.get("periodiciteit", "")), "teal"))
        if bm.get("mandaat_lokaal_bepaald") == "ja":
            chips.append(chip("mandaat lokaal bepaald", "warning"))

        return ('<div class="hero"><div class="hero__inner">'
                '<p class="hero__eyebrow">%s</p>'
                '<h1 class="hero__titel">%s</h1>'
                "%s%s"
                '<div class="hero__status">%s</div>'
                '<div class="hero__acties">%s'
                '<button type="button" class="btn" data-action="print">%s Printen</button>'
                "</div></div></div>"
                % ('<span class="kruimel__scheiding">·</span>'.join(eyebrow),
                   esc(bm.get("naam", self.code)),
                   '<p class="hero__belofte">%s</p>' % esc(bm["centrale_vraag"])
                   if bm.get("centrale_vraag") else "",
                   '<p class="hero__lead">%s</p>' % esc(bm["omschrijving"])
                   if bm.get("omschrijving") else "",
                   "".join(chips),
                   '<a class="btn btn--teal" href="../routeplanner.html#%s">%s In de routeplanner</a>'
                   % (esc(self.code), icon("i-map", 15, 1.8)),
                   icon("i-printer", 15, 1.8)))

    # -- blokken ----------------------------------------------------
    def blok_besluit(self):
        bm = self.bm
        stappen = [("Wat gaat erin", bm.get("benodigde_input_samenvatting")),
                   ("Wat wordt besloten", bm.get("verwacht_besluit")),
                   ("Wat komt eruit", bm.get("verwachte_output"))]
        cellen = []
        for n, (label, waarde) in enumerate(stappen):
            if n:
                cellen.append('<div class="flow__pijl">%s</div>' % icon("i-arrow-right", 18, 2))
            cellen.append('<div class="flow__stap"><span class="label">%s</span><p>%s</p></div>'
                          % (esc(label), esc(waarde or "niet vastgelegd")))
        volgende = ('<p class="bron-noot" style="margin-top:14px">%s<span><strong>Daarna:</strong> %s</span></p>'
                    % (icon("i-arrow-right", 15, 2), esc(bm["volgende_stap"]))
                    if bm.get("volgende_stap") else "")
        return self.blok("besluit", "Wat hier besloten wordt", None,
                         '<div class="flow">%s</div>%s' % ("".join(cellen), volgende))

    def blok_wie(self):
        rollen = sorted(self.m.bij("beslismoment_rol", "beslismoment_id", self.code),
                        key=lambda r: int(r.get("volgorde") or 99))
        if not rollen:
            return self.blok("wie", "Wie aan tafel zit", None,
                             self.leeg("Er zijn nog geen rollen aan dit beslismoment gekoppeld."))
        regels = []
        for r in rollen:
            rol = self.m.rec("rol", r["rol_id"]) or {}
            raci = r.get("raci_type", "")
            sub = " · ".join(x for x in [
                r.get("betrokkenheidstype"),
                rol.get("informatie_detailniveau") and "informatie op %s niveau" % rol["informatie_detailniveau"],
                "extern" if rol.get("externe_rol") == "ja" else None,
            ] if x)
            regels.append(
                '<a class="rolkaart rolkaart--moment" href="../instrumenten.html?rol=%s">'
                '<span class="raci raci--%s" title="RACI: %s">%s</span>'
                '<span><span class="rolkaart__naam">%s</span>'
                '<span class="rolkaart__sub">%s</span></span>'
                '<span style="width:16px;height:4px;border-radius:2px;background:%s"></span></a>'
                % (esc(r["rol_id"]), esc(raci), esc(raci), esc(raci),
                   esc(rol.get("naam", r["rol_id"])), esc(sub),
                   esc(self.b.clusterkleur(rol.get("rolcluster_id")))))
        legenda = ('<p class="tiny muted" style="margin-top:10px">RACI: '
                   "<strong>R</strong> doet het werk, <strong>A</strong> is eindverantwoordelijk, "
                   "<strong>C</strong> wordt geraadpleegd, <strong>I</strong> wordt geïnformeerd. "
                   "Het streepje rechts is de kleur van het rolcluster in de routeplanner.</p>")
        return self.blok("wie", "Wie aan tafel zit",
                         "Op volgorde van betrokkenheid zoals het model die vastlegt.",
                         "".join(regels) + legenda)

    def blok_informatie(self):
        lijst = self.m.bij("beslismoment_informatiebehoefte", "beslismoment_id", self.code)
        if not lijst:
            return self.blok("informatie", "Welke informatie je nodig hebt", None,
                             self.leeg("Er zijn nog geen informatiebehoeften vastgelegd."))
        volgorde = {"hoog": 0, "middel": 1, "laag": 2}
        lijst = sorted(lijst, key=lambda r: volgorde.get(r.get("prioriteit"), 3))
        kaarten = []
        for r in lijst:
            ib = self.m.rec("informatiebehoefte", r["informatiebehoefte_id"]) or {}
            ontbreekt = ib.get("vaak_ontbrekend") == "ja"
            meta = " · ".join(x for x in [
                r.get("prioriteit") and "prioriteit %s" % r["prioriteit"],
                "verplicht" if r.get("verplicht") == "ja" else "niet verplicht",
                r.get("beschikbaar_vanaf"),
            ] if x)
            feiten = " · ".join(x for x in [
                ib.get("vereist_detailniveau") and "niveau: %s" % ib["vereist_detailniveau"],
                ib.get("vormvoorkeur") and "vorm: %s" % ib["vormvoorkeur"],
                ib.get("actualiteitseis"),
            ] if x)
            kaarten.append(
                '<div class="detailkaart%s">'
                '<div class="detailkaart__kop"><span class="detailkaart__titel">%s</span>'
                '<span class="detailkaart__meta">%s</span></div>'
                '<p class="muted">%s</p>%s%s</div>'
                % (" detailkaart--ontbreekt" if ontbreekt else "",
                   esc(ib.get("naam", r["informatiebehoefte_id"])), esc(meta),
                   esc(ib.get("vraagstelling", "")),
                   '<p class="tiny muted">%s</p>' % esc(feiten) if feiten else "",
                   '<div class="detailkaart__waarschuwing">%s<span>Ontbreekt in de '
                   "praktijk vaak — reken erop dat je dit eerst moet ophalen.</span></div>"
                   % icon("i-alert", 14, 1.9) if ontbreekt else ""))
        return self.blok("informatie", "Welke informatie je nodig hebt",
                         "Op prioriteit. Een oranje rand betekent: dit ontbreekt in de "
                         "praktijk vaak.", "".join(kaarten))

    def blok_vragen(self):
        lijst = self.m.bij("beslismoment_financiele_vraag", "beslismoment_id", self.code)
        if not lijst:
            return self.blok("vragen", "Welke financiële vragen hier spelen", None,
                             self.leeg("Er zijn nog geen financiële vragen gekoppeld."))
        volgorde = {"hoog": 0, "middel": 1, "laag": 2}
        items = []
        for r in sorted(lijst, key=lambda x: volgorde.get(x.get("prioriteit"), 3)):
            v = self.m.rec("financiele_vraag", r["financiele_vraag_id"]) or {}
            items.append(
                '<li><a class="linklist__btn" href="../vraag/%s.html">%s'
                '<span class="linklist__meta">%s</span>'
                '<span class="arrow">%s</span></a></li>'
                % (slug(r["financiele_vraag_id"]), esc(v.get("vraagtekst", "")),
                   esc(" · ".join(x for x in [
                       r.get("prioriteit") and "prioriteit %s" % r["prioriteit"],
                       v.get("verwacht_antwoordtype") and "antwoord: %s" % v["verwacht_antwoordtype"],
                       self.m.naam("financieel_thema", v.get("financieel_thema_id"))
                       if v.get("financieel_thema_id") else None] if x)),
                   icon("i-arrow-right", 16, 1.8)))
        return self.blok("vragen", "Welke financiële vragen hier spelen", None,
                         '<ul class="linklist">%s</ul>' % "".join(items))

    def blok_overdracht(self):
        lijst = [r for r in self.m.tab("informatieoverdracht")
                 if r.get("beslismoment_id") == self.code]
        if not lijst:
            return self.blok(
                "overdracht", "Wie levert wat aan wie",
                None,
                self.leeg("Voor dit beslismoment is nog geen informatieoverdracht "
                          "vastgelegd. Het model beschrijft er in v0.1 %d, verdeeld over "
                          "een paar momenten." % len(self.m.tab("informatieoverdracht"))))
        rijen = []
        for r in lijst:
            product = (self.m.naam("beslisproduct", r["beslisproduct_id"])
                       if r.get("beslisproduct_id") else "")
            behoefte = (self.m.naam("informatiebehoefte", r["informatiebehoefte_id"])
                        if r.get("informatiebehoefte_id") else "")
            rijen.append(
                '<div class="overdracht">'
                "<div><strong>%s</strong><br><span class=\"tiny muted\">levert</span></div>"
                '<span class="overdracht__pijl">%s</span>'
                "<div><strong>%s</strong><br><span class=\"tiny muted\">%s</span></div>"
                '<div class="overdracht__risico" style="grid-column:1/-1">%s %s</div>'
                "</div>"
                % (esc(self.m.naam("rol", r.get("van_rol_id"))),
                   icon("i-arrow-right", 15, 2),
                   esc(self.m.naam("rol", r.get("naar_rol_id"))),
                   esc(" · ".join(x for x in [product or behoefte, r.get("vereist_formaat"),
                                              r.get("moment_binnen_fase")] if x)),
                   icon("i-alert", 13, 2),
                   esc("risico: %s" % r["overdrachtsrisico"]) if r.get("overdrachtsrisico")
                   else "kwaliteitseis: %s" % esc(r.get("kwaliteitseis", "niet vastgelegd"))))
        return self.blok("overdracht", "Wie levert wat aan wie",
                         "De overdracht tussen rollen is waar het in de praktijk misgaat: "
                         "te laat, of in een formaat waar de ontvanger niets mee kan.",
                         "".join(rijen))

    def blok_knelpunten(self):
        lijst = self.m.bij("beslismoment_knelpunt", "beslismoment_id", self.code)
        if not lijst:
            return self.blok("knelpunten", "Waar het vaak misgaat", None,
                             self.leeg("Er zijn nog geen knelpunten aan dit moment gekoppeld."))
        kaarten = []
        for r in sorted(lijst, key=lambda x: 0 if x.get("impact") == "hoog" else 1):
            k = self.m.rec("knelpunt", r["knelpunt_id"]) or {}
            kaarten.append(
                '<div class="detailkaart%s">'
                '<div class="detailkaart__kop"><span class="detailkaart__titel">%s</span>'
                '<span class="detailkaart__meta">%s</span></div><p class="muted">%s</p></div>'
                % (" detailkaart--hoog" if r.get("impact") == "hoog" else "",
                   esc(k.get("naam", r["knelpunt_id"])),
                   esc(" · ".join(x for x in [
                       r.get("impact") and "impact %s" % r["impact"],
                       k.get("ernst") and "ernst %s" % k["ernst"],
                       k.get("frequentie") and "komt %s voor" % k["frequentie"],
                       k.get("knelpunttype")] if x)),
                   esc(k.get("omschrijving", ""))))
        return self.blok("knelpunten", "Waar het vaak misgaat", None, "".join(kaarten))

    def blok_handelen(self):
        lijst = sorted(self.m.bij("beslismoment_handelingsperspectief", "beslismoment_id", self.code),
                       key=lambda r: int(r.get("sort_order") or 99))
        if not lijst:
            return self.blok("handelen", "Wat je kunt doen", None,
                             self.leeg("Er zijn nog geen handelingsperspectieven gekoppeld."))
        kaarten = []
        for r in lijst:
            hp = self.m.rec("handelingsperspectief", r["handelingsperspectief_id"]) or {}
            kaarten.append(
                '<div class="detailkaart">'
                '<div class="detailkaart__kop"><span class="detailkaart__titel">%s</span></div>'
                "%s%s%s%s</div>"
                % (esc(hp.get("titel", "")),
                   '<p class="muted">%s</p>' % esc(hp["samenvatting"]) if hp.get("samenvatting") else "",
                   '<p><strong>Doe dit:</strong> %s</p>' % esc(hp["aanbevolen_actie"])
                   if hp.get("aanbevolen_actie") else "",
                   '<p class="small muted"><strong>Levert op:</strong> %s</p>' % esc(hp["verwacht_resultaat"])
                   if hp.get("verwacht_resultaat") else "",
                   '<div class="detailkaart__waarschuwing">%s<span>%s</span></div>'
                   % (icon("i-alert", 14, 1.9), esc(hp["waarschuwing"]))
                   if hp.get("waarschuwing") else ""))
        return self.blok("handelen", "Wat je kunt doen",
                         "Handelingsperspectieven: concrete acties die dit besluit "
                         "vooruithelpen, met wat ze opleveren en waar je op moet letten.",
                         "".join(kaarten))

    def blok_producten(self):
        lijst = self.m.bij("beslismoment_beslisproduct", "beslismoment_id", self.code)
        if not lijst:
            return self.blok("producten", "Welke producten erbij horen", None,
                             self.leeg("Er zijn nog geen beslisproducten gekoppeld."))
        items = []
        for r in lijst:
            bp = self.m.rec("beslisproduct", r["beslisproduct_id"]) or {}
            meta = " · ".join(x for x in [
                r.get("productrol"),
                "verplicht" if r.get("verplicht") == "ja" else None,
                bp.get("producttype"),
                "formeel document" if bp.get("is_formeel_document") == "ja" else None,
            ] if x)
            sjabloon = bp.get("template_instrument_id")
            if sjabloon:
                items.append(
                    '<li><a class="linklist__btn" href="../instrument/%s.html">%s'
                    '<span class="linklist__meta">%s · sjabloon: %s</span>'
                    '<span class="arrow">%s</span></a></li>'
                    % (slug(sjabloon), esc(bp.get("naam", "")), esc(meta),
                       esc(self.m.naam("instrument", sjabloon)), icon("i-arrow-right", 16, 1.8)))
            else:
                items.append('<li><div class="linklist__btn" style="cursor:default">%s'
                             '<span class="linklist__meta">%s</span></div></li>'
                             % (esc(bp.get("naam", "")), esc(meta)))
        return self.blok("producten", "Welke producten erbij horen", None,
                         '<ul class="linklist">%s</ul>' % "".join(items))

    def blok_instrumenten(self):
        lijst = self.m.bij("instrument_beslismoment", "beslismoment_id", self.code)
        if not lijst:
            return self.blok("instrumenten", "Instrumenten die hier helpen", None,
                             self.leeg("Er zijn nog geen instrumenten aan dit moment gekoppeld."))
        volgorde = {"hoog": 0, "middel": 1, "laag": 2}
        items = []
        for r in sorted(lijst, key=lambda x: volgorde.get(x.get("relevantie"), 3)):
            items.append(
                '<li><a class="linklist__btn" href="../instrument/%s.html">%s'
                '<span class="linklist__meta">%s</span>'
                '<span class="arrow">%s</span></a></li>'
                % (slug(r["instrument_id"]), esc(self.m.naam("instrument", r["instrument_id"])),
                   esc(" · ".join(x for x in [
                       r.get("ondersteuningsfunctie"),
                       r.get("gebruik_voor_of_na_besluit") and
                       "te gebruiken %s het besluit" % r["gebruik_voor_of_na_besluit"],
                       r.get("relevantie") and "relevantie %s" % r["relevantie"]] if x)),
                   icon("i-arrow-right", 16, 1.8)))
        return self.blok("instrumenten", "Instrumenten die hier helpen", None,
                         '<ul class="linklist">%s</ul>'
                         '<a class="btn btn--block" style="margin-top:12px" '
                         'href="../instrumenten.html?moment=%s">Alle instrumenten bij dit '
                         "moment in de bibliotheek %s</a>"
                         % ("".join(items), esc(self.code), icon("i-arrow-right", 15, 1.9)))

    # -- zijkolom ---------------------------------------------------
    def zijkolom(self):
        bm = self.bm
        fase = self.m.rec("procesfase", bm.get("procesfase_id")) or {}
        feiten = [
            ("Fase", "%s · %s" % (bm.get("procesfase_id", ""), fase.get("naam", ""))),
            ("Procesniveau", self.m.naam("procesniveau", fase.get("procesniveau_id"))),
            ("Besluittype", self.m.naam("besluittype", bm["besluittype_id"]) if bm.get("besluittype_id") else None),
            ("Formaliteit", bm.get("formaliteitsniveau")),
            ("Karakter", bm.get("voorbereidend_of_definitief")),
            ("P&C-moment", self.m.naam("pc_moment", bm["pc_moment_id"]) if bm.get("pc_moment_id") else None),
            ("Mandaat", "lokaal bepaald" if bm.get("mandaat_lokaal_bepaald") == "ja" else "landelijk gelijk"),
            ("Generiek", "ja, geldt voor elke gemeente" if bm.get("is_generic") == "ja" else None),
        ]
        kaarten = ['<section class="card" aria-labelledby="oog-kop">'
                   '<div class="card__head"><h2 id="oog-kop">In één oogopslag</h2></div>'
                   '<div class="card__body"><dl class="deflist">%s</dl></div></section>'
                   % "".join('<div><dt>%s</dt><dd>%s</dd></div>' % (esc(k), esc(v))
                             for k, v in feiten if v)]

        # De fase waarin dit moment ligt, met zijn centrale vraag
        if fase:
            kaarten.append(
                '<section class="card" aria-labelledby="fase-kop">'
                '<div class="card__head">%s<h2 id="fase-kop">De fase eromheen</h2></div>'
                '<div class="card__body">%s%s%s'
                '<a class="btn btn--block" href="../instrumenten.html?fase=%s" '
                'style="margin-top:12px">Instrumenten in deze fase %s</a></div></section>'
                % (icon("i-route", 16, 1.8),
                   '<p class="small" style="color:var(--vmv-teal-dark);font-weight:600">%s</p>'
                   % esc(fase["centrale_vraag"]) if fase.get("centrale_vraag") else "",
                   '<p class="small muted">Start: %s</p>' % esc(fase["startcriterium"])
                   if fase.get("startcriterium") else "",
                   '<p class="small muted">Klaar als: %s</p>' % esc(fase["eindcriterium"])
                   if fase.get("eindcriterium") else "",
                   esc(bm.get("procesfase_id", "")), icon("i-arrow-right", 15, 1.9)))

        # Andere momenten in dezelfde fase
        buren = [b for b in self.m.tab("beslismoment")
                 if b.get("procesfase_id") == bm.get("procesfase_id")
                 and b["beslismoment_code"] != self.code]
        if buren:
            kaarten.append(
                '<section class="card" aria-labelledby="buren-kop">'
                '<div class="card__head">%s<h2 id="buren-kop">Ook in deze fase</h2></div>'
                '<div class="card__body"><ul class="linklist">%s</ul></div></section>'
                % (icon("i-list", 16, 1.8),
                   "".join('<li><a class="linklist__btn" href="%s.html">%s'
                           '<span class="arrow">%s</span></a></li>'
                           % (slug(b["beslismoment_code"]), esc(b.get("naam", "")),
                              icon("i-arrow-right", 16, 1.8)) for b in buren)))

        return '<aside class="zijkolom">%s</aside>' % "".join(kaarten)

    def bouw(self):
        bm = self.bm
        fase = self.m.rec("procesfase", bm.get("procesfase_id")) or {}
        hoofd = ('<div class="paginalayout"><div>%s%s%s%s%s%s%s%s%s</div>%s</div>'
                 % (self.blok_besluit(), self.blok_wie(), self.blok_informatie(),
                    self.blok_vragen(), self.blok_overdracht(), self.blok_knelpunten(),
                    self.blok_handelen(), self.blok_producten(), self.blok_instrumenten(),
                    self.zijkolom()))
        self.b.pagina(
            "beslismoment/%s.html" % slug(self.code),
            bm.get("naam", self.code),
            (bm.get("centrale_vraag") or "")[:180],
            hoofd,
            nav="beslismomenten",
            kruimels=[("Beslismomenten", "beslismomenten.html"),
                      ("%s · %s" % (bm.get("procesfase_id", ""), fase.get("naam", "")), None),
                      (bm.get("naam", self.code), None)],
            subnav=self.SUBNAV,
            hero=self.hero(),
            contextstrip=True,
        )


# ====================================================================
# Pagina van een financiële vraag
# ====================================================================
class Vraagpagina:

    SUBNAV = [("waar", "Waar hij speelt"), ("antwoord", "Wie geeft antwoord"),
              ("thema", "Zelfde thema")]

    def __init__(self, bouwer, code):
        self.b = bouwer
        self.m = bouwer.m
        self.code = code
        self.v = self.m.rec("financiele_vraag", code)

    def leeg(self, tekst):
        return '<p class="leeg">%s<span>%s</span></p>' % (icon("i-info", 15), esc(tekst))

    def blok(self, anker, titel, uitleg, inhoud):
        return ('<section class="blok" id="%s" aria-labelledby="%s-kop">'
                '<div class="blok__kop"><h2 id="%s-kop">%s</h2></div>%s'
                '<div class="card"><div class="card__body">%s</div></div></section>'
                % (anker, anker, anker, esc(titel),
                   '<p class="blok__uitleg">%s</p>' % esc(uitleg) if uitleg else "", inhoud))

    def hero(self):
        v = self.v
        thema = self.m.naam("financieel_thema", v.get("financieel_thema_id")) \
            if v.get("financieel_thema_id") else None
        eyebrow = [esc(self.code), "Financiële vraag"]
        if thema:
            eyebrow.append(esc(thema))
        chips = []
        if v.get("verwacht_antwoordtype"):
            chips.append(chip("antwoord is een %s" % v["verwacht_antwoordtype"], "purple"))
        n_instr = len(self.m.bij("instrument_financiele_vraag", "financiele_vraag_id", self.code))
        n_mom = len(self.m.bij("beslismoment_financiele_vraag", "financiele_vraag_id", self.code))
        chips.append(chip("%d instrumenten geven antwoord" % n_instr, "teal"))
        chips.append(chip("speelt bij %d beslismomenten" % n_mom))

        return ('<div class="hero"><div class="hero__inner">'
                '<p class="hero__eyebrow">%s</p>'
                '<h1 class="hero__titel">%s</h1>%s'
                '<div class="hero__status">%s</div>'
                '<div class="hero__acties">'
                '<a class="btn btn--teal" href="../instrumenten.html?vraag=%s">%s '
                "Instrumenten bij deze vraag</a>"
                '<button type="button" class="btn" data-action="print">%s Printen</button>'
                "</div></div></div>"
                % ('<span class="kruimel__scheiding">·</span>'.join(eyebrow),
                   esc(v.get("vraagtekst", self.code)),
                   '<p class="hero__lead">Korte naam in het model: <strong>%s</strong>.</p>'
                   % esc(v["korte_naam"]) if v.get("korte_naam") else "",
                   "".join(chips), esc(self.code),
                   icon("i-search", 15, 1.9), icon("i-printer", 15, 1.8)))

    def blok_waar(self):
        lijst = self.m.bij("beslismoment_financiele_vraag", "financiele_vraag_id", self.code)
        if not lijst:
            return self.blok("waar", "Waar deze vraag speelt", None,
                             self.leeg("Deze vraag is nog aan geen enkel beslismoment gekoppeld."))
        volgorde = {"hoog": 0, "middel": 1, "laag": 2}
        items = []
        for r in sorted(lijst, key=lambda x: volgorde.get(x.get("prioriteit"), 3)):
            bm = self.m.rec("beslismoment", r["beslismoment_id"]) or {}
            fase = self.m.rec("procesfase", bm.get("procesfase_id")) or {}
            items.append(
                '<li><a class="linklist__btn" href="../beslismoment/%s.html">%s'
                '<span class="linklist__meta">%s</span><span class="arrow">%s</span></a></li>'
                % (slug(r["beslismoment_id"]), esc(bm.get("naam", "")),
                   esc(" · ".join(x for x in [
                       "%s · %s" % (bm.get("procesfase_id", ""), fase.get("naam", "")),
                       r.get("prioriteit") and "prioriteit %s" % r["prioriteit"],
                       bm.get("formaliteitsniveau")] if x)),
                   icon("i-arrow-right", 16, 1.8)))
        return self.blok("waar", "Waar deze vraag speelt",
                         "De beslismomenten waar dit op tafel komt, op prioriteit.",
                         '<ul class="linklist">%s</ul>' % "".join(items))

    def blok_antwoord(self):
        lijst = self.m.bij("instrument_financiele_vraag", "financiele_vraag_id", self.code)
        if not lijst:
            return self.blok("antwoord", "Wie geeft antwoord", None,
                             self.leeg("Er is nog geen instrument gekoppeld dat deze vraag beantwoordt."))
        per_niveau = {}
        for r in lijst:
            per_niveau.setdefault(r.get("antwoordniveau", "niveau niet vastgelegd"), []).append(r)
        delen = []
        for niveau in sorted(per_niveau, key=lambda n: 0 if "indicatief" in n else 1):
            items = []
            for r in per_niveau[niveau]:
                i = self.m.rec("instrument", r["instrument_id"]) or {}
                ty = self.m.rec("instrumenttype", i.get("primaire_instrumenttype_id")) or {}
                items.append(
                    '<li><a class="linklist__btn" href="../instrument/%s.html">%s'
                    '<span class="linklist__meta">%s</span><span class="arrow">%s</span></a></li>'
                    % (slug(r["instrument_id"]),
                       esc(self.m.naam("instrument", r["instrument_id"])),
                       esc(" · ".join(x for x in [
                           ty.get("naam"), r.get("relevantie") and "relevantie %s" % r["relevantie"]
                       ] if x)), icon("i-arrow-right", 16, 1.8)))
            delen.append('<p class="effect__categorie">%s (%d)</p><ul class="linklist">%s</ul>'
                         % (esc(niveau), len(items), "".join(items)))
        return self.blok("antwoord", "Wie geeft antwoord",
                         "Indicatief inzicht is genoeg om een richting te kiezen. Voor een "
                         "investeringsbesluit heb je een specialistische onderbouwing nodig.",
                         "".join(delen))

    def blok_thema(self):
        v = self.v
        th = v.get("financieel_thema_id")
        buren = [x for x in self.m.sorteer(self.m.tab("financiele_vraag"))
                 if x.get("financieel_thema_id") == th and x["vraag_code"] != self.code]
        if not buren:
            return self.blok("thema", "Andere vragen in dit thema", None,
                             self.leeg("Dit is de enige vraag in dit thema."))
        items = "".join(
            '<li><a class="linklist__btn" href="%s.html">%s'
            '<span class="linklist__meta">%s</span><span class="arrow">%s</span></a></li>'
            % (slug(x["vraag_code"]), esc(x.get("vraagtekst", "")),
               esc(x.get("verwacht_antwoordtype", "")), icon("i-arrow-right", 16, 1.8))
            for x in buren)
        return self.blok("thema", "Andere vragen in dit thema",
                         "Thema: %s" % self.m.naam("financieel_thema", th),
                         '<ul class="linklist">%s</ul>' % items)

    def zijkolom(self):
        v = self.v
        feiten = [
            ("Code", self.code),
            ("Korte naam", v.get("korte_naam")),
            ("Thema", self.m.naam("financieel_thema", v["financieel_thema_id"])
             if v.get("financieel_thema_id") else None),
            ("Antwoordtype", v.get("verwacht_antwoordtype")),
        ]
        return ('<aside class="zijkolom">'
                '<section class="card" aria-labelledby="oog-kop">'
                '<div class="card__head"><h2 id="oog-kop">In één oogopslag</h2></div>'
                '<div class="card__body"><dl class="deflist">%s</dl></div></section>'
                '<section class="card" aria-labelledby="hoe-kop">'
                '<div class="card__head">%s<h2 id="hoe-kop">Hoe lees je dit?</h2></div>'
                '<div class="card__body"><p class="small muted">Financiële vragen zijn de '
                "ingang die het dichtst bij de praktijk ligt: je weet wat je wilt weten, "
                "nog niet welk instrument dat levert. Deze pagina legt de brug.</p>"
                '<a class="btn btn--block" href="../vragen.html" style="margin-top:10px">'
                "Alle vragen %s</a></div></section></aside>"
                % ("".join('<div><dt>%s</dt><dd>%s</dd></div>' % (esc(k), esc(x))
                           for k, x in feiten if x),
                   icon("i-help", 16, 1.8), icon("i-arrow-right", 15, 1.9)))

    def bouw(self):
        v = self.v
        hoofd = ('<div class="paginalayout"><div>%s%s%s</div>%s</div>'
                 % (self.blok_waar(), self.blok_antwoord(), self.blok_thema(), self.zijkolom()))
        self.b.pagina(
            "vraag/%s.html" % slug(self.code),
            v.get("korte_naam") or v.get("vraagtekst", self.code),
            v.get("vraagtekst", ""),
            hoofd,
            nav="vragen",
            kruimels=[("Financiële vragen", "vragen.html"),
                      (v.get("korte_naam") or self.code, None)],
            subnav=self.SUBNAV,
            hero=self.hero(),
            contextstrip=True,
        )


# ====================================================================
# Overzichtspagina's
# ====================================================================
def bouw_beslismomenten_index(b):
    m = b.m
    delen = []
    for niveau in m.sorteer(m.tab("procesniveau")):
        fasen = [f for f in b.fasen if f.get("procesniveau_id") == niveau["code"]]
        momenten_in_niveau = [x for f in fasen for x in m.tab("beslismoment")
                              if x.get("procesfase_id") == f["fase_code"]]
        if not momenten_in_niveau:
            continue
        delen.append('<div class="groepkop"><h2>%s</h2>'
                     '<span class="groepkop__sub">%s · %d beslismomenten</span></div>'
                     % (esc(niveau.get("naam", "")), esc(niveau.get("omschrijving", "")),
                        len(momenten_in_niveau)))
        for f in fasen:
            momenten = [x for x in m.tab("beslismoment") if x.get("procesfase_id") == f["fase_code"]]
            if not momenten:
                continue
            delen.append('<p class="effect__categorie">%s · %s — %s</p>'
                         % (esc(f["fase_code"]), esc(f.get("naam", "")),
                            esc(f.get("centrale_vraag", ""))))
            kaarten = []
            for bm in momenten:
                rollen = len(m.bij("beslismoment_rol", "beslismoment_id", bm["beslismoment_code"]))
                instr = len(m.bij("instrument_beslismoment", "beslismoment_id", bm["beslismoment_code"]))
                kaarten.append(
                    '<a class="momentkaart" href="beslismoment/%s.html">'
                    '<span class="momentkaart__code">%s</span>'
                    '<span class="momentkaart__naam">%s</span>'
                    '<span class="momentkaart__vraag">%s</span>'
                    '<span class="momentkaart__foot">%s%s%s</span></a>'
                    % (slug(bm["beslismoment_code"]), esc(bm["beslismoment_code"]),
                       esc(bm.get("naam", "")), esc(bm.get("centrale_vraag", "")),
                       chip(bm.get("formaliteitsniveau", ""),
                            "critical" if bm.get("formaliteitsniveau") == "bestuurlijk" else "blue"),
                       chip("%d rollen" % rollen),
                       chip("%d instrumenten" % instr, "teal")))
            delen.append('<div class="momentgrid">%s</div>' % "".join(kaarten))

    hoofd = ('<div class="viewhead"><span class="viewhead__eyebrow">Beslismomenten</span>'
             '<h1 class="viewhead__title">Welk besluit ligt er voor?</h1>'
             '<p class="viewhead__sub">De %d beslismomenten die het model onderscheidt, in de '
             "volgorde van de vastgoedcyclus. Per moment staat wie aan tafel zit, welke "
             "informatie nodig is, welke financiële vragen spelen en waar het meestal "
             "misgaat.</p></div>%s" % (len(m.tab("beslismoment")), "".join(delen)))

    b.pagina("beslismomenten.html", "Beslismomenten",
             "De %d beslismomenten in de vastgoedcyclus." % len(m.tab("beslismoment")),
             hoofd, nav="beslismomenten", kruimels=[("Beslismomenten", None)])


def bouw_vragen_index(b):
    m = b.m
    delen = []
    for th in m.sorteer(m.tab("financieel_thema")):
        vragen = [v for v in m.sorteer(m.tab("financiele_vraag"))
                  if v.get("financieel_thema_id") == th["thema_code"]]
        if not vragen:
            continue
        delen.append('<div class="groepkop"><h2>%s</h2>'
                     '<span class="groepkop__sub">%d %s</span></div>'
                     % (esc(th.get("naam", "")), len(vragen),
                        "vraag" if len(vragen) == 1 else "vragen"))
        kaarten = []
        for v in vragen:
            code = v["vraag_code"]
            n_i = len(m.bij("instrument_financiele_vraag", "financiele_vraag_id", code))
            n_m = len(m.bij("beslismoment_financiele_vraag", "financiele_vraag_id", code))
            kaarten.append(
                '<a class="momentkaart" href="vraag/%s.html">'
                '<span class="momentkaart__code">%s</span>'
                '<span class="momentkaart__naam">%s</span>'
                '<span class="momentkaart__foot">%s%s%s</span></a>'
                % (slug(code), esc(code), esc(v.get("vraagtekst", "")),
                   chip("antwoord: %s" % v.get("verwacht_antwoordtype", "onbekend"), "purple"),
                   chip("%d instrumenten" % n_i, "teal"),
                   chip("%d beslismomenten" % n_m)))
        delen.append('<div class="momentgrid">%s</div>' % "".join(kaarten))

    gebruikt = len([t for t in m.tab("financieel_thema")
                    if any(v.get("financieel_thema_id") == t["thema_code"]
                           for v in m.tab("financiele_vraag"))])
    hoofd = ('<div class="viewhead"><span class="viewhead__eyebrow">Financiële vragen</span>'
             '<h1 class="viewhead__title">Wat wil je weten?</h1>'
             '<p class="viewhead__sub">De %d financiële vragen uit het model, gegroepeerd in '
             "%d thema's. Dit is de ingang die het dichtst bij de praktijk ligt: je weet wat "
             "je wilt weten, nog niet welk instrument dat levert.</p></div>%s"
             % (len(m.tab("financiele_vraag")), gebruikt, "".join(delen)))

    b.pagina("vragen.html", "Financiële vragen",
             "De %d financiële vragen uit het model." % len(m.tab("financiele_vraag")),
             hoofd, nav="vragen", kruimels=[("Financiële vragen", None)])




# ====================================================================
# Routeplanner en adviseur
# ====================================================================
def bouw_routeplanner(b):
    m = b.m
    hoofd = """
<div class="viewhead">
  <div class="viewhead__row">
    <div>
      <span class="viewhead__eyebrow">Routeplanner</span>
      <h1 class="viewhead__title">Wie zit waar aan tafel?</h1>
      <p class="viewhead__sub">Ieder rolcluster heeft een eigen lijn door de vastgoedcyclus.
        De ruiten zijn de %(momenten)d beslismomenten: daar komen rollen samen. Klik op een
        ruit voor het besluit, op een lijn voor het cluster.</p>
    </div>
    <p class="notice notice--purple small" style="flex:0 1 400px;margin:0">%(icoon_route)s
      <span>%(clusters)d rolclusters met %(rollen)d rollen, door %(fasen)d procesfasen.
        Portefeuille en object staan naast elkaar op één rij, maar lopen niet in elkaar over.</span>
    </p>
  </div>
</div>

<section class="card" aria-labelledby="c2-kaart-titel" style="margin-bottom:16px">
  <div class="card__head">
    <h2 id="c2-kaart-titel">Rolclusters door de procesfasen</h2>
    <span class="small muted" style="margin-left:auto" id="c2-status" aria-live="polite"></span>
  </div>
  <div class="card__body">
    <div class="c2-map" id="c2-map"></div>
    <div class="c2-legenda" style="margin-top:14px">
      <span><svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true"><circle cx="9" cy="9" r="5" fill="#fff" stroke="var(--vmv-grey-400)" stroke-width="2.5"/></svg> Station: cluster actief in die fase</span>
      <span><svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true"><path d="M10 3.5 16.5 10 10 16.5 3.5 10z" fill="#fff" stroke="var(--c2-violet)" stroke-width="2.5"/></svg> Beslismoment</span>
      <span><svg width="26" height="10" viewBox="0 0 26 10" aria-hidden="true"><path d="M2 5h22" stroke="var(--c2-violet)" stroke-width="1.8" stroke-dasharray="4 3" fill="none"/></svg> Verbindt de clusters aan tafel</span>
    </div>
  </div>
</section>

<div class="layout c2-onder">
  <div class="stack">
    <section class="card" aria-labelledby="c2-clusters-titel">
      <div class="card__head"><h2 id="c2-clusters-titel">Kies een rolcluster</h2></div>
      <div class="card__body">
        <p class="small muted" style="margin-bottom:12px">De gekozen lijn licht op, de andere
          vervagen. Beslismomenten blijven altijd zichtbaar.</p>
        <div class="c2-rollen" id="c2-clusters"></div>
        <button type="button" class="btn btn--block" style="margin-top:12px" data-action="c2-alle">Toon alle clusters</button>
      </div>
    </section>
    <section class="card" aria-labelledby="c2-uitleg-titel">
      <div class="card__body">
        <h2 id="c2-uitleg-titel" class="panel-title">%(icoon_info)s Wat zie je hier?</h2>
        <p class="small muted">De lijnen tonen in welke fasen een rolcluster aan tafel zit.
          Een ruit is een beslismoment; de stippellijn verbindt de clusters die daar samenkomen.</p>
        <hr class="divider">
        <p class="tiny muted">Een gekozen beslismoment staat in de adresbalk, dus je kunt
          deze weergave delen. Voor de volledige inhoud van een besluit — RACI,
          actualiteitseisen, knelpunten — ga je door naar de beslismomentpagina.</p>
      </div>
    </section>
  </div>

  <section class="card" aria-labelledby="c2-moment-titel">
    <div class="card__head">
      <h2 id="c2-moment-titel">Beslismomenten</h2>
      <a class="small" style="margin-left:auto" href="beslismomenten.html">Alle %(momenten)d op een rij</a>
    </div>
    <div class="card__body"><ul class="linklist" id="c2-momentenlijst"></ul></div>
  </section>

  <section class="card detailpanel" aria-labelledby="c2-detail-titel" aria-live="polite">
    <div class="card__head"><h2 id="c2-detail-titel">Detail</h2></div>
    <div class="card__body" id="c2-detail"></div>
  </section>
</div>
""" % {
        "momenten": len(m.tab("beslismoment")),
        "clusters": len(m.tab("rolcluster")),
        "rollen": len(m.tab("rol")),
        "fasen": len(b.fasen),
        "icoon_route": icon("i-route", 16),
        "icoon_info": icon("i-info", 16),
    }

    b.pagina("routeplanner.html", "Routeplanner",
             "Negen rolclusters door twaalf procesfasen, met de zestien beslismomenten "
             "waar ze samenkomen.",
             hoofd, nav="routeplanner", kruimels=[("Routeplanner", None)],
             scripts=["assets/kompas-model.js", "assets/model.js", "assets/routeplanner.js"])


def bouw_adviseur(b):
    m = b.m
    hoofd = """
<div class="viewhead">
  <div class="viewhead__row">
    <div>
      <span class="viewhead__eyebrow">Adviseur</span>
      <h1 class="viewhead__title">Vertel waar je tegenaan loopt</h1>
      <p class="viewhead__sub">Vijf vragen langs de hoofdroute van het model: opgave,
        vastgoed, fase, rol en knelpunt. Daarna weet je welk besluit voorligt, welke
        informatie je nodig hebt en welke instrumenten passen — met de reden erbij.</p>
    </div>
    <p class="notice notice--purple small" style="flex:0 1 400px;margin:0">%(icoon_chat)s
      <span>Dit is een eerste navigatievoorstel, geen formeel financieel advies. De
        koppelingen waarop de uitkomst berust zijn dummy.</span>
    </p>
  </div>
</div>

<div class="layout layout--3">
  <div class="stack">
    <section class="card" aria-labelledby="d-profiel-titel">
      <div class="card__body">
        <h2 id="d-profiel-titel" class="panel-title">%(icoon_building)s Jouw situatie</h2>
        <dl class="deflist" id="d-profiel"></dl>
        <hr class="divider">
        <button type="button" class="btn btn--block" data-action="d-reset">%(icoon_refresh)s Opnieuw beginnen</button>
      </div>
    </section>
    <section class="card" aria-labelledby="d-waarom-titel">
      <div class="card__body">
        <h2 id="d-waarom-titel" class="panel-title">%(icoon_info)s Waarom deze vragen?</h2>
        <p class="small muted">Het model verbindt opgave, objecttype, eigenaar, procesfase,
          rol en knelpunt aan het beslismoment dat voorligt. Pas daarna komen instrumenten
          in beeld — dat is de volgorde die het Kompas voorstelt.</p>
      </div>
    </section>
  </div>

  <section class="card" aria-labelledby="d-intake-titel">
    <div class="card__head">
      <h2 id="d-intake-titel">Intake</h2>
      <span class="small muted" style="margin-left:auto" id="d-voortgang" aria-live="polite"></span>
    </div>
    <div class="card__body">
      <div class="d-stappen" id="d-stappenbalk"></div>
      <div id="d-vraag"></div>
      <div id="d-resultaat"></div>
    </div>
  </section>

  <div class="stack">
    <section class="card detailpanel" aria-labelledby="d-zij-titel" aria-live="polite">
      <div class="card__head"><h2 id="d-zij-titel">Wat dit oplevert</h2></div>
      <div class="card__body" id="d-zijpaneel"></div>
    </section>
  </div>
</div>
""" % {
        "icoon_chat": icon("i-chat", 16),
        "icoon_building": icon("i-building", 16),
        "icoon_refresh": icon("i-refresh", 15, 1.8),
        "icoon_info": icon("i-info", 16),
    }

    b.pagina("adviseur.html", "Adviseur",
             "Vijf vragen over je situatie, en daarna het beslismoment dat voorligt met "
             "de instrumenten die passen.",
             hoofd, nav="adviseur", kruimels=[("Adviseur", None)],
             scripts=["assets/kompas-model.js", "assets/model.js", "assets/adviseur.js"])




# ====================================================================
# Home en verantwoording
# ====================================================================
def bouw_home(b):
    m = b.m
    v1 = len([i for i in m.tab("instrument") if i.get("tonen_in_v1") != "nee"])

    ingangen = [
        ("i-route", "Waar sta je in het proces?",
         "Welk besluit ligt er nu voor?",
         "Negen rolclusters door twaalf fasen. Zoek het beslismoment dat voorligt en zie "
         "wie aan tafel zit, welke informatie nodig is en waar het meestal misgaat.",
         "routeplanner.html", "Naar de routeplanner"),
        ("i-euro", "Wat wil je weten?",
         "Wat kost niets doen?",
         "Twaalf financiële vragen, gegroepeerd in thema's. Je weet wat je wilt weten, nog "
         "niet welk instrument dat levert — hier ligt de brug.",
         "vragen.html", "Naar de financiële vragen"),
        ("i-grid", "Welk instrument helpt?",
         "Welke subsidies zijn beschikbaar?",
         "%d instrumenten, te filteren op opgave, rol, fase en beslismoment. Elk instrument "
         "heeft een eigen pagina die vertelt of het bij jouw situatie past." % v1,
         "instrumenten.html", "Naar de instrumenten"),
    ]
    ingangkaarten = "".join(
        '<a class="ingang" href="%s"><span class="ingang__icoon">%s</span>'
        '<span class="ingang__titel">%s</span>'
        '<span class="ingang__vraag">%s</span>'
        '<span class="ingang__tekst">%s</span>'
        '<span class="ingang__meer">%s %s</span></a>'
        % (esc(doel), icon(ico, 22, 1.7), esc(titel), esc(vraag), esc(tekst),
           esc(meer), icon("i-arrow-right", 15, 1.9))
        for ico, titel, vraag, tekst, doel, meer in ingangen)

    cijfers = [
        (len(m.tab("instrument")), "instrumenten"),
        (len(m.tab("beslismoment")), "beslismomenten"),
        (len(m.tab("rol")), "rollen"),
        (len(b.fasen), "procesfasen"),
        (len(m.tab("financiele_vraag")), "financiële vragen"),
        (len(m.tab("opgave")), "opgaven"),
    ]
    cijferstrip = "".join(
        '<div class="cijfer"><span class="cijfer__getal">%d</span>'
        '<span class="cijfer__label">%s</span></div>' % (n, esc(label))
        for n, label in cijfers)

    hoofd = """
<div class="viewhead">
  <span class="viewhead__eyebrow">Verduurzaming Maatschappelijk Vastgoed</span>
  <h1 class="viewhead__title">Het Financieel Vastgoedkompas</h1>
  <p class="viewhead__sub">Een navigatie-instrument, geen kennisbank. Het Kompas brengt je
    van je situatie naar het besluit dat voorligt, en pas daarna naar de instrumenten die
    daarbij horen. Begin waar je zelf staat.</p>
</div>

<div class="ingangen" style="margin-bottom:32px">%(ingangen)s</div>

<section class="card" style="margin-bottom:32px" aria-labelledby="adv-kop">
  <div class="card__body" style="display:grid;grid-template-columns:minmax(0,1fr) auto;
       gap:24px;align-items:center">
    <div style="min-width:0">
      <h2 id="adv-kop" style="margin-bottom:6px">Weet je nog niet waar je moet beginnen?</h2>
      <p class="small muted" style="margin:0">Beantwoord vijf vragen over je opgave, je
        vastgoed, je fase, je rol en waar je tegenaan loopt. De adviseur leidt je naar het
        beslismoment dat voorligt en de instrumenten die passen — met de reden erbij.</p>
    </div>
    <a class="btn btn--primary" href="adviseur.html">%(icoon_chat)s Start de adviseur</a>
  </div>
</section>

<div class="layout layout--2r" style="margin-bottom:32px">
  <section class="card" aria-labelledby="wat-kop">
    <div class="card__head">%(icoon_compass)s<h2 id="wat-kop">Hoe het Kompas denkt</h2></div>
    <div class="card__body">
      <p class="small">De route door het model loopt altijd dezelfde kant op:</p>
      <div class="flow" style="margin:14px 0">
        <div class="flow__stap"><span class="label">1. Je situatie</span>
          <p>Opgave, vastgoed, eigenaar, fase en rol.</p></div>
        <div class="flow__pijl">%(icoon_pijl)s</div>
        <div class="flow__stap"><span class="label">2. Het besluit</span>
          <p>Welk beslismoment voorligt, wie aan tafel zit en welke informatie je nodig hebt.</p></div>
        <div class="flow__pijl">%(icoon_pijl)s</div>
        <div class="flow__stap"><span class="label">3. Het instrument</span>
          <p>Pas dán wat je kunt gebruiken, en waarom dat bij jou past.</p></div>
      </div>
      <p class="small muted">Die volgorde is het verschil met een lijst met regelingen.
        Een instrument zonder besluit eromheen helpt niemand verder.</p>
    </div>
  </section>

  <section class="card" aria-labelledby="stand-kop">
    <div class="card__head">%(icoon_chart)s<h2 id="stand-kop">De stand van het model</h2></div>
    <div class="card__body">
      <div class="cijferstrip" style="grid-template-columns:repeat(2,minmax(0,1fr))">%(cijfers)s</div>
      <p class="tiny muted" style="margin-top:14px">Datamodel %(versie)s van %(datum)s,
        %(tabellen)d tabellen met %(records)d records.</p>
      <a class="btn btn--block" style="margin-top:10px" href="verantwoording.html">
        Wat is echt en wat is dummy? %(icoon_pijl_klein)s</a>
    </div>
  </section>
</div>

<div class="notice notice--purple" style="align-items:flex-start">%(icoon_info)s
  <span><strong>Dit is een conceptprototype.</strong> De instrumentnamen, omschrijvingen,
  bronnen en beheerders komen uit catalogus v0.1 en zijn echt. Alles wat ze verbindt — met
  rollen, fasen, beslismomenten, opgaven en vragen — is dummy, bedoeld om de navigatie te
  kunnen beoordelen. Het model is niet vastgesteld door het kernteam. Gebruik deze site om
  te oordelen over de manier van navigeren, niet over de inhoud.</span>
</div>
""" % {
        "ingangen": ingangkaarten,
        "cijfers": cijferstrip,
        "versie": esc(b.meta["versie"]),
        "datum": esc(datum_nl(b.meta["datum"])),
        "tabellen": len(m.data),
        "records": sum(len(v) for v in m.data.values()),
        "icoon_chat": icon("i-chat", 16, 1.8),
        "icoon_compass": icon("i-compass", 17, 1.7),
        "icoon_chart": icon("i-chart", 17, 1.7),
        "icoon_info": icon("i-info", 17),
        "icoon_pijl": icon("i-arrow-right", 18, 2),
        "icoon_pijl_klein": icon("i-arrow-right", 15, 1.9),
    }

    b.pagina("index.html", "Home",
             "Navigatie-instrument voor financiële besluitvorming rond maatschappelijk "
             "vastgoed. Van je situatie naar het besluit dat voorligt.",
             hoofd, nav="")


def bouw_verantwoording(b):
    m = b.m

    # Wat echt is en wat dummy, per onderdeel.
    echt = [
        ("Instrumentnamen en omschrijvingen", "catalogus v0.1",
         "De %d instrumenten, hun naam, korte omschrijving, doel, input en output."
         % len(m.tab("instrument"))),
        ("Bronnen", "catalogus v0.1",
         "De %d bronverwijzingen, met brontype en de datum waarop ze geraadpleegd zijn."
         % len(m.tab("bron"))),
        ("Beheerders", "catalogus v0.1",
         "Welke organisatie een instrument beheert (%d organisaties)." % len(m.tab("organisatie"))),
        ("Openstelling", "catalogus v0.1, deels",
         "Voor %d van de %d instrumenten staat een ronde of status in het model."
         % (len({r["instrument_id"] for r in m.tab("openstelling")}), len(m.tab("instrument")))),
    ]
    dummy = [
        ("Procesfasen en beslismomenten",
         "De %d fasen en %d beslismomenten zijn een werkhypothese van het ontwerpteam, niet "
         "vastgesteld." % (len(b.fasen), len(m.tab("beslismoment")))),
        ("Rollen en rolclusters",
         "De %d rollen in %d clusters, en wie bij welk besluit aan tafel zit (%d "
         "betrokkenheden)." % (len(m.tab("rol")), len(m.tab("rolcluster")),
                               len(m.tab("beslismoment_rol")))),
        ("Alle koppelingen van instrumenten",
         "Welke opgave, rol, fase, beslismoment, vraag, objecttype of eigenaartype bij een "
         "instrument hoort: in totaal %d koppelingen, allemaal dummy."
         % sum(len(m.tab(t)) for _, t, _ in KOPPELING)),
        ("Effecten en voorwaarden",
         "Wat een instrument met de businesscase doet (%d effecten) en onder welke "
         "voorwaarden het geldt (%d voorwaarden)."
         % (len(m.tab("instrument_effect")), len(m.tab("instrument_voorwaarde")))),
        ("Informatiebehoeften, knelpunten en handelingsperspectieven",
         "%d informatiebehoeften, %d knelpunten en %d handelingsperspectieven, plus hun "
         "koppeling aan beslismomenten."
         % (len(m.tab("informatiebehoefte")), len(m.tab("knelpunt")),
            len(m.tab("handelingsperspectief")))),
        ("Informatieoverdracht",
         "De %d overdrachten tussen rollen, met formaat en overdrachtsrisico."
         % len(m.tab("informatieoverdracht"))),
        ("Kennisproducten",
         "De %d kennisproducten zijn dummy-titels met voorbeeld-URL's."
         % len(m.tab("kennisproduct"))),
    ]

    def lijst(items, soort):
        return "".join(
            '<div class="detailkaart"><div class="detailkaart__kop">'
            '<span class="detailkaart__titel">%s</span>%s</div>'
            '<p class="muted">%s</p></div>'
            % (esc(x[0]),
               '<span class="detailkaart__meta">%s</span>' % esc(x[1]) if soort == "echt" else "",
               esc(x[-1]))
            for x in items)

    # Witte vlekken uit de kennisanalyse.
    per_type = {}
    for ka in m.tab("kennisanalyse"):
        per_type.setdefault(ka.get("analysetype", "overig"), []).append(ka)
    vlekken = []
    for soort in sorted(per_type):
        vlekken.append('<p class="effect__categorie">%s (%d)</p>' % (esc(soort), len(per_type[soort])))
        for ka in sorted(per_type[soort], key=lambda x: 0 if x.get("prioriteit") == "hoog" else 1):
            vlekken.append(
                '<div class="detailkaart%s"><div class="detailkaart__kop">'
                '<span class="detailkaart__titel">%s</span>'
                '<span class="detailkaart__meta">%s</span></div>'
                '<p class="muted">%s</p>%s</div>'
                % (" detailkaart--hoog" if ka.get("prioriteit") == "hoog" else "",
                   esc(ka.get("titel", "")),
                   esc(" · ".join(x for x in [
                       ka.get("prioriteit") and "prioriteit %s" % ka["prioriteit"],
                       ka.get("status")] if x)),
                   esc(ka.get("omschrijving", "")),
                   '<p><strong>Voorstel:</strong> %s</p>' % esc(ka["aanbevolen_actie"])
                   if ka.get("aanbevolen_actie") else ""))

    # Tabellenoverzicht
    rijen = "".join(
        "<tr><td>%s</td><td>%s</td><td>%d</td></tr>"
        % (esc(naam_t), esc(DOMEIN.get(b.domein.get(naam_t, ""), "")), len(records))
        for naam_t, records in sorted(m.data.items()))

    hoofd = """
<div class="viewhead">
  <span class="viewhead__eyebrow">Verantwoording</span>
  <h1 class="viewhead__title">Wat is echt en wat is dummy?</h1>
  <p class="viewhead__sub">Deze site draait op datamodel %(versie)s van %(datum)s. Dat model
    is concept: het is niet vastgesteld door het kernteam en mag niet als inhoud van het
    Kompas worden gepubliceerd. Hieronder staat per onderdeel waar het vandaan komt.</p>
</div>

<div class="layout layout--2r">
  <div>
    <section class="blok" id="echt" aria-labelledby="echt-kop">
      <div class="blok__kop">%(icoon_check)s<h2 id="echt-kop">Dit komt uit de catalogus</h2></div>
      <p class="blok__uitleg">Verzameld en nagekeken voor catalogus v0.1. Je kunt deze
        informatie gebruiken om te beoordelen of de bibliotheek compleet is.</p>
      <div class="card"><div class="card__body">%(echt)s</div></div>
    </section>

    <section class="blok" id="dummy" aria-labelledby="dummy-kop">
      <div class="blok__kop">%(icoon_alert)s<h2 id="dummy-kop">Dit is dummy</h2></div>
      <p class="blok__uitleg">Verzonnen om de navigatie te kunnen bouwen en testen. Het
        patroon klopt — de inhoud niet. Neem hier niets uit over.</p>
      <div class="card"><div class="card__body">%(dummy)s</div></div>
    </section>

    <section class="blok" id="vlekken" aria-labelledby="vlekken-kop">
      <div class="blok__kop">%(icoon_bulb)s<h2 id="vlekken-kop">Wat het model zelf nog mist</h2></div>
      <p class="blok__uitleg">De kennisanalyse benoemt %(n_vlekken)d punten waar het beeld
        nog niet compleet is. Dat is geen fout in deze site, maar de agenda voor v0.2.</p>
      <div class="card"><div class="card__body">%(vlekken)s</div></div>
    </section>

    <section class="blok" id="tabellen" aria-labelledby="tab-kop">
      <div class="blok__kop">%(icoon_grid)s<h2 id="tab-kop">De tabellen in deze site</h2></div>
      <p class="blok__uitleg">%(n_tabellen)d van de 65 tabellen uit het model zitten in deze
        site. De beheerdomeinen (validatie, wijzigingslog, reviewplanning, ontwikkelacties)
        blijven eruit.</p>
      <div class="card"><div class="card__body"><div class="tabelwrap">
        <table class="datatabel">
          <thead><tr><th>Tabel</th><th>Domein</th><th>Records</th></tr></thead>
          <tbody>%(rijen)s</tbody>
        </table>
      </div></div></div>
    </section>
  </div>

  <aside class="zijkolom">
    <section class="card" aria-labelledby="gebruik-kop">
      <div class="card__head">%(icoon_help)s<h2 id="gebruik-kop">Wat kun je hiermee?</h2></div>
      <div class="card__body">
        <p class="small"><strong>Wel:</strong> beoordelen of de manier van navigeren klopt.
          Vind je het beslismoment dat je zoekt? Staan de goede vragen op de goede plek?
          Mis je een rol, een fase of een ingang?</p>
        <p class="small"><strong>Niet:</strong> een instrument kiezen, een subsidie
          aanvragen, of een raadsvoorstel onderbouwen. Daarvoor is de inhoud niet
          vastgesteld en de koppeling niet gecontroleerd.</p>
      </div>
    </section>
    <section class="card" aria-labelledby="bouw-kop">
      <div class="card__head">%(icoon_layers)s<h2 id="bouw-kop">Hoe dit gebouwd is</h2></div>
      <div class="card__body">
        <p class="small muted">Deze site is uit het datamodel gegenereerd. Komt er een v0.2,
          dan is het één commando: nieuwe data erin, site eruit. Alle %(n_verwijzingen)d
          verwijzingen tussen de tabellen worden bij elke bouw gecontroleerd; een gebroken
          verwijzing stopt de bouw in plaats van stilletjes een leeg paneel op te leveren.</p>
        <p class="small muted">Eén bestand per pagina, geen framework, geen externe
          bronnen. De site werkt vanaf een USB-stick zonder internet.</p>
      </div>
    </section>
    <section class="card" aria-labelledby="eerder-kop">
      <div class="card__head">%(icoon_doc)s<h2 id="eerder-kop">Eerdere versies</h2></div>
      <div class="card__body">
        <p class="small muted">Voor deze site waren er drie prototypes in één bestand: de
          vijf archetypen, de drie navigatieconcepten en de datagedreven archetypen. Die
          staan nog in dezelfde map en blijven ongewijzigd, zodat je kunt vergelijken.</p>
      </div>
    </section>
  </aside>
</div>
""" % {
        "versie": esc(b.meta["versie"]),
        "datum": esc(datum_nl(b.meta["datum"])),
        "echt": lijst(echt, "echt"),
        "dummy": lijst(dummy, "dummy"),
        "vlekken": "".join(vlekken),
        "n_vlekken": len(m.tab("kennisanalyse")),
        "n_tabellen": len(m.data),
        "n_verwijzingen": b.aantal_verwijzingen,
        "rijen": rijen,
        "icoon_check": icon("i-shield", 17, 1.7),
        "icoon_alert": icon("i-alert", 17, 1.7),
        "icoon_bulb": icon("i-bulb", 17, 1.7),
        "icoon_grid": icon("i-grid", 17, 1.7),
        "icoon_help": icon("i-help", 17, 1.7),
        "icoon_layers": icon("i-layers", 17, 1.7),
        "icoon_doc": icon("i-doc", 17, 1.7),
    }

    b.pagina("verantwoording.html", "Verantwoording",
             "Wat in deze site echt is en wat dummy, per onderdeel van het datamodel.",
             hoofd, nav="verantwoording", kruimels=[("Verantwoording", None)])


# De vier domeinen van het model, zoals de bron ze noemt.
DOMEIN = {
    "A": "A · Navigatie", "B": "B · Besluitondersteuning",
    "C": "C · Instrumenten", "D": "D · Beheer",
}


# ====================================================================
# Linkcontrole: een multipaginasite faalt vooral op doodlopende links
# ====================================================================
LINKPAT = re.compile(r'(?:href|src)="([^"]+)"')

# Pagina's waar het anker door JavaScript wordt afgehandeld in plaats van
# naar een element te wijzen.
DYNAMISCHE_ANKERS = {"routeplanner.html"}


def controleer_links():
    """Elke interne link moet een bestaand bestand en anker raken.

    Alleen HTML wordt doorzocht: in de JavaScript staan href-waarden als
    losse stukjes string, die hier niets betekenen. Het gedrag daarvan
    toetsen we in de browser.
    """
    paginas = []
    for wortel, _, bestanden in os.walk(UIT):
        for naam in bestanden:
            if naam.endswith(".html"):
                paginas.append(os.path.join(wortel, naam))

    ankers = {}
    for pad in paginas:
        with open(pad, encoding="utf-8") as fh:
            ankers[pad] = set(re.findall(r'\sid="([^"]+)"', fh.read()))

    fouten, gecontroleerd = [], 0
    for pad in paginas:
        with open(pad, encoding="utf-8") as fh:
            tekst = fh.read()
        rel = os.path.relpath(pad, UIT)
        for doel in LINKPAT.findall(tekst):
            if doel.startswith(("http://", "https://", "mailto:", "data:")):
                continue
            if doel.startswith("#"):
                gecontroleerd += 1
                if len(doel) > 1 and doel[1:] not in ankers[pad]:
                    fouten.append("%s: anker %s bestaat niet" % (rel, doel))
                continue
            gecontroleerd += 1
            bestand = doel.split("?")[0].split("#")[0]
            anker = doel.split("#")[1] if "#" in doel else ""
            if not bestand:
                continue
            vol = os.path.normpath(os.path.join(os.path.dirname(pad), bestand))
            if not os.path.exists(vol):
                fouten.append("%s: %s bestaat niet" % (rel, doel))
            elif (anker and vol in ankers
                  and os.path.basename(vol) not in DYNAMISCHE_ANKERS
                  and anker not in ankers[vol]):
                fouten.append("%s: %s heeft geen anker %s" % (rel, bestand, anker))
    return gecontroleerd, fouten


# ====================================================================
# Hoofdprogramma
# ====================================================================
def main():
    args = sys.argv[1:]

    ruw = K.lees_bron()
    data = K.kleed_uit(ruw, K.TABELLEN_SITE)
    print("bron        : %s (v%s, %s)"
          % (os.path.basename(K.BRON), ruw["_meta"]["versie"].lstrip("v"), ruw["_meta"]["datum"]))
    print("tabellen    : %d" % len(data))
    print("records     : %d" % sum(len(v) for v in data.values()))

    gecontroleerd, fouten = K.controleer(data)
    print("verwijzingen: %d gecontroleerd" % gecontroleerd)
    if fouten:
        print("GEBROKEN VERWIJZINGEN: %d" % len(fouten))
        for f in fouten[:25]:
            print("   " + f)
        return 1
    print("              alle verwijzingen kloppen")

    if "--controleer" in args:
        return 0

    if "--schoon" in args:
        for map_ in GEGENEREERD:
            pad = os.path.join(UIT, map_)
            if os.path.isdir(pad):
                shutil.rmtree(pad)
        for naam in os.listdir(UIT):
            if naam.endswith(".html"):
                os.remove(os.path.join(UIT, naam))
        print("schoon      : gegenereerde pagina's verwijderd")

    model = K.Model(data)
    domein = {t: ruw["tabellen"][t].get("domein", "")
              for t in data if t in ruw["tabellen"]}
    b = Bouwer(model, ruw["_meta"], domein, gecontroleerd)
    b.bereken()

    # Data-assets eerst: de pagina's verwijzen ernaar.
    for naam, inhoud in [("kompas-namen.js", bouw_namen_js(b)),
                         ("kompas-index.js", bouw_index_js(b)),
                         ("kompas-model.js", bouw_model_js(b))]:
        with open(os.path.join(ASSETS, naam), "w", encoding="utf-8") as fh:
            fh.write(inhoud)
        print("asset       : %-18s %6.1f kB" % (naam, len(inhoud.encode()) / 1024))

    # Pagina's
    bouw_instrumenten_index(b)
    for i in model.tab("instrument"):
        Instrumentpagina(b, i["instrument_code"]).bouw()
    for code in [x["beslismoment_code"] for x in model.tab("beslismoment")]:
        Beslismomentpagina(b, code).bouw()
    for code in [x["vraag_code"] for x in model.tab("financiele_vraag")]:
        Vraagpagina(b, code).bouw()
    for maker in PAGINAMAKERS:
        maker(b)

    print("pagina's    : %d" % len(b.geschreven))
    bytes_totaal = sum(os.path.getsize(os.path.join(UIT, p)) for p in b.geschreven)
    print("omvang      : %.1f kB totaal, gemiddeld %.1f kB per pagina"
          % (bytes_totaal / 1024, bytes_totaal / 1024 / len(b.geschreven)))

    if "--links" in args:
        n, linkfouten = controleer_links()
        print("links       : %d gecontroleerd" % n)
        if linkfouten:
            print("GEBROKEN LINKS: %d" % len(linkfouten))
            for f in linkfouten[:40]:
                print("   " + f)
            return 1
        print("              alle links kloppen")
    return 0


PAGINAMAKERS = [bouw_beslismomenten_index, bouw_vragen_index,
                bouw_routeplanner, bouw_adviseur,
                bouw_home, bouw_verantwoording]


if __name__ == "__main__":
    sys.exit(main())
