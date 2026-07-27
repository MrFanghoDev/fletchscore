import tempfile
import unittest
from pathlib import Path

from fletchscore.storage import db


class TestOuvrirBase(unittest.TestCase):
    """ouvrir_base() est le point d'entrée du démarrage -- testé sur un
    vrai fichier (pas ':memory:') pour couvrir aussi la création du
    fichier et la réouverture d'une base existante."""

    def setUp(self):
        self._dossier = tempfile.TemporaryDirectory()
        self.chemin = str(Path(self._dossier.name) / "test.db")

    def tearDown(self):
        self._dossier.cleanup()

    def test_cree_le_fichier_et_les_referentiels(self):
        conn = db.ouvrir_base(self.chemin)
        try:
            self.assertTrue(Path(self.chemin).exists())
            self.assertEqual(len(db.list_styles(conn)), 12)
            self.assertIsNotNone(db.get_bareme(conn, "ifaa-indoor"))
            self.assertIsNotNone(db.get_bareme(conn, "flint-indoor"))
        finally:
            conn.close()

    def test_reouverture_est_idempotente(self):
        conn = db.ouvrir_base(self.chemin)
        conn.close()

        conn = db.ouvrir_base(self.chemin)
        try:
            # Pas de doublon de style ni de barème après un 2e démarrage.
            self.assertEqual(len(db.list_styles(conn)), 12)
        finally:
            conn.close()

    def test_donnees_conservees_entre_deux_ouvertures(self):
        from fletchscore.models import Club

        conn = db.ouvrir_base(self.chemin)
        db.insert_club(conn, Club("77123", "Archers Libres de FLP"))
        conn.close()

        conn = db.ouvrir_base(self.chemin)
        try:
            self.assertIsNotNone(db.get_club(conn, "77123"))
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
