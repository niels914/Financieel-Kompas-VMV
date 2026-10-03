#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vult het databok van archetypen-datamodel.html met een uitgeklede versie
van het datamodel.

  python3 scripts/ververs-datamodel.py              uitkleden en injecteren
  python3 scripts/ververs-datamodel.py --controleer alleen de data nakijken

De HTML blijft de bron van waarheid voor code en vormgeving; dit script
raakt uitsluitend het blok <script id="kompasdata"> aan. Een modelupdate
is dus: nieuwe JSON in data/, dit script draaien.
"""

import json
import os
import re
import sys

UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

HIER = os.path.dirname(os.path.abspath(__file__))
WORTEL = os.path.dirname(HIER)
BRON = os.path.join(WORTEL, "data", "kompas_dummy_data.json")
DOEL = os.path.join(WORTEL, "archetypen-datamodel.html")

# Beheervelden die het prototype niet gebruikt.
BEHEER = {
    "created_at", "created_by", "updated_at", "updated_by",
    "record_status", "version_number", "notes_internal",
}

# Velden die we per tabel extra weglaten (duplicaat of onbruikbaar).
EXTRA_WEG = {
    "instrument": {"uitgebreide_omschrijving"},
}

# De tabellen die de drie archetypen nodig hebben. De beheerdomeinen
# (validatie, wijzigingslog, reviewplanning, ontwikkelactie) blijven eruit.
TABELLEN = [
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
}


def lees_bron():
    with open(BRON, encoding="utf-8") as fh:
        return json.load(fh)


def kleed_uit(ruw):
    tabellen = ruw["tabellen"]
    uit = {}
    for naam in TABELLEN:
        if naam not in tabellen:
            print("  waarschuwing: tabel %s ontbreekt in de bron" % naam)
            continue
        weg = BEHEER | EXTRA_WEG.get(naam, set())
        schoon = []
        for rec in tabellen[naam]["records"]:
            o = {}
            for k, v in rec.items():
                if k in weg or v in (None, ""):
                    continue
                # Alle UUID-waarden vallen weg: het model verwijst op
                # leesbare codes, UUID's staan alleen in primaire sleutels.
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
                doel = VERWIJZINGEN.get(veld)
                if not doel or doel not in sleutels:
                    continue
                gecontroleerd += 1
                if str(waarde) not in sleutels[doel]:
                    fouten.append("%s[%d].%s = %r wijst niet naar %s"
                                  % (tabel, i, veld, waarde, doel))
    return gecontroleerd, fouten


def injecteer(data):
    js = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    with open(DOEL, encoding="utf-8") as fh:
        html = fh.read()
    patroon = re.compile(
        r'(<script id="kompasdata" type="application/json">).*?(</script>)',
        re.S)
    if not patroon.search(html):
        sys.exit("FOUT: blok <script id=\"kompasdata\"> niet gevonden in %s" % DOEL)
    nieuw = patroon.sub(lambda m: m.group(1) + js.replace("\\", "\\\\").replace("</", "<\\/") + m.group(2), html, count=1)
    with open(DOEL, "w", encoding="utf-8") as fh:
        fh.write(nieuw)
    return len(js.encode("utf-8"))


def main():
    ruw = lees_bron()
    print("bron        : %s (v%s, %s)"
          % (os.path.basename(BRON), ruw["_meta"]["versie"].lstrip("v"), ruw["_meta"]["datum"]))
    data = kleed_uit(ruw)
    totaal = sum(len(v) for v in data.values())
    compact = len(json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode())
    print("tabellen    : %d" % len(data))
    print("records     : %d" % totaal)
    print("compact     : %.1f kB" % (compact / 1024))

    gecontroleerd, fouten = controleer(data)
    print("verwijzingen: %d gecontroleerd" % gecontroleerd)
    if fouten:
        print("GEBROKEN VERWIJZINGEN: %d" % len(fouten))
        for f in fouten[:25]:
            print("   " + f)
        if len(fouten) > 25:
            print("   ... en nog %d" % (len(fouten) - 25))
    else:
        print("              alle verwijzingen kloppen")

    if "--controleer" in sys.argv:
        return 1 if fouten else 0

    n = injecteer(data)
    print("geschreven  : %s (databok %.1f kB)" % (os.path.basename(DOEL), n / 1024))
    return 1 if fouten else 0


if __name__ == "__main__":
    sys.exit(main())
