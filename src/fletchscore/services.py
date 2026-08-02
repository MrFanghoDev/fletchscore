"""Couche service -- cas d'usage de l'organisateur.

Fait le lien entre le stockage (storage/), les règles (scoring/) et
l'interface (gui/). Volontairement séparée des widgets : la GUI ne
contient que de l'affichage et des appels à ces fonctions, ce qui rend
tout le comportement testable sans affichage Tkinter (voir CLAUDE.md --
la GUI réelle n'est pas vérifiable dans l'environnement de dev).

Génère les identifiants (uuid4) plutôt que de les demander à
l'appelant : la GUI n'a pas à s'en préoccuper.
"""

from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from datetime import date

from fletchscore.models import (
    Club,
    Competiteur,
    Competition,
    Epreuve,
    EpreuveTemplate,
    Inscription,
    Score,
    Sexe,
    StatutCompetition,
    StatutScore,
)
from fletchscore.scoring import classement_par_categorie
from fletchscore.scoring.classement import LigneClassement
from fletchscore.storage import db


class ErreurMetier(Exception):
    """Erreur attendue, à afficher telle quelle à l'organisateur.

    Distincte d'une exception technique (sqlite3.Error, etc.) : le
    message est rédigé pour être lu par un bénévole, pas par un
    développeur.
    """


def _nouvel_id() -> str:
    return str(uuid.uuid4())


def parser_date(texte: str, nom_champ: str) -> date:
    """Convertit un champ de saisie AAAA-MM-JJ en date.

    Utilitaire partagé par les écrans GUI (qui ne manipulent que du
    texte saisi) -- vit ici plutôt que dans un module ``gui/`` pour
    rester testable sans customtkinter.
    """
    try:
        return date.fromisoformat(texte.strip())
    except ValueError as erreur:
        raise ErreurMetier(
            f"{nom_champ} invalide : « {texte} » -- format attendu AAAA-MM-JJ"
        ) from erreur


def libelle_epreuve(competition: Competition, epreuve: Epreuve) -> str:
    """Libellé d'affichage d'une épreuve, avec sa compétition -- partagé
    par les écrans qui doivent choisir une épreuve parmi toutes celles de
    toutes les compétitions (saisie, classement)."""
    return f"{competition.nom} — {epreuve.nom} ({epreuve.date})"


def libelle_competiteur(competiteur: Competiteur) -> str:
    """Libellé d'affichage d'un compétiteur, id fédéral inclus pour
    distinguer deux personnes du même nom."""
    return f"{competiteur.prenom} {competiteur.nom} ({competiteur.id_federal})"


# ------------------------------------------------------------ Référentiels --


def creer_club(conn: sqlite3.Connection, code_club: str, nom: str, ville: str = "") -> Club:
    """Ajoute un club manuellement -- mêmes règles que l'import CSV
    (voir io/import_csv.py) : code et nom obligatoires, code déjà pris
    refusé plutôt qu'écrasé silencieusement."""
    code_club = code_club.strip()
    nom = nom.strip()
    if not code_club:
        raise ErreurMetier("Le code du club ne peut pas être vide.")
    if not nom:
        raise ErreurMetier("Le nom du club ne peut pas être vide.")
    if db.get_club(conn, code_club) is not None:
        raise ErreurMetier(f"Un club avec le code « {code_club} » existe déjà.")

    club = Club(code_club, nom, ville.strip())
    db.insert_club(conn, club)
    return club


def modifier_club(conn: sqlite3.Connection, code_club: str, nom: str, ville: str = "") -> Club:
    """Corrige un club existant -- ``code_club`` n'est volontairement
    pas modifiable (voir storage.update_club) : c'est la clé référencée
    par les fiches compétiteur, la changer casserait ces références."""
    if db.get_club(conn, code_club) is None:
        raise ErreurMetier(f"Club introuvable : {code_club}")
    if not nom.strip():
        raise ErreurMetier("Le nom du club ne peut pas être vide.")

    club = Club(code_club, nom.strip(), ville.strip())
    db.update_club(conn, club)
    return club


def creer_competiteur(
    conn: sqlite3.Connection,
    id_federal: str,
    nom: str,
    prenom: str,
    code_club: str,
    sexe: Sexe,
    date_naissance: date,
    code_style: str,
    licence_valide_jusqu_au: date | None = None,
) -> Competiteur:
    """Ajoute un compétiteur manuellement -- mêmes règles que l'import
    CSV : club et style doivent déjà exister dans leur référentiel
    (jamais créés à la volée), id fédéral déjà pris refusé plutôt
    qu'écrasé silencieusement (voir io/import_csv.py, même principe)."""
    id_federal = id_federal.strip()
    nom = nom.strip()
    prenom = prenom.strip()
    code_club = code_club.strip()
    code_style = code_style.strip()

    if not id_federal:
        raise ErreurMetier("L'id fédéral ne peut pas être vide.")
    if not nom:
        raise ErreurMetier("Le nom ne peut pas être vide.")
    if not prenom:
        raise ErreurMetier("Le prénom ne peut pas être vide.")
    if db.get_competiteur(conn, id_federal) is not None:
        raise ErreurMetier(f"Un compétiteur avec l'id fédéral « {id_federal} » existe déjà.")
    if db.get_club(conn, code_club) is None:
        raise ErreurMetier(f"Club inconnu : {code_club} -- crée-le d'abord.")
    if db.get_style(conn, code_style) is None:
        raise ErreurMetier(f"Style inconnu : {code_style}.")

    competiteur = Competiteur(
        id_federal=id_federal,
        nom=nom,
        prenom=prenom,
        code_club=code_club,
        sexe=sexe,
        date_naissance=date_naissance,
        code_style=code_style,
        licence_valide_jusqu_au=licence_valide_jusqu_au,
    )
    db.insert_competiteur(conn, competiteur)
    return competiteur


def modifier_competiteur(
    conn: sqlite3.Connection,
    id_federal: str,
    nom: str,
    prenom: str,
    code_club: str,
    sexe: Sexe,
    date_naissance: date,
    code_style: str,
    licence_valide_jusqu_au: date | None = None,
) -> Competiteur:
    """Corrige un compétiteur existant -- mêmes règles que
    ``creer_competiteur()``. ``id_federal`` n'est volontairement pas
    modifiable (voir storage.update_competiteur) : c'est l'identifiant
    fédéral, la clé de tout le reste (inscriptions, tokens...)."""
    if db.get_competiteur(conn, id_federal) is None:
        raise ErreurMetier(f"Compétiteur introuvable : {id_federal}")

    nom = nom.strip()
    prenom = prenom.strip()
    code_club = code_club.strip()
    code_style = code_style.strip()

    if not nom:
        raise ErreurMetier("Le nom ne peut pas être vide.")
    if not prenom:
        raise ErreurMetier("Le prénom ne peut pas être vide.")
    if db.get_club(conn, code_club) is None:
        raise ErreurMetier(f"Club inconnu : {code_club} -- crée-le d'abord.")
    if db.get_style(conn, code_style) is None:
        raise ErreurMetier(f"Style inconnu : {code_style}.")

    competiteur = Competiteur(
        id_federal=id_federal,
        nom=nom,
        prenom=prenom,
        code_club=code_club,
        sexe=sexe,
        date_naissance=date_naissance,
        code_style=code_style,
        licence_valide_jusqu_au=licence_valide_jusqu_au,
    )
    db.update_competiteur(conn, competiteur)
    return competiteur


# ------------------------------------------------------- Compétition --


def creer_competition(
    conn: sqlite3.Connection,
    nom: str,
    date_debut: date,
    date_fin: date,
    *,
    lieu: str = "",
    categories_veteran_actives: bool = False,
) -> Competition:
    if not nom.strip():
        raise ErreurMetier("Le nom de la compétition ne peut pas être vide.")
    if date_fin < date_debut:
        raise ErreurMetier("La date de fin ne peut pas précéder la date de début.")

    competition = Competition(
        id=_nouvel_id(),
        nom=nom.strip(),
        date_debut=date_debut,
        date_fin=date_fin,
        lieu=lieu.strip(),
        statut=StatutCompetition.OUVERTE,
        categories_veteran_actives=categories_veteran_actives,
    )
    db.insert_competition(conn, competition)
    return competition


def modifier_competition(
    conn: sqlite3.Connection,
    competition_id: str,
    nom: str,
    date_debut: date,
    date_fin: date,
    *,
    lieu: str = "",
    categories_veteran_actives: bool = False,
) -> Competition:
    """Corrige une compétition existante -- mêmes règles que
    ``creer_competition()``, plus une vérification propre à la
    modification : si la compétition a déjà des épreuves, retrécir les
    dates ne doit pas en laisser une hors des nouvelles bornes (le statut
    n'est volontairement pas modifiable ici -- clôturer une compétition
    est une action distincte, pas un simple champ à corriger)."""
    existante = db.get_competition(conn, competition_id)
    if existante is None:
        raise ErreurMetier("Compétition introuvable.")
    if not nom.strip():
        raise ErreurMetier("Le nom de la compétition ne peut pas être vide.")
    if date_fin < date_debut:
        raise ErreurMetier("La date de fin ne peut pas précéder la date de début.")

    for epreuve in db.list_epreuves_by_competition(conn, competition_id):
        if not (date_debut <= epreuve.date <= date_fin):
            raise ErreurMetier(
                f"Impossible : l'épreuve « {epreuve.nom} » du {epreuve.date} "
                "se retrouverait hors des nouvelles dates de la compétition "
                "-- corrige ou supprime d'abord cette épreuve."
            )

    modifiee = Competition(
        id=competition_id,
        nom=nom.strip(),
        date_debut=date_debut,
        date_fin=date_fin,
        lieu=lieu.strip(),
        statut=existante.statut,
        categories_veteran_actives=categories_veteran_actives,
    )
    db.update_competition(conn, modifiee)
    return modifiee


# ----------------------------------------------------------- Épreuve --


def creer_epreuve(
    conn: sqlite3.Connection,
    competition_id: str,
    nom: str,
    date_epreuve: date,
    bareme_id: str,
) -> Epreuve:
    competition = db.get_competition(conn, competition_id)
    if competition is None:
        raise ErreurMetier("Compétition introuvable.")
    if competition.statut == StatutCompetition.CLOTUREE:
        raise ErreurMetier("Cette compétition est clôturée -- impossible d'y ajouter une épreuve.")
    if not nom.strip():
        raise ErreurMetier("Le nom de l'épreuve ne peut pas être vide.")
    if db.get_bareme(conn, bareme_id) is None:
        raise ErreurMetier(f"Barème inconnu : {bareme_id}")
    if not competition.couvre(date_epreuve):
        raise ErreurMetier(
            "La date de l'épreuve est en dehors des dates de la compétition "
            f"({competition.date_debut} -- {competition.date_fin})."
        )

    epreuve = Epreuve(
        id=_nouvel_id(),
        competition_id=competition_id,
        nom=nom.strip(),
        date=date_epreuve,
        bareme_id=bareme_id,
    )
    db.insert_epreuve(conn, epreuve)
    return epreuve


def modifier_epreuve(
    conn: sqlite3.Connection,
    epreuve_id: str,
    nom: str,
    date_epreuve: date,
    bareme_id: str,
) -> Epreuve:
    """Corrige une épreuve existante -- mêmes règles que
    ``creer_epreuve()``. Le barème ne peut plus être changé une fois une
    volée saisie (voir ``storage.epreuve_a_des_scores``) : les numéros de
    série/volée déjà enregistrés ne correspondraient plus forcément au
    nouveau barème (nombre de séries, de volées, de flèches différent)."""
    existante = db.get_epreuve(conn, epreuve_id)
    if existante is None:
        raise ErreurMetier("Épreuve introuvable.")

    competition = db.get_competition(conn, existante.competition_id)
    if competition is None:
        raise ErreurMetier("Compétition introuvable.")
    if competition.statut == StatutCompetition.CLOTUREE:
        raise ErreurMetier(
            "Cette compétition est clôturée -- impossible d'en modifier une épreuve."
        )
    if not nom.strip():
        raise ErreurMetier("Le nom de l'épreuve ne peut pas être vide.")
    if db.get_bareme(conn, bareme_id) is None:
        raise ErreurMetier(f"Barème inconnu : {bareme_id}")
    if not competition.couvre(date_epreuve):
        raise ErreurMetier(
            "La date de l'épreuve est en dehors des dates de la compétition "
            f"({competition.date_debut} -- {competition.date_fin})."
        )
    if bareme_id != existante.bareme_id and db.epreuve_a_des_scores(conn, epreuve_id):
        raise ErreurMetier(
            "Impossible de changer le barème : des scores ont déjà été "
            "saisis pour cette épreuve."
        )

    modifiee = Epreuve(
        id=epreuve_id,
        competition_id=existante.competition_id,
        nom=nom.strip(),
        date=date_epreuve,
        bareme_id=bareme_id,
    )
    db.update_epreuve(conn, modifiee)
    return modifiee


def lister_epreuves_toutes(conn: sqlite3.Connection) -> list[tuple[Competition, Epreuve]]:
    """Toutes les épreuves, toutes compétitions confondues, triées par
    date décroissante -- pour un sélecteur GUI qui n'a pas besoin de
    naviguer compétition par compétition pour retrouver l'épreuve du
    jour."""
    resultat = [
        (competition, epreuve)
        for competition in db.list_competitions(conn)
        for epreuve in db.list_epreuves_by_competition(conn, competition.id)
    ]
    resultat.sort(key=lambda paire: paire[1].date, reverse=True)
    return resultat


def creer_template_epreuve(conn: sqlite3.Connection, nom: str, bareme_id: str) -> EpreuveTemplate:
    """Crée un modèle d'épreuve réutilisable (nom + barème), indépendant
    de toute compétition -- voir EpreuveTemplate."""
    nom = nom.strip()
    if not nom:
        raise ErreurMetier("Le nom du modèle ne peut pas être vide.")
    if db.get_bareme(conn, bareme_id) is None:
        raise ErreurMetier(f"Barème inconnu : {bareme_id}")

    template = EpreuveTemplate(id=_nouvel_id(), nom=nom, bareme_id=bareme_id)
    db.insert_epreuve_template(conn, template)
    return template


def creer_template_depuis_epreuve(
    conn: sqlite3.Connection, epreuve_id: str, nom_template: str | None = None
) -> EpreuveTemplate:
    """Enregistre une épreuve existante comme modèle réutilisable --
    reprend son nom par défaut (personnalisable via ``nom_template``,
    utile si on veut un nom de modèle différent du nom de l'épreuve
    d'origine, ex. "IFAA Indoor -- samedi" -> modèle "IFAA Indoor")."""
    epreuve = db.get_epreuve(conn, epreuve_id)
    if epreuve is None:
        raise ErreurMetier("Épreuve introuvable.")

    return creer_template_epreuve(conn, nom_template or epreuve.nom, epreuve.bareme_id)


def lister_templates_epreuve(conn: sqlite3.Connection) -> list[EpreuveTemplate]:
    return db.list_epreuve_templates(conn)


def creer_epreuve_depuis_template(
    conn: sqlite3.Connection,
    competition_id: str,
    template_id: str,
    date_epreuve: date,
) -> Epreuve:
    """Crée une épreuve à partir d'un modèle -- seule la date reste à
    saisir, nom et barème sont repris du modèle. Passe par
    ``creer_epreuve()`` pour ne pas dupliquer ses validations (compétition
    ouverte, date dans les bornes de la compétition...)."""
    template = db.get_epreuve_template(conn, template_id)
    if template is None:
        raise ErreurMetier("Modèle d'épreuve introuvable.")

    return creer_epreuve(
        conn,
        competition_id=competition_id,
        nom=template.nom,
        date_epreuve=date_epreuve,
        bareme_id=template.bareme_id,
    )


# ------------------------------------------------------- Inscription --


def inscrire(conn: sqlite3.Connection, id_federal: str, epreuve_id: str) -> Inscription:
    competiteur = db.get_competiteur(conn, id_federal)
    if competiteur is None:
        raise ErreurMetier(
            f"Compétiteur inconnu : {id_federal} -- importe d'abord la base " "des compétiteurs."
        )
    epreuve = db.get_epreuve(conn, epreuve_id)
    if epreuve is None:
        raise ErreurMetier("Épreuve introuvable.")

    deja_inscrit = any(
        i.id_federal == id_federal for i in db.list_inscriptions_by_epreuve(conn, epreuve_id)
    )
    if deja_inscrit:
        raise ErreurMetier(
            f"{competiteur.prenom} {competiteur.nom} est déjà inscrit·e à " "cette épreuve."
        )

    inscription = Inscription(id=_nouvel_id(), id_federal=id_federal, epreuve_id=epreuve_id)
    db.insert_inscription(conn, inscription)
    return inscription


def lister_competiteurs_non_inscrits(
    conn: sqlite3.Connection, epreuve_id: str
) -> list[Competiteur]:
    """Compétiteurs de la base qui ne sont pas encore inscrits à cette
    épreuve -- pour alimenter un sélecteur GUI sans proposer deux fois
    la même personne."""
    deja_inscrits = {i.id_federal for i in db.list_inscriptions_by_epreuve(conn, epreuve_id)}
    return [
        competiteur
        for competiteur in db.list_competiteurs(conn)
        if competiteur.id_federal not in deja_inscrits
    ]


# ------------------------------------------------------------- Score --


# ------------------------------------------------------------- Score --


def saisir_score_final(
    conn: sqlite3.Connection,
    inscription_id: str,
    total: int,
    *,
    nombre_x: int = 0,
    statut: StatutScore = StatutScore.VALIDE,
) -> Score:
    """Enregistre (ou corrige) le score final d'une inscription, tel que
    totalisé sur la feuille de match -- pas une saisie flèche par flèche
    ni volée par volée (voir models/score.py pour le pourquoi).

    Le total est borné par ``bareme.score_max`` : au-delà, c'est un
    signal de saisie erronée (faute de frappe), pas une valeur à corriger
    silencieusement.

    Le statut par défaut est ``VALIDE`` : une saisie faite par
    l'organisateur lui-même n'a pas à repasser par une file de validation
    (voir docs/cahier-des-charges/securite.rst §7.2).
    """
    epreuve, bareme = _epreuve_et_bareme_de(conn, inscription_id)

    if total < 0:
        raise ErreurMetier("Le score total ne peut pas être négatif.")
    if total > bareme.score_max:
        raise ErreurMetier(
            f"Score total invalide : {total} -- dépasse le score maximum "
            f"possible pour ce barème ({bareme.score_max})."
        )
    if nombre_x < 0:
        raise ErreurMetier("Le nombre de X ne peut pas être négatif.")
    if nombre_x > bareme.total_flèches:
        raise ErreurMetier(
            f"Le nombre de X ({nombre_x}) dépasse le nombre de flèches de "
            f"l'épreuve ({bareme.total_flèches})."
        )
    if nombre_x > 0 and not bareme.departage_par_x:
        raise ErreurMetier(
            f"Le barème « {bareme.nom} » n'utilise pas de zone X -- laisse ce compteur à 0."
        )

    score = Score(
        id=_nouvel_id(),
        inscription_id=inscription_id,
        total=total,
        nombre_x=nombre_x,
        statut=statut,
    )
    db.upsert_score(conn, score)
    return score


def _epreuve_et_bareme_de(conn: sqlite3.Connection, inscription_id: str):
    """Remonte de l'inscription jusqu'au barème de son épreuve.

    Passe par une requête directe plutôt que par
    ``list_inscriptions_by_epreuve`` : on n'a que l'id d'inscription en
    entrée, pas celui de l'épreuve.
    """
    row = conn.execute(
        "SELECT epreuve_id FROM inscriptions WHERE id = ?", (inscription_id,)
    ).fetchone()
    if row is None:
        raise ErreurMetier("Inscription introuvable.")

    epreuve = db.get_epreuve(conn, row["epreuve_id"])
    if epreuve is None:
        raise ErreurMetier("Épreuve introuvable.")

    bareme = db.get_bareme(conn, epreuve.bareme_id)
    if bareme is None:
        raise ErreurMetier(f"Barème introuvable : {epreuve.bareme_id}")

    return epreuve, bareme


# -------------------------------------------------------- Classement --


def classement_epreuve(
    conn: sqlite3.Connection, epreuve_id: str
) -> dict[str, list[LigneClassement]]:
    """Classement live d'une épreuve, groupé par catégorie.

    Le paramètre ``categories_veteran_actives`` est lu sur la Compétition
    parente -- l'organisateur l'a choisi une fois à la création, la GUI
    n'a pas à le repasser à chaque affichage.
    """
    epreuve = db.get_epreuve(conn, epreuve_id)
    if epreuve is None:
        raise ErreurMetier("Épreuve introuvable.")

    bareme = db.get_bareme(conn, epreuve.bareme_id)
    if bareme is None:
        raise ErreurMetier(f"Barème introuvable : {epreuve.bareme_id}")

    competition = db.get_competition(conn, epreuve.competition_id)
    if competition is None:
        raise ErreurMetier("Compétition introuvable.")

    entrees: list[tuple[Competiteur, Score | None]] = []
    for inscription in db.list_inscriptions_by_epreuve(conn, epreuve_id):
        competiteur = db.get_competiteur(conn, inscription.id_federal)
        if competiteur is None:
            continue
        score = db.get_score_by_inscription(conn, inscription.id)
        entrees.append((competiteur, score))

    return classement_par_categorie(
        bareme,
        epreuve.date,
        entrees,
        categories_veteran_actives=competition.categories_veteran_actives,
    )


# ------------------------------------------------------------- Accueil --


@dataclass(slots=True)
class ResumeAccueil:
    nb_competitions: int
    nb_competiteurs: int
    nb_epreuves: int
    derniere_epreuve: tuple[Competition, Epreuve] | None
    """La compétition et l'épreuve les plus récentes par date (pas un
    horodatage de dernière action -- rien dans le modèle ne trace
    "quand" une compétition ou un score a été saisi, seulement les dates
    métier des épreuves elles-mêmes). C'est le meilleur indicateur
    disponible de "ce qui se passe en ce moment" sans ajouter un champ
    d'horodatage à plusieurs tables juste pour cet écran."""


def resumer_accueil(conn: sqlite3.Connection) -> ResumeAccueil:
    """Chiffres clés pour l'écran d'accueil -- une seule fonction, testée
    une fois, plutôt que de laisser la GUI recompter elle-même."""
    toutes_epreuves = lister_epreuves_toutes(conn)  # déjà triées par date décroissante
    return ResumeAccueil(
        nb_competitions=len(db.list_competitions(conn)),
        nb_competiteurs=len(db.list_competiteurs(conn)),
        nb_epreuves=len(toutes_epreuves),
        derniere_epreuve=toutes_epreuves[0] if toutes_epreuves else None,
    )
