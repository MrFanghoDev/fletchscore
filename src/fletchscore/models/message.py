"""Entité Message -- envoyé par l'organisateur, à un compétiteur précis
ou à tous ceux d'une compétition.

Demande de l'utilisateur, sans équivalent dans le cahier des charges
initial -- voir docs/roadmap.md pour le cadrage retenu (historique
persistant, pas de suivi lu/non lu par compétiteur).
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Message:
    id: str
    competition_id: str
    contenu: str
    id_federal: str | None = None
    """``None`` = message envoyé à tous les compétiteurs de la
    compétition ; sinon, un id fédéral précis -- message ciblé, visible
    seulement par cette personne (une fois son identité confirmée par
    cookie de session signé, voir api/competiteur.py)."""
    envoye_le: datetime | None = None
