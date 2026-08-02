"""Entité Barème -- définit la structure de score d'un type de round."""

from dataclasses import dataclass


@dataclass(slots=True)
class Bareme:
    id: str
    nom: str
    nb_series: int
    volees_par_serie: int
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
        return self.nb_series * self.volees_par_serie * self.fleches_par_volee

    @property
    def score_max(self) -> int:
        return self.total_flèches * self.valeurs_zones[0]


# Templates préconfigurés, directement dérivés du règlement IFAA/FFTL --
# voir docs/cahier-des-charges/regles-metier.rst §4.1. Les `id` sont
# stables (utilisés comme clés de référence, ex. dans les tests et les
# imports) : ne jamais les changer une fois publiés.
BAREME_FLINT_INDOOR = Bareme(
    id="flint-indoor",
    nom="Flint Indoor Round",
    nb_series=2,
    volees_par_serie=7,
    fleches_par_volee=4,
    valeurs_zones=[5, 4, 3],
    departage_par_x=False,
)

BAREME_IFAA_INDOOR = Bareme(
    id="ifaa-indoor",
    nom="IFAA Indoor Round",
    nb_series=2,
    volees_par_serie=6,
    fleches_par_volee=5,
    valeurs_zones=[5, 4, 3, 2, 1],
    departage_par_x=True,
)

# Field, Hunter, International et Expert Field -- confirmés dans le
# règlement IFAA (14 ou 20 cibles marquées, nombre de flèches fixe par
# cible, score constant quelle que soit la distance) : s'intègrent au
# modèle Bareme tel quel. nb_series=1 pour Field/Hunter/Expert Field :
# le règlement ne précise nulle part si un round complet représente 1
# ou 2 "unités standard" (contrairement à Flint/IFAA Indoor qui le disent
# explicitement) -- valeur la plus prudente en l'absence de confirmation,
# à corriger si l'usage du club en dit autrement.
#
# Volontairement HORS PÉRIMÈTRE : Animal Round (marqué et non marqué) et
# les rounds 3-D. Leur système de score est fondamentalement différent
# (zones "kill"/"wound", arrêt dès le premier impact, jusqu'à 3 flèches
# par cible à valeur décroissante selon le numéro de la flèche) -- ça
# demanderait un moteur de score distinct, pas seulement un nouveau
# Bareme. Voir docs/roadmap.md.
BAREME_FIELD = Bareme(
    id="field",
    nom="Field Round",
    nb_series=1,
    volees_par_serie=14,
    fleches_par_volee=4,
    valeurs_zones=[5, 4, 3],
    departage_par_x=False,
)

BAREME_HUNTER = Bareme(
    id="hunter",
    nom="Hunter Round",
    nb_series=1,
    volees_par_serie=14,
    fleches_par_volee=4,
    valeurs_zones=[5, 4, 3],
    departage_par_x=False,
)

BAREME_INTERNATIONAL = Bareme(
    id="international",
    nom="International Round",
    nb_series=2,
    volees_par_serie=10,
    fleches_par_volee=3,
    valeurs_zones=[5, 4, 3],
    departage_par_x=False,
)

BAREME_EXPERT_FIELD = Bareme(
    id="expert-field",
    nom="Expert Field Round",
    nb_series=1,
    volees_par_serie=14,
    fleches_par_volee=4,
    valeurs_zones=[5, 4, 3, 2, 1],
    departage_par_x=True,
)

BAREMES_PRECONFIGURES: list[Bareme] = [
    BAREME_FLINT_INDOOR,
    BAREME_IFAA_INDOOR,
    BAREME_FIELD,
    BAREME_HUNTER,
    BAREME_INTERNATIONAL,
    BAREME_EXPERT_FIELD,
]
