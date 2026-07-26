"""Référentiel Style de tir.

Fermé par défaut, pré-rempli avec les 12 codes IFAA (voir
STYLES_IFAA) -- voir docs/cahier-des-charges/regles-metier.rst. Une
compétition/club peut ajouter des variantes FFTL locales via
storage, mais la base pré-remplie ne doit jamais être perdue à
l'import (voir seed_referentiel_styles dans storage/db.py).
"""

from dataclasses import dataclass


@dataclass(slots=True)
class Style:
    code: str
    libelle: str
    libelle_en: str = ""


STYLES_IFAA: list[Style] = [
    Style("BB-R", "Barebow Recurve", "Barebow Recurve"),
    Style("BB-C", "Barebow Compound", "Barebow Compound"),
    Style("FS-R", "Freestyle Limited Recurve", "Freestyle Limited Recurve"),
    Style("FS-C", "Freestyle Limited Compound", "Freestyle Limited Compound"),
    Style("FU", "Freestyle Unlimited", "Freestyle Unlimited"),
    Style("BH-R", "Bowhunter Recurve", "Bowhunter Recurve"),
    Style("BH-C", "Bowhunter Compound", "Bowhunter Compound"),
    Style("BL", "Bowhunter Limited", "Bowhunter Limited"),
    Style("BU", "Bowhunter Unlimited", "Bowhunter Unlimited"),
    Style("LB", "Longbow", "Longbow"),
    Style("HB", "Historical Bow", "Historical Bow"),
    Style("TR", "Traditional Recurve", "Traditional Recurve"),
]
