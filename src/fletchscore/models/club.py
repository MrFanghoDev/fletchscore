"""Référentiel Club."""

from dataclasses import dataclass


@dataclass(slots=True)
class Club:
    code_club: str
    nom: str
    ville: str = ""
