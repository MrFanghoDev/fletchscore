"""Entité Inscription -- lien Compétiteur <-> Épreuve."""

from dataclasses import dataclass


@dataclass(slots=True)
class Inscription:
    id: str
    id_federal: str
    epreuve_id: str
