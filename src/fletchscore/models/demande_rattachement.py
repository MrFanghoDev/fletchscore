"""Entité DemandeRattachement -- attribution de token a posteriori.

Objet transitoire : un compétiteur qui n'a pas reçu de token à
l'inscription se retrouve dans une liste des inscrits, demande un
rattachement, et un organisateur valide après vérification visuelle de
l'identité -- le token n'est généré qu'à ce moment-là, jamais avant. Voir
docs/cahier-des-charges/securite.rst §7.3.
"""

from dataclasses import dataclass
from datetime import datetime

from fletchscore.models.enums import StatutDemandeRattachement


@dataclass(slots=True)
class DemandeRattachement:
    id: str
    id_federal: str
    competition_id: str
    statut: StatutDemandeRattachement = StatutDemandeRattachement.EN_ATTENTE
    horodatage: datetime | None = None
