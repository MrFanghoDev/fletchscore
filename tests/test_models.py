import unittest
from datetime import date

from fletchscore.models import (
    BAREME_EXPERT_FIELD,
    BAREME_FIELD,
    BAREME_HUNTER,
    BAREME_IFAA_INDOOR,
    BAREME_INTERNATIONAL,
    BAREMES_PRECONFIGURES,
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


class TestNouveauxBaremes(unittest.TestCase):
    """Field, Hunter, International, Expert Field -- confirmés dans le
    règlement IFAA (voir models/bareme.py pour les réserves sur le
    nombre d'unités). Animal Round et 3-D restent hors périmètre : leur
    système de score (kill/wound, arrêt au premier impact) ne rentre pas
    dans ce modèle."""

    def test_field_14_cibles_4_fleches(self):
        self.assertEqual(BAREME_FIELD.total_flèches, 14 * 4)
        self.assertEqual(BAREME_FIELD.valeurs_zones, [5, 4, 3])
        self.assertFalse(BAREME_FIELD.departage_par_x)

    def test_hunter_meme_structure_que_field(self):
        self.assertEqual(BAREME_HUNTER.total_flèches, 14 * 4)
        self.assertEqual(BAREME_HUNTER.valeurs_zones, [5, 4, 3])

    def test_international_20_cibles_3_fleches(self):
        # 2 séries de 10 cibles, 3 flèches par cible = 60 flèches.
        self.assertEqual(BAREME_INTERNATIONAL.total_flèches, 60)
        self.assertEqual(BAREME_INTERNATIONAL.valeurs_zones, [5, 4, 3])

    def test_expert_field_zones_et_departage_x(self):
        # Mêmes distances que Field Round, mais zones subdivisées en 5
        # avec X de départage (comme IFAA Indoor).
        self.assertEqual(BAREME_EXPERT_FIELD.total_flèches, 14 * 4)
        self.assertEqual(BAREME_EXPERT_FIELD.valeurs_zones, [5, 4, 3, 2, 1])
        self.assertTrue(BAREME_EXPERT_FIELD.departage_par_x)

    def test_six_baremes_preconfigures_avec_ids_uniques(self):
        ids = [b.id for b in BAREMES_PRECONFIGURES]
        self.assertEqual(len(ids), 6)
        self.assertEqual(len(set(ids)), 6)  # aucun doublon d'id


class TestScore(unittest.TestCase):
    def test_champs_par_defaut(self):
        score = Score(id="s1", inscription_id="i1", total=270)
        self.assertEqual(score.nombre_x, 0)
        self.assertEqual(score.statut, StatutScore.PROPOSE)

    def test_total_explicite(self):
        score = Score(id="s1", inscription_id="i1", total=280, nombre_x=15)
        self.assertEqual(score.total, 280)
        self.assertEqual(score.nombre_x, 15)


if __name__ == "__main__":
    unittest.main()
