"""Classement par catégorie et départage au X.

Fonctions pures : reçoivent des objets déjà chargés (Competiteur, Score),
sans dépendance au stockage ni à la GUI -- voir
docs/cahier-des-charges/architecture.rst.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from fletchscore.models import Bareme, Competiteur, Score, StatutScore


def total_scores(score: Score | None) -> tuple[int, int]:
    """Total de points et nombre de X, en ne comptant QUE si le score est
    validé -- une proposition en attente ne doit jamais influencer un
    classement officiel (voir docs/cahier-des-charges/securite.rst §7.2).
    Un compétiteur sans score saisi (``None``) compte pour 0."""
    if score is None or score.statut != StatutScore.VALIDE:
        return 0, 0
    return score.total, score.nombre_x


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
    entrees: list[tuple[Competiteur, Score | None]],
    *,
    categories_veteran_actives: bool = False,
) -> dict[str, list[LigneClassement]]:
    """Construit le classement, groupé par code de catégorie combiné
    (ex. ``AMBB-R``), trié par total décroissant puis, si le barème
    utilise un départage au X (``bareme.departage_par_x``), par nombre de
    X décroissant.

    ``entrees`` associe chaque compétiteur à son score final (au plus un
    par inscription -- voir models/score.py) ou ``None`` s'il n'a pas
    encore été saisi.
    """
    par_categorie: dict[str, list[LigneClassement]] = {}

    for competiteur, score in entrees:
        total, nombre_x = total_scores(score)
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
            lignes.sort(key=lambda ligne: (-ligne.total, -ligne.nombre_x))
        else:
            lignes.sort(key=lambda ligne: -ligne.total)
        _attribuer_rangs(lignes, depart_par_x=bareme.departage_par_x)

    return par_categorie


def podium_par_categorie(
    classement: dict[str, list[LigneClassement]], taille: int = 3
) -> dict[str, list[LigneClassement]]:
    """Extrait le podium (par défaut top 3) de chaque catégorie d'un
    classement déjà calculé.

    Filtre sur le *rang* (``ligne.rang <= taille``), pas sur la position
    dans la liste : si deux personnes sont ex-aequo au rang 1, les DEUX
    sont sur le podium, comme au rang 2 il n'y en aura donc aucune --
    cohérent avec la convention 1, 2, 2, 4 déjà utilisée pour l'attribution
    des rangs. Une catégorie avec moins de compétiteurs que ``taille``
    retourne simplement tout le monde.
    """
    return {
        categorie: [ligne for ligne in lignes if ligne.rang <= taille]
        for categorie, lignes in classement.items()
    }


def _attribuer_rangs(lignes: list[LigneClassement], *, depart_par_x: bool) -> None:
    rang_courant = 0
    precedent: tuple[int, int] | None = None
    for position, ligne in enumerate(lignes, start=1):
        cle = (ligne.total, ligne.nombre_x if depart_par_x else 0)
        if cle != precedent:
            rang_courant = position
            precedent = cle
        ligne.rang = rang_courant


@dataclass(slots=True)
class LigneClassementGlobal:
    competiteur: Competiteur
    code_categorie: str
    totaux_par_epreuve: dict[str, int]
    """Total de chaque épreuve, indexé par ``epreuve_id`` -- 0 si le
    compétiteur n'y était pas inscrit ou n'y a pas de score validé."""
    total_global: int
    nombre_x_global: int
    rang: int = 0
    """Rang au sein de sa catégorie, sur le total global uniquement --
    voir :func:`classement_global`."""


def classement_global(
    date_reference: date,
    epreuve_ids: list[str],
    entrees: list[tuple[Competiteur, dict[str, Score | None]]],
    *,
    categories_veteran_actives: bool = False,
) -> dict[str, list[LigneClassementGlobal]]:
    """Classement cumulé sur plusieurs épreuves d'une même compétition --
    un total par épreuve, plus un total global qui sert seul de critère
    de tri.

    Volontairement pas de départage au X ici : les épreuves d'une même
    compétition peuvent utiliser des barèmes différents (certains avec
    zone X, d'autres non), un critère uniforme n'aurait pas de sens
    garanti -- contrairement à :func:`classement_par_categorie`, qui
    connaît le barème d'une seule épreuve et peut s'y fier.

    ``entrees`` associe chaque compétiteur à un dict {epreuve_id: Score
    ou None} -- une entrée manquante pour une épreuve compte pour 0,
    pas une erreur (un compétiteur peut ne pas être inscrit à toutes les
    épreuves de la compétition).
    """
    par_categorie: dict[str, list[LigneClassementGlobal]] = {}

    for competiteur, scores_par_epreuve in entrees:
        totaux: dict[str, int] = {}
        total_global = 0
        nombre_x_global = 0
        for epreuve_id in epreuve_ids:
            total, nombre_x = total_scores(scores_par_epreuve.get(epreuve_id))
            totaux[epreuve_id] = total
            total_global += total
            nombre_x_global += nombre_x

        code_categorie = competiteur.code_categorie(
            date_reference, categories_veteran_actives=categories_veteran_actives
        )
        ligne = LigneClassementGlobal(
            competiteur=competiteur,
            code_categorie=code_categorie,
            totaux_par_epreuve=totaux,
            total_global=total_global,
            nombre_x_global=nombre_x_global,
        )
        par_categorie.setdefault(code_categorie, []).append(ligne)

    for lignes in par_categorie.values():
        lignes.sort(key=lambda ligne: -ligne.total_global)
        _attribuer_rangs_global(lignes)

    return par_categorie


def _attribuer_rangs_global(lignes: list[LigneClassementGlobal]) -> None:
    rang_courant = 0
    precedent: int | None = None
    for position, ligne in enumerate(lignes, start=1):
        if ligne.total_global != precedent:
            rang_courant = position
            precedent = ligne.total_global
        ligne.rang = rang_courant
