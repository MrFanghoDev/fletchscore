import unittest
from datetime import date

from fletchscore import services
from fletchscore.models import Club, Competiteur, Competition, Sexe, StatutCompetition, StatutScore
from fletchscore.services import (
    ErreurMetier,
    libelle_competiteur,
    libelle_epreuve,
    parser_date,
)
from fletchscore.storage import db


class ServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")
        db.init_schema(self.conn)
        db.seed_referentiel_styles(self.conn)
        db.seed_baremes_preconfigures(self.conn)
        db.insert_club(self.conn, Club("77123", "Archers Libres de FLP"))
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

    def _competition(self, **overrides):
        params = dict(
            nom="Compétition test",
            date_debut=date(2026, 3, 14),
            date_fin=date(2026, 3, 15),
        )
        params.update(overrides)
        return services.creer_competition(self.conn, **params)

    def _epreuve(self, competition, bareme_id="ifaa-indoor", **overrides):
        params = dict(
            competition_id=competition.id,
            nom="IFAA Indoor",
            date_epreuve=date(2026, 3, 14),
            bareme_id=bareme_id,
        )
        params.update(overrides)
        return services.creer_epreuve(self.conn, **params)


class TestCreerCompetition(ServiceTestCase):
    def test_creation_valide(self):
        competition = self._competition(lieu="Fontaine-le-Port")
        self.assertEqual(competition.nom, "Compétition test")
        self.assertEqual(competition.statut, StatutCompetition.OUVERTE)
        self.assertIsNotNone(db.get_competition(self.conn, competition.id))

    def test_nom_vide_refuse(self):
        with self.assertRaises(ErreurMetier):
            self._competition(nom="   ")

    def test_date_fin_avant_debut_refusee(self):
        with self.assertRaises(ErreurMetier):
            self._competition(date_debut=date(2026, 3, 15), date_fin=date(2026, 3, 14))

    def test_nom_et_lieu_sont_nettoyes(self):
        competition = self._competition(nom="  Test  ", lieu="  Ville  ")
        self.assertEqual(competition.nom, "Test")
        self.assertEqual(competition.lieu, "Ville")


class TestCreerEpreuve(ServiceTestCase):
    def test_creation_valide(self):
        competition = self._competition()
        epreuve = self._epreuve(competition)
        self.assertEqual(epreuve.competition_id, competition.id)
        self.assertIsNotNone(db.get_epreuve(self.conn, epreuve.id))

    def test_competition_inconnue_refusee(self):
        with self.assertRaises(ErreurMetier):
            services.creer_epreuve(
                self.conn,
                competition_id="inconnue",
                nom="X",
                date_epreuve=date(2026, 3, 14),
                bareme_id="ifaa-indoor",
            )

    def test_bareme_inconnu_refuse(self):
        competition = self._competition()
        with self.assertRaises(ErreurMetier):
            self._epreuve(competition, bareme_id="bareme-fantome")

    def test_date_hors_competition_refusee(self):
        competition = self._competition()
        with self.assertRaises(ErreurMetier) as contexte:
            self._epreuve(competition, date_epreuve=date(2026, 4, 1))
        self.assertIn("en dehors des dates", str(contexte.exception))


class TestModifierCompetition(ServiceTestCase):
    def test_modification_valide(self):
        competition = self._competition()
        modifiee = services.modifier_competition(
            self.conn,
            competition.id,
            nom="Nom corrigé",
            date_debut=date(2026, 3, 14),
            date_fin=date(2026, 3, 15),
            lieu="Nouvelle ville",
            categories_veteran_actives=True,
        )
        self.assertEqual(modifiee.nom, "Nom corrigé")
        self.assertEqual(modifiee.lieu, "Nouvelle ville")
        self.assertTrue(modifiee.categories_veteran_actives)
        self.assertEqual(db.get_competition(self.conn, competition.id), modifiee)

    def test_competition_inconnue_refusee(self):
        with self.assertRaises(ErreurMetier):
            services.modifier_competition(
                self.conn,
                "inconnue",
                nom="X",
                date_debut=date(2026, 1, 1),
                date_fin=date(2026, 1, 2),
            )

    def test_nom_vide_refuse(self):
        competition = self._competition()
        with self.assertRaises(ErreurMetier):
            services.modifier_competition(
                self.conn,
                competition.id,
                nom="   ",
                date_debut=competition.date_debut,
                date_fin=competition.date_fin,
            )

    def test_date_fin_avant_debut_refusee(self):
        competition = self._competition()
        with self.assertRaises(ErreurMetier):
            services.modifier_competition(
                self.conn,
                competition.id,
                nom="X",
                date_debut=date(2026, 3, 15),
                date_fin=date(2026, 3, 14),
            )

    def test_retrecir_les_dates_sous_une_epreuve_existante_refuse(self):
        competition = self._competition()  # 2026-03-14 -- 2026-03-15
        self._epreuve(competition, date_epreuve=date(2026, 3, 15))

        with self.assertRaises(ErreurMetier) as contexte:
            services.modifier_competition(
                self.conn,
                competition.id,
                nom=competition.nom,
                date_debut=date(2026, 3, 14),
                date_fin=date(2026, 3, 14),  # exclut l'épreuve du 15
            )
        self.assertIn("hors des nouvelles dates", str(contexte.exception))

    def test_elargir_les_dates_reste_possible(self):
        competition = self._competition()
        modifiee = services.modifier_competition(
            self.conn,
            competition.id,
            nom=competition.nom,
            date_debut=date(2026, 3, 10),
            date_fin=date(2026, 3, 20),
        )
        self.assertEqual(modifiee.date_debut, date(2026, 3, 10))

    def test_statut_non_modifie_par_cette_fonction(self):
        competition = self._competition()
        modifiee = services.modifier_competition(
            self.conn,
            competition.id,
            nom="X",
            date_debut=competition.date_debut,
            date_fin=competition.date_fin,
        )
        self.assertEqual(modifiee.statut, StatutCompetition.OUVERTE)


class TestModifierEpreuve(ServiceTestCase):
    def test_modification_valide(self):
        competition = self._competition()
        epreuve = self._epreuve(competition)
        modifiee = services.modifier_epreuve(
            self.conn,
            epreuve.id,
            nom="Nom corrigé",
            date_epreuve=date(2026, 3, 15),
            bareme_id="flint-indoor",
        )
        self.assertEqual(modifiee.nom, "Nom corrigé")
        self.assertEqual(modifiee.bareme_id, "flint-indoor")
        self.assertEqual(db.get_epreuve(self.conn, epreuve.id), modifiee)

    def test_epreuve_inconnue_refusee(self):
        with self.assertRaises(ErreurMetier):
            services.modifier_epreuve(
                self.conn,
                "inconnue",
                nom="X",
                date_epreuve=date(2026, 1, 1),
                bareme_id="ifaa-indoor",
            )

    def test_nom_vide_refuse(self):
        epreuve = self._epreuve(self._competition())
        with self.assertRaises(ErreurMetier):
            services.modifier_epreuve(
                self.conn,
                epreuve.id,
                nom="  ",
                date_epreuve=epreuve.date,
                bareme_id=epreuve.bareme_id,
            )

    def test_bareme_inconnu_refuse(self):
        epreuve = self._epreuve(self._competition())
        with self.assertRaises(ErreurMetier):
            services.modifier_epreuve(
                self.conn,
                epreuve.id,
                nom="X",
                date_epreuve=epreuve.date,
                bareme_id="bareme-fantome",
            )

    def test_date_hors_competition_refusee(self):
        epreuve = self._epreuve(self._competition())  # compétition 2026-03-14 -- 15
        with self.assertRaises(ErreurMetier):
            services.modifier_epreuve(
                self.conn,
                epreuve.id,
                nom="X",
                date_epreuve=date(2026, 4, 1),
                bareme_id=epreuve.bareme_id,
            )

    def test_changer_le_bareme_sans_score_reste_possible(self):
        epreuve = self._epreuve(self._competition(), bareme_id="ifaa-indoor")
        modifiee = services.modifier_epreuve(
            self.conn,
            epreuve.id,
            nom=epreuve.nom,
            date_epreuve=epreuve.date,
            bareme_id="flint-indoor",
        )
        self.assertEqual(modifiee.bareme_id, "flint-indoor")

    def test_changer_le_bareme_apres_saisie_refuse(self):
        competition = self._competition()
        epreuve = self._epreuve(competition, bareme_id="ifaa-indoor")
        inscription = services.inscrire(self.conn, "FR-1", epreuve.id)
        services.saisir_score_final(self.conn, inscription.id, 260)

        with self.assertRaises(ErreurMetier) as contexte:
            services.modifier_epreuve(
                self.conn,
                epreuve.id,
                nom=epreuve.nom,
                date_epreuve=epreuve.date,
                bareme_id="flint-indoor",
            )
        self.assertIn("scores ont déjà été", str(contexte.exception))

    def test_garder_le_meme_bareme_apres_saisie_reste_possible(self):
        # Changer le nom ou la date après saisie ne doit pas être bloqué --
        # seul un changement de barème l'est.
        competition = self._competition()
        epreuve = self._epreuve(competition, bareme_id="ifaa-indoor")
        inscription = services.inscrire(self.conn, "FR-1", epreuve.id)
        services.saisir_score_final(self.conn, inscription.id, 260)

        modifiee = services.modifier_epreuve(
            self.conn,
            epreuve.id,
            nom="Nom corrigé après saisie",
            date_epreuve=epreuve.date,
            bareme_id="ifaa-indoor",
        )
        self.assertEqual(modifiee.nom, "Nom corrigé après saisie")

    def test_competition_cloturee_refuse_la_modification(self):
        competition = self._competition()
        epreuve = self._epreuve(competition)
        competition_cloturee = services.modifier_competition(
            self.conn,
            competition.id,
            nom=competition.nom,
            date_debut=competition.date_debut,
            date_fin=competition.date_fin,
        )
        # modifier_competition ne change pas le statut -- on le force
        # directement en base pour simuler une compétition déjà clôturée.
        db.update_competition(
            self.conn,
            Competition(
                id=competition.id,
                nom=competition_cloturee.nom,
                date_debut=competition_cloturee.date_debut,
                date_fin=competition_cloturee.date_fin,
                lieu=competition_cloturee.lieu,
                statut=StatutCompetition.CLOTUREE,
                categories_veteran_actives=competition_cloturee.categories_veteran_actives,
            ),
        )
        with self.assertRaises(ErreurMetier):
            services.modifier_epreuve(
                self.conn,
                epreuve.id,
                nom="X",
                date_epreuve=epreuve.date,
                bareme_id=epreuve.bareme_id,
            )


class TestInscrire(ServiceTestCase):
    def test_inscription_valide(self):
        epreuve = self._epreuve(self._competition())
        inscription = services.inscrire(self.conn, "FR-1", epreuve.id)
        self.assertEqual(inscription.id_federal, "FR-1")

    def test_competiteur_inconnu_refuse(self):
        epreuve = self._epreuve(self._competition())
        with self.assertRaises(ErreurMetier):
            services.inscrire(self.conn, "FR-INCONNU", epreuve.id)

    def test_double_inscription_refusee_avec_message_lisible(self):
        epreuve = self._epreuve(self._competition())
        services.inscrire(self.conn, "FR-1", epreuve.id)
        with self.assertRaises(ErreurMetier) as contexte:
            services.inscrire(self.conn, "FR-1", epreuve.id)
        self.assertIn("déjà inscrit", str(contexte.exception))


class TestSaisirScoreFinal(ServiceTestCase):
    def setUp(self):
        super().setUp()
        self.competition = self._competition()
        self.epreuve = self._epreuve(self.competition)  # ifaa-indoor : score_max=300
        self.inscription = services.inscrire(self.conn, "FR-1", self.epreuve.id)

    def test_saisie_valide_est_validee_par_defaut(self):
        score = services.saisir_score_final(self.conn, self.inscription.id, 260, nombre_x=10)
        self.assertEqual(score.statut, StatutScore.VALIDE)
        self.assertEqual(score.total, 260)
        self.assertEqual(score.nombre_x, 10)

    def test_total_negatif_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.saisir_score_final(self.conn, self.inscription.id, -1)

    def test_total_superieur_au_score_max_refuse(self):
        with self.assertRaises(ErreurMetier) as contexte:
            services.saisir_score_final(self.conn, self.inscription.id, 301)
        self.assertIn("score maximum", str(contexte.exception))

    def test_total_egal_au_score_max_accepte(self):
        score = services.saisir_score_final(self.conn, self.inscription.id, 300)
        self.assertEqual(score.total, 300)

    def test_nombre_x_negatif_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.saisir_score_final(self.conn, self.inscription.id, 260, nombre_x=-1)

    def test_nombre_x_superieur_au_nombre_de_fleches_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.saisir_score_final(self.conn, self.inscription.id, 260, nombre_x=61)

    def test_x_refuse_si_le_bareme_nen_utilise_pas(self):
        # Flint Indoor : departage_par_x=False.
        epreuve_flint = self._epreuve(self.competition, bareme_id="flint-indoor", nom="Flint")
        inscription = services.inscrire(self.conn, "FR-1", epreuve_flint.id)
        with self.assertRaises(ErreurMetier) as contexte:
            services.saisir_score_final(self.conn, inscription.id, 200, nombre_x=1)
        self.assertIn("n'utilise pas de zone X", str(contexte.exception))

    def test_correction_ecrase_le_score_precedent_sans_doublon(self):
        services.saisir_score_final(self.conn, self.inscription.id, 200)
        services.saisir_score_final(self.conn, self.inscription.id, 260)
        score = db.get_score_by_inscription(self.conn, self.inscription.id)
        self.assertEqual(score.total, 260)

    def test_inscription_inconnue_refusee(self):
        with self.assertRaises(ErreurMetier):
            services.saisir_score_final(self.conn, "inscription-fantome", 200)


class TestClassementEpreuve(ServiceTestCase):
    def test_classement_utilise_le_reglage_veteran_de_la_competition(self):
        # Compétiteur né en 1965 -> 61 ans en 2026 -> Veteran si activé.
        db.insert_competiteur(
            self.conn,
            Competiteur(
                id_federal="FR-VET",
                nom="Ancien",
                prenom="Jean",
                code_club="77123",
                sexe=Sexe.M,
                date_naissance=date(1965, 1, 1),
                code_style="BB-R",
            ),
        )
        competition = self._competition(categories_veteran_actives=True)
        epreuve = self._epreuve(competition)
        inscription = services.inscrire(self.conn, "FR-VET", epreuve.id)
        services.saisir_score_final(self.conn, inscription.id, 260)

        classement = services.classement_epreuve(self.conn, epreuve.id)
        self.assertIn("VMBB-R", classement)

    def test_classement_vide_si_aucune_inscription(self):
        epreuve = self._epreuve(self._competition())
        self.assertEqual(services.classement_epreuve(self.conn, epreuve.id), {})

    def test_epreuve_inconnue_refusee(self):
        with self.assertRaises(ErreurMetier):
            services.classement_epreuve(self.conn, "epreuve-fantome")


class TestCreerClub(ServiceTestCase):
    def test_creation_valide(self):
        club = services.creer_club(self.conn, "75001", "Club de Paris", "Paris")
        self.assertEqual(db.get_club(self.conn, "75001"), club)

    def test_ville_optionnelle(self):
        club = services.creer_club(self.conn, "75001", "Club de Paris")
        self.assertEqual(club.ville, "")

    def test_code_vide_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.creer_club(self.conn, "   ", "Club de Paris")

    def test_nom_vide_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.creer_club(self.conn, "75001", "   ")

    def test_code_deja_pris_refuse_sans_ecraser(self):
        with self.assertRaises(ErreurMetier) as contexte:
            services.creer_club(self.conn, "77123", "Nom différent")
        self.assertIn("existe déjà", str(contexte.exception))
        self.assertEqual(db.get_club(self.conn, "77123").nom, "Archers Libres de FLP")


class TestModifierClub(ServiceTestCase):
    def test_modification_valide(self):
        club = services.modifier_club(self.conn, "77123", "Nouveau nom", "Nouvelle ville")
        self.assertEqual(club.nom, "Nouveau nom")
        self.assertEqual(db.get_club(self.conn, "77123"), club)

    def test_club_inconnu_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.modifier_club(self.conn, "CLUB-FANTOME", "X")

    def test_nom_vide_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.modifier_club(self.conn, "77123", "   ")

    def test_code_club_reste_le_meme(self):
        club = services.modifier_club(self.conn, "77123", "Nouveau nom")
        self.assertEqual(club.code_club, "77123")


class TestCreerCompetiteur(ServiceTestCase):
    def test_creation_valide(self):
        competiteur = services.creer_competiteur(
            self.conn, "FR-2", "Martin", "Léo", "77123", Sexe.M, date(1995, 6, 1), "BB-R"
        )
        self.assertEqual(db.get_competiteur(self.conn, "FR-2"), competiteur)

    def test_licence_optionnelle(self):
        competiteur = services.creer_competiteur(
            self.conn, "FR-2", "Martin", "Léo", "77123", Sexe.M, date(1995, 6, 1), "BB-R"
        )
        self.assertIsNone(competiteur.licence_valide_jusqu_au)

    def test_id_federal_deja_pris_refuse_sans_ecraser(self):
        with self.assertRaises(ErreurMetier) as contexte:
            services.creer_competiteur(
                self.conn, "FR-1", "Autre", "Nom", "77123", Sexe.M, date(2000, 1, 1), "BB-R"
            )
        self.assertIn("existe déjà", str(contexte.exception))
        self.assertEqual(db.get_competiteur(self.conn, "FR-1").nom, "Dupont")

    def test_club_inconnu_refuse_sans_creation_automatique(self):
        with self.assertRaises(ErreurMetier) as contexte:
            services.creer_competiteur(
                self.conn, "FR-2", "X", "Y", "CLUB-FANTOME", Sexe.M, date(2000, 1, 1), "BB-R"
            )
        self.assertIn("Club inconnu", str(contexte.exception))
        self.assertIsNone(db.get_club(self.conn, "CLUB-FANTOME"))

    def test_style_inconnu_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.creer_competiteur(
                self.conn, "FR-2", "X", "Y", "77123", Sexe.M, date(2000, 1, 1), "STYLE-FANTOME"
            )

    def test_nom_vide_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.creer_competiteur(
                self.conn, "FR-2", "  ", "Y", "77123", Sexe.M, date(2000, 1, 1), "BB-R"
            )


class TestModifierCompetiteur(ServiceTestCase):
    def test_modification_valide(self):
        competiteur = services.modifier_competiteur(
            self.conn,
            "FR-1",
            "Nouveau nom",
            "Nouveau prenom",
            "77123",
            Sexe.M,
            date(1990, 1, 1),
            "LB",
        )
        self.assertEqual(competiteur.nom, "Nouveau nom")
        self.assertEqual(db.get_competiteur(self.conn, "FR-1"), competiteur)

    def test_id_federal_reste_le_meme(self):
        competiteur = services.modifier_competiteur(
            self.conn, "FR-1", "X", "Y", "77123", Sexe.F, date(1995, 3, 14), "BB-R"
        )
        self.assertEqual(competiteur.id_federal, "FR-1")

    def test_competiteur_inconnu_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.modifier_competiteur(
                self.conn, "FR-FANTOME", "X", "Y", "77123", Sexe.M, date(2000, 1, 1), "BB-R"
            )

    def test_nom_vide_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.modifier_competiteur(
                self.conn, "FR-1", "   ", "Y", "77123", Sexe.F, date(1995, 3, 14), "BB-R"
            )

    def test_club_inconnu_refuse_sans_creation_automatique(self):
        with self.assertRaises(ErreurMetier) as contexte:
            services.modifier_competiteur(
                self.conn, "FR-1", "X", "Y", "CLUB-FANTOME", Sexe.F, date(1995, 3, 14), "BB-R"
            )
        self.assertIn("Club inconnu", str(contexte.exception))

    def test_style_inconnu_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.modifier_competiteur(
                self.conn, "FR-1", "X", "Y", "77123", Sexe.F, date(1995, 3, 14), "STYLE-FANTOME"
            )

    def test_licence_modifiable(self):
        competiteur = services.modifier_competiteur(
            self.conn,
            "FR-1",
            "X",
            "Y",
            "77123",
            Sexe.F,
            date(1995, 3, 14),
            "BB-R",
            licence_valide_jusqu_au=date(2026, 12, 31),
        )
        self.assertEqual(competiteur.licence_valide_jusqu_au, date(2026, 12, 31))


class TestParserDate(ServiceTestCase):
    def test_date_valide(self):
        self.assertEqual(parser_date("2026-03-14", "Date"), date(2026, 3, 14))

    def test_espaces_autour_tolerees(self):
        self.assertEqual(parser_date("  2026-03-14  ", "Date"), date(2026, 3, 14))

    def test_format_invalide_leve_erreur_metier(self):
        with self.assertRaises(ErreurMetier) as contexte:
            parser_date("14/03/2026", "Date de début")
        self.assertIn("Date de début invalide", str(contexte.exception))

    def test_chaine_vide_leve_erreur_metier(self):
        with self.assertRaises(ErreurMetier):
            parser_date("", "Date")


class TestListerEpreuvesToutes(ServiceTestCase):
    def test_toutes_competitions_confondues_triees_par_date_desc(self):
        c1 = self._competition(
            nom="Ancienne", date_debut=date(2025, 1, 1), date_fin=date(2025, 1, 2)
        )
        e1 = self._epreuve(c1, date_epreuve=date(2025, 1, 1))
        c2 = self._competition(
            nom="Récente", date_debut=date(2026, 3, 14), date_fin=date(2026, 3, 15)
        )
        e2 = self._epreuve(c2, date_epreuve=date(2026, 3, 14))

        resultat = services.lister_epreuves_toutes(self.conn)

        self.assertEqual([e.id for _, e in resultat], [e2.id, e1.id])

    def test_liste_vide_si_aucune_epreuve(self):
        self.assertEqual(services.lister_epreuves_toutes(self.conn), [])


class TestTemplateEpreuve(ServiceTestCase):
    def test_creer_template_valide(self):
        template = services.creer_template_epreuve(self.conn, "IFAA Indoor", "ifaa-indoor")
        self.assertEqual(template.nom, "IFAA Indoor")
        self.assertIn(template, services.lister_templates_epreuve(self.conn))

    def test_nom_vide_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.creer_template_epreuve(self.conn, "   ", "ifaa-indoor")

    def test_bareme_inconnu_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.creer_template_epreuve(self.conn, "Modèle", "bareme-fantome")

    def test_creer_template_depuis_epreuve_existante(self):
        epreuve = self._epreuve(self._competition(), nom="IFAA Indoor -- samedi")
        template = services.creer_template_depuis_epreuve(self.conn, epreuve.id)
        self.assertEqual(template.nom, "IFAA Indoor -- samedi")
        self.assertEqual(template.bareme_id, epreuve.bareme_id)

    def test_creer_template_depuis_epreuve_avec_nom_personnalise(self):
        epreuve = self._epreuve(self._competition(), nom="IFAA Indoor -- samedi")
        template = services.creer_template_depuis_epreuve(
            self.conn, epreuve.id, nom_template="IFAA Indoor"
        )
        self.assertEqual(template.nom, "IFAA Indoor")

    def test_creer_template_depuis_epreuve_inconnue_refuse(self):
        with self.assertRaises(ErreurMetier):
            services.creer_template_depuis_epreuve(self.conn, "epreuve-fantome")

    def test_creer_epreuve_depuis_template(self):
        competition_source = self._competition()
        epreuve_source = self._epreuve(
            competition_source, nom="IFAA Indoor -- samedi", bareme_id="ifaa-indoor"
        )
        template = services.creer_template_depuis_epreuve(
            self.conn, epreuve_source.id, nom_template="IFAA Indoor"
        )

        autre_competition = self._competition(
            nom="Autre compétition",
            date_debut=date(2026, 5, 1),
            date_fin=date(2026, 5, 2),
        )
        nouvelle_epreuve = services.creer_epreuve_depuis_template(
            self.conn, autre_competition.id, template.id, date(2026, 5, 1)
        )

        self.assertEqual(nouvelle_epreuve.nom, "IFAA Indoor")
        self.assertEqual(nouvelle_epreuve.bareme_id, "ifaa-indoor")
        self.assertEqual(nouvelle_epreuve.competition_id, autre_competition.id)

    def test_creer_epreuve_depuis_template_reprend_les_validations_de_creer_epreuve(self):
        # Une date hors des bornes de la compétition doit être refusée,
        # exactement comme creer_epreuve() -- pas de chemin de contournement
        # via un modèle.
        template = services.creer_template_epreuve(self.conn, "IFAA Indoor", "ifaa-indoor")
        competition = self._competition()  # 2026-03-14 -- 2026-03-15
        with self.assertRaises(ErreurMetier):
            services.creer_epreuve_depuis_template(
                self.conn, competition.id, template.id, date(2026, 4, 1)
            )

    def test_template_inconnu_refuse(self):
        competition = self._competition()
        with self.assertRaises(ErreurMetier):
            services.creer_epreuve_depuis_template(
                self.conn, competition.id, "template-fantome", date(2026, 3, 14)
            )


class TestListerCompetiteursNonInscrits(ServiceTestCase):
    def setUp(self):
        super().setUp()
        db.insert_competiteur(
            self.conn,
            Competiteur(
                id_federal="FR-2",
                nom="Martin",
                prenom="Léo",
                code_club="77123",
                sexe=Sexe.M,
                date_naissance=date(1995, 6, 1),
                code_style="BB-R",
            ),
        )

    def test_exclut_les_deja_inscrits(self):
        epreuve = self._epreuve(self._competition())
        services.inscrire(self.conn, "FR-1", epreuve.id)

        non_inscrits = services.lister_competiteurs_non_inscrits(self.conn, epreuve.id)

        self.assertEqual([c.id_federal for c in non_inscrits], ["FR-2"])

    def test_tous_non_inscrits_si_aucune_inscription(self):
        epreuve = self._epreuve(self._competition())
        non_inscrits = services.lister_competiteurs_non_inscrits(self.conn, epreuve.id)
        self.assertEqual({c.id_federal for c in non_inscrits}, {"FR-1", "FR-2"})


class TestLibelles(ServiceTestCase):
    def test_libelle_epreuve(self):
        competition = self._competition(nom="Week-end FFTL")
        epreuve = self._epreuve(competition, nom="IFAA Indoor", date_epreuve=date(2026, 3, 14))
        self.assertEqual(
            libelle_epreuve(competition, epreuve),
            "Week-end FFTL — IFAA Indoor (2026-03-14)",
        )

    def test_libelle_competiteur_inclut_lid_federal(self):
        competiteur = db.get_competiteur(self.conn, "FR-1")
        self.assertEqual(libelle_competiteur(competiteur), "Marie Dupont (FR-1)")


class TestResumerAccueil(ServiceTestCase):
    def test_base_vide(self):
        # ServiceTestCase crée déjà un club, un style et FR-1 -- mais
        # aucune compétition/épreuve tant qu'on n'en crée pas.
        resume = services.resumer_accueil(self.conn)
        self.assertEqual(resume.nb_competitions, 0)
        self.assertEqual(resume.nb_competiteurs, 1)
        self.assertEqual(resume.nb_epreuves, 0)
        self.assertIsNone(resume.derniere_epreuve)

    def test_compte_competitions_et_epreuves(self):
        competition = self._competition()
        self._epreuve(competition)

        resume = services.resumer_accueil(self.conn)

        self.assertEqual(resume.nb_competitions, 1)
        self.assertEqual(resume.nb_epreuves, 1)

    def test_derniere_epreuve_est_la_plus_recente(self):
        c1 = self._competition(
            nom="Ancienne", date_debut=date(2025, 1, 1), date_fin=date(2025, 1, 2)
        )
        self._epreuve(c1, nom="Vieille épreuve", date_epreuve=date(2025, 1, 1))
        c2 = self._competition(
            nom="Récente", date_debut=date(2026, 3, 14), date_fin=date(2026, 3, 15)
        )
        epreuve_recente = self._epreuve(c2, nom="Épreuve récente", date_epreuve=date(2026, 3, 14))

        resume = services.resumer_accueil(self.conn)

        self.assertIsNotNone(resume.derniere_epreuve)
        competition_resultat, epreuve_resultat = resume.derniere_epreuve
        self.assertEqual(epreuve_resultat.id, epreuve_recente.id)
        self.assertEqual(competition_resultat.id, c2.id)


if __name__ == "__main__":
    unittest.main()
