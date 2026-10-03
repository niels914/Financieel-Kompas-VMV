#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gedeelde datalaag voor het Financieel Vastgoedkompas.

Twee dingen:

1. `kleed_uit()` maakt van de ruwe modeldump een compacte bundel: beheervelden
   eruit, lege waarden eruit, UUID-waarden eruit. Het model verwijst namelijk op
   leesbare codes (ROL-003, P1, I-001); de UUID staat alleen in de primaire
   sleutel van het doelrecord en is dus nergens voor nodig.
2. `Model` is de datatoegang voor de generator: tab/idx/rec/naam/bij/sorteer,
   bewust dezelfde vorm als de JavaScript-laag in de browser, zodat de generator
   en de pagina's hetzelfde lezen.

Gebruikt door scripts/bouw-site.py en scripts/ververs-datamodel.py.
"""

import json
import os
import re

UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

HIER = os.path.dirname(os.path.abspath(__file__))
WORTEL = os.path.dirname(HIER)
BRON = os.path.join(WORTEL, "data", "kompas_dummy_data.json")

# Beheervelden die geen enkel prototype gebruikt.
BEHEER = {
    "created_at", "created_by", "updated_at", "updated_by",
    "record_status", "version_number", "notes_internal",
}

# Velden die we per tabel extra weglaten (duplicaat of onbruikbaar).
EXTRA_WEG = {
    "instrument": {"uitgebreide_omschrijving"},
}

# De tabellen die de drie archetypen in archetypen-datamodel.html nodig hebben.
TABELLEN_ARCHETYPEN = [
    # A. Navigatiestructuur
    "opgave", "procesniveau", "procesfase", "procesfase_relatie",
    "beslismoment", "besluittype", "rol", "rolcluster", "functie_alias",
    "eigenaartype", "objecttype",
    # B. Besluitondersteuning
    "financiele_vraag", "financieel_thema", "informatiebehoefte",
    "informatietype", "beslisproduct", "handelingsperspectief", "knelpunt",
    "informatieoverdracht", "beslismoment_rol",
    "beslismoment_informatiebehoefte", "beslismoment_financiele_vraag",
    "beslismoment_beslisproduct", "beslismoment_handelingsperspectief",
    "beslismoment_knelpunt",
    # C. Instrumentenbibliotheek
    "instrument", "instrumenttype", "digitale_vorm", "organisatie",
    "organisatietype", "instrument_organisatie", "bron", "brontype",
    "instrument_bron", "instrument_rol", "instrument_procesfase",
    "instrument_beslismoment", "instrument_opgave",
    "instrument_financiele_vraag", "instrument_eigenaartype",
    "instrument_objecttype", "financiele_route",
    "instrument_financiele_route", "effecttype", "instrument_effect",
    "voorwaardetype", "instrument_voorwaarde", "werkingsgebied",
    "instrument_werkingsgebied", "openstelling", "pc_moment",
    "instrument_relatie", "instrument_relatietype",
]

# De site heeft daarnaast de kennisproducten, de witte vlekken en de
# statuswaarden nodig voor de instrumentpagina en de verantwoording.
TABELLEN_SITE = TABELLEN_ARCHETYPEN + [
    "kennisproduct", "kennisproduct_instrument", "kennisproduct_beslismoment",
    "kennisanalyse", "gebruikersfeedback",
    "inhoudelijke_status", "publicatiestatus",
]

# Welk veld in elke tabel de leesbare sleutel is waarop verwezen wordt.
SLEUTEL = {
    "opgave": "opgave_code", "procesniveau": "code", "procesfase": "fase_code",
    "beslismoment": "beslismoment_code", "besluittype": "code", "rol": "rol_code",
    "rolcluster": "code", "eigenaartype": "code", "objecttype": "objecttype_code",
    "financiele_vraag": "vraag_code", "financieel_thema": "thema_code",
    "informatiebehoefte": "informatie_code", "informatietype": "code",
    "beslisproduct": "code", "handelingsperspectief": "code", "knelpunt": "code",
    "instrument": "instrument_code", "instrumenttype": "code",
    "digitale_vorm": "code", "organisatie": "naam", "organisatietype": "code",
    "bron": "titel", "brontype": "code", "financiele_route": "route_code",
    "effecttype": "code", "voorwaardetype": "code", "werkingsgebied": "naam",
    "pc_moment": "code", "instrument_relatietype": "code",
    "kennisproduct": "product_code", "kennisanalyse": "analyse_code",
    "inhoudelijke_status": "code", "publicatiestatus": "code",
}

# Verwijsveld -> doeltabel. Alleen wat we daadwerkelijk joinen.
VERWIJZINGEN = {
    "procesniveau_id": "procesniveau", "procesfase_id": "procesfase",
    "beslismoment_id": "beslismoment", "besluittype_id": "besluittype",
    "rol_id": "rol", "van_rol_id": "rol", "naar_rol_id": "rol",
    "rolcluster_id": "rolcluster", "eigenaartype_id": "eigenaartype",
    "objecttype_id": "objecttype", "parent_objecttype_id": "objecttype",
    "opgave_id": "opgave", "financiele_vraag_id": "financiele_vraag",
    "financieel_thema_id": "financieel_thema",
    "informatiebehoefte_id": "informatiebehoefte",
    "informatietype_id": "informatietype", "beslisproduct_id": "beslisproduct",
    "handelingsperspectief_id": "handelingsperspectief", "knelpunt_id": "knelpunt",
    "instrument_id": "instrument", "van_instrument_id": "instrument",
    "naar_instrument_id": "instrument", "primaire_instrumenttype_id": "instrumenttype",
    "digitale_vorm_id": "digitale_vorm", "organisatie_id": "organisatie",
    "organisatietype_id": "organisatietype", "bron_id": "bron",
    "brontype_id": "brontype", "financiele_route_id": "financiele_route",
    "effecttype_id": "effecttype", "voorwaardetype_id": "voorwaardetype",
    "werkingsgebied_id": "werkingsgebied", "pc_moment_id": "pc_moment",
    "relatietype_id": "instrument_relatietype",
    "van_procesfase_id": "procesfase", "naar_procesfase_id": "procesfase",
    "template_instrument_id": "instrument",
    "kennisproduct_id": "kennisproduct",
    "inhoudelijke_status_id": "inhoudelijke_status",
    "publicatiestatus_id": "publicatiestatus",
}

# Velden die naar een tabel verwijzen die we niet meenemen, of die vrije tekst
# bevatten die op _id eindigt. Niet controleren.
GEEN_VERWIJZING = {"validation_status_id"}


def lees_bron(pad=BRON):
    with open(pad, encoding="utf-8") as fh:
        return json.load(fh)


def kleed_uit(ruw, tabellen=None, stil=False):
    """Compacte bundel: beheervelden, lege waarden en UUID's eruit."""
    bron = ruw["tabellen"]
    uit = {}
    for naam in (tabellen or TABELLEN_SITE):
        if naam not in bron:
            if not stil:
                print("  waarschuwing: tabel %s ontbreekt in de bron" % naam)
            continue
        weg = BEHEER | EXTRA_WEG.get(naam, set())
        schoon = []
        for rec in bron[naam]["records"]:
            o = {}
            for k, v in rec.items():
                if k in weg or v in (None, ""):
                    continue
                if isinstance(v, str) and UUID.match(v):
                    continue
                o[k] = v
            schoon.append(o)
        uit[naam] = schoon
    return uit


def controleer(data):
    """Elke verwijzing moet een bestaand record raken."""
    sleutels = {}
    for tabel, veld in SLEUTEL.items():
        if tabel in data:
            sleutels[tabel] = {str(r.get(veld)) for r in data[tabel] if r.get(veld)}

    fouten, gecontroleerd = [], 0
    for tabel, records in data.items():
        for i, rec in enumerate(records):
            for veld, waarde in rec.items():
                if veld in GEEN_VERWIJZING:
                    continue
                doel = VERWIJZINGEN.get(veld)
                if not doel or doel not in sleutels:
                    continue
                gecontroleerd += 1
                if str(waarde) not in sleutels[doel]:
                    fouten.append("%s[%d].%s = %r wijst niet naar %s"
                                  % (tabel, i, veld, waarde, doel))
    return gecontroleerd, fouten


def compact(data):
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


class Model:
    """Datatoegang met dezelfde vorm als de JavaScript-laag in de browser."""

    def __init__(self, data):
        self.data = data
        self._idx = {}
        self._grp = {}

    # -- basis ----------------------------------------------------------
    def tab(self, naam):
        return self.data.get(naam, [])

    def sleutelveld(self, tabel):
        return SLEUTEL.get(tabel, tabel + "_code")

    def idx(self, tabel):
        if tabel not in self._idx:
            sl = self.sleutelveld(tabel)
            self._idx[tabel] = {str(r[sl]): r for r in self.tab(tabel) if r.get(sl) is not None}
        return self._idx[tabel]

    def rec(self, tabel, code):
        if code is None:
            return None
        return self.idx(tabel).get(str(code))

    def naam(self, tabel, code):
        r = self.rec(tabel, code)
        if not r:
            return str(code)
        for veld in ("naam", "naam_kort", "naam_officieel", "titel", "vraagtekst"):
            if r.get(veld):
                return r[veld]
        return str(code)

    def bij(self, tabel, veld, code):
        """Alle records van een koppeltabel bij één sleutelwaarde."""
        pot = (tabel, veld)
        if pot not in self._grp:
            groepen = {}
            for r in self.tab(tabel):
                if r.get(veld) is not None:
                    groepen.setdefault(str(r[veld]), []).append(r)
            self._grp[pot] = groepen
        return self._grp[pot].get(str(code), [])

    # -- afgeleid -------------------------------------------------------
    @staticmethod
    def sorteer(lijst):
        def sleutel(r):
            so = r.get("sort_order")
            try:
                so = int(so)
            except (TypeError, ValueError):
                so = 9999
            return (so, str(r.get("naam") or r.get("titel") or ""))
        return sorted(lijst, key=sleutel)

    def fasen_op_rij(self):
        """De 12 procesfasen in modelvolgorde, portefeuille eerst."""
        rij = []
        for n in self.sorteer(self.tab("procesniveau")):
            for f in self.sorteer(self.tab("procesfase")):
                if f.get("procesniveau_id") == n["code"]:
                    rij.append(f)
        return rij
