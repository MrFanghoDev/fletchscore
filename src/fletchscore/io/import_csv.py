"""Import des référentiels clubs.csv et competiteurs.csv.

Règle centrale (voir docs/cahier-des-charges/modele-donnees.rst §6.1) :
si un code_club ou code_style référencé n'existe pas dans son référentiel,
la ligne est REJETÉE avec un message explicite -- jamais de création
automatique silencieuse, pour éviter les doublons du type "ALFP" /
"Archers Libres FP".

Toutes les fonctions acceptent soit un chemin de fichier (str), soit un
objet texte déjà ouvert (io.StringIO en test, un fichier uploadé...) --
ça évite de dépendre du système de fichiers réel dans les tests
unitaires.
"""

from __future__ import annotations

import csv
import sqlite3
from dataclasses import dataclass, field
from datetime import date
from typing import TextIO

from fletchscore.models import Club, Competiteur, Sexe
from fletchscore.storage import db


@dataclass(slots=True)
class ErreurImport:
    numero_ligne: int
    """Numéro de ligne dans le fichier source, en-tête comprise (la
    première ligne de données est donc la ligne 2) -- pour que le message
    corresponde à ce que l'organisateur voit s'il ouvre le fichier dans
    un tableur."""
    message: str


@dataclass(slots=True)
class RapportImport:
    lignes_traitees: int = 0
    importees: int = 0
    ignorees: int = 0
    """Lignes valides mais déjà présentes en base (ex. club déjà importé
    lors d'une session précédente) -- pas une erreur, juste un import
    idempotent."""
    erreurs: list[ErreurImport] = field(default_factory=list)

    @property
    def succes(self) -> bool:
        return not self.erreurs


def _ouvrir(source: str | TextIO) -> TextIO:
    if isinstance(source, str):
        return open(source, encoding="utf-8-sig", newline="")
    return source


_COLONNES_CLUBS = {"code_club", "nom"}
_COLONNES_COMPETITEURS = {
    "id_federal",
    "nom",
    "prenom",
    "code_club",
    "sexe",
    "date_naissance",
    "code_style",
}


def import_clubs(conn: sqlite3.Connection, source: str | TextIO) -> RapportImport:
    """Importe clubs.csv -- colonnes attendues : code_club, nom, ville
    (ville optionnelle)."""
    rapport = RapportImport()
    fichier = _ouvrir(source)
    try:
        lecteur = csv.DictReader(fichier)
        colonnes_manquantes = _COLONNES_CLUBS - set(lecteur.fieldnames or [])
        if colonnes_manquantes:
            rapport.erreurs.append(
                ErreurImport(
                    numero_ligne=1,
                    message=f"Colonne(s) manquante(s) : {', '.join(sorted(colonnes_manquantes))}",
                )
            )
            return rapport

        codes_vus_dans_ce_fichier: set[str] = set()
        for numero_ligne, ligne in enumerate(lecteur, start=2):
            rapport.lignes_traitees += 1
            code_club = (ligne.get("code_club") or "").strip()
            nom = (ligne.get("nom") or "").strip()
            ville = (ligne.get("ville") or "").strip()

            if not code_club:
                rapport.erreurs.append(ErreurImport(numero_ligne, "code_club manquant ou vide"))
                continue
            if not nom:
                rapport.erreurs.append(ErreurImport(numero_ligne, "nom manquant ou vide"))
                continue
            if code_club in codes_vus_dans_ce_fichier:
                rapport.erreurs.append(
                    ErreurImport(
                        numero_ligne,
                        f"code_club '{code_club}' apparaît plusieurs fois dans ce fichier",
                    )
                )
                continue

            if db.get_club(conn, code_club) is not None:
                rapport.ignorees += 1
                codes_vus_dans_ce_fichier.add(code_club)
                continue

            db.insert_club(conn, Club(code_club, nom, ville))
            codes_vus_dans_ce_fichier.add(code_club)
            rapport.importees += 1
    finally:
        if isinstance(source, str):
            fichier.close()

    return rapport


def import_competiteurs(conn: sqlite3.Connection, source: str | TextIO) -> RapportImport:
    """Importe competiteurs.csv -- colonnes attendues : id_federal, nom,
    prenom, code_club, sexe, date_naissance, code_style
    (licence_valide_jusqu_au optionnelle).

    code_club et code_style doivent déjà exister dans leurs référentiels
    respectifs -- une ligne qui en référence un absent est rejetée, pas
    corrigée automatiquement (voir docstring du module)."""
    rapport = RapportImport()
    fichier = _ouvrir(source)
    try:
        lecteur = csv.DictReader(fichier)
        colonnes_manquantes = _COLONNES_COMPETITEURS - set(lecteur.fieldnames or [])
        if colonnes_manquantes:
            rapport.erreurs.append(
                ErreurImport(
                    numero_ligne=1,
                    message=f"Colonne(s) manquante(s) : {', '.join(sorted(colonnes_manquantes))}",
                )
            )
            return rapport

        ids_vus_dans_ce_fichier: set[str] = set()
        for numero_ligne, ligne in enumerate(lecteur, start=2):
            rapport.lignes_traitees += 1
            erreur = _valider_et_inserer_competiteur(
                conn, ligne, numero_ligne, ids_vus_dans_ce_fichier
            )
            if erreur is not None:
                rapport.erreurs.append(erreur)
                continue
            rapport.importees += 1
    finally:
        if isinstance(source, str):
            fichier.close()

    return rapport


def _valider_et_inserer_competiteur(
    conn: sqlite3.Connection,
    ligne: dict[str, str],
    numero_ligne: int,
    ids_vus_dans_ce_fichier: set[str],
) -> ErreurImport | None:
    id_federal = (ligne.get("id_federal") or "").strip()
    nom = (ligne.get("nom") or "").strip()
    prenom = (ligne.get("prenom") or "").strip()
    code_club = (ligne.get("code_club") or "").strip()
    sexe_brut = (ligne.get("sexe") or "").strip().upper()
    date_naissance_brute = (ligne.get("date_naissance") or "").strip()
    code_style = (ligne.get("code_style") or "").strip()
    licence_brute = (ligne.get("licence_valide_jusqu_au") or "").strip()

    if not id_federal:
        return ErreurImport(numero_ligne, "id_federal manquant ou vide")
    if not nom:
        return ErreurImport(numero_ligne, "nom manquant ou vide")
    if not prenom:
        return ErreurImport(numero_ligne, "prenom manquant ou vide")

    if id_federal in ids_vus_dans_ce_fichier:
        return ErreurImport(
            numero_ligne,
            f"id_federal '{id_federal}' apparaît plusieurs fois dans ce fichier",
        )
    if db.get_competiteur(conn, id_federal) is not None:
        return ErreurImport(
            numero_ligne,
            f"id_federal '{id_federal}' existe déjà en base -- pas de mise à "
            "jour automatique, corrige ou retire la fiche existante d'abord",
        )

    if sexe_brut not in ("F", "M"):
        return ErreurImport(numero_ligne, f"sexe invalide '{sexe_brut}' -- attendu 'F' ou 'M'")

    try:
        date_naissance = date.fromisoformat(date_naissance_brute)
    except ValueError:
        return ErreurImport(
            numero_ligne,
            f"date_naissance invalide '{date_naissance_brute}' -- format attendu AAAA-MM-JJ",
        )

    licence_valide_jusqu_au: date | None = None
    if licence_brute:
        try:
            licence_valide_jusqu_au = date.fromisoformat(licence_brute)
        except ValueError:
            return ErreurImport(
                numero_ligne,
                f"licence_valide_jusqu_au invalide '{licence_brute}' -- format attendu AAAA-MM-JJ",
            )

    if not code_club:
        return ErreurImport(numero_ligne, "code_club manquant ou vide")
    if db.get_club(conn, code_club) is None:
        return ErreurImport(
            numero_ligne,
            f"code_club '{code_club}' inconnu -- importe d'abord clubs.csv, "
            "ou vérifie l'orthographe (aucune création automatique)",
        )

    if not code_style:
        return ErreurImport(numero_ligne, "code_style manquant ou vide")
    if db.get_style(conn, code_style) is None:
        return ErreurImport(
            numero_ligne,
            f"code_style '{code_style}' inconnu -- vérifie le référentiel de "
            "styles (aucune création automatique)",
        )

    competiteur = Competiteur(
        id_federal=id_federal,
        nom=nom,
        prenom=prenom,
        code_club=code_club,
        sexe=Sexe(sexe_brut),
        date_naissance=date_naissance,
        code_style=code_style,
        licence_valide_jusqu_au=licence_valide_jusqu_au,
    )
    db.insert_competiteur(conn, competiteur)
    ids_vus_dans_ce_fichier.add(id_federal)
    return None
