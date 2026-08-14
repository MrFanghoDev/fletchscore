"""Sauvegarde/restauration d'une compétition complète -- issue #7,
"Extension -- Import/export de compétitions" (besoin 1, voir
docs/roadmap.md) : archiver une compétition, ou la transférer d'une
machine à une autre.

Format JSON auto-descriptif (pas de dépendance externe -- cohérent avec
la philosophie "stdlib d'abord" du projet, voir CLAUDE.md), pensé pour
être autoportant : en plus de la compétition/épreuves/inscriptions/
scores proprement dits, embarque aussi les clubs, compétiteurs et
barèmes référencés -- sans ça, réimporter sur une machine qui ne les
connaît pas déjà échouerait sur des clés étrangères manquantes. Ceux
déjà présents sur la machine cible sont réutilisés tels quels plutôt
que dupliqués (voir ``importer_competition``).

Volontairement hors périmètre : tokens, demandes de rattachement,
procurations, messages -- état d'accès/session propre à la machine
d'origine, pas des données "de compétition" à proprement parler (un
token exporté serait de toute façon inutilisable, seul son hash est
stocké, jamais le secret en clair).
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import date
from typing import TextIO

from fletchscore.models import (
    Bareme,
    Club,
    Competiteur,
    Competition,
    Epreuve,
    Inscription,
    Score,
    Sexe,
    StatutCompetition,
    StatutScore,
)
from fletchscore.storage import db

FORMAT_VERSION = 1


class ErreurSauvegarde(Exception):
    """Erreur attendue (compétition introuvable, déjà restaurée,
    fichier corrompu...) -- à afficher telle quelle à l'organisateur,
    même principe que ``services.ErreurMetier`` mais sans dépendre de
    ``services`` (``io/`` reste un module bas niveau, voir
    ``import_csv.py``)."""


@dataclass(slots=True)
class RapportRestauration:
    competition_id: str
    reussi: bool = False
    epreuves_importees: int = 0
    inscriptions_importees: int = 0
    scores_importes: int = 0
    clubs_reutilises: int = 0
    clubs_importes: int = 0
    competiteurs_reutilises: int = 0
    competiteurs_importes: int = 0
    baremes_reutilises: int = 0
    baremes_importes: int = 0


def formater_rapport_restauration(rapport: RapportRestauration) -> str:
    """Résumé lisible d'un RapportRestauration -- même esprit que
    ``import_csv.formater_rapport``."""
    return (
        f"Compétition {rapport.competition_id} restaurée : "
        f"{rapport.epreuves_importees} épreuve(s), "
        f"{rapport.inscriptions_importees} inscription(s), "
        f"{rapport.scores_importes} score(s). "
        f"Clubs : {rapport.clubs_importes} importé(s), "
        f"{rapport.clubs_reutilises} déjà présent(s). "
        f"Compétiteurs : {rapport.competiteurs_importes} importé(s), "
        f"{rapport.competiteurs_reutilises} déjà présent(s). "
        f"Barèmes : {rapport.baremes_importes} importé(s), "
        f"{rapport.baremes_reutilises} déjà présent(s)."
    )


def _ouvrir_ecriture(destination: str | TextIO) -> TextIO:
    if isinstance(destination, str):
        return open(destination, "w", encoding="utf-8")
    return destination


def _ouvrir_lecture(source: str | TextIO) -> TextIO:
    if isinstance(source, str):
        return open(source, encoding="utf-8")
    return source


# ---------------------------------------------------- Sérialisation --


def _competition_vers_dict(c: Competition) -> dict:
    return {
        "id": c.id,
        "nom": c.nom,
        "date_debut": c.date_debut.isoformat(),
        "date_fin": c.date_fin.isoformat(),
        "lieu": c.lieu,
        "statut": c.statut.value,
        "categories_veteran_actives": c.categories_veteran_actives,
    }


def _dict_vers_competition(d: dict) -> Competition:
    return Competition(
        id=d["id"],
        nom=d["nom"],
        date_debut=date.fromisoformat(d["date_debut"]),
        date_fin=date.fromisoformat(d["date_fin"]),
        lieu=d.get("lieu", ""),
        statut=StatutCompetition(d["statut"]),
        categories_veteran_actives=d.get("categories_veteran_actives", False),
    )


def _epreuve_vers_dict(e: Epreuve) -> dict:
    return {
        "id": e.id,
        "competition_id": e.competition_id,
        "nom": e.nom,
        "date": e.date.isoformat(),
        "bareme_id": e.bareme_id,
    }


def _dict_vers_epreuve(d: dict) -> Epreuve:
    return Epreuve(
        id=d["id"],
        competition_id=d["competition_id"],
        nom=d["nom"],
        date=date.fromisoformat(d["date"]),
        bareme_id=d["bareme_id"],
    )


def _club_vers_dict(c: Club) -> dict:
    return {"code_club": c.code_club, "nom": c.nom, "ville": c.ville}


def _dict_vers_club(d: dict) -> Club:
    return Club(code_club=d["code_club"], nom=d["nom"], ville=d.get("ville", ""))


def _competiteur_vers_dict(c: Competiteur) -> dict:
    return {
        "id_federal": c.id_federal,
        "nom": c.nom,
        "prenom": c.prenom,
        "code_club": c.code_club,
        "sexe": c.sexe.value,
        "date_naissance": c.date_naissance.isoformat(),
        "code_style": c.code_style,
        "licence_valide_jusqu_au": (
            c.licence_valide_jusqu_au.isoformat() if c.licence_valide_jusqu_au else None
        ),
    }


def _dict_vers_competiteur(d: dict) -> Competiteur:
    licence = d.get("licence_valide_jusqu_au")
    return Competiteur(
        id_federal=d["id_federal"],
        nom=d["nom"],
        prenom=d["prenom"],
        code_club=d["code_club"],
        sexe=Sexe(d["sexe"]),
        date_naissance=date.fromisoformat(d["date_naissance"]),
        code_style=d["code_style"],
        licence_valide_jusqu_au=date.fromisoformat(licence) if licence else None,
    )


def _bareme_vers_dict(b: Bareme) -> dict:
    return {
        "id": b.id,
        "nom": b.nom,
        "nb_series": b.nb_series,
        "volees_par_serie": b.volees_par_serie,
        "fleches_par_volee": b.fleches_par_volee,
        "valeurs_zones": b.valeurs_zones,
        "departage_par_x": b.departage_par_x,
    }


def _dict_vers_bareme(d: dict) -> Bareme:
    return Bareme(
        id=d["id"],
        nom=d["nom"],
        nb_series=d["nb_series"],
        volees_par_serie=d["volees_par_serie"],
        fleches_par_volee=d["fleches_par_volee"],
        valeurs_zones=d["valeurs_zones"],
        departage_par_x=d.get("departage_par_x", False),
    )


def _inscription_vers_dict(i: Inscription) -> dict:
    return {"id": i.id, "id_federal": i.id_federal, "epreuve_id": i.epreuve_id}


def _dict_vers_inscription(d: dict) -> Inscription:
    return Inscription(id=d["id"], id_federal=d["id_federal"], epreuve_id=d["epreuve_id"])


def _score_vers_dict(s: Score) -> dict:
    return {
        "id": s.id,
        "inscription_id": s.inscription_id,
        "total": s.total,
        "nombre_x": s.nombre_x,
        "statut": s.statut.value,
        "propose_par_id_federal": s.propose_par_id_federal,
    }


def _dict_vers_score(d: dict) -> Score:
    return Score(
        id=d["id"],
        inscription_id=d["inscription_id"],
        total=d["total"],
        nombre_x=d.get("nombre_x", 0),
        statut=StatutScore(d["statut"]),
        propose_par_id_federal=d.get("propose_par_id_federal"),
    )


# --------------------------------------------------------- Export --


def exporter_competition(
    conn: sqlite3.Connection, competition_id: str, destination: str | TextIO
) -> None:
    """Exporte une compétition complète (épreuves, inscriptions, scores)
    -- plus les clubs/compétiteurs/barèmes référencés, pour que le
    fichier soit réimportable seul sur une autre machine."""
    competition = db.get_competition(conn, competition_id)
    if competition is None:
        raise ErreurSauvegarde(f"Compétition introuvable : {competition_id}")

    epreuves = db.list_epreuves_by_competition(conn, competition_id)

    inscriptions: list[Inscription] = []
    scores: list[Score] = []
    ids_federaux: set[str] = set()
    ids_baremes: set[str] = set()
    for epreuve in epreuves:
        ids_baremes.add(epreuve.bareme_id)
        for inscription in db.list_inscriptions_by_epreuve(conn, epreuve.id):
            inscriptions.append(inscription)
            ids_federaux.add(inscription.id_federal)
            score = db.get_score_by_inscription(conn, inscription.id)
            if score is not None:
                scores.append(score)

    competiteurs = [
        c
        for c in (db.get_competiteur(conn, id_federal) for id_federal in sorted(ids_federaux))
        if c is not None
    ]
    codes_clubs = {c.code_club for c in competiteurs}
    clubs = [c for c in (db.get_club(conn, code) for code in sorted(codes_clubs)) if c is not None]
    baremes = [
        b for b in (db.get_bareme(conn, bareme_id) for bareme_id in sorted(ids_baremes)) if b
    ]

    donnees = {
        "format_version": FORMAT_VERSION,
        "competition": _competition_vers_dict(competition),
        "epreuves": [_epreuve_vers_dict(e) for e in epreuves],
        "clubs": [_club_vers_dict(c) for c in clubs],
        "competiteurs": [_competiteur_vers_dict(c) for c in competiteurs],
        "baremes": [_bareme_vers_dict(b) for b in baremes],
        "inscriptions": [_inscription_vers_dict(i) for i in inscriptions],
        "scores": [_score_vers_dict(s) for s in scores],
    }

    fichier = _ouvrir_ecriture(destination)
    try:
        json.dump(donnees, fichier, ensure_ascii=False, indent=2)
    finally:
        if isinstance(destination, str):
            fichier.close()


# -------------------------------------------------------- Import --


def importer_competition(conn: sqlite3.Connection, source: str | TextIO) -> RapportRestauration:
    """Restaure une compétition exportée par ``exporter_competition``.

    Refuse si une compétition avec le même id existe déjà (déjà
    restaurée précédemment ?) -- pas de fusion, un import réussi ou pas
    du tout. Clubs/compétiteurs/barèmes déjà présents sur la machine
    cible (même code_club/id_federal/id) sont réutilisés tels quels,
    jamais dupliqués ni écrasés. Compétition/épreuves/inscriptions/
    scores écrits en une seule transaction (voir
    ``db.importer_donnees_competition``) -- une compétition à moitié
    restaurée serait pire qu'un échec net.
    """
    fichier = _ouvrir_lecture(source)
    try:
        donnees = json.load(fichier)
    finally:
        if isinstance(source, str):
            fichier.close()

    version = donnees.get("format_version")
    if version != FORMAT_VERSION:
        raise ErreurSauvegarde(
            f"Format de sauvegarde non supporté (version {version!r}, "
            f"attendu {FORMAT_VERSION})."
        )

    competition = _dict_vers_competition(donnees["competition"])
    if db.get_competition(conn, competition.id) is not None:
        raise ErreurSauvegarde(
            f"Une compétition avec l'id « {competition.id} » existe déjà -- "
            "déjà restaurée précédemment ?"
        )

    epreuves = [_dict_vers_epreuve(e) for e in donnees["epreuves"]]
    clubs = [_dict_vers_club(c) for c in donnees["clubs"]]
    competiteurs = [_dict_vers_competiteur(c) for c in donnees["competiteurs"]]
    baremes = [_dict_vers_bareme(b) for b in donnees["baremes"]]
    inscriptions = [_dict_vers_inscription(i) for i in donnees["inscriptions"]]
    scores = [_dict_vers_score(s) for s in donnees["scores"]]

    rapport = RapportRestauration(competition_id=competition.id)

    clubs_a_creer = []
    for club in clubs:
        if db.get_club(conn, club.code_club) is not None:
            rapport.clubs_reutilises += 1
        else:
            clubs_a_creer.append(club)
            rapport.clubs_importes += 1

    baremes_a_creer = []
    for bareme in baremes:
        if db.get_bareme(conn, bareme.id) is not None:
            rapport.baremes_reutilises += 1
        else:
            baremes_a_creer.append(bareme)
            rapport.baremes_importes += 1

    competiteurs_a_creer = []
    for competiteur in competiteurs:
        if db.get_competiteur(conn, competiteur.id_federal) is not None:
            rapport.competiteurs_reutilises += 1
        else:
            competiteurs_a_creer.append(competiteur)
            rapport.competiteurs_importes += 1

    db.importer_donnees_competition(
        conn,
        competition=competition,
        epreuves=epreuves,
        clubs_a_creer=clubs_a_creer,
        competiteurs_a_creer=competiteurs_a_creer,
        baremes_a_creer=baremes_a_creer,
        inscriptions=inscriptions,
        scores=scores,
    )

    rapport.epreuves_importees = len(epreuves)
    rapport.inscriptions_importees = len(inscriptions)
    rapport.scores_importes = len(scores)
    rapport.reussi = True
    return rapport
