"""Entité Score -- une volée tirée, rattachée à une Inscription.

L'application des cas particuliers du règlement (flèches en trop/
manquantes, mauvaise cible...) est de la responsabilité de la couche
scoring/ (voir fletchscore.scoring) -- ce modèle se contente de stocker
fidèlement ce qui a été saisi/proposé.
"""

from dataclasses import dataclass, field

from fletchscore.models.enums import StatutScore


@dataclass(slots=True)
class Score:
    id: str
    inscription_id: str
    numero_serie: int
    """Numéro de la série (1 à Bareme.nb_series) -- une volée seule ne
    suffit pas à identifier une saisie sans ambiguïté : le Flint Indoor a
    2 séries de 7 volées chacune, donc "volée 1" existe deux fois par
    inscription sans ce champ."""
    numero_volee: int
    """Numéro de la volée au sein de sa série (1 à
    Bareme.volees_par_serie)."""
    valeurs: list[int] = field(default_factory=list)
    """Valeur de chaque flèche de la volée, dans l'ordre de tir."""
    nombre_x: int = 0
    """Nombre de flèches en zone X dans cette volée -- critère de
    départage uniquement, jamais ajouté au total (voir Bareme.departage_par_x)."""
    statut: StatutScore = StatutScore.PROPOSE

    @property
    def total(self) -> int:
        return sum(self.valeurs)
