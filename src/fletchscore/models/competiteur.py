"""Entité Compétiteur et calcul de la division d'âge officielle."""

from dataclasses import dataclass
from datetime import date

from fletchscore.models.enums import DivisionAge, Sexe


def categorie_age(
    date_naissance: date,
    date_reference: date,
    *,
    categories_veteran_actives: bool = False,
) -> DivisionAge:
    """Détermine la division d'âge IFAA/FFTL à une date donnée.

    L'âge est calculé à la date de référence (l'épreuve), jamais figé sur
    la fiche du compétiteur -- voir
    docs/cahier-des-charges/modele-donnees.rst.

    Veteran (55+) et Senior (65+) sont explicitement "optionnelles, non
    contraignantes" dans le règlement IFAA -- une compétition peut choisir
    de ne pas les distinguer et de tout regrouper sous Adult, d'où le
    paramètre ``categories_veteran_actives`` (résout un point ouvert du
    cahier des charges : ce réglage vit sur l'entité Competition).
    """
    age = date_reference.year - date_naissance.year
    if (date_reference.month, date_reference.day) < (
        date_naissance.month,
        date_naissance.day,
    ):
        age -= 1

    if age < 0:
        raise ValueError("La date de référence précède la date de naissance.")

    if age < 13:
        return DivisionAge.CUB
    if age <= 16:
        return DivisionAge.JUNIOR
    if age <= 20:
        return DivisionAge.YOUNG_ADULT
    if categories_veteran_actives:
        if age >= 65:
            return DivisionAge.SENIOR
        if age >= 55:
            return DivisionAge.VETERAN
    return DivisionAge.ADULT


@dataclass(slots=True)
class Competiteur:
    id_federal: str
    nom: str
    prenom: str
    code_club: str
    sexe: Sexe
    date_naissance: date
    code_style: str
    licence_valide_jusqu_au: date | None = None

    def categorie_age(
        self, date_reference: date, *, categories_veteran_actives: bool = False
    ) -> DivisionAge:
        return categorie_age(
            self.date_naissance,
            date_reference,
            categories_veteran_actives=categories_veteran_actives,
        )

    def licence_valide(self, date_reference: date) -> bool:
        """True si aucune date de validité n'est renseignée (pas de
        contrôle possible) ou si elle n'est pas encore expirée."""
        if self.licence_valide_jusqu_au is None:
            return True
        return date_reference <= self.licence_valide_jusqu_au

    def code_categorie(
        self, date_reference: date, *, categories_veteran_actives: bool = False
    ) -> str:
        """Code combiné sexe + division d'âge + style, ex. ``AMBB-R``
        (Adulte Homme Barebow-Recurve) -- voir la nomenclature officielle
        dans docs/cahier-des-charges/regles-metier.rst."""
        prefixe_age = {
            DivisionAge.CUB: "C",
            DivisionAge.JUNIOR: "J",
            DivisionAge.YOUNG_ADULT: "YA",
            DivisionAge.ADULT: "A",
            DivisionAge.VETERAN: "V",
            DivisionAge.SENIOR: "S",
        }[
            self.categorie_age(
                date_reference, categories_veteran_actives=categories_veteran_actives
            )
        ]
        return f"{prefixe_age}{self.sexe.value}{self.code_style}"
