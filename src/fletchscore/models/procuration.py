"""Entité Procuration -- autorise un compétiteur (le mandataire) à
proposer un score au nom d'un autre (le mandant), pour une compétition
donnée.

Cas d'usage réel : sur un pas de tir, une seule personne note souvent
les scores de tout le groupe plutôt que chacun sorte son téléphone.
Demandé par l'utilisateur -- toujours soumis à validation humaine de
l'organisateur avant de produire le moindre effet (même principe que
DemandeRattachement) : jamais de proposition au nom d'autrui possible
tant qu'une Procuration n'est pas VALIDEE.
"""

from dataclasses import dataclass
from datetime import datetime

from fletchscore.models.enums import StatutProcuration


@dataclass(slots=True)
class Procuration:
    id: str
    competition_id: str
    id_federal_mandataire: str
    """Celui qui va proposer des scores -- typiquement le scoreur du
    groupe."""
    id_federal_mandant: str
    """Celui pour qui les scores seront proposés."""
    statut: StatutProcuration = StatutProcuration.EN_ATTENTE
    demandee_le: datetime | None = None
