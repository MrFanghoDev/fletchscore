"""Entité Compétition -- regroupe une ou plusieurs Épreuves."""

from dataclasses import dataclass
from datetime import date

from fletchscore.models.enums import StatutCompetition


@dataclass(slots=True)
class Competition:
    id: str
    nom: str
    date_debut: date
    date_fin: date
    lieu: str = ""
    statut: StatutCompetition = StatutCompetition.OUVERTE
    categories_veteran_actives: bool = False
    """Active ou non les divisions Veteran/Senior pour cette compétition
    -- le règlement les laisse optionnelles, voir
    fletchscore.models.competiteur.categorie_age."""
    code_club: str | None = None
    """Club organisateur -- optionnel (issue #48), distinct du club de
    chaque compétiteur. ``None`` pour une compétition inter-clubs ou
    fédérale sans club organisateur unique identifié."""

    def couvre(self, jour: date) -> bool:
        return self.date_debut <= jour <= self.date_fin
