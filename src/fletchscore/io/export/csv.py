"""Export CSV du classement (résultats complets ou podiums).

Format brut de secours -- voir docs/cahier-des-charges/modele-donnees.rst
§6.2. Fonctions pures sur un classement déjà calculé (voir
``services.classement_epreuve``), sans dépendance au stockage.
"""

from __future__ import annotations

import csv
from typing import TextIO

from fletchscore.scoring import LigneClassement

_ENTETE = ["categorie", "rang", "id_federal", "nom", "prenom", "total", "nombre_x"]


def _ouvrir_ecriture(destination: str | TextIO) -> TextIO:
    if isinstance(destination, str):
        return open(destination, "w", newline="", encoding="utf-8")
    return destination


def exporter_classement_csv(
    classement: dict[str, list[LigneClassement]], destination: str | TextIO
) -> None:
    """Écrit le classement complet, une ligne par compétiteur classé,
    catégories triées alphabétiquement puis par rang -- ordre stable et
    reproductible, pas l'ordre d'insertion du dict."""
    fichier = _ouvrir_ecriture(destination)
    try:
        redacteur = csv.writer(fichier)
        redacteur.writerow(_ENTETE)
        for categorie in sorted(classement):
            for ligne in classement[categorie]:
                _ecrire_ligne(redacteur, categorie, ligne)
    finally:
        if isinstance(destination, str):
            fichier.close()


def _ecrire_ligne(redacteur, categorie: str, ligne: LigneClassement) -> None:
    redacteur.writerow(
        [
            categorie,
            ligne.rang,
            ligne.competiteur.id_federal,
            ligne.competiteur.nom,
            ligne.competiteur.prenom,
            ligne.total,
            ligne.nombre_x,
        ]
    )
