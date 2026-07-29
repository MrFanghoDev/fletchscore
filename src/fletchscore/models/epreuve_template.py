"""Entité EpreuveTemplate -- modèle d'épreuve réutilisable.

Une Épreuve a trois données : nom, date, barème. La date est propre à
chaque compétition (jamais réutilisable), mais nom + barème forment
souvent un même "type d'épreuve" répété d'une compétition à l'autre
(ex. "IFAA Indoor" avec le barème ifaa-indoor) -- ce modèle capture
uniquement cette partie réutilisable.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class EpreuveTemplate:
    id: str
    nom: str
    bareme_id: str
