"""Entité Barème -- définit la structure de score d'un type de round."""

from dataclasses import dataclass


@dataclass(slots=True)
class Bareme:
    id: str
    nom: str
    nb_unites: int
    volees_par_unite: int
    fleches_par_volee: int
    valeurs_zones: list[int]
    """Valeurs de zones possibles, de la plus haute à la plus basse
    (ex. [5, 4, 3, 2, 1] pour l'IFAA Indoor Round)."""
    departage_par_x: bool = False
    """True si le round utilise un compteur de flèches en zone X comme
    critère de départage (ex. IFAA Indoor Round) -- jamais compté dans le
    score brut, voir docs/cahier-des-charges/regles-metier.rst."""

    def __post_init__(self) -> None:
        if not self.valeurs_zones:
            raise ValueError("Un barème doit définir au moins une valeur de zone.")
        if list(self.valeurs_zones) != sorted(self.valeurs_zones, reverse=True):
            raise ValueError("valeurs_zones doit être trié de la plus haute à la plus basse.")

    @property
    def total_flèches(self) -> int:
        return self.nb_unites * self.volees_par_unite * self.fleches_par_volee

    @property
    def score_max(self) -> int:
        return self.total_flèches * self.valeurs_zones[0]

    def valeur_valide(self, valeur: int) -> bool:
        """0 est toujours une valeur valide (flèche manquée, flèche
        manquante comptée à 0, mauvaise cible -- voir règles métier)."""
        return valeur == 0 or valeur in self.valeurs_zones


# Templates préconfigurés, directement dérivés du règlement IFAA/FFTL --
# voir docs/cahier-des-charges/regles-metier.rst §4.1. Les `id` sont
# stables (utilisés comme clés de référence, ex. dans les tests et les
# imports) : ne jamais les changer une fois publiés.
BAREME_FLINT_INDOOR = Bareme(
    id="flint-indoor",
    nom="Flint Indoor Round",
    nb_unites=2,
    volees_par_unite=7,
    fleches_par_volee=4,
    valeurs_zones=[5, 4, 3],
    departage_par_x=False,
)

BAREME_IFAA_INDOOR = Bareme(
    id="ifaa-indoor",
    nom="IFAA Indoor Round",
    nb_unites=2,
    volees_par_unite=6,
    fleches_par_volee=5,
    valeurs_zones=[5, 4, 3, 2, 1],
    departage_par_x=True,
)

BAREMES_PRECONFIGURES: list[Bareme] = [BAREME_FLINT_INDOOR, BAREME_IFAA_INDOOR]
