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

import hashlib
import hmac
import secrets
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import date, datetime

from fletchscore import securite
from fletchscore.models import (
    Club,
    Competiteur,
    Competition,
    DemandeRattachement,
    Epreuve,
    EpreuveTemplate,
    Inscription,
    Score,
    Sexe,
    StatutCompetition,
    StatutDemandeRattachement,
    StatutScore,
    StatutToken,
    Token,
)
from fletchscore.scoring import classement_global, classement_par_categorie
from fletchscore.scoring.classement import LigneClassement, LigneClassementGlobal
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


def classement_global_competition(
    conn: sqlite3.Connection, competition_id: str
) -> tuple[list[Epreuve], dict[str, list[LigneClassementGlobal]]]:
    """Classement cumulé sur toutes les épreuves d'une compétition -- un
    total par épreuve, plus un total global qui sert de critère de tri
    (voir scoring.classement_global pour le pourquoi de l'absence de
    départage au X ici).

    Retourne aussi la liste des épreuves (dans l'ordre où
    ``classement_global`` les a utilisées) -- nécessaire à l'appelant
    pour savoir quelle colonne correspond à quelle épreuve à l'export.
    """
    competition = db.get_competition(conn, competition_id)
    if competition is None:
        raise ErreurMetier("Compétition introuvable.")

    epreuves = db.list_epreuves_by_competition(conn, competition_id)
    if not epreuves:
        return [], {}

    competiteurs_par_id: dict[str, Competiteur] = {}
    scores_par_competiteur: dict[str, dict[str, Score | None]] = {}

    for epreuve in epreuves:
        for inscription in db.list_inscriptions_by_epreuve(conn, epreuve.id):
            competiteur = db.get_competiteur(conn, inscription.id_federal)
            if competiteur is None:
                continue
            competiteurs_par_id.setdefault(competiteur.id_federal, competiteur)
            scores_par_competiteur.setdefault(competiteur.id_federal, {})
            scores_par_competiteur[competiteur.id_federal][epreuve.id] = (
                db.get_score_by_inscription(conn, inscription.id)
            )

    entrees = [
        (competiteurs_par_id[id_federal], scores_par_competiteur[id_federal])
        for id_federal in competiteurs_par_id
    ]

    classement = classement_global(
        competition.date_debut,
        [epreuve.id for epreuve in epreuves],
        entrees,
        categories_veteran_actives=competition.categories_veteran_actives,
    )
    return epreuves, classement


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


# ---------------------------------------------------- Token / rattachement --

_CARACTERES_CODE_COURT = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
"""Exclut 0/O et 1/I -- ambigus à la lecture/saisie manuelle en secours
si le QR code n'est pas scannable (voir models/token.py)."""


def _generer_code_court(longueur: int = 6) -> str:
    return "".join(secrets.choice(_CARACTERES_CODE_COURT) for _ in range(longueur))


def _hash_token(secret_token: str) -> str:
    """HMAC-SHA256 du secret, avec la clé serveur -- jamais le secret
    stocké tel quel (voir fletchscore/securite.py pour le pourquoi de la
    clé stockée hors de la base).

    Passe explicitement ``securite.CHEMIN_CLE_PAR_DEFAUT`` plutôt que de
    laisser ``obtenir_cle_secrete()`` utiliser son propre défaut : un
    argument par défaut est figé une seule fois à la définition de la
    fonction -- patcher l'attribut du module en test (voir
    ``TokenTestCase``) ne le changerait pas si on ne le relit pas ici.
    """
    cle = securite.obtenir_cle_secrete(securite.CHEMIN_CLE_PAR_DEFAUT)
    return hmac.new(cle, secret_token.encode(), hashlib.sha256).hexdigest()


def generer_token(
    conn: sqlite3.Connection,
    id_federal: str,
    competition_id: str,
    *,
    expire_le: datetime | None = None,
) -> tuple[Token, str]:
    """Génère un nouveau token d'accès pour ce compétiteur à cette
    compétition.

    Retourne le ``Token`` persisté ET le secret en clair -- ce dernier
    n'est jamais stocké tel quel (seul son HMAC l'est, voir
    ``_hash_token``), donc c'est la seule fois où l'appelant peut le
    récupérer pour l'encoder dans un QR code ou l'afficher.
    """
    if db.get_competiteur(conn, id_federal) is None:
        raise ErreurMetier(f"Compétiteur introuvable : {id_federal}")
    if db.get_competition(conn, competition_id) is None:
        raise ErreurMetier("Compétition introuvable.")

    secret_token = secrets.token_urlsafe(24)
    code_court = _generer_code_court()
    while db.get_token_by_code_court(conn, code_court) is not None:
        # Collision improbable (32 caractères ^ 6) mais pas impossible --
        # code_court est UNIQUE en base, mieux vaut réessayer que planter.
        code_court = _generer_code_court()

    token = Token(
        id_federal=id_federal,
        competition_id=competition_id,
        code_court=code_court,
        hash_token=_hash_token(secret_token),
        statut=StatutToken.EMIS,
        cree_le=datetime.now(),
        expire_le=expire_le,
    )
    db.insert_token(conn, token)
    return token, secret_token


def verifier_token(conn: sqlite3.Connection, code_court: str, secret_token: str) -> Token | None:
    """Vérifie un token présenté par un compétiteur : recherche par
    ``code_court`` puis comparaison du HMAC du secret présenté --
    jamais une comparaison directe (le secret n'est jamais stocké en
    clair). ``hmac.compare_digest`` plutôt que ``==`` : une comparaison
    naïve fuiterait un minuscule signal temporel exploitable (attaque par
    canal auxiliaire), même si le risque réel reste faible sur un wifi de
    club -- pas de raison de s'en priver, ça ne coûte rien.

    Retourne ``None`` aussi bien si le token n'existe pas, si le secret
    ne correspond pas, que s'il est expiré/révoqué -- volontairement le
    même signal dans les trois cas, pour ne pas révéler à un attaquant
    lequel des trois a échoué.
    """
    token = db.get_token_by_code_court(conn, code_court)
    if token is None:
        return None
    if not hmac.compare_digest(token.hash_token, _hash_token(secret_token)):
        return None
    if not token.est_valide(datetime.now()):
        return None
    return token


def verifier_code_court(conn: sqlite3.Connection, code_court: str) -> Token | None:
    """Vérifie un accès à partir du seul code court, saisi à la main --
    volontairement plus faible que ``verifier_token()`` : ne demande pas
    le secret complet, seulement le code à 6 caractères communiqué de
    vive voix ou par écrit.

    Acceptable dans le contexte actuel (v0.3, wifi de club, aucune
    écriture de score en jeu -- juste "confirmer que je suis bien
    identifié") mais **pas suffisant** le jour où une vraie donnée
    sensible transitera par ce chemin (proposition de score, v0.4) :
    un code à 6 caractères depuis un alphabet de 32 (~30 bits) reste
    devinable par force brute si l'enjeu grandit -- à revoir à ce
    moment-là plutôt que d'y ajouter des rustines a posteriori.
    """
    token = db.get_token_by_code_court(conn, code_court)
    if token is None:
        return None
    if not token.est_valide(datetime.now()):
        return None
    return token


def revoquer_acces(conn: sqlite3.Connection, id_federal: str, competition_id: str) -> None:
    """Révoque le token d'un compétiteur pour une compétition -- ne lève
    pas d'erreur si aucun token n'existait déjà (l'effet recherché,
    "cette personne n'a plus accès", est atteint dans les deux cas)."""
    db.revoquer_token(conn, id_federal, competition_id)


def demander_rattachement(
    conn: sqlite3.Connection, id_federal: str, competition_id: str
) -> DemandeRattachement:
    """Enregistre une demande de rattachement -- ne génère jamais de
    token à ce stade, seulement une entrée en file d'attente (voir
    docs/cahier-des-charges/securite.rst : le token n'est émis qu'après
    validation humaine de l'organisateur, voir ``valider_rattachement``).
    """
    if db.get_competiteur(conn, id_federal) is None:
        raise ErreurMetier(f"Compétiteur introuvable : {id_federal}")
    if db.get_competition(conn, competition_id) is None:
        raise ErreurMetier("Compétition introuvable.")

    demande = DemandeRattachement(
        id=_nouvel_id(),
        id_federal=id_federal,
        competition_id=competition_id,
        statut=StatutDemandeRattachement.EN_ATTENTE,
        horodatage=datetime.now(),
    )
    db.insert_demande_rattachement(conn, demande)
    return demande


def lister_demandes_en_attente(
    conn: sqlite3.Connection, competition_id: str
) -> list[tuple[Competiteur, DemandeRattachement]]:
    """Associe chaque demande en attente à son compétiteur -- pour
    affichage direct dans la GUI (nom, prénom), pas juste un id_federal
    brut à recouper manuellement."""
    resultat = []
    for demande in db.list_demandes_en_attente(conn, competition_id):
        competiteur = db.get_competiteur(conn, demande.id_federal)
        if competiteur is not None:
            resultat.append((competiteur, demande))
    return resultat


def lister_tokens_actifs(
    conn: sqlite3.Connection, competition_id: str
) -> list[tuple[Competiteur, Token]]:
    """Associe chaque token *non révoqué* de cette compétition à son
    compétiteur -- pour l'écran "révoquer un accès" de la GUI. Les
    tokens révoqués ne sont pas cachés en base (traçabilité), mais n'ont
    pas leur place dans une liste "accès actifs"."""
    resultat = []
    for token in db.list_tokens_by_competition(conn, competition_id):
        if token.statut == StatutToken.REVOQUE:
            continue
        competiteur = db.get_competiteur(conn, token.id_federal)
        if competiteur is not None:
            resultat.append((competiteur, token))
    return resultat


def _obtenir_demande_en_attente(conn: sqlite3.Connection, demande_id: str) -> DemandeRattachement:
    demande = db.get_demande_rattachement(conn, demande_id)
    if demande is None:
        raise ErreurMetier("Demande de rattachement introuvable.")
    if demande.statut != StatutDemandeRattachement.EN_ATTENTE:
        raise ErreurMetier("Cette demande a déjà été traitée.")
    return demande


def valider_rattachement(conn: sqlite3.Connection, demande_id: str) -> tuple[Token, str]:
    """Valide une demande après vérification visuelle de l'identité par
    l'organisateur -- génère et attribue le token à ce moment précis,
    jamais avant (voir docs/cahier-des-charges/securite.rst)."""
    demande = _obtenir_demande_en_attente(conn, demande_id)
    token, secret_token = generer_token(conn, demande.id_federal, demande.competition_id)
    db.update_statut_demande(conn, demande_id, StatutDemandeRattachement.VALIDEE)
    return token, secret_token


def rejeter_rattachement(conn: sqlite3.Connection, demande_id: str) -> None:
    _obtenir_demande_en_attente(conn, demande_id)  # lève ErreurMetier si invalide
    db.update_statut_demande(conn, demande_id, StatutDemandeRattachement.REJETEE)
