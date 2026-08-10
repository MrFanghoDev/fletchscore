import unittest

from fletchscore.gui.i18n import TRADUCTIONS, traduire


class TestTraduire(unittest.TestCase):
    def test_francais_par_defaut(self):
        self.assertEqual(traduire("section_accueil", "fr"), "Accueil")

    def test_anglais(self):
        self.assertEqual(traduire("section_accueil", "en"), "Home")

    def test_interpolation(self):
        self.assertEqual(
            traduire("statut_serveur_en_cours", "fr", ip="10.0.0.1"),
            "Serveur en cours -- 10.0.0.1",
        )

    def test_langue_inconnue_retombe_sur_le_francais(self):
        self.assertEqual(traduire("section_accueil", "de"), "Accueil")

    def test_cle_absente_retourne_la_cle_elle_meme(self):
        self.assertEqual(traduire("cle_qui_n_existe_pas", "fr"), "cle_qui_n_existe_pas")

    def test_fr_et_en_ont_exactement_les_memes_cles(self):
        # Une clé oubliée dans une des deux langues romprait silencieusement
        # la traduction (repli sur le français, jamais un plantage) --
        # mais autant l'attraper ici plutôt qu'en changeant de langue à la
        # main dans la GUI.
        self.assertEqual(set(TRADUCTIONS["fr"]), set(TRADUCTIONS["en"]))


if __name__ == "__main__":
    unittest.main()
