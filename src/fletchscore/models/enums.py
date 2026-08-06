"""Enums partagés entre les entités du modèle de données FletchScore.

Values are stored as plain strings in SQLite (see storage/db.py) --
StrEnum (Python 3.11+) keeps comparisons and serialization simple
without a custom adapter.
"""

from enum import StrEnum


class Sexe(StrEnum):
    F = "F"
    M = "M"


class DivisionAge(StrEnum):
    """Divisions d'âge officielles IFAA/FFTL.

    VETERAN et SENIOR sont explicitement "optionnelles, non
    contraignantes" dans le règlement -- voir
    :func:`fletchscore.models.competiteur.categorie_age`, qui n'y bascule
    que si la compétition les active.
    """

    CUB = "cub"
    JUNIOR = "junior"
    YOUNG_ADULT = "young_adult"
    ADULT = "adult"
    VETERAN = "veteran"
    SENIOR = "senior"


class StatutCompetition(StrEnum):
    OUVERTE = "ouverte"
    CLOTUREE = "cloturee"


class StatutScore(StrEnum):
    PROPOSE = "propose"
    VALIDE = "valide"
    REJETE = "rejete"


class StatutToken(StrEnum):
    EMIS = "emis"
    DISTRIBUE = "distribue"
    UTILISE = "utilise"
    REVOQUE = "revoque"


class StatutDemandeRattachement(StrEnum):
    EN_ATTENTE = "en_attente"
    VALIDEE = "validee"
    REJETEE = "rejetee"


class StatutProcuration(StrEnum):
    EN_ATTENTE = "en_attente"
    VALIDEE = "validee"
    REJETEE = "rejetee"
    REVOQUEE = "revoquee"
