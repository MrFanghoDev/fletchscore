"""Entité Score -- le score final d'une Inscription à son épreuve.

Simplifié à un total + un compteur de X (pas une saisie flèche par
flèche ni volée par volée) : décision prise après un premier jalon de
saisie détaillée, jugée trop lourde face à l'usage réel -- les scores
sont déjà totalisés à la main sur la feuille de match pendant le tir, le
rôle de FletchScore est d'enregistrer ce résultat et de classer, pas de
rejouer le calcul flèche par flèche. Voir docs/architecture.md.

Une seule ligne par Inscription (contrainte UNIQUE en base, voir
storage/db.py) -- pas une liste de volées.
"""

from dataclasses import dataclass

from fletchscore.models.enums import StatutScore


@dataclass(slots=True)
class Score:
    id: str
    inscription_id: str
    total: int
    """Score final tel que totalisé sur la feuille de match."""
    nombre_x: int = 0
    """Nombre de flèches en zone X sur l'ensemble de l'épreuve --
    critère de départage uniquement, jamais ajouté au total (voir
    Bareme.departage_par_x)."""
    statut: StatutScore = StatutScore.PROPOSE
