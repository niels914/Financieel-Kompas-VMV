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

De uitkleedlogica zelf staat in kompasdata.py, omdat bouw-site.py die ook
gebruikt.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kompasdata as K  # noqa: E402

DOEL = os.path.join(K.WORTEL, "archetypen-datamodel.html")


def injecteer(data):
    js = K.compact(data)
    with open(DOEL, encoding="utf-8") as fh:
        html = fh.read()
    patroon = re.compile(
        r'(<script id="kompasdata" type="application/json">).*?(</script>)',
        re.S)
    if not patroon.search(html):
        sys.exit('FOUT: blok <script id="kompasdata"> niet gevonden in %s' % DOEL)
    veilig = js.replace("\\", "\\\\").replace("</", "<\\/")
    nieuw = patroon.sub(lambda m: m.group(1) + veilig + m.group(2), html, count=1)
    with open(DOEL, "w", encoding="utf-8") as fh:
        fh.write(nieuw)
    return len(js.encode("utf-8"))


def main():
    ruw = K.lees_bron()
    print("bron        : %s (v%s, %s)"
          % (os.path.basename(K.BRON), ruw["_meta"]["versie"].lstrip("v"),
             ruw["_meta"]["datum"]))
    data = K.kleed_uit(ruw, K.TABELLEN_ARCHETYPEN)
    print("tabellen    : %d" % len(data))
    print("records     : %d" % sum(len(v) for v in data.values()))
    print("compact     : %.1f kB" % (len(K.compact(data).encode()) / 1024))

    gecontroleerd, fouten = K.controleer(data)
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
