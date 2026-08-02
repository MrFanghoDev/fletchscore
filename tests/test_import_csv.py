import io
import unittest
from datetime import date

from fletchscore.io.import_csv import (
    ErreurImport,
    RapportImport,
    exporter_clubs_csv,
    exporter_competiteurs_csv,
    formater_rapport,
    import_clubs,
    import_competiteurs,
)
from fletchscore.models import Club, Competiteur, Sexe
from fletchscore.storage import db


class TestImportClubs(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")
        db.init_schema(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_import_valide(self):
        csv_text = (
            "code_club,nom,ville\n"
            "77123,Archers Libres de Fontaine le Port,Fontaine-le-Port\n"
            "75001,Club de Paris,Paris\n"
        )
        rapport = import_clubs(self.conn, io.StringIO(csv_text))

        self.assertTrue(rapport.succes)
        self.assertEqual(rapport.importees, 2)
        self.assertEqual(rapport.lignes_traitees, 2)
        self.assertEqual(
            db.get_club(self.conn, "77123"),
            Club("77123", "Archers Libres de Fontaine le Port", "Fontaine-le-Port"),
        )

    def test_ville_optionnelle(self):
        csv_text = "code_club,nom,ville\n77123,Archers Libres,\n"
        rapport = import_clubs(self.conn, io.StringIO(csv_text))
        self.assertTrue(rapport.succes)
        self.assertEqual(db.get_club(self.conn, "77123").ville, "")

    def test_colonne_manquante_rejette_tout_le_fichier(self):
        csv_text = "code_club,ville\n77123,Fontaine-le-Port\n"  # 'nom' absent
        rapport = import_clubs(self.conn, io.StringIO(csv_text))
        self.assertFalse(rapport.succes)
        self.assertIn("nom", rapport.erreurs[0].message)

    def test_ligne_sans_code_club_rejetee(self):
        csv_text = "code_club,nom,ville\n,Sans code,Ville\n"
        rapport = import_clubs(self.conn, io.StringIO(csv_text))
        self.assertEqual(rapport.importees, 0)
        self.assertEqual(len(rapport.erreurs), 1)
        self.assertEqual(rapport.erreurs[0].numero_ligne, 2)

    def test_doublon_dans_le_meme_fichier_rejete(self):
        csv_text = "code_club,nom,ville\n77123,Club A,\n77123,Club A bis,\n"
        rapport = import_clubs(self.conn, io.StringIO(csv_text))
        self.assertEqual(rapport.importees, 1)
        self.assertEqual(len(rapport.erreurs), 1)
        self.assertEqual(rapport.erreurs[0].numero_ligne, 3)

    def test_reimport_club_existant_est_idempotent_pas_une_erreur(self):
        db.insert_club(self.conn, Club("77123", "Déjà présent"))
        csv_text = "code_club,nom,ville\n77123,Nouveau nom ignoré,\n"
        rapport = import_clubs(self.conn, io.StringIO(csv_text))

        self.assertTrue(rapport.succes)
        self.assertEqual(rapport.importees, 0)
        self.assertEqual(rapport.ignorees, 1)
        # Le club existant n'est pas modifié (pas de mise à jour en v0.1).
        self.assertEqual(db.get_club(self.conn, "77123").nom, "Déjà présent")


class TestImportCompetiteurs(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")
        db.init_schema(self.conn)
        db.seed_referentiel_styles(self.conn)
        db.insert_club(self.conn, Club("77123", "Archers Libres de FLP"))

    def tearDown(self):
        self.conn.close()

    def _csv(self, lignes: list[str], colonnes: str | None = None) -> io.StringIO:
        entete = colonnes or (
            "id_federal,nom,prenom,code_club,sexe,date_naissance,"
            "code_style,licence_valide_jusqu_au"
        )
        return io.StringIO(entete + "\n" + "\n".join(lignes) + "\n")

    def test_import_valide(self):
        fichier = self._csv(["FR-1,Dupont,Marie,77123,F,1995-03-14,BB-R,2026-08-31"])
        rapport = import_competiteurs(self.conn, fichier)

        self.assertTrue(rapport.succes)
        self.assertEqual(rapport.importees, 1)
        competiteur = db.get_competiteur(self.conn, "FR-1")
        self.assertEqual(competiteur.nom, "Dupont")
        self.assertEqual(competiteur.licence_valide_jusqu_au, date(2026, 8, 31))

    def test_licence_optionnelle(self):
        fichier = self._csv(["FR-1,Dupont,Marie,77123,F,1995-03-14,BB-R,"])
        rapport = import_competiteurs(self.conn, fichier)
        self.assertTrue(rapport.succes)
        self.assertIsNone(db.get_competiteur(self.conn, "FR-1").licence_valide_jusqu_au)

    def test_code_club_inconnu_rejete_sans_creation_automatique(self):
        fichier = self._csv(["FR-1,Dupont,Marie,CLUB-FANTOME,F,1995-03-14,BB-R,"])
        rapport = import_competiteurs(self.conn, fichier)

        self.assertEqual(rapport.importees, 0)
        self.assertIn("CLUB-FANTOME", rapport.erreurs[0].message)
        self.assertIn("aucune création automatique", rapport.erreurs[0].message)
        self.assertIsNone(db.get_club(self.conn, "CLUB-FANTOME"))

    def test_code_style_inconnu_rejete_sans_creation_automatique(self):
        fichier = self._csv(["FR-1,Dupont,Marie,77123,F,1995-03-14,STYLE-FANTOME,"])
        rapport = import_competiteurs(self.conn, fichier)

        self.assertEqual(rapport.importees, 0)
        self.assertIn("STYLE-FANTOME", rapport.erreurs[0].message)

    def test_sexe_invalide_rejete(self):
        fichier = self._csv(["FR-1,Dupont,Marie,77123,X,1995-03-14,BB-R,"])
        rapport = import_competiteurs(self.conn, fichier)
        self.assertEqual(rapport.importees, 0)
        self.assertIn("sexe invalide", rapport.erreurs[0].message)

    def test_date_naissance_invalide_rejetee(self):
        fichier = self._csv(["FR-1,Dupont,Marie,77123,F,14-03-1995,BB-R,"])
        rapport = import_competiteurs(self.conn, fichier)
        self.assertEqual(rapport.importees, 0)
        self.assertIn("date_naissance invalide", rapport.erreurs[0].message)

    def test_licence_invalide_rejetee(self):
        fichier = self._csv(["FR-1,Dupont,Marie,77123,F,1995-03-14,BB-R,pas-une-date"])
        rapport = import_competiteurs(self.conn, fichier)
        self.assertEqual(rapport.importees, 0)
        self.assertIn("licence_valide_jusqu_au invalide", rapport.erreurs[0].message)

    def test_doublon_id_federal_dans_le_meme_fichier_rejete(self):
        fichier = self._csv(
            [
                "FR-1,Dupont,Marie,77123,F,1995-03-14,BB-R,",
                "FR-1,Dupont,Marie,77123,F,1995-03-14,BB-R,",
            ]
        )
        rapport = import_competiteurs(self.conn, fichier)
        self.assertEqual(rapport.importees, 1)
        self.assertEqual(len(rapport.erreurs), 1)
        self.assertEqual(rapport.erreurs[0].numero_ligne, 3)

    def test_id_federal_deja_en_base_rejete_pas_de_maj_silencieuse(self):
        fichier1 = self._csv(["FR-1,Dupont,Marie,77123,F,1995-03-14,BB-R,"])
        import_competiteurs(self.conn, fichier1)

        fichier2 = self._csv(["FR-1,AutreNom,AutrePrenom,77123,F,1995-03-14,BB-R,"])
        rapport2 = import_competiteurs(self.conn, fichier2)

        self.assertEqual(rapport2.importees, 0)
        self.assertIn("existe déjà en base", rapport2.erreurs[0].message)
        # La fiche existante n'a pas été écrasée.
        self.assertEqual(db.get_competiteur(self.conn, "FR-1").nom, "Dupont")

    def test_colonne_manquante_rejette_tout_le_fichier(self):
        fichier = self._csv(
            ["FR-1,Dupont,Marie,77123,F,1995-03-14,BB-R,"],
            colonnes="id_federal,nom,prenom,code_club,sexe,date_naissance",
        )
        rapport = import_competiteurs(self.conn, fichier)
        self.assertFalse(rapport.succes)
        self.assertIn("code_style", rapport.erreurs[0].message)

    def test_fichier_avec_plusieurs_erreurs_et_une_ligne_valide(self):
        fichier = self._csv(
            [
                "FR-1,Dupont,Marie,77123,F,1995-03-14,BB-R,",  # valide
                "FR-2,X,Y,CLUB-FANTOME,F,1995-03-14,BB-R,",  # club inconnu
                "FR-3,X,Y,77123,Z,1995-03-14,BB-R,",  # sexe invalide
            ]
        )
        rapport = import_competiteurs(self.conn, fichier)
        self.assertEqual(rapport.importees, 1)
        self.assertEqual(len(rapport.erreurs), 2)
        self.assertEqual([e.numero_ligne for e in rapport.erreurs], [3, 4])


class TestFormaterRapport(unittest.TestCase):
    def test_rapport_sans_erreur(self):
        rapport = RapportImport(lignes_traitees=3, importees=2, ignorees=1)
        texte = formater_rapport(rapport)
        self.assertIn("2 importé(s)", texte)
        self.assertIn("1 ignoré(s)", texte)
        self.assertIn("0 erreur(s)", texte)
        self.assertIn("sur 3 ligne(s)", texte)

    def test_rapport_avec_erreurs_liste_chaque_ligne(self):
        rapport = RapportImport(
            lignes_traitees=2,
            importees=1,
            erreurs=[ErreurImport(3, "code_club inconnu")],
        )
        texte = formater_rapport(rapport)
        self.assertIn("1 erreur(s)", texte)
        self.assertIn("ligne 3 : code_club inconnu", texte)

    def test_rapport_avec_erreurs_reel_apres_import(self):
        conn = db.connect(":memory:")
        db.init_schema(conn)
        db.seed_referentiel_styles(conn)
        db.insert_club(conn, Club("77123", "Archers Libres de FLP"))
        fichier = io.StringIO(
            "id_federal,nom,prenom,code_club,sexe,date_naissance,code_style\n"
            "FR-1,X,Y,CLUB-FANTOME,F,1995-01-01,BB-R\n"
        )
        rapport = import_competiteurs(conn, fichier)
        texte = formater_rapport(rapport)
        self.assertIn("CLUB-FANTOME", texte)
        conn.close()


class TestExporterClubsCsv(unittest.TestCase):
    def test_entete_correcte(self):
        destination = io.StringIO()
        exporter_clubs_csv(
            [Club("77123", "Archers Libres de FLP", "Fontaine-le-Port")], destination
        )
        lignes = destination.getvalue().splitlines()
        self.assertEqual(lignes[0], "code_club,nom,ville")

    def test_une_ligne_par_club(self):
        clubs = [
            Club("77123", "Archers Libres de FLP", "Fontaine-le-Port"),
            Club("75001", "Compagnie d'Arc de Paris", "Paris"),
        ]
        destination = io.StringIO()
        exporter_clubs_csv(clubs, destination)
        lignes = destination.getvalue().splitlines()
        self.assertEqual(len(lignes), 3)  # en-tête + 2 clubs

    def test_liste_vide_donne_seulement_lentete(self):
        destination = io.StringIO()
        exporter_clubs_csv([], destination)
        lignes = destination.getvalue().splitlines()
        self.assertEqual(len(lignes), 1)

    def test_export_puis_reimport_round_trip(self):
        club = Club("77123", "Archers Libres de FLP", "Fontaine-le-Port")
        destination = io.StringIO()
        exporter_clubs_csv([club], destination)

        conn = db.connect(":memory:")
        db.init_schema(conn)
        rapport = import_clubs(conn, io.StringIO(destination.getvalue()))

        self.assertTrue(rapport.succes)
        self.assertEqual(db.get_club(conn, "77123"), club)
        conn.close()


class TestExporterCompetiteursCsv(unittest.TestCase):
    def _competiteur(self, **overrides) -> Competiteur:
        defaults = dict(
            id_federal="FR-1",
            nom="Dupont",
            prenom="Marie",
            code_club="77123",
            sexe=Sexe.F,
            date_naissance=date(1995, 3, 14),
            code_style="BB-R",
        )
        defaults.update(overrides)
        return Competiteur(**defaults)

    def test_entete_correcte(self):
        destination = io.StringIO()
        exporter_competiteurs_csv([self._competiteur()], destination)
        lignes = destination.getvalue().splitlines()
        self.assertEqual(
            lignes[0],
            "id_federal,nom,prenom,code_club,sexe,date_naissance,code_style,"
            "licence_valide_jusqu_au",
        )

    def test_licence_absente_donne_un_champ_vide(self):
        destination = io.StringIO()
        exporter_competiteurs_csv([self._competiteur()], destination)
        derniere_colonne = destination.getvalue().splitlines()[1].split(",")[-1]
        self.assertEqual(derniere_colonne, "")

    def test_liste_vide_donne_seulement_lentete(self):
        destination = io.StringIO()
        exporter_competiteurs_csv([], destination)
        lignes = destination.getvalue().splitlines()
        self.assertEqual(len(lignes), 1)

    def test_export_puis_reimport_round_trip(self):
        competiteur = self._competiteur(licence_valide_jusqu_au=date(2026, 12, 31))
        destination = io.StringIO()
        exporter_competiteurs_csv([competiteur], destination)

        conn = db.connect(":memory:")
        db.init_schema(conn)
        db.seed_referentiel_styles(conn)
        db.insert_club(conn, Club("77123", "Archers Libres de FLP"))
        rapport = import_competiteurs(conn, io.StringIO(destination.getvalue()))

        self.assertTrue(rapport.succes)
        self.assertEqual(db.get_competiteur(conn, "FR-1"), competiteur)
        conn.close()


if __name__ == "__main__":
    unittest.main()
