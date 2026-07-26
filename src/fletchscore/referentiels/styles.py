"""Référentiel Style -- lecture et extension locale.

La base des 12 codes IFAA est pré-remplie via
fletchscore.storage.db.seed_referentiel_styles (idempotent, appelée au
démarrage). Ce module ne gère que ce qui vient éventuellement s'ajouter
par-dessus : une variante FFTL locale non couverte par le règlement IFAA
-- point ouvert du cahier des charges, non tranché à ce stade (voir
docs/roadmap.md).
"""

from __future__ import annotations

import sqlite3

from fletchscore.models import Style
from fletchscore.storage import db


def styles_disponibles(conn: sqlite3.Connection) -> list[Style]:
    """Styles IFAA + variantes locales ajoutées par le club, triés par
    code."""
    return db.list_styles(conn)


def ajouter_variante_style(
    conn: sqlite3.Connection, code: str, libelle: str, libelle_en: str = ""
) -> None:
    """Ajoute une variante de style non couverte par les 12 codes IFAA.

    Refuse explicitement d'écraser un code déjà existant (IFAA ou
    variante précédemment ajoutée) -- une variante locale doit avoir un
    code qui lui est propre, jamais réutiliser un code IFAA existant pour
    éviter toute ambiguïté dans les classements par catégorie.
    """
    if db.get_style(conn, code) is not None:
        raise ValueError(
            f"Le code de style '{code}' existe déjà -- choisis un code "
            "distinct pour ta variante locale."
        )
    db.insert_style(conn, Style(code, libelle, libelle_en))
