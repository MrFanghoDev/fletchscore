import io
import json
import unittest
from datetime import date

from fletchscore import services
from fletchscore.io.sauvegarde_competition import (
    ErreurSauvegarde,
    exporter_competition,
    importer_competition,
)
from fletchscore.models import Club, Competiteur, Sexe
from fletchscore.storage import db


def _construire_competition_source(conn) -> tuple[str, str, str]:
    """Compétition avec 1 épreuve, 2 compétiteurs de clubs différents,
    2 scores -- retourne (competition_id, epreuve_id, id_federal du 1er)."""
    db.seed_baremes_preconfigures(conn)
    db.insert_club(conn, Club("77123", "Archers Libres de FLP"))
    db.insert_club(conn, Club("75001", "Club de Paris"))
    db.insert_competiteur(
        conn,
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
    db.insert_competiteur(
        conn,
        Competiteur(
            id_federal="FR-2",
            nom="Martin",
            prenom="Luc",
            code_club="75001",
            sexe=Sexe.M,
            date_naissance=date(1990, 1, 1),
            code_style="BB-R",
        ),
    )
    competition = services.creer_competition(
        conn, "Week-end FFTL", date(2026, 3, 14), date(2026, 3, 15)
    )
    epreuve = services.creer_epreuve(
        conn, competition.id, "Indoor", date(2026, 3, 14), "ifaa-indoor"
    )
    i1 = services.inscrire(conn, "FR-1", epreuve.id)
    i2 = services.inscrire(conn, "FR-2", epreuve.id)
    services.saisir_score_final(conn, i1.id, 260)
    services.saisir_score_final(conn, i2.id, 240)
    return competition.id, epreuve.id, "FR-1"


class TestExporterCompetition(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")
        db.init_schema(self.conn)
        db.seed_referentiel_styles(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_competition_introuvable_refuse(self):
        with self.assertRaises(ErreurSauvegarde):
            exporter_competition(self.conn, "competition-fantome", io.StringIO())

    def test_contenu_exporte(self):
        competition_id, epreuve_id, _ = _construire_competition_source(self.conn)
        destination = io.StringIO()
        exporter_competition(self.conn, competition_id, destination)

        donnees = json.loads(destination.getvalue())
        self.assertEqual(donnees["competition"]["id"], competition_id)
        self.assertEqual(len(donnees["epreuves"]), 1)
        self.assertEqual(len(donnees["clubs"]), 2)
        self.assertEqual(len(donnees["competiteurs"]), 2)
        self.assertEqual(len(donnees["baremes"]), 1)
        self.assertEqual(len(donnees["inscriptions"]), 2)
        self.assertEqual(len(donnees["scores"]), 2)


class TestImporterCompetitionBaseVide(unittest.TestCase):
    """Restauration sur une base neuve, sans aucun référentiel préchargé
    -- le scénario "transférer d'une machine à une autre" du roadmap :
    tout (clubs, compétiteurs, barème) doit être importé, rien n'existe
    déjà côté cible."""

    def setUp(self):
        self.conn_source = db.connect(":memory:")
        db.init_schema(self.conn_source)
        db.seed_referentiel_styles(self.conn_source)
        self.competition_id, self.epreuve_id, _ = _construire_competition_source(self.conn_source)
        self.fichier = io.StringIO()
        exporter_competition(self.conn_source, self.competition_id, self.fichier)

        self.conn_cible = db.connect(":memory:")
        db.init_schema(self.conn_cible)
        db.seed_referentiel_styles(self.conn_cible)
        # Volontairement PAS de seed_baremes_preconfigures ici -- vérifie
        # que le barème vient bien de la sauvegarde, pas d'un référentiel
        # déjà là.

    def tearDown(self):
        self.conn_source.close()
        self.conn_cible.close()

    def test_tout_est_importe(self):
        self.fichier.seek(0)
        rapport = importer_competition(self.conn_cible, self.fichier)

        self.assertTrue(rapport.reussi)
        self.assertEqual(rapport.epreuves_importees, 1)
        self.assertEqual(rapport.inscriptions_importees, 2)
        self.assertEqual(rapport.scores_importes, 2)
        self.assertEqual(rapport.clubs_importes, 2)
        self.assertEqual(rapport.clubs_reutilises, 0)
        self.assertEqual(rapport.competiteurs_importes, 2)
        self.assertEqual(rapport.baremes_importes, 1)

    def test_donnees_fidelement_restaurees(self):
        self.fichier.seek(0)
        importer_competition(self.conn_cible, self.fichier)

        competition = db.get_competition(self.conn_cible, self.competition_id)
        self.assertIsNotNone(competition)
        self.assertEqual(competition.nom, "Week-end FFTL")

        epreuves = db.list_epreuves_by_competition(self.conn_cible, self.competition_id)
        self.assertEqual(len(epreuves), 1)
        self.assertEqual(epreuves[0].id, self.epreuve_id)

        competiteur = db.get_competiteur(self.conn_cible, "FR-1")
        self.assertIsNotNone(competiteur)
        self.assertEqual(competiteur.nom, "Dupont")

        inscription = db.get_inscription_par_competiteur_epreuve(
            self.conn_cible, "FR-1", self.epreuve_id
        )
        self.assertIsNotNone(inscription)
        score = db.get_score_by_inscription(self.conn_cible, inscription.id)
        self.assertEqual(score.total, 260)

    def test_classement_fonctionne_apres_restauration(self):
        self.fichier.seek(0)
        importer_competition(self.conn_cible, self.fichier)

        classement = services.classement_epreuve(self.conn_cible, self.epreuve_id)
        # FR-1 (F) et FR-2 (M) tombent dans deux catégories différentes
        # -- vérifie le total toutes catégories confondues, pas une
        # seule catégorie.
        toutes_lignes = [ligne for lignes in classement.values() for ligne in lignes]
        self.assertEqual(len(toutes_lignes), 2)
        lignes_fr1 = [ligne for ligne in toutes_lignes if ligne.competiteur.id_federal == "FR-1"]
        self.assertEqual(lignes_fr1[0].rang, 1)
        self.assertEqual(lignes_fr1[0].total, 260)

    def test_import_deux_fois_refuse_la_seconde(self):
        self.fichier.seek(0)
        importer_competition(self.conn_cible, self.fichier)

        self.fichier.seek(0)
        with self.assertRaises(ErreurSauvegarde):
            importer_competition(self.conn_cible, self.fichier)

    def test_format_version_invalide_refuse(self):
        self.fichier.seek(0)
        donnees = json.load(self.fichier)
        donnees["format_version"] = 999
        with self.assertRaises(ErreurSauvegarde):
            importer_competition(self.conn_cible, io.StringIO(json.dumps(donnees)))


class TestImporterCompetitionReferentielsExistants(unittest.TestCase):
    """La base cible a déjà le club/compétiteur/barème (ex. déjà
    configurée normalement, ou même club que la machine source) --
    doivent être réutilisés, jamais dupliqués ni écrasés."""

    def setUp(self):
        self.conn_source = db.connect(":memory:")
        db.init_schema(self.conn_source)
        db.seed_referentiel_styles(self.conn_source)
        self.competition_id, self.epreuve_id, _ = _construire_competition_source(self.conn_source)
        self.fichier = io.StringIO()
        exporter_competition(self.conn_source, self.competition_id, self.fichier)
        self.fichier.seek(0)

        self.conn_cible = db.connect(":memory:")
        db.init_schema(self.conn_cible)
        db.seed_referentiel_styles(self.conn_cible)
        db.seed_baremes_preconfigures(self.conn_cible)  # barème déjà là
        db.insert_club(self.conn_cible, Club("77123", "Archers Libres de FLP"))
        db.insert_competiteur(
            self.conn_cible,
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
        self.conn_source.close()
        self.conn_cible.close()

    def test_referentiels_partages_reutilises_pas_dupliques(self):
        rapport = importer_competition(self.conn_cible, self.fichier)

        self.assertEqual(rapport.baremes_reutilises, 1)
        self.assertEqual(rapport.baremes_importes, 0)
        self.assertEqual(rapport.clubs_reutilises, 1)
        self.assertEqual(rapport.clubs_importes, 1)  # 75001 (Club de Paris) manquant, lui importé
        self.assertEqual(rapport.competiteurs_reutilises, 1)
        self.assertEqual(rapport.competiteurs_importes, 1)  # FR-2 manquant, lui importé

        # Un seul exemplaire du club/compétiteur partagé, pas de doublon.
        self.assertIsNotNone(db.get_club(self.conn_cible, "77123"))
        self.assertIsNotNone(db.get_competiteur(self.conn_cible, "FR-1"))


if __name__ == "__main__":
    unittest.main()
