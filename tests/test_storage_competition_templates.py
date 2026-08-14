import sqlite3
import unittest

from fletchscore.models import CompetitionTemplate, CompetitionTemplateEpreuve
from fletchscore.storage import db


class TestCompetitionTemplate(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")
        db.init_schema(self.conn)
        db.seed_baremes_preconfigures(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_roundtrip(self):
        template = CompetitionTemplate(id="t1", nom="Week-end FFTL type")
        db.insert_competition_template(self.conn, template)
        self.assertEqual(db.get_competition_template(self.conn, "t1"), template)

    def test_get_inexistant_retourne_none(self):
        self.assertIsNone(db.get_competition_template(self.conn, "inconnu"))

    def test_liste_vide_au_depart(self):
        self.assertEqual(db.list_competition_templates(self.conn), [])

    def test_liste_triee_par_nom(self):
        db.insert_competition_template(self.conn, CompetitionTemplate(id="t2", nom="Zebre"))
        db.insert_competition_template(self.conn, CompetitionTemplate(id="t1", nom="Alpha"))
        templates = db.list_competition_templates(self.conn)
        self.assertEqual([t.nom for t in templates], ["Alpha", "Zebre"])


class TestCompetitionTemplateEpreuve(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")
        db.init_schema(self.conn)
        db.seed_baremes_preconfigures(self.conn)
        db.insert_competition_template(self.conn, CompetitionTemplate(id="t1", nom="Week-end FFTL"))

    def tearDown(self):
        self.conn.close()

    def test_roundtrip(self):
        epreuve_template = CompetitionTemplateEpreuve(
            id="e1",
            competition_template_id="t1",
            nom="Indoor 18m",
            bareme_id="ifaa-indoor",
            ordre=0,
        )
        db.insert_competition_template_epreuve(self.conn, epreuve_template)
        self.assertEqual(db.list_competition_template_epreuves(self.conn, "t1"), [epreuve_template])

    def test_liste_vide_au_depart(self):
        self.assertEqual(db.list_competition_template_epreuves(self.conn, "t1"), [])

    def test_liste_triee_par_ordre_pas_par_insertion(self):
        db.insert_competition_template_epreuve(
            self.conn,
            CompetitionTemplateEpreuve(
                id="e2",
                competition_template_id="t1",
                nom="Flint",
                bareme_id="flint-indoor",
                ordre=1,
            ),
        )
        db.insert_competition_template_epreuve(
            self.conn,
            CompetitionTemplateEpreuve(
                id="e1",
                competition_template_id="t1",
                nom="Indoor 18m",
                bareme_id="ifaa-indoor",
                ordre=0,
            ),
        )
        epreuves = db.list_competition_template_epreuves(self.conn, "t1")
        self.assertEqual([e.nom for e in epreuves], ["Indoor 18m", "Flint"])

    def test_ne_retourne_que_les_epreuves_du_bon_modele(self):
        db.insert_competition_template(self.conn, CompetitionTemplate(id="t2", nom="Autre modèle"))
        db.insert_competition_template_epreuve(
            self.conn,
            CompetitionTemplateEpreuve(
                id="e1",
                competition_template_id="t1",
                nom="Indoor",
                bareme_id="ifaa-indoor",
                ordre=0,
            ),
        )
        db.insert_competition_template_epreuve(
            self.conn,
            CompetitionTemplateEpreuve(
                id="e2",
                competition_template_id="t2",
                nom="Flint",
                bareme_id="flint-indoor",
                ordre=0,
            ),
        )
        epreuves_t1 = db.list_competition_template_epreuves(self.conn, "t1")
        self.assertEqual([e.nom for e in epreuves_t1], ["Indoor"])

    def test_bareme_inconnu_rejete_par_cle_etrangere(self):
        epreuve_template = CompetitionTemplateEpreuve(
            id="e1",
            competition_template_id="t1",
            nom="X",
            bareme_id="bareme-fantome",
            ordre=0,
        )
        with self.assertRaises(sqlite3.IntegrityError):
            db.insert_competition_template_epreuve(self.conn, epreuve_template)

    def test_modele_inconnu_rejete_par_cle_etrangere(self):
        epreuve_template = CompetitionTemplateEpreuve(
            id="e1",
            competition_template_id="modele-fantome",
            nom="X",
            bareme_id="ifaa-indoor",
            ordre=0,
        )
        with self.assertRaises(sqlite3.IntegrityError):
            db.insert_competition_template_epreuve(self.conn, epreuve_template)


if __name__ == "__main__":
    unittest.main()
