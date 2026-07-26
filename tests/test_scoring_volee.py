import unittest

from fletchscore.models import BAREME_IFAA_INDOOR, Bareme
from fletchscore.scoring import normaliser_volee


class TestNormaliserVolee(unittest.TestCase):
    def test_volee_complete_inchangee(self):
        # IFAA Indoor : 5 flèches par volée.
        self.assertEqual(normaliser_volee(BAREME_IFAA_INDOOR, [5, 5, 4, 3, 2]), [5, 5, 4, 3, 2])

    def test_trop_de_fleches_garde_les_n_plus_faibles(self):
        # 6 flèches tirées par erreur -- pénalité : les 5 PLUS FAIBLES
        # comptent (pas les plus fortes).
        resultat = normaliser_volee(BAREME_IFAA_INDOOR, [5, 5, 5, 4, 3, 1])
        self.assertEqual(sorted(resultat), [1, 3, 4, 5, 5])
        self.assertEqual(len(resultat), 5)

    def test_pas_assez_de_fleches_complete_a_zero(self):
        # 3 flèches seulement -- les 2 manquantes comptent à 0.
        resultat = normaliser_volee(BAREME_IFAA_INDOOR, [5, 4, 3])
        self.assertEqual(sorted(resultat, reverse=True), [5, 4, 3, 0, 0])
        self.assertEqual(len(resultat), 5)

    def test_volee_vide_complete_entierement_a_zero(self):
        resultat = normaliser_volee(BAREME_IFAA_INDOOR, [])
        self.assertEqual(resultat, [0, 0, 0, 0, 0])

    def test_valeur_zero_toujours_acceptee_mauvaise_cible(self):
        # Une flèche sur la mauvaise cible arrive déjà comme un 0 --
        # aucune erreur ne doit être levée.
        resultat = normaliser_volee(BAREME_IFAA_INDOOR, [5, 0, 4, 3, 2])
        self.assertEqual(resultat, [5, 0, 4, 3, 2])

    def test_valeur_hors_zones_leve(self):
        with self.assertRaises(ValueError):
            normaliser_volee(BAREME_IFAA_INDOOR, [5, 5, 4, 3, 6])

    def test_valeur_negative_leve(self):
        with self.assertRaises(ValueError):
            normaliser_volee(BAREME_IFAA_INDOOR, [5, 5, 4, 3, -1])

    def test_flint_indoor_zones_3_4_5(self):
        bareme = Bareme(
            id="test-flint",
            nom="Flint test",
            nb_series=1,
            volees_par_serie=1,
            fleches_par_volee=4,
            valeurs_zones=[5, 4, 3],
        )
        self.assertEqual(normaliser_volee(bareme, [5, 4, 3, 3]), [5, 4, 3, 3])
        with self.assertRaises(ValueError):
            normaliser_volee(bareme, [5, 4, 3, 2])  # 2 n'existe pas sur ce barème


if __name__ == "__main__":
    unittest.main()
