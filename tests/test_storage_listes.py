import unittest
from datetime import date

from fletchscore.models import Competition
from fletchscore.storage import db


class TestListCompetitions(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")
        db.init_schema(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_liste_vide_au_depart(self):
        self.assertEqual(db.list_competitions(self.conn), [])

    def test_triee_par_date_debut_decroissante(self):
        db.insert_competition(
            self.conn,
            Competition(
                id="c1", nom="Ancienne", date_debut=date(2025, 1, 1), date_fin=date(2025, 1, 2)
            ),
        )
        db.insert_competition(
            self.conn,
            Competition(
                id="c2", nom="Récente", date_debut=date(2026, 3, 14), date_fin=date(2026, 3, 15)
            ),
        )
        competitions = db.list_competitions(self.conn)
        self.assertEqual([c.id for c in competitions], ["c2", "c1"])


class TestListBaremes(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")
        db.init_schema(self.conn)
        db.seed_baremes_preconfigures(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_contient_les_baremes_preconfigures(self):
        baremes = db.list_baremes(self.conn)
        self.assertEqual(
            {b.id for b in baremes},
            {"flint-indoor", "ifaa-indoor", "field", "hunter", "international", "expert-field"},
        )

    def test_liste_vide_si_rien_seede(self):
        conn = db.connect(":memory:")
        db.init_schema(conn)
        self.assertEqual(db.list_baremes(conn), [])
        conn.close()


if __name__ == "__main__":
    unittest.main()
