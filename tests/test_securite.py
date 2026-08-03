import tempfile
import unittest
from pathlib import Path

from fletchscore import securite


class TestObtenirCleSecrete(unittest.TestCase):
    def test_genere_une_cle_de_32_octets(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "cle.txt"
            cle = securite.obtenir_cle_secrete(chemin)
            self.assertEqual(len(cle), 32)

    def test_cree_le_fichier(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "cle.txt"
            securite.obtenir_cle_secrete(chemin)
            self.assertTrue(chemin.exists())

    def test_meme_cle_a_chaque_appel(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "cle.txt"
            premiere = securite.obtenir_cle_secrete(chemin)
            seconde = securite.obtenir_cle_secrete(chemin)
            self.assertEqual(premiere, seconde)

    def test_cles_differentes_pour_deux_fichiers_differents(self):
        with tempfile.TemporaryDirectory() as dossier:
            cle1 = securite.obtenir_cle_secrete(Path(dossier) / "cle1.txt")
            cle2 = securite.obtenir_cle_secrete(Path(dossier) / "cle2.txt")
            self.assertNotEqual(cle1, cle2)

    def test_cree_le_dossier_parent_si_absent(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = Path(dossier) / "sous_dossier" / "cle.txt"
            cle = securite.obtenir_cle_secrete(chemin)
            self.assertEqual(len(cle), 32)
            self.assertTrue(chemin.exists())


if __name__ == "__main__":
    unittest.main()
