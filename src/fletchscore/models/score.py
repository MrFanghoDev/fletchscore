"""Entité Score -- une volée tirée, rattachée à une Inscription.

L'application des cas particuliers du règlement (flèches en trop/
manquantes, mauvaise cible...) est de la responsabilité de la couche
scoring/ (prochain jalon, voir docs/roadmap.md) -- ce modèle se contente
de stocker fidèlement ce qui a été saisi/proposé.
"""

from dataclasses import dataclass, field

from fletchscore.models.enums import StatutScore


@dataclass(slots=True)
class Score:
    id: str
    inscription_id: str
    numero_volee: int
    valeurs: list[int] = field(default_factory=list)
    """Valeur de chaque flèche de la volée, dans l'ordre de tir."""
    nombre_x: int = 0
    """Nombre de flèches en zone X dans cette volée -- critère de
    départage uniquement, jamais ajouté au total (voir Bareme.departage_par_x)."""
    statut: StatutScore = StatutScore.PROPOSE

    @property
    def total(self) -> int:
        return sum(self.valeurs)
