import unittest

from fletchscore.referentiels.styles import (
    ajouter_variante_style,
    styles_disponibles,
)
from fletchscore.storage import db


class TestReferentielStyles(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")
        db.init_schema(self.conn)
        db.seed_referentiel_styles(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_styles_disponibles_contient_les_12_codes_ifaa(self):
        self.assertEqual(len(styles_disponibles(self.conn)), 12)

    def test_ajouter_variante_locale(self):
        ajouter_variante_style(self.conn, "XX-1", "Variante FFTL locale")
        styles = styles_disponibles(self.conn)
        self.assertEqual(len(styles), 13)
        self.assertIn("XX-1", [s.code for s in styles])

    def test_ajouter_variante_avec_code_ifaa_existant_refuse(self):
        with self.assertRaises(ValueError):
            ajouter_variante_style(self.conn, "BB-R", "Tentative de doublon")
        # Le style IFAA d'origine n'a pas été modifié.
        styles = styles_disponibles(self.conn)
        self.assertEqual(len(styles), 12)

    def test_ajouter_deux_fois_la_meme_variante_refuse_la_seconde(self):
        ajouter_variante_style(self.conn, "XX-1", "Variante A")
        with self.assertRaises(ValueError):
            ajouter_variante_style(self.conn, "XX-1", "Variante B")


if __name__ == "__main__":
    unittest.main()
