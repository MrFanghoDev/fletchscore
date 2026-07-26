"""Classement par catégorie et départage au X.

Fonctions pures : reçoivent des objets déjà chargés (Competiteur, Score),
sans dépendance au stockage ni à la GUI -- voir
docs/cahier-des-charges/architecture.rst.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from fletchscore.models import Bareme, Competiteur, Score, StatutScore


def total_scores(scores: list[Score]) -> tuple[int, int]:
    """Total de points et nombre de X, en ne comptant QUE les scores
    validés -- une proposition en attente ne doit jamais influencer un
    classement officiel (voir
    docs/cahier-des-charges/securite.rst §7.2)."""
    valides = [s for s in scores if s.statut == StatutScore.VALIDE]
    total = sum(s.total for s in valides)
    nombre_x = sum(s.nombre_x for s in valides)
    return total, nombre_x


@dataclass(slots=True)
class LigneClassement:
    competiteur: Competiteur
    code_categorie: str
    total: int
    nombre_x: int
    rang: int = 0
    """Rang au sein de sa catégorie -- calculé par
    :func:`classement_par_categorie`, pas par l'appelant. Deux
    compétiteurs à égalité totale (et à égalité de X si le barème en tient
    compte) partagent le même rang ; le rang suivant saute en conséquence
    (1, 2, 2, 4 -- convention sportive standard). Une égalité qui subsiste
    à ce stade doit être départagée sous supervision de l'organisateur,
    voir docs/cahier-des-charges/regles-metier.rst §4.3 -- ce module
    n'invente pas de critère supplémentaire."""


def classement_par_categorie(
    bareme: Bareme,
    date_reference: date,
    entrees: list[tuple[Competiteur, list[Score]]],
    *,
    categories_veteran_actives: bool = False,
) -> dict[str, list[LigneClassement]]:
    """Construit le classement, groupé par code de catégorie combiné
    (ex. ``AMBB-R``), trié par total décroissant puis, si le barème
    utilise un départage au X (``bareme.departage_par_x``), par nombre de
    X décroissant."""
    par_categorie: dict[str, list[LigneClassement]] = {}

    for competiteur, scores in entrees:
        total, nombre_x = total_scores(scores)
        code_categorie = competiteur.code_categorie(
            date_reference, categories_veteran_actives=categories_veteran_actives
        )
        ligne = LigneClassement(
            competiteur=competiteur,
            code_categorie=code_categorie,
            total=total,
            nombre_x=nombre_x,
        )
        par_categorie.setdefault(code_categorie, []).append(ligne)

    for lignes in par_categorie.values():
        if bareme.departage_par_x:
            lignes.sort(key=lambda l: (-l.total, -l.nombre_x))
        else:
            lignes.sort(key=lambda l: -l.total)
        _attribuer_rangs(lignes, depart_par_x=bareme.departage_par_x)

    return par_categorie


def _attribuer_rangs(lignes: list[LigneClassement], *, depart_par_x: bool) -> None:
    rang_courant = 0
    precedent: tuple[int, int] | None = None
    for position, ligne in enumerate(lignes, start=1):
        cle = (ligne.total, ligne.nombre_x if depart_par_x else 0)
        if cle != precedent:
            rang_courant = position
            precedent = cle
        ligne.rang = rang_courant
