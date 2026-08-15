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
import logging
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
    CompetitionTemplate,
    CompetitionTemplateEpreuve,
    DemandeRattachement,
    Epreuve,
    EpreuveTemplate,
    Inscription,
    Message,
    Procuration,
    Score,
    Sexe,
    StatutCompetition,
    StatutDemandeRattachement,
    StatutProcuration,
    StatutScore,
    StatutToken,
    Token,
)
from fletchscore.scoring import classement_global, classement_par_categorie
from fletchscore.scoring.classement import LigneClassement, LigneClassementGlobal
from fletchscore.storage import db

logger = logging.getLogger("fletchscore")


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


def anonymiser_competiteur(conn: sqlite3.Connection, id_federal: str) -> None:
    """Anonymise un compétiteur -- droit à l'effacement RGPD (issue #37).

    Choix délibéré : anonymisation plutôt que suppression complète, pour
    ne pas fausser un classement déjà publié en faisant "remonter" les
    rangs suivants (voir docstring de ``db.anonymiser_competiteur`` pour
    le détail de ce qui est conservé/supprimé). Le nom devient
    ``Compétiteur/{id_federal}`` -- reste techniquement rattaché à
    l'identifiant fédéral (conservé comme clé, voir discussion issue
    #37) plutôt qu'un texte totalement générique, pour qu'un
    organisateur retrouve facilement quelle ligne correspond à quelle
    demande d'effacement s'il doit s'y référer plus tard."""
    if db.get_competiteur(conn, id_federal) is None:
        raise ErreurMetier(f"Compétiteur introuvable : {id_federal}")

    db.anonymiser_competiteur(conn, id_federal, f"Compétiteur/{id_federal}")


def supprimer_competiteur(conn: sqlite3.Connection, id_federal: str) -> None:
    """Supprime purement et simplement une fiche compétiteur -- réservé
    à un compétiteur qui n'a jamais concouru (issue #43), contrairement
    à ``anonymiser_competiteur`` (#37) qui s'applique à un compétiteur
    déjà engagé. Refusé dès la moindre inscription, dans n'importe
    quelle épreuve : le seul chemin pour quelqu'un déjà classé reste
    l'anonymisation, pour ne pas revenir sur la décision prise à ce
    sujet (risque de fausser un classement déjà publié)."""
    if db.get_competiteur(conn, id_federal) is None:
        raise ErreurMetier(f"Compétiteur introuvable : {id_federal}")
    if db.list_inscriptions_by_competiteur(conn, id_federal):
        raise ErreurMetier(
            "Impossible de supprimer un compétiteur déjà inscrit à une épreuve -- "
            "utilise l'anonymisation (🗑) à la place."
        )

    db.supprimer_competiteur(conn, id_federal)


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


def supprimer_competition(conn: sqlite3.Connection, competition_id: str) -> None:
    """Supprime une compétition vide -- issue #45. Refusée dès qu'un
    score existe dans n'importe laquelle de ses épreuves, même un
    seul -- pas de cascade forcée sur des données notées. En
    l'absence de score, cascade complète sur épreuves, inscriptions et
    accès (voir ``db.supprimer_competition``). Contrairement à
    ``supprimer_epreuve`` (#44), le statut de la compétition n'est pas
    vérifié ici -- ``modifier_competition`` ne bloque déjà pas sur une
    compétition clôturée (clôturer est une action à part, pas un champ
    comme un autre), pas de raison d'introduire une règle plus stricte
    à la suppression."""
    competition = db.get_competition(conn, competition_id)
    if competition is None:
        raise ErreurMetier("Compétition introuvable.")

    for epreuve in db.list_epreuves_by_competition(conn, competition_id):
        if db.epreuve_a_des_scores(conn, epreuve.id):
            raise ErreurMetier(
                "Impossible de supprimer une compétition où au moins un " "score a été saisi."
            )

    db.supprimer_competition(conn, competition_id)


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


def supprimer_epreuve(conn: sqlite3.Connection, epreuve_id: str) -> None:
    """Supprime une épreuve vide -- issue #44. Contrairement à la
    compétition (#45), les inscriptions sans score sont supprimées avec
    (rien d'irréversible à perdre) plutôt que de bloquer aussi sur
    elles -- seule la présence d'un score, même un seul, refuse toute
    la suppression. Même règle que ``modifier_epreuve`` sur une
    compétition clôturée : pas plus supprimable que modifiable."""
    epreuve = db.get_epreuve(conn, epreuve_id)
    if epreuve is None:
        raise ErreurMetier("Épreuve introuvable.")

    competition = db.get_competition(conn, epreuve.competition_id)
    if competition is not None and competition.statut == StatutCompetition.CLOTUREE:
        raise ErreurMetier(
            "Cette compétition est clôturée -- impossible d'en supprimer une épreuve."
        )
    if db.epreuve_a_des_scores(conn, epreuve_id):
        raise ErreurMetier("Impossible de supprimer une épreuve où au moins un score a été saisi.")

    db.supprimer_epreuve(conn, epreuve_id)


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


# ---------------------------------------------- Modèle de compétition --


def creer_template_competition(
    conn: sqlite3.Connection, nom: str, epreuves: list[tuple[str, str]]
) -> CompetitionTemplate:
    """Crée un modèle de compétition réutilisable -- un bundle de
    plusieurs épreuves (nom, bareme_id), toujours sans date (même
    principe qu'``EpreuveTemplate``, voir son docstring).

    ``epreuves`` : liste de ``(nom, bareme_id)`` dans l'ordre souhaité --
    au moins une, un modèle vide n'aurait rien à générer."""
    nom = nom.strip()
    if not nom:
        raise ErreurMetier("Le nom du modèle ne peut pas être vide.")
    if not epreuves:
        raise ErreurMetier("Un modèle de compétition doit contenir au moins une épreuve.")
    for nom_epreuve, bareme_id in epreuves:
        if not nom_epreuve.strip():
            raise ErreurMetier("Le nom d'une épreuve du modèle ne peut pas être vide.")
        if db.get_bareme(conn, bareme_id) is None:
            raise ErreurMetier(f"Barème inconnu : {bareme_id}")

    template = CompetitionTemplate(id=_nouvel_id(), nom=nom)
    db.insert_competition_template(conn, template)
    for ordre, (nom_epreuve, bareme_id) in enumerate(epreuves):
        db.insert_competition_template_epreuve(
            conn,
            CompetitionTemplateEpreuve(
                id=_nouvel_id(),
                competition_template_id=template.id,
                nom=nom_epreuve.strip(),
                bareme_id=bareme_id,
                ordre=ordre,
            ),
        )
    return template


def creer_template_depuis_competition(
    conn: sqlite3.Connection, competition_id: str, nom_template: str | None = None
) -> CompetitionTemplate:
    """Enregistre les épreuves d'une compétition existante comme modèle
    réutilisable -- reprend le nom de la compétition par défaut
    (personnalisable via ``nom_template``, même principe que
    ``creer_template_depuis_epreuve``)."""
    competition = db.get_competition(conn, competition_id)
    if competition is None:
        raise ErreurMetier("Compétition introuvable.")
    epreuves = db.list_epreuves_by_competition(conn, competition_id)
    if not epreuves:
        raise ErreurMetier("Cette compétition n'a aucune épreuve à enregistrer comme modèle.")

    paires = [(epreuve.nom, epreuve.bareme_id) for epreuve in epreuves]
    return creer_template_competition(conn, nom_template or competition.nom, paires)


def lister_templates_competition(conn: sqlite3.Connection) -> list[CompetitionTemplate]:
    return db.list_competition_templates(conn)


def lister_epreuves_du_template_competition(
    conn: sqlite3.Connection, template_id: str
) -> list[CompetitionTemplateEpreuve]:
    return db.list_competition_template_epreuves(conn, template_id)


def creer_competition_depuis_template(
    conn: sqlite3.Connection,
    template_id: str,
    nom: str,
    date_debut: date,
    date_fin: date,
    *,
    lieu: str = "",
    categories_veteran_actives: bool = False,
) -> tuple[Competition, list[Epreuve]]:
    """Crée une compétition puis génère en une fois toutes ses épreuves à
    partir du modèle -- délègue à ``creer_competition()``/``creer_epreuve()``
    pour ne pas dupliquer leurs validations, même principe que
    ``creer_epreuve_depuis_template``.

    Chaque épreuve générée prend ``date_debut`` comme date par défaut --
    un modèle de compétition ne porte aucune date (voir docstring de
    ``CompetitionTemplate``). Si les épreuves ne tombent pas toutes le
    même jour, l'organisateur ajuste ensuite individuellement via
    ``modifier_epreuve()``, déjà existant -- pas la peine d'un mécanisme
    de dates par épreuve dans le modèle rien que pour ce cas."""
    template = db.get_competition_template(conn, template_id)
    if template is None:
        raise ErreurMetier("Modèle de compétition introuvable.")
    epreuves_template = db.list_competition_template_epreuves(conn, template_id)
    if not epreuves_template:
        raise ErreurMetier("Ce modèle de compétition n'a aucune épreuve.")

    competition = creer_competition(
        conn,
        nom,
        date_debut,
        date_fin,
        lieu=lieu,
        categories_veteran_actives=categories_veteran_actives,
    )
    epreuves = [
        creer_epreuve(
            conn, competition.id, epreuve_template.nom, date_debut, epreuve_template.bareme_id
        )
        for epreuve_template in epreuves_template
    ]
    return competition, epreuves


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


def annuler_inscription(conn: sqlite3.Connection, inscription_id: str) -> None:
    """Annule une inscription -- issue #46. Refusée dès qu'un score a
    déjà été saisi : il faut d'abord le traiter (mécanisme existant côté
    saisie) avant de pouvoir annuler l'inscription elle-même."""
    inscription = db.get_inscription(conn, inscription_id)
    if inscription is None:
        raise ErreurMetier("Inscription introuvable.")
    if db.get_score_by_inscription(conn, inscription_id) is not None:
        raise ErreurMetier(
            "Impossible d'annuler une inscription pour laquelle un score a déjà été saisi."
        )

    db.supprimer_inscription(conn, inscription_id)


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
    propose_par_id_federal: str | None = None,
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

    ``propose_par_id_federal`` : qui a réellement soumis ce score, pour
    une proposition en ligne (voir ``proposer_score``) -- laissé à
    ``None`` pour une saisie organisateur, sans lien avec une soumission
    en ligne.
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
        propose_par_id_federal=propose_par_id_federal,
    )
    try:
        db.upsert_score(conn, score)
    except Exception:
        # Chemin critique (CLAUDE.md) : couvre à la fois la saisie
        # organisateur, une proposition compétiteur (proposer_score) et
        # sa validation (valider_score_propose), qui passent toutes les
        # trois par ici -- jamais de corruption silencieuse d'un score,
        # toujours une trace exploitable après coup. Ré-échouée telle
        # quelle après journalisation, pas de repli ni de correction
        # automatique : à l'appelant de décider quoi faire d'une
        # écriture en base qui a échoué.
        logger.exception(
            "Échec de l'enregistrement du score (inscription_id=%s, statut=%s)",
            inscription_id,
            statut,
        )
        raise
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


def _a_une_procuration_valide(
    conn: sqlite3.Connection, id_federal_mandataire: str, id_federal_mandant: str, epreuve_id: str
) -> bool:
    epreuve = db.get_epreuve(conn, epreuve_id)
    if epreuve is None:
        return False
    return (
        db.get_procuration_validee(
            conn, epreuve.competition_id, id_federal_mandataire, id_federal_mandant
        )
        is not None
    )


def proposer_score(
    conn: sqlite3.Connection,
    id_federal_proposant: str,
    epreuve_id: str,
    total: int,
    *,
    nombre_x: int = 0,
    id_federal_cible: str | None = None,
) -> Score:
    """Propose un score final pour une épreuve -- pour soi-même par
    défaut (``id_federal_cible`` omis), ou pour quelqu'un d'autre via
    une ``Procuration`` déjà **validée** par l'organisateur
    (``id_federal_cible`` fourni). Mêmes bornes que la saisie
    organisateur (``saisir_score_final``), statut ``PROPOSE`` :
    n'apparaît dans aucun classement tant qu'un organisateur ne l'a pas
    validé (``valider_score_propose``), voir ``scoring.total_scores``.

    Le proposant réel est toujours enregistré
    (``Score.propose_par_id_federal``), même en cas d'auto-proposition
    -- pour que l'organisateur puisse juger la fiabilité d'une
    proposition avant de la valider, plutôt que de voir un total sans
    savoir qui l'a réellement soumis (voir models/score.py).

    Refuse d'écraser un score déjà **validé** -- une nouvelle
    proposition ne doit jamais rouvrir silencieusement un score
    officiel déjà entériné ; seul l'organisateur peut le corriger
    (écran Saisie). Re-proposer avant validation, en revanche, remplace
    la proposition précédente sans problème (une correction avant
    revue, cas normal).
    """
    id_federal_cible = id_federal_cible or id_federal_proposant

    inscription = db.get_inscription_par_competiteur_epreuve(conn, id_federal_cible, epreuve_id)
    if inscription is None:
        if id_federal_cible == id_federal_proposant:
            raise ErreurMetier("Tu n'es pas inscrit·e à cette épreuve.")
        raise ErreurMetier("Cette personne n'est pas inscrite à cette épreuve.")

    if id_federal_cible != id_federal_proposant and not _a_une_procuration_valide(
        conn, id_federal_proposant, id_federal_cible, epreuve_id
    ):
        raise ErreurMetier(
            "Aucune procuration validée ne t'autorise à proposer un " "score pour cette personne."
        )

    score_existant = db.get_score_by_inscription(conn, inscription.id)
    if score_existant is not None and score_existant.statut == StatutScore.VALIDE:
        raise ErreurMetier(
            "Un score officiel existe déjà pour cette épreuve -- "
            "contacte l'organisateur pour le faire corriger."
        )

    return saisir_score_final(
        conn,
        inscription.id,
        total,
        nombre_x=nombre_x,
        statut=StatutScore.PROPOSE,
        propose_par_id_federal=id_federal_proposant,
    )


def lister_propositions_en_attente(
    conn: sqlite3.Connection, epreuve_id: str
) -> list[tuple[Competiteur, Score]]:
    """Associe chaque score proposé (pas encore validé/rejeté) de cette
    épreuve à son compétiteur -- pour affichage direct dans la GUI."""
    resultat = []
    for inscription in db.list_inscriptions_by_epreuve(conn, epreuve_id):
        score = db.get_score_by_inscription(conn, inscription.id)
        if score is not None and score.statut == StatutScore.PROPOSE:
            competiteur = db.get_competiteur(conn, inscription.id_federal)
            if competiteur is not None:
                resultat.append((competiteur, score))
    return resultat


def valider_score_propose(conn: sqlite3.Connection, inscription_id: str) -> Score:
    """Valide un score proposé par le compétiteur -- le fait passer de
    ``PROPOSE`` à ``VALIDE`` sans en changer les valeurs. Devient à ce
    moment précis LE score officiel de cette inscription, comptabilisé
    dans le classement."""
    score = _obtenir_proposition_en_attente(conn, inscription_id)
    return saisir_score_final(
        conn,
        inscription_id,
        score.total,
        nombre_x=score.nombre_x,
        statut=StatutScore.VALIDE,
        propose_par_id_federal=score.propose_par_id_federal,
    )


def rejeter_score_propose(conn: sqlite3.Connection, inscription_id: str) -> None:
    score = _obtenir_proposition_en_attente(conn, inscription_id)
    saisir_score_final(
        conn,
        inscription_id,
        score.total,
        nombre_x=score.nombre_x,
        statut=StatutScore.REJETE,
        propose_par_id_federal=score.propose_par_id_federal,
    )


def _obtenir_proposition_en_attente(conn: sqlite3.Connection, inscription_id: str) -> Score:
    score = db.get_score_by_inscription(conn, inscription_id)
    if score is None or score.statut != StatutScore.PROPOSE:
        raise ErreurMetier("Aucun score proposé en attente pour cette inscription.")
    return score


# --------------------------------------------------------- Procuration --


def demander_procuration(
    conn: sqlite3.Connection,
    id_federal_mandataire: str,
    id_federal_mandant: str,
    competition_id: str,
) -> Procuration:
    """Demande le droit de proposer des scores au nom d'un autre
    compétiteur pour une compétition -- sans effet tant qu'un
    organisateur ne l'a pas validée (voir ``valider_procuration``), même
    principe que ``demander_rattachement``.
    """
    if id_federal_mandataire == id_federal_mandant:
        raise ErreurMetier("Impossible de demander une procuration pour toi-même.")
    if db.get_competiteur(conn, id_federal_mandataire) is None:
        raise ErreurMetier(f"Compétiteur introuvable : {id_federal_mandataire}")
    if db.get_competiteur(conn, id_federal_mandant) is None:
        raise ErreurMetier(f"Compétiteur introuvable : {id_federal_mandant}")
    if db.get_competition(conn, competition_id) is None:
        raise ErreurMetier("Compétition introuvable.")

    if db.get_procuration_validee(conn, competition_id, id_federal_mandataire, id_federal_mandant):
        raise ErreurMetier("Une procuration valide existe déjà pour cette personne.")

    for procuration in db.list_procurations_en_attente(conn, competition_id):
        if (
            procuration.id_federal_mandataire == id_federal_mandataire
            and procuration.id_federal_mandant == id_federal_mandant
        ):
            raise ErreurMetier(
                "Une demande de procuration est déjà en attente pour cette personne."
            )

    procuration = Procuration(
        id=_nouvel_id(),
        competition_id=competition_id,
        id_federal_mandataire=id_federal_mandataire,
        id_federal_mandant=id_federal_mandant,
        statut=StatutProcuration.EN_ATTENTE,
        demandee_le=datetime.now(),
    )
    db.insert_procuration(conn, procuration)
    return procuration


def lister_procurations_en_attente(
    conn: sqlite3.Connection, competition_id: str
) -> list[tuple[Competiteur, Competiteur, Procuration]]:
    """Associe chaque demande en attente à ses deux compétiteurs
    (mandataire, mandant) -- pour affichage direct dans la GUI."""
    resultat = []
    for procuration in db.list_procurations_en_attente(conn, competition_id):
        mandataire = db.get_competiteur(conn, procuration.id_federal_mandataire)
        mandant = db.get_competiteur(conn, procuration.id_federal_mandant)
        if mandataire is not None and mandant is not None:
            resultat.append((mandataire, mandant, procuration))
    return resultat


def lister_procurations_validees(
    conn: sqlite3.Connection, competition_id: str
) -> list[tuple[Competiteur, Competiteur, Procuration]]:
    """Associe chaque procuration *validée* de cette compétition à ses
    deux compétiteurs -- pour l'écran "révoquer une procuration" de la
    GUI, sur le modèle de ``lister_tokens_actifs``."""
    resultat = []
    for procuration in db.list_procurations_validees(conn, competition_id):
        mandataire = db.get_competiteur(conn, procuration.id_federal_mandataire)
        mandant = db.get_competiteur(conn, procuration.id_federal_mandant)
        if mandataire is not None and mandant is not None:
            resultat.append((mandataire, mandant, procuration))
    return resultat


def lister_mandants_pour(
    conn: sqlite3.Connection, id_federal_mandataire: str, competition_id: str
) -> list[Competiteur]:
    """Compétiteurs pour lesquels ce mandataire a une procuration
    validée sur cette compétition -- pour lui proposer, côté web, pour
    qui il peut soumettre un score."""
    resultat = []
    for procuration in db.list_procurations_validees_par_mandataire(
        conn, competition_id, id_federal_mandataire
    ):
        mandant = db.get_competiteur(conn, procuration.id_federal_mandant)
        if mandant is not None:
            resultat.append(mandant)
    return resultat


def _obtenir_procuration_en_attente(conn: sqlite3.Connection, procuration_id: str) -> Procuration:
    procuration = db.get_procuration(conn, procuration_id)
    if procuration is None:
        raise ErreurMetier("Procuration introuvable.")
    if procuration.statut != StatutProcuration.EN_ATTENTE:
        raise ErreurMetier("Cette demande de procuration a déjà été traitée.")
    return procuration


def valider_procuration(conn: sqlite3.Connection, procuration_id: str) -> Procuration:
    _obtenir_procuration_en_attente(conn, procuration_id)
    db.update_statut_procuration(conn, procuration_id, StatutProcuration.VALIDEE)
    return db.get_procuration(conn, procuration_id)


def rejeter_procuration(conn: sqlite3.Connection, procuration_id: str) -> None:
    _obtenir_procuration_en_attente(conn, procuration_id)
    db.update_statut_procuration(conn, procuration_id, StatutProcuration.REJETEE)


def revoquer_procuration(conn: sqlite3.Connection, procuration_id: str) -> None:
    """Révoque une procuration déjà validée -- le mandataire ne peut
    plus proposer de score pour ce mandant à partir de maintenant (les
    scores déjà proposés ne sont pas affectés rétroactivement)."""
    if db.get_procuration(conn, procuration_id) is None:
        raise ErreurMetier("Procuration introuvable.")
    db.update_statut_procuration(conn, procuration_id, StatutProcuration.REVOQUEE)


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

    Acceptable dans le contexte actuel (v0.2, wifi de club, aucune
    écriture de score en jeu -- juste "confirmer que je suis bien
    identifié") mais **pas suffisant** le jour où une vraie donnée
    sensible transitera par ce chemin (proposition de score, v0.3) :
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


def signer_identite_competiteur(id_federal: str, competition_id: str) -> str:
    """Signe un id fédéral + une compétition pour un cookie de session
    côté vue compétiteur -- empêche un navigateur de se faire passer
    pour quelqu'un d'autre juste en modifiant son cookie à la main.

    Utilisé après confirmation d'un code d'accès (voir
    ``api/competiteur.py``) pour que le navigateur "se souvienne" de qui
    il est le temps de la session, sans qu'un cookie en clair suffise à
    usurper l'identité d'un autre compétiteur -- même principe HMAC que
    les tokens (``_hash_token``), même clé serveur. La compétition est
    signée avec l'id fédéral (pas seulement l'id) : "Mes messages" a
    besoin de savoir pour quelle compétition, un compétiteur pouvant en
    principe avoir un accès à plusieurs.
    """
    cle = securite.obtenir_cle_secrete(securite.CHEMIN_CLE_PAR_DEFAUT)
    charge = f"{id_federal}|{competition_id}"
    signature = hmac.new(cle, charge.encode(), hashlib.sha256).hexdigest()
    return f"{charge}:{signature}"


def verifier_identite_signee(valeur: str) -> tuple[str, str] | None:
    """Vérifie une valeur de cookie produite par
    ``signer_identite_competiteur`` -- retourne ``(id_federal,
    competition_id)`` si la signature est valide, ``None`` sinon (cookie
    absent, altéré, ou fabriqué de toutes pièces)."""
    charge, _, signature_recue = valeur.rpartition(":")
    if not charge or "|" not in charge:
        return None
    id_federal, _, competition_id = charge.partition("|")
    if not id_federal or not competition_id:
        return None
    signature_attendue = signer_identite_competiteur(id_federal, competition_id).rpartition(":")[2]
    if not hmac.compare_digest(signature_attendue, signature_recue):
        return None
    return id_federal, competition_id


def _a_deja_un_acces_valide(conn: sqlite3.Connection, id_federal: str, competition_id: str) -> bool:
    maintenant = datetime.now()
    return any(
        token.id_federal == id_federal and token.est_valide(maintenant)
        for token in db.list_tokens_by_competition(conn, competition_id)
    )


def _a_deja_une_demande_en_attente(
    conn: sqlite3.Connection, id_federal: str, competition_id: str
) -> bool:
    return any(
        demande.id_federal == id_federal
        for demande in db.list_demandes_en_attente(conn, competition_id)
    )


def demander_rattachement(
    conn: sqlite3.Connection, id_federal: str, competition_id: str
) -> DemandeRattachement:
    """Enregistre une demande de rattachement -- ne génère jamais de
    token à ce stade, seulement une entrée en file d'attente (voir
    docs/cahier-des-charges/securite.rst : le token n'est émis qu'après
    validation humaine de l'organisateur, voir ``valider_rattachement``).

    Refuse une nouvelle demande si un accès valide existe déjà, ou si
    une demande est déjà en attente pour ce (compétiteur, compétition)
    -- sans ce garde-fou, valider une demande redondante émettrait un
    second token pour la même personne, sans jamais révoquer le
    premier : deux codes valides simultanés pour un seul compétiteur,
    confusion pour l'organisateur qui reverrait une demande déjà
    traitée en pratique.
    """
    if db.get_competiteur(conn, id_federal) is None:
        raise ErreurMetier(f"Compétiteur introuvable : {id_federal}")
    if db.get_competition(conn, competition_id) is None:
        raise ErreurMetier("Compétition introuvable.")
    if _a_deja_un_acces_valide(conn, id_federal, competition_id):
        raise ErreurMetier(
            "Un accès valide existe déjà pour cette compétition -- "
            "utilise ton code existant plutôt que d'en redemander un."
        )
    if _a_deja_une_demande_en_attente(conn, id_federal, competition_id):
        raise ErreurMetier("Une demande est déjà en attente de validation pour cette compétition.")

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


# ------------------------------------------------------------- Message --


def envoyer_message(
    conn: sqlite3.Connection,
    competition_id: str,
    contenu: str,
    id_federal: str | None = None,
) -> Message:
    """Envoie un message -- à un compétiteur précis (``id_federal``
    fourni) ou à tous ceux de la compétition (``id_federal=None``).

    Pas de suivi lu/non lu : envoyer suffit, l'organisateur n'a pas
    besoin de savoir qui l'a vu (choix explicite, voir docs/roadmap.md).
    """
    if db.get_competition(conn, competition_id) is None:
        raise ErreurMetier("Compétition introuvable.")
    if id_federal is not None and db.get_competiteur(conn, id_federal) is None:
        raise ErreurMetier(f"Compétiteur introuvable : {id_federal}")
    if not contenu.strip():
        raise ErreurMetier("Le message ne peut pas être vide.")

    message = Message(
        id=_nouvel_id(),
        competition_id=competition_id,
        contenu=contenu.strip(),
        id_federal=id_federal,
        envoye_le=datetime.now(),
    )
    db.insert_message(conn, message)
    return message


def lister_messages_pour(
    conn: sqlite3.Connection, competition_id: str, id_federal: str
) -> list[Message]:
    """Messages visibles par ce compétiteur : les siens + ceux adressés
    à tous, du plus récent au plus ancien (voir db.list_messages_for)."""
    if db.get_competiteur(conn, id_federal) is None:
        raise ErreurMetier(f"Compétiteur introuvable : {id_federal}")
    return db.list_messages_for(conn, competition_id, id_federal)


def lister_messages_envoyes(conn: sqlite3.Connection, competition_id: str) -> list[Message]:
    """Historique complet des messages envoyés pour cette compétition,
    tous destinataires confondus -- pour l'écran organisateur."""
    return db.list_messages_by_competition(conn, competition_id)
