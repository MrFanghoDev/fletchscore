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
from fletchscore.scoring import classement_par_categorie, normaliser_volee
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


def parser_valeurs_fleches(textes: list[str]) -> list[int]:
    """Convertit les champs de saisie d'une volée (un texte par flèche)
    en liste d'entiers.

    Les champs vides sont ignorés plutôt que convertis en 0 : une volée
    incomplète doit passer par ``normaliser_volee`` (via
    ``saisir_volee``), qui applique la bonne règle du barème (compléter
    à 0), plutôt que d'imposer 0 ici pour un champ simplement pas encore
    rempli par l'organisateur.
    """
    valeurs: list[int] = []
    for texte in textes:
        texte = texte.strip()
        if not texte:
            continue
        try:
            valeurs.append(int(texte))
        except ValueError as erreur:
            raise ErreurMetier(
                f"Valeur de flèche invalide : « {texte} » -- un nombre entier est attendu"
            ) from erreur
    return valeurs


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


def saisir_volee(
    conn: sqlite3.Connection,
    inscription_id: str,
    numero_serie: int,
    numero_volee: int,
    valeurs: list[int],
    *,
    nombre_x: int = 0,
    statut: StatutScore = StatutScore.VALIDE,
) -> Score:
    """Enregistre (ou corrige) une volée saisie par l'organisateur.

    Les valeurs passent par ``normaliser_volee`` : flèches en trop
    ramenées aux N plus faibles, flèches manquantes complétées à 0. Une
    valeur hors zones du barème est refusée (``ErreurMetier``) plutôt que
    corrigée silencieusement -- c'est un signal de saisie erronée.

    Le statut par défaut est ``VALIDE`` : une saisie faite par
    l'organisateur lui-même n'a pas à repasser par une file de validation
    (voir docs/cahier-des-charges/securite.rst §7.2).
    """
    epreuve, bareme = _epreuve_et_bareme_de(conn, inscription_id)

    if not 1 <= numero_serie <= bareme.nb_series:
        raise ErreurMetier(
            f"Numéro de série invalide : {numero_serie} -- ce barème en "
            f"compte {bareme.nb_series}."
        )
    if not 1 <= numero_volee <= bareme.volees_par_serie:
        raise ErreurMetier(
            f"Numéro de volée invalide : {numero_volee} -- ce barème compte "
            f"{bareme.volees_par_serie} volées par série."
        )
    if nombre_x < 0:
        raise ErreurMetier("Le nombre de X ne peut pas être négatif.")
    if nombre_x > bareme.fleches_par_volee:
        raise ErreurMetier(
            f"Le nombre de X ({nombre_x}) dépasse le nombre de flèches de la "
            f"volée ({bareme.fleches_par_volee})."
        )
    if nombre_x > 0 and not bareme.departage_par_x:
        raise ErreurMetier(
            f"Le barème « {bareme.nom} » n'utilise pas de zone X -- laisse ce " "compteur à 0."
        )

    try:
        valeurs_normalisees = normaliser_volee(bareme, valeurs)
    except ValueError as erreur:
        raise ErreurMetier(str(erreur)) from erreur

    score = Score(
        id=_nouvel_id(),
        inscription_id=inscription_id,
        numero_serie=numero_serie,
        numero_volee=numero_volee,
        valeurs=valeurs_normalisees,
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

    entrees: list[tuple[Competiteur, list[Score]]] = []
    for inscription in db.list_inscriptions_by_epreuve(conn, epreuve_id):
        competiteur = db.get_competiteur(conn, inscription.id_federal)
        if competiteur is None:
            continue
        scores = db.list_scores_by_inscription(conn, inscription.id)
        entrees.append((competiteur, scores))

    return classement_par_categorie(
        bareme,
        epreuve.date,
        entrees,
        categories_veteran_actives=competition.categories_veteran_actives,
    )
