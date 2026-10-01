#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genereert het conceptuele kompasbeeld voor het VMV Financieel Vastgoedkompas.

Levert drie SVG's in beeld/:
  kompas-cover.svg          voorplaat 16:9 met titel en kernvraag
  kompas-cover-blanco.svg   zelfde compositie, zonder tekstblok
  kompas-embleem.svg        alleen de kompasroos, vierkant

Geen externe afhankelijkheden. Pas de constanten hieronder aan om kleur,
tekst of maatvoering te wijzigen; daarna opnieuw draaien.
"""

import math
import os

# ---------------------------------------------------------------- kleuren
# Exact gelijk aan de tokens in index.html en navigatieconcepten.html.
TEAL        = "#4bb3b8"
TEAL_DONKER = "#168b94"
MINT        = "#ecf7f4"
PAARS       = "#3b2943"
PAARS_MID   = "#65506f"
GRIJS_50    = "#fafbfb"
GRIJS_200   = "#dce1e2"
GRIJS_400   = "#9aa4a6"
WIT         = "#ffffff"

# Rolkleuren uit archetype C2.
ROLKLEUREN = ["#0f6fa8", "#12a3a0", "#e2833c", "#9462a6", "#3e9b62"]

FONT = 'Aptos, &quot;Segoe UI&quot;, Arial, Helvetica, sans-serif'

# ------------------------------------------------------------- maatvoering
HUB_R      = 60      # straal middencirkel
MAJOR_TIP  = 244     # punt van de vier hoofdrichtingen
MAJOR_BAS  = 56
MAJOR_HW   = 46
MINOR_TIP  = 148     # punt van de vier tussenrichtingen
MINOR_BAS  = 46
MINOR_HW   = 34
ROL_RADII  = [276, 287, 298, 309, 320]
RING_R     = 368     # fasering en de vier chips
HALO_R     = 490

# De vier ingangen van het kompas, met hun hoek in graden (0 = oost).
INGANGEN = [
    (-90, "Opgave",     "wat speelt er"),
    (0,   "Rol",        "wie ben jij"),
    (90,  "Moment",     "waar in het proces"),
    (180, "Instrument", "wat helpt"),
]

# Roltrajecten: (kleur-index, starthoek, eindhoek) - elk een ander stuk
# van de cyclus, zodat zichtbaar wordt dat rollen verschillende delen lopen.
ROLBOGEN = [
    (0, -100, 20),
    (1, -30, 90),
    (2, 40, 160),
    (3, 110, 230),
    (4, 180, 300),
]


# ------------------------------------------------------------- hulpmiddelen
def pol(cx, cy, r, graden):
    t = math.radians(graden)
    return cx + r * math.cos(t), cy + r * math.sin(t)


def f(x):
    return ("%.2f" % x).rstrip("0").rstrip(".")


def boogpad(cx, cy, r, start, eind):
    """Pad voor een cirkelboog, met de klok mee van start- naar eindhoek."""
    x1, y1 = pol(cx, cy, r, start)
    x2, y2 = pol(cx, cy, r, eind)
    groot = 1 if (eind - start) % 360 > 180 else 0
    return "M%s %s A%s %s 0 %d 1 %s %s" % (f(x1), f(y1), f(r), f(r), groot, f(x2), f(y2))


def facetpunt(cx, cy, hoek, tip_r, basis_r, hw, links, rechts):
    """Eén kompaspunt: twee facetten die op de as samenkomen."""
    t = math.radians(hoek)
    ux, uy = math.cos(t), math.sin(t)
    px, py = -uy, ux
    tx, ty = cx + tip_r * ux, cy + tip_r * uy
    mx, my = cx + basis_r * ux, cy + basis_r * uy
    lx, ly = mx + hw * px, my + hw * py
    rx, ry = mx - hw * px, my - hw * py
    return (
        '<path d="M%s %s L%s %s L%s %s Z" fill="%s"/>'
        '<path d="M%s %s L%s %s L%s %s Z" fill="%s"/>'
        % (f(tx), f(ty), f(lx), f(ly), f(cx), f(cy), links,
           f(tx), f(ty), f(cx), f(cy), f(rx), f(ry), rechts)
    )


def zeshoek(cx, cy, r, kleur, dikte=2, opacity=0.6):
    punten = []
    for i in range(6):
        x, y = pol(cx, cy, r, -90 + i * 60)
        punten.append("%s,%s" % (f(x), f(y)))
    return ('<polygon points="%s" fill="none" stroke="%s" stroke-width="%s" '
            'opacity="%s"/>' % (" ".join(punten), kleur, dikte, opacity))


def breedte(tekst, grootte, vet=False):
    """Ruwe tekstbreedte; genoeg om chips op maat te maken."""
    factor = 0.58 if vet else 0.52
    return len(tekst) * grootte * factor


# ------------------------------------------------------------- onderdelen
def achtergrond(breed, hoog, cx, cy, met_zeshoeken=True):
    d = ['<rect width="%d" height="%d" fill="%s"/>' % (breed, hoog, GRIJS_50)]
    d.append('<circle cx="%s" cy="%s" r="%d" fill="%s" opacity="0.5"/>'
             % (f(cx), f(cy), HALO_R, MINT))
    d.append('<circle cx="%s" cy="%s" r="%d" fill="none" stroke="%s" '
             'stroke-width="1.5" stroke-dasharray="2 10" opacity="0.45"/>'
             % (f(cx), f(cy), HALO_R, TEAL))
    if met_zeshoeken:
        d.append(zeshoek(236, hoog - 150, 74, GRIJS_200, 2, 0.4))
        d.append(zeshoek(cx + 430, 148, 46, TEAL, 2, 0.3))
        d.append(zeshoek(150, 196, 34, GRIJS_200, 2, 0.45))
    return "\n  ".join(d)


def kompasroos(cx, cy):
    d = []

    # Fasering: negen boogsegmenten met tussenruimte.
    for i in range(9):
        start = -90 + i * 40 + 4
        eind = -90 + (i + 1) * 40 - 4
        d.append('<path d="%s" fill="none" stroke="%s" stroke-width="6" '
                 'stroke-linecap="round"/>'
                 % (boogpad(cx, cy, RING_R, start, eind), GRIJS_200))
    for i in range(9):
        x, y = pol(cx, cy, RING_R, -90 + i * 40)
        d.append('<circle cx="%s" cy="%s" r="4" fill="%s"/>' % (f(x), f(y), GRIJS_400))

    # Roltrajecten: elk een ander deel van de cyclus.
    for idx, start, eind in ROLBOGEN:
        r = ROL_RADII[idx]
        kleur = ROLKLEUREN[idx]
        d.append('<path d="%s" fill="none" stroke="%s" stroke-width="4.5" '
                 'stroke-linecap="round" opacity="0.9"/>'
                 % (boogpad(cx, cy, r, start, eind), kleur))
        x, y = pol(cx, cy, r, start)
        d.append('<circle cx="%s" cy="%s" r="6.5" fill="%s"/>' % (f(x), f(y), kleur))

    # De roos: eerst de tussenrichtingen, dan de hoofdrichtingen.
    for hoek in (-45, 45, 135, 225):
        d.append(facetpunt(cx, cy, hoek, MINOR_TIP, MINOR_BAS, MINOR_HW,
                           TEAL_DONKER, TEAL))
    for hoek in (-90, 0, 90, 180):
        d.append(facetpunt(cx, cy, hoek, MAJOR_TIP, MAJOR_BAS, MAJOR_HW,
                           PAARS, PAARS_MID))

    # Naaf met daarin een daklijn: het gaat om vastgoed.
    d.append('<circle cx="%s" cy="%s" r="%d" fill="%s" stroke="%s" '
             'stroke-width="4"/>' % (f(cx), f(cy), HUB_R, WIT, TEAL_DONKER))
    d.append('<g transform="translate(%s %s)" fill="none" stroke="%s" '
             'stroke-width="3.4" stroke-linejoin="round" stroke-linecap="round">'
             '<path d="M-24 8 L-24 -3 L-9 -14 L6 -3 L6 8"/>'
             '<path d="M9 8 L9 -2 L23 -2 L23 8"/>'
             '<path d="M-29 8 H28"/>'
             '</g>' % (f(cx), f(cy + 2), TEAL_DONKER))

    return "\n  ".join(d)


def ingangen(cx, cy):
    """De vier ingangen als chips op de ring. Het witte vlak maskeert de
    ring en de rolbogen erachter, zodat de tekst altijd vrij staat."""
    d = []
    for hoek, naam, onder in INGANGEN:
        x, y = pol(cx, cy, RING_R, hoek)
        w = max(breedte(naam, 27, vet=True), breedte(onder, 17)) + 46
        h = 76
        d.append('<rect x="%s" y="%s" width="%s" height="%d" rx="38" '
                 'fill="%s" stroke="%s" stroke-width="2"/>'
                 % (f(x - w / 2), f(y - h / 2), f(w), h, WIT, GRIJS_200))
        d.append('<text x="%s" y="%s" text-anchor="middle" font-family="%s" '
                 'font-size="27" font-weight="600" fill="%s">%s</text>'
                 % (f(x), f(y - 2), FONT, PAARS, naam))
        d.append('<text x="%s" y="%s" text-anchor="middle" font-family="%s" '
                 'font-size="17" fill="%s">%s</text>'
                 % (f(x), f(y + 22), FONT, GRIJS_400, onder))
    return "\n  ".join(d)


def tekstblok():
    x = 140
    regels = [
        "Welke informatie heeft welke rol nodig om",
        "op het juiste moment een goede financiële",
        "keuze te maken?",
    ]
    d = ['<text x="%d" y="378" font-family="%s" font-size="21" '
         'font-weight="700" letter-spacing="3.2" fill="%s">'
         'VERDUURZAMING MAATSCHAPPELIJK VASTGOED</text>' % (x, FONT, TEAL_DONKER)]
    d.append('<text x="%d" y="468" font-family="%s" font-size="80" '
             'font-weight="600" fill="%s">Financieel</text>' % (x, FONT, PAARS))
    d.append('<text x="%d" y="556" font-family="%s" font-size="80" '
             'font-weight="600" fill="%s">Vastgoedkompas</text>' % (x, FONT, PAARS))
    d.append('<path d="M%d 604 H%d" stroke="%s" stroke-width="4" '
             'stroke-linecap="round"/>' % (x, x + 84, TEAL))
    for i, regel in enumerate(regels):
        d.append('<text x="%d" y="%d" font-family="%s" font-size="28" '
                 'fill="%s">%s</text>' % (x, 668 + i * 38, FONT, PAARS_MID, regel))
    return "\n  ".join(d)


# ------------------------------------------------------------- documenten
def omhul(breed, hoog, inhoud, titel):
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" '
        'width="%d" height="%d" role="img" aria-label="%s">\n'
        '  <title>%s</title>\n  %s\n</svg>\n'
        % (breed, hoog, breed, hoog, titel, titel, inhoud)
    )


def cover(met_tekst=True):
    cx, cy = 1340, 540
    delen = [achtergrond(1920, 1080, cx, cy),
             kompasroos(cx, cy),
             ingangen(cx, cy)]
    if met_tekst:
        delen.append(tekstblok())
    label = ("Kompasroos met vier ingangen: opgave, rol, moment en instrument, "
             "omringd door de negen fasen van de vastgoedcyclus")
    return omhul(1920, 1080, "\n  ".join(delen), label)


def embleem():
    cx, cy = 540, 540
    delen = [achtergrond(1080, 1080, cx, cy, met_zeshoeken=False),
             kompasroos(cx, cy),
             ingangen(cx, cy)]
    return omhul(1080, 1080, "\n  ".join(delen),
                 "Kompasroos met de vier ingangen van het Financieel Vastgoedkompas")


def main():
    hier = os.path.dirname(os.path.abspath(__file__))
    uit = os.path.join(os.path.dirname(hier), "beeld")
    os.makedirs(uit, exist_ok=True)
    bestanden = {
        "kompas-cover.svg": cover(True),
        "kompas-cover-blanco.svg": cover(False),
        "kompas-embleem.svg": embleem(),
    }
    for naam, inhoud in bestanden.items():
        pad = os.path.join(uit, naam)
        with open(pad, "w", encoding="utf-8") as fh:
            fh.write(inhoud)
        print("geschreven: %s (%d bytes)" % (naam, len(inhoud.encode("utf-8"))))


if __name__ == "__main__":
    main()
