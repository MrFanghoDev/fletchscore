"""Enums partagés entre les entités du modèle de données FletchScore.

Values are stored as plain strings in SQLite (see storage/db.py) -- using
str, Enum keeps comparisons and serialization simple without a custom
adapter.
"""

from enum import Enum


class Sexe(str, Enum):
    F = "F"
    M = "M"


class DivisionAge(str, Enum):
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


class StatutCompetition(str, Enum):
    OUVERTE = "ouverte"
    CLOTUREE = "cloturee"


class StatutScore(str, Enum):
    PROPOSE = "propose"
    VALIDE = "valide"
    REJETE = "rejete"


class StatutToken(str, Enum):
    EMIS = "emis"
    DISTRIBUE = "distribue"
    UTILISE = "utilise"
    REVOQUE = "revoque"


class StatutDemandeRattachement(str, Enum):
    EN_ATTENTE = "en_attente"
    VALIDEE = "validee"
    REJETEE = "rejetee"
