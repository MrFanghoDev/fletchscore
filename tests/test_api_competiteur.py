import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

from fletchscore import services
from fletchscore.api.competiteur import (
    adresse_ip_locale,
    creer_serveur,
    page_accueil,
    page_competition,
    page_epreuve,
)
from fletchscore.models import Club, Competiteur, Sexe
from fletchscore.storage import db


class TestPageAccueil(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")
        db.init_schema(self.conn)
        db.seed_baremes_preconfigures(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_aucune_competition(self):
        page = page_accueil(self.conn)
        self.assertIn("Aucune compétition", page)

    def test_liste_les_competitions_et_epreuves(self):
        competition = services.creer_competition(
            self.conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )
        epreuve = services.creer_epreuve(
            self.conn, competition.id, "IFAA Indoor", date(2026, 3, 14), "ifaa-indoor"
        )
        page = page_accueil(self.conn)
        self.assertIn("Week-end FFTL", page)
        self.assertIn("IFAA Indoor", page)
        self.assertIn(f"/epreuve/{epreuve.id}", page)
        self.assertIn(f"/competition/{competition.id}", page)

    def test_echappe_le_html_dans_les_noms(self):
        services.creer_competition(
            self.conn, "<script>alert(1)</script>", date(2026, 1, 1), date(2026, 1, 2)
        )
        page = page_accueil(self.conn)
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;", page)


class TestPageEpreuve(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")
        db.init_schema(self.conn)
        db.seed_baremes_preconfigures(self.conn)
        db.insert_club(self.conn, Club("77123", "Archers Libres de FLP"))
        db.seed_referentiel_styles(self.conn)
        db.insert_competiteur(
            self.conn,
            Competiteur(
                id_federal="FR-1",
                nom="Dupont",
                prenom="Marie",
                code_club="77123",
                sexe=Sexe.F,
                date_naissance=date(1995, 3, 14),
                code_style="BB-R",
            ),
        )
        self.competition = services.creer_competition(
            self.conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )
        self.epreuve = services.creer_epreuve(
            self.conn, self.competition.id, "IFAA Indoor", date(2026, 3, 14), "ifaa-indoor"
        )

    def tearDown(self):
        self.conn.close()

    def test_epreuve_introuvable(self):
        page = page_epreuve(self.conn, "epreuve-fantome")
        self.assertIn("introuvable", page.lower())

    def test_classement_vide(self):
        page = page_epreuve(self.conn, self.epreuve.id)
        self.assertIn("IFAA Indoor", page)
        self.assertIn("Aucun compétiteur classé", page)

    def test_affiche_le_classement(self):
        inscription = services.inscrire(self.conn, "FR-1", self.epreuve.id)
        services.saisir_score_final(self.conn, inscription.id, 270, nombre_x=12)

        page = page_epreuve(self.conn, self.epreuve.id)
        self.assertIn("Marie", page)
        self.assertIn("Dupont", page)
        self.assertIn("270", page)
        self.assertIn("12", page)

    def test_contient_le_rafraichissement_automatique(self):
        page = page_epreuve(self.conn, self.epreuve.id)
        self.assertIn('http-equiv="refresh"', page)


class TestPageCompetition(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")
        db.init_schema(self.conn)
        db.seed_baremes_preconfigures(self.conn)
        db.insert_club(self.conn, Club("77123", "Archers Libres de FLP"))
        db.seed_referentiel_styles(self.conn)
        db.insert_competiteur(
            self.conn,
            Competiteur(
                id_federal="FR-1",
                nom="Dupont",
                prenom="Marie",
                code_club="77123",
                sexe=Sexe.F,
                date_naissance=date(1995, 3, 14),
                code_style="BB-R",
            ),
        )

    def tearDown(self):
        self.conn.close()

    def test_competition_introuvable(self):
        page = page_competition(self.conn, "competition-fantome")
        self.assertIn("introuvable", page.lower())

    def test_colonnes_par_epreuve_et_total(self):
        competition = services.creer_competition(
            self.conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )
        epreuve1 = services.creer_epreuve(
            self.conn, competition.id, "Indoor", date(2026, 3, 14), "ifaa-indoor"
        )
        epreuve2 = services.creer_epreuve(
            self.conn, competition.id, "Flint", date(2026, 3, 15), "flint-indoor"
        )
        inscription1 = services.inscrire(self.conn, "FR-1", epreuve1.id)
        inscription2 = services.inscrire(self.conn, "FR-1", epreuve2.id)
        services.saisir_score_final(self.conn, inscription1.id, 260)
        services.saisir_score_final(self.conn, inscription2.id, 220)

        page = page_competition(self.conn, competition.id)
        self.assertIn("Indoor", page)
        self.assertIn("Flint", page)
        self.assertIn("260", page)
        self.assertIn("220", page)
        self.assertIn("480", page)  # total cumulé


class TestAdresseIpLocale(unittest.TestCase):
    def test_retourne_une_chaine_non_vide(self):
        adresse = adresse_ip_locale()
        self.assertIsInstance(adresse, str)
        self.assertTrue(adresse)


class TestServeurIntegration(unittest.TestCase):
    """Test bout-en-bout avec un vrai serveur HTTP démarré sur un port
    local et de vraies requêtes -- pas seulement les fonctions de
    génération HTML isolées."""

    def setUp(self):
        self.dossier_temporaire = tempfile.TemporaryDirectory()
        self.chemin_base = str(Path(self.dossier_temporaire.name) / "test.db")

        conn = db.connect(self.chemin_base)
        db.init_schema(conn)
        db.seed_baremes_preconfigures(conn)
        competition = services.creer_competition(
            conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
        )
        self.epreuve = services.creer_epreuve(
            conn, competition.id, "IFAA Indoor", date(2026, 3, 14), "ifaa-indoor"
        )
        conn.close()  # le serveur ouvre ses propres connexions

        self.serveur = creer_serveur(self.chemin_base, port=0)
        self.thread = threading.Thread(target=self.serveur.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.serveur.shutdown()
        self.serveur.server_close()
        self.thread.join(timeout=2)
        self.dossier_temporaire.cleanup()

    def _url(self, chemin: str) -> str:
        return f"http://127.0.0.1:{self.serveur.server_port}{chemin}"

    def test_page_accueil_repond_200(self):
        with urllib.request.urlopen(self._url("/"), timeout=5) as reponse:
            self.assertEqual(reponse.status, 200)
            contenu = reponse.read().decode("utf-8")
        self.assertIn("Week-end FFTL", contenu)

    def test_page_epreuve_repond_200(self):
        with urllib.request.urlopen(self._url(f"/epreuve/{self.epreuve.id}"), timeout=5) as reponse:
            self.assertEqual(reponse.status, 200)
            contenu = reponse.read().decode("utf-8")
        self.assertIn("IFAA Indoor", contenu)

    def test_page_inconnue_donne_404(self):
        with self.assertRaises(urllib.error.HTTPError) as contexte:
            urllib.request.urlopen(self._url("/nimportequoi"), timeout=5)
        self.assertEqual(contexte.exception.code, 404)


if __name__ == "__main__":
    unittest.main()
