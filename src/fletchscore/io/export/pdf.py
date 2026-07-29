"""Export PDF du classement -- tableau par catégorie, une page continue.

Utilise fpdf2 (voir pyproject.toml) -- choisi pour rester pur Python
(pas de dépendance C, plus sûr sur Pydroid/Android) et pour la
simplicité de l'API sur un besoin volontairement simple : un tableau,
pas une mise en page élaborée.

⚠️ Non exécuté dans l'environnement de développement : fpdf2 n'est pas
installable ici (pas d'accès réseau). Le code est écrit avec soin à
partir de l'API connue de fpdf2, mais n'a pas pu être vérifié par un
vrai test -- à confirmer par la CI ou en le lançant côté utilisateur
(voir CLAUDE.md).
"""

from __future__ import annotations

from typing import BinaryIO

from fpdf import FPDF

from fletchscore.scoring import LigneClassement

_LARGEURS_COLONNES = (20, 90, 25, 20)  # rang, nom, total, X (mm)
_ENTETES_COLONNES = ("Rang", "Nom", "Total", "X")


def exporter_classement_pdf(
    classement: dict[str, list[LigneClassement]],
    destination: str | BinaryIO,
    titre: str = "Classement",
) -> None:
    """Écrit le classement en PDF, un tableau par catégorie (triées
    alphabétiquement), dans l'ordre de rang déjà calculé par
    ``scoring.classement_par_categorie``."""
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, titre, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    if not classement:
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 8, "Aucun compétiteur classé.", new_x="LMARGIN", new_y="NEXT")
    else:
        for categorie in sorted(classement):
            _ecrire_categorie(pdf, categorie, classement[categorie])

    _ecrire_sortie(pdf, destination)


def _ecrire_categorie(pdf: FPDF, categorie: str, lignes: list[LigneClassement]) -> None:
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 9, categorie, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 10)
    for largeur, entete in zip(_LARGEURS_COLONNES, _ENTETES_COLONNES):
        pdf.cell(largeur, 7, entete, border=1)
    pdf.ln()

    pdf.set_font("Helvetica", "", 10)
    for ligne in lignes:
        _ecrire_ligne(pdf, ligne)

    pdf.ln(5)


def _ecrire_ligne(pdf: FPDF, ligne: LigneClassement) -> None:
    valeurs = (
        str(ligne.rang),
        f"{ligne.competiteur.prenom} {ligne.competiteur.nom}",
        str(ligne.total),
        str(ligne.nombre_x) if ligne.nombre_x else "",
    )
    for largeur, valeur in zip(_LARGEURS_COLONNES, valeurs):
        pdf.cell(largeur, 7, valeur, border=1)
    pdf.ln()


def _ecrire_sortie(pdf: FPDF, destination: str | BinaryIO) -> None:
    if isinstance(destination, str):
        pdf.output(destination)
    else:
        # pdf.output() sans argument retourne le document en bytearray
        # (fpdf2 >= 2.7) -- écrit directement dans le flux binaire fourni,
        # plutôt que de forcer un chemin de fichier réel (utile pour les
        # tests, ou un export vers un flux HTTP plus tard).
        destination.write(bytes(pdf.output()))
