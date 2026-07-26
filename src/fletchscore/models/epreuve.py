"""Entité Épreuve -- une session de tir avec un barème donné."""

from dataclasses import dataclass
from datetime import date


@dataclass(slots=True)
class Epreuve:
    id: str
    competition_id: str
    nom: str
    date: date
    bareme_id: str
