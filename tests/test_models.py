import unittest
from datetime import date

from fletchscore.models import (
    BAREME_IFAA_INDOOR,
    Bareme,
    Competiteur,
    DivisionAge,
    Score,
    Sexe,
    StatutScore,
    categorie_age,
)


class TestCategorieAge(unittest.TestCase):
    def test_cub_moins_de_13(self):
        self.assertEqual(categorie_age(date(2015, 6, 1), date(2026, 1, 1)), DivisionAge.CUB)

    def test_junior_13_a_16(self):
        self.assertEqual(categorie_age(date(2011, 6, 1), date(2026, 1, 1)), DivisionAge.JUNIOR)

    def test_young_adult_17_a_20(self):
        self.assertEqual(categorie_age(date(2007, 6, 1), date(2026, 1, 1)), DivisionAge.YOUNG_ADULT)

    def test_adult_par_defaut_sans_veteran_actif(self):
        # 60 ans, mais categories_veteran_actives=False -> reste Adult
        self.assertEqual(categorie_age(date(1966, 1, 1), date(2026, 1, 1)), DivisionAge.ADULT)

    def test_veteran_si_actif(self):
        self.assertEqual(
            categorie_age(date(1966, 1, 1), date(2026, 1, 1), categories_veteran_actives=True),
            DivisionAge.VETERAN,
        )

    def test_senior_si_actif(self):
        self.assertEqual(
            categorie_age(date(1955, 1, 1), date(2026, 1, 1), categories_veteran_actives=True),
            DivisionAge.SENIOR,
        )

    def test_anniversaire_pas_encore_passe_cette_annee(self):
        # Né le 2011-12-31 : au 2026-01-01, n'a *pas encore* fêté ses 15 ans
        # (les fête le 2026-12-31) -> encore 14 ans, toujours Junior.
        self.assertEqual(categorie_age(date(2011, 12, 31), date(2026, 1, 1)), DivisionAge.JUNIOR)

    def test_date_reference_avant_naissance_leve(self):
        with self.assertRaises(ValueError):
            categorie_age(date(2026, 1, 1), date(2020, 1, 1))


class TestCompetiteur(unittest.TestCase):
    def _competiteur(self, **overrides) -> Competiteur:
        defaults = dict(
            id_federal="FR-77123",
            nom="Dupont",
            prenom="Marie",
            code_club="77123",
            sexe=Sexe.F,
            date_naissance=date(1995, 3, 14),
            code_style="BB-R",
        )
        defaults.update(overrides)
        return Competiteur(**defaults)

    def test_code_categorie_reproduit_exemple_reglement(self):
        # AMBB-R = Adulte Homme Barebow-Recurve, exemple du règlement.
        competiteur = self._competiteur(sexe=Sexe.M, date_naissance=date(1995, 3, 14))
        self.assertEqual(competiteur.code_categorie(date(2026, 1, 1)), "AMBB-R")

    def test_licence_valide_sans_date_renseignee(self):
        competiteur = self._competiteur(licence_valide_jusqu_au=None)
        self.assertTrue(competiteur.licence_valide(date(2026, 1, 1)))

    def test_licence_expiree(self):
        competiteur = self._competiteur(licence_valide_jusqu_au=date(2025, 12, 31))
        self.assertFalse(competiteur.licence_valide(date(2026, 1, 1)))

    def test_licence_encore_valide(self):
        competiteur = self._competiteur(licence_valide_jusqu_au=date(2026, 8, 31))
        self.assertTrue(competiteur.licence_valide(date(2026, 1, 1)))


class TestBareme(unittest.TestCase):
    def test_ifaa_indoor_total_fleches(self):
        # 2 unités x 6 volées x 5 flèches = 60 flèches.
        self.assertEqual(BAREME_IFAA_INDOOR.total_flèches, 60)

    def test_ifaa_indoor_score_max(self):
        self.assertEqual(BAREME_IFAA_INDOOR.score_max, 60 * 5)

    def test_valeur_zero_toujours_valide(self):
        self.assertTrue(BAREME_IFAA_INDOOR.valeur_valide(0))

    def test_valeur_hors_zones_invalide(self):
        self.assertFalse(BAREME_IFAA_INDOOR.valeur_valide(6))

    def test_valeurs_zones_non_triees_leve(self):
        with self.assertRaises(ValueError):
            Bareme(
                id="invalide",
                nom="Barème mal ordonné",
                nb_series=1,
                volees_par_serie=1,
                fleches_par_volee=1,
                valeurs_zones=[3, 5, 4],
            )

    def test_valeurs_zones_vide_leve(self):
        with self.assertRaises(ValueError):
            Bareme(
                id="vide",
                nom="Barème vide",
                nb_series=1,
                volees_par_serie=1,
                fleches_par_volee=1,
                valeurs_zones=[],
            )


class TestScore(unittest.TestCase):
    def test_total_somme_les_valeurs(self):
        score = Score(
            id="s1",
            inscription_id="i1",
            numero_volee=1,
            valeurs=[5, 5, 4, 3, 0],
            statut=StatutScore.PROPOSE,
        )
        self.assertEqual(score.total, 17)

    def test_total_volee_vide(self):
        score = Score(id="s1", inscription_id="i1", numero_volee=1)
        self.assertEqual(score.total, 0)


if __name__ == "__main__":
    unittest.main()
