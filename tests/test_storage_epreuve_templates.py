import sqlite3
import unittest

from fletchscore.models import EpreuveTemplate
from fletchscore.storage import db


class TestEpreuveTemplate(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")
        db.init_schema(self.conn)
        db.seed_baremes_preconfigures(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_roundtrip(self):
        template = EpreuveTemplate(id="t1", nom="IFAA Indoor", bareme_id="ifaa-indoor")
        db.insert_epreuve_template(self.conn, template)
        self.assertEqual(db.get_epreuve_template(self.conn, "t1"), template)

    def test_get_inexistant_retourne_none(self):
        self.assertIsNone(db.get_epreuve_template(self.conn, "inconnu"))

    def test_liste_vide_au_depart(self):
        self.assertEqual(db.list_epreuve_templates(self.conn), [])

    def test_liste_triee_par_nom(self):
        db.insert_epreuve_template(
            self.conn, EpreuveTemplate(id="t2", nom="Zebre", bareme_id="ifaa-indoor")
        )
        db.insert_epreuve_template(
            self.conn, EpreuveTemplate(id="t1", nom="Alpha", bareme_id="flint-indoor")
        )
        templates = db.list_epreuve_templates(self.conn)
        self.assertEqual([t.nom for t in templates], ["Alpha", "Zebre"])

    def test_bareme_inconnu_rejete_par_cle_etrangere(self):
        template = EpreuveTemplate(id="t1", nom="X", bareme_id="bareme-fantome")
        with self.assertRaises(sqlite3.IntegrityError):
            db.insert_epreuve_template(self.conn, template)


if __name__ == "__main__":
    unittest.main()
